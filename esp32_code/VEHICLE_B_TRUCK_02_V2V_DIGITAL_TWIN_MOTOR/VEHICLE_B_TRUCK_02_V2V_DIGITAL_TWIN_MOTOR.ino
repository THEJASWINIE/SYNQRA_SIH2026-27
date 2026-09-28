#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>

// NVS Persistent Boot & Session ID (Parity Contract)
Preferences bootPrefs;
uint32_t bootId = 1;

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
// MOTOR PINS - TB6612FNG MOTOR DRIVER
// =====================================================

#define LEFT_IN1    25
#define LEFT_IN2    26
#define LEFT_PWM    27

#define RIGHT_IN1   32
#define RIGHT_IN2   33
#define RIGHT_PWM   14

#define MOTOR_STBY  13


// =====================================================
// TEMPORARY CONTINUOUS FORWARD MOTOR TEST MODE
// =====================================================

#define CONTINUOUS_FORWARD_TEST false

const int CONTINUOUS_TEST_PWM = 120;


// =====================================================
// SPEED SENSOR & WHEEL PARAMETERS
// =====================================================

#define SPEED_SENSOR_PIN      35
#define RAW_ENCODER_PPR       43.0f
#define ENCODER_EFFECTIVE_PPR 34.58f
#define PULSES_PER_REV        ENCODER_EFFECTIVE_PPR

const float WHEEL_DIAMETER_M = 0.060f;

const float WHEEL_CIRCUMFERENCE_M =
    PI * WHEEL_DIAMETER_M;


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
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

const char* WIFI_SSID = SECRET_WIFI_SSID;
const char* WIFI_PASSWORD = SECRET_WIFI_PASSWORD;

const char* HMI_SERVER = SECRET_HMI_TELEMETRY_URL;


// =====================================================
// DIGITAL TWIN SERVER
// =====================================================

WebServer commandServer(80);


// =====================================================
// VEHICLE SPEED LIMITS
// =====================================================

const float MAX_PROTOTYPE_SPEED_MS = 1.30f;

// Default continuous forward speed (used on power-on and command fallback)
const float DEFAULT_SPEED_MS = 0.40f;

const int MAX_MOTOR_PWM = 220;

const int MIN_MOTOR_PWM = 0;

// Minimum effective starting PWM to overcome static chassis friction.
const int MIN_EFFECTIVE_PWM = 100;

// ESP32 Arduino Core 3.x LEDC PWM parameters
const int PWM_FREQUENCY = 1000;
const int PWM_RESOLUTION = 8;

// Direction polarity inversion flags for bench/chassis alignment.
bool invertLeftMotor = false;
bool invertRightMotor = false;


// =====================================================
// MOTOR RAMP
// =====================================================

const unsigned long MOTOR_UPDATE_INTERVAL = 50;

const int PWM_STEP = 3;

unsigned long lastMotorUpdate = 0;


// =====================================================
// VEHICLE COMMAND & CONTROL STATE (SAFE STARTUP: 0 m/s)
// =====================================================

float commandedSpeedMs = 0.0f;

float appliedSpeedMs = 0.0f;

int targetMotorPWM = 0;

int appliedMotorPWM = 0;

String lastCommandId = "NONE";

unsigned long lastCommandReceived = 0;

// Local safety timeout (failsafe: stop vehicle if command link is lost)
const unsigned long COMMAND_TIMEOUT_MS = 15000;


// Direct Wi-Fi Telemetry Toggle:
// Set to true for live telemetry streaming to backend
#define ENABLE_DIRECT_WIFI_TELEMETRY true


// =====================================================
// V2V & SEQUENCE STATE
// =====================================================

// Unified strictly monotonic sequence counter across V2V LoRa and Wi-Fi transmissions
unsigned long globalSequence = 0;

unsigned long txSequence = 0;

// Dedicated strictly monotonic sequence for direct HMI telemetry (unified with globalSequence)
uint32_t telemetrySequence = 0;

// Safe Beacon parameters (Parity Contract)
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
// MOTOR (TB6612FNG & ESP32 CORE 3.x LEDC)
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
// CONTINUOUS FORWARD TEST (ISOLATED HARDWARE VALIDATION)
// =====================================================

