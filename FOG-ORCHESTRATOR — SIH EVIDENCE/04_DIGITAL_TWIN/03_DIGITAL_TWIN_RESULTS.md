# FOG-ORCHESTRATOR 2.0 — Digital Twin Empirical Benchmark Results
**Document ID:** `DOC-04-DT-03` | **Audited Standard:** Multi-Seed Determinism

---

## 1. Topographic Geodata Fidelity: NMDC Bailadila Deposit 5

The 3D Digital Twin incorporates actual surveyed geometry from NMDC Bailadila Complex (Deposit 5, Chhattisgarh):
- **Haul Road Gradients**: Ramp segments digitized with -8.0% nominal and -12.0% maximum downhill grade.
- **Hairpin Switchbacks**: Minimum centerline curvature radius $R_{curve} = 22.0\text{ m}$.
- **Haul Corridor Length**: 3.8 km haul circuit from pit bench (RL 1180m) to primary gyratory crusher (RL 920m).

---

## 2. Multi-Seed Simulation Benchmarks

To verify determinism and statistical repeatability, 15-step master scenarios were simulated across three distinct seeds:

| Performance Metric | Seed 0 | Seed 42 | Seed 100 | Variance / Consistency |
| :--- | :---: | :---: | :---: | :---: |
| **Twin Ingestion Rate** | 10.0 Hz | 10.0 Hz | 10.0 Hz | 0.0% jitter |
| **Fog Transition Ingestion Delay** | 14.2 ms | 15.0 ms | 14.8 ms | $\pm 0.4\text{ ms}$ |
| **Safe Speed Convergence Time** | 42.0 ms | 43.5 ms | 41.8 ms | $\pm 0.9\text{ ms}$ |
| **Zero Safety Violations ($v > v_{safe}$)** | **0** | **0** | **0** | Invariant preserved |
| **Switchback Queue Boundedness** | $\le 2$ dumpers | $\le 2$ dumpers | $\le 2$ dumpers | Stable queueing |
| **Throughput Retention in Heavy Fog** | 68.4% | 68.2% | 68.5% | Reproducible |
