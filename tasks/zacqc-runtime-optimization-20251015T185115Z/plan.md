# Plan

## Task Overview
zac_qc combines the QuantConnect Lean-based `ZacReferenceAlgorithm` under `ZacQC/` with Python services that launch, monitor, and post-process trading runs. Recent executions show rising wall-clock times and per-tick latency, so we need a structured optimization roadmap that preserves deterministic fills and P&L. This plan focuses on benchmarking, profiling, hot-path refactoring, smarter data access, and infrastructure tuning across the algorithm, data managers, and orchestration layers. All outcomes must stay compatible with the Lean CLI workflow and existing deployment scripts while documenting guardrails for future tuning.

## Definition of Ready (DoR)
- Clarifications resolved: Target runtime SLO confirmed (≥50% end-to-end runtime reduction on current Lean build/hardware) and scope limited to Lean algorithm code under `ZacQC/`; ready to proceed.
- Test strategy agreed (matrix): Baseline Lean backtest (`lean backtest ZacQC --project ZacQC`), targeted `pytest` modules under `tests/`, and a perf harness capturing bars/sec, OnData latency, and warm-up duration.
- Rollout strategy (flag/canary/batch): Roll out via configuration toggles in `TradingParameters` and environment flags, validating on a staging Lean node before promoting to live/backtest servers.
- Data/backfill owner assigned (if applicable): Data ingestion and cache maintenance owned by DataManager maintainers; assign named stakeholder once confirmed.

## Clarification Questions
<!-- Ask before executing. Mark each as Critical or Nice-to-have. -->
_(none outstanding — previous questions resolved as of 2025-10-15)_

## Constraints & Requirements
- Performance: Achieve ≥50% end-to-end runtime reduction on the canonical backtest while keeping OnData end-to-end latency ≤50 ms p95.
- Security/Compliance: No new outbound network calls or data persistence outside approved directories; maintain reproducibility for audits.
- Compatibility: Preserve compatibility with QuantConnect Lean CLI (`lean.json`), Python 3.10 runtime, and existing configuration/parameter files.
- Delivery: Produce an executable optimization plan and baseline metrics by 2025-10-29 with iteration check-ins every two business days.
- Reliability/Availability: Guarantee trading outputs remain identical (orders, fills, P&L) versus the golden baseline; halt rollout on divergence.
- Observability: Emit structured performance logs (bars/sec, OnData timings, history duration) via Lean logging plus optional StatsD/CSV exports for comparisons.
- Cost: Stay within current single-node CPU/RAM budgets; escalate before provisioning additional hardware.

## Dependencies
- Internal: `ZacQC/core/*`, `ZacQC/data/*`, `ZacQC/trading/*`, `ZacQC/management/*`, `configs/TradingParameters`, `tests/`.
- External: QuantConnect Lean engine & CLI, Python scientific stack (`numpy`, `pandas`), profiling tools (`cProfile`, `line_profiler`), optional `numba`.

## Checklist of Subtasks
- Use `[ ]` now and flip items to `[x]` as you complete them during execution.
- [x] Capture baseline metrics (bars/sec, OnData latency, warm-up) for representative backtests and live-sim scenarios.
- [x] Instrument and profile hot paths (OnData, SymbolManager, DataManager, order managers) using cProfile/line-profiler and built-in Lean timings.
- [x] Optimize data access and state management (batch `History()`, rolling windows, caching strategy, allocation reuse).
- [x] Streamline algorithm logic (hoist invariants, trim logging, remove per-tick heavy operations) while validating correctness.
- [ ] Evaluate concurrency and orchestration options for backtest batches and job scheduling without overloading hardware.
- [x] Enhance observability and regression guardrails (perf dashboards, golden baseline storage, diff tooling).
- [ ] Document new workflows, toggles, and runbooks; prepare handoff and CI updates.

## Definition of Done (DoD)
- Functional: Golden backtest outputs (orders, fills, metrics) match the pre-optimization baseline across reference scenarios.
- Quality: `pytest` suite passes; Lean backtest completes within new runtime targets; OnData latency telemetry stays below agreed p95 budgets.
- UX/API: Configuration schemas (TradingParameters, server endpoints) remain backward compatible; performance toggles default to safe values.
- Docs: README and performance runbook updated with profiling steps, metrics collection, and toggle usage.
- Tests: Automated perf harness executed (`lean backtest`, targeted profiling scripts) with results stored and reviewed.

## Tests to Run
- `pytest -q tests`
- `lean backtest ZacQC --project ZacQC`
- `python tools/perf_harness.py --scenario reference --emit-metrics` (new harness introduced during execution)
- `python scripts/profile_ondata.py` (collect and review line-profiler output)

## Experts to Scan (keywords)
QuantConnect Lean profiling
Python OnData line profiler
Numba Lean compatibility

## Web Research Summary
- No external web research performed yet; relying on local expertise (`Experts/lean_python_perf.md`, `Experts/trading_perf.md`). After running searches, replace this note with bullets referencing files in `references/web/` (e.g., `references/web/<query-slug>--<timestamp>.md` → top findings and stack constraints).

## Risks & Mitigations
- Risk: Optimizations alter trading decisions through subtle state changes → Mitigation: Maintain golden baseline diffs and fail rollout on any divergence.
- Risk: Profiling overhead skews measurements or is impractical on live nodes → Mitigation: Use sampling profilers offline, isolate instrumentation behind flags, and replay logs where possible.
- Risk: Parallelism or caching introduces race conditions or stale data → Mitigation: Add unit/integration tests for symbol manager state, enforce thread/process-safe structures, roll out gradually.

## Pipeline Integration Plan
- Cross-cutting updates: Centralize performance instrumentation in `ZacQC/core/utils.py` and shared metrics helpers; standardize timing decorators.
- Interfaces/contracts: Ensure new configuration options default to current behavior; version parameter schema if additional fields are required.
- Tests: Add nightly perf regression job that runs the harness and compares metrics against stored baseline thresholds.
- CI/CD: Update automation to collect and archive perf metric artifacts; enforce linting on instrumentation paths.
- Config/migrations: Introduce optional flags (e.g., `enable_perf_opt`, `max_history_batch_size`) with documented defaults and rollback instructions.
- Documentation: Extend README, `docs/`, and runbooks with profiling workflow, new toggles, and regression procedures.

## Data & Migrations
- Schema changes: None anticipated; any cache/index adjustments must be idempotent and gated behind feature flags.
- Privacy: Ensure performance logs exclude PII and follow existing retention/rotation policies within `logs/`.

## Observability, Rollout & Rollback Plan
- Release strategy: Deploy behind `TradingParameters.enable_perf_opt` and staging feature flags; enable on staging, then pilot accounts, before full rollout.
- Metrics/SLOs: Track bars/sec, OnData latency p95/p99, warm-up duration, memory footprint, and history request timing; abort rollout if degradation exceeds 5%.
- Rollback path: Disable feature flags, revert to prior config/containers, and restore baseline cached artifacts; exposure window limited to the current trading session.

## Closed-Loop Execution Strategy
- Follow the Closed-Loop protocol with an expected three loops: baseline capture, hot-path optimization, and regression hardening.
- After each loop, collect Lean metrics (bars/sec, OnData latency distribution, warm-up duration) and diff against the golden baseline before advancing.
- Stop early if improvements fall below 5% or correctness drifts; otherwise proceed until the ≥50% runtime reduction goal is met.
