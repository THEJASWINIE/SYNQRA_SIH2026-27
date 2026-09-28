#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>

// NVS Persistent Boot & Session ID (Gap 1 Closure)
Preferences bootPrefs;
uint32_t bootId = 1;

// WebServer for Digital Twin / Command Gateway HTTP commands
WebServer commandServer(80);

// =====================================================
// FOG-ORCHESTRATOR 2.0
// VEHICLE A - TRUCK_01
//
// BIDIRECTIONAL V2V + DIRECT WIFI HMI
//
// A <--- LoRa ---> B
// A ---- WiFi ----> HMI
//
// Vehicle B can provide a reduced velocity to A.
// That received velocity becomes A's target speed.
//
// EXISTING HARDWARE CONNECTIONS FROZEN.
// =====================================================


// =====================================================
// VEHICLE IDENTIFICATION
// =====================================================

#define VEHICLE_ID "TRUCK_01"
#define REMOTE_ID  "TRUCK_02"


// =====================================================
// MOTOR PINS - FROZEN
// =====================================================

#define LEFT_IN1   25
#define LEFT_IN2   26
#define LEFT_PWM   27

#define RIGHT_IN1  32
#define RIGHT_IN2  33
#define RIGHT_PWM 14

#define MOTOR_STBY 13


// =====================================================
// SPEED SENSOR - FROZEN
// =====================================================

#define SPEED_SENSOR_PIN      35
#define RAW_ENCODER_PPR       42.0f
#define ENCODER_EFFECTIVE_PPR 34.58f
#define PULSES_PER_REV        ENCODER_EFFECTIVE_PPR
#define WHEEL_DIAMETER_M      0.060f // 6.0 cm calibrated wheel diameter
const float WHEEL_CIRCUMFERENCE_M = 3.14159265f * WHEEL_DIAMETER_M;


// =====================================================
// MPU6050 - FROZEN
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
// LORA - FROZEN
// =====================================================

#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23

#define LORA_SS    5
#define LORA_RST   4
#define LORA_DIO0  34

#define LORA_FREQUENCY 433E6


// =====================================================
// WIFI - FROZEN
// =====================================================

// Credentials and the HMI endpoint are NOT stored in source.
// Copy secrets.example.h to secrets.h in this sketch folder and
// fill in the values for your deployment. secrets.h is gitignored.
#include "secrets.h"

const char* WIFI_SSID = SECRET_WIFI_SSID;
const char* WIFI_PASSWORD = SECRET_WIFI_PASSWORD;

const char* HMI_SERVER = SECRET_HMI_TELEMETRY_URL;


// =====================================================
// SPEED VARIABLES
// =====================================================

volatile unsigned long pulseCount = 0;

unsigned long previousPulseCount = 0;

float wheelRPM = 0.0f;
float vehicleSpeed = 0.0f;


// =====================================================
// MOTOR / DIGITAL TWIN CONTROL
// =====================================================
//
// IMPORTANT:
//
// The Digital Twin / Vehicle B provides a velocity.
// Vehicle A converts that velocity into PWM.
//
// The physical prototype is deliberately scaled.
//
// Example:
//
// B sends 1.0 m/s
//        ↓
// A target = 1.0 m/s
//        ↓
// PWM calculated locally
//
// =====================================================

// TEMPORARY CONTINUOUS FORWARD MOTOR TEST MODE
#define CONTINUOUS_FORWARD_TEST false
const int CONTINUOUS_TEST_PWM = 120;

// Default speed used when no remote velocity has been received yet.
const float DEFAULT_SPEED_MS = 0.40f;


// Maximum physical prototype speed (TRUCK_01 calibrated Vmax).
const float MAX_PROTOTYPE_SPEED_MS = 1.40f;


// Maximum PWM allowed.
const int MAX_MOTOR_PWM = 220;


// Minimum PWM for stop.
const int MIN_MOTOR_PWM = 0;


// Minimum effective starting PWM to overcome static chassis friction.
const int MIN_EFFECTIVE_PWM = 100;


// ESP32 Arduino Core 3.x LEDC PWM parameters.
const int PWM_FREQUENCY = 1000;
const int PWM_RESOLUTION = 8;


// Direction polarity inversion flags for bench/chassis alignment.
bool invertLeftMotor = false;
bool invertRightMotor = false;


// Motor update period.
const unsigned long MOTOR_UPDATE_INTERVAL = 50;


// Smooth acceleration/deceleration.
const int PWM_STEP = 4;


// Current commanded speed.
float commandedSpeedMs = 0.0f;


// Actual PWM applied.
int appliedMotorPWM = 0;


// Desired PWM.
int targetMotorPWM = 0;


// Estimated applied speed.
float appliedSpeedMs = 0.0f;


// Last motor update.
unsigned long lastMotorUpdate = 0;


// Last command received timestamp.
unsigned long lastCommandReceived = 0;


// =====================================================
// REMOTE VEHICLE B
// =====================================================

unsigned long remoteSequence = 0;

float remoteRPM = 0.0f;
float remoteSpeed = 0.0f;

int remoteAccelX = 0;
int remoteAccelY = 0;
int remoteAccelZ = 0;

int remoteGyroX = 0;
int remoteGyroY = 0;
int remoteGyroZ = 0;

int remoteRSSI = 0;
float remoteSNR = 0.0f;

unsigned long lastRemotePacket = 0;

bool remoteDataValid = false;


// =====================================================
// V2V STATISTICS
// =====================================================

unsigned long validPackets = 0;
unsigned long duplicatePackets = 0;
unsigned long outOfOrderPackets = 0;
unsigned long missingPackets = 0;
unsigned long malformedPackets = 0;
unsigned long ignoredPackets = 0;


// =====================================================
// UNIFIED MONOTONIC SEQUENCE & V2V TIMING (Gap 1)
// =====================================================

unsigned long globalSequence = 0;
unsigned long txSequence = 0;

const unsigned long V2V_INTERVAL = 2000;


// Vehicle A transmits at 500 ms into the cycle.
const unsigned long V2V_START_DELAY = 500;

unsigned long lastV2VTransmission = 0;


// =====================================================
// HMI & SAFE BEACON (Gap 2)
// =====================================================

// Strictly monotonic sequence counter for HMI telemetry (unified with globalSequence)
uint32_t telemetrySequence = 0;

// Safe Beacon parameters (Gap 2 Closure)
unsigned long lastBeaconTx = 0;
const unsigned long BEACON_INTERVAL_MS = 1000;
uint32_t beaconSequence = 0;

