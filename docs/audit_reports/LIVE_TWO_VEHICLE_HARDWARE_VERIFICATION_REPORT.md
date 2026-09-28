# LIVE TWO-VEHICLE HARDWARE VERIFICATION REPORT

**Verification date:** 2026-09-08
**Branch:** `arun_HMI_integration` @ `89a1a19` (ahead 2 of origin, not pushed)

---

## VERDICT

### PHYSICAL HARDWARE E2E — **NOT VERIFIED — HARDWARE UNAVAILABLE**

No physical vehicle was connected at any point during this verification. No PASS is
claimed for any test requiring hardware.

---

## 1. HARDWARE ACTUALLY CONNECTED

**NONE.** Established by three independent checks, not by assumption:

| Check | Result |
|---|---|
| USB serial devices matching `CP210 / CH340 / FTDI / Silicon Labs / UART / ESP32` | **NONE**. `COM6` and `COM8` exist but are Bluetooth virtual ports, not an ESP32 bridge |
| Host Wi-Fi interfaces | All hold `169.254.x.x` link-local addresses — **not associated with any Wi-Fi network**. Host is on Ethernet `192.168.32.238` |
| **60-second live listen**, backend bound `0.0.0.0:8000` so a real ESP32 on the LAN could reach it | `accepted 0, invalid 0, duplicate 0, unknown_vehicle 0`; `twin_vehicle_count 0`; zero `[HARDWARE TELEMETRY]` log lines; twin vehicles `NONE` |

The LAN-exposed listener was stopped immediately after the test.

## 2. TRUCK_01 — NOT VERIFIED
## 3. TRUCK_02 — NOT VERIFIED

No ESP32 boot, sensor init, Wi-Fi association, telemetry transmission, backend receipt,
Twin update or S1 render was observed for either vehicle. Neither vehicle transmitted a
single frame.

## 4. TEST MATRIX

| Test | TRUCK_01 | TRUCK_02 | Result | Evidence |
|---|---|---|---|---|
| ESP32 boot | — | — | **NOT VERIFIED** | no device present |
| Wi-Fi | — | — | **NOT VERIFIED** | host Wi-Fi unassociated |
| Telemetry TX | — | — | **NOT VERIFIED** | 0 frames in 60 s |
| Backend RX | — | — | **NOT VERIFIED** | `accepted 0` |
| Payload contract | — | — | **NOT VERIFIED (live)** | static check only, §6 |
| Sequence | — | — | **NOT VERIFIED (live)** | code + unit tests only |
| RPM | — | — | **NOT VERIFIED** | no sensor connected |
| Speed | — | — | **NOT VERIFIED** | see §5 calibration |
| IMU | — | — | **NOT VERIFIED** | no sensor connected |
| RSSI | — | — | **NOT VERIFIED** | no radio connected |
| Digital Twin | — | — | **NOT VERIFIED (live)** | `twin_vehicle_count 0` |
| S1 rendering | — | — | **NOT VERIFIED (live)** | no live vehicle to render |
| Disconnect | — | — | **NOT VERIFIED** | requires a connected vehicle first |
| Reconnect | — | — | **NOT VERIFIED** | as above |
| Concurrent operation | — | — | **NOT VERIFIED** | requires both vehicles |

**Nothing in the hardware-dependent column can be claimed.**

## 5. SPEED CALIBRATION — SOFTWARE CHECK (§8)

`config/physical_vehicle_parameters.json` is present and internally consistent with the
firmware constants:

| Vehicle | Config radius | Config PPR | Firmware diameter | Firmware PPR | Consistent |
|---|---|---|---|---|---|
| TRUCK_01 | 0.050 m | 42.0 | `WHEEL_DIAMETER_M 0.10` | `PULSES_PER_REV 42.0` | **YES** |
| TRUCK_02 | 0.0425 m | 20.0 | `WHEEL_DIAMETER_M 0.085` | `PULSES_PER_REV 20.0` | **YES** |

`UnitConverter.rpm_to_speed_mps` computes `v = RPM · 2πr / 60`, algebraically identical to
the firmware's `RPM · π · D / 60` since `D = 2r`. It returns `None` — rendering
UNAVAILABLE, never 0 — when the radius is missing, non-positive, or the RPM is invalid or
negative.

**Caveat:** the configured radii are *stated*, not evidenced as physically measured. Wheel
radius should be confirmed with calipers before any speed figure is presented as accurate.
A 5% radius error is a 5% speed error, silently.

## 6. SOFTWARE-SIDE CHECKS LEGITIMATELY PERFORMED

| Check | Result |
|---|---|
| Payload contract vs firmware (static) | Vehicle A firmware emits `vehicle_id, sequence, rpm, speed, accel_x/y/z, gyro_x/y/z, rssi, snr, source` — matches `HardwareTelemetryPayload` including the alias fields. **No mismatch** |
| LIVE never falls back to MOCK | `ProviderHost.tsx:151` — `targetKind === "LIVE" ? liveProvider : mockProvider`, chosen once from `VITE_PROVIDER`. **No runtime fallback path exists** |
| DIRECT_WIFI SNR rule | `snrReadout()` returns UNAVAILABLE with reason for `DIRECT_WIFI`; a V2V frame keeps its value. Test-enforced |
| Position never fabricated | `PhysicalVehiclePositionProvider` always returns UNAVAILABLE and is not even given the site extent. Test-enforced |
| TRUCK_02 PWM semantics | `speed_mps_pwm_derived` stored under its own name; never labelled encoder-measured. Test-enforced |
| Backend imports and serves | `/api/health` OK; hardware endpoints registered |

## 7. AUTOMATED REGRESSION — ALL PASSING

| Suite | Result |
|---|---|
| Frontend `npx vitest run` | **1269 passed** (46 files) |
| TypeScript `npx tsc --noEmit` | **clean** |
| Root `pytest tests/` | **612 passed, 1 skipped** |
| Main `pytest tests` (own cwd) | **50 passed** |

No test was weakened, deleted or modified.

## 8. DEFECTS CARRIED FORWARD (previously reported, unchanged)

1. **Fabricated SNR at source.** `sketch_aug26a.ino` sends a hard-coded `9.5` dB when it
   holds no valid LoRa packet, and `telemetry_ingest.py:582` stamps `snr_db` as *observed*
   — so a fabricated value reaches the Twin labelled as a hardware measurement. The
   frontend suppresses it for DIRECT_WIFI; **the source is still wrong**.
2. **Wheel radius unevidenced** (§5).

Neither was fixed in this phase — this was a verification phase, and §20 forbids firmware
changes without proven necessity.

## 9. WHAT MUST HAPPEN TO REACH A REAL PASS

1. Power both ESP32 vehicles and join them to the same network as the backend host.
2. Set `SECRET_HMI_TELEMETRY_URL` to `http://<host-ip>:8000/api/hardware/telemetry`.
3. Bind the backend to `0.0.0.0` (as done here) so vehicles can reach it.
4. Re-run this verification and record actual frames, RPM response to wheel rotation, IMU
   response to movement, disconnect/reconnect, and concurrent operation.

## 10. FILES CHANGED

**None.** No code, configuration, firmware or test was modified during this verification.
The only new file is this report.

## 11. EXPLICIT STATEMENTS

**NO GITHUB PUSH PERFORMED.**

**PHYSICAL HARDWARE E2E IS NOT VERIFIED** — no hardware was connected during this
implementation.

Software-path verification is **not** physical verification. Passing automated tests
establishes only that the software behaves correctly against synthetic input.
