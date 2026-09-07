"""
P10 — the final end-to-end chain, as a test.

The chain itself lives in `verify_p10_final.py` so there is ONE implementation: the demo
runs it for its trace, and this file asserts on the same evidence. Duplicating the walk
here would create a second version that could drift from the one the demo shows.

Provenance: SIMULATION / EMULATED. No physical ESP32.
"""

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import verify_p10_final as chain  # noqa: E402


@pytest.fixture(scope="module")
def evidence():
    """Walk the chain once; every test below reads the same evidence."""
    return chain.run_chain()


def test_every_hop_in_the_chain_passes(evidence):
    failed = ["%s (%s)" % (h["hop"], h["detail"]) for h in evidence.failed]
    assert not failed, "chain broken at: " + "; ".join(failed)


def test_the_chain_actually_walked_the_whole_path(evidence):
    """Guards against a chain that passes by doing almost nothing."""
    assert len(evidence.hops) >= 20
    assert len(evidence.trace) >= 10


@pytest.mark.parametrize("keyword", [
    "environment reaches the canonical Twin",
    "fog_safe result is held by the Twin",
    "dense fog lowers v_safe",
    "REFUSED",
    "local governor clamps",
    "canonical ingestion boundary",
    "single REST/WS shape",
    "game_ui displays",
    "recovers when the fog clears",
])
def test_named_hop_is_present_and_passing(evidence, keyword):
    """Each link of the P10 objective chain must be individually accounted for."""
    matches = [h for h in evidence.hops if keyword in h["hop"]]
    assert matches, "no hop covers %r" % keyword
    assert all(h["status"] == "PASS" for h in matches), matches


def test_trace_is_writable_and_complete(evidence, tmp_path):
    import csv

    path = chain.write_trace(evidence, str(tmp_path / "trace.csv"))
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == len(evidence.trace)
    assert set(rows[0]) == set(chain.TRACE_COLUMNS)
    # Every traced row carries provenance or says UNAVAILABLE - never a bare number.
    for row in rows:
        if row["v_safe_mps"]:
            assert row["source"], "a traced v_safe with no provenance"


def test_monotonicity_helper_rejects_a_bad_sweep():
    """The sweep check must be capable of failing, or it proves nothing."""
    good = [(50.0, 13.0), (10.0, 4.0), (50.0, 13.0)]
    bad = [(50.0, 13.0), (10.0, 20.0)]          # v_safe ROSE as visibility fell
    missing = [(50.0, 13.0), (10.0, None)]

    assert chain._monotonic_in_visibility(good) is True
    assert chain._monotonic_in_visibility(bad) is False
    assert chain._monotonic_in_visibility(missing) is False
