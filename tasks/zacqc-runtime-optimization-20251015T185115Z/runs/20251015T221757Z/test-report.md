# Test Report
- Command: `lean backtest .`
- Scope: Baseline rerun with performance logging enabled (captures final per-stage timings)
- Result: Completed successfully (run_id 1370479558)
- Wall runtime: 200.0 s (Start 2025-10-15T19:17:58Z → End 2025-10-15T19:21:18Z)
- Algorithm runtime (reported): 196.58 s processing 2,808,751 data points (≈14,000 pts/s)
- Warm-up duration: 4.39 s (engine start → first portfolio log)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms, metrics avg 0.14 ms, rally_update avg 0.01 ms, risk_checks avg 0.00 ms, strategy_logic avg 0.18 ms, total avg 0.06 ms (counts in file)
- Orders executed: 89; Logs emitted: 34,884 lines
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`, aggregated metrics JSON
