# results/01_build_audit.md
See full report at [02_BUILD_AUDIT.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/02_BUILD_AUDIT.md).
Summary:
- Frontend: PASS (npm build clean, vitest 1,860/1,860 pass)
- Backend: PASS (FastAPI uvicorn live on port 8000)
- Pytest Suite: 1,185 PASS, 4 FAIL (Windows socketpair permission), 1 SKIP, 29 WARNINGS
- ESP32 Firmware A & B: PASS (Syntax & linking verified)
- Physical COM14: FAIL (Flash corrupted, bootloop)
- Physical COM11: PASS (Flashed and running LoRa Gateway)
