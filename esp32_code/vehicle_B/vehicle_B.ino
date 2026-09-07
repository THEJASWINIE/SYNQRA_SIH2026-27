#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>

// =====================================================
// VEHICLE B - TRUCK_02
//
// BIDIRECTIONAL V2V + WIFI HMI GATEWAY
//
// A <---LoRa---> B ---> WiFi ---> HMI
//
// HARDWARE CONNECTIONS FROZEN
// =====================================================


// =====================================================
// MOTOR PINS - L298N
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
#define PULSES_PER_REV 43.0

volatile unsigned long pulseCount = 0;
unsigned long previousPulseCount = 0;

float wheelRPM = 0.0;
float vehicleSpeed = 0.0;


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
// V2V
// =====================================================

unsigned long txSequence = 0;

const unsigned long V2V_INTERVAL = 2000;

// B transmission slot
const unsigned long V2V_START_DELAY = 1500;

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
// ISR
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
}


// =====================================================
// MPU INIT
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
    Serial.println("MPU6050 Initialized");
  }
  else
  {
    Serial.print("MPU6050 ERROR: ");
    Serial.println(status);
  }
}


// =====================================================
// MPU READ
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
    AcX = Wire.read() << 8 | Wire.read();
    AcY = Wire.read() << 8 | Wire.read();
    AcZ = Wire.read() << 8 | Wire.read();
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
    GyX = Wire.read() << 8 | Wire.read();
    GyY = Wire.read() << 8 | Wire.read();
    GyZ = Wire.read() << 8 | Wire.read();
  }
}


// =====================================================
// RPM
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
    ((float)newPulses /
     PULSES_PER_REV) * 60.0;

  previousPulseCount =
    currentPulseCount;

  vehicleSpeed = wheelRPM;
}


// =====================================================
// BUILD B STATE
// =====================================================

String buildOwnState()
{
  txSequence++;

  String packet = "";

  packet += "STATE";
  packet += ",TRUCK_02";
  packet += ",";
  packet += String(txSequence);
  packet += ",";
  packet += String(wheelRPM, 2);
  packet += ",";
  packet += String(vehicleSpeed, 2);
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
// SEND B -> A
// =====================================================

void sendV2VState()
{
  String packet =
    buildOwnState();

  Serial.println();
  Serial.println(">>> V2V TX B -> A");
  Serial.println(packet);

  LoRa.beginPacket();

  LoRa.print(packet);

  LoRa.endPacket();

  Serial.println("TX COMPLETE");
}


// =====================================================
// PARSE A STATE
// =====================================================

bool parseVehicleA(String packet)
{
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


  // Missing packets
  if (
    lastRemotePacket != 0 &&
    sequence > remoteSequence + 1
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

  Serial.print("Sequence: ");
  Serial.println(remoteSequence);

  Serial.print("RPM: ");
  Serial.println(remoteRPM);

  Serial.print("Speed: ");
  Serial.println(remoteSpeed);

  Serial.print("Accel X: ");
  Serial.println(remoteAccelX);

  Serial.print("Accel Y: ");
  Serial.println(remoteAccelY);

  Serial.print("Accel Z: ");
  Serial.println(remoteAccelZ);

  Serial.print("Gyro X: ");
  Serial.println(remoteGyroX);

  Serial.print("Gyro Y: ");
  Serial.println(remoteGyroY);

  Serial.print("Gyro Z: ");
  Serial.println(remoteGyroZ);

  Serial.print("RSSI: ");
  Serial.println(remoteRSSI);

  Serial.print("SNR: ");
  Serial.println(remoteSNR);

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

  if (!packetSize)
    return;


  String packet = "";

  while (LoRa.available())
  {
    packet +=
      (char)LoRa.read();
  }


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
    if (parseVehicleA(packet))
    {
      // Immediately relay A to HMI
      sendRemoteAToHMI();
    }
  }
  else
  {
    ignoredPackets++;

    Serial.println(
      "IGNORED NON-STATE PACKET"
    );
  }
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
      "IP: "
    );

    Serial.println(
      WiFi.localIP()
    );
  }
  else
  {
    Serial.println(
      "Wi-Fi FAILED"
    );
  }
}


// =====================================================
// GENERIC HMI POST
// =====================================================

