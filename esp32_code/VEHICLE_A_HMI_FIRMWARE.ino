#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>

// =====================================================
// VEHICLE A FIRMWARE — FOG-ORCHESTRATOR 2.0 (TRUCK_01)
// 4-Wheel Differential Drive (TB6612FNG) + LM393 + MPU6050 + Ra-02 LoRa
// =====================================================

// MOTOR PINS (TB6612FNG)
#define LEFT_IN1 25
#define LEFT_IN2 26
#define LEFT_PWM 27

#define RIGHT_IN1 32
#define RIGHT_IN2 33
#define RIGHT_PWM 14

#define MOTOR_STBY 13

// SPEED SENSOR / ENCODER
#define SPEED_SENSOR_PIN 35
#define PULSES_PER_REV 42.0
#define WHEEL_DIAMETER_M 0.10 // 10 cm wheel diameter

// MPU6050 IMU
#define MPU_ADDR 0x68
int16_t AcX, AcY, AcZ;
int16_t GyX, GyY, GyZ;

// LORA RA-02
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS   5
#define LORA_RST  4
#define LORA_DIO0 34
#define LORA_FREQUENCY 433E6

// ENCODER VARIABLES
volatile unsigned long pulseCount = 0;
unsigned long previousPulseCount = 0;
float wheelRPM = 0.0;
float speedMps = 0.0;
float pulsesPerSecond = 0.0;

// NON-BLOCKING MILLIS TIMERS
unsigned long lastSpeedCalculation = 0;
unsigned long lastIMURead = 0;
unsigned long lastLoRaSend = 0;
unsigned long lastSerialPrint = 0;

const unsigned long SPEED_CALC_INTERVAL_MS = 500;
const unsigned long IMU_READ_INTERVAL_MS = 100;
const unsigned long LORA_SEND_INTERVAL_MS = 500; // 500ms telemetry rate

// MOTOR CONTROL FUNCTIONS (PRESERVED)
void moveForward(int speedValue) {
  digitalWrite(MOTOR_STBY, HIGH);
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);
  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);
  analogWrite(LEFT_PWM, speedValue);
  analogWrite(RIGHT_PWM, speedValue);
}

void moveBackward(int speedValue) {
  digitalWrite(MOTOR_STBY, HIGH);
  digitalWrite(LEFT_IN1, HIGH);
  digitalWrite(LEFT_IN2, LOW);
  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, HIGH);
  analogWrite(LEFT_PWM, speedValue);
  analogWrite(RIGHT_PWM, speedValue);
}

void stopVehicle() {
  analogWrite(LEFT_PWM, 0);
  analogWrite(RIGHT_PWM, 0);
  digitalWrite(MOTOR_STBY, LOW);
}

// SPEED SENSOR ISR (PRESERVED)
void IRAM_ATTR speedSensorISR() {
  pulseCount++;
}

// MPU6050 INIT & READ
void initializeMPU6050() {
  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);
  Serial.println("[VEHICLE_A] MPU6050 Initialized");
}

void readMPU6050() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);
  AcX = Wire.read() << 8 | Wire.read();
  AcY = Wire.read() << 8 | Wire.read();
  AcZ = Wire.read() << 8 | Wire.read();

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x43);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);
  GyX = Wire.read() << 8 | Wire.read();
  GyY = Wire.read() << 8 | Wire.read();
  GyZ = Wire.read() << 8 | Wire.read();
}

// SPEED CALCULATION
void calculateSpeed() {
  noInterrupts();
  unsigned long currentPulseCount = pulseCount;
  interrupts();

  unsigned long newPulses = currentPulseCount - previousPulseCount;
  float dt_s = (millis() - lastSpeedCalculation) / 1000.0;
  if (dt_s <= 0.0) dt_s = 0.5;

  pulsesPerSecond = newPulses / dt_s;
  wheelRPM = (pulsesPerSecond / PULSES_PER_REV) * 60.0;
  speedMps = (wheelRPM * 3.14159 * WHEEL_DIAMETER_M) / 60.0;

  previousPulseCount = currentPulseCount;
  lastSpeedCalculation = millis();
}

// CANONICAL LORA TELEMETRY TRANSMISSION
void sendLoRaTelemetry() {
  // Normalize raw IMU values to physical units
  float ax_g = AcX / 16384.0 * 9.81;
  float ay_g = AcY / 16384.0 * 9.81;
  float az_g = AcZ / 16384.0 * 9.81;
  float gx_rad = (GyX / 131.0) * (3.14159 / 180.0);
  float gy_rad = (GyY / 131.0) * (3.14159 / 180.0);
  float gz_rad = (GyZ / 131.0) * (3.14159 / 180.0);

  LoRa.beginPacket();
  LoRa.print("V=TRUCK_01,");
  LoRa.print("RPM="); LoRa.print(wheelRPM, 1); LoRa.print(",");
  LoRa.print("SPD="); LoRa.print(speedMps, 2); LoRa.print(",");
  LoRa.print("AX="); LoRa.print(ax_g, 2); LoRa.print(",");
  LoRa.print("AY="); LoRa.print(ay_g, 2); LoRa.print(",");
  LoRa.print("AZ="); LoRa.print(az_g, 2); LoRa.print(",");
  LoRa.print("GX="); LoRa.print(gx_rad, 2); LoRa.print(",");
  LoRa.print("GY="); LoRa.print(gy_rad, 2); LoRa.print(",");
  LoRa.print("GZ="); LoRa.print(gz_rad, 2);
  LoRa.endPacket();

  Serial.println("[VEHICLE_A] Sent Telemetry: V=TRUCK_01");
}

void setup() {
  Serial.begin(115200);
  pinMode(LEFT_IN1, OUTPUT);
  pinMode(LEFT_IN2, OUTPUT);
  pinMode(LEFT_PWM, OUTPUT);
  pinMode(RIGHT_IN1, OUTPUT);
  pinMode(RIGHT_IN2, OUTPUT);
  pinMode(RIGHT_PWM, OUTPUT);
  pinMode(MOTOR_STBY, OUTPUT);

  pinMode(SPEED_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SPEED_SENSOR_PIN), speedSensorISR, RISING);

  initializeMPU6050();

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("[VEHICLE_A] ERROR: LoRa init failed!");
  } else {
    Serial.println("[VEHICLE_A] LoRa Initialized OK (433MHz)");
  }

  // Initial motor state: stopped
  stopVehicle();
}

void loop() {
  unsigned long now = millis();

  if (now - lastIMURead >= IMU_READ_INTERVAL_MS) {
    readMPU6050();
    lastIMURead = now;
  }

  if (now - lastSpeedCalculation >= SPEED_CALC_INTERVAL_MS) {
    calculateSpeed();
  }

  if (now - lastLoRaSend >= LORA_SEND_INTERVAL_MS) {
    sendLoRaTelemetry();
    lastLoRaSend = now;
  }
}
