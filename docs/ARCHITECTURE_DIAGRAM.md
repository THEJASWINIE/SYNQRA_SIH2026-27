# ARCHITECTURE AND DATA FLOW

Process boundaries are drawn explicitly. Everything inside one box is one OS process.

## 1. Whole system

```
   PHYSICAL / EMULATED SOURCES                    ── separate processes / devices ──
   ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  ┌──────────────────┐
   │ ESP32        │  │ ESP32        │  │ hardware_emulator  │  │ mock generators  │
   │ TRUCK_01     │  │ TRUCK_02     │  │ (EMULATED)         │  │ (SIMULATION)     │
   └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘  └────────┬─────────┘
          │ V2V / Wi-Fi     │ Wi-Fi Direct       │ serial               │ HTTP
          └─────────────────┴────────────────────┴──────────────────────┘
                                       │
════════════════════════════════ PROCESS BOUNDARY ════════════════════════════════
                                       │
   ┌───────────────────────────────────▼───────────────────────────────────────┐
   │ HMI BACKEND PROCESS   uvicorn app.main:app   (SYNQRA_SIH2026-27-HMI/backend)│
   │                                                                            │
   │   POST /api/hardware/telemetry ─┐   POST /api/telemetry ─┐   WS /api/ws ─┐ │
   │        provenance = HARDWARE    │   provenance = SIM     │   = SIM       │ │
   │                                 └────────────┬───────────┴───────────────┘ │
   │                                              ▼                             │
   │                        ┌──────────────────────────────────┐                │
   │                        │ telemetry_ingest.TelemetryIngestor│  ← ONE boundary│
   │                        │  validate · dedupe · order ·      │                │
   │                        │  normalize · stamp provenance     │                │
   │                        └──────────────┬───────────────────┘                │
   │                                       ▼                                    │
   │                        ┌──────────────────────────────────┐                │
   │                        │ twin.TwinStateStore  (CANONICAL) │                │
   │                        │  per-field value/ts/source/origin │                │
   │                        │  /quality/clock_domain            │                │
   │                        └───────┬──────────────────┬────────┘                │
   │                                │ read             │ read                    │
   │                 ┌──────────────▼──────┐  ┌────────▼──────────────┐          │
   │                 │ command_gateway     │  │ twin_projection       │          │
   │                 │  reads v_safe ONLY  │  │  ONE projection fn    │          │
   │                 │  never solves       │  │  for REST + WS        │          │
   │                 └──────────┬──────────┘  └────────┬──────────────┘          │
   │                            │                      │                         │
   │   GET /api/observability ──┘   GET /api/twin/* ────┤  WS twin_vehicle_update │
   └────────────────────────────────────────────────────┬───────────────────────┘
                                                        │
════════════════════════════════ PROCESS BOUNDARY ══════╪════════════════════════
                                                        │
   ┌────────────────────────────────────────────────────▼───────────────────────┐
   │ REACT FRONTEND PROCESS   npm run dev   (SYNQRA_SIH2026-27-HMI/frontend)     │
   │   LiveDataProvider → AppStateStore → Technician HMI · Operator HMI          │
   │   PRESENTATION ONLY. No physics, no invented vehicle state.                 │
   └────────────────────────────────────────────────────────────────────────────┘
```

## 2. The Pygame visualiser (separate process, separate Twin)

```
════════════════════════════════ PROCESS BOUNDARY ════════════════════════════════
   ┌────────────────────────────────────────────────────────────────────────────┐
   │ PYGAME PROCESS   python game_ui.py   (SYNQRA_SIH2026-27-main)               │
   │                                                                            │
   │   twin/simulator.py  ──►  twin/ui_domain.UISimulationDomain                 │
   │                             │  calls models.vehicle_physics.resolve_v_safe  │
   │                             │  ── which is the adapter over fog_safe ──     │
   │                             ▼                                              │
   │                    TwinStateStore (this process's own instance)             │
   │                             │ read-only                                     │
   │                             ▼                                              │
   │                    SimulationUIBridge  ──►  pygame draw                     │
   │                    UNAVAILABLE renders as "--", never as a number           │
   └────────────────────────────────────────────────────────────────────────────┘
```

**Limitation:** this process holds a SEPARATE `TwinStateStore` from the backend process.
Both are built from the same class and the same rules, but they are not one instance. See
`ARCHITECTURE_STATUS.md` §7.1.

## 3. The safety loop the demo proves

```
 environment visibility falls
        │
        ▼
 Twin environment field updated (source=SIMULATION, clock_domain=SIMULATION)
        │
        ▼
 fog_safe.solve_safe_speed:  v_safe = min(v_stop, v_retarder, v_traction,
                                          v_traction_ceiling, v_curve, v_mine)
        │
        ▼
 Twin vehicle v_safe_mps updated (source=DERIVED, origin=SIMULATION)
        │
        ├────────────────────────────► twin_projection ──► REST + WS ──► HMI
        │
        ▼
 command_gateway: v_command = min(v_dispatch, v_safe)
   · target above v_safe            → REJECTED (counted as unsafe + rejected)
   · v_safe stale or unavailable    → REJECTED, fail closed
   · STOP / HOLD                    → never blocked
        │
        ▼
 vehicle state changes ──► Twin updates ──► HMI updates
```

The Tier-1 local governor on the vehicle remains authoritative. The gateway can only ever
lower a commanded speed; it never raises one and never computes safety itself.
