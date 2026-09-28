"""
experiments/generate_final_registers_and_matrices.py
---------------------------------------------------
Generates the authoritative CSV matrices and registers for the FINAL evidence package:
1. FINAL_HARDWARE_EVIDENCE_MATRIX.csv
2. FINAL_EVIDENCE_MATRIX.csv
3. FINAL_CLAIM_REGISTER.csv
4. FINAL_CONTRADICTION_REGISTER.csv
"""

import csv
import os

FINAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FINAL"))
os.makedirs(FINAL_DIR, exist_ok=True)

def generate_hardware_evidence_matrix():
    path = os.path.join(FINAL_DIR, "FINAL_HARDWARE_EVIDENCE_MATRIX.csv")
    headers = [
        "Component", "Physical_Measured", "Simulated", "HIL", "Analytical",
        "Evidence_Level", "Hardware_Tested", "Test_Setup", "Known_Limitation"
    ]
    rows = [
        [
            "ESP32 Microcontroller", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "ESP32-WROOM-32D (Dual Core 240MHz)", "Bench testbed running FreeRTOS dual-task firmware",
            "Bench environment; mine vibration, thermal cycling, and IP67 enclosure unverified"
        ],
        [
            "LoRa SX1278 Transceiver", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "Ai-Thinker Ra-02 (SX1278 433MHz)", "Dual ESP32 nodes over 150m outdoor LOS bench test",
            "LOS outdoor open terrain; open-pit hematite dust attenuation and pit multipath uncharacterized"
        ],
        [
            "V2V Protocol (STATE format)", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "ESP32 + Ra-02 LoRa / WiFi broadcast", "Peer-to-peer cyclic state broadcasts at 10 Hz",
            "Tested with 2 physical nodes; scalable mesh contention (>10 nodes) modeled in simulation"
        ],
        [
            "Gateway Coordination", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "ESP32 LoRa-to-UDP Gateway bridge", "Gateway bench node relaying packets to orchestrator",
            "Tested on bench LAN; open-cast mine fiber backhaul and repeater hops uncharacterized"
        ],
        [
            "RF Packet Delivery Ratio (PDR)", "YES", "YES", "YES", "NO",
            "L7_BENCH_MEASURED", "Dual ESP32 SX1278 (1,000 packets)", "150m outdoor line-of-sight testbed (99.1% PDR)",
            "Bench LOS only; pit highwall shadowing and heavy machinery RF occlusion simulated"
        ],
        [
            "RF Latency (Roundtrip)", "YES", "YES", "YES", "NO",
            "L7_BENCH_MEASURED", "ESP32 LoRa ping-pong timer", "Hardware timer logging 41.2 ms mean roundtrip over air",
            "Does not include heavy network congestion or multi-hop gateway relay queueing"
        ],
        [
            "CAN / TWAI Bus Controller", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "ESP32 TWAI peripheral + SN65HVD230", "250 kbps 29-bit extended bus testbed (0.512 ms wire delay)",
            "Bench wiring harness; not connected to live OEM Cummins/Allison J1939 powertrain backbone"
        ],
        [
            "J1939-Compatible Frames", "YES", "NO", "YES", "NO",
            "L7_BENCH_MEASURED", "Project-defined PGN encoder/decoder", "6 PGNs (61444, 65265, 61441, 65281, 65282, 65280)",
            "Project-defined J1939-style signal definitions; OEM proprietary security seeds unvalidated"
        ],
        [
            "Wheel Speed Encoder", "NO", "YES", "YES", "NO",
            "L6_MODELED", "Simulated Vehicle ECU pulse generator", "Software pulse generator feeding simulated CCVS CAN frame",
            "Physical optical/magnetic hall encoder on BH100 wheel hub not installed"
        ],
        [
            "MPU-6050 IMU Sensor", "YES", "YES", "YES", "NO",
            "L7_BENCH_MEASURED", "InvenSense MPU-6050 6-DOF I2C", "I2C read at 40 Hz on ESP32 bench node (1.26 ms sample time)",
            "Laboratory benchtop; haul truck chassis vibration filtering and mounting unvalidated"
        ],
        [
            "Brake Actuator Valve", "NO", "YES", "YES", "NO",
            "L6_MODELED", "HIL Actuator Model (tau in [200, 350] ms)", "Parametric electro-pneumatic delay model in software",
            "Physical BH100 air-over-hydraulic proportional valve dynamics not physically plumbed"
        ],
        [
            "Service Friction Brakes", "NO", "YES", "NO", "YES",
            "L6_MATHEMATICAL_DERIVATION", "Newtonian deceleration model", "550 kN rated mechanical brake force derived from ISO 3450",
            "No physical dyno or vehicle pad deceleration test performed"
        ],
        [
            "Hydrodynamic Retarder", "NO", "YES", "NO", "YES",
            "L2_OEM_DOCUMENTED", "Allison 8610 transmission retarder", "OEM continuous absorption envelope modeled on -8% grade",
            "Physical transmission fluid temperature rise and continuous thermal fade unmeasured"
        ],
        [
            "Longitudinal Vehicle Dynamics", "NO", "YES", "YES", "YES",
            "L6_MODELED", "SimulatedVehicleECU Runge-Kutta integrator", "Closed-loop force balance (grade, roll, aero, brake, engine)",
            "Longitudinal 1D dynamics; multi-body lateral roll, pitch, and tire shear slip unmodeled"
        ],
        [
            "Visibility / Fog Measurement", "NO", "YES", "YES", "NO",
            "L6_MODELED", "Synthetic visibility profile generator", "Controlled visibility inputs (100m to 3m) in test scripts",
            "Physical transmissometer / forward-scatter fog sensor not deployed in field"
        ],
        [
            "GNSS / RTK Localization", "NO", "YES", "NO", "NO",
            "L6_MODELED", "Simulated coordinate telemetry", "1D stationing / GPS coordinate emulation in Digital Twin",
            "Physical multi-constellation RTK receiver with Bailadila canyon multipath unmeasured"
        ],
        [
            "BEML BH100 Haul Truck", "NO", "NO", "YES", "YES",
            "L2_OEM_DOCUMENTED", "OEM specification brochure & civil data", "165.5 t gross operating weight, 91.5 t payload, 10.525 m length",
            "No live physical BH100 truck operated or modified in active mine operations"
        ]
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Saved {path}")

def generate_evidence_matrix():
    path = os.path.join(FINAL_DIR, "FINAL_EVIDENCE_MATRIX.csv")
    headers = [
        "Claim_ID", "Claim", "Evidence", "Evidence_Level", "Physical", "HIL",
        "Simulation", "Analytical", "Reproducible", "Independent", "Limitation"
    ]
    rows = [
        [
            "EVID-01", "Dual ESP32 SX1278 RF link achieves 99.1% PDR over 150m LOS",
            "1,000 packets transmitted on Ra-02 433 MHz hardware testbed",
            "L7_BENCH_MEASURED", "YES", "NO", "NO", "NO", "YES", "YES",
            "Valid only for open LOS benchtop; pit wall occlusion and mining dust uncharacterized"
        ],
        [
            "EVID-02", "CAN/TWAI 250 kbps bus latency is 0.512 ms wire propagation",
            "Measured on ESP32 TWAI peripheral with 29-bit extended frames",
            "L7_BENCH_MEASURED", "YES", "NO", "NO", "NO", "YES", "YES",
            "Wire time only; chassis queueing under heavy CAN bus traffic reaches 12.6 ms"
        ],
        [
            "EVID-03", "Electronic command-path latency is 216.05 ms median under HIL",
            "Logged across 105 systematic trials in HIL simulator",
            "L7_L6_COMBINED", "PARTIAL", "YES", "NO", "NO", "YES", "YES",
            "Electronic path only (13.8 ms bench + 202.2 ms modeled actuator); not physical brake build"
        ],
        [
            "EVID-04", "Local safety governor clamps all central overspeed requests",
            "Adversarial 30 m/s request clamped to 5.12 m/s or 1.95 m/s",
            "FACT_ARCHITECTURAL", "NO", "YES", "YES", "YES", "YES", "YES",
            "Requires uncompromised onboard firmware execution on vehicle ECU"
        ],
        [
            "EVID-05", "Zero safety invariant violations across 10,000 Monte Carlo trials",
            "10,000 random vectors sampled across mass, grade, friction, vis, delay",
            "L6_MODELED", "NO", "NO", "YES", "YES", "YES", "YES",
            "Proves safety within modeled 1D kinematic envelope; does not guarantee mechanical health"
        ],
        [
            "EVID-06", "77.36% reduction in hazardous haul ramp queue waiting time",
            "Measured across 20 matched seeds (625.4 s down to 141.6 s per trip)",
            "L9_SIMULATION", "NO", "NO", "YES", "NO", "YES", "YES",
            "Valid for 6-truck closed-loop fleet on Bailadila Deposit-5 haul road model"
        ],
        [
            "EVID-07", "35.88% steady-state delivered throughput improvement",
            "Delivered TPH increased from 1171.2 to 1591.4 TPH across 20 seeds",
            "L9_SIMULATION", "NO", "NO", "YES", "NO", "YES", "YES",
            "Represents recovery of lost crusher capacity (71.1% to 96.6% utilization of 1647 TPH ceiling)"
        ],
        [
            "EVID-08", "Crusher physical intake ceiling is 1647.0 TPH",
            "Derived from 200 s single tipping pocket cycle (18 dumps/hr x 91.5 t)",
            "L6_ANALYTICAL", "NO", "NO", "NO", "YES", "YES", "YES",
            "Theoretical upper bound for single primary gyratory crusher pocket"
        ],
        [
            "EVID-09", "Dense fog safe crawl speed is 5.12 m/s (18.4 km/h) at 12m visibility",
            "Derived from quadratic stopping envelope with 0.4371s delay and 5m buffer",
            "L6_ANALYTICAL", "NO", "NO", "NO", "YES", "YES", "YES",
            "Assumes dry/nominal friction (mu >= 0.34); reduced to 3.60 m/s under wet slurry"
        ],
        [
            "EVID-10", "Zero speed controlled stop strictly enforced at visibility <= 5.0m",
            "Analytical root yields v_safe = 0.0 m/s when sightline <= S_base (5m)",
            "L6_ANALYTICAL", "NO", "YES", "YES", "YES", "YES", "YES",
            "Haulage is halted when visibility falls within defensive safety buffer"
        ],
        [
            "EVID-11", "Safe Beacon communication failure maintains defensive vehicle motion",
            "Peer timeout triggers SAFE motion state with 2x headway expansion",
            "L7_L6_COMBINED", "YES", "YES", "YES", "NO", "YES", "YES",
            "Separates transport COMM_LOSS from local defensive vehicle motion"
        ],
        [
            "EVID-12", "Frozen sensor value detection is partial on single-channel CAN",
            "Stale frame timeout triggers at 150 ms; static valid float requires plausibility checks",
            "FACT_ARCHITECTURAL", "YES", "YES", "YES", "NO", "YES", "YES",
            "Single-sensor freeze without redundant dual-channel cross-check is only partially detectable"
        ]
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Saved {path}")

def generate_claim_register():
    path = os.path.join(FINAL_DIR, "FINAL_CLAIM_REGISTER.csv")
    headers = [
        "Claim_ID", "Claim_Topic", "Evidence_Level", "Metric", "Result",
        "Scope", "Limitation", "Allowed_Wording", "Forbidden_Wording"
    ]
    rows = [
        [
            "CLM-01", "Hazardous Ramp Waiting Reduction", "L9_SIMULATION", "Hazardous waiting (s/trip)", "-77.36% (-483.8 s)",
            "20 matched seeds, 7200s horizon, 6 trucks, -8% grade", "Waiting is relocated to flat shovel staging bay (+401.0 s)",
            "Hazardous queue waiting on the -8% fog ramp was reduced by 77.36% via proactive staging.",
            "77% improvement in overall mine safety / eliminated all truck waiting."
        ],
        [
            "CLM-02", "Throughput Improvement", "L9_SIMULATION", "Steady throughput (TPH)", "+35.88% (+420.2 TPH)",
            "2-hour shift simulation, 12m fog, single 1647 TPH crusher", "Paces arrivals to match crusher intake; cannot exceed 1647 TPH",
            "Delivered throughput increased by 35.88% (1171.2 to 1591.4 TPH) by eliminating ramp gridlock.",
            "Mine production increased by 36% / throughput was doubled / sustained 3294 TPH."
        ],
        [
            "CLM-03", "Command-Path Latency", "L7_L6_COMBINED", "Electronic latency (ms)", "216.05 ms median",
            "ESP32 TWAI CAN bus + HIL simulated actuator model", "Includes modeled electro-pneumatic actuator delay (200 ms)",
            "HIL command-path latency was characterized at 216.05 ms median under the configured model.",
            "Physical vehicle braking response is 216 ms / truck stops in 216 ms."
        ],
        [
            "CLM-04", "RF Communication Reliability", "L7_BENCH_MEASURED", "Packet delivery ratio (%)", "99.1% PDR",
            "Dual ESP32 SX1278 LoRa bench testbed over 150m outdoor LOS", "Valid only in direct outdoor line-of-sight without mine clutter",
            "99.1% packet delivery ratio was measured in the specified SX1278 outdoor LOS bench test.",
            "99.1% reliable mine-wide communication / wireless operates through rock and iron ore."
        ],
        [
            "CLM-05", "Safety Invariant Adherence", "L6_MODELED", "Safety violations (count)", "0 violations in 10,000 trials",
            "Monte Carlo parameter space (mass, grade, friction, vis, delay)", "Applies strictly to 1D kinematic model; mechanical brake health unmeasured",
            "Zero modeled safety invariant violations across 10,000 Monte Carlo scenarios.",
            "Zero collision risk in real mines / mathematically proven 100% collision-free."
        ],
        [
            "CLM-06", "CAN / TWAI Bus Protocol", "L7_BENCH_MEASURED", "Frame encoding / decode", "100% valid decoding",
            "ESP32 TWAI peripheral with 6 project-defined J1939-style PGNs", "Not integrated into factory OEM wiring harness of physical BH100",
            "Validated project-defined J1939-style HIL frames over ESP32 TWAI at 250 kbps.",
            "BH100 J1939 factory integration certified / OEM engine ECU directly controlled."
        ],
        [
            "CLM-07", "Blindout Safety Stop", "L6_ANALYTICAL", "Safe speed at vis <= 5m", "v_safe = 0.0 m/s (Halt)",
            "Deterministic quadratic stopping root where R_eff <= S_base (5m)", "Production ceases during extreme zero-visibility blindout",
            "Vehicles are commanded to a controlled halt when visibility drops to 5m or below.",
            "System maintains high-speed autonomous haulage through zero-visibility fog."
        ],
        [
            "CLM-08", "Safe Beacon Fail-Safe", "L7_L6_COMBINED", "Motion state on comm loss", "SAFE_DEFENSIVE (2x headway)",
            "Communication failover state machine across 4 network tiers", "Throughput derated to defensive convoy limits during total comm loss",
            "Total communication failure triggers local safe defensive crawl with 2x headway expansion.",
            "Comms loss causes truck to disappear / comms loss crashes fleet / comms loss permits runaway."
        ]
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Saved {path}")

def generate_contradiction_register():
    path = os.path.join(FINAL_DIR, "FINAL_CONTRADICTION_REGISTER.csv")
    headers = [
        "Contradiction_ID", "Parameter_Or_Metric", "Old_Value", "New_Canonical_Value",
        "Source_Of_Discrepancy", "Why_Changed", "Final_Canonical_Status"
    ]
    rows = [
        [
            "CONT-01", "Safe Speed in 12m Fog", "5.1158 / 5.256 / 4.3815 m/s", "5.12 m/s (18.4 km/h)",
            "Different latency assumptions (0.8s vs 0.4371s) and decimal truncation",
            "Standardized on 0.4371s P99 latency budget and a_dec = 2.7856 m/s^2",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-02", "Emergency Deceleration", "2.7466 m/s^2", "2.7856 m/s^2",
            "Legacy model used Crr=0.02, g=9.81, mass=165.0t; canonical uses Crr=0.025, g=9.80665, mass=165.5t",
            "Derived from authoritative force balance with BEML BH100 tare+payload mass",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-03", "Service Deceleration", "2.7466 m/s^2 (used for both)", "1.20 m/s^2",
            "Early phases conflated emergency full braking with comfortable service braking",
            "Separated emergency stopping limit from comfortable service deceleration assumption",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-04", "BEML BH100 Gross Mass", "165,000 kg", "165,500 kg",
            "Generic 165t round number vs BEML brochure (74.0 t tare + 91.5 t rated payload)",
            "Adopted exact OEM rated gross vehicle weight of 165,500 kg",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-05", "BEML BH100 Rated Payload", "91,000 kg", "91,500 kg (91.5 tonnes)",
            "Informal rounding in early documentation",
            "Locked to official BEML BH100 spec sheet (91.5 metric tonnes nominal)",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-06", "Space Headway in Fog", "17.52 m", "22.52 m",
            "Early calculation omitted vehicle body length (S_stop 7.0m + S_base 5.0m + 5.5m bumper)",
            "Corrected to full formula: H = S_stop (6.99m) + S_base (5.0m) + L_truck (10.525m) = 22.52m",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-07", "Road Capacity Kinematic Flux", "700.5 VPH", "817.8 VPH (emergency) / 587.2 VPH (service)",
            "Calculated using legacy 4.38 m/s speed vs canonical 5.12 m/s and service 3.61 m/s",
            "Classified as theoretical kinematic flux: C = 3600*v/H; explicitly decoupled from mine TPH",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-08", "Peak Mine Throughput", "3294.0 TPH / 2745.0 TPH", "1591.4 TPH steady-state (1647 TPH ceiling)",
            "10-minute flush transient (6 trucks pre-dumped in 10 min = 3294 TPH) mislabeled as sustained",
            "Retracted transient burst; locked steady-state throughput to 1591.4 TPH across 2-hour shift",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-09", "Hazardous Ramp Waiting Reduction", "77.4% vs 77.36%", "77.36% (from 625.4s to 141.6s)",
            "Rounding discrepancy between presentation slides and raw CSV output",
            "Locked to 77.36% (or 77.4% rounded); noted waiting relocation to flat staging bay (+401.0s)",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-10", "End-to-End Latency Claim", "216.05 ms vs 437.1 ms vs 475 ms", "216.05 ms HIL command / 437.1 ms budget",
            "Conflating measured electronic command path (216 ms) with worst-case safety budget (437 ms)",
            "Decomposed: T_physical_measured = 13.8 ms, T_modelled = 202.2 ms, T_budget = 437.1 ms",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-11", "LoRa PDR vs Fault Loss", "99.1% PDR vs 75% packet loss injection", "99.1% baseline bench PDR / 75% fault tolerance",
            "Reported 99.1% physical bench PDR in one section and 75% synthetic loss tolerance in another",
            "Clarified: 99.1% is clean bench baseline; 75% is an injected fault scenario survived without violation",
            "RESOLVED_CANONICAL"
        ],
        [
            "CONT-12", "Blindout Stopping Behavior", "Slow crawl vs complete halt", "0.0 m/s (Complete Controlled Halt)",
            "Early code permitted crawl at 3-5m visibility",
            "Audited quadratic root: R_eff <= S_base (5m) leaves zero stopping margin, forcing v_safe = 0.0 m/s",
            "RESOLVED_CANONICAL"
        ]
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Saved {path}")

def main():
    generate_hardware_evidence_matrix()
    generate_evidence_matrix()
    generate_claim_register()
    generate_contradiction_register()
    print("All 4 CSV registers generated successfully in FINAL/")

if __name__ == "__main__":
    main()
