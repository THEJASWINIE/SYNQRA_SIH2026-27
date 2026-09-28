"""Cross-language contract parity — M2. Required test category 16.

Validates the SAME fixtures the TypeScript tests use (``contracts/fixtures/``, MAD-C), so
a TypeScript schema and its Pydantic mirror cannot silently drift apart.

This is what turns the backend mirrors from dormant code into an active guard: without it
the two type sets could disagree for months and nothing would notice until M12.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.contracts.messages import CONTRACT_MESSAGES

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
VALID_DIR = FIXTURE_ROOT / "valid"
INVALID_DIR = FIXTURE_ROOT / "invalid"
UNKNOWN_ENUM_DIR = FIXTURE_ROOT / "unknown-enum"


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _message_type_from_filename(path: Path) -> str:
    """Fixture files are named ``<MessageType>__<case>.json``."""
    return path.stem.split("__")[0]


def test_fixture_root_exists() -> None:
    assert FIXTURE_ROOT.is_dir(), f"fixtures not found at {FIXTURE_ROOT}"


def test_all_fifteen_contract_messages_are_mirrored() -> None:
    assert len(CONTRACT_MESSAGES) == 15


def test_every_contract_message_has_a_valid_fixture() -> None:
    """Parity is only meaningful if both sides are exercised on the same shapes."""
    missing = [name for name in CONTRACT_MESSAGES if not (VALID_DIR / f"{name}.json").is_file()]
    assert missing == [], f"contract messages without a fixture: {missing}"


@pytest.mark.parametrize("message_type", sorted(CONTRACT_MESSAGES))
def test_valid_fixture_accepted(message_type: str) -> None:
    model = CONTRACT_MESSAGES[message_type]
    payload = _load(VALID_DIR / f"{message_type}.json")
    model.model_validate(payload)


@pytest.mark.parametrize("fixture_path", sorted(INVALID_DIR.glob("*.json")), ids=lambda p: p.name)
def test_invalid_fixture_rejected(fixture_path: Path) -> None:
    """A supplied-but-malformed payload must fail validation.

    It is INVALID, never MISSING — the distinction the frontend relies on.
    """
    message_type = _message_type_from_filename(fixture_path)
    model = CONTRACT_MESSAGES[message_type]
    with pytest.raises(ValidationError):
        model.model_validate(_load(fixture_path))


@pytest.mark.parametrize(
    "fixture_path", sorted(UNKNOWN_ENUM_DIR.glob("*.json")), ids=lambda p: p.name
)
def test_unknown_enum_fixture_accepted(fixture_path: Path) -> None:
    """An unrecognised tolerant-enum value must NOT reject the message (contract E-03).

    Both languages accept it; mapping to UNKNOWN is normalization's job.
    """
    message_type = _message_type_from_filename(fixture_path)
    model = CONTRACT_MESSAGES[message_type]
    model.model_validate(_load(fixture_path))


def test_unexpected_field_is_rejected() -> None:
    """Producer and contract disagreeing should surface, not be silently dropped."""
    payload = dict(_load(VALID_DIR / "SafetyState.json"))  # type: ignore[arg-type]
    payload["not_in_the_contract"] = 1
    with pytest.raises(ValidationError):
        CONTRACT_MESSAGES["SafetyState"].model_validate(payload)


def test_absent_optional_stays_none_and_is_not_coerced_to_zero() -> None:
    """PAD-F: an unsupplied value must never become 0."""
    kpis = CONTRACT_MESSAGES["KpiSnapshot"].model_validate(_load(VALID_DIR / "KpiSnapshot.json"))
    assert kpis.throughput_tph is None  # type: ignore[attr-defined]
    assert kpis.cycle_time_s is None  # type: ignore[attr-defined]
