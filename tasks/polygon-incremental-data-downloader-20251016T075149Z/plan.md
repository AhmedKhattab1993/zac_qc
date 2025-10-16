# Plan

## Task Overview
Replacing the current `lean data download` shell-outs with a native Polygon REST downloader so backtest jobs fetch only the deltas they need. The solution must honor Lean's on-disk equity data layout (`data/equity/usa/<resolution>/<symbol>/<YYYYMMDD>_trade.zip`). Scope is Python services under `server/` that orchestrate data preparation before Lean backtests run. We will design an incremental fetcher that reads the Polygon key from `lean.json`, infers gaps per trading day, and persists files in identical format with improved throughput.

## Definition of Ready (DoR)
- Clarifications resolved: Lean equity data format verified via existing `data/equity/usa/minute/<symbol>/<date>_trade.zip` samples; Polygon API key located at `lean.json['polygon-api-key']`; trading calendar utility already available via `server/trading_calendar.py`; scope confirmed to US equity Trade data at Daily/Minute/Second resolutions using Polygon aggregate bars.
- Test strategy agreed (matrix)
- Rollout strategy (flag/canary/batch)
- Data/backfill owner assigned (if applicable)

## Clarification Questions
<!-- Ask before executing. Mark each as Critical or Nice-to-have. One per bullet. -->
- [Critical] Data scope: **Resolved (Option A)** — focus on US equity Trade data at Daily/Minute/Second resolutions matching the current server implementation.
- [Critical] Polygon endpoint contract: **Resolved (Option B)** — use Polygon aggregate bar endpoints (e.g., `/v2/aggs`) rather than raw trades or quotes.
- [Nice] Performance baseline: **Resolved (Option A)** — demonstrate the new flow is faster than the CLI without committing to a fixed percentage target; still capture before/after timings for transparency.

## Constraints & Requirements
- Performance: Demonstrate measurably faster end-to-end download time than the current Lean CLI flow for comparable workloads; capture before/after timings but no fixed percentage target.
- Security/Compliance: Never log the Polygon API key; load it from `lean.json` or env overrides; respect Polygon rate limits and exponential backoff on HTTP 429/5xx.
- Compatibility: Output must match QuantConnect Lean data format (zip-compressed trade CSV) and remain compatible with Python 3.11 runtime used in `server/` services; preserve lowercase symbol folders and `_trade.zip` naming.
- Delivery: Target code-complete by 2025-10-23 to align with current sprint cutoff.
- Reliability/Availability: Downloader must detect partial files, support resumable retries, and fall back (or fail fast with actionable log) if Polygon is unreachable.
- Observability: Emit structured log entries under `backtest_logger` (phase `data_download`) plus timing metrics (start/end, bytes fetched, cache hits) for Grafana ingestion.
- Cost: Minimize duplicate Polygon calls by caching request windows and batching within documented rate limits (max 5 concurrent requests, reuse aggregated responses when possible).

## Dependencies
- Internal: `server/backtest_server.BacktestManager`, `_check_data_availability`, `server/trading_calendar.USEquityTradingCalendar`, `ZacQC/config/parameters.py` (for symbol/date inputs), local `data/` directory structure.
- External: Polygon REST API (historical trades/aggregates endpoints), `requests`/`httpx` library, compression utilities (`zipfile`, `gzip`), pandas for data shaping if needed.

## User Stories
Duplicate the following story block for each user story in scope. Execute the closed loop per story; move to the next only after the current story meets its DoD.

### Story [S-1]: Build incremental Polygon downloader core
- Story ID: S-1 | Priority: P0 | Owner: Codex | Due: 2025-10-21
- User Story: As a backtest platform engineer, I want a native Polygon downloader that only fetches missing Lean-formatted data, so backtests can start sooner without redundant network calls.
- Dependencies: server/trading_calendar, lean.json | Non-goals: Supporting non-equity asset classes in this iteration

#### Acceptance Criteria
- Given a date range where some trading-day files are absent locally, When the downloader runs, Then it fetches only the missing days from Polygon and writes `_trade.zip` files identical in schema to Lean’s output for Daily, Minute, and Second resolutions.
- Given a date range where all required files already exist, When the downloader runs, Then no external HTTP requests are issued and the module reports cache hits in logs.

