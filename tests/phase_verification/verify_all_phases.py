"""
MASTER VERIFICATION RUNNER — FOG-ORCHESTRATOR 2.0 ROADMAP
Executes Phase 1, Phase 2, and Phase 3 in sequence with strict gating rules.
"""

import sys
import time
from verify_phase1 import verify_phase1_hardware_hmi
from verify_phase2 import verify_phase2_digital_twin
from verify_phase3 import verify_phase3_final_integration


def main():
    print("#" * 70)
    print("      FOG-ORCHESTRATOR 2.0 -- MASTER ROADMAP VERIFICATION SUITE")
    print("      Date: 2026-08-28")
    print("#" * 70 + "\n")

    t_start = time.time()

    # Step 1: Phase 1 Hardware <-> HMI
    p1_pass = verify_phase1_hardware_hmi()
    if not p1_pass:
        print("\n[CRITICAL ERROR] Phase 1 Hardware <-> HMI verification FAILED!")
        sys.exit(1)

    # Step 2: Phase 2 Digital Twin (Separate)
    p2_pass = verify_phase2_digital_twin()
    if not p2_pass:
        print("\n[CRITICAL ERROR] Phase 2 Digital Twin verification FAILED!")
        sys.exit(1)

    # Step 3: Phase 3 Final Integration (Gated by P1 & P2 success)
    p3_pass = verify_phase3_final_integration()
    if not p3_pass:
        print("\n[CRITICAL ERROR] Phase 3 Final Integration FAILED!")
        sys.exit(1)

    t_elapsed = time.time() - t_start

    print("#" * 70)
    print("                      ALL PHASES VERIFIED 100% PASS")
    print("  Phase 1 -- Hardware <-> HMI:           [PASS]")
    print("  Phase 2 -- Digital Twin (Separate):    [PASS]")
    print("  Phase 3 -- Final Integration:         [PASS]")
    print(f"  Total Execution Time:                 {t_elapsed:.2f} seconds")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