void runContinuousForwardTest()
{
  digitalWrite(MOTOR_STBY, HIGH);

  // LEFT MOTOR FORWARD
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);

  // RIGHT MOTOR FORWARD
  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);

  ledcWrite(LEFT_PWM, CONTINUOUS_TEST_PWM);
  ledcWrite(RIGHT_PWM, CONTINUOUS_TEST_PWM);

  appliedMotorPWM = CONTINUOUS_TEST_PWM;
  appliedSpeedMs =
    (
      (float)CONTINUOUS_TEST_PWM /
      (float)MAX_MOTOR_PWM
    )
    *
    MAX_PROTOTYPE_SPEED_MS;
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
    stopVehicle();
    return;
  }

  digitalWrite(MOTOR_STBY, HIGH);

  setForwardDirection();

  ledcWrite(LEFT_PWM, pwm);
  ledcWrite(RIGHT_PWM, pwm);
}


// =====================================================
// SPEED -> PWM
// =====================================================

int speedToPWM(float speedMs)
{
  if (!isfinite(speedMs) || speedMs <= 0.0f)
    return 0;

  speedMs = constrain(
    speedMs,
    0.0f,
    MAX_PROTOTYPE_SPEED_MS
  );

  float ratio = speedMs / MAX_PROTOTYPE_SPEED_MS;
  int pwm = MIN_EFFECTIVE_PWM + (int)round(ratio * (MAX_MOTOR_PWM - MIN_EFFECTIVE_PWM));

  return constrain(pwm, MIN_EFFECTIVE_PWM, MAX_MOTOR_PWM);
}


// =====================================================
// CONTINUOUS MOTOR CONTROL
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


  // -------------------------------------------------
  // COMMAND TIMEOUT
  // -------------------------------------------------

  if (
    lastCommandReceived != 0 &&
    now - lastCommandReceived >
    COMMAND_TIMEOUT_MS
  )
  {
    if (commandedSpeedMs != DEFAULT_SPEED_MS && commandedSpeedMs > 0.0f)
    {
      Serial.println();
      Serial.println(
        "!!! COMMAND TIMEOUT -> FALLBACK TO DEFAULT SPEED !!!"
      );
      commandedSpeedMs = DEFAULT_SPEED_MS;
      targetMotorPWM = speedToPWM(commandedSpeedMs);
    }
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
#endif
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


  float revolutionsPerSecond =
    (float)newPulses /
    PULSES_PER_REV;


  wheelRPM =
    revolutionsPerSecond *
    60.0f;


  measuredVehicleSpeed =
    revolutionsPerSecond *
    WHEEL_CIRCUMFERENCE_M;


  previousPulseCount =
    currentPulseCount;
}


// =====================================================
// BUILD V2V STATE
// =====================================================

