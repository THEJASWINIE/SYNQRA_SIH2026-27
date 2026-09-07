#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>

// =====================================================
// VEHICLE B - TRUCK_02
//
// DIGITAL TWIN -> MOTOR
//          +
// BIDIRECTIONAL V2V
//          +
// WIFI -> HMI
//
// A <------LoRa------> B
//                         |
//                         +---- WiFi ----> HMI
//
// DIGITAL TWIN commands B motor velocity.
// B broadcasts that velocity through existing V2V.
// =====================================================


// =====================================================
// MOTOR PINS - FROZEN
// =====================================================

#define LEFT_IN1   25
#define LEFT_IN2   26
#define LEFT_PWM   27

#define RIGHT_IN1  32
#define RIGHT_IN2  33
#define RIGHT_PWM 14


// =====================================================
// SPEED SENSOR
// =====================================================

#define SPEED_SENSOR_PIN 35
#define PULSES_PER_REV   43.0


volatile unsigned long pulseCount = 0;
unsigned long previousPulseCount = 0;

float wheelRPM = 0.0;
float measuredVehicleSpeed = 0.0;


// =====================================================
// MPU6050
// =====================================================

#define MPU_ADDR 0x68

#define MPU_SDA 21
#define MPU_SCL 22

int16_t AcX = 0;
int16_t AcY = 0;
int16_t AcZ = 0;

int16_t GyX = 0;
int16_t GyY = 0;
int16_t GyZ = 0;


// =====================================================
// LORA
// =====================================================

#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23

#define LORA_SS    5
#define LORA_RST   4
#define LORA_DIO0  34

#define LORA_FREQUENCY 433E6


// =====================================================
// WIFI
// =====================================================

// Credentials and the HMI endpoint are NOT stored in source.
// Copy secrets.example.h to secrets.h in this sketch folder and
// fill in the values for your deployment. secrets.h is gitignored.
#include "secrets.h"

const char* WIFI_SSID = SECRET_WIFI_SSID;
const char* WIFI_PASSWORD = SECRET_WIFI_PASSWORD;

const char* HMI_SERVER = SECRET_HMI_TELEMETRY_URL;


// =====================================================
// DIGITAL TWIN SERVER
// =====================================================

WebServer commandServer(80);


// =====================================================
// PROTOTYPE SPEED LIMITS
// =====================================================

// Maximum physical prototype velocity.
// Twin physics velocity is scaled down before motor control.

const float PROTOTYPE_SCALE = 0.10f;

const float MAX_PROTOTYPE_SPEED_MS = 1.40f;

const int MAX_MOTOR_PWM = 220;

const int MIN_MOTOR_PWM = 0;


// =====================================================
// MOTOR RAMP
// =====================================================

const unsigned long MOTOR_UPDATE_INTERVAL = 50;

const int PWM_STEP = 3;

unsigned long lastMotorUpdate = 0;


// =====================================================
// DIGITAL TWIN STATE
// =====================================================

float commandedSpeedMs = 0.0f;

float appliedSpeedMs = 0.0f;

int targetMotorPWM = 0;

int appliedMotorPWM = 0;

String lastCommandId = "NONE";

unsigned long lastCommandReceived = 0;


// Stop if twin disappears.

const unsigned long COMMAND_TIMEOUT_MS = 15000;


// =====================================================
// V2V
// =====================================================

unsigned long txSequence = 0;

const unsigned long V2V_INTERVAL = 2000;

// B transmits after A.

const unsigned long V2V_START_DELAY = 1000;

unsigned long lastTransmission = 0;


// =====================================================
// REMOTE TRUCK A
// =====================================================

unsigned long remoteSequence = 0;

float remoteRPM = 0.0;

float remoteSpeed = 0.0;

int remoteAccelX = 0;
int remoteAccelY = 0;
int remoteAccelZ = 0;

int remoteGyroX = 0;
int remoteGyroY = 0;
int remoteGyroZ = 0;

int remoteRSSI = 0;

float remoteSNR = 0.0;

unsigned long lastRemotePacket = 0;


