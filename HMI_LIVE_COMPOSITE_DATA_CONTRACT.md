# FOG-ORCHESTRATOR 2.0 — HMI LIVE COMPOSITE DATA CONTRACT MATRIX

**Date**: 2026-08-29  
**Author**: Principal Systems Architect, HMI Data Layer Engineer, Software Verification Engineer  
**Scope**: Composition Matrix for HMI Frontend Data Contract Slices in LIVE and MOCK Modes

---

## 1. Executive Summary & Data Composition Strategy

The HMI Frontend requires a complete, multi-slice data contract to render mine operations (`MineMap`, `MineTopology`, `VehicleState`, `RoadState`, `VisibilityForecast`, `BottleneckState`, `DispatchCommand`, `Alert`, `SystemHealth`, `FreshnessConfig`).

Enabling `VITE_PROVIDER=live` MUST NOT replace non-hardware scenario/twin data with an empty store. Instead, the HMI Data Layer composes:
```text
LIVE HMI STATE = 
  EXISTING SCENARIO / TOPOLOGY / FOG / BOTTLENECK / DISPATCH DATA (Authoritative Twin Baseline)
  +
  REAL PHYSICAL ESP32 VEHICLE TELEMETRY (Live Hardware Stream via WebSocket)
```

---

## 2. HMI Composite Data Contract Matrix

| Data Slice / Field | Live Mode Data Source | Mock Mode Data Source | Physical vs Software | Fallback / Recovery Mechanism |
|---|---|---|---|---|
| **Vehicles** (`vehicles`) | Live ESP32 Wi-Fi / V2V Backend Stream (`POST /api/hardware/telemetry`) | Local Authored Scenario (`MockDataProvider`) | **Physical Hardware** | Stale / Offline timeout ($\le 3\text{ s}$ ONLINE, $>10\text{ s}$ OFFLINE). Non-hardware scenario baseline if stream inactive. |
| **Mine Topology** (`topology`) | Authoritative Scenario / Twin Baseline (`MineTopology` step) | Authored Scenario File (`nominal.json`) | **Software Model** | Retains mine geometry, nodes, and segments even when hardware telemetries drop. |
| **Mine Map** (`mine_map`) | Authoritative Scenario / Twin Topology Renderer | Authored Scenario Renderer | **Software Model** | Rendered statically from topology nodes/segments. Never requires ESP32 geometry. |
| **Fog / Visibility** (`road`, `forecasts`) | Authoritative Fog Model (`VisibilityForecast`, `RoadState`) | Authored Fog Scenario (`fog-rolling-in.json`) | **Software Model** | Preserved from twin/scenario propagation model. |
| **Bottlenecks / Queues** (`bottlenecks`) | Authoritative Bottleneck Detector (`BottleneckState`) | Authored Bottleneck Scenario | **Software Model** | Preserved from twin bottleneck detector. |
| **Dispatch Commands** (`dispatch`) | Authoritative Orchestrator (`DispatchCommand`) | Authored Dispatch Scenario | **Software Model** | Supervisory dispatch commands routed to ESP32 vehicles; advisory UI state maintained. |
| **Alerts & Events** (`alerts`, `events`) | Live Telemetry Quality & Safety Filter + Twin Alerts | Authored Scenario Alerts | **Composite Software/Hardware** | Hardware comm loss generates degraded alerts; safety alerts remain non-overrideable. |
| **System Health** (`health`) | Backend Liveness Endpoint (`/api/health`) + `SystemHealth` | Mock System Health | **Composite** | Backend connectivity indicator (`CONNECTED` / `DISCONNECTED`). |
| **Freshness Threshold** (`freshness`) | `VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS=3000` ($3.0\text{ s}$) | Authored Config / Injected Test Threshold | **Software Config** | Exposes $3000\text{ ms}$ threshold matching backend STALE boundary ($3\text{ s}$). |
| **System Mode** (`mode`) | Backend Dynamic Mode Calculation (`"LIVE"` when hardware active) | Fixed Scenario Mode (`"MOCK"`) | **Backend State** | Transitions `"LIVE"` $\leftrightarrow$ `"MOCK"` dynamically based on physical telemetry age. |

---

## 3. Physical vs Baseline Source Precedence Rules

1. **Vehicle Telemetry Priority**:
   - `PHYSICAL LIVE TELEMETRY` > `MOCK VEHICLE TELEMETRY`.
   - While `TRUCK_01` or `TRUCK_02` physical stream is active ($age \le 10.0\text{ s}$), physical parameters (`sequence_number`, `rpm`, `speed`, `ax`, `ay`, `az`, `gx`, `gy`, `gz`, `rssi`, `snr`, `communication_status`) override mock vehicle state.
2. **Mine Geometry & Environment Priority**:
   - `AUTHORITATIVE SCENARIO / TWIN BASELINE` > `NONE`.
   - Topology, mine map, fog propagation, queues, bottlenecks, and supervisory dispatch commands NEVER disappear or wipe out when switching to `LIVE` mode.

---

## 4. Verification Evidence

- **99/99 Pytest Tests PASSED**
- **5/5 Master Regression Suites PASSED** (`FINAL MASTER REGRESSION VERDICT: PASS`)
- **Backend Port 8000 Binding**: `0.0.0.0:8000`
- **Frontend Environment**: `VITE_PROVIDER=live`, `VITE_LIVE_WS_URL=ws://10.126.54.41:8000/api/ws`, `VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS=3000`.