String buildOwnState()
{
  globalSequence++;
  txSequence = globalSequence;


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

  Serial.println(
    "[TRUCK_02 TX]"
  );

  Serial.println(packet);


  // Put LoRa into TX/standby before starting a new packet.
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


  // Explicitly return to receive mode.

  delay(2);

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
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    hmiPacketsFailed++;
    wifiState = COMM_DISCONNECTED;

    unsigned long now = millis();
    if (now - lastWiFiReconnectAttempt >= WIFI_RECONNECT_INTERVAL_MS)
    {
      lastWiFiReconnectAttempt = now;
      Serial.println("[WIFI TRUCK_02] Reconnecting to AP...");
      WiFi.reconnect();
    }

    Serial.println(
      "HMI: Wi-Fi disconnected"
    );

    return;
  }

  wifiState = COMM_CONNECTED;

  // Unified strictly monotonic sequence incremented once per frame
  globalSequence++;
  telemetrySequence = globalSequence;


  HTTPClient http;

  // Bounded timeout so HMI communication does not
  // unnecessarily block the control loop.

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


  // Wi-Fi signal strength for the direct telemetry link.

  int wifiRSSI =
    WiFi.RSSI();


  // The existing LoRa V2V link provides the latest
  // measured remote SNR when TRUCK_01 data exists.
  // Otherwise retain the existing project fallback.

  float telemetrySNR =
    (lastRemotePacket != 0)
    ? remoteSNR
    : 9.5f;


  // Canonical HardwareTelemetryPayload fields.

  String json = "{";


  json +=
    "\"vehicle_id\":\"TRUCK_02\",";

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


  // HMI receives the currently applied prototype
  // velocity commanded by the Digital Twin.

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
    "\"rssi\":";

  json +=
    String(wifiRSSI);

  json += ",";


  json +=
    "\"snr\":";

  json +=
    String(telemetrySNR, 2);

  json += ",";


  json +=
    "\"source\":\"DIRECT_WIFI\"";


  json += "}";


  Serial.println();

  Serial.print(
    ">>> HMI TX TRUCK_02 (Seq "
  );

  Serial.print(
    telemetrySequence
  );

  Serial.println(
    ")"
  );

  Serial.println(
    json
  );


  int response =
    http.POST(
      json
    );


  Serial.print(
    "HMI B HTTP: "
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
      hmiPacketsSent++;
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
    hmiPacketsFailed++;

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
    "VEHICLE COMMAND"
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
        "TRUCK_02 VEHICLE COMMAND SERVER"
      );
    }
  );


  commandServer.begin();


  Serial.println();
  Serial.println(
    "VEHICLE COMMAND SERVER READY"
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
    "VEHICLE CONTROL"
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
// PRODUCTION SAFE BEACON (Wi-Fi Loss Parity)
// =====================================================
//
// Transmitted over LoRa (SX1278 half-duplex) at strictly 1.0 Hz
// when primary Wi-Fi telemetry is disconnected.
// Enforces local vehicle safe state (speed reduction / stop).
//
// Format: BEACON,TRUCK_02,<beacon_seq>,<state>,<millis>,<zone_id>
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

  String beaconPacket = "BEACON,TRUCK_02,";
  beaconPacket += String(beaconSequence);
  beaconPacket += ",DEGRADED,";
  beaconPacket += String(now);
  beaconPacket += ",PIT_ZONE_A";

  LoRa.idle();
  delay(2);
  if (LoRa.beginPacket() == 1)
  {
    LoRa.print(beaconPacket);
    LoRa.endPacket();
  }
  delay(2);
  LoRa.receive();

  Serial.println();
  Serial.print(">>> [SAFE BEACON TX TRUCK_02] Seq ");
  Serial.print(beaconSequence);
  Serial.print(": ");
  Serial.println(beaconPacket);
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println();
  Serial.println("======================================");
  Serial.println("       FOG-ORCHESTRATOR 2.0");
  Serial.println("       VEHICLE B / TRUCK_02");
  Serial.println("======================================");

  // Initialize NVS Persistent Boot ID (Parity Contract)
  bootPrefs.begin("synqra", false);
  bootId = bootPrefs.getUInt("boot_id", 0) + 1;
  bootPrefs.putUInt("boot_id", bootId);
  bootPrefs.end();

  Serial.print("[BOOT SESSION] Persistent Boot ID: ");
  Serial.println(bootId);


  // -------------------------------------------------
  // MOTOR (TB6612FNG & ESP32 CORE 3.x LEDC)
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

  pinMode(
    MOTOR_STBY,
    OUTPUT
  );

  digitalWrite(
    MOTOR_STBY,
    LOW
  );

  digitalWrite(
    LEFT_IN1,
    LOW
  );

  digitalWrite(
    LEFT_IN2,
    LOW
  );

  digitalWrite(
    RIGHT_IN1,
    LOW
  );

  digitalWrite(
    RIGHT_IN2,
    LOW
  );


  // Attach LEDC PWM channels (ESP32 Arduino Core 3.x)
  if (
    !ledcAttach(
      LEFT_PWM,
      PWM_FREQUENCY,
      PWM_RESOLUTION
    )
  )
  {
    Serial.println(
      "FATAL: Failed to attach LEDC to LEFT_PWM (GPIO27)"
    );

    while (true)
      delay(1000);
  }

  if (
    !ledcAttach(
      RIGHT_PWM,
      PWM_FREQUENCY,
      PWM_RESOLUTION
    )
  )
  {
    Serial.println(
      "FATAL: Failed to attach LEDC to RIGHT_PWM (GPIO14)"
    );

    while (true)
      delay(1000);
  }


#if CONTINUOUS_FORWARD_TEST
  runContinuousForwardTest();
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

#if !CONTINUOUS_FORWARD_TEST
    while (true)
      delay(1000);
#endif
  }


  LoRa.enableCrc();

  LoRa.setTxPower(17);

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


  // -------------------------------------------------
  // GATEWAY DISCOVERY
  // -------------------------------------------------
  // One startup identity packet allows a gateway listener
  // to immediately identify TRUCK_02. The existing V2V
  // STATE packet and bidirectional V2V behavior are unchanged.

  LoRa.idle();

  delay(2);

  if (LoRa.beginPacket() == 1)
  {
    LoRa.print(
      "HELLO,TRUCK_02"
    );

    int gatewayHelloResult =
      LoRa.endPacket();

    if (gatewayHelloResult == 1)
    {
      Serial.println(
        "GATEWAY HELLO SENT: TRUCK_02"
      );
    }
    else
    {
      Serial.println(
        "GATEWAY HELLO TX FAILED"
      );
    }
  }
  else
  {
    Serial.println(
      "GATEWAY HELLO beginPacket FAILED"
    );
  }

  delay(2);

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
    millis()
    - V2V_INTERVAL
    + V2V_START_DELAY;

  lastHMITransmission =
    millis();

  lastStatusPrint =
    millis();


  // ===================================================
  // INITIAL MOTOR STATE
  // ===================================================