#### Story Definition of Ready (DoR)
- Clarifications: Data scope, aggregate bar usage, and performance baseline expectations confirmed
- Test strategy: Unit tests to validate file naming and gap detection; integration test hitting Polygon sandbox/mock to verify zip payloads over short date windows to keep runtime low
- Credentials: Valid Polygon API key available in test/staging environments for live integration runs
- Data/backfill: Not applicable (no historical migration needed)

#### Tasks Checklist
- [ ] Document Lean trade zip schema by inspecting current samples and capture in module docs/tests.
- [ ] Implement Polygon REST client with rate limiting, retries, and chunked requests per symbol/resolution.
- [ ] Build incremental storage pipeline that lowercases symbols, writes temp files, and atomically swaps to final `_trade.zip` outputs.
- [ ] Add unit and integration tests covering gap detection, skip-on-cache, and successful download paths, using short date ranges to keep runtime low.
- [ ] Add a mandatory live integration test harness that calls Polygon with a one-day window; fail loudly if a Polygon key is absent in environments where tests run.

#### Story Tests to Run
- Unit/Integration: `pytest -q tests/unit/test_polygon_downloader.py` and `pytest -q tests/integration/test_polygon_downloader_incremental.py`
- Live integration: `pytest -q tests/integration/test_polygon_downloader_live.py` — hits Polygon’s real API over a one-day window; requires valid key.
- E2E (Playwright, if applicable): `npx playwright test tests/e2e/polygon-downloader.spec.ts`

#### Story Definition of Done (DoD)
- AC satisfied; unit/integration tests pass locally; generated zip files validated against baseline fixture hashes; inline module docs updated.

#### Story Implementation Plan
- Inspect existing Lean `_trade.zip` archives to reverse-engineer CSV headers, timezone handling, and compression settings.
- Create a Polygon API client helper wrapping authentication, pagination, rate limiting, and retries with jitter.
- Implement per-resolution fetchers that call Polygon aggregate bar endpoints and transform responses into Lean CSV rows (including trade timestamps) before writing temp files.
- Build gap detection that leverages `USEquityTradingCalendar` to list missing trading days and orchestrates fetch/write per symbol.
- Add checksum/size validation and atomic rename to prevent leaving corrupt partial files on interruption.
- Cover logic with unit tests (gap detection, naming) and integration tests using mocked Polygon responses sized to short date windows.

#### Story Execution Protocol (Closed Loop)
Note: Applies to both bug fixes and new features.
Optional pre-steps:
- Feature — 0) Capture baseline Lean CLI output for one symbol/day set for later comparison
1) Run & Capture — execute tests/commands for S‑1; save logs & metrics; update Decision Log.
2) Diagnose — one-line failure summary; smallest viable fix; re-scan `experts/` and internal docs if needed.
3) Plan — 3–5 step micro-plan; files/functions; rollback note; update risk/impact.
4) Change — implement minimal delta; commits small; reference `[S‑1/T‑x]`.
5) Re-Test & Compare — re-run failing tests; compare metrics; paste deltas.
6) Decide — if DoD met → mark S-1 done; else loop/refine/escalate.

Stop conditions: 3 loops without measurable progress, or time-box exceeded → summarize blockers for S-1 and ask questions (`BLOCKED`).

#### Story Runbook & Logs
- Test matrix: `pytest -q tests/unit/test_polygon_downloader.py`, `pytest -q tests/integration/test_polygon_downloader_incremental.py`, `pytest -q tests/integration/test_polygon_downloader_live.py`
- Logs: `$FEATURE_DIR/runs/S-1/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-1/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-1]`
- Artifacts: `$FEATURE_DIR/artifacts/` (screenshots under `artifacts/screenshots/`)
 
#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: Generate Polygon response fixtures; scaffold pytest parametrized cases; synthesize docstrings from sample zip metadata
- Inputs: Existing sample zip files, Polygon API schema, AC details
- Acceptance: Fixtures stored under `tests/fixtures/polygon/`; tests passing on `pytest -q`

#### Links/Artifacts
- Backlog ticket: TBD

### Story [S-2]: Integrate downloader into backtest pipeline
- Story ID: S-2 | Priority: P0 | Owner: Codex | Due: 2025-10-23
- User Story: As a quant running backtests, I want the server to use the faster incremental downloader automatically, so runs spend less time waiting on data prep.
- Dependencies: S-1 completion, server/backtest_server.BacktestManager | Non-goals: Changing Lean backtest invocation logic

