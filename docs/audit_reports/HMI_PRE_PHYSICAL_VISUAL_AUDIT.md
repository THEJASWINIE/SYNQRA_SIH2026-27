# HMI_PRE_PHYSICAL_VISUAL_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Pre-Physical Hostile Audit: HMI Layout, Provenance & Safety Truth

**Date:** 2026-09-27  
**Authoritative Status:** **PASS (PRE-PHYSICAL AUDIT & RE-ALIGNMENT COMPLETE)**  
**Classification:** L1 (Source Code Inspection) + L2 (Automated Test Verification) + Rendering Audit  
**Rule Compliance:** AGENTS.md Rules 3, 4, 5, 6, 7, 8, 9, 11, 12 ("One authoritative Digital Twin", "Frontend must not invent vehicle state", "Safety remains authoritative", "Explicit units", "Zero fabrication")

---

### 1. Executive Summary & Defect Disclosure

This audit subjects both the **Operator HMI (`DriverScreen.tsx`)** and the **Control Room HMI (`OperationsOverview.tsx`)** to a rigorous panel-by-panel interrogation across utility, truthfulness, provenance, SI units, freshness observability, and safety governor distinction.

#### Critical Provenance Vulnerability Discovered & Fixed:
* **The Defect (False LIVE Status on MOCK Provider):**
  In `OperationsOverview.tsx` (line 112), the topbar status pill computed feed text as:
  ```tsx
  const isReplay = state.connection.provider === "REPLAY";
  const isConnected = state.connection.status.toUpperCase() === "CONNECTED";
  const feedStateText = isReplay ? "REPLAY ▶" : isConnected ? "LIVE ●" : "DISCONNECTED ○";
  ```
  If `state.connection.provider === "MOCK"`, but the internal mock store connection status was `"CONNECTED"`, the HMI displayed `"LIVE ●"` with `data-feed="LIVE"`. This violated Non-Negotiable Rule 3 (*Never fabricate telemetry / explicitly identify SIMULATION/MOCK*).
* **Fix Applied:**
  Updated `OperationsOverview.tsx` to strictly isolate MOCK and DISCONNECTED states:
  ```tsx
  const isReplay = state.connection.provider === "REPLAY";
  const isMock = state.connection.provider === "MOCK";
  const isConnected = state.connection.status.toUpperCase() === "CONNECTED";
  const feedStateText = !isConnected
    ? "DISCONNECTED ○"
    : isReplay
      ? "REPLAY ▶"
      : isMock
        ? "MOCK ◌"
        : "LIVE ●";
  const feedDataAttr = !isConnected ? "DISCONNECTED" : isReplay ? "REPLAY" : isMock ? "MOCK" : "LIVE";
  ```
  Now MOCK is clearly rendered as `"MOCK ◌"` and never masquerades as `"LIVE ●"`.

---

### 2. The 10-Question Panel Interrogation

Every panel across both HMIs was evaluated against the 10 hostile questions:
1. *Is this useful?*
2. *Is the value real (authoritative from backend/twin)?*
3. *Is provenance visible?*
4. *Is the unit correct (SI units: m/s, km/h, m, % grade)?*
5. *Is the update rate clear?*
6. *Is stale data visually obvious?*
7. *Is the panel duplicating another panel?*
8. *Is there unused space filled with decorative fluff?*
9. *Is important safety information buried?*
10. *Is anything presented as LIVE when it is actually simulation?*

---

### 3. Detailed Inspection: Operator HMI (`DriverScreen.tsx`)

| Panel / Element | Content Displayed | Provenance / Backend Source | Unit | Stale Behavior | Truthfulness & Honesty Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Current Speed** | Large tactile readout | `projection.vehicle.speed` (canonical odometry / telemetry) | km/h (derived from m/s) | Amber warning if age $> 1.0\text{ s}$ | **PASS** — Live measured ground speed |
| **Command Requested** | Dispatch target speed | `projection.dispatch.targetSpeed` | km/h | Shows `UNAVAILABLE` if no dispatch | **PASS** — Explicitly labeled as REQUESTED |
| **Safe Limit ($v_{\text{safe}}$)** | Governor clamp ceiling | `projection.safety.vSafe` | km/h | Red badge if speed $> v_{\text{safe}}$ | **PASS** — Authoritative physics clamp |
| **Command Applied** | Actual PWM motor drive | Hardware actuator feedback | N/A | **Explicitly labeled: `UNKNOWN / NOT TELEMETRIED`** | **PASS** — Refuses to fabricate motor speed without physical current sensor |
| **Sensor Health — Encoder** | Status & measured RPM | `projection.provenance.rpm.value` | RPM | "STANDBY / NO TICKS" when stationary | **PASS** — Ground truth pulse rate |
| **Sensor Health — IMU** | MPU6050 3-axis accel/gyro | `projection.provenance.ax_mps2.value` | m/s² | "UNAVAILABLE" if I2C fails | **PASS** — Authentic accelerometer health |
| **Sensor Health — GNSS** | GNSS / GPS status | None (no GNSS module on chassis) | N/A | **Explicitly labeled: `NOT FITTED ON CHASSIS`** | **PASS** — Honest hardware disclosure |
| **Failover & Redundancy** | Primary Link, LoRa, RF Failover | `projection.communication` | Status | Amber if degraded; RF Failover labeled `NOT VERIFIED` | **PASS** — Refuses to claim failover verified |
| **Safe Beacon** | Failsafe broadcast state | `vehicle.safeBeaconActive` | Enum | Labeled `ACTIVE` or `SOFTWARE READY · FIELD GATE PENDING` | **PASS** — Reflects open physical gate |
| **Diagnostics** | Firmware, Boot ID, Sequence | `provenance.boot_id`, `provenance.sequence` | Integer | Live session telemetry counters | **PASS** — Direct NVS session lineage |

