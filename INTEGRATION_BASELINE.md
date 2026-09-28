# INTEGRATION_BASELINE.md
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety & Fleet Orchestration System
**Phase 9: Hardware + Software Integration**

*(See comprehensive detailed report in [01_INTEGRATION_BASELINE.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/01_INTEGRATION_BASELINE.md))*

### Baseline Summary Matrix
- **Physical Hardware:** 2x ESP32 NodeMCU-32S (Truck 01 & Truck 02) + Semtech SX1278 (Ra-02) 433 MHz LoRa + MPU6050 6-DOF IMU.
- **Physical Gateway:** ESP32 LoRa-to-WiFi Gateway Aggregator transmitting via HTTP POST to `/api/hardware/telemetry`.
- **Modulation Truth:** Physical hardware executes Chirp Spread Spectrum (CSS) LoRa. DSSS is an evaluated architectural research abstraction.
- **Backend Architecture:** FastAPI backend with validated telemetry ingestion (`telemetry_ingest.py`), authoritative Digital Twin state store (`twin_state_store.py`), physics safety engine (`fog_safe/`), and command gateway (`command_gateway.py`).
- **Telemetry Protocols:**
  - V2V over-the-air: `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz[,RSSI=...,SNR=...]`
  - Safe Beacon: `BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>`
  - CAN / TWAI: J1939 250 kbps (PGN 61444, 65265, 61441, 61440, 65281, 65282)
- **Baseline Test Results:** 1047 passed, 1 skipped, 0 failed in 60.29s across 83 test suites.
- **Safety Invariant I1:** $v_{\text{command}} \le v_{\text{safe}}$ strictly holds at all times.
- **Authority:** Local Vehicle Safety Governor is authoritative over any remote or dispatch command.