#### Acceptance Criteria
- Given a backtest trigger with missing data, When `BacktestManager` enters the download phase, Then it uses the new Polygon downloader instead of spawning `lean data download`, and logs show per-resolution timings without spawning external Lean CLI processes.
- Given Polygon outages or request failures, When the downloader exhausts retries, Then the system surfaces a clear error to the UI/logs and optionally falls back to the existing CLI path if a feature flag enables it.
- Given all data already present, When a backtest starts, Then the download phase completes in under 5 seconds and issues no external commands.

#### Story Definition of Ready (DoR)
- Clarifications: Need decision on fallback-to-CLI flag behavior and backlog owner for toggling
- Test strategy: Integration test invoking backtest endpoint with mocked Polygon responses; regression test ensuring no CLI subprocess is spawned; live backtest smoke test hitting Polygon over a one-day window
- Credentials: Valid Polygon API key available for live backtest smoke test environments
- Data/backfill: N/A (relies on existing files)

#### Tasks Checklist
- [ ] Add configuration/feature flag (env or config) to toggle between CLI and native downloader during rollout.
- [ ] Refactor `BacktestManager` download path to call the new module, passing symbols/resolutions and capturing progress updates while defaulting tests to short date windows.
- [ ] Update logging/metrics to include downloader stats (cache hits, API call counts, duration) and remove CLI-specific messaging.
- [ ] Write integration tests for `BacktestManager` to validate success, cache-only, and retry/failure flows using mocks over short sample periods to keep runtime low.
- [ ] Add a live end-to-end backtest test that exercises the new downloader against Polygon over a one-day window and ensures logs capture real download timings.

#### Story Tests to Run
- Unit/Integration: `pytest -q tests/integration/test_backtest_manager_downloader.py`
- Live backtest smoke: `pytest -q tests/integration/test_backtest_manager_downloader_live.py`
- E2E (Playwright, if applicable): `npx playwright test tests/e2e/backtest-download-flow.spec.ts`

#### Story Definition of Done (DoD)
- AC met; integration tests pass; no `lean data download` subprocess appears in logs; feature flag default documented; telemetry dashboards updated with new metrics.

#### Story Implementation Plan
- Introduce a downloader interface/adapter so `BacktestManager` can swap between CLI and Polygon implementations.
- Wire `BacktestManager` to compute missing days via existing `_check_data_availability` and delegate fetches per resolution to the new downloader.
- Implement structured logging (JSON-ready) for each phase plus progress updates derived from downloader callbacks.
- Add optional fallback to old CLI flow guarded by config/env flag, defaulting to the new downloader once validated.
- Extend integration tests to cover success, cache-only, and forced failure fallback scenarios.

#### Story Execution Protocol (Closed Loop)
Note: Applies to both bug fixes and new features.
Optional pre-steps:
- Feature — 0) Measure current CLI-based download duration for comparison and capture logs for regression
1) Run & Capture — execute tests/commands for S‑2; save logs & metrics; update Decision Log.
2) Diagnose — one-line failure summary; smallest viable fix; re-scan `experts/` and internal docs if needed.
3) Plan — 3–5 step micro-plan; files/functions; rollback note; update risk/impact.
4) Change — implement minimal delta; commits small; reference `[S‑2/T‑x]`.
5) Re-Test & Compare — re-run failing tests; compare metrics; paste deltas.
6) Decide — if DoD met → mark S-2 done; else loop/refine/escalate.

Stop conditions: 3 loops without measurable progress, or time-box exceeded → summarize blockers for S-2 and ask questions (`BLOCKED`).

#### Story Runbook & Logs
- Test matrix: `pytest -q tests/integration/test_backtest_manager_downloader.py`, `pytest -q tests/integration/test_backtest_manager_downloader_live.py`
- Logs: `$FEATURE_DIR/runs/S-2/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-2/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-2]`
- Artifacts: `$FEATURE_DIR/artifacts/`
 
#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: Update frontend/backoffice messaging to reflect faster downloads; capture CLI baseline metrics; prepare feature flag documentation
- Inputs: Story AC, log schema, performance targets
- Acceptance: Metrics notebook saved under `$FEATURE_DIR/artifacts/benchmarks/`; documentation snippet ready for README/CHANGELOG update

#### Links/Artifacts
- Release note stub: TBD

### Story [S-3]: Benchmark and document performance gains
- Story ID: S-3 | Priority: P1 | Owner: Codex | Due: 2025-10-24
- User Story: As product stakeholders, we need quantified evidence and documentation of the new downloader’s speedup so we can communicate value and monitor regressions.
- Dependencies: Completion of S-1 and S-2 | Non-goals: Automating long-term trend monitoring

