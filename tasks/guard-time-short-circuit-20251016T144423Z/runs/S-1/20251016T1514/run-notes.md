# Lean Backtest Post-Change — 2025-10-16T15:14 (local)

- Command: `lean backtest ZacQC`
- Status: **Success** (run time 54.8 s wall clock, 2.81M data points)
- Key stats (from summary.json):
  - Total Orders: 157
  - Net Profit: 0.248%
  - Sharpe Ratio: 0.896
  - OrderListHash: 770eef5fb78706619ac4b315c18e4142
- PERF_FINAL aggregate avg total time: 0.12 ms (max 33.88 ms) across 187,185 cycles.
- Files captured: `summary.json`, `orders.json`, `Lean.log`
- Next: capture baseline (pre-change) run for comparison and diff the `order-events.json` + `summary.json` for parity, then evaluate perf delta vs baseline.
