# VISIBILITY VS SAFE SPEED BENCHMARK REPORT
## FOG-ORCHESTRATOR 2.0 — Canonical Safety Operating Envelope

### Reference Context: BEML BH100 (165.5 t GVM) on -8% Ramp Grade

| Visibility (m) | Safe Speed (m/s) | Safe Speed (km/h) | S_stop (m) | Safety Margin (m) | Vehicle State | Production Eligibility |
|---|---|---|---|---|---|---|
| 100.0 | 11.1110 | 40.00 | 27.02 | 67.98 | `NORMAL_GOVERNED` | FULL_PRODUCTION |
| 50.0 | 11.1110 | 40.00 | 27.02 | 17.98 | `NORMAL_GOVERNED` | FULL_PRODUCTION |
| 25.0 | 9.4082 | 33.87 | 20.00 | 0.00 | `FOG_RESTRICTED_CRAWL` | REDUCED_SPEED_PRODUCTION |
| 12.0 | 5.1449 | 18.52 | 7.00 | -0.00 | `FOG_RESTRICTED_CRAWL` | REDUCED_SPEED_PRODUCTION |
| 10.0 | 4.1989 | 15.12 | 5.00 | 0.00 | `FOG_RESTRICTED_CRAWL` | REDUCED_SPEED_PRODUCTION |
| 8.0 | 3.0481 | 10.97 | 3.00 | 0.00 | `FOG_RESTRICTED_CRAWL` | REDUCED_SPEED_PRODUCTION |
| 5.0 | 0.0000 | 0.00 | 0.00 | 5.00 | `CONTROLLED_STOP_STAGED` | ZERO_THROUGHPUT_STAGED |
| 4.0 | 0.0000 | 0.00 | 0.00 | 4.00 | `CONTROLLED_STOP_STAGED` | ZERO_THROUGHPUT_STAGED |
| 3.0 | 0.0000 | 0.00 | 0.00 | 3.00 | `CONTROLLED_STOP_STAGED` | ZERO_THROUGHPUT_STAGED |

### Mandatory Safety Finding:
When visibility drops to $R_v \le 5.0\text{ m}$, the available sightline is fully absorbed by the $S_{\text{base}} = 5.0\text{ m}$ safety buffer. The analytical quadratic root yields $v_{\text{safe}} = 0.00\text{ m/s}$. The system strictly commands a **CONTROLLED STOP / STAGED STATE**, proving that production is never forced through an unsafe visibility regime.
