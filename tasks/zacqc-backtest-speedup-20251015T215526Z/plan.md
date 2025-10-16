# Plan

## Task Overview
ZacQC’s QuantConnect Lean backtests currently take roughly 65 seconds to execute the default 15-symbol configuration (2025-10-01 to 2025-10-10). The user needs at least a 25% reduction in end-to-end runtime without regressing trading outcomes or risk controls. The stack mixes Python QCAlgorithm modules (data/metrics/strategy) orchestrated by Lean CLI on macOS. Optimization must retain identical trading decisions and support repeatable benchmarking. Plan assumes we can instrument the pipeline locally and adjust Python modules, Lean configuration, or data access patterns while staying within existing infrastructure.

## Definition of Ready (DoR)
- Clarifications resolved: pending answers to Critical questions below
- Test strategy agreed (matrix): baseline vs optimized Lean backtest runtime, regression of order/trade outputs
- Rollout strategy (flag/canary/batch): gated by reproducible benchmark script; no production rollout planned
- Data/backfill owner assigned (if applicable): not applicable (performance-only change)

## Clarification Questions
- [Critical] Can we treat the current Lean backtest (parameters.py default window, 15 symbols, start 2025-10-01, end 2025-10-10) as the canonical baseline for timing and trade-by-trade regression?
- [Critical] Are there tolerances for minor floating-point variations (e.g., VWAP rounding) if we restructure computations, or must fills/orders match exactly?
- [Nice] Should the performance harness target single-threaded runs only, or document CPU affinity/cores to normalize comparisons across machines?

## Constraints & Requirements
- Performance: ≥25% reduction in Lean backtest wall-clock time vs baseline, measured on same machine with warmed cache; zero increase in peak memory >10% without approval.
- Security/Compliance: No new external services; avoid persisting sensitive trading configs outside repo.
- Compatibility: Must run with current Lean CLI tooling and QuantConnect Algorithm Python environment on macOS (Apple Silicon); preserve interface for frontend/config_api interactions.
- Delivery: Target completion by 2025-10-18 to unblock follow-on tuning.
- Reliability/Availability: Backtests must complete successfully with identical order events and risk limit enforcement.
- Observability: Emit structured timing logs/metrics around key algorithm stages (data loading, strategy, metrics, risk) and collect benchmark artifacts under feature dir.
- Cost: No paid data downloads or cloud spend; reuse local data cache.

## Dependencies
- Internal: `ZacQC/config/parameters.py`, `ZacQC/main.py`, `ZacQC/data/data_manager.py`, `ZacQC/data/metrics_calculator.py`, `ZacQC/trading/*`, `frontend/config_api.py`
- External: QuantConnect Lean CLI, local market data cache under `data/`, Python runtime packaged with Lean, system profiler tools (`time`, `cProfile`, `py-spy`)

## User Stories

### Story [S-1]: Establish reproducible performance baseline
- Story ID: S-1 | Priority: P0 | Owner: Codex | Due: 2025-10-16
- User Story: As the maintainer, I want a deterministic benchmarking harness for the default ZacQC backtest so that I can quantify runtime reductions and detect regressions.
- Dependencies: Lean CLI, `frontend/config_api.py` trigger path, access to local data cache | Non-goals: production deployment automation

#### Acceptance Criteria
- Given the default parameters, When I run the baseline benchmark script, Then it records wall-clock, CPU time, and summary metrics under `$FEATURE_DIR/benchmarks/`.
- Given a subsequent optimization, When I rerun the benchmark, Then it compares runtime vs baseline and produces pass/fail verdict for ≥25% speedup target.

#### Story Definition of Ready (DoR)
- Clarifications: confirm baseline scenario, confirm acceptable variance window.
- Test strategy: smoke Lean backtest run + instrumentation assertions.
- Data/backfill: ensure necessary equity second-resolution data is cached locally.

#### Tasks Checklist
- [x] Capture baseline runtime via `/usr/bin/time` (or equivalent) and store raw outputs.
- [x] Create benchmark runner script/notebook under `$FEATURE_DIR` automating repeated Lean invocations.
- [x] Archive baseline logs, summary JSON, and timing artifacts.

#### Story Tests to Run
- Integration: `lean backtest ZacQC --no-update` wrapped by benchmark script (3 runs, median recorded).

#### Story Definition of Done (DoD)
- Baseline timings stored; reference decision log updated; harness documented for reuse.

