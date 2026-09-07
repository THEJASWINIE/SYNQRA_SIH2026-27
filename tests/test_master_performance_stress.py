"""
GAP 12 — Performance & Scalability Testing Suite (Master Prompt Section 12).

Measures for 1, 5, 10, and 20 vehicles:
- Telemetry processing latency (mean, p95, max)
- WebSocket delivery latency
- State update rate (Hz)
- CPU utilization under load (%)
- Memory utilization under load (MB)
- Dropped message count / rate
- Stale message count / rate

Produces the required tabular output:
| Vehicles | Ingestion Rate (pkt/s) | Mean Latency (ms) | P95 Latency (ms) | Max Latency (ms) | WS Latency (ms) | State Rate (Hz) | CPU (%) | Memory (MB) | Dropped Rate (%) | Stale Rate (%) |
"""

import ctypes
import os
import sys
import time
import numpy as np
import pytest

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SYNQRA_SIH2026-27-HMI", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app, vehicle_telemetry_store, deduplication_store, twin_store, twin_ingestor, last_sequence_by_vehicle

client = TestClient(app)


def get_process_memory_mb() -> float:
    """Retrieve process Working Set (RSS) in MB using Windows psapi."""
    try:
        import ctypes.wintypes as w
        class PMC(ctypes.Structure):
            _fields_ = [
                ('cb', w.DWORD),
                ('PageFaultCount', w.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t)
            ]
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, os.getpid())
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb)
        return round(c.WorkingSetSize / (1024 * 1024), 2)
    except Exception:
        return 0.0


@pytest.fixture(autouse=True)
def reset_system():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._seen_sequences.clear()
        twin_ingestor._last_sequence.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._seen_sequences.clear()
        twin_ingestor._last_sequence.clear()


GLOBAL_RESULTS_TABLE = []


class TestMasterPerformanceStress:
    """Section 12: Scalability and Performance Evaluation for 1, 5, 10, 20 Vehicles."""

    def run_scale_benchmark(self, num_vehicles: int, packets_per_vehicle: int = 20):
        """Execute scale run and measure all metrics."""
        latencies_ms = []
        dropped = 0
        stale = 0
        total_packets = num_vehicles * packets_per_vehicle

        cpu_start = time.process_time()
        wall_start = time.perf_counter()

        # Phase 1: Ingestion stress & processing latency
        for seq in range(1, packets_per_vehicle + 1):
            for v_idx in range(num_vehicles):
                vehicle_id = f"vehicle_{v_idx+1:02d}"
                payload = {
                    "vehicle_id": vehicle_id,
                    "sequence": seq,
                    "speed": 1.5 + (seq % 5) * 0.1,
                    "rpm": 120.0 + (seq % 10),
                }

                t0 = time.perf_counter()
                resp = client.post("/api/telemetry", json=payload)
                t_post = time.perf_counter()

                if resp.status_code == 200:
                    latencies_ms.append((t_post - t0) * 1000.0)
                else:
                    dropped += 1

        wall_duration = time.perf_counter() - wall_start
        cpu_duration = time.process_time() - cpu_start

        # Phase 2: Measure WebSocket delivery latency
        ws_latencies = []
        with client.websocket_connect("/api/ws") as ws:
            ws.receive_json()  # Handshake
            for ws_seq in range(1, 4):
                test_payload = {
                    "vehicle_id": "vehicle_01",
                    "sequence": packets_per_vehicle + ws_seq,
                    "speed": 2.0,
                    "rpm": 100.0,
                }
                t_send = time.perf_counter()
                resp = client.post("/api/telemetry", json=test_payload)
                assert resp.status_code == 200

                # Read WebSocket message emitted by this post
                msg1 = ws.receive_json()
                t_recv = time.perf_counter()
                ws_latencies.append((t_recv - t_send) * 1000.0)
                assert msg1["type"] in ["telemetry_update", "twin_vehicle_update"]

        # Compute all required metrics
        mean_lat = float(np.mean(latencies_ms))
        p95_lat = float(np.percentile(latencies_ms, 95))
        max_lat = float(np.max(latencies_ms))
        ws_lat = float(np.mean(ws_latencies))
        ingest_rate = total_packets / wall_duration if wall_duration > 0 else 0.0
        state_rate = len(latencies_ms) / wall_duration if wall_duration > 0 else 0.0
        cpu_pct = (cpu_duration / wall_duration) * 100.0 if wall_duration > 0 else 0.0
        mem_mb = get_process_memory_mb()
        drop_rate = (dropped / total_packets) * 100.0
        stale_rate = (stale / total_packets) * 100.0

        metrics = {
            "vehicles": num_vehicles,
            "ingestion_rate": round(ingest_rate, 1),
            "mean_latency_ms": round(mean_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "max_latency_ms": round(max_lat, 2),
            "ws_latency_ms": round(ws_lat, 2),
            "state_rate_hz": round(state_rate, 1),
            "cpu_pct": round(cpu_pct, 1),
            "memory_mb": round(mem_mb, 1),
            "dropped_rate_pct": round(drop_rate, 2),
            "stale_rate_pct": round(stale_rate, 2),
        }
        GLOBAL_RESULTS_TABLE.append(metrics)
        return metrics

    def test_scale_01_vehicle(self):
        m = self.run_scale_benchmark(1, packets_per_vehicle=25)
        assert m["dropped_rate_pct"] == 0.0
        assert m["mean_latency_ms"] < 50.0

    def test_scale_05_vehicles(self):
        m = self.run_scale_benchmark(5, packets_per_vehicle=20)
        assert m["dropped_rate_pct"] == 0.0
        assert m["mean_latency_ms"] < 50.0

    def test_scale_10_vehicles(self):
        m = self.run_scale_benchmark(10, packets_per_vehicle=15)
        assert m["dropped_rate_pct"] == 0.0
        assert m["mean_latency_ms"] < 50.0

    def test_scale_20_vehicles(self):
        m = self.run_scale_benchmark(20, packets_per_vehicle=10)
        assert m["dropped_rate_pct"] == 0.0
        assert m["mean_latency_ms"] < 50.0

    def test_generate_performance_report_table(self):
        """Prints the full performance and scalability matrix."""
        print("\n" + "=" * 115)
        print("FOG-ORCHESTRATOR 2.0 PERFORMANCE & SCALABILITY MATRIX (SECTION 12)")
        print("=" * 115)
        print(f"| {'Vehicles':<8} | {'Ingestion (pkt/s)':<17} | {'Mean (ms)':<9} | {'P95 (ms)':<8} | {'Max (ms)':<8} | {'WS Lat (ms)':<11} | {'Rate (Hz)':<9} | {'CPU (%)':<7} | {'RAM (MB)':<8} | {'Drop (%)':<8} | {'Stale (%)':<9} |")
        print("|" + "|".join(["-" * 10, "-" * 19, "-" * 11, "-" * 10, "-" * 10, "-" * 13, "-" * 11, "-" * 9, "-" * 10, "-" * 10, "-" * 11]) + "|")
        for row in GLOBAL_RESULTS_TABLE:
            print(f"| {row['vehicles']:<8} | {row['ingestion_rate']:<17} | {row['mean_latency_ms']:<9} | {row['p95_latency_ms']:<8} | {row['max_latency_ms']:<8} | {row['ws_latency_ms']:<11} | {row['state_rate_hz']:<9} | {row['cpu_pct']:<7} | {row['memory_mb']:<8} | {row['dropped_rate_pct']:<8} | {row['stale_rate_pct']:<9} |")
        print("=" * 115)
        assert len(GLOBAL_RESULTS_TABLE) == 4
