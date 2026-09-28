# FOG-ORCHESTRATOR 2.0 — HMI → VEHICLE COMMAND + ACK TEST RESULTS (GATE 3)

**Date**: 2026-08-28  
**Author**: Senior Embedded Systems Verification Engineer, Industrial HMI Validation Engineer  
**Scope**: Gate 3 Reverse Command Path (HMI $\rightarrow$ Backend $\rightarrow$ Gateway $\rightarrow$ LoRa $\rightarrow$ Vehicle) & ACK Verification

---

## 1. Command Verification Matrix

| Test ID | Vehicle ID | Action | Requested Speed | Applied Speed | ACK Status | Command Latency | ACK Latency | Total RTT | Result |
|---------|------------|--------|-----------------|---------------|------------|-----------------|-------------|-----------|--------|
| **CMD-01** | `TRUCK_01` | `TARGET_SPEED` | $5.00\text{ m/s}$ | $5.00\text{ m/s}$ | `ACCEPTED` | $14.20\text{ ms}$ | $14.30\text{ ms}$ | $28.50\text{ ms}$ | **PASS** |
| **CMD-02 (Safety)** | `TRUCK_01` | `TARGET_SPEED` | $25.00\text{ m/s}$ | $10.87\text{ m/s}$ | `CLAMPED` | $14.50\text{ ms}$ | $14.60\text{ ms}$ | $29.10\text{ ms}$ | **PASS** |
| **CMD-03** | `TRUCK_01` | `HOLD` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $13.90\text{ ms}$ | $13.90\text{ ms}$ | $27.80\text{ ms}$ | **PASS** |
| **CMD-04** | `TRUCK_01` | `RELEASE` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $14.10\text{ ms}$ | $14.10\text{ ms}$ | $28.20\text{ ms}$ | **PASS** |
| **CMD-05** | `TRUCK_01` | `STOP` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $13.40\text{ ms}$ | $13.50\text{ ms}$ | $26.90\text{ ms}$ | **PASS** |
| **CMD-06** | `TRUCK_02` | `TARGET_SPEED` | $4.50\text{ m/s}$ | $4.50\text{ m/s}$ | `ACCEPTED` | $14.70\text{ ms}$ | $14.70\text{ ms}$ | $29.40\text{ ms}$ | **PASS** |
| **CMD-07 (Safety)** | `TRUCK_02` | `TARGET_SPEED` | $30.00\text{ m/s}$ | $10.87\text{ m/s}$ | `CLAMPED` | $15.00\text{ ms}$ | $15.10\text{ ms}$ | $30.10\text{ ms}$ | **PASS** |
| **CMD-08** | `TRUCK_02` | `HOLD` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $14.00\text{ ms}$ | $14.00\text{ ms}$ | $28.00\text{ ms}$ | **PASS** |
| **CMD-09** | `TRUCK_02` | `RELEASE` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $13.70\text{ ms}$ | $13.80\text{ ms}$ | $27.50\text{ ms}$ | **PASS** |
| **CMD-10** | `TRUCK_02` | `STOP` | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | `ACCEPTED` | $14.40\text{ ms}$ | $14.40\text{ ms}$ | $28.80\text{ ms}$ | **PASS** |
| **CMD-11 (Dup)** | `TRUCK_01` | `TARGET_SPEED` | $25.00\text{ m/s}$ | $0.00\text{ m/s}$ | `REJECTED` | $6.00\text{ ms}$ | $6.10\text{ ms}$ | $12.10\text{ ms}$ | **PASS** |

---

## 2. Statistical Performance Metrics

- **Command Success Rate**: 100% (10/10 valid commands executed successfully)
- **ACK Correlation Success Rate**: 100% (`command_id` perfectly matched between dispatch and ACK)
- **Mean Round-Trip Latency**: $28.43\text{ ms}$
- **Timeout Rate**: 0.0%
- **Duplicate Command Protection**: Re-issuing an existing `command_id` (e.g. `CMD_102`) returns immediate `REJECTED` status to prevent duplicate hardware execution.

---

## 3. Mandatory Safety Clamping Test Verdict

Requesting an unsafe speed of $25.00\text{ m/s}$ ($90\text{ km/h}$) resulted in:
1. **Applied Speed**: Clamped strictly to $10.87\text{ m/s}$ ($39.13\text{ km/h}$).
2. **ACK Status**: `CLAMPED`.
3. **HMI Display**: The HMI UI displays requested speed ($25.00\text{ m/s}$), applied speed ($10.87\text{ m/s}$), and ACK status (`CLAMPED`).

Gate 3 is **VALIDATED**.
