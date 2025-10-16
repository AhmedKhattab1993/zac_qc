# Plan

## Task Overview
Add deterministic Playwright end-to-end coverage to validate the Zac backtest control UI when historical data is missing versus already cached. The Flask server in `server/backtest_server.py` drives data checks, downloads, and Lean CLI execution; we must run the real Lean CLI while keeping workloads fast by constraining symbols/dates and reusing synthetic fixtures. Each scenario seeds a dedicated Lean data directory (empty vs populated) and exercises the UI through the browser to confirm status transitions, download behaviour, and Lean completion. Tests run headless against the local server on port 8080 and rely on a reduced parameters file so Lean backtests finish quickly with local data.

## Definition of Ready (DoR)
- Clarifications resolved: baseline config lives in `ZacQC/config/parameters.py`; `start_server.py` binds Flask on `http://localhost:8080`; `/api/backtest/status` and `/api/backtest/logs` expose the observability we can assert against; Lean CLI must execute (no stubbing) while using reduced parameters.
- Test strategy agreed (matrix): rely on Playwright UI specs plus direct API polling for verification; reuse existing pytest runner; capture traces only on failure to keep runs lean.
- Rollout strategy (flag/canary/batch): gate new specs behind a dedicated `@backtest-data` tag and hook them into the fast E2E job before expanding to full CI.
- Data/backfill owner assigned (if applicable): new fixtures created via `LeanDataStore` in test code; QA automation owns maintenance of the generated zip payloads.

## Clarification Questions
- [Critical] Is a Polygon API key (or deterministic offline dataset) available so downloads succeed when data is missing?
- [Nice] Should Playwright capture HTML reports or traces for every run, or only retain artifacts on failure to limit storage?

## Constraints & Requirements
- Performance: Keep each Playwright spec ≤ 90 s and total suite ≤ 3 min by constraining Lean workloads (single symbol, narrow date window) and optimising polling intervals.
- Security/Compliance: Never load real Polygon API keys or hit external services; redact any credentials from logs and artifacts.
- Compatibility: Target Python 3.11 runtime, Flask + threading server, Playwright for Python ≥ 1.48; ensure tests run on macOS (developer) and Ubuntu CI nodes.
- Delivery: Aim to land the test suite by 2025-10-20 so it can bake ahead of the next regression run.
- Reliability/Availability: Flakiness below 5%; ensure server cleanup between specs and deterministic log assertions.
- Observability: Collect Playwright trace/screenshot on failure and persist server stdout snippets under `$FEATURE_DIR/runs/`.
- Cost: Prefer local resources; if Polygon downloads are required, ensure usage stays within existing quotas and document credential handling.
- E2E Runtime Budgets: Total ≤ 3 min; per-spec ≤ 90 s; allow ≤ 3% flakiness before marking `BLOCKED`.

## Dependencies
- Internal: `server/backtest_server.py`, `server/data_download/data_store.py`, `frontend/index.html`, `ZacQC/config/parameters.py`, pytest configuration, prospective `tests/e2e` package.
- External: Playwright for Python tooling (browser binaries), Lean CLI binary (invoked during tests), Polygon calendar utilities (local only).

## User Stories
Duplicate the following story block for each user story in scope. Execute the closed loop per story; NEVER proceed to the next story unless the current story’s Acceptance Criteria (AC) are satisfied and evidenced. Do not advance based solely on partial work; the story must also meet its DoD.

### Story [S-1]: Surface Missing Data Path in UI
- Story ID: S-1 | Priority: P0 | Owner: Codex | Due: 2025-10-19
- User Story: As a release engineer, I want a Playwright spec that proves the UI highlights missing historical data, so we can catch regressions in the data-check/download flow before production.
- Dependencies: Flask backtest server (configurable data/config roots), Lean data store helpers | Non-goals: validating long-horizon performance metrics or Polygon rate limits.

#### Acceptance Criteria
- Given the server runs with an empty Lean data root and reduced parameters, when a user clicks “Start Backtest”, then the status card transitions to “Downloading Data” and exposes the configured symbol set.
- Given the same setup, when Playwright polls `/api/backtest/logs`, then at least one entry contains the missing-data warning (`missing data for` with the symbol) followed by a successful download completion log.
- Given the real Lean CLI execution, when the asynchronous run settles, then the status transitions to “Completed” and logs show the Lean process launch plus a zero exit code.

#### Story Definition of Ready (DoR)
- Clarifications: confirm availability of Polygon credentials or deterministic offline download fixtures so Lean can succeed.
- Test strategy: Playwright spec + direct API request assertions for log content.
- Data/backfill: rely on an empty temporary directory seeded via pytest fixture (no seconds data) alongside minimal parameters file (single symbol, tight date window).