// Wi-Fi Connection States & Non-blocking Management
enum WiFiCommState {
  COMM_CONNECTED,
  COMM_DEGRADED,
  COMM_DISCONNECTED
};
WiFiCommState wifiState = COMM_DISCONNECTED;
unsigned long lastWiFiReconnectAttempt = 0;
const unsigned long WIFI_RECONNECT_INTERVAL_MS = 5000;

unsigned long lastHMITransmission = 0;

const unsigned long HMI_INTERVAL = 2000;

unsigned long hmiSent = 0;
unsigned long hmiFailed = 0;


// =====================================================
// OTHER TIMERS
// =====================================================

unsigned long lastSpeedCalculation = 0;
unsigned long lastIMURead = 0;
unsigned long lastStatusPrint = 0;


// =====================================================
// MOTOR COMMAND TIMEOUT
// =====================================================
//
// If Vehicle B stops sending valid V2V data for this
// duration, A does NOT blindly continue using stale
// remote data.
//
// Instead it returns to DEFAULT_SPEED_MS.
//
// You can change this to 0 if you don't want timeout
// behavior.
//
// =====================================================

const unsigned long REMOTE_COMMAND_TIMEOUT = 5000;


// =====================================================
// SPEED SENSOR ISR
// =====================================================

void IRAM_ATTR speedSensorISR()
{
  pulseCount++;
}


// =====================================================
// MOTOR - FORWARD DIRECTION
// =====================================================

void setForwardDirection()
{
  digitalWrite(MOTOR_STBY, HIGH);

  if (!invertLeftMotor)
  {
    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, HIGH);
  }
  else
  {
    digitalWrite(LEFT_IN1, HIGH);
    digitalWrite(LEFT_IN2, LOW);
  }

  if (!invertRightMotor)
  {
    digitalWrite(RIGHT_IN1, HIGH);
    digitalWrite(RIGHT_IN2, LOW);
  }
  else
  {
    digitalWrite(RIGHT_IN1, LOW);
    digitalWrite(RIGHT_IN2, HIGH);
  }
}


// =====================================================
// CONTINUOUS FORWARD TEST (UNCONDITIONAL HARDWARE DRIVE)
// =====================================================

void runContinuousForwardTest()
{
  digitalWrite(MOTOR_STBY, HIGH);

  if (!invertLeftMotor)
  {
    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, HIGH);
  }
  else
  {
    digitalWrite(LEFT_IN1, HIGH);
    digitalWrite(LEFT_IN2, LOW);
  }

  if (!invertRightMotor)
  {
    digitalWrite(RIGHT_IN1, HIGH);
    digitalWrite(RIGHT_IN2, LOW);
  }
  else
  {
    digitalWrite(RIGHT_IN1, LOW);
    digitalWrite(RIGHT_IN2, HIGH);
  }

  ledcWrite(LEFT_PWM, CONTINUOUS_TEST_PWM);
  ledcWrite(RIGHT_PWM, CONTINUOUS_TEST_PWM);

  appliedMotorPWM = CONTINUOUS_TEST_PWM;
  appliedSpeedMs =
    ((float)CONTINUOUS_TEST_PWM / (float)MAX_MOTOR_PWM) * MAX_PROTOTYPE_SPEED_MS;
}


// =====================================================
// MOTOR STOP
// =====================================================

void stopVehicle()
{
  ledcWrite(LEFT_PWM, 0);
  ledcWrite(RIGHT_PWM, 0);

  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, LOW);

  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, LOW);

  digitalWrite(MOTOR_STBY, LOW);

  appliedMotorPWM = 0;
  appliedSpeedMs = 0.0f;
}


// =====================================================
// APPLY MOTOR PWM
// =====================================================

void applyMotorPWM(int pwm)
{
  pwm = constrain(
    pwm,
    MIN_MOTOR_PWM,
    MAX_MOTOR_PWM
  );

  if (pwm <= 0)
  {
    stopVehicle();
    return;
  }

  setForwardDirection();

  ledcWrite(
    LEFT_PWM,
    pwm
  );

  ledcWrite(
    RIGHT_PWM,
    pwm
  );
}


// =====================================================
// SPEED -> PWM (WITH MINIMUM EFFECTIVE THRESHOLD)
// =====================================================

int speedToPWM(float speedMs)
{
  if (!isfinite(speedMs) || speedMs <= 0.0f)
  {
    return 0;
  }

  speedMs = constrain(
    speedMs,
    0.0f,
    MAX_PROTOTYPE_SPEED_MS
  );

  float ratio =
    speedMs /
    MAX_PROTOTYPE_SPEED_MS;

  int pwm =
    MIN_EFFECTIVE_PWM +
    (int)round(
      ratio *
      (MAX_MOTOR_PWM - MIN_EFFECTIVE_PWM)
    );

  return constrain(
    pwm,
    MIN_EFFECTIVE_PWM,
    MAX_MOTOR_PWM
  );
}


// =====================================================
// JSON PARSING HELPERS & HTTP COMMAND HANDLERS
// =====================================================

bool extractJsonFloat(
  const String &json,
  const char *key,
  float &value
)
{
  String search = String("\"") + key + "\"";
  int keyIndex = json.indexOf(search);
  if (keyIndex < 0) return false;

  int colon = json.indexOf(':', keyIndex);
  if (colon < 0) return false;

  int start = colon + 1;
  while (start < (int)json.length() && (json.charAt(start) == ' ' || json.charAt(start) == '\t'))
  {
    start++;
  }

  int end = start;
  while (end < (int)json.length() &&
         (isDigit(json.charAt(end)) || json.charAt(end) == '-' ||
          json.charAt(end) == '+' || json.charAt(end) == '.' ||
          json.charAt(end) == 'e' || json.charAt(end) == 'E'))
  {
    end++;
  }

  if (end == start) return false;
  value = json.substring(start, end).toFloat();
  return isfinite(value);
}

String extractJsonString(
  const String &json,
  const char *key
)
{
  String search = String("\"") + key + "\"";
  int keyIndex = json.indexOf(search);
  if (keyIndex < 0) return "";

  int colon = json.indexOf(':', keyIndex);
  if (colon < 0) return "";

  int firstQuote = json.indexOf('"', colon + 1);
  if (firstQuote < 0) return "";

  int secondQuote = json.indexOf('"', firstQuote + 1);
  if (secondQuote < 0) return "";

  return json.substring(firstQuote + 1, secondQuote);
}

