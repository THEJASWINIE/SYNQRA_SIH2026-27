# FOG-ORCHESTRATOR 2.0 — Current Wiring Truth & Pin Assignments
**Document ID:** `DOC-03-HW-03` | **Audited Standard:** Direct Pinout Inspection

---

## 1. Complete GPIO Pin Assignment Table

| Subsystem Peripheral | Vehicle A (`TRUCK_01`) Pin | Vehicle B (`TRUCK_02`) Pin | Signal Direction | Hardware Peripheral |
| :--- | :---: | :---: | :---: | :--- |
| **Motor Left DIR1** | GPIO 25 | GPIO 25 | Digital Output | Left H-Bridge Direction 1 |
| **Motor Left DIR2** | GPIO 26 | GPIO 26 | Digital Output | Left H-Bridge Direction 2 |
| **Motor Left PWM** | GPIO 27 | GPIO 27 | LEDC PWM (1 kHz) | Left Motor Speed Enable |
| **Motor Right DIR1** | GPIO 32 | GPIO 32 | Digital Output | Right H-Bridge Direction 1 |
| **Motor Right DIR2** | GPIO 33 | GPIO 33 | Digital Output | Right H-Bridge Direction 2 |
| **Motor Right PWM** | GPIO 14 | GPIO 14 | LEDC PWM (1 kHz) | Right Motor Speed Enable |
| **Motor Standby (STBY)**| GPIO 13 | GPIO 13 | Digital Output | Active HIGH; LOW forces High-Z |
| **Wheel Optical Encoder**| GPIO 35 | GPIO 35 | Input (Interrupt) | RISING edge slot detector |
| **I2C SDA (IMU)** | GPIO 21 | GPIO 21 | Bidirectional | MPU6050 Accelerometer / Gyro |
| **I2C SCL (IMU)** | GPIO 22 | GPIO 22 | Output | MPU6050 I2C Clock |
| **LoRa SPI SCK** | GPIO 18 | GPIO 18 | SPI Clock Output | Semtech SX1278 SPI Bus |
| **LoRa SPI MISO** | GPIO 19 | GPIO 19 | SPI Data Input | Semtech SX1278 SPI Bus |
| **LoRa SPI MOSI** | GPIO 23 | GPIO 23 | SPI Data Output | Semtech SX1278 SPI Bus |
| **LoRa NSS (Chip Select)**| GPIO 5 | GPIO 5 | Digital Output | Semtech SX1278 Chip Select |
| **LoRa Reset (RST)** | GPIO 4 | GPIO 4 | Digital Output | Semtech SX1278 Hardware Reset |
| **LoRa DIO0 (Interrupt)**| GPIO 2 | GPIO 2 | Digital Input | Semtech SX1278 TX/RX Done IRQ |

---

## 2. Standby Safety Invariant

On Vehicle B (`TRUCK_02`), Toshiba TB6612FNG hardware pin 19 (`STBY`) is wired directly to GPIO 13.
- **Boot Invariant**: During `setup()`, GPIO 13 is explicitly driven LOW (`digitalWrite(MOTOR_STBY, LOW)`).
- **Physical Safety**: Pulling STBY LOW physically disconnects the MOSFET H-bridge outputs into high-impedance mode, guaranteeing zero motor movement regardless of input pin states until software initialization is complete.
