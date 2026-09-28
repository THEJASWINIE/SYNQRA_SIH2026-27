/*
  ============================================================
  SIH 2026-27
  FOG-ORCHESTRATOR
  VEHICLE SPEED CALIBRATION
  ============================================================

  Based on the frozen hardware connections from the
  FOG-ORCHESTRATOR vehicle code.

  Vehicle A:
      Encoder PPR = 42

  Vehicle B:
      Encoder PPR = 43

  Wheel diameter:
      6 cm

  Test:
      Enter PWM in Serial Monitor.
      Vehicle runs for 10 seconds.
      Record:
          - encoder counts
          - RPM
          - encoder-derived speed
          - actual measured distance

  ESP32 Arduino Core 3.x
  ============================================================
*/


#include <Arduino.h>


// ============================================================
// SELECT VEHICLE
// ============================================================

// 1 = Vehicle A
// 2 = Vehicle B

#define VEHICLE 1


// ============================================================
// VEHICLE PARAMETERS
// ============================================================

// Effective calibrated PPR matching production firmware (K = 34.58 pulses/rev)
#define ENCODER_EFFECTIVE_PPR 34.58f

#if VEHICLE == 1

const float PPR = ENCODER_EFFECTIVE_PPR; // Calibrated effective PPR (nominal 42.0f)

#else

const float PPR = ENCODER_EFFECTIVE_PPR; // Calibrated effective PPR (nominal 43.0f)

#endif


// ============================================================
// FROZEN MOTOR CONNECTIONS
// FROM YOUR ORIGINAL VEHICLE CODE
// ============================================================

// LEFT MOTOR

#define LEFT_IN1   25
#define LEFT_IN2   26
#define LEFT_PWM   27


// RIGHT MOTOR

#define RIGHT_IN1  32
#define RIGHT_IN2  33
#define RIGHT_PWM  14


// MOTOR STANDBY

#define MOTOR_STBY 13


// ============================================================
// SPEED SENSOR
// ============================================================

#define SPEED_SENSOR_PIN 35


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


// ============================================================
// TEST TIME
// ============================================================

const unsigned long TEST_TIME_MS = 10000;


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
// MOTOR FORWARD
// ============================================================

void setForwardDirection()
{
    /*
      Based directly on your existing code.
    */

    // LEFT MOTOR
    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, HIGH);

    // RIGHT MOTOR
    digitalWrite(RIGHT_IN1, HIGH);
    digitalWrite(RIGHT_IN2, LOW);
}


// ============================================================
// MOTOR STOP
// ============================================================

void stopVehicle()
{
    ledcWrite(LEFT_PWM, 0);
    ledcWrite(RIGHT_PWM, 0);

    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, LOW);

    digitalWrite(RIGHT_IN1, LOW);
    digitalWrite(RIGHT_IN2, LOW);

    digitalWrite(MOTOR_STBY, LOW);
}


// ============================================================
// APPLY PWM
// ============================================================

void applyMotorPWM(int pwm)
{
    pwm = constrain(pwm, 0, 255);

    if (pwm == 0)
    {
        stopVehicle();
        return;
    }

    // Enable motor driver
    digitalWrite(MOTOR_STBY, HIGH);

    // Forward
    setForwardDirection();

    // Same PWM to both motors
    ledcWrite(LEFT_PWM, pwm);
    ledcWrite(RIGHT_PWM, pwm);
}


// ============================================================
// RUN CALIBRATION TEST
// ============================================================

