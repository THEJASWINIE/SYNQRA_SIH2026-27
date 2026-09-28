"""Health response schema — M1 foundation only.

Scope note: this is the *service* health of the HMI backend process itself. It is
deliberately NOT the `Health` / `SystemHealth` message from
`requirements/task1-data-contract.md` §9, which describes component and link health
supplied by Task 2 and lands in M2. Keeping the two separate stops M1 from
front-running the data contract.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

SERVICE_NAME = "fog-orchestrator-hmi-backend"
SERVICE_VERSION = "0.1.0"
MILESTONE = "M1"


class HealthResponse(BaseModel):
    """Structured, typed health payload."""

    status: Literal["ok"] = "ok"
    service: str = SERVICE_NAME
    version: str = SERVICE_VERSION
    milestone: str = MILESTONE
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
