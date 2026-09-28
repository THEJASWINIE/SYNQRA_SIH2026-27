# FOG-ORCHESTRATOR 2.0 — VEHICLE IDENTITY MAPPING AUDIT (AUDIT PART 3)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Identity Compatibility & Mapping between Phase 1 Physical Vehicles (`TRUCK_01`, `TRUCK_02`) and Phase 2 Simulated Mining Fleet (`vehicle_1` .. `vehicle_6`)

---

## 1. Inventory & Naming Comparison

| Dimension | Phase 1 (Physical Hardware) | Phase 2 (Digital Twin Simulation) | Compatibility Status |
|-----------|-----------------------------|-----------------------------------|----------------------|
| **Fleet Scale** | 2 Physical Vehicles | 6 Simulated Heavy Mining Dumpers | **Mismatched Scale** ($2\text{ vs }6$) |
| **Naming Syntax** | `TRUCK_01`, `TRUCK_02` | `vehicle_1` .. `vehicle_6` / `DUMPER_01` .. `DUMPER_06` | **Incompatible Identifiers** |
| **Physical Vehicle A** | 4-wheel differential drive, ESP32, TB6612, LM393 | 165-tonne 6-wheel BEML BH100 mining dumper model | **Physical vs Simulated Model mismatch** |
| **Physical Vehicle B** | 2-wheel drive, ESP32, L298N, LM393 | 165-tonne 6-wheel BEML BH100 mining dumper model | **Physical vs Simulated Model mismatch** |

---

## 2. Conceptual Role Architectural Options

### Option A: Direct Twins (`TRUCK_01` $\leftrightarrow$ `vehicle_1`, `TRUCK_02` $\leftrightarrow$ `vehicle_2`)
- **Concept**: Bind `TRUCK_01` directly to `vehicle_1` state in the Digital Twin. `vehicle_3` through `vehicle_6` remain purely simulated background traffic.
- **Pros**: Direct 1-to-1 mapping for 2 vehicles.
- **Cons**: Scale discrepancy (mass, inertia, acceleration limits) creates physics mismatch if simulation expects 165t dumper response from a small 2kg prototype.

### Option B: Hardware-in-the-Loop (HIL) Agents (RECOMMENDED)
- **Concept**: Physical vehicles `TRUCK_01` and `TRUCK_02` operate as **HIL Agents** inside the mine simulation workspace. An explicit **Vehicle ID Mapper Adapter** translates physical `TRUCK_01` telemetry into `HIL_DUMPER_01` state, normalizing physical speed to scaled mine velocity.
- **Pros**: Preserves simulation integrity, handles fleet scaling gracefully, allows physical hardware testing alongside 4 simulated background dumpers.
- **Cons**: Requires explicit scaling & normalization adapter.

### Option C: Representative Validation Proxies
- **Concept**: Physical vehicles run independently on test bench; Digital Twin subscribes to telemetry only to validate safe speed clamping logic.

---

## 3. Recommended Mapping Architecture

```text
PHYSICAL VEHICLES                 VEHICLE ID MAPPER ADAPTER               DIGITAL TWIN FLEET
┌──────────────────┐             ┌─────────────────────────┐             ┌──────────────────┐
│ TRUCK_01 (4WD)   │────────────>│ TRUCK_01 ➔ HIL_DUMPER_01 │────────────>│ HIL_DUMPER_01    │
│ TRUCK_02 (2WD)   │────────────>│ TRUCK_02 ➔ HIL_DUMPER_02 │────────────>│ HIL_DUMPER_02    │
└──────────────────┘             └─────────────────────────┘             │ SIM_DUMPER_03    │
                                                                         │ SIM_DUMPER_04    │
                                                                         │ SIM_DUMPER_05    │
                                                                         │ SIM_DUMPER_06    │
                                                                         └──────────────────┘
```

### Recommendation Summary:
Adopt **Option B (Hardware-in-the-Loop Agents)** using an explicit **Vehicle ID Mapper Adapter**. Never force raw physical vehicle identity directly into Digital Twin state without translation.
