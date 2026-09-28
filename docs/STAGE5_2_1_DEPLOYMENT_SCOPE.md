# STAGE 5.2.1: FIELD DEPLOYMENT SCOPE & GAP AUDIT
**Separating Architectural Deployability from Real-World Field Validation at NMDC Bailadila**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Complex)  
**Status:** EVIDENCE INTEGRITY GATE — OBJECTIVE MATURITY CLASSIFICATION  

---

## 1. Executive Forensic Question

In technical presentations, the claim **"System is deployable to NMDC"** is frequently made.

This audit establishes a rigorous distinction between:
1. **Architectural Deployability:** The system’s schemas, data contracts, physical calibration, and software interfaces are strictly modeled on NMDC Bailadila Deposit 5 / Deposit 14 mine topologies and Caterpillar 777G dumpers.
2. **Field Deployment Validation:** The system has been physically installed and operated inside an active, deep-pit iron ore mine with real heavy earthmoving machinery (HEMM).

### Forensic Verdict:
> ### **VERDICT: ARCHITECTURALLY DEPLOYABLE — FIELD UNVALIDATED**
> **FOG-ORCHESTRATOR 2.0 has achieved comprehensive architectural and prototype hardware validation. However, it has NOT undergone deep-pit in-situ field trials at NMDC Bailadila. Claiming that the system is "field-ready" or "mine-validated" is false and prohibited.**

---

## 2. Deployment Readiness & Evidence Classification

We systematically audit the 12 core engineering layers required for full-scale commercial deployment in an open-cast iron ore mine:

| Operational Subsystem | Target Industrial Requirement (NMDC Bailadila) | Current Implementation Level | Evidence Class | Validation Gap / Outstanding Work |
| :--- | :--- | :--- | :---: | :--- |
| **1. Vehicle Dynamics & Mass** | Caterpillar 777G ($74\text{ t}$ tare, $91.5\text{ t}$ payload, $165.5\text{ t}$ gross) | Fully calibrated in `vehicle.yaml` and `BrakingModel` | **CLASS A (Sim)** | Calibrated to OEM specs; field validation on active dumper telematics pending. |
| **2. Road Geometry & Topography** | Bailadila Deposit 5 layout ($1{,}850\text{ m}$, $+6.25\%$ ramp, $-8.0\%$ switchback) | Surveyed coordinates in `nodes.yaml` and `roads.yaml` | **CLASS A (Sim)** | Digital Twin topology verified against mine maps; RTK drone LiDAR survey pending. |
| **3. Wet Road Friction** | Monsoon rain-slicked hematite clay ($\mu = 0.35$, $\mu_{\text{safe}} = 0.282$) | Modeled continuously in `FrictionModel` | **CLASS A (Sim)** | Deceleration verified in simulation; skid-pad decelerometer field tests pending. |
| **4. Direct V2V Communication** | Sub-GHz peer-to-peer telemetry between haulers | Direct LoRa SX1278 peer broadcast ($433\text{ MHz}$) | **CLASS B (HW)** | Validated on bench ESP32 hardware; deep-pit $200\text{ m}$ bench multipath testing required. |
| **5. Central Gateway Uplink** | Serial/Wi-Fi aggregation from gateway to server | LoRa Gateway ESP32 $\to$ Wi-Fi $\to$ FastAPI backend | **CLASS B (HW)** | Validated on local network; mine-wide LTE/Private 5G backhaul integration pending. |
| **6. Local Safety Governor** | Fail-safe speed clamping directly at vehicle actuator | Tier-1 local governor algorithm in ESP32 firmware | **CLASS B (HW)** | Tested via PWM motor emulator; requires physical J1939 CAN-bus brake ECU interface. |
| **7. Positioning & Odometry** | High-precision vehicle tracking on narrow switchbacks | Modeled wheel odometry and spatial dead-reckoning | **CLASS A (Sim)** | Real deployment requires multi-constellation RTK-DGPS with base station corrections. |
| **8. Environmental Sensing** | Real-time optical visibility measurement along ramps | Discrete visibility injection ($100\text{ m} \to 3\text{ m}$) | **CLASS A (Sim)** | Real deployment requires physical optical transmissometers / forward-scatter sensors. |
| **9. In-Cab Operator HMI** | Clear visual/audio speed guidance under cab vibration | Web-based responsive Operator HMI (FastAPI/React) | **CLASS B (HW)** | UI contract validated; ruggedized IP67 anti-glare vehicle mount display required. |
| **10. Central Technician HMI** | Full fleet supervisory dispatch and bottleneck monitor | React Control Room HMI + 3D Pygame Digital Twin | **CLASS B (HW)** | Fully operational against live FastAPI/WebSocket backend; control-room tested. |
| **11. Electrical & Environmental** | Heavy vibration, dust, extreme monsoon downpours | Lab-grade ESP32 development boards | **CLASS C (Field Gap)** | Industrial IP67 / NEMA 4X enclosures and DGMS intrinsic safety certification required. |
| **12. Regulatory Certification** | Directorate General of Mines Safety (DGMS) compliance | Architecture enforces fail-safe Tier-1 local veto | **CLASS C (Field Gap)** | Formal DGMS India statutory testing and mine safety approval required before live use. |

---

## 3. The 3 Evidence Classes

All project claims must be explicitly assigned to one of these three classes:

- **CLASS A — SIMULATION PROVEN:**
  The physics of stopping sight distance, grade deceleration, single-lane switchback queueing, multi-vehicle car-following, and dynamic fog progression have been mathematically and computationally validated across thousands of timesteps and multiple deterministic seeds.
- **CLASS B — HARDWARE / PROTOTYPE PROVEN:**
  The peer-to-peer LoRa V2V communication protocol (`STATE,TRUCK_01,seq...`), packet serialization, gateway bridging, FastAPI REST/WebSocket ingestion, and frontend HMI presentation have been verified on physical ESP32 microcontrollers and networked hosts.
- **CLASS C — FIELD UNVALIDATED:**
  Operation inside an active open-cast iron ore mine, exposure to Bailadila's vertical high-wall RF shadows, physical interface to Caterpillar 777G brake controllers, and formal DGMS regulatory approval remain unexecuted.

---

## 4. Mandatory Wording for SIH 2026-27

In all interactions with judges, evaluators, and NMDC officials, use the following formulation:

> *"FOG-ORCHESTRATOR 2.0 is an architecturally complete, hardware-bench-validated prototype designed specifically for NMDC Bailadila haulage parameters. The core software, physics solvers, communication protocols, and operator interfaces are fully functional. The next required phase of development is an on-site pilot trial at Bailadila to evaluate deep-pit LoRa RF propagation and interface with commercial J1939 vehicle CAN bus ECUs."*
