# Test Report
- Command: `lean backtest .`
- Scope: Metrics caching + lightweight perf collector refactor
- Result: Completed successfully (run_id 1684470332)
- Wall runtime: 82.1 s (Start 2025-10-15T20:09:37Z → End 2025-10-15T20:10:54Z)
- Algorithm runtime (reported): 73.85 s processing 2,808,751 data points (≈38,000 pts/s)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms, metrics avg 0.05 ms, rally_update avg 0.01 ms, risk_checks avg 0.00 ms, strategy_logic avg 0.16 ms, total avg 0.24 ms (counts 187,185)
- Orders executed: 89; Logs emitted: 21 lines
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`
