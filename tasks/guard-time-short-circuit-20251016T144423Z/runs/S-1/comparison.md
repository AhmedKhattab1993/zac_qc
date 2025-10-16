# Baseline vs Guard Short-Circuit Comparison

| Metric | Baseline (2025-10-16 15:23) | Guard Short-Circuit (2025-10-16 15:14) | Delta |
| --- | --- | --- | --- |
| Runtime (wall-clock) | 56.11 s | 54.82 s | -1.29 s (-2.3%) |
| Total Orders | 157 | 157 | 0 |
| OrderListHash | 770eef5fb78706619ac4b315c18e4142 | 770eef5fb78706619ac4b315c18e4142 | identical |
| PERF_FINAL_AGG avg total | 0.13 ms | 0.12 ms | -0.01 ms (-7.7%) |
| PERF_FINAL_AGG max total | 24.86 ms | 33.88 ms | +9.02 ms* |

*Higher max in the feature run stems from a single cycle spike; average latency still improved. Order timelines and P&L remain unchanged.

Artifacts:
- Baseline: `runs/S-1/baseline-20251016T1523/`
- Feature: `runs/S-1/20251016T1514/`
