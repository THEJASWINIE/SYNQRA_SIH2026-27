/*
  ============================================================
  SIH 2026-27
  FOG-ORCHESTRATOR
  VEHICLE B - TRUCK_02
  PHYSICAL SPEED CALIBRATION
  ============================================================

  BASED ON ACTUAL VEHICLE B CODE

  Motor Driver:
      L298N

  Motor Connections:
      LEFT  IN1 = GPIO25
      LEFT  IN2 = GPIO26
      LEFT  PWM = GPIO27

      RIGHT IN1 = GPIO32
      RIGHT IN2 = GPIO33
      RIGHT PWM = GPIO14

  Encoder:
      GPIO35

  Nominal Encoder PPR:
      43

  Wheel:
      Diameter = 6 cm

  Calibration:
      PWM -> Actual Ground Speed

  Test:
      10 seconds per PWM value

  Recommended PWM:
      50
      75
      100
      125
      150

  IMPORTANT:
      Measure actual ground distance manually.

  ESP32 Arduino Core 3.x
  ============================================================
*/

#include <Arduino.h>


// ============================================================
// VEHICLE B PARAMETERS
// ============================================================

#define VEHICLE_NAME "TRUCK_02"


// ============================================================
// L298N MOTOR DRIVER
// FROM ACTUAL VEHICLE B CODE
// ============================================================

// LEFT MOTOR
#define LEFT_IN1   25
#define LEFT_IN2   26
#define LEFT_PWM   27

// RIGHT MOTOR
#define RIGHT_IN1  32
#define RIGHT_IN2  33
#define RIGHT_PWM 14


// ============================================================
// ENCODER
// FROM ACTUAL VEHICLE B CODE
// ============================================================

#define SPEED_SENSOR_PIN 35

// Vehicle B nominal PPR
#define PULSES_PER_REV   34.58f


// ============================================================
// WHEEL
// ============================================================

const float WHEEL_DIAMETER_M = 0.06f;

const float WHEEL_CIRCUMFERENCE_M =
    PI * WHEEL_DIAMETER_M;


// ============================================================
// PWM
// ============================================================

const int PWM_FREQUENCY = 1000;

const int PWM_RESOLUTION = 8;

const int MIN_PWM = 0;

const int MAX_PWM = 150;


// ============================================================
// TEST
// ============================================================

const unsigned long TEST_TIME_MS = 10000;

const unsigned long START_DELAY_MS = 3000;


// ============================================================
// ENCODER
// ============================================================

volatile unsigned long pulseCount = 0;


// ============================================================
// ENCODER INTERRUPT
// ============================================================

void IRAM_ATTR speedSensorISR()
{
    pulseCount++;
}


// ============================================================
// SET FORWARD DIRECTION
// EXACT DIRECTION FROM VEHICLE B CODE
// ============================================================

void setForwardDirection()
{
    // LEFT MOTOR
    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, HIGH);

    // RIGHT MOTOR
    digitalWrite(RIGHT_IN1, HIGH);
    digitalWrite(RIGHT_IN2, LOW);
}


// ============================================================
// STOP VEHICLE
// ============================================================

void stopVehicle()
{
    ledcWrite(LEFT_PWM, 0);
    ledcWrite(RIGHT_PWM, 0);

    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, LOW);

    digitalWrite(RIGHT_IN1, LOW);
    digitalWrite(RIGHT_IN2, LOW);
}


// ============================================================
// APPLY PWM
// ============================================================

