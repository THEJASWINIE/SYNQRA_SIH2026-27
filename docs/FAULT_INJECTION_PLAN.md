# FAULT INJECTION & ADVERSARIAL STRESS TEST PLAN
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phases H1–H10**  
**Lead Safety-Critical Systems & CPS Integration Engineer**  
**Document Revision:** 1.0  
**Date:** 2026-09-24  

---

## 1. Objective & Scope

This document specifies the formal test procedures, injection harnesses, and pass/fail criteria for the **20 Mandatory System Faults (F01–F20)** required for complete end-to-end integration certification.

The objective is to prove that **every possible failure in sensing, computing, networking, and actuation results in a deterministic, observable, and fail-safe response**.

---

## 2. Fault Injection Taxonomy (F01–F20)

| ID | Fault Category | Specific Fault Injected | Injection Point / Mechanism | Expected Detection Time |
| :---: | :--- | :--- | :--- | :---: |
| **F01** | Communication | Periodic RF Packet Loss (20% dropped) | Software packet drop filter on LoRa queue | $< 200\text{ ms}$ |
| **F02** | Communication | Complete RF Severance (100% loss) | Radio silence / hardware antenna disconnected | $500.0\text{ ms}$ |
| **F03** | Infrastructure | Gateway Disappearance (Power outage) | Gateway process SIGKILL; zero downlinks | $500.0\text{ ms}$ |
| **F04** | Infrastructure | Gateway Handover Flapping | Injected Rayleigh noise $\sigma \ge 0.15$ on candidate GW | $< 100\text{ ms}$ |
| **F05** | Telemetry | Stale Telemetry Injection | Replay old packets with frozen timestamps ($>300\text{ ms}$) | $< 50\text{ ms}$ |
| **F06** | Telemetry | Duplicate Telemetry Packet Injection | Re-transmit identical sequence number ($seq_k = seq_{k-1}$) | $< 10\text{ ms}$ |
| **F07** | Telemetry | Out-of-Order Telemetry Injection | Invert sequence order ($seq = 105$ before $104$) | $< 10\text{ ms}$ |
| **F08** | Sensing | Optical Encoder Failure (Zero pulses) | Hardware pulse pin disconnected / simulated 0 PPR | $< 100\text{ ms}$ |
| **F09** | Sensing | Optical Transmissometer Missing | Telemetry payload missing `visibility` field | $< 50\text{ ms}$ |
| **F10** | Sensing | Optical Transmissometer Stuck | Frozen floating-point value repeated $N > 10$ cycles | $200.0\text{ ms}$ |
| **F11** | Sensing | Sensor Outlier (Spike Injection) | Accelerometer spike $a_x > 25\text{ m/s}^2$ | $< 20\text{ ms}$ |
| **F12** | Sensing | Sensor Inconsistency (Wheel vs. IMU) | Wheel speed $1.4\text{ m/s}$, IMU integrated speed $0.1\text{ m/s}$ | $< 80\text{ ms}$ |
| **F13** | Distributed | Digital Twin Process Crash | Backend process killed with `kill -9` | $< 200\text{ ms}$ |
| **F14** | Distributed | Backend WebSocket Severance | Client-side socket close / TCP RST injection | $< 100\text{ ms}$ |
| **F15** | Command | Command Expiration Timeout | Dispatch frame with timestamp $t_{\text{now}} - 1.5\text{ s}$ | $< 10\text{ ms}$ |
| **F16** | Controller | CAN / TWAI Watchdog Silence | Physical severance of CAN_H / CAN_L lines | $150.2\text{ ms}$ |
| **F17** | Resilience | Safe Beacon Transmitter Failure | Beacon transceiver fails to strobe during comm loss | $< 200\text{ ms}$ |
| **F18** | Controller | Vehicle Controller Link Loss | ESP32 serial / UART cable disconnected | $< 150\text{ ms}$ |
| **F19** | Emergency | Hardware E-Stop Depressed | GPIO 13 (TB6612 STBY) pulled LOW | $< 5\text{ ms}$ |
| **F20** | Recovery | Communication Recovery Handshake | Link restored; test 5-packet persistence requirement | $\ge 2.5\text{ s}$ |

---

## 3. Detailed Injection Harness & Verification Workflow

### 3.1 RF & Gateway Injections (F01–F04)
- **Harness:** `integration_adapters/dsss_gateway_selector.py` & `esp32_code/LORA_GATEWAY_RECEIVER/`.
- **Pass Criteria:**
  - In F01, system enters `DEGRADED`, increases headway $h_{\text{safe}}$ by $+20\%$, and does not trigger spurious emergency stops.
  - In F02 and F03, system enters `COMMUNICATION_LOSS` at exactly $500\text{ ms}$, engages `SAFE_BEACON_ACTIVE`, and reverts to `LOCAL_SAFE_MODE`.
  - In F04, gateway selector hysteresis (`SWITCH_MARGIN = 0.18`) suppresses flapping.

### 3.2 Telemetry Ingestion Injections (F05–F07)
- **Harness:** `telemetry_ingest.py` & `integration_adapters/telemetry_quality_filter.py`.
- **Pass Criteria:**
  - Duplicate sequence numbers dropped immediately with error counter incremented.
  - Out-of-order packets held in reorder buffer or rejected if outside window.
  - Stale timestamps flagged with `is_stale: true`; speeds not trusted for dispatch.

### 3.3 Sensor Health Injections (F08–F12)
- **Harness:** `integration_adapters/environmental_data_health.py`.
- **Pass Criteria:**
  - Encoder failure detected via cross-check with IMU acceleration within $100\text{ ms}$.
  - Missing visibility defaults to conservative floor ($R_{\text{eff}} = 8.0\text{ m}$).
  - Inconsistent wheel/IMU triggers `INCONSISTENT` and adopts minimum speed.

### 3.4 Command & Watchdog Injections (F15–F19)
- **Harness:** `integration_adapters/fail_safe_controller.py` & `integration_adapters/can_twai_hil.py`.
- **Pass Criteria:**
  - CAN silence $> 150\text{ ms}$ engages immediate active dynamic braking.
  - E-Stop pin drop stops motors instantaneously ($< 5\text{ ms}$) at hardware level.
  - Remote dispatch commands rejected 100% when vehicle is in `LOCAL_SAFE_MODE`.
