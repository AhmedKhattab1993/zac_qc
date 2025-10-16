# Referenced Expertise

## Scan @ 2025-10-15T21:59:10Z
- Keywords: quantconnect performance, lean backtest, profiling, rolling window, optimization

### Key Findings
- `experts/lean_python_perf.md`: Reinforces "correctness first" with golden baseline diffs, emphasizes profiling before optimizations, and recommends incremental RollingWindow updates plus batching `History()` calls to avoid redundant work.
- `experts/trading_perf.md`: Provides a profiling protocol (macro wall-clock + micro sampling) and highlights hoisting invariants, caching high-hit computations, and documenting SLOs for bars/sec and peak memory.
- `experts/lean_unix_run.md`: Details Lean CLI backtest outputs (`backtests/<timestamp>/results.json`) and suggests using JSON/CLI artifacts for performance analysis.

### Context Excerpts (-C2)
```text
experts/lean_python_perf.md: Correctness first. Never accept speed that changes fills... Profile → change → re-measure... Use RollingWindow to maintain state; avoid repeated History() calls.
experts/trading_perf.md: Confirm baseline metrics, profile to find top offenders, pick smallest change with biggest impact... Hoist invariant work out of loops; cache high-hit pure computations.
experts/lean_unix_run.md: Lean creates a backtests/<timestamp>/ folder with results.json for every run; inspect these outputs for performance and regression comparisons.
```

### Top Files (by relevance)
- experts/lean_python_perf.md
- experts/trading_perf.md
- experts/lean_unix_run.md