void applyMotorPWM(int pwm)
{
    pwm = constrain(
        pwm,
        MIN_PWM,
        MAX_PWM
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


// ============================================================
// RUN CALIBRATION
// ============================================================

void runCalibration(int pwm)
{
    Serial.println();
    Serial.println();
    Serial.println("========================================");
    Serial.println("       VEHICLE B CALIBRATION");
    Serial.println("========================================");

    Serial.print("Vehicle            : ");
    Serial.println(VEHICLE_NAME);

    Serial.print("Motor Driver       : L298N");

    Serial.println();

    Serial.print("PWM                : ");
    Serial.println(pwm);

    Serial.print("Nominal PPR        : ");
    Serial.println(PULSES_PER_REV, 2);

    Serial.print("Wheel diameter     : ");
    Serial.print(WHEEL_DIAMETER_M, 3);
    Serial.println(" m");

    Serial.print("Wheel circumference: ");
    Serial.print(WHEEL_CIRCUMFERENCE_M, 6);
    Serial.println(" m");

    Serial.println();
    Serial.println("========================================");
    Serial.println("MEASUREMENT INSTRUCTIONS");
    Serial.println("========================================");

    Serial.println("1. Place vehicle on the ground.");
    Serial.println("2. Mark the starting position.");
    Serial.println("3. Enter/confirm PWM.");
    Serial.println("4. Vehicle waits 3 seconds.");
    Serial.println("5. Vehicle runs for 10 seconds.");
    Serial.println("6. Measure actual distance travelled.");
    Serial.println();

    Serial.println("Starting in 3 seconds...");

    delay(START_DELAY_MS);


    // ========================================================
    // RESET ENCODER
    // ========================================================

    noInterrupts();

    pulseCount = 0;

    interrupts();


    // ========================================================
    // START
    // ========================================================

    Serial.println();
    Serial.println(">>> START");

    applyMotorPWM(pwm);

    unsigned long startTime = millis();


    // ========================================================
    // 10 SECOND TEST
    // ========================================================

    while (
        millis() - startTime <
        TEST_TIME_MS
    )
    {
        delay(5);
    }


    // ========================================================
    // STOP
    // ========================================================

    stopVehicle();

    Serial.println(">>> STOP");


    // ========================================================
    // READ ENCODER
    // ========================================================

    noInterrupts();

    unsigned long counts = pulseCount;

    interrupts();


    // ========================================================
    // CALCULATIONS
    // ========================================================

    const float timeSeconds =
        TEST_TIME_MS / 1000.0f;


    // --------------------------------------------------------
    // WHEEL REVOLUTIONS
    // --------------------------------------------------------

    float revolutions =
        (float)counts /
        PULSES_PER_REV;


    // --------------------------------------------------------
    // RPM
    // --------------------------------------------------------

    float rpm =
        (
            revolutions /
            timeSeconds
        ) * 60.0f;


    // --------------------------------------------------------
    // ENCODER DISTANCE
    // --------------------------------------------------------

    float encoderDistance =
        revolutions *
        WHEEL_CIRCUMFERENCE_M;


    // --------------------------------------------------------
    // ENCODER SPEED
    // --------------------------------------------------------

    float encoderSpeed =
        encoderDistance /
        timeSeconds;


    // ========================================================
    // PRINT RESULTS
    // ========================================================

    Serial.println();
    Serial.println("----------------------------------------");
    Serial.println("             RAW RESULTS");
    Serial.println("----------------------------------------");

    Serial.print("PWM                 : ");
    Serial.println(pwm);

    Serial.print("Encoder counts      : ");
    Serial.println(counts);

    Serial.print("Wheel revolutions   : ");
    Serial.println(
        revolutions,
        4
    );

    Serial.print("Wheel RPM           : ");
    Serial.println(
        rpm,
        3
    );

    Serial.print("Encoder distance    : ");
    Serial.print(
        encoderDistance,
        4
    );
    Serial.println(" m");

    Serial.print("Encoder speed       : ");
    Serial.print(
        encoderSpeed,
        4
    );
    Serial.println(" m/s");

    Serial.println("----------------------------------------");

    Serial.println();
    Serial.println(">>> NOW MEASURE ACTUAL GROUND DISTANCE");

    Serial.println();
    Serial.println("Example:");
    Serial.println("actual distance: 1.25");

    Serial.println();
    Serial.println("Enter next PWM after recording distance.");
    Serial.println();
}


// ============================================================
// SETUP
// ============================================================

void setup()
{
    Serial.begin(115200);

    delay(1000);


    // ========================================================
    // HEADER
    // ========================================================

    Serial.println();
    Serial.println();
    Serial.println("========================================");
    Serial.println("   FOG-ORCHESTRATOR VEHICLE B");
    Serial.println("       SPEED CALIBRATION");
    Serial.println("========================================");

    Serial.println();

    Serial.println("Vehicle: TRUCK_02");

    Serial.println("Motor Driver: L298N");

    Serial.println("ESP32");

    Serial.println();

    Serial.println("Motor Pins:");

    Serial.println("LEFT  -> IN1=25 IN2=26 PWM=27");

    Serial.println("RIGHT -> IN1=32 IN2=33 PWM=14");

    Serial.println();

    Serial.println("Encoder GPIO: 35");

    Serial.print("Nominal PPR: ");
    Serial.println(
        PULSES_PER_REV,
        1
    );

    Serial.print("Wheel diameter: ");
    Serial.print(
        WHEEL_DIAMETER_M * 100.0f,
        1
    );
    Serial.println(" cm");

    Serial.println();


    // ========================================================
    // MOTOR PINS
    // ========================================================

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


    // ========================================================
    // INITIAL MOTOR STATE
    // ========================================================

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


    // ========================================================
    // ESP32 CORE 3.x PWM
    // ========================================================

    bool leftPWMOK =
        ledcAttach(
            LEFT_PWM,
            PWM_FREQUENCY,
            PWM_RESOLUTION
        );


    bool rightPWMOK =
        ledcAttach(
            RIGHT_PWM,
            PWM_FREQUENCY,
            PWM_RESOLUTION
        );


    if (
        !leftPWMOK ||
        !rightPWMOK
    )
    {
        Serial.println();
        Serial.println(
            "ERROR: PWM ATTACH FAILED!"
        );

        while (true)
        {
            delay(1000);
        }
    }


    // ========================================================
    // ENCODER
    // ========================================================

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


    // ========================================================
    // MOTOR OFF
    // ========================================================

    stopVehicle();


    // ========================================================
    // READY
    // ========================================================

    Serial.println();
    Serial.println("========================================");
    Serial.println("          READY FOR VEHICLE B");
    Serial.println("             CALIBRATION");
    Serial.println("========================================");

    Serial.println();

    Serial.println("Recommended sequence:");

    Serial.println("50");

    Serial.println("75");

    Serial.println("100");

    Serial.println("125");

    Serial.println("150");

    Serial.println();

    Serial.println("IMPORTANT:");

    Serial.println("Maximum calibration PWM = 150");

    Serial.println("Perform test ON THE GROUND.");

    Serial.println("Measure actual distance manually.");

    Serial.println();

    Serial.println("Enter PWM in Serial Monitor:");

    Serial.println();
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
    if (
        Serial.available()
    )
    {
        String input =
            Serial.readStringUntil(
                '\n'
            );

        input.trim();


        if (
            input.length() == 0
        )
        {
            return;
        }


        int pwm =
            input.toInt();


        // ====================================================
        // VALIDATION
        // ====================================================

        if (
            pwm < 0 ||
            pwm > MAX_PWM
        )
        {
            Serial.println();

            Serial.println(
                "ERROR: PWM must be between 0 and 150."
            );

            Serial.println();

            return;
        }


        // ====================================================
        // STOP COMMAND
        // ====================================================

        if (
            pwm == 0
        )
        {
            stopVehicle();

            Serial.println();

            Serial.println(
                "VEHICLE STOPPED."
            );

            return;
        }


        // ====================================================
        // RUN
        // ====================================================

        runCalibration(
            pwm
        );
    }
}