// =====================================================
// STATISTICS
// =====================================================

unsigned long validPackets = 0;
unsigned long duplicatePackets = 0;
unsigned long outOfOrderPackets = 0;
unsigned long missedPackets = 0;
unsigned long malformedPackets = 0;
unsigned long ignoredPackets = 0;

unsigned long hmiPacketsSent = 0;
unsigned long hmiPacketsFailed = 0;


// =====================================================
// TIMERS
// =====================================================

unsigned long lastSpeedCalculation = 0;
unsigned long lastIMURead = 0;
unsigned long lastHMITransmission = 0;
unsigned long lastStatusPrint = 0;

const unsigned long HMI_INTERVAL = 2000;


// =====================================================
// SPEED ISR
// =====================================================

void IRAM_ATTR speedSensorISR()
{
  pulseCount++;
}


// =====================================================
// MOTOR
// =====================================================

void stopVehicle()
{
  analogWrite(LEFT_PWM, 0);
  analogWrite(RIGHT_PWM, 0);

  appliedMotorPWM = 0;
  appliedSpeedMs = 0.0f;
}


void setForwardDirection()
{
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);

  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);
}


void applyMotorPWM(int pwm)
{
  pwm = constrain(
    pwm,
    MIN_MOTOR_PWM,
    MAX_MOTOR_PWM
  );

  if (pwm <= 0)
  {
    analogWrite(LEFT_PWM, 0);
    analogWrite(RIGHT_PWM, 0);
    return;
  }

  setForwardDirection();

  analogWrite(LEFT_PWM, pwm);
  analogWrite(RIGHT_PWM, pwm);
}


// =====================================================
// SPEED -> PWM
// =====================================================

int speedToPWM(float speedMs)
{
  if (!isfinite(speedMs))
    return 0;

  if (speedMs <= 0.0f)
    return 0;

  speedMs = constrain(
    speedMs,
    0.0f,
    MAX_PROTOTYPE_SPEED_MS
  );

  float pwm =
    (speedMs / MAX_PROTOTYPE_SPEED_MS)
    * MAX_MOTOR_PWM;

  return (int)round(pwm);
}


// =====================================================
// CONTINUOUS MOTOR CONTROL
// =====================================================

void updateMotorControl()
{
  unsigned long now = millis();

  if (
    now - lastMotorUpdate <
    MOTOR_UPDATE_INTERVAL
  )
  {
    return;
  }

  lastMotorUpdate = now;


  // -------------------------------------------------
  // COMMAND TIMEOUT
  // -------------------------------------------------

  if (
    lastCommandReceived != 0 &&
    now - lastCommandReceived >
    COMMAND_TIMEOUT_MS
  )
  {
    if (commandedSpeedMs != 0.0f)
    {
      Serial.println();
      Serial.println(
        "!!! DIGITAL TWIN TIMEOUT -> STOP !!!"
      );
    }

    commandedSpeedMs = 0.0f;
  }


  // -------------------------------------------------
  // TARGET PWM
  // -------------------------------------------------

  targetMotorPWM =
    speedToPWM(commandedSpeedMs);


  // -------------------------------------------------
  // RAMP UP
  // -------------------------------------------------

  if (
    appliedMotorPWM <
    targetMotorPWM
  )
  {
    appliedMotorPWM += PWM_STEP;

    if (
      appliedMotorPWM >
      targetMotorPWM
    )
    {
      appliedMotorPWM =
        targetMotorPWM;
    }
  }


  // -------------------------------------------------
  // RAMP DOWN
  // -------------------------------------------------

  else if (
    appliedMotorPWM >
    targetMotorPWM
  )
  {
    appliedMotorPWM -= PWM_STEP;

    if (
      appliedMotorPWM <
      targetMotorPWM
    )
    {
      appliedMotorPWM =
        targetMotorPWM;
    }
  }


  // -------------------------------------------------
  // APPLY
  // -------------------------------------------------

  applyMotorPWM(
    appliedMotorPWM
  );


  // -------------------------------------------------
  // CALCULATE APPLIED PROTOTYPE VELOCITY
  // -------------------------------------------------

  appliedSpeedMs =
    (
      (float)appliedMotorPWM /
      (float)MAX_MOTOR_PWM
    )
    *
    MAX_PROTOTYPE_SPEED_MS;
}