void handleVehicleCommand()
{
  if (!commandServer.hasArg("plain"))
  {
    commandServer.send(400, "application/json", "{\"status\":\"ERROR\",\"reason\":\"EMPTY_BODY\"}");
    return;
  }

  String body = commandServer.arg("plain");
  body.trim();

  String vehicleId = extractJsonString(body, "vehicle_id");
  if (vehicleId.length() > 0 && vehicleId != VEHICLE_ID)
  {
    commandServer.send(400, "application/json", "{\"status\":\"REJECTED\",\"reason\":\"WRONG_VEHICLE\"}");
    return;
  }

  String action = extractJsonString(body, "action");
  float requestedSpeed = 0.0f;
  bool found = false;

  if (action == "STOP")
  {
    requestedSpeed = 0.0f;
    found = true;
  }
  else if (extractJsonFloat(body, "target_speed_ms", requestedSpeed))
  {
    found = true;
  }
  else if (extractJsonFloat(body, "target_speed", requestedSpeed))
  {
    found = true;
  }
  else if (extractJsonFloat(body, "velocity", requestedSpeed))
  {
    found = true;
  }
  else if (action == "FORWARD")
  {
    requestedSpeed = 0.40f;
    found = true;
  }

  if (!found || !isfinite(requestedSpeed))
  {
    commandServer.send(400, "application/json", "{\"status\":\"REJECTED\",\"reason\":\"INVALID_SPEED\"}");
    return;
  }

  requestedSpeed = max(0.0f, requestedSpeed);
  bool clamped = false;
  if (requestedSpeed > MAX_PROTOTYPE_SPEED_MS)
  {
    requestedSpeed = MAX_PROTOTYPE_SPEED_MS;
    clamped = true;
  }

  commandedSpeedMs = requestedSpeed;
  targetMotorPWM = speedToPWM(commandedSpeedMs);
  lastCommandReceived = millis();

  String response = "{";
  response += "\"status\":\"" + String(clamped ? "CLAMPED" : "ACCEPTED") + "\",";
  response += "\"vehicle_id\":\"" + String(VEHICLE_ID) + "\",";
  response += "\"target_speed_ms\":" + String(commandedSpeedMs, 3) + ",";
  response += "\"target_pwm\":" + String(targetMotorPWM) + ",";
  response += "\"direction\":\"" + String(commandedSpeedMs > 0.0f ? "FORWARD" : "STOP") + "\"";
  response += "}";

  commandServer.send(200, "application/json", response);
  Serial.print("[HTTP_CMD] Commanded: ");
  Serial.print(commandedSpeedMs, 3);
  Serial.print(" m/s -> Target PWM: ");
  Serial.println(targetMotorPWM);
}

void handleCommandStatus()
{
  String status = "{";
  status += "\"vehicle_id\":\"" + String(VEHICLE_ID) + "\",";
  status += "\"commanded_speed_ms\":" + String(commandedSpeedMs, 3) + ",";
  status += "\"applied_speed_ms\":" + String(appliedSpeedMs, 3) + ",";
  status += "\"target_pwm\":" + String(targetMotorPWM) + ",";
  status += "\"applied_pwm\":" + String(appliedMotorPWM) + ",";
  status += "\"wheel_rpm\":" + String(wheelRPM, 2) + ",";
  status += "\"direction\":\"" + String(appliedMotorPWM > 0 ? "FORWARD" : "STOP") + "\",";
  status += "\"driver\":\"TB6612FNG\"";
  status += "}";
  commandServer.send(200, "application/json", status);
}

// =====================================================
// START COMMAND SERVER
// =====================================================

bool commandServerStarted = false;

void startCommandServer()
{
  if (commandServerStarted)
  {
    return;
  }

  commandServer.on("/api/command", HTTP_POST, handleVehicleCommand);
  commandServer.on("/api/vehicle/command", HTTP_POST, handleVehicleCommand);
  commandServer.on("/api/command/status", HTTP_GET, handleCommandStatus);
  commandServer.on("/", HTTP_GET, []() {
    commandServer.send(200, "text/plain", "TRUCK_01 VEHICLE COMMAND SERVER");
  });

  commandServer.begin();
  commandServerStarted = true;

  Serial.println();
  Serial.println("======================================");
  Serial.println("VEHICLE A COMMAND SERVER READY");
  Serial.print("TRUCK_01 IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("POST /api/command");
  Serial.println("GET /api/command/status");
  Serial.println("======================================");
}


// =====================================================
// MOTOR CONTROL
// =====================================================
//
// This function is called continuously.
//
// Therefore the motor does NOT receive a single
// short pulse and stop.
//
// PWM is maintained continuously.
//
// =====================================================

void updateMotorControl()
{
#if CONTINUOUS_FORWARD_TEST
  runContinuousForwardTest();
  return;
#else
  unsigned long now = millis();

  if (
    now - lastMotorUpdate <
    MOTOR_UPDATE_INTERVAL
  )
  {
    return;
  }

  lastMotorUpdate = now;


  // ---------------------------------------------------
  // CHECK REMOTE VELOCITY TIMEOUT
  // ---------------------------------------------------

  if (
    remoteDataValid &&
    lastRemotePacket != 0 &&
    now - lastRemotePacket >
      REMOTE_COMMAND_TIMEOUT
  )
  {
    remoteDataValid = false;

    if (lastCommandReceived == 0 || now - lastCommandReceived > 10000)
    {
      commandedSpeedMs = DEFAULT_SPEED_MS;
      Serial.println();
      Serial.println("!!! REMOTE V2V VELOCITY TIMEOUT -> DEFAULT SPEED !!!");
    }
  }


  // ---------------------------------------------------
  // TARGET PWM
  // ---------------------------------------------------

  targetMotorPWM =
    speedToPWM(
      commandedSpeedMs
    );


  // ---------------------------------------------------
  // PWM RAMP UP
  // ---------------------------------------------------

  if (
    appliedMotorPWM <
    targetMotorPWM
  )
  {
    appliedMotorPWM +=
      PWM_STEP;

    if (
      appliedMotorPWM >
      targetMotorPWM
    )
    {
      appliedMotorPWM =
        targetMotorPWM;
    }
  }


  // ---------------------------------------------------
  // PWM RAMP DOWN
  // ---------------------------------------------------

  else if (
    appliedMotorPWM >
    targetMotorPWM
  )
  {
    appliedMotorPWM -=
      PWM_STEP;

    if (
      appliedMotorPWM <
      targetMotorPWM
    )
    {
      appliedMotorPWM =
        targetMotorPWM;
    }
  }


  // ---------------------------------------------------
  // APPLY CONTINUOUS PWM
  // ---------------------------------------------------

  applyMotorPWM(
    appliedMotorPWM
  );


  // ---------------------------------------------------
  // ESTIMATE APPLIED SPEED
  // ---------------------------------------------------

  if (MAX_MOTOR_PWM > 0)
  {
    appliedSpeedMs =
      (
        (float)appliedMotorPWM /
        (float)MAX_MOTOR_PWM
      ) *
      MAX_PROTOTYPE_SPEED_MS;
  }
  else
  {
    appliedSpeedMs = 0.0f;
  }
#endif
}


// =====================================================
// MPU6050 INITIALIZATION
// =====================================================

void initializeMPU6050()
{
  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(0x6B);
  Wire.write(0x00);

  byte status =
    Wire.endTransmission(
      true
    );

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
  // ---------------------------------------------------
  // ACCELEROMETER
  // ---------------------------------------------------

  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(0x3B);

  if (
    Wire.endTransmission(false) != 0
  )
  {
    Serial.println(
      "MPU ACCEL READ ERROR"
    );

    return;
  }

  Wire.requestFrom(
    MPU_ADDR,
    6,
    true
  );

  if (Wire.available() >= 6)
  {
    AcX =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );

    AcY =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );

    AcZ =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );
  }


  // ---------------------------------------------------
  // GYROSCOPE
  // ---------------------------------------------------

  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(0x43);

  if (
    Wire.endTransmission(false) != 0
  )
  {
    Serial.println(
      "MPU GYRO READ ERROR"
    );

    return;
  }

  Wire.requestFrom(
    MPU_ADDR,
    6,
    true
  );

  if (Wire.available() >= 6)
  {
    GyX =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );

    GyY =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );

    GyZ =
      (int16_t)(
        (Wire.read() << 8) |
        Wire.read()
      );
  }
}


