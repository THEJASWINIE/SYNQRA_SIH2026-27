import sys
import os

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
digital_twin_root = os.path.join(workspace_root, "SYNQRA_SIH2026-27-main")

if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
if digital_twin_root not in sys.path:
    sys.path.insert(0, digital_twin_root)