// =====================================================
// MPU6050 INIT
// =====================================================

void initializeMPU6050()
{
  Wire.beginTransmission(MPU_ADDR);

  Wire.write(0x6B);
  Wire.write(0x00);

  byte status =
    Wire.endTransmission(true);

  if (status == 0)
  {
    Serial.println(
      "MPU6050 Initialized"
    );
  }
  else
  {
    Serial.print(
      "MPU6050 ERROR: "
    );

    Serial.println(status);
  }
}


// =====================================================
// MPU6050 READ
// =====================================================

void readMPU6050()
{
  Wire.beginTransmission(MPU_ADDR);

  Wire.write(0x3B);

  Wire.endTransmission(false);

  Wire.requestFrom(
    MPU_ADDR,
    6,
    true
  );

  if (Wire.available() >= 6)
  {
    AcX =
      Wire.read() << 8 |
      Wire.read();

    AcY =
      Wire.read() << 8 |
      Wire.read();

    AcZ =
      Wire.read() << 8 |
      Wire.read();
  }


  Wire.beginTransmission(MPU_ADDR);

  Wire.write(0x43);

  Wire.endTransmission(false);

  Wire.requestFrom(
    MPU_ADDR,
    6,
    true
  );

  if (Wire.available() >= 6)
  {
    GyX =
      Wire.read() << 8 |
      Wire.read();

    GyY =
      Wire.read() << 8 |
      Wire.read();

    GyZ =
      Wire.read() << 8 |
      Wire.read();
  }
}


// =====================================================
// ENCODER SPEED
// =====================================================

void calculateSpeed()
{
  noInterrupts();

  unsigned long currentPulseCount =
    pulseCount;

  interrupts();


  unsigned long newPulses =
    currentPulseCount -
    previousPulseCount;


  wheelRPM =
    (
      (float)newPulses /
      PULSES_PER_REV
    )
    *
    60.0;


  previousPulseCount =
    currentPulseCount;


  // This remains the measured speed.
  // Existing project convention is preserved.

  measuredVehicleSpeed =
    wheelRPM;
}


// =====================================================
// BUILD V2V STATE
// =====================================================

String buildOwnState()
{
  txSequence++;


  /*
   * IMPORTANT:
   *
   * The V2V SPEED FIELD carries the
   * Digital-Twin-controlled prototype
   * velocity.
   *
   * This allows TRUCK_01 to react to
   * the Twin command even if the encoder
   * is not generating pulses.
   */

  float v2vSpeed =
    appliedSpeedMs;


  String packet = "";

  packet += "STATE";
  packet += ",TRUCK_02";
  packet += ",";
  packet += String(txSequence);
  packet += ",";
  packet += String(wheelRPM, 2);
  packet += ",";
  packet += String(v2vSpeed, 3);
  packet += ",";
  packet += String(AcX);
  packet += ",";
  packet += String(AcY);
  packet += ",";
  packet += String(AcZ);
  packet += ",";
  packet += String(GyX);
  packet += ",";
  packet += String(GyY);
  packet += ",";
  packet += String(GyZ);

  return packet;
}


// =====================================================
// SEND V2V B -> A
// =====================================================

void sendV2VState()
{
  String packet =
    buildOwnState();


  Serial.println();
  Serial.println(
    ">>> V2V TX B -> A"
  );

  Serial.println(packet);


  LoRa.beginPacket();

  LoRa.print(packet);

  LoRa.endPacket();


  Serial.println(
    "TX COMPLETE"
  );


  // Explicitly return to receive mode.

  LoRa.receive();
}


// =====================================================
// PARSE TRUCK A
// =====================================================