#### Tasks Checklist
- [x] Add environment-driven configuration to point `BacktestManager` at test-specific data/config roots while preserving real Lean execution.
- [x] Create pytest/Playwright fixture to boot the server against an empty temporary data tree and reduced parameters file.
- [x] Implement Playwright scenario to start a backtest, wait for “Downloading Data”, and assert missing-data and download-complete log output.
- [x] Persist run artifacts (console log, Lean stdout excerpt, trace on failure) under `$FEATURE_DIR/runs/S-1/`.

#### Story Tests to Run
- Playwright: `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@missing-data" --project=chromium --workers=1 --retries=0 --timeout=90000`
- Supporting Python harness (if pytest wrapper): `pytest -q tests/e2e/support/test_backtest_harness.py::test_missing_data_download`

#### Story Definition of Done (DoD)
- AC met with evidence (status + log assertions captured).
- Lean CLI runs exactly once during the spec and exits successfully; evidence captured from logs/stdout.
- Playwright command above passes locally; artifacts stored in feature directory.
- Documentation updated to explain configuration overrides, credentials/fixtures, and runtime expectations.

#### Story Exit Checklist (AC Gate — do not proceed unless all checked)
- [x] All Acceptance Criteria satisfied for S-1 with captured screenshots/logs.
- [x] Evidence recorded in `$FEATURE_DIR/runs/S-1/<RUN_ID>/` (Playwright report, server + Lean log snippet).
- [x] Listed commands executed successfully with timestamps in decision log `[S-1]`.
- [x] Story DoD items verified (Lean run evidence, docs updated).
- [x] Tasks Checklist boxes updated to final state.
- [x] Decision Log includes final "Done" entry for `[S-1]`.
- [x] Referenced expertise documented; proposals filed if needed.
- [x] E2E run duration within budget and noted in decision log.

#### Story Implementation Plan
- Introduce configuration flags (env vars or CLI) in `start_server.py`/`backtest_server.py` to override data/config roots while retaining production behaviour.
- Implement helper utilities to seed empty vs populated Lean data directories and reduced parameters files (single symbol, narrow date range).
- Build pytest fixtures to spawn the Flask server in a subprocess with those overrides and to expose helper API clients to Playwright.
- Author Playwright steps and selectors (`data-testid` attributes if necessary) to drive Start Backtest, poll status/logs, and confirm Lean completion.
- Document setup in README/tests so future engineers can run the scenario locally with required credentials or fixture-generation steps.

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — boot server with empty data root, execute Playwright `@missing-data` spec, pipe output to `$FEATURE_DIR/runs/S-1/<RUN_ID>/stdout.log`, capture `/usr/bin/time -v` metrics and Lean stdout sample.
2) Diagnose — if assertions fail, inspect server logs (`api/backtest/logs`) and fixture config; adjust configuration or waits.
3) Plan — draft minimal code delta (env flag, fixture, selectors) referencing `[S-1/T-x]` tasks with rollback notes.
4) Change — implement/test changes incrementally, ensuring Lean process hook remains production-equivalent.
5) Re-Test & Compare — rerun Playwright spec; ensure Lean subprocess launches and completes successfully.
6) Decide — if AC + Exit Checklist satisfied, mark S-1 complete; else iterate or escalate.

#### Story Runbook & Logs
- Test matrix: Playwright `@missing-data`; optional pytest harness sanity.
- Logs: `$FEATURE_DIR/runs/S-1/<RUN_ID>/{stdout.log,stderr.log,server.log,lean.log}`.
- Decision log tag: `[S-1]` entries in `$FEATURE_DIR/decision-log.md`.
- Artifacts: `$FEATURE_DIR/artifacts/S-1/` for screenshots/traces.

#### Story Progress & Hygiene (per loop)
- [ ] Update S-1 Tasks Checklist statuses truthfully.
- [ ] Append Decision Log entry `[S-1]` with attempt/result/evidence/next step and runtime metrics.
- [ ] Update `$FEATURE_DIR/referenced-expertise.md` with consulted docs (e.g., Playwright guide, Lean data store).
- [ ] File proposals under `$FEATURE_DIR/proposals/expert-additions.md` if new guidance is warranted.
- [ ] Record E2E runtime vs budget alongside monitoring notes.

#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: zip-fixture generation for Lean seconds data; selectors audit in `frontend/index.html`.
- Inputs: target symbol list, date range, expected log messages.
- Acceptance: deliver zipped fixture paths, confirmed selectors, and passing local dry-run.

#### Links/Artifacts
- Ticket: TBD-backtest-data-e2e
- PR: (to be created)

### Story [S-2]: Confirm Cached Data Path in UI
- Story ID: S-2 | Priority: P1 | Owner: Codex | Due: 2025-10-20
- User Story: As a QA engineer, I want a Playwright spec proving the UI skips download work when seconds data already exists, so cached environments remain fast and predictable.
- Dependencies: Configuration overrides and fixtures from S-1, Lean data helpers | Non-goals: validating actual equity curve rendering or long-running Lean analytics.

