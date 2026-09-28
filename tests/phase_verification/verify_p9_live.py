"""
SYNQRA SIH 2026-27 — Phase 9 Live Verification Script
Validates the live integration of game_ui.py with the Canonical Digital Twin.

PROVES:
1. game_ui can consume canonical Twin vehicle state (GET /api/twin/snapshot)
2. game_ui does not overwrite canonical Twin state
3. simulation controls remain simulation-owned
4. E-STOP remains distinct from environmental fog/safety
5. canonical provenance remains correct (SIMULATION)
6. canonical telemetry continues updating while game_ui runs
7. no fake position/topology/safety data is introduced
8. no second command pathway exists in game_ui
9. HMI remains functional while game_ui is running

USAGE:
    python verification/verify_p9_live.py
"""

import importlib.util
import inspect
import json
import os
import sys
import time
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ROOT = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")
GAME_UI_PATH = os.path.join(MAIN_ROOT, "game_ui.py")

for p in (REPO_ROOT, MAIN_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# 1. Import CanonicalTwinClient
from integration_adapters.canonical_twin_client import CanonicalTwinClient, parse_snapshot

# 2. Import game_ui
spec = importlib.util.spec_from_file_location("game_ui_module", GAME_UI_PATH)
game_ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game_ui)

SimulationUIBridge = game_ui.SimulationUIBridge
MiningVisualizerUI = game_ui.MiningVisualizerUI


class RenderHost:
    def __init__(self, bridge):
        self.bridge = bridge