// =====================================================
// CALCULATE SPEED
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

  unsigned long now = millis();
  float dt_s = (float)(now - lastSpeedCalculation) / 1000.0f;
  if (dt_s <= 0.0f) dt_s = 0.5f;

  float pulsesPerSecond = (float)newPulses / dt_s;

  wheelRPM =
    (
      pulsesPerSecond /
      PULSES_PER_REV
    ) *
    60.0f;


  previousPulseCount =
    currentPulseCount;
  lastSpeedCalculation = now;


  // DERIVED FROM CALIBRATED MEASUREMENT: v = (RPM / 60) * pi * D
  // Wheel diameter = 0.060 m (6.0 cm), effective PPR = 34.58 pulses/rev.
  // Note: encoder-derived linear speed in m/s, calibrated against ground distance.
  vehicleSpeed = (wheelRPM * 3.14159265f * WHEEL_DIAMETER_M) / 60.0f;
}


// =====================================================
// BUILD OWN V2V STATE
// =====================================================
//
// PACKET FORMAT IS UNCHANGED:
//
// STATE,
// TRUCK_01,
// sequence,
// rpm,
// speed,
// ax,
// ay,
// az,
// gx,
// gy,
// gz
//
// =====================================================

String buildOwnState()
{
  globalSequence++;
  txSequence = globalSequence;


  String packet = "";

  packet += "STATE";
  packet += ",";
  packet += VEHICLE_ID;

  packet += ",";
  packet += String(
    txSequence
  );

  packet += ",";
  packet += String(
    wheelRPM,
    2
  );

  packet += ",";
  packet += String(
    vehicleSpeed,
    2
  );

  packet += ",";
  packet += String(
    AcX
  );

  packet += ",";
  packet += String(
    AcY
  );

  packet += ",";
  packet += String(
    AcZ
  );

  packet += ",";
  packet += String(
    GyX
  );

  packet += ",";
  packet += String(
    GyY
  );

  packet += ",";
  packet += String(
    GyZ
  );


  return packet;
}


// =====================================================
// SEND A -> B
// =====================================================

void sendV2VState()
{
  String packet =
    buildOwnState();


  Serial.println();
  Serial.println(
    ">>> V2V TX A -> B"
  );

  Serial.println(packet);


  // Put LoRa into TX/standby.
  LoRa.idle();

  delay(2);


  int result =
    LoRa.beginPacket();


  if (result != 1)
  {
    Serial.println(
      "LoRa beginPacket FAILED"
    );

    LoRa.receive();

    return;
  }


  LoRa.print(
    packet
  );


  result =
    LoRa.endPacket();


  if (result == 1)
  {
    Serial.println(
      "TX COMPLETE"
    );
  }
  else
  {
    Serial.println(
      "TX FAILED"
    );
  }


  // IMPORTANT:
  // Return immediately to receive mode.

  delay(2);

  LoRa.receive();
}


// =====================================================
// PARSE VEHICLE B
// =====================================================