#### Acceptance Criteria
- Given seeded seconds data for the configured symbol(s) and reduced parameters, when the user starts a backtest, then the status card reaches “Completed” with at most one “Downloading Data” poll cycle.
- Given the same setup, when Playwright polls `/api/backtest/logs`, then it finds the success message `All required Seconds data is available`.
- Given cached data, when the run finishes, then server logs show the Lean process launch and successful completion (exit code 0) with runtime shorter than the missing-data scenario.

#### Story Definition of Ready (DoR)
- Clarifications: confirm acceptable minimal dataset (one day for one symbol) and location for fixture storage.
- Test strategy: Playwright spec with assertions on status timing and logs, reusing server harness/fixtures.
- Data/backfill: generate zipped seconds data via `LeanDataStore.write_intraday_day` into temp directory before server launch.

#### Tasks Checklist
- [x] Extend fixture builder to populate seconds zip(s) for target symbol/date in the temporary data root.
- [x] Write Playwright scenario tagged `@cached-data` that launches the server with populated data, runs Start Backtest, and asserts status/log expectations.
- [x] Refine selectors or API polling utilities to measure download duration (≤ one interval).
- [x] Store artifacts under `$FEATURE_DIR/runs/S-2/` (including Lean stdout sample) and update decision log with runtime/completion evidence.

#### Story Tests to Run
- Playwright: `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@cached-data" --project=chromium --workers=1 --retries=0 --timeout=90000`
- Fixture smoke (optional): `pytest -q tests/e2e/support/test_backtest_harness.py::test_cached_data_fixture`

#### Story Definition of Done (DoD)
- AC satisfied with logs/screenshots preserved.
- Cached-data spec stable across three consecutive local runs without flake.
- Lean CLI run completes successfully and logs captured; runtime noted for comparison to missing-data case.
- Documentation updated with instructions to seed fixtures and interpret logs.
- Both Playwright tags (`@missing-data`, `@cached-data`) can run sequentially within 3 min.

#### Story Exit Checklist (AC Gate — do not proceed unless all checked)
- [x] All Acceptance Criteria satisfied for S-2 with explicit evidence.
- [x] Artifacts stored in `$FEATURE_DIR/runs/S-2/<RUN_ID>/` (Playwright report, server + Lean log snippet) and linked from decision log `[S-2]`.
- [x] Listed commands executed successfully; timings captured.
- [x] DoD items verified (docs, stability evidence, runtime budget).
- [x] Tasks Checklist reflects completion state.
- [x] Decision Log updated with final “Done” entry for `[S-2]`.
- [x] Expertise updates and proposals logged if new learnings emerged.
- [x] E2E runtime within budget and recorded.

#### Story Implementation Plan
- Reuse configuration overrides from S-1 and extend fixture utility to write valid Lean seconds zip for a chosen trading day (e.g., 2025-10-08) and symbol.
- Parameterize server launch fixture to accept `data_root`/`config_path` overrides so the same Playwright spec can target empty vs populated roots.
- Implement Playwright assertions for quick transition (track timestamps before/after polling) and log content verifying the cached path.
- Update shared documentation/readme for running both tags and interpreting results.
- Add CI hook or instructions ensuring new tags are included in smoke suite.

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — seed fixtures, launch server, execute `@cached-data` spec with `/usr/bin/time -v`, capture console output and Lean stdout sample.
2) Diagnose — inspect server logs if status lingers in download; verify fixture path correctness.
3) Plan — outline minimal code/config tweaks needed (fixture builder, selectors) with rollback strategy.
4) Change — apply updates, ensuring configuration overrides remain production-safe.
5) Re-Test & Compare — rerun Playwright spec, confirm logs show cached-data message and Lean completion.
6) Decide — once AC + Exit Checklist achieved, mark S-2 complete; otherwise iterate or escalate.

#### Story Runbook & Logs
- Test matrix: Playwright `@cached-data`; optional pytest harness validation.
- Logs: `$FEATURE_DIR/runs/S-2/<RUN_ID>/{stdout.log,stderr.log,server.log,lean.log}`.
- Decision log tag: `[S-2]` in `$FEATURE_DIR/decision-log.md`.
- Artifacts: `$FEATURE_DIR/artifacts/S-2/` (screenshots/traces on failure).

#### Story Progress & Hygiene (per loop)
- [ ] Update S-2 Tasks Checklist each loop.
- [ ] Append Decision Log entries `[S-2]` with attempt/result/evidence/next steps.
- [ ] Maintain referenced expertise index and proposals as in S-1.
- [ ] Track runtime budget adherence and monitoring notes per run.