#### Story Implementation Plan
- Inventory existing backtest outputs to confirm parameter scope and run duration.
- Build shell/python wrapper to call Lean with consistent flags and parse summary JSON.
- Persist metrics (wall-clock, CPU time, memory if available) and trade count for regression checks.
- Document usage in `$FEATURE_DIR/plan.md` Tests section and update decision log.

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — execute listed commands for S-1; save logs/metrics; update Decision Log `[S-1]`.
2) Diagnose — summarize failures or anomalies; revisit expertise if blocked.
3) Plan — outline micro-fix, impacted files, and rollback.
4) Change — implement minimal harness updates tagged `[S-1/T-x]`.
5) Re-Test & Compare — rerun benchmark; store delta vs baseline.
6) Decide — mark story complete when AC satisfied; otherwise iterate or escalate.

#### Story Runbook & Logs
- Test matrix: benchmark script invoking Lean backtest.
- Logs: `$FEATURE_DIR/runs/S-1/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-1/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-1]`
- Artifacts: `$FEATURE_DIR/benchmarks/` for timing CSV/JSON.

#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: optional automation to parse Lean logs.
- Inputs: baseline command, log path.
- Acceptance: script outputs metrics table and stores under benchmarks.

#### Links/Artifacts
- Baseline artifacts: `tasks/zacqc-backtest-speedup-20251015T215526Z/runs/baseline/20251015T221344/run_01/summary.json`

### Story [S-2]: Optimize critical data & metrics path
- Story ID: S-2 | Priority: P0 | Owner: Codex | Due: 2025-10-18
- User Story: As the algorithm developer, I want to reduce DataManager/MetricsCalculator overhead so that Lean spends less time per 15-second bar while producing identical signals.
- Dependencies: `data/data_manager.py`, `data/metrics_calculator.py`, `core/strategy.py` | Non-goals: altering trading logic or resolution.

#### Acceptance Criteria
- Given a backtest run with optimizations enabled, When compared to baseline logs, Then per-stage timings for data/metrics drop by ≥25%.
- Given production parameters, When the optimized run completes, Then generated order events and summary JSON match baseline within tolerance (identical trade count, PnL, and order list).

#### Story Definition of Ready (DoR)
- Clarifications: confirm acceptable instrumentation overhead.
- Test strategy: targeted unit/perf tests for metrics functions + full Lean regression.
- Data/backfill: rely on existing cached minute/daily history.

#### Tasks Checklist
- [ ] Profile hot paths (cProfile/line_profiler) to rank cost centers.
- [ ] Refactor/correct caches, rolling window usage, and redundant calculations.
- [ ] Add micro-benchmarks or unit tests covering optimized methods.

#### Story Tests to Run
- Unit: targeted pytest modules if available (add as needed).
- Integration: benchmark script comparing baseline vs optimized Lean runs.

#### Story Definition of Done (DoD)
- ≥25% runtime savings observed in benchmark; no regression in trade outputs; code documented via inline comments and changelog entry in plan artifacts.

#### Story Implementation Plan
- Instrument `main.py` performance tracking to emit stage timings into logs/metrics.
- Optimize DataManager historical load (avoid redundant `History` calls, reduce RollingWindow resets).
- Cache metrics recalculated every OnData invocation (e.g., 30DMA, VWAP) using incremental updates.
- Evaluate symbol loop to skip processing when data missing and avoid repeated attribute lookups.
- Update risk/strategy modules to leverage cached metrics instead of recomputing.

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — gather profiler snapshots and baseline metrics.
2) Diagnose — isolate top hotspots; confirm with follow-up sampling.
3) Plan — record micro-plan (files, rollback note) in Decision Log.
4) Change — apply minimal refactors tagged `[S-2/T-x]`.
5) Re-Test & Compare — run Lean benchmark; validate metrics/trade parity.
6) Decide — accept improvements meeting target; otherwise iterate or escalate.

#### Story Runbook & Logs
- Test matrix: profiler commands + Lean runs.
- Logs: `$FEATURE_DIR/runs/S-2/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-2/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-2]`
- Artifacts: `$FEATURE_DIR/benchmarks/optimized-*.json` snapshots.

#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: assist in cProfile output parsing or generating flamegraphs.
- Inputs: raw profiler stats.
- Acceptance: summarized hotspots plus annotated diff suggestions.

#### Links/Artifacts
- Consult local expert docs on Python performance if available.

### Story [S-3]: Validate regressions & document optimization
- Story ID: S-3 | Priority: P1 | Owner: Codex | Due: 2025-10-18
- User Story: As a reviewer, I want automated regression comparisons and documentation so that future runs can trust the optimized algorithm.
- Dependencies: Benchmark artifacts, `experts/` documentation | Non-goals: full CI integration today.

