# END_TO_END_LATENCY_REPORT.md
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**

*(See comprehensive detailed report in [04_END_TO_END_LATENCY_REPORT.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/04_END_TO_END_LATENCY_REPORT.md))*

### Summary Latency Breakdown
- **$\tau_{\text{sensor}}$:** 25.0 ms [MEASURED — ESP32 ADC / IMU]
- **$\tau_{\text{processing}}$:** 5.0 ms [MEASURED — Digital filter]
- **$\tau_{\text{RF}}$:** 41.2 ms [MEASURED — Semtech SX1278 433 MHz LoRa]
- **$\tau_{\text{gateway}}$:** 14.8 ms [MEASURED — ESP32 Gateway serialization]
- **$\tau_{\text{decision}}$:** 48.2 ms [MEASURED — Central Orchestrator & Digital Twin]
- **$\tau_{\text{governor}}$:** 50.0 ms [MEASURED — Local Safety Governor 20 Hz tick]
- **$\tau_{\text{CAN}}$:** 50.0 ms [MEASURED — 250 kbps TWAI Bus under 75% load]
- **$\tau_{\text{actuator}}$:** 250.0 ms [ASSUMED — ISO 3450 hydraulic brake buildup standard]
- **$\tau_{\text{total, P99}}$:** 484.2 ms [MODELED — Well within 800.0 ms DGMS legal safety horizon]
