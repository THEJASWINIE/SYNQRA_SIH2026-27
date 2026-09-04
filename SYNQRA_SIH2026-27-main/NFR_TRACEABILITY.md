# TASK 2 Quality Requirements (NFR) Traceability Matrix

| ID | Quality Attribute | Requirement Description | Test/Evidence | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Determinism | Identical seeds must produce byte-for-byte matching states | Replay check with seed 999 | PASS | [VERIFICATION] |
| NFR-002 | Time resolution | Configurable timestep dt <= 1 s | Ran simulation with dt = 1.0s successfully | PASS | [VERIFICATION] |
| NFR-003 | Scale | Minimum 50 vehicles run successfully | Ran fleet sizes 10 to 100 without memory drops | PASS | [VERIFICATION] |
| NFR-004 | Performance | Executes faster than real-time | 1800s simulation runs in under 0.15s | PASS | [VERIFICATION] |
| NFR-005 | Traceability | All KPIs traceable to logged inputs | Results files results.json write correct metrics | PASS | [SIMULATION] |
| NFR-006 | Modularity | Modular classes can be tested independently | Modular unit tests discoverable | PASS | [VERIFICATION] |
| NFR-007 | Units | Internal SI units, display only at output | Internal values in m, s, kg, N, W | PASS | [MATHEMATICAL] |
| NFR-008 | Numerical safety | Prevent silent NaN/Inf propagation | NaN parameters trigger fallback boundaries | PASS | [VERIFICATION] |
| NFR-009 | Fail-safe fallback | Stale/loss events force conservative modes | Safe speed drops to 2.78 m/s on comm loss | PASS | [VERIFICATION] |
| NFR-010 | Interoperability | Standard JSON schemas validated | Validates state vector against HMI schema | PASS | [VERIFICATION] |
| NFR-011 | Reproducibility | Configuration bundle reproduces benchmarks | run_experiments.py bundles configs | PASS | [VERIFICATION] |
| NFR-012 | Visualization | Core simulator functions without 3D GUI | Verification suite runs cleanly in terminal | PASS | [VERIFICATION] |
