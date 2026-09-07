"""
Path setup so this sub-repository's suite can run standalone.

Since P2, `models/vehicle_physics.py` is a compatibility adapter over the authoritative
`fog_safe` engine, which lives at the WORKSPACE root rather than inside this
sub-repository. Running `pytest tests` from within `SYNQRA_SIH2026-27-main/` therefore
needs the workspace root on `sys.path`.

This mirrors the existing root-level `tests/conftest.py`. It adds paths only; it changes
no behaviour and imports nothing.
"""

import os
import sys

subrepo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
workspace_root = os.path.abspath(os.path.join(subrepo_root, ".."))

for path in (subrepo_root, workspace_root):
    if path not in sys.path:
        sys.path.insert(0, path)