void runCalibration(int pwm)
{
    Serial.println();
    Serial.println("========================================");
    Serial.println("          CALIBRATION TEST");
    Serial.println("========================================");

#if VEHICLE == 1
    Serial.println("Vehicle          : A");
#else
    Serial.println("Vehicle          : B");
#endif

    Serial.print("PWM              : ");
    Serial.println(pwm);

    Serial.print("PPR              : ");
    Serial.println(PPR);

    Serial.print("Wheel diameter   : ");
    Serial.print(WHEEL_DIAMETER_M, 3);
    Serial.println(" m");

    Serial.print("Wheel circumference: ");
    Serial.print(WHEEL_CIRCUMFERENCE_M, 6);
    Serial.println(" m");

    Serial.println();
    Serial.println("Vehicle will start in 3 seconds...");

    delay(3000);


    // --------------------------------------------------------
    // RESET ENCODER
    // --------------------------------------------------------

    noInterrupts();

    pulseCount = 0;

    interrupts();


    // --------------------------------------------------------
    // START MOTOR
    // --------------------------------------------------------

    Serial.println("START");

    applyMotorPWM(pwm);


    unsigned long startTime = millis();


    // --------------------------------------------------------
    // 10 SECOND TEST
    // --------------------------------------------------------

    while (millis() - startTime < TEST_TIME_MS)
    {
        delay(10);
    }


    // --------------------------------------------------------
    // STOP
    // --------------------------------------------------------

    stopVehicle();

    Serial.println("STOP");


    // --------------------------------------------------------
    // READ ENCODER
    // --------------------------------------------------------

    noInterrupts();

    unsigned long counts = pulseCount;

    interrupts();


    // ========================================================
    // CALCULATIONS
    // ========================================================

    float timeSeconds =
        TEST_TIME_MS / 1000.0f;


    // Wheel revolutions

    float revolutions =
        (float)counts / PPR;


    // RPM

    float rpm =
        (revolutions / timeSeconds) * 60.0f;


    // Encoder-derived distance

    float encoderDistance =
        revolutions *
        WHEEL_CIRCUMFERENCE_M;


    // Encoder-derived speed

    float encoderSpeed =
        encoderDistance /
        timeSeconds;


    // ========================================================
    // RESULTS
    // ========================================================

    Serial.println();
    Serial.println("----------------------------------------");
    Serial.println("                RESULTS");
    Serial.println("----------------------------------------");

    Serial.print("PWM                 : ");
    Serial.println(pwm);

    Serial.print("Encoder counts      : ");
    Serial.println(counts);

    Serial.print("Wheel revolutions   : ");
    Serial.println(revolutions, 4);

    Serial.print("Wheel RPM           : ");
    Serial.println(rpm, 3);

    Serial.print("Encoder distance    : ");
    Serial.print(encoderDistance, 4);
    Serial.println(" m");

    Serial.print("Encoder speed       : ");
    Serial.print(encoderSpeed, 4);
    Serial.println(" m/s");

    Serial.println("----------------------------------------");

    Serial.println();
    Serial.println("IMPORTANT:");
    Serial.println("Measure the ACTUAL ground distance");
    Serial.println("travelled during this 10-second run.");

    Serial.println();
    Serial.println("Then enter the next PWM.");
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
    Serial.println("   FOG-ORCHESTRATOR SPEED CALIBRATION");
    Serial.println("========================================");

#if VEHICLE == 1
    Serial.println("Vehicle: A");
#else
    Serial.println("Vehicle: B");
#endif

    Serial.print("PPR: ");
    Serial.println(PPR);

    Serial.print("Wheel diameter: ");
    Serial.print(WHEEL_DIAMETER_M * 100.0f);
    Serial.println(" cm");


    // ========================================================
    // MOTOR PINS
    // ========================================================

    pinMode(LEFT_IN1, OUTPUT);
    pinMode(LEFT_IN2, OUTPUT);

    pinMode(RIGHT_IN1, OUTPUT);
    pinMode(RIGHT_IN2, OUTPUT);

    pinMode(MOTOR_STBY, OUTPUT);


    // ========================================================
    // INITIAL MOTOR STATE
    // ========================================================

    digitalWrite(MOTOR_STBY, LOW);

    digitalWrite(LEFT_IN1, LOW);
    digitalWrite(LEFT_IN2, LOW);

    digitalWrite(RIGHT_IN1, LOW);
    digitalWrite(RIGHT_IN2, LOW);


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


    if (!leftPWMOK || !rightPWMOK)
    {
        Serial.println();
        Serial.println("ERROR: PWM ATTACH FAILED!");

        while (true)
        {
            delay(1000);
        }
    }


    // ========================================================
    // SPEED SENSOR
    // ========================================================

    pinMode(
        SPEED_SENSOR_PIN,
        INPUT
    );


    attachInterrupt(
        digitalPinToInterrupt(SPEED_SENSOR_PIN),
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
    Serial.println("READY FOR CALIBRATION");
    Serial.println("========================================");

    Serial.println();
    Serial.println("Enter PWM value in Serial Monitor.");

    Serial.println();
    Serial.println("Suggested sequence:");
    Serial.println("50");
    Serial.println("75");
    Serial.println("100");
    Serial.println("125");
    Serial.println("150");
    Serial.println("175");
    Serial.println("200");
    Serial.println("225");

    Serial.println();
    Serial.println("PWM 255 can be tested later if safe.");

    Serial.println();
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
    if (Serial.available())
    {
        String input =
            Serial.readStringUntil('\n');

        input.trim();


        if (input.length() == 0)
        {
            return;
        }


        int pwm =
            input.toInt();


        // ----------------------------------------------------
        // VALIDATION
        // ----------------------------------------------------

        if (pwm < 0 || pwm > 255)
        {
            Serial.println();
            Serial.println(
                "ERROR: PWM must be 0-255."
            );

            return;
        }


        // ----------------------------------------------------
        // STOP COMMAND
        // ----------------------------------------------------

        if (pwm == 0)
        {
            stopVehicle();

            Serial.println();
            Serial.println("VEHICLE STOPPED.");

            return;
        }


        // ----------------------------------------------------
        // RUN
        // ----------------------------------------------------

        runCalibration(pwm);
    }
}