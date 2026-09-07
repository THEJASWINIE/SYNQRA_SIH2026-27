"""
Project-anchored configuration paths (P7).

P6.1 browser verification found that adapters resolved
`config/physical_vehicle_parameters.json` relative to the PROCESS WORKING DIRECTORY.
Launching uvicorn from `SYNQRA_SIH2026-27-HMI/backend/` therefore silently produced an
uncalibrated UnitConverter, and a speed legitimately derived from a MEASURED wheel RPM
came back unavailable.

Configuration must be found from a stable location, so it resolves identically no matter
where the process was started. Parameter VALUES are unchanged - only how the file is
located.
"""

import os

# This file lives in <project_root>/integration_adapters/, so the project root is one up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")


def config_path(filename: str) -> str:
    """Absolute path to a project configuration file, independent of the current CWD."""
    return os.path.join(CONFIG_DIR, filename)


# ---------------------------------------------------------------------------
# Timing / freshness thresholds (P9)
#
# These live in `config/integration_config.json` and were previously re-typed as literals
# at each use site: `stale_after_s=3.0` in the HMI backend, `safety_stale_after_s=3.0` in
# the command gateway, `3.0 / 10.0` in the serial reader. Two copies of a safety-relevant
# threshold drift the moment one is tuned, so the file is now the single source and the
# literals below are the documented fallback used only when it cannot be read.
# ---------------------------------------------------------------------------

import json
import logging

_TIMEOUT_DEFAULTS = {
    "max_telemetry_age_seconds": 3.0,      # a telemetry field older than this is STALE
    "offline_threshold_seconds": 10.0,     # a link silent this long is OFFLINE
    "max_recommendation_age_seconds": 5.0, # command validity window
    "command_ack_timeout_seconds": 3.0,    # no ACK within this -> TIMEOUT
}


def load_timeouts() -> dict:
    """
    Configured timing thresholds, in seconds.

    Never raises: unreadable configuration must not stop a service from starting, and the
    fallback is the same value the file ships with, logged so the substitution is visible.
    """
    try:
        with open(config_path("integration_config.json"), "r", encoding="utf-8") as handle:
            configured = json.load(handle).get("timeouts", {})
        return {k: float(configured.get(k, v)) for k, v in _TIMEOUT_DEFAULTS.items()}
    except Exception as exc:  # noqa: BLE001 - configuration must never break startup
        logging.getLogger("config_paths").warning(
            "Could not read integration_config.json (%s); using documented defaults.", exc
        )
        return dict(_TIMEOUT_DEFAULTS)