bool parseVehicleA(
  String packet
)
{
  packet.trim();


  String fields[11];

  int fieldIndex = 0;
  int startIndex = 0;


  for (
    int i = 0;
    i <= packet.length();
    i++
  )
  {
    if (
      packet.charAt(i) == ',' ||
      i == packet.length()
    )
    {
      if (fieldIndex < 11)
      {
        fields[fieldIndex] =
          packet.substring(
            startIndex,
            i
          );

        fieldIndex++;
      }

      startIndex = i + 1;
    }
  }


  if (fieldIndex != 11)
  {
    malformedPackets++;

    Serial.println(
      "REJECTED: WRONG FIELD COUNT"
    );

    return false;
  }


  if (fields[0] != "STATE")
  {
    ignoredPackets++;
    return false;
  }


  if (fields[1] != "TRUCK_01")
  {
    ignoredPackets++;
    return false;
  }


  unsigned long sequence =
    fields[2].toInt();


  // Duplicate

  if (
    lastRemotePacket != 0 &&
    sequence == remoteSequence
  )
  {
    duplicatePackets++;

    Serial.println(
      "DUPLICATE A PACKET"
    );

    return false;
  }


  // Out of order

  if (
    lastRemotePacket != 0 &&
    sequence < remoteSequence
  )
  {
    outOfOrderPackets++;

    Serial.println(
      "OUT-OF-ORDER A PACKET"
    );

    return false;
  }


  // Missing

  if (
    lastRemotePacket != 0 &&
    sequence >
    remoteSequence + 1
  )
  {
    missedPackets +=
      sequence -
      remoteSequence -
      1;
  }


  remoteSequence = sequence;

  remoteRPM =
    fields[3].toFloat();

  remoteSpeed =
    fields[4].toFloat();

  remoteAccelX =
    fields[5].toInt();

  remoteAccelY =
    fields[6].toInt();

  remoteAccelZ =
    fields[7].toInt();

  remoteGyroX =
    fields[8].toInt();

  remoteGyroY =
    fields[9].toInt();

  remoteGyroZ =
    fields[10].toInt();


  remoteRSSI =
    LoRa.packetRssi();

  remoteSNR =
    LoRa.packetSnr();


  lastRemotePacket =
    millis();


  validPackets++;


  Serial.println();
  Serial.println(
    "<<< VALID V2V FROM TRUCK_01"
  );

  Serial.print(
    "Sequence: "
  );

  Serial.println(
    remoteSequence
  );

  Serial.print(
    "Speed: "
  );

  Serial.println(
    remoteSpeed,
    3
  );

  Serial.print(
    "RSSI: "
  );

  Serial.println(
    remoteRSSI
  );

  Serial.print(
    "SNR: "
  );

  Serial.println(
    remoteSNR,
    2
  );


  return true;
}


// =====================================================
// RECEIVE V2V
// =====================================================

void receiveV2V()
{
  int packetSize =
    LoRa.parsePacket();


  if (packetSize <= 0)
    return;


  String packet = "";


  while (LoRa.available())
  {
    packet +=
      (char)LoRa.read();
  }


  packet.trim();


  Serial.println();
  Serial.println(
    "<<< LORA PACKET"
  );

  Serial.println(packet);


  if (
    packet.startsWith(
      "STATE,TRUCK_01,"
    )
  )
  {
    parseVehicleA(packet);
  }
  else
  {
    ignoredPackets++;

    Serial.println(
      "IGNORED NON-STATE PACKET"
    );
  }


  LoRa.receive();
}


// =====================================================
// WIFI
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println(
    "Connecting Wi-Fi..."
  );


  WiFi.mode(WIFI_STA);

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );


  unsigned long start =
    millis();


  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - start < 15000
  )
  {
    delay(500);

    Serial.print(".");
  }


  Serial.println();


  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    Serial.println(
      "Wi-Fi CONNECTED"
    );

    Serial.print(
      "ESP32 IP: "
    );

    Serial.println(
      WiFi.localIP()
    );
  }
  else
  {
    Serial.println(
      "Wi-Fi unavailable"
    );
  }
}


// =====================================================
// GENERIC HMI POST
// =====================================================