#### Acceptance Criteria
- Given defined benchmark scenarios (symbols/date ranges), When tests run before and after the change against the live Polygon API, Then the report shows the native downloader outperforming the CLI baseline (new duration < old duration) with raw timings, request counts, and cache hit ratios archived in `$FEATURE_DIR/benchmarks/`; default scenarios should use short date windows to keep runs quick, with optional extended runs documented.
- Given the new downloader is live, When developers consult the docs, Then they find updated guidance in `Experts/` or README describing configuration, usage, and troubleshooting.

#### Story Definition of Ready (DoR)
- Clarifications: Need sign-off on benchmark scenarios and Polygon rate-limit budgets
- Test strategy: Benchmark harness script plus regression assertion comparing baseline vs new metrics; doc build/lint checks if applicable; live benchmark execution path defined
- Credentials: Valid Polygon API key and rate-limit budget confirmed for benchmark environments
- Data/backfill: N/A

#### Tasks Checklist
- [ ] Implement a reproducible benchmark script comparing CLI vs native downloader across representative workloads against the live Polygon API, defaulting to short date windows with an option to scale up for deeper analysis.
- [ ] Capture and store results (timings, API counts) under `$FEATURE_DIR/benchmarks/` and update Decision Log with summary.
- [ ] Update documentation (`Experts/` or README) to describe new downloader usage, configuration flags, and fallback.

#### Story Tests to Run
- Unit/Integration: `pytest -q tests/benchmarks/test_downloader_benchmarks.py`
- Live benchmark run: `pytest -q tests/benchmarks/test_downloader_benchmarks_live.py`
- E2E (Playwright, if applicable): `npx playwright test tests/e2e/perf-dashboard.spec.ts`

#### Story Definition of Done (DoD)
- Benchmarks executed and archived; documentation PR merged; performance delta communicated to stakeholders; automated check (if any) verifies the new downloader remains faster than the CLI baseline for the defined short-window scenarios.

#### Story Implementation Plan
- Design benchmark scenarios (symbol sets, short date windows by default) and script both CLI and native downloader runs with consistent environment setup against live Polygon endpoints.
- Automate metrics collection (duration, bytes, HTTP calls) and export to JSON/CSV under `$FEATURE_DIR/benchmarks/`, flagging how to run extended intervals if desired.
- Add regression assertion logic comparing new downloader vs baseline and flagging if improvement threshold missed.
- Update relevant docs (`Experts/lean_unix_run.md` or new doc) with configuration steps, troubleshooting, and benchmark highlights.
- Share findings via Decision Log and prepare summary for release notes/ChangeLog.

#### Story Execution Protocol (Closed Loop)
Note: Applies to both bug fixes and new features.
Optional pre-steps:
- Feature — 0) Align stakeholders on benchmark scenarios and success criteria before coding
1) Run & Capture — execute tests/commands for S‑3; save logs & metrics; update Decision Log.
2) Diagnose — one-line failure summary; smallest viable fix; re-scan `experts/` and internal docs if needed.
3) Plan — 3–5 step micro-plan; files/functions; rollback note; update risk/impact.
4) Change — implement minimal delta; commits small; reference `[S‑3/T‑x]`.
5) Re-Test & Compare — re-run failing tests; compare metrics; paste deltas.
6) Decide — if DoD met → mark S-3 done; else loop/refine/escalate.

Stop conditions: 3 loops without measurable progress, or time-box exceeded → summarize blockers for S-3 and ask questions (`BLOCKED`).

#### Story Runbook & Logs
- Test matrix: `pytest -q tests/benchmarks/test_downloader_benchmarks.py`, `pytest -q tests/benchmarks/test_downloader_benchmarks_live.py`
- Logs: `$FEATURE_DIR/runs/S-3/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-3/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-3]`
- Artifacts: `$FEATURE_DIR/artifacts/`
 
#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: Automate benchmark plotting; lint updated docs; prepare CHANGELOG entry draft
- Inputs: Benchmark script outputs, documentation pages, AC
- Acceptance: Plots stored under `$FEATURE_DIR/artifacts/benchmarks/`; docs lint passes; CHANGELOG snippet reviewed

#### Links/Artifacts
- Benchmark report: TBD