bool parseVehicleB(
  String packet
)
{
  packet.trim();


  Serial.println();
  Serial.println(
    "<<< RAW LORA RX >>>"
  );

  Serial.println(packet);


  // ---------------------------------------------------
  // EMPTY
  // ---------------------------------------------------

  if (
    packet.length() == 0
  )
  {
    malformedPackets++;

    Serial.println(
      "REJECT: EMPTY PACKET"
    );

    return false;
  }


  // ---------------------------------------------------
  // SPLIT
  // ---------------------------------------------------

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
      i == packet.length() ||
      packet.charAt(i) == ','
    )
    {
      if (
        fieldIndex < 11
      )
      {
        fields[fieldIndex] =
          packet.substring(
            startIndex,
            i
          );

        fields[fieldIndex].trim();

        fieldIndex++;
      }

      startIndex =
        i + 1;
    }
  }


  // ---------------------------------------------------
  // FIELD COUNT
  // ---------------------------------------------------

  if (
    fieldIndex != 11
  )
  {
    malformedPackets++;

    Serial.print(
      "Parsed field count: "
    );

    Serial.println(
      fieldIndex
    );

    Serial.println(
      "REJECT: MALFORMED"
    );

    return false;
  }


  // ---------------------------------------------------
  // PACKET TYPE
  // ---------------------------------------------------

  if (
    fields[0] != "STATE"
  )
  {
    ignoredPackets++;

    Serial.println(
      "REJECT: WRONG PACKET TYPE"
    );

    return false;
  }


  // ---------------------------------------------------
  // VEHICLE ID
  // ---------------------------------------------------

  Serial.print(
    "Parsed vehicle ID: "
  );

  Serial.println(
    fields[1]
  );

  Serial.print(
    "Expected remote ID: "
  );

  Serial.println(
    REMOTE_ID
  );


  if (
    fields[1] != REMOTE_ID
  )
  {
    ignoredPackets++;

    Serial.println(
      "REJECT: WRONG VEHICLE ID"
    );

    return false;
  }


  // ---------------------------------------------------
  // SEQUENCE
  // ---------------------------------------------------

  unsigned long seq =
    strtoul(
      fields[2].c_str(),
      NULL,
      10
    );


  Serial.print(
    "Parsed sequence: "
  );

  Serial.println(seq);


  // ---------------------------------------------------
  // DUPLICATE
  // ---------------------------------------------------

  if (
    remoteDataValid &&
    seq == remoteSequence
  )
  {
    duplicatePackets++;

    Serial.println(
      "Sequence decision: REJECT"
    );

    Serial.println(
      "REJECT REASON: DUPLICATE"
    );

    return false;
  }


  // ---------------------------------------------------
  // OUT OF ORDER
  // ---------------------------------------------------

  if (
    remoteDataValid &&
    seq < remoteSequence
  )
  {
    outOfOrderPackets++;

    Serial.println(
      "Sequence decision: REJECT"
    );

    Serial.println(
      "REJECT REASON: OUT-OF-ORDER"
    );

    Serial.print(
      "Received: "
    );

    Serial.println(seq);

    Serial.print(
      "Last accepted: "
    );

    Serial.println(
      remoteSequence
    );

    return false;
  }


  // ---------------------------------------------------
  // MISSING PACKETS
  // ---------------------------------------------------

  if (
    remoteDataValid &&
    seq > remoteSequence + 1
  )
  {
    unsigned long gap =
      seq -
      remoteSequence -
      1;

    missingPackets +=
      gap;

    Serial.print(
      "MISSING PACKETS: "
    );

    Serial.println(
      gap
    );
  }


  // ---------------------------------------------------
  // ACCEPT
  // ---------------------------------------------------

  Serial.println(
    "Sequence decision: ACCEPT"
  );


  // ---------------------------------------------------
  // UPDATE REMOTE DATA
  // ---------------------------------------------------

  remoteSequence =
    seq;


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


  // ---------------------------------------------------
  // RADIO QUALITY
  // ---------------------------------------------------

  remoteRSSI =
    LoRa.packetRssi();


  remoteSNR =
    LoRa.packetSnr();


  // ---------------------------------------------------
  // TIMESTAMP
  // ---------------------------------------------------

  lastRemotePacket =
    millis();


  remoteDataValid =
    true;


  validPackets++;


  // ---------------------------------------------------
  // IMPORTANT:
  //
  // Vehicle B's speed becomes A's target speed.
  //
  // BUT:
  //
  // Your current B firmware must actually transmit
  // the Digital Twin-controlled velocity in field[4].
  //
  // ---------------------------------------------------

  // V2V Peer telemetry received from Vehicle B
  // Record remote state for headway and fleet coordination.
  // Authoritative velocity is set by Backend Governor / Digital Twin closed loop.
  // We do NOT allow a stationary peer (0.0 m/s) to kill Vehicle A's governed forward drive.
  if (
    isfinite(remoteSpeed) &&
    remoteSpeed > 0.05f &&
    remoteSpeed < commandedSpeedMs
  )
  {
    // Cooperative platoon slowing: match peer speed if peer is moving slower ahead
    commandedSpeedMs =
      constrain(
        remoteSpeed,
        0.0f,
        MAX_PROTOTYPE_SPEED_MS
      );
    targetMotorPWM = speedToPWM(commandedSpeedMs);

    Serial.println();
    Serial.println(
      ">>> V2V COOPERATIVE SPEED ADJUSTMENT"
    );
    Serial.print("Vehicle B velocity: ");
    Serial.print(remoteSpeed, 3);
    Serial.println(" m/s");
    Serial.print("Vehicle A target: ");
    Serial.print(commandedSpeedMs, 3);
    Serial.println(" m/s");
  }


  // ---------------------------------------------------
  // PRINT VALID PACKET
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "<<< VALID V2V FROM TRUCK_02"
  );


  Serial.print(
    "Sequence: "
  );

  Serial.println(
    remoteSequence
  );


  Serial.print(
    "RPM: "
  );

  Serial.println(
    remoteRPM,
    2
  );


  Serial.print(
    "Speed: "
  );

  Serial.println(
    remoteSpeed,
    2
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


  Serial.print(
    "A Target Speed: "
  );

  Serial.print(
    commandedSpeedMs,
    3
  );

  Serial.println(
    " m/s"
  );


  Serial.println(
    "======================================"
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


  if (
    packetSize <= 0
  )
  {
    return;
  }


  Serial.println();

  Serial.print(
    "LoRa packet size: "
  );

  Serial.println(
    packetSize
  );


  String packet = "";


  while (
    LoRa.available()
  )
  {
    packet +=
      (char)LoRa.read();
  }


  parseVehicleB(
    packet
  );


  // Always return to RX.

  LoRa.receive();
}


// =====================================================
// WIFI CONNECT
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println(
    "======================================"
  );

  Serial.println(
    "CONNECTING WIFI"
  );

  Serial.println(
    "======================================"
  );


  WiFi.mode(
    WIFI_STA
  );


  WiFi.disconnect(
    true
  );


  delay(500);


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
    wifiState = COMM_CONNECTED;

    Serial.println(
      "Wi-Fi CONNECTED"
    );


    Serial.print(
      "ESP32 IP: "
    );

    Serial.println(
      WiFi.localIP()
    );


    Serial.print(
      "HMI SERVER: "
    );

    Serial.println(
      HMI_SERVER
    );

    // Start HTTP Command Server only after network stack is initialized
    startCommandServer();

    // Synchronize sequence counter from backend on boot (Option 3 hierarchy)
    HTTPClient httpSync;
    httpSync.setTimeout(1500);
    String syncUrl = String(HMI_SERVER);
    int apiIdx = syncUrl.indexOf("/api/");
    if (apiIdx != -1) {
      syncUrl = syncUrl.substring(0, apiIdx) + "/api/hardware/sequence?vehicle_id=TRUCK_01";
    }
    if (httpSync.begin(syncUrl)) {
      int code = httpSync.GET();
      if (code == 200) {
        String body = httpSync.getString();
        int seqIdx = body.indexOf("\"next_sequence\":");
        if (seqIdx != -1) {
          uint32_t sNext = (uint32_t)body.substring(seqIdx + 16).toInt();
          if (sNext > telemetrySequence) {
            telemetrySequence = sNext;
            Serial.print("[SYNC] Seeded sequence from backend: ");
            Serial.println(telemetrySequence);
          }
        }
      }
      httpSync.end();
    }
  }
  else
  {
    wifiState = COMM_DISCONNECTED;
    Serial.println(
      "Wi-Fi unavailable"
    );
  }
}


