"""M1 backend smoke test: the health endpoint responds with a valid typed payload."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.health import SERVICE_NAME, HealthResponse

client = TestClient(app)


def test_health_returns_200_and_valid_schema() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200

    # Fails if the payload ever drifts from the declared schema.
    payload = HealthResponse.model_validate(response.json())
    assert payload.status == "ok"
    assert payload.service == SERVICE_NAME
    assert payload.milestone == "M1"


def test_health_timestamp_is_timezone_aware() -> None:
    """Data freshness (NFR-003) depends on unambiguous timestamps from the first line."""
    payload = HealthResponse.model_validate(client.get("/api/health").json())
    assert isinstance(payload.timestamp, datetime)
    assert payload.timestamp.tzinfo is not None
