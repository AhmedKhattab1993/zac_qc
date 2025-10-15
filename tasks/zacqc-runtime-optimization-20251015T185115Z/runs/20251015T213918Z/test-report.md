# Test Report
- Command: `lean backtest ZacQC`
- Scope: Max-down metrics optimization (single-pass window scan)
- Result: Completed successfully (run_id 1240157994)
- Wall runtime: 65.0 s (Start 2025-10-15T21:39:23Z → End 2025-10-15T21:40:28Z)
- Algorithm throughput: ≈43.2k data points/s over 2,808,751 points (reported runtime 65.0 s)
- Final per-stage latencies (`PERF_FINAL_AGG`): data_manager avg 0.00 ms / max 0.20 ms, metrics avg 0.05 ms / max 5.31 ms, rally_update avg 0.01 ms / max 7.92 ms, risk_checks avg 0.00 ms / max 0.10 ms, strategy_logic avg 0.11 ms / max 24.41 ms, total avg 0.19 ms / max 24.51 ms (n = 187,185)
- Orders executed: 89; Order hash: 84e79bd641b57df60c29386afb1ecca5
- Outputs saved: `summary.json`, `engine-log.txt`, `algorithm-log.txt`
