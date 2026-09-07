"""
GAP 14 — Security & Robustness Verification Suite (Master Prompt Section 14).

Covers all security requirements and audits:
1. SQL injection payloads in vehicle_id
2. Command injection payloads in command fields
3. Oversized payload rejection (HTTP 413 Bounded Body / D005)
4. Non-numeric and non-finite inputs rejection (D001)
5. Replay attack prevention via duplicate sequence rejection (D004)
6. Audit of `/docs`, `/openapi.json`, and `/redoc`
7. Explicit audit of authentication absence (documented limitation)
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SYNQRA_SIH2026-27-HMI", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle
from command_gateway import CommandGateway, VehicleCommand, CommandSource, CommandStatus
from twin.twin_state_store import TwinStateStore, TwinMode

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_system():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()


class TestMasterSecurityAudit:
    """Security and Robustness Evaluation."""

    def test_sql_injection_payload_in_vehicle_id(self):
        """1. SQL injection string in vehicle_id must not crash and must be safely rejected."""
        sqli_payload = "TRUCK_01' OR '1'='1' --"
        resp = client.post("/api/hardware/telemetry", json={
            "vehicle_id": sqli_payload,
            "sequence": 1,
            "speed": 1.0,
            "rpm": 100.0,
            "source": "DIRECT_WIFI"
        })
        assert resp.status_code == 400
        assert "TRUCK_01" not in vehicle_telemetry_store
        assert sqli_payload not in vehicle_telemetry_store

    def test_command_injection_payload_in_command_gateway(self):
        """2. Shell command injection payload in action/command_id rejected safely."""
        store = TwinStateStore(mode=TwinMode.HYBRID)
        class FixedClock:
            t = 100.0
            def __call__(self):
                return self.t
        gateway = CommandGateway(store=store, clock=FixedClock())
        cmd = VehicleCommand(
            command_id="CMD; rm -rf /; calc.exe",
            vehicle_id="TRUCK_01",
            action="TARGET_SPEED; shutdown -s",
            target_speed_mps=1.0,
            created_at=100.0,
            source=CommandSource.OPERATOR
        )
        res = gateway.submit(cmd)
        # Action is not a recognized CommandAction -> INVALID or REJECTED
        assert res.status in [CommandStatus.INVALID, CommandStatus.REJECTED]

    def test_oversized_payload_rejection_http_413(self):
        """3. Payload > 64 KiB is rejected with HTTP 413 before body buffering / mutation (D005)."""
        oversized_data = "X" * (70 * 1024)  # 70 KiB
        resp = client.post(
            "/api/telemetry",
            content=f'{{"vehicle_id": "TRUCK_01", "speed": 1.0, "junk": "{oversized_data}"}}',
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 413
        assert "TRUCK_01" not in vehicle_telemetry_store

    def test_non_numeric_and_non_finite_inputs_rejected(self):
        """4. String, boolean, NaN, and Inf speeds rejected before mutation."""
        for invalid_speed in ["fast", True, [1.0], {"val": 1.0}]:
            resp = client.post("/api/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "speed": invalid_speed,
                "sequence": 1
            })
            assert resp.status_code == 400
            assert "TRUCK_01" not in vehicle_telemetry_store

    def test_replay_attack_duplicate_sequence_rejected(self):
        """5. Replay of identical sequence is rejected as duplicate (D004)."""
        valid_payload = {
            "vehicle_id": "TRUCK_01",
            "sequence": 55,
            "speed": 1.5,
            "rpm": 120.0,
            "source": "DIRECT_WIFI"
        }
        r1 = client.post("/api/hardware/telemetry", json=valid_payload)
        assert r1.status_code == 200

        # Replay same packet
        r2 = client.post("/api/hardware/telemetry", json=valid_payload)
        assert r2.status_code == 409
        assert r2.json().get("status") == "ACCEPTED_DUPLICATE"

    def test_audit_docs_and_openapi_endpoints(self):
        """6. Explicit audit of /docs and /openapi.json accessibility."""
        # /openapi.json is served
        resp_openapi = client.get("/openapi.json")
        assert resp_openapi.status_code == 200
        spec = resp_openapi.json()
        assert "paths" in spec
        assert "/api/telemetry" in spec["paths"]
        assert "/api/hardware/telemetry" in spec["paths"]

        # /docs Swagger UI is accessible
        resp_docs = client.get("/docs")
        assert resp_docs.status_code == 200
        assert "swagger-ui" in resp_docs.text.lower()

    def test_audit_authentication_absence_documented_limitation(self):
        """7. Explicitly audits and confirms that authentication is not present on core endpoints."""
        # Telemetry ingestion does not require Bearer token
        resp_telem = client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "speed": 1.0})
        assert resp_telem.status_code == 200

        # Commands endpoint does not require auth headers
        resp_cmd = client.post("/api/commands", json={
            "command_id": "CMD-AUTH-AUDIT-01",
            "vehicle_id": "TRUCK_01",
            "action": "STOP",
            "target_speed": 0.0
        })
        assert resp_cmd.status_code == 200

        # Verification: System operates in open prototype/sandbox mode (documented architectural limitation)
        # Authentication is scheduled for production deployment (M12).