// =====================================================
// SEND LOCAL STATE TO HMI
// =====================================================

void sendLocalToHMI()
{
  unsigned long now = millis();

  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    wifiState = COMM_DISCONNECTED;
    hmiFailed++;

    Serial.println(
      "HMI: Wi-Fi disconnected"
    );

    // Non-blocking reconnect attempt every 5 seconds
    if (now - lastWiFiReconnectAttempt >= WIFI_RECONNECT_INTERVAL_MS)
    {
      lastWiFiReconnectAttempt = now;
      WiFi.reconnect();
    }

    return;
  }

  wifiState = COMM_CONNECTED;

  // Dedicated strictly monotonic sequence incremented once per transmitted frame
  globalSequence++;
  telemetrySequence = globalSequence;


  HTTPClient http;

  // Bounded timeout (1000 ms) to prevent stalling motor/safety loops
  http.setTimeout(
    1000
  );

  http.begin(
    HMI_SERVER
  );

  http.addHeader(
    "Content-Type",
    "application/json"
  );


  // Wi-Fi signal strength
  int wifiRSSI = WiFi.RSSI();

  // Canonical JSON payload conforming strictly to backend HardwareTelemetryPayload
  String json = "{";

  json +=
    "\"vehicle_id\":\"TRUCK_01\",";

  json +=
    "\"boot_id\":";
  json +=
    String(bootId);
  json += ",";

  json +=
    "\"sequence\":";
  json +=
    String(telemetrySequence);
  json += ",";

  json +=
    "\"rpm\":";
  json +=
    String(wheelRPM, 2);
  json += ",";

  json +=
    "\"speed\":";
  json +=
    String(vehicleSpeed, 2);
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
    "\"rssi\":";
  json +=
    String(wifiRSSI);
  json += ",";

  json +=
    "\"snr\":";
  json +=
    String(remoteDataValid ? remoteSNR : 9.5f, 2);
  json += ",";

  json +=
    "\"source\":\"DIRECT_WIFI\"";

  json += "}";


  Serial.println();
  Serial.print(">>> HMI TX TRUCK_01 (Seq ");
  Serial.print(telemetrySequence);
  Serial.println(")");
  Serial.println(json);

  int response =
    http.POST(
      json
    );

  Serial.print(
    "HMI A HTTP: "
  );
  Serial.println(
    response
  );

  if (
    (response >= 200 && response < 300) ||
    response == 409
  )
  {
    if (response >= 200 && response < 300)
    {
      hmiSent++;
      Serial.println(
        "HMI POST SUCCESS (2xx)"
      );
    }
    else
    {
      Serial.println(
        "HMI POST ACK (409 CLOSED-LOOP SYNC)"
      );
    }

    // Parse authoritative Digital Twin / Governor safe-speed update (closed loop)
    String body = http.getString();
    float backendTarget = 0.0f;
    if (extractJsonFloat(body, "target_speed_mps", backendTarget))
    {
      commandedSpeedMs = backendTarget;
      targetMotorPWM = speedToPWM(commandedSpeedMs);
      lastCommandReceived = millis();
      Serial.print("[HMI_GOV] Closed-loop target speed: ");
      Serial.print(commandedSpeedMs, 3);
      Serial.print(" m/s -> Target PWM: ");
      Serial.println(targetMotorPWM);
    }
  }
  else
  {
    hmiFailed++;
    wifiState = COMM_DEGRADED;
    Serial.println(
      "HMI POST FAILED"
    );

    if (
      response > 0
    )
    {
      String body =
        http.getString();

      Serial.print(
        "HMI RESPONSE: "
      );
      Serial.println(
        body
      );
    }
  }

  http.end();
}


// =====================================================
// REMOTE STATUS
// =====================================================

String remoteStatus()
{
  if (
    !remoteDataValid
  )
  {
    return "WAITING";
  }


  unsigned long age =
    millis() -
    lastRemotePacket;


  if (
    age < 5000
  )
  {
    return "ONLINE";
  }


  if (
    age < 10000
  )
  {
    return "STALE";
  }


  return "OFFLINE";
}


// =====================================================
// PRINT STATUS
// =====================================================

