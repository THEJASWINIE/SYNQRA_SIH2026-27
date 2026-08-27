# FOG-ORCHESTRATOR 2.0 — Functional Mine Digital Twin Visualization UI

A standalone, real-time 2.5D mining haulage visualization and fog safety monitoring UI built in Pygame on top of the verified digital twin `Simulator`, `FogModel`, and `resolve_v_safe()` physics pipeline.

---

## 1. Quick Start

### Launch Interactive Graphical UI
From the project root using the project's virtual environment:

```powershell
.\.venv\Scripts\python.exe game_ui.py
```
*(or activate the virtual environment with `.\.venv\Scripts\Activate.ps1` and run `python game_ui.py`)*

### Run Automated Headless Verification Test
```powershell
.\.venv\Scripts\python.exe game_ui.py --test
```

### Run Unit Tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

### Run Task 2 Comprehensive Verification Suite
```powershell
.\.venv\Scripts\python.exe verify_task2_final.py
```

---

## 2. System Architecture

The UI operates as a clean presentation and interactive control layer directly on top of the authoritative digital twin simulation:

```
+--------------------------------------------------------------------+
|                Authoritative Digital Twin Simulator                |
|  - TwinState, MineNetwork, Vehicle Fleet, Switchback, Queues       |
+---------------------------------+----------------------------------+
                                  |
                                  v
+---------------------------------+----------------------------------+
|           Verified Physics & Environmental Safety Pipeline         |
|  - resolve_v_safe(mass, grade, mu, Crr, R, visibility, ...)        |
|  - Local Safety Governor: v_command = min(v_dispatch, v_safe)     |
|  - FogModel (Visibility m <-> Friction mu <-> Surface State)       |
+---------------------------------+----------------------------------+
                                  |
                                  v
+---------------------------------+----------------------------------+
|                 Simulation UI Bridge (game_ui.py)                  |
|  - Parameter injection (live visibility & speed target commands)   |
|  - Telemetry packaging (speed, safe speed, grade, headway, status) |
|  - History buffer for real-time telemetry charts                   |
+---------------------------------+----------------------------------+
                                  |
                                  v
+---------------------------------+----------------------------------+
|                 Pygame 2.5D Visualization Engine                   |
|  - Curved Mine Haul Road (ROAD_1, ROAD_2, ROAD_RETURN)             |
|  - Realistic CAT/Komatsu Haul Truck with ore payload & headlights  |
|  - Volumetric atmospheric fog depth and distance fading            |
|  - Live speedometer, SAFE/CAUTION/UNSAFE badge, telemetry graph    |
+--------------------------------------------------------------------+
```

---

## 3. UI Features & Controls

### Main 2.5D Mine Simulation Viewport
- **ROAD_1 (Flat 0% Grade, 500m)**: Pit bench section departing from the Shovel loading facility.
- **ROAD_2 (Downhill -8% Grade, 400m, Curve $R=50\text{m}$)**: Steep descending switchback ramp to the Crusher basin, with roadside berms, slope hatchings, and grade warning sign.
- **ROAD_RETURN (Uphill +4% Grade, 900m)**: Ascending return haul ramp climbing from the crusher basin back up to the pit floor.
- **Mining Haul Truck**: Heavy yellow dump chassis, operator cab, massive off-road tires, ore payload rock texture when loaded, headlights casting light beams through fog, and glowing brake lights during deceleration.
- **Volumetric Atmospheric Fog Overlay**: Multi-layer depth haze where distant roads progressively fade into fog mist as visibility drops from 50m down to 5m.

### Fog / Visibility Control
- **Interactive Drag Slider**: Adjust visibility continuously from `5.0 m` to `50.0 m`.
- **Quick Presets**:
  - `[CLEAR 50m]`: 50m visibility, dry surface, $\mu = 0.60$, $C_{rr} = 0.02$
  - `[MOD 30m]`: 30m visibility, damp surface, $\mu = 0.40$, $C_{rr} = 0.025$
  - `[DENSE 15m]`: 15m visibility, wet surface, $\mu = 0.25$, $C_{rr} = 0.03$
  - `[EXT 5m]`: 5m extreme fog, saturated surface, $\mu = 0.15$, $C_{rr} = 0.04$

### Speed Monitoring & Safety Status
- **Current Speed ($v$)**: Live vehicle speed in km/h.
- **Safe Speed Ceiling ($v_{\text{safe}}$)**: Authoritative physical safe speed calculated by `resolve_v_safe()`.
- **Road Speed Limit**: Mine speed limit for the active road segment.
- **Safety Indicator Badge**:
  - `SAFE` (Green Glow): Current speed $\le$ safe speed under normal conditions.
  - `CAUTION` (Amber Glow): Reduced visibility ($\le 10\text{m}$), approaching safe ceiling ($>88\%$), or wet downhill slope.
  - `UNSAFE` (Red Flashing): Current speed exceeds safe speed or safety fault detected.
  - `E-STOP` (Red Solid): Emergency stop activated.

### Road & Environment Conditions Panel
- Displays current road segment, road gradient (%), friction coefficient ($\mu$), surface condition (`DRY`/`DAMP`/`WET`/`SATURATED`), stopping envelope distance, safe headway distance, and haul progress.

### Simulation Controls & Time Warp
- `[START]` / `[PAUSE]`: Toggle simulation time execution.
- `[STEP (1s)]`: Advance simulation by a single 1.0s timestep.
- `[RESET]`: Restore initial truck positions, queues, and simulation state.
- `[E-STOP]`: Command instantaneous zero speed with full emergency braking.
- `[1x Rate]`, `[2x Rate]`, `[5x Rate]`: Simulation time acceleration.

### Real-Time Telemetry Graph
- Rolling 120-second real-time plot:
  - **Solid Cyan Line**: Current Truck Speed (km/h)
  - **Dashed Amber Line**: Safe Speed Limit Ceiling ($v_{\text{safe}}$)
  - **Dotted Green Line**: Commanded Target Speed

---

## 4. Keyboard Shortcuts

| Key | Action |
|---|---|
| `SPACE` | Toggle Start / Pause |
| `S` | Step simulation by 1 second |
| `R` | Reset simulation to initial state |
| `E` | Trigger / Release Emergency Stop |
| `1` | Fog Preset: Clear (50m) |
| `2` | Fog Preset: Moderate (30m) |
| `3` | Fog Preset: Dense (15m) |
| `4` | Fog Preset: Extreme (5m) |
| `UP` | Increase commanded target speed by +2 km/h |
| `DOWN` | Decrease commanded target speed by -2 km/h |
| `ESC` | Exit application |
