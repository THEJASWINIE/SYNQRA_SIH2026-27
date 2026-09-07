# MASTER CONFIGURATION AUDIT — FOG-ORCHESTRATOR 2.0
**Document ID**: MCA-2026-09-05  
**Author**: Independent Senior Test Engineer / Validation Architect  
**Evaluation Target**: FOG-ORCHESTRATOR Core, HMI Backend/Frontend, Adapters, and Firmware Configurations  

---

## 1. Executive Summary

This Configuration Audit systematically inventories and classifies every configuration value, network binding, timeout, buffer limit, credential, and environmental constant across the FOG-ORCHESTRATOR codebase.

Every discovered setting is evaluated and assigned exactly one classification:
- **CONFIGURED**: Sourced dynamically via environment variables (`.env` or OS env) or external JSON config files.
- **INTENTIONAL CONSTANT**: Scientifically or architecturally fixed constants (e.g., standard gravity, vehicle kinematic limits, mining regulations, network security buffer thresholds).
- **TEST FIXTURE**: Scoped exclusively to test suites, mock runners, or integration verification harnesses.
- **DEMO-ONLY**: Hardcoded values used strictly for synthetic demonstration scenarios or simulated fleet runners.
- **HARDCODED PROBLEM**: Hardcoded settings in core production paths that should be configurable or present security/portability risks.

---

## 2. Configuration Inventory and Classification Matrix

| Key / Parameter | Source File / Location | Value / Default | Classification | Rationale & Impact |
|:---|:---|:---|:---|:---|
| `HMI_HOST` | `backend/app/config.py:19` | `"0.0.0.0"` (env: `HMI_HOST`) | **CONFIGURED** | Binds to all interfaces to accept ESP32 Wi-Fi telemetry; configurable via env. |
| `HMI_PORT` | `backend/app/config.py:20` | `8000` (env: `HMI_PORT`) | **CONFIGURED** | Standard HTTP/WS port for HMI backend; configurable via env. |
| `HMI_CORS_ORIGINS` | `backend/app/config.py:24` | `http://localhost:5173,http://127.0.0.1:5173` | **CONFIGURED** | Controls CORS allowed origins; parseable comma-separated list from env. |
| `VITE_API_BASE_URL` | `frontend/src/api/healthClient.ts:28` | `import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"` | **CONFIGURED** | Frontend base URL for backend API; configurable in `.env`. |
| `VITE_LIVE_WS_URL` | `frontend/.env.example:15` | `ws://127.0.0.1:8000/ws/live` | **CONFIGURED** | Frontend live WebSocket endpoint; overridable per deployment. |
| `FOG_BACKEND_URL` | `verify_*.py`, `run_*.py` | `os.getenv("FOG_BACKEND_URL", "http://127.0.0.1:8000")` | **CONFIGURED** | Test & demo harness target backend; reads env var with fallback. |
| `integration_mode` | `config/integration_config.json:2` | `"CONTROLLED_ADAPTER_SANDBOX"` | **CONFIGURED** | Controls integration mode across backend adapters. |
| `time_authority` | `config/integration_config.json:4` | `"HOST_NTP_CLOCK"` | **CONFIGURED** | Authoritative clock domain reference. |
| `max_telemetry_age_seconds` | `config/integration_config.json:6` | `3.0` | **CONFIGURED** | Telemetry freshness cutoff before marking stale. |
| `offline_threshold_seconds` | `config/integration_config.json:7` | `10.0` | **CONFIGURED** | Telemetry silence cutoff before marking OFFLINE/DISCONNECTED. |
| `max_recommendation_age_seconds` | `config/integration_config.json:8` | `5.0` | **CONFIGURED** | Safe speed recommendation expiry window. |
| `command_ack_timeout_seconds` | `config/integration_config.json:9` | `3.0` | **CONFIGURED** | Command acknowledgment roundtrip timeout. |
| `kinematic_scale.prototype_max_speed_mps` | `config/integration_config.json:13` | `3.0` | **CONFIGURED** | Physical scale model hardware speed limit. |
| `kinematic_scale.twin_dumper_max_speed_mps`| `config/integration_config.json:14` | `11.11` | **CONFIGURED** | Full-scale mining dump truck equivalent speed limit (40 km/h). |
| `kinematic_scale.scale_factor_lambda` | `config/integration_config.json:15` | `0.27` | **CONFIGURED** | Physical-to-Twin scaling factor. |
| `MAX_TELEMETRY_BODY_BYTES` | `backend/app/main.py:27` | `65536` (64 KiB) | **INTENTIONAL CONSTANT** | DoS protection boundary rejecting oversized payloads before parsing. |
| `MAX_TRACKED_VEHICLES` | `bounded_history.py:10` | `10000` | **INTENTIONAL CONSTANT** | Memory boundary preventing sequence tracker memory leak exhaustion. |
| `mass_empty_kg` | `fog_orchestrator/core/config.py:13`| `74000.0` | **INTENTIONAL CONSTANT** | BEML BH100 heavy mining dumper tare mass specification. |
| `mass_loaded_kg` | `fog_orchestrator/core/config.py:14`| `165000.0` | **INTENTIONAL CONSTANT** | BEML BH100 gross vehicle mass specification. |
| `payload_rated_kg` | `fog_orchestrator/core/config.py:15`| `91000.0` | **INTENTIONAL CONSTANT** | BEML BH100 rated iron ore payload capacity. |
| `max_retarder_kw` | `fog_orchestrator/core/config.py:20`| `1200.0` | **INTENTIONAL CONSTANT** | Continuous retarder absorption thermal capacity. |
| `max_service_brake_n` | `fog_orchestrator/core/config.py:21`| `550000.0` | **INTENTIONAL CONSTANT** | Maximum hydraulic service brake clamp force. |
| `max_deceleration_mps2` | `fog_orchestrator/core/config.py:26`| `3.5` | **INTENTIONAL CONSTANT** | Physical adhesion and passenger safety deceleration ceiling. |
| `gravity_mps2` | `fog_orchestrator/core/config.py:31`| `9.81` | **INTENTIONAL CONSTANT** | Standard gravitational acceleration constant. |
| `v_mine_limit_kmh` | `fog_orchestrator/core/config.py:37`| `20.0` (5.56 m/s) | **INTENTIONAL CONSTANT** | DGMS statutory maximum haul road operating speed. |
| `tau_sensor_s` | `fog_orchestrator/core/config.py:42`| `0.10` | **INTENTIONAL CONSTANT** | LiDAR / Radar perception pipeline latency. |
| `tau_comm_s` | `fog_orchestrator/core/config.py:43`| `0.10` | **INTENTIONAL CONSTANT** | V2V / V2X network propagation delay estimate. |
| `tau_ecu_s` | `fog_orchestrator/core/config.py:44`| `0.25` | **INTENTIONAL CONSTANT** | ECU command processing & hydraulic pressure rise delay. |
| `tau_human_s` | `fog_orchestrator/core/config.py:45`| `0.50` | **INTENTIONAL CONSTANT** | Standard driver perception-reaction delay (DGMS/SAE). |
| `s_base_m` | `fog_orchestrator/core/config.py:46`| `5.0` | **INTENTIONAL CONSTANT** | Minimum absolute standstill safety buffer distance. |
| `k_comm_s` | `fog_orchestrator/core/config.py:47`| `0.50` | **INTENTIONAL CONSTANT** | Penalty weighting for degraded communication confidence. |
| `PORT 8077` | `verify_p9_end_to_end.py:19` | `8077` | **TEST FIXTURE** | Dedicated ephemeral port to prevent collision with live dev server. |
| `PORT 8088` | `verify_p10_live_contract.py:49` | `8088` | **TEST FIXTURE** | Dedicated test port for live contract verification. |
| `SECRET_WIFI_SSID` | `esp32_code/.../secrets.example.h:15`| `"YOUR_WIFI_SSID"` | **TEST FIXTURE** | Header template for field engineers; unpopulated in version control. |
| `SECRET_WIFI_PASSWORD` | `esp32_code/.../secrets.example.h:16`| `"YOUR_WIFI_PASSWORD"` | **TEST FIXTURE** | Header template; unpopulated in version control. |
| `SECRET_HMI_TELEMETRY_URL` | `esp32_code/.../secrets.example.h:20`| `"http://192.0.2.10:8000/api/hardware/telemetry"` | **TEST FIXTURE** | RFC 5737 TEST-NET-2 documentation IP address; prevents accidental broadcast. |
| `DEMO_VEHICLES` | `mock_vehicle_generator.py:22` | `["TRUCK_01", "TRUCK_02"]` | **DEMO-ONLY** | Preconfigured IDs for synthetic dual-truck demonstration. |
| `SIM_SPEED_RAMP` | `mock_vehicle_generator.py` | `0.0 -> 8.0 m/s` | **DEMO-ONLY** | Synthetic trapezoidal profile for display testing without hardware. |
| `allow_origins=["*"]` in legacy branch | `SYNQRA_SIH2026-27-main/backend/app/main.py:35` | `allow_origins=["*"]` | **HARDCODED PROBLEM** | Permissive wildcard CORS present in legacy demo branch; resolved in active branch to `HMI_CORS_ORIGINS`. |