bool postToHMI(
  String json
)
{
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    hmiPacketsFailed++;

    return false;
  }


  HTTPClient http;

  http.setTimeout(1000);

  http.begin(
    HMI_SERVER
  );

  http.addHeader(
    "Content-Type",
    "application/json"
  );


  int response =
    http.POST(json);


  http.end();


  if (
    response >= 200 &&
    response < 300
  )
  {
    hmiPacketsSent++;

    return true;
  }


  hmiPacketsFailed++;


  Serial.print(
    "HMI HTTP ERROR: "
  );

  Serial.println(
    response
  );


  return false;
}


// =====================================================
// SEND B TELEMETRY TO HMI
// =====================================================

void sendOwnToHMI()
{
  String json = "{";


  json +=
    "\"vehicle_id\":\"TRUCK_02\",";


  json +=
    "\"sequence\":";

  json +=
    String(txSequence);

  json += ",";


  json +=
    "\"rpm\":";

  json +=
    String(wheelRPM, 2);

  json += ",";


  // HMI gets the actual prototype
  // velocity currently applied.

  json +=
    "\"speed\":";

  json +=
    String(appliedSpeedMs, 3);

  json += ",";


  json +=
    "\"accel_x\":";

  json +=
    String(AcX);

  json += ",";


  json +=
    "\"accel_y\":";

  json +=
    String(AcY);

  json += ",";


  json +=
    "\"accel_z\":";

  json +=
    String(AcZ);

  json += ",";


  json +=
    "\"gyro_x\":";

  json +=
    String(GyX);

  json += ",";


  json +=
    "\"gyro_y\":";

  json +=
    String(GyY);

  json += ",";


  json +=
    "\"gyro_z\":";

  json +=
    String(GyZ);

  json += ",";


  json +=
    "\"source\":\"DIRECT_WIFI\"";


  json += "}";


  postToHMI(json);
}


// =====================================================
// COMMAND JSON HELPERS
// =====================================================

bool extractJsonFloat(
  const String &json,
  const char *key,
  float &value
)
{
  String search =
    String("\"") +
    key +
    "\"";


  int keyIndex =
    json.indexOf(search);


  if (keyIndex < 0)
    return false;


  int colon =
    json.indexOf(
      ':',
      keyIndex
    );


  if (colon < 0)
    return false;


  int start =
    colon + 1;


  while (
    start <
    (int)json.length() &&
    (
      json.charAt(start) == ' ' ||
      json.charAt(start) == '\t'
    )
  )
  {
    start++;
  }


  int end = start;


  while (
    end <
    (int)json.length() &&
    (
      isDigit(json.charAt(end)) ||
      json.charAt(end) == '-' ||
      json.charAt(end) == '+' ||
      json.charAt(end) == '.' ||
      json.charAt(end) == 'e' ||
      json.charAt(end) == 'E'
    )
  )
  {
    end++;
  }


  if (end == start)
    return false;


  value =
    json.substring(
      start,
      end
    ).toFloat();


  return isfinite(value);
}


String extractJsonString(
  const String &json,
  const char *key
)
{
  String search =
    String("\"") +
    key +
    "\"";


  int keyIndex =
    json.indexOf(search);


  if (keyIndex < 0)
    return "";


  int colon =
    json.indexOf(
      ':',
      keyIndex
    );


  if (colon < 0)
    return "";


  int firstQuote =
    json.indexOf(
      '"',
      colon + 1
    );


  if (firstQuote < 0)
    return "";


  int secondQuote =
    json.indexOf(
      '"',
      firstQuote + 1
    );


  if (secondQuote < 0)
    return "";


  return json.substring(
    firstQuote + 1,
    secondQuote
  );
}


// =====================================================
// DIGITAL TWIN COMMAND
// =====================================================