## Checklist of Subtasks
- [ ] Plan & Setup (repo/env ready, confirm requirements)
- [ ] Design Solution (modules, data flow, interfaces)
- [ ] Implement Core Functionality (primary logic, edge cases)
- [ ] Integrate Components (wire modules, data contracts)
- [ ] Testing (unit/integration/e2e as applicable)
- [ ] Optimization (refactor/perf/quality passes)
- [ ] Documentation & Final Review (README, examples)

## Definition of Done (DoD)
- Functional: Downloader covers Daily/Minute/Second equity trade data with gap-aware fetch and Lean-compatible output.
- Quality: `pytest -q` suite passes; mypy/ruff (if configured) show no new violations; performance guard ensures the native downloader remains faster than the CLI baseline on agreed short-window scenarios.
- UX/API: Backtest logs surface clear progress/errors; feature flag documented; CLI removal is transparent to end users.
- Docs: Updated runbook plus `Experts/` guidance on configuring Polygon downloader and benchmarking steps.
- Tests: `pytest -q` (unit/integration/live/benchmarks) and targeted Playwright specs executed successfully; live suites must run with real Polygon access in designated environments.

## Tests to Run
- Unit: `pytest -q tests/unit/test_polygon_downloader.py`
- Integration: `pytest -q tests/integration/test_backtest_manager_downloader.py`
- Live integration: `pytest -q tests/integration/test_polygon_downloader_live.py`
- Live backtest smoke: `pytest -q tests/integration/test_backtest_manager_downloader_live.py`
- Live benchmark: `pytest -q tests/benchmarks/test_downloader_benchmarks_live.py`
- Runtime guard: default fixtures should cover short date windows to keep test cycles fast; document any extended-range benchmark separately.
- E2E (Playwright, if web UI):
  - Setup: `npx playwright install --with-deps`
  - Run: `npx playwright test --project=chromium --reporter=junit`
  - Practices: add `data-testid` selectors; stub network where appropriate; use fixtures for auth/data; keep tests idempotent and parallel-safe.

## Experts to Scan (keywords)
polygon trade data format
quantconnect lean data structure
python zip incremental download

## Risks & Mitigations
- Risk: Polygon rate limits or outages could stall downloads → Mitigation: Implement exponential backoff with jitter and configurable retry budgets plus optional fallback to CLI path.
- Risk: Misaligned data schema leading to Lean parse errors → Mitigation: Build schema validation against known-good fixtures and run Lean smoke backtests on downloaded data before rollout.
- Risk: Increased API spend due to redundant fetches → Mitigation: Cache trading-day completeness metadata and log request counts for monitoring.

## Pipeline Integration Plan
- Cross-cutting updates: Introduce downloader abstraction module shared between backtest server and any future services; ensure imports centralized under `server/data_download/`.
- Interfaces/contracts: Maintain existing BacktestManager API; add internal interface for downloader with clear contract; version via feature flag for rollback.
- Tests: Add integration tests to CI to verify downloader gap detection; wire benchmarks to optional nightly job for regression detection.
- CI/CD: Ensure new pytest suites are added to pipeline configuration; monitor coverage reports for new modules.
- Config/migrations: Add config flag defaults (e.g., `use_polygon_native_downloader`) and document env variable overrides; provide rollback instructions in README.
- Documentation: Update `Experts/lean_unix_run.md` and possibly `docs/data-download.md` with new flow diagrams and troubleshooting.

## Data & Migrations
- Schema changes: None (reuse existing Lean on-disk layout); add automated script to validate zip contents during CI.
- Privacy: No PII involved; ensure logs redact API keys; respect data retention policies for cached benchmark outputs.

## Observability, Rollout & Rollback Plan
- Release strategy: Ship behind config flag defaulting to new downloader in staging, then enable in production environments after benchmark validation.
- Metrics/SLOs: Track downloader duration, cache hit ratio, HTTP error rate; abort rollout if error rate >5% or average duration regresses by >10% vs baseline.
- Rollback path: Toggle feature flag back to CLI downloader; retain CLI code path for one release cycle; keep documentation for manual fallback commands.
 
## Implementation Plan (optional, cross-cutting)
- Steps: (1) Finish clarifications and finalize downloader contract; (2) Implement core downloader module with tests (S-1); (3) Integrate into BacktestManager with feature flag and logging (S-2); (4) Run end-to-end benchmarks and documentation updates (S-3); (5) Prep rollout checklist and CI additions.
- Rollback: Feature flag toggle to revert to Lean CLI; remove downloader package if critical issues arise.
- Risks/Impact: High impact on backtest latency; ensure staged rollout to mitigate potential data corruption or API outages.