#### Acceptance Criteria
- Given optimized code, When regression script runs, Then it confirms trade parity (orders, fills, PnL) with baseline within zero-diff tolerance.
- Given optimizations complete, When reviewing docs, Then changelog/README updates describe new performance tools and usage.

#### Story Definition of Ready (DoR)
- Clarifications: confirm documentation targets (README vs docs/).
- Test strategy: diff order JSON, summary stats; lint docs.
- Data/backfill: reuse existing outputs.

#### Tasks Checklist
- [ ] Implement comparison tool to diff `order-events.json`, `summary.json`, and stage timing logs.
- [ ] Update relevant documentation (README, docs) with optimization summary and usage.
- [ ] Capture final benchmark and regression evidence in artifacts.

#### Story Tests to Run
- Integration: regression comparison script.
- Docs: run formatting/lint checks as applicable.

#### Story Definition of Done (DoD)
- Regression script passes; docs updated; final benchmark shows ≥25% gain; decision log records closure.

#### Story Implementation Plan
- Build Python utility to load baseline vs optimized JSON files and assert equality/tolerances.
- Add CLI entry in `$FEATURE_DIR` to automate comparisons and produce markdown summary.
- Update README or `docs/` with optimization steps, benchmark numbers, and usage guide.
- Archive artifacts in `$FEATURE_DIR/artifacts/`.

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — execute regression script and collect outputs.
2) Diagnose — address discrepancies (data/time mismatches) promptly.
3) Plan — outline corrective actions and rollback path.
4) Change — update script/docs tagged `[S-3/T-x]`.
5) Re-Test & Compare — rerun regression checks; ensure docs lint clean.
6) Decide — sign off when parity & documentation verified.

#### Story Runbook & Logs
- Test matrix: regression script vs baseline/optimized artifacts.
- Logs: `$FEATURE_DIR/runs/S-3/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-3/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-3]`
- Artifacts: `$FEATURE_DIR/artifacts/` for markdown summary & final benchmark chart.

#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: optional doc formatting assistance.
- Inputs: raw benchmark numbers, diff outputs.
- Acceptance: polished markdown summary referencing artifacts.

#### Links/Artifacts
- Baseline vs optimized outputs recorded under `$FEATURE_DIR/benchmarks/`.

## Checklist of Subtasks
- [ ] Plan & Setup (repo/env ready, confirm requirements)
- [ ] Design Solution (modules, performance strategy)
- [ ] Implement Core Functionality (harness + optimizations)
- [ ] Integrate Components (ensure Lean + scripts work together)
- [ ] Testing (benchmarks, regression diffs)
- [ ] Optimization (iterative profiling and tuning)
- [ ] Documentation & Final Review (benchmarks, README updates)

## Definition of Done (DoD)
- Functional: Lean backtest completes with identical trading results and no runtime errors.
- Quality: lint/tests (if touched) pass; new scripts adhere to repo style.
- UX/API: CLI/backtest entrypoints unchanged; instrumentation toggles documented.
- Docs: Benchmark methodology and results captured in repo artifacts (README/docs + decision log).
- Tests: Benchmark script, regression diff tool, and Lean run executed with ≥25% runtime improvement validated.

## Tests to Run
- Unit: `pytest -q` (for any new unit tests added around metrics utilities).
- Integration: `$FEATURE_DIR/benchmarks/run_backtest.sh` (baseline + optimized).
- Regression: `$FEATURE_DIR/scripts/diff_results.py baseline.json optimized.json`.

## Experts to Scan (keywords)
- quantconnect performance
- lean backtest optimization
- python rollingwindow caching
- profiling qcalgorithm
- data consolidation throughput

## Risks & Mitigations
- Performance optimizations could change trading logic → mitigate with regression diff script and summary JSON comparisons.
- Instrumentation overhead may skew results → keep timers lightweight, disable in production mode, measure with/without instrumentation.
- Data cache misses could dominate runtime → verify local data availability before benchmarking and document warmup steps.

## Pipeline Integration Plan
- Add benchmark script to repo tooling and document invocation.
- Capture benchmark outputs in CI/manual checklists before merging performance changes.
- Evaluate adding nightly performance regression job once stable.

## Data & Migrations
- No schema or data migrations; ensure local Lean data cache warmed via baseline run.

## Observability, Rollout & Rollback Plan
- Observability: Stage timing logs aggregated via performance tracker; store metrics JSON per run.
- Rollout: Merge optimized code behind optional flag if necessary; default to enabled after validation.
- Rollback: Revert commits or disable optimization flag to restore baseline behavior.