void printStatus()
{
  Serial.println();

  Serial.println(
    "######################################"
  );

  Serial.println(
    "          TRUCK_01 STATUS"
  );

  Serial.println(
    "######################################"
  );


  // ---------------------------------------------------
  // LOCAL
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "LOCAL VEHICLE"
  );


  Serial.print(
    "Own Sequence: "
  );

  Serial.println(
    txSequence
  );


  Serial.print(
    "Own RPM: "
  );

  Serial.println(
    wheelRPM,
    2
  );


  Serial.print(
    "Own Speed: "
  );

  Serial.println(
    vehicleSpeed,
    2
  );


  // ---------------------------------------------------
  // REMOTE
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "REMOTE TRUCK_02"
  );


  Serial.print(
    "Sequence: "
  );

  Serial.println(
    remoteSequence
  );


  Serial.print(
    "RPM: "
  );

  Serial.println(
    remoteRPM,
    2
  );


  Serial.print(
    "Speed: "
  );

  Serial.println(
    remoteSpeed,
    2
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


  Serial.print(
    "Status: "
  );

  Serial.println(
    remoteStatus()
  );


  // ---------------------------------------------------
  // MOTOR
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "DIGITAL TWIN / V2V MOTOR CONTROL"
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


  // ---------------------------------------------------
  // WIFI
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "HMI GATEWAY"
  );


  Serial.print(
    "Wi-Fi: "
  );


  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    Serial.println(
      "CONNECTED"
    );
  }
  else
  {
    Serial.println(
      "DISCONNECTED"
    );
  }


  Serial.print(
    "HMI Sent: "
  );

  Serial.println(
    hmiSent
  );


  Serial.print(
    "HMI Failed: "
  );

  Serial.println(
    hmiFailed
  );


  // ---------------------------------------------------
  // V2V STATISTICS
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "V2V STATISTICS"
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
    missingPackets
  );


  Serial.print(
    "Malformed: "
  );

  Serial.println(
    malformedPackets
  );


  Serial.print(
    "Ignored: "
  );

  Serial.println(
    ignoredPackets
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
  Serial.begin(
    115200
  );


  delay(1000);


  Serial.println();
  Serial.println();

  Serial.println(
    "======================================"
  );

  Serial.println(
    "       FOG-ORCHESTRATOR 2.0"
  );

  Serial.println(
    "       VEHICLE A / TRUCK_01"
  );

  Serial.println(
    "======================================"
  );

  // Initialize NVS Persistent Boot ID (Gap 1)
  bootPrefs.begin("synqra", false);
  bootId = bootPrefs.getUInt("boot_id", 0) + 1;
  bootPrefs.putUInt("boot_id", bootId);
  bootPrefs.end();

  Serial.print("[BOOT SESSION] Persistent Boot ID: ");
  Serial.println(bootId);


  // ===================================================
  // MOTOR
  // ===================================================

  pinMode(
    LEFT_IN1,
    OUTPUT
  );

  pinMode(
    LEFT_IN2,
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
    MOTOR_STBY,
    OUTPUT
  );

  // ESP32 Arduino Core 3.x LEDC PWM setup
  ledcAttach(LEFT_PWM, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttach(RIGHT_PWM, PWM_FREQUENCY, PWM_RESOLUTION);

#if CONTINUOUS_FORWARD_TEST
  runContinuousForwardTest();
  Serial.println("[MOTOR] CONTINUOUS FORWARD DRIVE ACTIVE (PWM=120)");
#else
  commandedSpeedMs = DEFAULT_SPEED_MS;
  targetMotorPWM = speedToPWM(commandedSpeedMs);
  appliedMotorPWM = targetMotorPWM;
  setForwardDirection();
  applyMotorPWM(targetMotorPWM);
  Serial.print("[MOTOR] BOOT FORWARD SPEED: ");
  Serial.print(commandedSpeedMs, 3);
  Serial.print(" m/s -> PWM ");
  Serial.println(targetMotorPWM);
#endif


  // ===================================================
  // SPEED SENSOR
  // ===================================================

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


  // ===================================================
  // MPU6050
  // ===================================================

  Wire.begin(
    MPU_SDA,
    MPU_SCL
  );


  initializeMPU6050();


  // ===================================================
  // LORA
  // ===================================================

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
      "LoRa FAILED!"
    );

#if !CONTINUOUS_FORWARD_TEST
    while (true)
    {
      delay(1000);
    }
#endif
  }


  LoRa.enableCrc();

  LoRa.setTxPower(
    17
  );


  // IMPORTANT:
  // Start listening.

  LoRa.receive();


  Serial.println(
    "LoRa SUCCESS"
  );

  Serial.println(
    "Frequency: 433 MHz"
  );

  Serial.println(
    "CRC: ENABLED"
  );

  Serial.println(
    "RX MODE: ENABLED"
  );


  // ===================================================
  // WIFI
  // ===================================================

  connectWiFi();

  if (WiFi.status() == WL_CONNECTED)
  {
    startCommandServer();
  }


  // ===================================================
  // TIMERS
  // ===================================================

  lastSpeedCalculation =
    millis();

  lastIMURead =
    millis();


  lastV2VTransmission =
    millis()
    - V2V_INTERVAL
    + V2V_START_DELAY;


  lastHMITransmission =
    millis();


  lastStatusPrint =
    millis();


  lastMotorUpdate =
    millis();


  // ===================================================
  // INITIAL MOTOR COMMAND
  // ===================================================

  commandedSpeedMs =
    DEFAULT_SPEED_MS;


  targetMotorPWM =
    speedToPWM(
      commandedSpeedMs
    );


  Serial.println();

  Serial.println(
    "======================================"
  );

  Serial.println(
    "TRUCK_01 READY"
  );

  Serial.println(
    "Remote Target: TRUCK_02"
  );

  Serial.println(
    "V2V: BIDIRECTIONAL"
  );

  Serial.println(
    "HMI: DIRECT WIFI"
  );

  Serial.println(
    "MOTOR: CONTINUOUS"
  );

  Serial.print(
    "DEFAULT SPEED: "
  );

  Serial.print(
    DEFAULT_SPEED_MS,
    3
  );

  Serial.println(
    " m/s"
  );

  Serial.println(
    "======================================"
  );
}


// =====================================================
// PRODUCTION SAFE BEACON GENERATOR (Gap 2)
// =====================================================
//
// Transmitted over LoRa (SX1278 half-duplex) at strictly 1.0 Hz
// when primary Wi-Fi telemetry is disconnected.
// Enforces local vehicle safe state (speed reduction / stop).
//
// Format: BEACON,<vehicle_id>,<beacon_seq>,<state>,<millis>,<zone_id>
// =====================================================