---

### 4. Detailed Inspection: Control Room HMI (`OperationsOverview.tsx`)

| Panel / Element | Content Displayed | Provenance / Backend Source | Unit | Truthfulness & Honesty Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Topbar Status Pill** | Feed mode & connection | `state.connection.provider`, `state.connection.status` | Tag | **PASS** — Fixed: MOCK renders as `MOCK ◌`, REPLAY as `REPLAY ▶`, LIVE only when hardware connected |
| **Fleet Twin Count** | Vehicles in authoritative Twin | `state.twin.vehicles.length` | Count | **PASS** — Reflects authoritative store vehicles |
| **Mine-Site 2D/3D Map** | Geo-spatial vehicle poses | `resolveVehiclePosition(vehicle, provider, extent)` | Coordinates | **PASS** — Real coordinates, unplaced vehicles cleanly shown in unplaced queue |
| **Command & Governor** | Requested, Safe Limit, Applied, Governor Status | Central Dispatch + Tier-1 Physics Governor | km/h | **PASS** — Applied Speed labeled `UNKNOWN / NOT TELEMETRIED`; Governor Status shows `ACTIVE INTERVENTION` |
| **RF Failover & Redundancy** | Primary (Wi-Fi), Redundant (LoRa), Protocol, Beacon | Gateway Ingestion & Health Store | Enum | **PASS** — RF Failover labeled `NOT VERIFIED (PROTOCOL OPEN)`; Safe Beacon labeled `SOFTWARE READY · FIELD GATE PENDING` |
| **Sensor Health & Diagnostics** | Encoder RPM, IMU MPU6050, GNSS, Boot ID, Sequence | Live telemetry payload provenance | SI units / IDs | **PASS** — GNSS explicitly labeled `NOT FITTED ON CHASSIS`; Boot ID and Sequence displayed |
| **Haul Roads & Pit Morphology** | Grade %, speed limits, road status | Canonical Bailadila mine network model | % Grade, m | **PASS** — Authoritative static road network geometry |

---

### 5. Safety Truth Attack: Governor Distinction Audit

The audit strictly verified that neither HMI conflates the five distinct speed quantities:

```text
[Central Dispatcher]
        │
        ▼
1. COMMAND REQUESTED (e.g. 10.0 m/s)
        │
        ▼
   [Tier-1 Safety Solver] ◄─── Fog Visibility, Grade, Traction
        │
        ▼
2. SAFE LIMIT (v_safe) (e.g. 4.2 m/s)
        │
        ▼
   [Command Gateway] ─── min(v_dispatch, v_safe)
        │
        ▼
3. COMMAND ACCEPTED (4.2 m/s)
        │
        ▼
   [ESP32 Motor Driver TB6612FNG]
        │
        ▼
4. COMMAND APPLIED (PWM Drive)
   --> AUDIT RESULT: UNKNOWN / NOT TELEMETRIED (No current shunt feedback fitted)
        │
        ▼
   [Physical Wheel & Track]
        │
        ▼
5. ACTUAL VEHICLE STATE (Canonical odometry from LM393 optical pulses)
```

**Compliance Verification:**
- Both `DriverScreen.tsx` and `OperationsOverview.tsx` clearly separate **Command Requested** from **Safe Limit**.
- Both HMIs explicitly display **`UNKNOWN / NOT TELEMETRIED`** for **Command Applied**, refusing to invent or mirror PWM command values as measured motor speed.
- Actual vehicle speed is exclusively derived from measured optical pulses ($K_{\text{cal}} = 34.58\text{ pulses/rev}$).

---

### 6. Audit Verdict: PASS (HMI CODE & VISUAL TRUTH COMPLETE)

- Zero decorative placeholder charts.
- Zero synthetic values masquerading as LIVE.
- Fixed MOCK provider bug in `OperationsOverview.tsx`.
- All unmeasured fields honestly labeled (`UNKNOWN / NOT TELEMETRIED`, `NOT FITTED ON CHASSIS`, `FIELD GATE PENDING`).
- All 1860 frontend tests passing (`71 / 71 test files`).
