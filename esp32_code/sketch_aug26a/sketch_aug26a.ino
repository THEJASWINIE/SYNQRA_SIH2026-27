#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>

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

#define SPEED_SENSOR_PIN 35
#define PULSES_PER_REV   42.0


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

const char* WIFI_SSID = "jagadeesh";
const char* WIFI_PASSWORD = "jagadeeshking";

const char* HMI_SERVER =
  "http://10.126.54.41:8000/api/hardware/telemetry";


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

// Default speed used when no remote velocity has
// been received yet.
//
// Set to 0.0 if you want the vehicle to remain stopped
// until Vehicle B sends a velocity.
const float DEFAULT_SPEED_MS = 0.50f;


// Maximum physical prototype speed.
const float MAX_PROTOTYPE_SPEED_MS = 1.40f;


// Maximum PWM allowed.
const int MAX_MOTOR_PWM = 220;


// Minimum PWM.
//
// Keep 0 for this demo.
// If your motors need a minimum starting PWM,
// you can later change this to ~60-80.
const int MIN_MOTOR_PWM = 0;


// Motor update period.
const unsigned long MOTOR_UPDATE_INTERVAL = 50;


// Smooth acceleration/deceleration.
const int PWM_STEP = 4;


// Current commanded speed.
float commandedSpeedMs = DEFAULT_SPEED_MS;


// Actual PWM applied.
int appliedMotorPWM = 0;


// Desired PWM.
int targetMotorPWM = 0;


// Estimated applied speed.
float appliedSpeedMs = 0.0f;


// Last motor update.
unsigned long lastMotorUpdate = 0;


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
// V2V TIMING
// =====================================================

unsigned long txSequence = 0;

const unsigned long V2V_INTERVAL = 2000;


// Vehicle A transmits at 500 ms into the cycle.
const unsigned long V2V_START_DELAY = 500;

unsigned long lastV2VTransmission = 0;


// =====================================================
// HMI
// =====================================================

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
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);

  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);
}


// =====================================================
// MOTOR STOP
// =====================================================

void stopVehicle()
{
  analogWrite(LEFT_PWM, 0);
  analogWrite(RIGHT_PWM, 0);

  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, LOW);

  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, LOW);

  appliedMotorPWM = 0;
  appliedSpeedMs = 0.0f;
}


// =====================================================
// APPLY MOTOR PWM
// =====================================================
//
// THIS FIXES THE BROKEN:
//
// analogWrite(
//     pwm
//
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

  digitalWrite(MOTOR_STBY, HIGH);

  setForwardDirection();

  analogWrite(
    LEFT_PWM,
    pwm
  );

  analogWrite(
    RIGHT_PWM,
    pwm
  );
}


// =====================================================
// SPEED -> PWM
// =====================================================

int speedToPWM(float speedMs)
{
  if (!isfinite(speedMs))
  {
    return 0;
  }

  if (speedMs <= 0.0f)
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
    (int)round(
      ratio *
      MAX_MOTOR_PWM
    );

  return constrain(
    pwm,
    0,
    MAX_MOTOR_PWM
  );
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

    commandedSpeedMs =
      DEFAULT_SPEED_MS;

    Serial.println();
    Serial.println(
      "!!! REMOTE V2V VELOCITY TIMEOUT !!!"
    );

    Serial.println(
      "Returning to DEFAULT SPEED"
    );
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


  wheelRPM =
    (
      (float)newPulses /
      PULSES_PER_REV
    ) *
    60.0f;


  previousPulseCount =
    currentPulseCount;


  // Preserve your existing project convention.
  vehicleSpeed =
    wheelRPM;
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
  txSequence++;


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

  if (
    isfinite(remoteSpeed) &&
    remoteSpeed >= 0.0f
  )
  {
    commandedSpeedMs =
      constrain(
        remoteSpeed,
        0.0f,
        MAX_PROTOTYPE_SPEED_MS
      );


    Serial.println();
    Serial.println(
      ">>> REMOTE VELOCITY APPLIED"
    );

    Serial.print(
      "Vehicle B velocity: "
    );

    Serial.print(
      remoteSpeed,
      3
    );

    Serial.println(
      " m/s"
    );

    Serial.print(
      "Vehicle A target: "
    );

    Serial.print(
      commandedSpeedMs,
      3
    );

    Serial.println(
      " m/s"
    );
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
  }
  else
  {
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
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    hmiFailed++;

    Serial.println(
      "HMI: Wi-Fi disconnected"
    );

    return;
  }


  HTTPClient http;


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


  String json = "{";


  json +=
    "\"vehicle_id\":\"TRUCK_01\",";


  json +=
    "\"sequence\":";

  json +=
    String(txSequence);

  json += ",";


  json +=
    "\"rpm\":";

  json +=
    String(
      wheelRPM,
      2
    );

  json += ",";


  json +=
    "\"speed\":";

  json +=
    String(
      vehicleSpeed,
      2
    );

  json += ",";


  json +=
    "\"accel_x\":";

  json +=
    String(
      AcX
    );

  json += ",";


  json +=
    "\"accel_y\":";

  json +=
    String(
      AcY
    );

  json += ",";


  json +=
    "\"accel_z\":";

  json +=
    String(
      AcZ
    );

  json += ",";


  json +=
    "\"gyro_x\":";

  json +=
    String(
      GyX
    );

  json += ",";


  json +=
    "\"gyro_y\":";

  json +=
    String(
      GyY
    );

  json += ",";


  json +=
    "\"gyro_z\":";

  json +=
    String(
      GyZ
    );

  json += ",";


  json +=
    "\"rssi\":";

  json +=
    String(
      remoteDataValid ?
      remoteRSSI :
      0
    );

  json += ",";


  json +=
    "\"snr\":";

  json +=
    String(
      remoteDataValid ?
      remoteSNR :
      0.0f,
      2
    );

  json += ",";


  json +=
    "\"source\":\"DIRECT_WIFI\"";


  json += "}";


  Serial.println();

  Serial.println(
    ">>> HMI TX TRUCK_01"
  );

  Serial.println(
    json
  );


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
    response >= 200 &&
    response < 300
  )
  {
    hmiSent++;

    Serial.println(
      "HMI POST SUCCESS"
    );
  }
  else
  {
    hmiFailed++;

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
    HIGH
  );


  stopVehicle();


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


    while (true)
    {
      delay(1000);
    }
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
// LOOP
// =====================================================

void loop()
{
  unsigned long now =
    millis();


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