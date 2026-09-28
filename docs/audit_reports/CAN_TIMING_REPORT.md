# CAN_TIMING_REPORT.md
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**

*(See comprehensive detailed report in [03_CAN_TIMING_REPORT.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/03_CAN_TIMING_REPORT.md))*

### Summary CAN Timing Statistics (250 kbps TWAI / 10,000 cycles)
- **Minimum Latency:** 0.512 ms
- **Mean Latency ($\mu$):** 6.302 ms
- **Median Latency ($P_{50}$):** 5.820 ms
- **95th Percentile ($P_{95}$):** 22.410 ms
- **99th Percentile ($P_{99}$):** 50.000 ms
- **Maximum Latency:** 54.820 ms
- **Jitter ($\sigma$):** 4.815 ms
- **Dropped Frames:** 0 (0.0%)
- **Duplicate Frames:** 0
- **Out-of-Order Frames:** 0
- **Timeouts:** 0 under nominal operation
- **Actuator Acknowledgment:** `NOT MEASURED — HARDWARE LIMITATION` (BEML BH100 hydraulic valve uninstrumented; 250 ms modeled per ISO 3450).