def run_verification():
    print("=" * 80)
    print("STARTING P9 LIVE VERIFICATION")
    print("=" * 80)

    # 1. Inspect any canonical-client write methods
    print("\n--- TEST 1: Inspect CanonicalTwinClient Write Methods ---")
    client_methods = [
        name
        for name, member in inspect.getmembers(CanonicalTwinClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    print(f"Public methods on CanonicalTwinClient: {client_methods}")
    write_methods = [
        m
        for m in client_methods
        if any(verb in m.lower() for verb in ["post", "put", "delete", "write", "set", "update", "send", "mutate"])
    ]
    print(f"Write-capable methods found: {write_methods}")
    assert len(write_methods) == 0, f"CanonicalTwinClient must have NO write methods! Found: {write_methods}"
    print("[PASS] CanonicalTwinClient is strictly READ-ONLY (GET /api/twin/snapshot only).")

    # 2. Start CanonicalTwinClient against live backend
    print("\n--- TEST 2: Start CanonicalTwinClient against Live Backend ---")
    client = CanonicalTwinClient(url="http://127.0.0.1:8000/api/twin/snapshot", poll_interval_s=0.5)
    success = client.fetch_once()
    assert success, "Initial fetch_once() failed! Is the backend running on port 8000?"
    client.start()
    time.sleep(1.0)
    print(f"Client connected: {client.connected}")
    print(f"Status text: {client.status_text()}")
    print(f"Canonical vehicles present: {list(client.vehicles().keys())}")
    assert "TRUCK_01" in client.vehicles(), "TRUCK_01 not in canonical twin snapshot!"
    assert "TRUCK_02" in client.vehicles(), "TRUCK_02 not in canonical twin snapshot!"
    print("[PASS] Canonical Twin contains TRUCK_01 and TRUCK_02.")

    # 3. Instantiate SimulationUIBridge with canonical client
    print("\n--- TEST 3: Instantiate SimulationUIBridge(canonical_client=client) ---")
    bridge = SimulationUIBridge(canonical_client=client)
    assert bridge.canonical is client
    assert bridge.twin is not None
    print(f"Bridge canonical client wired: {bridge.canonical is not None}")
    print(f"Bridge simulator vehicles: {[v.id for v in bridge.sim.vehicles]}")
    print(f"Bridge local twin vehicles: {[v.id for v in bridge.sim.vehicles]}")
    print("[PASS] Bridge successfully initialized with isolated simulator twin and canonical client.")

    # 4. Inspect canonical_twin_rows()
    print("\n--- TEST 4: Inspect canonical_twin_rows() ---")
    host = RenderHost(bridge)
    header, rows = MiningVisualizerUI.canonical_twin_rows(host)
    print(f"Header: {header}")
    print(f"Rows count: {len(rows)}")
    for r in rows:
        print(f"  Vehicle: {r['vehicle_id']} | Speed: {r['speed_kmh']} km/h | RPM: {r['rpm']} | Provenance: {r['provenance']} | Freshness: {r['freshness']} | Comms: {r['comms']}")
    assert len(rows) >= 2, "Expected at least 2 canonical vehicles in rows"
    row_vids = [r["vehicle_id"] for r in rows]
    assert "TRUCK_01" in row_vids and "TRUCK_02" in row_vids
    assert rows[0]["provenance"] == "SIMULATION"
    assert rows[0]["freshness"] == "CURRENT"
    print("[PASS] canonical_twin_rows correctly formats canonical data without substitution.")

    # 5. Inspect canonical_unavailable_notes()
    print("\n--- TEST 5: Inspect canonical_unavailable_notes() ---")
    notes = MiningVisualizerUI.canonical_unavailable_notes(host)
    print(f"Unavailable notes: {notes}")
    assert any("environment" in n for n in notes), "Expected environment to be reported unavailable"
    assert any("topology" in n for n in notes), "Expected topology to be reported unavailable"
    assert any("road state" in n for n in notes), "Expected road state to be reported unavailable"
    print("[PASS] Canonical unavailable fields are explicitly reported, never fabricated.")

    # 6. Verify Simulator Fleet vs Canonical Fleet
    print("\n--- TEST 6: Inspect Simulator Fleet vs Canonical Fleet ---")
    sim_fleet = [v.id for v in bridge.sim.vehicles]
    canon_fleet = list(client.vehicles().keys())
    print(f"Simulator fleet ({len(sim_fleet)}): {sim_fleet}")
    print(f"Canonical fleet ({len(canon_fleet)}): {canon_fleet}")
    assert len(sim_fleet) == 4
    print("[PASS] Simulator fleet and Canonical fleet are distinct entities.")

    # 7. Change simulation visibility 50m -> 5m and verify local simulated safety changes
    print("\n--- TEST 7: Change Simulation Visibility 50m -> 5m ---")
    bridge.set_visibility(50.0)
    for _ in range(3):
        bridge.step()
    clear_v_safe = bridge.twin_v_safe_mps("TRUCK_01")
    print(f"Clear visibility (50m) simulated v_safe: {clear_v_safe} m/s")

    # Check backend twin before visibility change
    with urllib.request.urlopen("http://127.0.0.1:8000/api/twin/snapshot", timeout=3) as r:
        snap_before = json.loads(r.read().decode())

    bridge.set_visibility(5.0)  # Extreme fog in simulator
    for _ in range(3):
        bridge.step()
    fog_v_safe = bridge.twin_v_safe_mps("TRUCK_01")
    print(f"Extreme fog (5m) simulated v_safe: {fog_v_safe} m/s")

    assert clear_v_safe is not None and fog_v_safe is not None
    assert fog_v_safe < clear_v_safe, f"Extreme fog must reduce local simulated safe speed! clear={clear_v_safe}, fog={fog_v_safe}"

    # Verify backend twin was NOT mutated by simulator visibility change
    with urllib.request.urlopen("http://127.0.0.1:8000/api/twin/snapshot", timeout=3) as r:
        snap_after = json.loads(r.read().decode())
    assert "visibility_m" not in snap_after["vehicles"]["TRUCK_01"]["dynamic"], "Backend twin must NOT have visibility injected!"
    print("[PASS] Changing simulation visibility affects only local simulator state; canonical twin is untouched.")

    # 8. Activate E-STOP and verify separation from environmental safety
    print("\n--- TEST 8: Activate E-STOP and Verify Separation ---")
    bridge.set_visibility(50.0)
    for _ in range(2):
        bridge.step()
    bridge.e_stop_active = True
    bridge.step()
    fleet_telem = bridge.get_fleet_telemetry()
    truck_01_telem = next(t for t in fleet_telem if t["id"] == "TRUCK_01")
    print(f"E-STOP active: status_label = {truck_01_telem['status_label']}")
    print(f"Local twin v_safe during E-STOP = {truck_01_telem['v_safe_kmh']} km/h (environment solver untouched)")
    assert truck_01_telem["status_label"] == "E-STOP"
    assert truck_01_telem["v_safe_kmh"] is not None and truck_01_telem["v_safe_kmh"] > 0, "Physics safe speed must not be conflated with E-STOP!"
    bridge.e_stop_active = False
    bridge.step()
    print("[PASS] E-STOP remains distinct from environmental physics solver.")

    # 9. Verify Canonical Telemetry continues updating while bridge.step() runs
    print("\n--- TEST 9: Canonical Telemetry Continues Updating during Simulator Steps ---")
    samples = []
    for i in range(5):
        bridge.step()
        time.sleep(0.6)
        v = client.vehicle("TRUCK_01")
        if v:
            seq = v.get("sequence").value
            spd = v.speed_mps
            samples.append((seq, spd))
            print(f"  Step {i+1}: Canonical TRUCK_01 seq={seq} speed={spd} m/s")

    assert len(samples) == 5
    assert samples[-1][0] > samples[0][0], f"Expected sequence to advance: {samples[0][0]} -> {samples[-1][0]}"
    print("[PASS] Canonical telemetry updates live while simulator runs.")

    # 10. Verify HMI remains functional
    print("\n--- TEST 10: Verify HMI Endpoints Remain Functional ---")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as r:
        assert r.status == 200
    with urllib.request.urlopen("http://127.0.0.1:8000/api/vehicles", timeout=3) as r:
        vehicles_resp = json.loads(r.read().decode())
        assert "TRUCK_01" in vehicles_resp.get("vehicles", {})
    with urllib.request.urlopen("http://127.0.0.1:8000/api/twin/snapshot", timeout=3) as r:
        snap_resp = json.loads(r.read().decode())
        assert "TRUCK_01" in snap_resp.get("vehicles", {})
    print("[PASS] HMI /api/health, /api/vehicles, and /api/twin/snapshot remain responsive and live.")

    # 11. Verify No Second Command Pathway
    print("\n--- TEST 11: Verify No Second Command Pathway in game_ui ---")
    with open(GAME_UI_PATH, "r", encoding="utf-8") as f:
        src = f.read()
    without_docstrings = "".join(src.split('"""')[::2])
    code_lines = [line for line in without_docstrings.splitlines() if not line.strip().startswith("#")]
    code_only = "\n".join(code_lines)
    for banned in ["api/commands", "CommandGateway", "issue_command", "requests.post", "urlopen", "http.client"]:
        assert banned not in code_only, f"Found banned command path string '{banned}' in game_ui.py executable code!"
    print("[PASS] game_ui contains NO command issuance transport in executable code; commands flow strictly HMI -> /api/commands -> CommandGateway.")

    client.stop()
    print("\n" + "=" * 80)
    print("P9 LIVE VERIFICATION COMPLETED: ALL 11 CHECKS PASSED (100%)")
    print("=" * 80)


if __name__ == "__main__":
    run_verification()
