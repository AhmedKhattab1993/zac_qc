# Runtime Comparison (Baseline vs Optimized)

| Metric | Baseline (run_id 1370479558) | Optimized v1 (run_id 1596293644) | Optimized v2 (run_id 1134364430) | Optimized v3 (run_id 1684470332) | Optimized v4 (run_id 1969908674) | Optimized v5 (run_id 1791976862) | Δ vs Baseline† | Δ v2→v1 | Δ v3→v2 | Δ v4→v3 | Δ v5→v4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Algorithm runtime (s) | 196.58 | 96.64 | 89.44 | 73.85 | 65.67 | 63.60 | -67.6% | -7.5% | -17.4% | -11.1% | -3.2% |
| Wall runtime (s) | 200.0 | 100.0 | 96.1 | 82.1 | 72.2 | 70.7 | -64.6% | -3.9% | -14.6% | -12.1% | -2.1% |
| Data points per second | 14,000 | 29,000 | 31,000 | 38,000 | 43,000 | 44,000 | +3.1× | +7% | +23% | +13% | +2% |
| `total` avg latency (ms) | 0.06 | 0.36* | 0.33* | 0.24* | 0.20* | 0.19* | +0.13 | -0.03 | -0.09 | -0.04 | -0.01 |
| `total` samples | 2,808,000 | 187,185 | 187,185 | 187,185 | 187,185 | 187,185 | -93% | 0% | 0% | 0% | 0% |
| Log lines (algo / engine) | — | 34,884 / 34,809 | 20 / 153 | 20 / 100 | 20 / 102 | 20 / 101 | — | -99.9% | engine -35% | engine +2% | engine -1% |
| Order count | 89 | 89 | 89 | 89 | 89 | 89 | unchanged | unchanged | unchanged | unchanged | unchanged |

†Δ vs Baseline compares the latest optimized run (v5) against the original baseline.

*Avg latency now measures only consolidated-bar events (counts dropped from ~2.8M to 187k), so overall time falls despite higher per-event average.
