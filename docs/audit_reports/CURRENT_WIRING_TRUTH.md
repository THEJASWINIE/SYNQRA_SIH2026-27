# CURRENT WIRING TRUTH — FOG-ORCHESTRATOR 2.0
**Document Date:** 2026-09-27  
**Forensic Source:** Direct Firmware Source (`sketch_aug26a.ino` & `VEHICLE_B_...ino`), Serial Boot Logs, and Board Pinouts  

---

## 1. Pin Assignment & Hardware Subsystem Comparison

| Signal / Function | Vehicle A (`TRUCK_01`) Pin | Vehicle B (`TRUCK_02`) Pin | Direction / Type | Hardware Peripheral / Target |
|:---|:---:|:---:|:---:|:---|
| **Motor Left DIR1** | GPIO 25 (`LEFT_IN1`) | GPIO 25 (`LEFT_IN1`) | Output (Digital) | Left Motor Direction Input 1 |
| **Motor Left DIR2** | GPIO 26 (`LEFT_IN2`) | GPIO 26 (`LEFT_IN2`) | Output (Digital) | Left Motor Direction Input 2 |
| **Motor Left PWM** | GPIO 27 (`LEFT_PWM`) | GPIO 27 (`LEFT_PWM`) | Output (LEDC / PWM) | Left Motor Speed Enable |
| **Motor Right DIR1** | GPIO 32 (`RIGHT_IN1`) | GPIO 32 (`RIGHT_IN1`) | Output (Digital) | Right Motor Direction Input 1 |
| **Motor Right DIR2** | GPIO 33 (`RIGHT_IN2`) | GPIO 33 (`RIGHT_IN2`) | Output (Digital) | Right Motor Direction Input 2 |
| **Motor Right PWM** | GPIO 14 (`RIGHT_PWM`) | GPIO 14 (`RIGHT_PWM`) | Output (LEDC / PWM) | Right Motor Speed Enable |
| **Motor Standby / Enable** | GPIO 13 (`MOTOR_STBY`) | GPIO 13 (`MOTOR_STBY`) | Output (Digital) | H-Bridge Standby (HIGH = Active, LOW = High-Z) |
| **Speed Encoder Input** | GPIO 35 (`SPEED_SENSOR_PIN`) | GPIO 35 (`SPEED_SENSOR_PIN`) | Input (Interrupt, RISING) | Slotted Optical Disc Sensor |
| **I2C SDA (IMU)** | GPIO 21 (`MPU_SDA`) | GPIO 21 (`MPU_SDA`) | Bidirectional (I2C) | MPU6050 Accelerometer / Gyroscope (0x68) |
| **I2C SCL (IMU)** | GPIO 22 (`MPU_SCL`) | GPIO 22 (`MPU_SCL`) | Output (I2C Clock) | MPU6050 Accelerometer / Gyroscope (0x68) |
| **LoRa SPI SCK** | GPIO 18 (`LORA_SCK`) | GPIO 18 (`LORA_SCK`) | Output (SPI Clock) | Semtech SX1278 SPI Bus |
| **LoRa SPI MISO** | GPIO 19 (`LORA_MISO`) | GPIO 19 (`LORA_MISO`) | Input (SPI MISO) | Semtech SX1278 SPI Bus |
| **LoRa SPI MOSI** | GPIO 23 (`LORA_MOSI`) | GPIO 23 (`LORA_MOSI`) | Output (SPI MOSI) | Semtech SX1278 SPI Bus |
| **LoRa Chip Select (NSS)** | GPIO 5 (`LORA_SS`) | GPIO 5 (`LORA_SS`) | Output (Digital) | Semtech SX1278 Chip Select |
| **LoRa Reset** | GPIO 4 (`LORA_RST`) | GPIO 4 (`LORA_RST`) | Output (Digital) | Semtech SX1278 Hardware Reset |
| **LoRa DIO0 (IRQ)** | GPIO 2 (`LORA_DIO0`) | GPIO 2 (`LORA_DIO0`) | Input (Interrupt) | Semtech SX1278 Packet RX/TX Done |

---

## 2. Motor Driver Architecture Differences

### Vehicle A (`TRUCK_01`)
- **Driver Module:** L298N Dual Full-Bridge Driver (or TB6612 compatible).
- **Control Truth Table:**
  - Forward: `LEFT_IN1 = HIGH`, `LEFT_IN2 = LOW`, `RIGHT_IN1 = HIGH`, `RIGHT_IN2 = LOW`
  - Reverse: `LEFT_IN1 = LOW`, `LEFT_IN2 = HIGH`, `RIGHT_IN1 = LOW`, `RIGHT_IN2 = HIGH`
  - Stop/Standby: `MOTOR_STBY = LOW`, `LEFT_PWM = 0`, `RIGHT_PWM = 0`

### Vehicle B (`TRUCK_02`)
- **Driver Module:** TB6612FNG MOSFET-based Dual Motor Driver.
- **Standby Logic:** TB6612FNG hardware pin 19 (`STBY`) is directly driven by GPIO 13.
- **Safety Invariant:**
  - On startup (`setup()`), `digitalWrite(MOTOR_STBY, LOW)` forces the MOSFET H-bridge outputs into high-impedance mode, physically preventing motor current flow regardless of PWM or input pins until explicit software initialization occurs.
