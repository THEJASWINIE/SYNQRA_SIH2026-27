# Contract fixtures

Cross-language artifact (MAD-C). Parsed by **both** the TypeScript tests
(`frontend/src/data/*.test.ts`) and the Python tests
(`backend/tests/test_contract_parity.py`), so that a TypeScript schema and its Pydantic
mirror cannot silently disagree.

## What these are

Minimal, schema-oriented examples of each contract message shape. One valid fixture per
message, plus invalid variants used by validation tests.

## What these are NOT

**Not mock scenarios.** They encode no mine dynamics, no fog progression, no vehicle
trajectory, no queue evolution and no dispatch behaviour. Values are placeholders chosen
to exercise the schema, not to look plausible.

Mock scenarios are M3 and live elsewhere. A fixture that starts telling a story about the
mine has become a scenario and is out of place here.

## Layout

- `valid/<MessageType>.json` — one minimal valid payload per message
- `invalid/<case>.json` — payloads that must fail validation, named for the defect

Field names are snake_case throughout: these represent the **wire format** (MAD-E), not
the normalized domain shape.
