# Test Report
- Command: `lean backtest .`
- Scope: After risk-check gating + consolidated-bar short-circuit optimizations
- Result: Completed successfully (run_id 1596293644)
- Wall runtime: 100.0 s (Start 2025-10-15T19:25:38Z → End 2025-10-15T19:27:18Z)
- Algorithm runtime (reported): 96.64 s processing 2,808,751 data points (≈29,000 pts/s)
- Warm-up duration: 4.32 s
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms, metrics avg 0.14 ms, rally_update avg 0.01 ms, risk_checks avg 0.00 ms, strategy_logic avg 0.18 ms, total avg 0.36 ms (counts now 187,185)
- Orders executed: 89; Logs emitted: 34,885 lines
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`, optimized metrics JSON
