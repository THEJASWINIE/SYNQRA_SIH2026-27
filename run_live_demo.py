"""
DEMO PRODUCER - live SIMULATED telemetry into the canonical ingestion path.

=========================================================================
  ALL TELEMETRY PRODUCED BY THIS SCRIPT IS **SIMULATED**.
  There is no ESP32, no sensor and no vehicle behind these numbers - they come from
  `MockVehicleGenerator`, which is a pure math model. Nothing here constitutes
  hardware, HIL or physical validation.
=========================================================================

WHY THIS FILE CHANGED
    `MockVehicleGenerator.update()` emits frames with no `sequence` / `sequence_number`.
    The canonical boundary in `telemetry_ingest.py` requires one:

        seq_raw = parsed.get("sequence_number", parsed.get("sequence"))
        try:
            sequence = int(seq_raw)
        except (TypeError, ValueError):
            return self._reject(vid, None, REJECT_BAD_SEQUENCE)

    `int(None)` raises TypeError, so every mock frame was refused as
    REJECTED_INVALID_SEQUENCE. Measured before the fix:
    `accepted=0, invalid=2, twin vehicles=0` - while the backend's own cache still held
    2 vehicles, so the HMI could show cached data over an empty Twin.

    The PRODUCER was wrong, so the producer is what is fixed. This script now supplies
    the field the contract already requires. It does NOT relax sequence validation, and
    does not touch the Twin, the safety solver, the HMI, or the telemetry contract.
    `mock_vehicle_generator.py` is deliberately left unmodified - three verify_* scripts
    import it.

USAGE
    python run_live_demo.py
    python run_live_demo.py --url http://127.0.0.1:8000 --hz 2 --duration 30
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from integration_adapters.unit_converter import UnitConverter
from mock_vehicle_generator import MockVehicleGenerator
from scene_position_sim import route_speed_mps, scene_telemetry_fields

DEFAULT_URL = "http://127.0.0.1:8000"
DEMO_VEHICLES = ("TRUCK_01", "TRUCK_02")


def _get(url, path, timeout=5):
    with urllib.request.urlopen(url + path, timeout=timeout) as response:
        return json.loads(response.read())


def _post(url, path, payload, timeout=5):
    request = urllib.request.Request(
        url + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"{}")
        except Exception:  # noqa: BLE001
            return error.code, {}
    except Exception as exc:  # noqa: BLE001
        return None, {"transport_error": str(exc)}


def seed_sequences(url):
    """
    Start each vehicle's counter ABOVE whatever the Twin already holds.

    The ingestor enforces strictly increasing sequences per vehicle. A producer restarting
    at 1 would have every frame refused as out-of-order - and since /api/telemetry answers
    HTTP 200 either way, that failure is easy to miss. Seeding from the live Twin makes a
    restart safe.
    """
    seeds = {}
    for vehicle_id in DEMO_VEHICLES:
        try:
            vehicle = _get(url, "/api/twin/vehicles/%s" % vehicle_id)
            seeds[vehicle_id] = int(vehicle["dynamic"].get("sequence", {}).get("value") or 0)
        except Exception:  # noqa: BLE001 - vehicle simply not in the Twin yet
            seeds[vehicle_id] = 0
    return seeds


def run(url=DEFAULT_URL, hz=2.0, duration=None, quiet=False):
    generator = MockVehicleGenerator(backend_url=url)
    # The ONE calibration the ingestor derives speed with; see the speed override below.
    unit_converter = UnitConverter()
    sequences = seed_sequences(url)
    interval = 1.0 / max(hz, 0.1)

    print("SIMULATED telemetry producer -> %s/api/telemetry" % url)
    print("  vehicles  : %s" % ", ".join(DEMO_VEHICLES))
    print("  rate      : %.1f Hz per vehicle" % hz)
    print("  sequences : seeded at %s" % sequences)
    print("  PROVENANCE: SIMULATION. No physical hardware is involved.")
    print("-" * 78)

    started = time.time()
    posted = accepted = refused = 0

    try:
        while duration is None or (time.time() - started) < duration:
            elapsed = time.time() - started
            for frame in generator.update(dt_s=interval):
                vehicle_id = frame.get("vehicle_id")
                if vehicle_id not in sequences:
                    continue

                sequences[vehicle_id] += 1
                # The fields being added. Everything else is the generator's own frame,
                # forwarded unchanged. Provenance is decided by the transport
                # (/api/telemetry is the simulated ingress), never declared here.
                payload = dict(frame)
                payload["sequence"] = sequences[vehicle_id]
                # MAP-02: the Digital Twin demonstration scene pose, so both trucks are
                # visible on the mine map. `scene_position_sim` is deterministic in the
                # elapsed demo time, and the ingestor stamps every scene pose SIMULATION -
                # this is NOT a GNSS fix and is never presented as one.
                payload.update(scene_telemetry_fields(vehicle_id, elapsed))

                # DIGITAL-TWIN-OPERATIONAL-FLOW-01: the displayed "speed" must agree with
                # how fast the truck actually moves on the mine plan. `MockVehicleGenerator`
                # (deliberately left unmodified - three verify_* scripts import it) supplies
                # its own independent sin/cos speed for HMI-only validation, which visibly
                # disagreed with the route's constant progression speed. Overridden here,
                # in the same place the scene pose is overridden, with the EXACT constant
                # `scene_position_sim` uses to advance this vehicle's position - not a new
                # or fabricated value. Only trucks with a demonstration route are touched;
                # this endpoint (/api/telemetry) always ingests as SIMULATION (main.py
                # forces is_simulated=True), so provenance is unchanged, and the physical
                # hardware ingress (/api/hardware/telemetry) is a separate code path this
                # producer never touches.
                #
                # The canonical Twin `speed_mps` is DERIVED FROM RPM through the calibrated
                # wheel radius (telemetry_ingest -> UnitConverter.rpm_to_speed_mps); the
                # reported speed only lands in `speed_mps_reported`. So the RPM is published
                # through the SAME calibration's exact inverse - one wheel radius, no copy
                # of it here - and both fields agree with the route. NOTE (stated, not
                # hidden): the calibrated radii are the bench prototypes' (5 cm / 4.25 cm),
                # so a full-scale demo speed of 8 m/s is ~1500 simulated RPM, above the
                # prototypes' `max_physical_speed_mps`. It is a SIMULATION frame about the
                # full-scale twin, never a claim about the bench hardware.
                sim_speed = route_speed_mps(vehicle_id)
                if sim_speed is not None:
                    payload["speed_mps"] = sim_speed
                    sim_rpm = unit_converter.speed_mps_to_rpm(vehicle_id, sim_speed)
                    if sim_rpm is not None:
                        payload["rpm"] = sim_rpm

                status, body = _post(url, "/api/telemetry", payload)
                posted += 1
                if status == 200 and str(body.get("status", "")).upper().startswith("INGEST"):
                    accepted += 1
                else:
                    refused += 1
                    if not quiet:
                        print("  refused %s seq=%d -> HTTP %s %s"
                              % (vehicle_id, sequences[vehicle_id], status, body))

            if not quiet and posted % 20 == 0:
                try:
                    stats = _get(url, "/api/observability")
                    print("  posted=%-5d ingest=%s twin_vehicles=%s"
                          % (posted, stats.get("telemetry_ingest"),
                             stats.get("twin_vehicle_count")))
                except Exception:  # noqa: BLE001 - observability is best-effort here
                    pass

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nstopped by user")

    print("-" * 78)
    print("posted=%d accepted=%d refused=%d" % (posted, accepted, refused))
    return 0 if refused == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Post SIMULATED TRUCK_01/TRUCK_02 telemetry to the canonical ingress.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--hz", type=float, default=2.0)
    parser.add_argument("--duration", type=float, default=None,
                        help="seconds to run; omit to run until interrupted")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    return run(url=args.url, hz=args.hz, duration=args.duration, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
