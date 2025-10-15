# Test Report
- Command: `lean backtest .`
- Scope: Rally detector cache pruning + metrics_calculator max-down optimization + logging toggle defaults
- Result: Completed successfully (run_id 1134364430)
- Wall runtime: 89.4 s (Start 2025-10-15T19:39:51Z → End 2025-10-15T19:41:26Z)
- Algorithm runtime (reported): 89.44 s processing 2,808,751 data points (≈31,000 pts/s)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms / max 5.06 ms, metrics avg 0.13 ms / max 19.06 ms, rally_update avg 0.01 ms / max 2.80 ms, risk_checks avg 0.00 ms / max 2.78 ms, strategy_logic avg 0.17 ms / max 25.27 ms, total avg 0.33 ms / max 25.50 ms (n = 187,185)
- Orders executed: 89; Order hash: 84e79bd641b57df60c29386afb1ecca5 (matches baseline)
- Logs emitted: 20 algorithm lines / 153 engine lines (down from 34,884 / 34,809 before optimizations)
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`
