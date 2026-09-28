"""Contract primitives — Pydantic mirror. M2.

Source of truth: ``requirements/task1-data-contract.md`` §1.

These mirror the TypeScript contract in ``frontend/src/contracts/``. Field names are the
contract's snake_case, matching the wire format (MAD-E) — which is also what the shared
fixtures in ``contracts/fixtures/`` contain, so both languages validate the same bytes.

Scope: shapes only. Nothing here computes an operational value.
"""

from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict

# ISO-8601, UTC, millisecond precision. Kept as the exact string the source sent.
Iso8601 = str

VehicleId = str
SegmentId = str
NodeId = str
SlotId = str
CommandId = str
RouteId = str
ComponentId = str

T = TypeVar("T")

#: Data quality. Contract §1.
#:
#: MISSING — the complete datum was NOT supplied.
#: INVALID — the datum WAS supplied but failed validation.
#: STALE   — valid, but older than the configured threshold. Value is retained.
#: OK      — valid and within the threshold.
#:
#: A malformed payload must never become MISSING, and an INVALID datum is never also
#: reported as STALE.
Quality = Literal["OK", "STALE", "MISSING", "INVALID"]


class StrictModel(BaseModel):
    """Base for every contract mirror.

    ``extra="forbid"`` matters: an unexpected field means the producer and this contract
    disagree, and that should surface as a validation failure rather than be silently
    dropped.
    """

    model_config = ConfigDict(extra="forbid")


class Estimate(StrictModel):
    """A value with its supplied uncertainty. Contract §1."""

    value: float | None
    sigma: float | None
