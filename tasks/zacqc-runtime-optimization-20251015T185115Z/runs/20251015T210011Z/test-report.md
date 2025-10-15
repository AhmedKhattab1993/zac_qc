# Test Report
- Command: `lean backtest ZacQC`
- Scope: RallyDetector sample struct optimization + single-pass state evaluation
- Result: Completed successfully (run_id 1409207371)
- Wall runtime: 66.0 s (Start 2025-10-15T21:00:11Z → End 2025-10-15T21:01:17Z)
- Algorithm runtime (reported): 63.28 s processing 2,808,751 data points (≈44,000 pts/s)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms, metrics avg 0.05 ms (max 15.02 ms), rally_update avg 0.01 ms, risk_checks avg 0.00 ms, strategy_logic avg 0.11 ms (max 24.64 ms), total avg 0.19 ms (max 29.31 ms)
- Orders executed: 89; Logs emitted: 21 lines; Order hash unchanged (`84e79bd641b57df60c29386afb1ecca5`)
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`