void handleVehicleCommand()
{
  if (
    !commandServer.hasArg("plain")
  )
  {
    commandServer.send(
      400,
      "application/json",
      "{\"status\":\"ERROR\",\"reason\":\"EMPTY_BODY\"}"
    );

    return;
  }


  String body =
    commandServer.arg("plain");

  body.trim();


  Serial.println();
  Serial.println(
    "======================================"
  );

  Serial.println(
    "DIGITAL TWIN COMMAND"
  );

  Serial.println(body);


  String vehicleId =
    extractJsonString(
      body,
      "vehicle_id"
    );


  if (
    vehicleId !=
    "TRUCK_02"
  )
  {
    commandServer.send(
      400,
      "application/json",
      "{\"status\":\"REJECTED\",\"reason\":\"WRONG_VEHICLE\"}"
    );

    return;
  }


  float requestedSpeed =
    0.0f;

  bool found = false;


  // -------------------------------------------------
  // TARGET PROTOTYPE SPEED
  // -------------------------------------------------

  if (
    extractJsonFloat(
      body,
      "target_speed_ms",
      requestedSpeed
    )
  )
  {
    found = true;
  }


  // -------------------------------------------------
  // OR FULL PHYSICS SPEED
  // -------------------------------------------------

  else
  {
    float physicsSpeed = 0.0f;


    if (
      extractJsonFloat(
        body,
        "physics_safe_speed_ms",
        physicsSpeed
      )
    )
    {
      requestedSpeed =
        physicsSpeed *
        PROTOTYPE_SCALE;

      found = true;
    }
  }


  if (
    !found ||
    !isfinite(requestedSpeed)
  )
  {
    commandServer.send(
      400,
      "application/json",
      "{\"status\":\"REJECTED\",\"reason\":\"INVALID_SPEED\"}"
    );

    return;
  }


  String commandId =
    extractJsonString(
      body,
      "command_id"
    );


  if (
    commandId.length() == 0
  )
  {
    commandId =
      "NO_ID";
  }


  // Never allow negative velocity.

  requestedSpeed =
    max(
      0.0f,
      requestedSpeed
    );


  bool clamped = false;


  if (
    requestedSpeed >
    MAX_PROTOTYPE_SPEED_MS
  )
  {
    requestedSpeed =
      MAX_PROTOTYPE_SPEED_MS;

    clamped = true;
  }


  // -------------------------------------------------
  // UPDATE CONTROL STATE
  // -------------------------------------------------

  commandedSpeedMs =
    requestedSpeed;


  targetMotorPWM =
    speedToPWM(
      commandedSpeedMs
    );


  lastCommandId =
    commandId;


  lastCommandReceived =
    millis();


  Serial.print(
    "Commanded velocity: "
  );

  Serial.print(
    commandedSpeedMs,
    3
  );

  Serial.println(
    " m/s"
  );


  Serial.print(
    "Target PWM: "
  );

  Serial.println(
    targetMotorPWM
  );


  if (clamped)
  {
    Serial.println(
      "LOCAL LIMIT -> CLAMPED"
    );
  }


  String response = "{";


  response +=
    "\"status\":\"";

  response +=
    clamped
    ? "CLAMPED"
    : "ACCEPTED";

  response += "\",";


  response +=
    "\"vehicle_id\":\"TRUCK_02\",";


  response +=
    "\"target_speed_ms\":";

  response +=
    String(
      commandedSpeedMs,
      3
    );

  response += ",";


  response +=
    "\"target_pwm\":";

  response +=
    String(
      targetMotorPWM
    );

  response += ",";


  response +=
    "\"command_id\":\"";

  response +=
    lastCommandId;

  response += "\"";


  response += "}";


  commandServer.send(
    200,
    "application/json",
    response
  );


  Serial.println(
    "COMMAND ACCEPTED"
  );

  Serial.println(
    "======================================"
  );
}


// =====================================================
// COMMAND STATUS
// =====================================================

void handleCommandStatus()
{
  String response = "{";


  response +=
    "\"vehicle_id\":\"TRUCK_02\",";


  response +=
    "\"commanded_speed_ms\":";

  response +=
    String(
      commandedSpeedMs,
      3
    );

  response += ",";


  response +=
    "\"applied_speed_ms\":";

  response +=
    String(
      appliedSpeedMs,
      3
    );

  response += ",";


  response +=
    "\"target_pwm\":";

  response +=
    String(
      targetMotorPWM
    );

  response += ",";


  response +=
    "\"applied_pwm\":";

  response +=
    String(
      appliedMotorPWM
    );

  response += ",";


  response +=
    "\"last_command_id\":\"";

  response +=
    lastCommandId;

  response += "\"";


  response += "}";


  commandServer.send(
    200,
    "application/json",
    response
  );
}