#if CONTINUOUS_FORWARD_TEST
  Serial.println();
  Serial.println(
    "===================================="
  );
  Serial.println(
    "VEHICLE B MOTOR TEST"
  );
  Serial.println(
    "CONTINUOUS FORWARD MODE"
  );
  Serial.println(
    "===================================="
  );
  Serial.println();
  Serial.println(
    "TB6612FNG"
  );
  Serial.println(
    "LEFT  : IN1=25 IN2=26 PWM=27"
  );
  Serial.println(
    "RIGHT : IN1=32 IN2=33 PWM=14"
  );
  Serial.println(
    "STBY  : 13"
  );
  Serial.println();
  Serial.print(
    "TEST PWM: "
  );
  Serial.println(
    CONTINUOUS_TEST_PWM
  );
  Serial.println();
  Serial.println(
    "FORWARD DIRECTION:"
  );
  Serial.println(
    "LEFT  = LOW/HIGH"
  );
  Serial.println(
    "RIGHT = HIGH/LOW"
  );
  Serial.println();
  Serial.println(
    "MOTOR TEST ACTIVE"
  );
  Serial.println(
    "===================================="
  );

  runContinuousForwardTest();
#else
  Serial.println();
  Serial.println(
    "======================================"
  );
  Serial.println(
    "TRUCK_02 READY"
  );
  Serial.println(
    "VEHICLE CONTROL INITIALIZED (RUNNING)"
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
  Serial.print(
    "TARGET PWM:    "
  );
  Serial.println(
    targetMotorPWM
  );
  Serial.println(
    "MOTOR: TB6612FNG (FORWARD)"
  );
  Serial.println(
    "V2V BIDIRECTIONAL ENABLED"
  );
  Serial.println(
    "======================================"
  );
#endif
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  unsigned long now =
    millis();


  // ===================================================
  // SERIAL COMMANDS (Physical Test & Failover Harness)
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
      Serial.println("--- VEHICLE B (TRUCK_02) STATUS ---");
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


  // -------------------------------------------------
  // VEHICLE COMMAND HTTP SERVER
  // -------------------------------------------------

  commandServer.handleClient();


  // -------------------------------------------------
  // CONTINUOUS MOTOR CONTROL
  // -------------------------------------------------

#if CONTINUOUS_FORWARD_TEST
  runContinuousForwardTest();
#else
  updateMotorControl();
#endif


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

#if CONTINUOUS_FORWARD_TEST
    Serial.println();
    Serial.print(
      "[MOTOR TEST] PWM="
    );
    Serial.print(
      CONTINUOUS_TEST_PWM
    );
    Serial.println(
      " | LEFT=RUNNING | RIGHT=RUNNING"
    );

    Serial.print(
      "[ENCODER] pulses="
    );
    Serial.print(
      pulseCount
    );
    Serial.print(
      " | RPM="
    );
    Serial.print(
      wheelRPM,
      2
    );
    Serial.print(
      " | speed="
    );
    Serial.print(
      measuredVehicleSpeed,
      3
    );
    Serial.println(
      " m/s"
    );
#endif

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
  // HMI DIRECT WIFI (ROLLBACK TOGGLE)
  // -------------------------------------------------

  if (ENABLE_DIRECT_WIFI_TELEMETRY)
  {
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


  // -------------------------------------------------
  // SAFE BEACON (Wi-Fi Loss Parity)
  // -------------------------------------------------
  if (wifiState == COMM_DISCONNECTED)
  {
    sendSafeBeacon();
  }


  delay(1);
}