#### Sub-Agent Delegation (Codex CLI)
- Tasks to delegate: script Lean seconds zip generation; gather selectors for status card/time measurements.
- Inputs: symbol/date, expected success log strings.
- Acceptance: validated fixture writer and selector map with documented usage.

#### Links/Artifacts
- Ticket: TBD-backtest-data-e2e
- PR: (to be created)

## Checklist of Subtasks
- [ ] Gate: confirm current story’s Exit Checklist complete before starting the next story.
- [ ] Never-Stop: kick off the next story immediately unless blocked.
- [ ] All User Stories completed with Exit Checklists satisfied.
- [ ] Per-loop hygiene enforced (tasks checklist, decision log, expertise, proposals).
- [ ] Plan & Setup (tooling/env ready; Lean runtime validated with reduced parameters).
- [ ] Design Solution (harness architecture, selectors, fixture strategy).
- [ ] Implement Core Functionality (test harness + specs).
- [ ] Integrate Components (server flags, Playwright fixtures, docs).
- [ ] Testing (run Playwright tags + supporting pytest checks).
- [ ] Optimization (address flakiness/perf, refactor helpers).
- [ ] Documentation & Final Review (README/test docs updated).

## Definition of Done (DoD)
- Functional: Playwright specs detect both missing-data and cached-data paths via UI + API assertions while executing the real Lean CLI end-to-end.
- Quality: Lint/type (ruff/mypy if applicable) pass; Playwright + pytest suites green; flake rate < 5%.
- UX/API: No changes to production endpoints; configuration overrides default off for normal usage.
- Docs: Test runbook and environment variables documented in repo docs/tests README.
- Tests: `pytest -q` (focused harness tests) and targeted Playwright commands executed with recorded evidence, including Lean runtime proof.

## Tests to Run
- `pytest -q tests/e2e/support`
- `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@missing-data"`
- `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@cached-data"`
- Optional CI smoke: `/usr/bin/time -v npx playwright test tests/e2e/backtest-data-availability.spec.ts --project=chromium -g "@backtest-data" --workers=1 --retries=0`

## Experts to Scan (keywords)
playwright python
lean data store
flask subprocess testing
quantconnect polygon downloader
deterministic e2e fixtures

## Risks & Mitigations
- Risk: Lean CLI exceeds runtime budget or fails due to missing data/API credentials. → Mitigation: constrain parameters to single symbol/date, provide deterministic fixtures or documented credentials, and track runtime in decision logs.
- Risk: Playwright polling misses transient “Downloading Data” state due to rapid transitions. → Mitigation: rely on `/api/backtest/logs` assertions and add deterministic waits tied to log entries rather than UI-only checks.
- Risk: Fixture zip format drifts from Lean expectations causing false negatives. → Mitigation: reuse `LeanDataStore.write_intraday_day` helper and cover with pytest harness tests.

## Pipeline Integration Plan
- Cross-cutting updates: add configurable data/config root overrides in server startup and shared fixtures; centralize Playwright helpers in `tests/e2e`.
- Interfaces/contracts: ensure new environment variables (e.g., `BACKTEST_DATA_ROOT`, `BACKTEST_CONFIG_PATH`, `BACKTEST_SYMBOLS`) default off and are documented.
- Tests: register new Playwright tags in CI configuration so smoke job can include/exclude them explicitly.
- CI/CD: update Playwright job script to install browsers once and run `@backtest-data` tag; ensure artifacts archived on failure.
- Config/migrations: no DB/schema changes; add sample `.env.test` entries for new flags and credential placeholders.
- Documentation: extend tests README with server start instructions, env vars, and commands listed under “Tests to Run”.

## Data & Migrations
- Schema changes: none; manipulate only temporary Lean data directories created per test run.
- Privacy: generated fixtures contain synthetic data only; ensure cleanup of temp dirs after tests.

## Observability, Rollout & Rollback Plan
- Release strategy: merge behind default-off env flags; enable tests gradually in CI via targeted tag.
- Metrics/SLOs: monitor Playwright runtime (<3 min) and failure counts; abort enabling in full CI if failure rate >5%.
- Rollback path: revert test harness commits or disable `@backtest-data` tag in CI; remove env variables if causing issues.
 
## Implementation Plan (optional, cross-cutting)
- Steps: (1) Add env-configurable data/config overrides to `backtest_server.py`/`start_server.py`; (2) Build reusable pytest fixtures for Lean data seeding and server lifecycle; (3) Author unified Playwright spec file with tagged tests for missing vs cached data; (4) Update docs/CI scripts to run new tags and describe env vars/credentials; (5) Record decision logs, artifacts, and expertise per story loop.
- Rollback: disable env flags and Playwright tags, delete test harness code, restore server defaults.
- Risks/Impact: new override paths must not alter production runs; guard with explicit env checks and automated tests.