---

## 3. Security and Credential Audit Findings

1. **Zero Secret Leakage in Version Control**:
   - Neither production passwords nor live Wi-Fi credentials are committed to Git.
   - All `secrets.h` instances in `esp32_code` are gitignored and template files (`secrets.example.h`) contain RFC 5737 non-routable addresses (`192.0.2.10`).
2. **Denial of Service Limits**:
   - `MAX_TELEMETRY_BODY_BYTES = 65536` strictly bounded before buffering or JSON parsing.
   - `BoundedSequenceTracker` with bounded size `10000` prevents unbounded RAM consumption from malformed client sequences.
3. **CORS Boundary**:
   - Active HMI backend enforces explicit `cors_origins` (`http://localhost:5173,http://127.0.0.1:5173` by default) instead of wildcard `*`.
4. **FastAPI OpenAPI & Docs Audit**:
   - `/docs` (Swagger UI) and `/openapi.json` are enabled by default for developer integration. In hardened air-gapped field deployment, these should be gated or disabled via `docs_url=None` if untrusted networks are present.

---

## 4. Audit Verdict

**CONFIGURATION AUDIT VERDICT: PASS WITH OBSERVATIONS**
- All critical operational parameters are externalized or anchored to verified physics/mining engineering standards.
- Zero credentials or sensitive secrets exist in version control.
- Hardcoded legacy wildcard CORS is isolated to the archived branch and is actively fixed in the current integration codebase.