bool postToHMI(String json)
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

  Serial.println(response);

  return false;
}


// =====================================================
// SEND B -> HMI
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
    "\"source\":\"DIRECT_WIFI\"";


  json += "}";


  Serial.println();
  Serial.println(
    ">>> HMI TX TRUCK_02"
  );

  Serial.println(json);

  postToHMI(json);
}


// =====================================================
// FORWARD A -> HMI
// =====================================================

void sendRemoteAToHMI()
{
  String json = "{";

  json +=
    "\"vehicle_id\":\"TRUCK_01\",";

  json +=
    "\"sequence\":";

  json +=
    String(remoteSequence);

  json += ",";


  json +=
    "\"rpm\":";

  json +=
    String(remoteRPM, 2);

  json += ",";


  json +=
    "\"speed\":";

  json +=
    String(remoteSpeed, 2);

  json += ",";


  json +=
    "\"accel_x\":";

  json +=
    String(remoteAccelX);

  json += ",";


  json +=
    "\"accel_y\":";

  json +=
    String(remoteAccelY);

  json += ",";


  json +=
    "\"accel_z\":";

  json +=
    String(remoteAccelZ);

  json += ",";


  json +=
    "\"gyro_x\":";

  json +=
    String(remoteGyroX);

  json += ",";


  json +=
    "\"gyro_y\":";

  json +=
    String(remoteGyroY);

  json += ",";


  json +=
    "\"gyro_z\":";

  json +=
    String(remoteGyroZ);

  json += ",";


  json +=
    "\"rssi\":";

  json +=
    String(remoteRSSI);

  json += ",";


  json +=
    "\"snr\":";

  json +=
    String(remoteSNR, 2);

  json += ",";


  json +=
    "\"source\":\"V2V_VIA_TRUCK_02\"";


  json += "}";


  Serial.println();
  Serial.println(
    ">>> RELAY TRUCK_01 -> HMI"
  );

  Serial.println(json);


  postToHMI(json);
}


// =====================================================
// REMOTE STATUS
// =====================================================

String remoteStatus()
{
  if (
    lastRemotePacket == 0
  )
    return "WAITING";


  unsigned long age =
    millis() -
    lastRemotePacket;


  if (age < 5000)
    return "ONLINE";


  if (age < 10000)
    return "STALE";


  return "OFFLINE";
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
    "       TRUCK_02 GATEWAY STATUS"
  );

  Serial.println(
    "######################################"
  );


  Serial.println();

  Serial.println(
    "LOCAL VEHICLE"
  );

  Serial.print(
    "Sequence: "
  );

  Serial.println(
    txSequence
  );

  Serial.print(
    "RPM: "
  );

  Serial.println(
    wheelRPM
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
    "RPM: "
  );

  Serial.println(
    remoteRPM
  );

  Serial.print(
    "Speed: "
  );

  Serial.println(
    remoteSpeed
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
    remoteSNR
  );

  Serial.print(
    "Status: "
  );

  Serial.println(
    remoteStatus()
  );


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
    missedPackets
  );

  Serial.print(
    "Malformed: "
  );

  Serial.println(
    malformedPackets
  );


  Serial.println();

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


  // Motors
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


  // Encoder
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


  // IMU
  Wire.begin(
    MPU_SDA,
    MPU_SCL
  );

  initializeMPU6050();


  // LoRa
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
      delay(1000);
  }


  LoRa.enableCrc();

  LoRa.setTxPower(17);


  Serial.println(
    "LoRa SUCCESS"
  );


  // Wi-Fi
  connectWiFi();


  lastSpeedCalculation =
    millis();

  lastIMURead =
    millis();


  // B gets the 1500 ms slot
  lastTransmission =
    millis() -
    V2V_INTERVAL +
    V2V_START_DELAY;


  lastHMITransmission =
    millis();

  lastStatusPrint =
    millis();


  Serial.println();

  Serial.println(
    "TRUCK_02 READY"
  );

  Serial.println(
    "HMI GATEWAY READY"
  );

  Serial.println(
    "V2V SLOT: 1500 ms"
  );
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  unsigned long now =
    millis();


  // RPM
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


  // IMU
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


  // FIRST: RECEIVE A
  receiveV2V();


  // B -> A
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


  // B -> HMI
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


  // STATUS
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
}