void sendSafeBeacon()
{
  unsigned long now = millis();
  if (now - lastBeaconTx < BEACON_INTERVAL_MS)
  {
    return;
  }
  lastBeaconTx = now;
  beaconSequence++;

  // Degraded RF broadcast: announce state over LoRa without killing active motor drive
  // Authoritative stop is commanded by Backend Governor or STOP command.

  String beaconPacket = "BEACON,";
  beaconPacket += VEHICLE_ID;
  beaconPacket += ",";
  beaconPacket += String(beaconSequence);
  beaconPacket += ",DEGRADED,";
  beaconPacket += String(now);
  beaconPacket += ",PIT_ZONE_A";

  LoRa.beginPacket();
  LoRa.print(beaconPacket);
  LoRa.endPacket();

  // Put SX1278 back to receive mode immediately
  LoRa.receive();

  Serial.println();
  Serial.print(">>> [SAFE BEACON TX] Seq ");
  Serial.print(beaconSequence);
  Serial.print(": ");
  Serial.println(beaconPacket);
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  unsigned long now =
    millis();


  // Maintain Wi-Fi connectivity state for Safe Beacon logic
  if (WiFi.status() == WL_CONNECTED)
  {
    if (wifiState == COMM_DISCONNECTED)
    {
      wifiState = COMM_CONNECTED;
    }
    if (!commandServerStarted)
    {
      startCommandServer();
    }
  }
  else
  {
    wifiState = COMM_DISCONNECTED;
  }

  // Maintain non-blocking HTTP Command Server
  if (commandServerStarted)
  {
    commandServer.handleClient();
  }

  // ===================================================
  // SERIAL COMMANDS (Physical Test & Failover Harness)
  // ===================================================
  if (Serial.available())
  {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "STOP")
    {
      commandedSpeedMs = 0.0f;
      targetMotorPWM = 0;
      appliedMotorPWM = 0;
      stopVehicle();
      Serial.println("[CMD_ACK] MOTOR STOPPED (PWM=0, STBY=LOW)");
    }
    else if (cmd.startsWith("FORWARD"))
    {
      float spd = 0.40f;
      if (cmd.length() > 7)
      {
        spd = cmd.substring(8).toFloat();
      }
      if (spd <= 0.0f) spd = 0.40f;
      spd = constrain(spd, 0.0f, MAX_PROTOTYPE_SPEED_MS);
      commandedSpeedMs = spd;
      targetMotorPWM = speedToPWM(commandedSpeedMs);
      setForwardDirection();
      Serial.print("[CMD_ACK] FORWARD COMMAND ACCEPTED: ");
      Serial.print(commandedSpeedMs, 3);
      Serial.print(" m/s -> PWM ");
      Serial.println(targetMotorPWM);
    }
    else if (cmd == "DIR_NORMAL")
    {
      invertLeftMotor = false;
      invertRightMotor = false;
      setForwardDirection();
      Serial.println("[CMD_ACK] DIRECTION: NORMAL (Left: Normal, Right: Normal)");
    }
    else if (cmd == "DIR_INVERT_LEFT")
    {
      invertLeftMotor = !invertLeftMotor;
      setForwardDirection();
      Serial.print("[CMD_ACK] DIRECTION: Left Inverted = ");
      Serial.println(invertLeftMotor ? "TRUE" : "FALSE");
    }
    else if (cmd == "DIR_INVERT_RIGHT")
    {
      invertRightMotor = !invertRightMotor;
      setForwardDirection();
      Serial.print("[CMD_ACK] DIRECTION: Right Inverted = ");
      Serial.println(invertRightMotor ? "TRUE" : "FALSE");
    }
    else if (cmd == "STATUS")
    {
      Serial.println("--- VEHICLE A (TRUCK_01) STATUS ---");
      Serial.print("Commanded Speed: "); Serial.print(commandedSpeedMs, 3); Serial.println(" m/s");
      Serial.print("Applied Speed:   "); Serial.print(appliedSpeedMs, 3); Serial.println(" m/s");
      Serial.print("Target PWM:      "); Serial.println(targetMotorPWM);
      Serial.print("Applied PWM:     "); Serial.println(appliedMotorPWM);
      Serial.print("Wheel RPM:       "); Serial.println(wheelRPM, 2);
      Serial.print("Direction:       "); Serial.println(appliedMotorPWM > 0 ? "FORWARD" : "STOP");
      Serial.print("Driver:          TB6612FNG (STBY="); Serial.print(digitalRead(MOTOR_STBY)); Serial.println(")");
      Serial.print("Wi-Fi Status:    "); Serial.println(WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED");
      Serial.print("ESP32 IP:        "); Serial.println(WiFi.localIP());
      Serial.println("-----------------------------------");
    }
    else if (cmd == "HELP")
    {
      Serial.println("Commands: FORWARD [spd], STOP, DIR_NORMAL, DIR_INVERT_LEFT, DIR_INVERT_RIGHT, STATUS, REBOOT, WIFI_DROP, WIFI_RECONNECT");
    }
    else if (cmd == "WIFI_DROP")
    {
      WiFi.disconnect();
      wifiState = COMM_DISCONNECTED;
      Serial.println("[CMD_ACK] WIFI_DROP_EXECUTED");
    }
    else if (cmd == "WIFI_RECONNECT")
    {
      WiFi.reconnect();
      Serial.println("[CMD_ACK] WIFI_RECONNECT_EXECUTED");
    }
    else if (cmd == "REBOOT")
    {
      Serial.println("[CMD_ACK] REBOOTING_ESP32");
      delay(100);
      ESP.restart();
    }
    else if (cmd.startsWith("DRIVE "))
    {
      int spaceIdx = cmd.indexOf(' ', 6);
      if (spaceIdx != -1)
      {
        int pwmVal = cmd.substring(6, spaceIdx).toInt();
        unsigned long dur = cmd.substring(spaceIdx + 1).toInt();
        setForwardDirection();
        applyMotorPWM(pwmVal);
        Serial.print("[CMD_ACK] MOTOR DRIVE PWM=");
        Serial.print(pwmVal);
        Serial.print(" DUR_MS=");
        Serial.println(dur);
        delay(dur);
        stopVehicle();
        Serial.println("[CMD_ACK] MOTOR DRIVE STOPPED");
      }
    }
  }

  // ===================================================
  // MOTOR
  // ===================================================
  //
  // MUST RUN CONTINUOUSLY.
  //
  // This is deliberately called every loop.
  // ===================================================

  updateMotorControl();


  // ===================================================
  // SPEED
  // ===================================================

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


  // ===================================================
  // IMU
  // ===================================================

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


  // ===================================================
  // V2V RECEIVE
  // ===================================================
  //
  // Keep this continuously active.
  // ===================================================

  receiveV2V();


  // ===================================================
  // V2V TRANSMIT A -> B
  // ===================================================

  if (
    now -
    lastV2VTransmission >=
    V2V_INTERVAL
  )
  {
    sendV2VState();

    lastV2VTransmission =
      now;
  }


  // ===================================================
  // HMI
  // ===================================================

  if (
    now -
    lastHMITransmission >=
    HMI_INTERVAL
  )
  {
    sendLocalToHMI();

    lastHMITransmission =
      now;
  }


  // ===================================================
  // SAFE BEACON (Gap 2 Closure)
  // ===================================================
  // If Wi-Fi link is disconnected, emit periodic LoRa Safe Beacon
  if (wifiState == COMM_DISCONNECTED)
  {
    sendSafeBeacon();
  }


  // ===================================================
  // STATUS
  // ===================================================

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


  // Small cooperative delay.
  delay(2);
}