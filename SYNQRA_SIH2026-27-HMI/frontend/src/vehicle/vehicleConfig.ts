/**
 * Vehicle HMI configuration — what each truck actually is.
 *
 * ==========================================================================
 *  THE VEHICLE ID IS A BUILD-TIME CONSTANT, NOT A RUNTIME CHOICE.
 *
 *  `truck01.tsx` names TRUCK_01 and `truck02.tsx` names TRUCK_02, each as a `const`.
 *  There is deliberately no query parameter, no localStorage key, no environment
 *  variable and no picker that can retarget a running vehicle HMI at the other truck.
 *
 *  This is a CONVENIENCE, not a security boundary. Someone with a debugger can call
 *  anything with any argument. What stops a TRUCK_01 console from commanding TRUCK_02 is
 *  the backend: identity comes from a server-issued token and assignment is checked
 *  server-side, fail closed (operator_registry.py). The frontend scope exists so an
 *  operator cannot make that mistake by accident, not so an attacker cannot make it
 *  on purpose.
 * ==========================================================================
 *
 * WHAT THE CAPABILITY FLAGS ARE FOR
 *
 * They describe the PROTOTYPE AS BUILT, so a panel can say "this truck has no such
 * sensor" instead of rendering a row that is permanently blank and looks broken. They are
 * never used to synthesise a value: a capability that is present still shows UNAVAILABLE
 * until real data arrives. Each flag below is traceable to firmware or to the ingestion
 * contract, cited inline.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

/** The two vehicles this prototype has. Widening this needs hardware, not a code edit. */
export const VEHICLE_IDS = ["TRUCK_01", "TRUCK_02"] as const;
export type ConfiguredVehicleId = (typeof VEHICLE_IDS)[number];

/** How a vehicle's position may legitimately be obtained. Ordered by strength. */
export type PositionMethod = "GNSS" | "WHEEL_IMU_ODOMETRY" | "SYNTHETIC_GNSS" | "SIMULATED";

export interface VehicleHmiConfig {
  readonly vehicleId: ConfiguredVehicleId;
  readonly displayName: string;
  /** Dev server port for this HMI. Control room keeps 5173. */
  readonly devPort: number;

  // -- sensors, as actually fitted -----------------------------------------
  /** LM393 slot encoder. Both trucks have one physically. */
  readonly hasWheelEncoder: boolean;
  /** MPU6050. Both trucks have one. */
  readonly hasImu: boolean;
  /**
   * Whether the encoder's own derived speed REACHES the backend.
   *
   * TRUCK_01: yes - `sketch_aug26a.ino` divides by a measured dt and posts the result.
   * TRUCK_02: NO - its firmware posts `appliedSpeedMs`, the commanded PWM velocity, and
   * its encoder RPM is computed against a nominal 1000 ms loop rather than a measured dt.
   * So TRUCK_02's transmitted speed is not an encoder measurement and must never be
   * displayed as one.
   */
  readonly transmitsEncoderDerivedSpeed: boolean;
  /** No GNSS receiver is fitted to either vehicle. */
  readonly hasGnss: boolean;
  /** SX1278 433 MHz LoRa modem. Both trucks have one. */
  readonly hasLoRa: boolean;

  /**
   * Position methods this vehicle could legitimately support once implemented.
   *
   * Listing a method here does NOT mean a position exists. It means that if one appears,
   * this is a source it may honestly have come from.
   */
  readonly supportedPositionMethods: readonly PositionMethod[];

  /** Why this vehicle has no position right now, in words an operator can act on. */
  readonly positionLimitation: string;
}

const TRUCK_01_CONFIG: VehicleHmiConfig = {
  vehicleId: "TRUCK_01",
  displayName: "TRUCK_01",
  devPort: 3001,
  hasWheelEncoder: true,
  hasImu: true,
  transmitsEncoderDerivedSpeed: true,
  hasGnss: false,
  hasLoRa: true,
  // Wheel+IMU odometry is a LATER pass. It is listed as supportable, not as available.
  supportedPositionMethods: ["WHEEL_IMU_ODOMETRY", "SYNTHETIC_GNSS", "SIMULATED"],
  positionLimitation:
    "No GNSS receiver fitted. Wheel + IMU odometry is not yet implemented, so no position is produced.",
};

const TRUCK_02_CONFIG: VehicleHmiConfig = {
  vehicleId: "TRUCK_02",
  displayName: "TRUCK_02",
  devPort: 3002,
  hasWheelEncoder: true,
  hasImu: true,
  transmitsEncoderDerivedSpeed: false,
  hasGnss: false,
  hasLoRa: true,
  // Deliberately excludes WHEEL_IMU_ODOMETRY: the encoder signal this would need is not
  // transmitted, and the speed that IS transmitted is PWM-derived.
  supportedPositionMethods: ["SYNTHETIC_GNSS", "SIMULATED"],
  positionLimitation:
    "No GNSS receiver fitted. Encoder-derived speed is not transmitted by this vehicle's firmware, so wheel odometry is not available either.",
};

const CONFIGS: Readonly<Record<ConfiguredVehicleId, VehicleHmiConfig>> = {
  TRUCK_01: TRUCK_01_CONFIG,
  TRUCK_02: TRUCK_02_CONFIG,
};

/** True when the id names a vehicle this build knows about. */
export function isConfiguredVehicleId(id: string): id is ConfiguredVehicleId {
  return (VEHICLE_IDS as readonly string[]).includes(id);
}

/**
 * The configuration for a vehicle.
 *
 * THROWS on an unknown id rather than returning a default. A vehicle HMI that cannot say
 * which truck it is must not start at all: a console showing a plausible-looking but
 * wrong vehicle is the single worst failure this application can have.
 */
export function vehicleConfig(id: string): VehicleHmiConfig {
  if (!isConfiguredVehicleId(id)) {
    throw new Error(
      `Unknown vehicle id "${id}". A vehicle HMI must be built for a configured vehicle; ` +
        `known ids are ${VEHICLE_IDS.join(", ")}.`,
    );
  }
  return CONFIGS[id];
}
