"""
failsafe/__init__.py
--------------------
FOG-ORCHESTRATOR 2.0 Failsafe Package.
Autonomous failsafe mechanisms, Safe Beacon protocol, and standalone controller.
"""

from failsafe.safe_beacon import (
    SafeBeaconState,
    SafeBeaconSystemState,
    SafeBeaconMessage,
    SafeBeaconController,
    parse_safe_beacon,
    format_safe_beacon,
)

__all__ = [
    "SafeBeaconState",
    "SafeBeaconSystemState",
    "SafeBeaconMessage",
    "SafeBeaconController",
    "parse_safe_beacon",
    "format_safe_beacon",
]
