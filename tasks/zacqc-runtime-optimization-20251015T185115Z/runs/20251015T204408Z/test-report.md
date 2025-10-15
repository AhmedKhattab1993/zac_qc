# Test Report
- Command: `lean backtest ZacQC`
- Scope: RallyDetector per-bar caching for long/short momentum gates
- Result: Completed successfully (run_id 1791976862)
- Wall runtime: 70.7 s (Start 2025-10-15T20:44:08Z → End 2025-10-15T20:45:16Z)
- Algorithm runtime (reported): 63.60 s processing 2,808,751 data points (≈44,000 pts/s)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms, metrics avg 0.04 ms, rally_update avg 0.01 ms, risk_checks avg 0.00 ms, strategy_logic avg 0.11 ms, total avg 0.19 ms (counts 187,185)
- Orders executed: 89; Logs emitted: 21 lines
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`