// =====================================================
// START COMMAND SERVER
// =====================================================

void startCommandServer()
{
  commandServer.on(
    "/api/command",
    HTTP_POST,
    handleVehicleCommand
  );


  commandServer.on(
    "/api/vehicle/command",
    HTTP_POST,
    handleVehicleCommand
  );


  commandServer.on(
    "/api/command/status",
    HTTP_GET,
    handleCommandStatus
  );


  commandServer.on(
    "/",
    HTTP_GET,
    []()
    {
      commandServer.send(
        200,
        "text/plain",
        "TRUCK_02 DIGITAL TWIN MOTOR SERVER"
      );
    }
  );


  commandServer.begin();


  Serial.println();
  Serial.println(
    "DIGITAL TWIN SERVER READY"
  );

  Serial.print(
    "TRUCK_02 IP: "
  );

  Serial.println(
    WiFi.localIP()
  );

  Serial.println(
    "POST /api/command"
  );

  Serial.println(
    "GET /api/command/status"
  );
}


// =====================================================
// STATUS
// =====================================================

void printStatus()
{
  Serial.println();
  Serial.println(
    "######################################"
  );

  Serial.println(
    "       TRUCK_02 STATUS"
  );

  Serial.println(
    "######################################"
  );


  Serial.println();

  Serial.println(
    "DIGITAL TWIN"
  );

  Serial.print(
    "Commanded Speed: "
  );

  Serial.print(
    commandedSpeedMs,
    3
  );

  Serial.println(
    " m/s"
  );


  Serial.print(
    "Applied Speed: "
  );

  Serial.print(
    appliedSpeedMs,
    3
  );

  Serial.println(
    " m/s"
  );


  Serial.print(
    "Target PWM: "
  );

  Serial.println(
    targetMotorPWM
  );


  Serial.print(
    "Applied PWM: "
  );

  Serial.println(
    appliedMotorPWM
  );


  Serial.println();

  Serial.println(
    "REMOTE TRUCK_01"
  );


  Serial.print(
    "Sequence: "
  );

  Serial.println(
    remoteSequence
  );


  Serial.print(
    "Speed: "
  );

  Serial.println(
    remoteSpeed,
    3
  );


  Serial.print(
    "Status: "
  );


  if (lastRemotePacket == 0)
  {
    Serial.println(
      "WAITING"
    );
  }
  else
  {
    unsigned long age =
      millis() -
      lastRemotePacket;

    if (age < 5000)
      Serial.println("ONLINE");
    else if (age < 10000)
      Serial.println("STALE");
    else
      Serial.println("OFFLINE");
  }


  Serial.println();

  Serial.println(
    "HMI GATEWAY"
  );


  Serial.print(
    "Wi-Fi: "
  );

  Serial.println(
    WiFi.status() ==
    WL_CONNECTED
    ? "CONNECTED"
    : "DISCONNECTED"
  );


  Serial.print(
    "HMI Sent: "
  );

  Serial.println(
    hmiPacketsSent
  );


  Serial.print(
    "HMI Failed: "
  );

  Serial.println(
    hmiPacketsFailed
  );


  Serial.println();

  Serial.println(
    "V2V"
  );


  Serial.print(
    "Valid: "
  );

  Serial.println(
    validPackets
  );


  Serial.print(
    "Duplicate: "
  );

  Serial.println(
    duplicatePackets
  );


  Serial.print(
    "Out-of-order: "
  );

  Serial.println(
    outOfOrderPackets
  );


  Serial.print(
    "Missing: "
  );

  Serial.println(
    missedPackets
  );


  Serial.println(
    "######################################"
  );
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(115200);

  delay(1000);


  // -------------------------------------------------
  // MOTOR
  // -------------------------------------------------

  pinMode(
    LEFT_IN1,
    OUTPUT
  );

  pinMode(
    LEFT_IN2,
    OUTPUT
  );

  pinMode(
    LEFT_PWM,
    OUTPUT
  );


  pinMode(
    RIGHT_IN1,
    OUTPUT
  );

  pinMode(
    RIGHT_IN2,
    OUTPUT
  );

  pinMode(
    RIGHT_PWM,
    OUTPUT
  );


  stopVehicle();


  // -------------------------------------------------
  // ENCODER
  // -------------------------------------------------

  pinMode(
    SPEED_SENSOR_PIN,
    INPUT
  );


  attachInterrupt(
    digitalPinToInterrupt(
      SPEED_SENSOR_PIN
    ),
    speedSensorISR,
    RISING
  );


  // -------------------------------------------------
  // MPU
  // -------------------------------------------------

  Wire.begin(
    MPU_SDA,
    MPU_SCL
  );

  initializeMPU6050();


  // -------------------------------------------------
  // LORA
  // -------------------------------------------------

  SPI.begin(
    LORA_SCK,
    LORA_MISO,
    LORA_MOSI,
    LORA_SS
  );


  LoRa.setPins(
    LORA_SS,
    LORA_RST,
    LORA_DIO0
  );


  Serial.println(
    "Initializing LoRa..."
  );


  if (
    !LoRa.begin(
      LORA_FREQUENCY
    )
  )
  {
    Serial.println(
      "LoRa FAILED"
    );

    while (true)
      delay(1000);
  }


  LoRa.enableCrc();

  LoRa.setTxPower(17);

  LoRa.receive();


  // -------------------------------------------------
  // WIFI
  // -------------------------------------------------

  connectWiFi();


  // -------------------------------------------------
  // COMMAND SERVER
  // -------------------------------------------------

  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    startCommandServer();
  }


  // -------------------------------------------------
  // TIMERS
  // -------------------------------------------------

  lastSpeedCalculation =
    millis();

  lastIMURead =
    millis();

  lastTransmission =
    millis() -
    V2V_START_DELAY;

  lastHMITransmission =
    millis();

  lastStatusPrint =
    millis();


  Serial.println();

  Serial.println(
    "======================================"
  );

  Serial.println(
    "TRUCK_02 READY"
  );

  Serial.println(
    "DIGITAL TWIN CONTROL ENABLED"
  );

  Serial.println(
    "V2V BIDIRECTIONAL ENABLED"
  );

  Serial.println(
    "======================================"
  );
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  unsigned long now =
    millis();


  // -------------------------------------------------
  // DIGITAL TWIN HTTP SERVER
  // -------------------------------------------------

  commandServer.handleClient();


  // -------------------------------------------------
  // CONTINUOUS MOTOR CONTROL
  // -------------------------------------------------

  updateMotorControl();


  // -------------------------------------------------
  // SPEED
  // -------------------------------------------------

  if (
    now -
    lastSpeedCalculation >=
    1000
  )
  {
    calculateSpeed();

    lastSpeedCalculation =
      now;
  }


  // -------------------------------------------------
  // IMU
  // -------------------------------------------------

  if (
    now -
    lastIMURead >=
    100
  )
  {
    readMPU6050();

    lastIMURead =
      now;
  }


  // -------------------------------------------------
  // V2V RECEIVE
  // -------------------------------------------------

  receiveV2V();


  // -------------------------------------------------
  // V2V TRANSMIT
  // -------------------------------------------------

  if (
    now -
    lastTransmission >=
    V2V_INTERVAL
  )
  {
    sendV2VState();

    lastTransmission =
      now;
  }


  // -------------------------------------------------
  // HMI
  // -------------------------------------------------

  if (
    now -
    lastHMITransmission >=
    HMI_INTERVAL
  )
  {
    sendOwnToHMI();

    lastHMITransmission =
      now;
  }


  // -------------------------------------------------
  // STATUS
  // -------------------------------------------------

  if (
    now -
    lastStatusPrint >=
    5000
  )
  {
    printStatus();

    lastStatusPrint =
      now;
  }


  delay(1);
}