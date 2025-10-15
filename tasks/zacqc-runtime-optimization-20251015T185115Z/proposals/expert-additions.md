# Proposed Additions/Updates to `experts/`

## Lean Performance Regression Harness
- **Keywords:** lean cli, performance benchmarking, regression metrics, baseline diffing
- **Rationale:** Plan requires a repeatable way to collect and diff Lean runtime metrics (bars/sec, OnData latency, warm-up duration) across optimization loops; existing expert docs do not cover harness design or artifact retention.
- **Proposed outline:**
  - Define canonical baseline scenarios and hardware assumptions.
  - Detail tooling for cProfile/line-profiler integration with Lean CLI runs.
  - Describe metrics storage (CSV/JSON) and diff thresholds for acceptance.
  - Provide checklist for automating nightly perf regression jobs.
- **Sources/lessons:** Insights while drafting `tasks/zacqc-runtime-optimization-20251015T185115Z/plan.md` and referencing `Experts/lean_python_perf.md` + `Experts/trading_perf.md`.
