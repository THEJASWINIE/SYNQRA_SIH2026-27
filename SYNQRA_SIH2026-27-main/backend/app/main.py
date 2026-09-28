"""FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend.

M1 foundation. This service exposes a health endpoint and nothing else.

Scope boundary (see `CLAUDE.md`, `requirements/DECISIONS.md` PAD-A/B/E):
this process performs no Digital Twin computation, no physics, no prediction,
no optimization and no simulation. It issues no command and no actuation.
Task 2 data will arrive through a provider in M12 and is only ever visualized.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas.health import SERVICE_VERSION, HealthResponse

app = FastAPI(
    title="FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend",
    version=SERVICE_VERSION,
    summary="Supervisory HMI backend. Advisory only; performs no safety computation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    """Liveness of this service. Used by the frontend as its connectivity proof."""
    return HealthResponse()
