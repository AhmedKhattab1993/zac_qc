
---
codex_mode: PLAN_ONLY   # PLAN_ONLY | EXECUTE
human_approval_required: true
stop_after: READY_FOR_APPROVAL
mode_detection_rules:
  default: PLAN_ONLY
  plan_only_triggers: ["plan only", "planning", "proposal", "scope", "design", "do not run", "no execution", "dry run"]
  execute_triggers: ["implement", "execute", "run tests", "fix", "integrate", "apply", "PR", "open PR", "merge", "build", "test", "deploy", "release", "ship", "migrate", "backfill", "hotfix", "rollback"]
output_contract:
  allowed_sections:
    - Task Overview
    - Definition of Ready (DoR)
    - Clarification Questions
    - Constraints & Requirements
    - Dependencies
    - Checklist of Subtasks
    - Definition of Done (DoD)
    - Tests to Run
    - Experts to Scan (keywords)
    - Web Research Summary
    - Risks & Mitigations
    - Pipeline Integration Plan
    - Data & Migrations
    - Observability, Rollout & Rollback Plan
    - Referenced Expertise
    - Expert Augmentation Report (draft)
    - Decision Log (if EXECUTE)
  # v2: PLAN_ONLY may write files and do research. The only restriction is not running tests.
  forbidden_actions:
    - run tests (PLAN_ONLY)
stop_tokens:
  needs_clarification: NEEDS_CLARIFICATION
  ready_for_approval: READY_FOR_APPROVAL
  blocked: BLOCKED
---

# Ultimate Codex CLI Task Planning Template — **v2** (Built‑in Web Search)

> **What changed vs v2 (DDG):**
> - Uses **Codex CLI's built‑in web search tool (MCP)** directly. No custom Python or external scripts.
> - **PLAN_ONLY may write** scaffolding, plans, and research notes.
> - No additional security/env gating; the agent can do what it needs within the chosen mode.

> **Agent contract (read first):**
> - Determine **mode** from user intent (see detection rules above). If ambiguous, use **PLAN_ONLY**.
> - Ask **Clarification Questions** and stop with `NEEDS_CLARIFICATION` if any critical item is unresolved.
> - Always scan local `experts/` for guidance. If results are thin or stale, **use the built‑in web search tool** and save findings.
> - Produce a structured **Plan** (Markdown) with **Checklist** and **DoD**.
> - Ensure fixes/changes are **generalized into the project pipeline** (no ad‑hoc per‑run hacks).
> - **EXECUTE only**: follow the **Closed Loop** and log everything under `tasks/`.
> - Emit an **Expert Augmentation Report** proposing additions/updates to `experts/` from lessons learned.

---

## 0) Mode & Approval Gate
**Mode resolution:**
- If the request includes any *execute triggers* → set `codex_mode: EXECUTE` (unless explicitly forbidden).
- If unclear → keep `codex_mode: PLAN_ONLY`.

**PLAN_ONLY behavior (v2):**
- Must run the **Bootstrap** step below and create the feature scaffold (directories + blank docs) before drafting the plan.
- May create directories/files and perform **research** (including built‑in web search).
- Does **not** run tests or code. End with `READY_FOR_APPROVAL` (or `NEEDS_CLARIFICATION` if questions remain).

**EXECUTE behavior:**
- If any **critical** clarification unanswered → stop before running and emit `NEEDS_CLARIFICATION`.
- Otherwise run **Bootstrap**, optional **Research**, then **Closed Loop**.

---

## 1) Workspace & Logging Layout (per feature)
Create a dedicated **feature pack** and write all plans, logs, and artifacts there.

Run the bootstrap shell snippet **immediately after** clarifications/mode resolution, regardless of `codex_mode`.

**Naming**
- **Feature title:** short human title (e.g., `Auth refresh token`)
- **Feature slug:** kebab‑case (e.g., `auth-refresh-token`)
- **Feature dir:** `tasks/<FEATURE_SLUG>-<YYYYMMDDTHHMMSSZ>` (UTC timestamp)

**Structure**
```
tasks/
  <FEATURE_SLUG>-<YYYYMMDDTHHMMSSZ>/      # = $FEATURE_DIR
    plan.md                               # Plan, Checklist, DoD, Tests, Experts, Research Summary
    decision-log.md                       # One line per loop (EXECUTE)
    referenced-expertise.md               # Expert files used + takeaways
    references/
      excerpts/                           # Snippets pulled from experts/
      web/                                # Web search snapshots & notes (.md)
    proposals/
      expert-additions.md                 # Suggested new/updated expert topics (lessons learned)
    runs/                                 # One subfolder per loop (EXECUTE)
      <ISO8601Z>/
        test-report.md                    # Human summary of the run
        stdout.log                        # Raw stdout
        stderr.log                        # Raw stderr
        metrics.json                      # Perf/coverage/etc. (optional)
        screenshots/                      # UI/visual artifacts (if any)
    benchmarks/                           # Perf comparisons (optional)
    patches/                              # .patch files or diff exports (optional)
    artifacts/                            # Any other generated assets
```

---

## 2) Bootstrap (run once per feature; both modes may write)
```bash
# 1) Define feature variables
CODEX_MODE="${CODEX_MODE:-PLAN_ONLY}"   # PLAN_ONLY | EXECUTE
FEATURE_TITLE="<short human title here>"
FEATURE_SLUG="$(printf '%s' "$FEATURE_TITLE"   | tr '[:upper:]' '[:lower:]'   | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')"
FEATURE_DIR="tasks/${FEATURE_SLUG}-$(date -u +%Y%m%dT%H%M%SZ)"

# 2) Create base scaffold (both modes)
mkdir -p "$FEATURE_DIR"/{references/excerpts,references/web,proposals,artifacts}
: > "$FEATURE_DIR/plan.md"
: > "$FEATURE_DIR/referenced-expertise.md"
: > "$FEATURE_DIR/proposals/expert-additions.md"

# 3) Exec-only folders
if [ "$CODEX_MODE" != "PLAN_ONLY" ]; then
  mkdir -p "$FEATURE_DIR"/{runs,benchmarks,patches,artifacts/screenshots}
  : > "$FEATURE_DIR/decision-log.md"
fi

# 4) Optional index at repo root
if [ -f TASKS.md ]; then
  echo "- [${FEATURE_TITLE}](${FEATURE_DIR}) — $(date -u +%F)" >> TASKS.md
fi

echo "[Bootstrap] Created: $FEATURE_DIR"
```

---

## 3) Plan Template (fill in `plan.md`)
```markdown
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
- Performance: Achieve ≥30% wall-clock reduction on the canonical backtest and keep OnData end-to-end latency ≤50 ms p95 once SLOs are confirmed.
- Security/Compliance: No new outbound network calls or data persistence outside approved directories; maintain reproducibility for audits.
- Compatibility: Preserve compatibility with QuantConnect Lean CLI (`lean.json`), Python 3.10 runtime, and existing configuration/parameter files.
- Delivery: Produce an executable optimization plan and baseline metrics by 2025-10-29 with iteration check-ins every two business days.
- Reliability/Availability: Guarantee trading outputs remain identical (orders, fills, P&L) versus the golden baseline; halt rollout on divergence.
- Observability: Emit structured performance logs (bars/sec, OnData timings, history duration) via Lean logging plus optional StatsD/CSV exports for comparisons.
- Cost: Stay within current single-node CPU/RAM budgets; escalate before provisioning additional hardware.

## Dependencies
- Internal: `ZacQC/core/*`, `ZacQC/data/*`, `ZacQC/trading/*`, `ZacQC/management/*`, `server/` orchestration, `configs/TradingParameters`, `tests/`.
- External: QuantConnect Lean engine & CLI, Python scientific stack (`numpy`, `pandas`), profiling tools (`cProfile`, `line_profiler`), optional `numba`.

## Checklist of Subtasks
- Use `[ ]` now and flip items to `[x]` as you complete them during execution.
- [ ] Capture baseline metrics (bars/sec, OnData latency, warm-up) for representative backtests and live-sim scenarios.
- [ ] Instrument and profile hot paths (OnData, SymbolManager, DataManager, order managers) using cProfile/line-profiler and built-in Lean timings.
- [ ] Optimize data access and state management (batch `History()`, rolling windows, caching strategy, allocation reuse).
- [ ] Streamline algorithm logic (hoist invariants, trim logging, remove per-tick heavy operations) while validating correctness.
- [ ] Evaluate concurrency and orchestration options for backtest batches and server job scheduling without overloading hardware.
- [ ] Enhance observability and regression guardrails (perf dashboards, golden baseline storage, diff tooling).
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
<!-- One query per line. Use phrases (e.g., "python concurrency", "sql indexes"). -->
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
- Cross-cutting updates: Centralize performance instrumentation in `ZacQC/core/utils.py` and shared server metrics helpers; standardize timing decorators.
- Interfaces/contracts: Ensure new configuration options default to current behavior; version parameter schema if additional fields are required.
- Tests: Add nightly perf regression job that runs the harness and compares metrics against stored baseline thresholds.
- CI/CD: Update automation to collect and archive perf metric artifacts; enforce linting on instrumentation code paths.
- Config/migrations: Introduce optional flags (e.g., `enable_perf_opt`, `max_history_batch_size`) with documented defaults and rollback instructions.
- Documentation: Extend README, `docs/`, and runbooks with profiling workflow, new toggles, and regression procedures.

## Data & Migrations
- Schema changes: None anticipated; any cache/index adjustments must be idempotent and gated behind feature flags.
- Privacy: Ensure performance logs exclude PII and follow existing retention/rotation policies within `logs/`.

## Observability, Rollout & Rollback Plan
- Release strategy: Deploy behind `TradingParameters.enable_perf_opt` and server feature flags; enable on staging, then pilot accounts, before full rollout.
- Metrics/SLOs: Track bars/sec, OnData latency p95/p99, warm-up duration, memory footprint, and history request timing; abort rollout if degradation exceeds 5%.
- Rollback path: Disable feature flags, revert to prior config/containers, and restore baseline cached artifacts; exposure window limited to the current trading session.

## Closed-Loop Execution Strategy
- Follow the Closed-Loop protocol (Section 6) with an initial expectation of two to three optimization loops: baseline capture, hot-path optimization, regression hardening.
- For each loop, capture Lean runtime metrics (bars/sec, OnData latency distribution, warm-up duration) and diff against the golden baseline before proceeding.
- Define exit criteria per loop (e.g., ≥20% improvement, no correctness drift) and a stop condition if improvements fall below 5% or metrics regress.
```

---

## 4) Expert Guidance Capture **and Built‑in Web Search** (both modes)
> Use **Codex CLI's built‑in web search tool (MCP)**. Do **not** use custom scripts.

**4.1 Scan local experts/**
```bash
KEYWORDS="python concurrency|async|caching|database|testing|security|lean|nautilus|fastapi|pytest|observability|feature flags|semver|migration|backfill|rollback"
OUT="$FEATURE_DIR/referenced-expertise.md"
{
  echo "# Referenced Expertise"; echo;
  grep -RInE "$KEYWORDS" experts 2>/dev/null | sed 's/^/ - /' || true
} >> "$OUT"
```

**4.2 Derive queries from plan**
- Parse `## Experts to Scan (keywords)` section in `plan.md`; treat **each line as one query**.
- If that section is empty, synthesize 3–5 queries from **Task Overview**, **Constraints**, and **Dependencies**.

**4.3 Discover the available web tool (introspect)**
- List tools and pick the first available in this preference order:
  1. `web.search` → fetch via `web.open`/`web.get`
  2. `browser.search` → fetch via `browser.open`/`browser.get`
  3. `search` → fetch via `open`/`get`
  4. `web.run` (if your MCP exposes a single entrypoint that accepts search+open)
- If none are available, **skip** web research and note it in the plan.

**4.4 Call pattern (MCP pseudo‑contract)**
```
# Search
TOOL: <web.search | browser.search | search>
ARGS: {"query": "<full phrase>", "limit": 10}

# For top 3–5 results:
TOOL: <web.open | browser.open | web.get | get>
ARGS: {"url": "<result.url>"}

# Write one Markdown file per query:
$FEATURE_DIR/references/web/<slug-of-query>--<UTC>.md

# Each file must contain:
- Original query
- Top links (title + URL)
- 3–7 concise bullet insights (quote short excerpts when helpful)
- Any constraints/compat notes relevant to our stack
```

**4.5 Summarize in plan**
- Append `## Web Research Summary` to `plan.md` with 3–5 bullets linking to the created files in `references/web/`.
- Keep summaries **implementation‑relevant** (APIs, version constraints, edge cases).

---

## 5) Expert Augmentation Report (lessons → experts)
> Always produce or update `$FEATURE_DIR/proposals/expert-additions.md` with suggestions.

```markdown
# Proposed Additions/Updates to `experts/`

## <Proposed-Topic-Title>
- **Keywords:** <comma list>
- **Rationale:** <what problem we hit; why existing expertise was insufficient>
- **Proposed outline:**
  - <bullet>
  - <bullet>
- **Example snippet (if any):**
  ```lang
  <short, generic example>
  ```
- **Sources/lessons:** <what run or reference led to this>

## <Another-Topic>
...
```

---

## 6) Closed‑Loop Execution Protocol (EXECUTE mode)
> If `codex_mode: PLAN_ONLY` → **stop here** and output `READY_FOR_APPROVAL` (or `NEEDS_CLARIFICATION`).

**Loop triggers:** failing/flake tests, runtime errors, unmet DoD, new requirements.

**Iterate until DoD passes or stop conditions hit:**
1) **Run & Capture** — execute tests/commands; save logs & metrics; append **Decision Log**.
2) **Diagnose** — one‑line failure summary; smallest viable fix; **re‑scan `experts/`** and **use web search tool** if needed.
3) **Plan** — 3–5 step micro‑plan; files/functions; rollback note; update risk/impact.
4) **Change** — implement minimal delta; commits small; reference `[T‑x]`.
5) **Re‑Test & Compare** — re‑run failing tests; compare metrics; paste deltas.
6) **Decide** — if DoD met → check off [T‑x]; else loop/refine/escalate.

**Stop conditions:** 3 loops without measurable progress, or time‑box exceeded → summarize blockers and ask questions (`BLOCKED`).

---

## 7) Run Directories & Logs (per loop; EXECUTE only)
```bash
[ "$CODEX_MODE" = "PLAN_ONLY" ] && { echo "PLAN_ONLY: skipping runs"; exit 0; }

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"; RUN_DIR="$FEATURE_DIR/runs/$RUN_ID"
mkdir -p "$RUN_DIR"/screenshots

# Replace with your actual test matrix
{
  echo "# Test Report"; echo "- Commands: <list here>";
} > "$RUN_DIR/test-report.md"

{ pytest -q; } 1>"$RUN_DIR/stdout.log" 2>"$RUN_DIR/stderr.log" || true
# Optionally: echo '{"coverage": 0.87, "p95_ms": 112}' > "$RUN_DIR/metrics.json"

printf -- "- [T-x | %s] Result: <pass/fail>. Summary: <one-liner>. Next: <plan>. Sources: <experts...>\n"   "$RUN_ID" >> "$FEATURE_DIR/decision-log.md"
```

---

## 8) Loop‑Ready Task Skeleton (duplicate for each [T‑x])
```markdown
### Task [T-1]: <clear, actionable title>
- **Status:** todo | in‑progress | blocked | done
- **Owner:** Codex
- **DoD:** <copy relevant items from the global DoD or customize>
- **Tests to run:** <exact commands/files>
- **Perf target (if any):** <e.g., p95 < 120ms>
- **Experts to scan (keywords):** <e.g., "python concurrency", "sql indexes">
- **Links/Artifacts:** <$FEATURE_DIR/runs/...>

**Checklist**
- [ ] Plan created for [T‑1] (files/functions to change, rollback)
- [ ] Implementation landed (referenced commits)
- [ ] Tests added/updated and passing
- [ ] DoD verified & documented
- [ ] Notes merged into README/CHANGELOG
```

---

## 9) Pipeline Integration Policy (no ad‑hoc fixes)
**Generalize changes** so they apply across runs and future work:
- **Centralize logic** in shared modules/utilities; avoid one‑off monkey‑patches.
- **Stable interfaces**: version or document contract changes; ensure backward compatibility where needed.
- **Regression safety**: add tests to CI for every discovered bug; guard against recurrence.
- **CI/CD hooks**: enforce lint/type/format and smoke tests; update pipelines if needed.
- **Config/migrations**: ship schema/config changes with migrations and rollbacks.
- **Docs/runbooks**: update README/CHANGELOG and operational notes.
- **Idempotence**: code and scripts should be safe to re‑run.

---

## 10) Where Each Piece Lives (quick reference)
- **Plan & Checklist & DoD:** `$FEATURE_DIR/plan.md`
- **Referenced expertise index:** `$FEATURE_DIR/referenced-expertise.md`
- **Expert augmentation proposals:** `$FEATURE_DIR/proposals/expert-additions.md`
- **Web search notes:** `$FEATURE_DIR/references/web/*.md`
- **Per‑loop raw outputs:** `$FEATURE_DIR/runs/<RUN_ID>/{stdout.log,stderr.log}` (EXECUTE)
- **Per‑loop human summary:** `$FEATURE_DIR/runs/<RUN_ID>/test-report.md` (EXECUTE)
- **Screenshots/visuals:** `$FEATURE_DIR/runs/<RUN_ID>/screenshots/` (EXECUTE)
- **Loop journal:** `$FEATURE_DIR/decision-log.md` (EXECUTE)
- **Optional diffs/patches:** `$FEATURE_DIR/patches/`
- **Optional perf history:** `$FEATURE_DIR/benchmarks/`

---

## 11) Minimal Example (illustrative)
```markdown
# Plan

## Task Overview
Add `/health` endpoint to FastAPI app, returning build info and DB connectivity status. Stack: Python, FastAPI, Postgres. Assume existing app factory and DB pool.

## Definition of Ready (DoR)
- Clarifications resolved: status schema confirmed
- Test strategy: unit tests + simulated DB down
- Rollout: feature flagged route exposure (config toggle)
- Data/backfill: N/A

## Clarification Questions
- [Critical] Should DB ping be a lightweight `SELECT 1` or driver‑level ping?
- [Nice] Include git SHA in response?

## Constraints & Requirements
- Performance: p95 < 50ms for route
- Compatibility: Python 3.11; FastAPI 0.115+
- Delivery: end of week
- Observability: structured logs on failure

## Dependencies
- Internal: app factory module, DB pool util
- External: Postgres 14

## Checklist of Subtasks
- [ ] Add route `GET /health` with JSON `{status, build, db}`
- [ ] Implement DB ping with 100ms timeout
- [ ] Unit tests for success and DB‑down cases
- [ ] Update README with endpoint docs

## Definition of Done (DoD)
- Functional: 200 OK with schema; 503 when DB ping fails
- Quality: ruff/mypy pass; coverage ≥ 85%
- Docs: README updated with example curl
- Tests: `tests/test_health.py::test_ok` and `::test_db_down` pass

## Tests to Run
pytest -q

## Experts to Scan (keywords)
fastapi healthcheck
database timeout
connection pool ping

## Web Research Summary
- Use built‑in web search: "fastapi healthcheck" — see `references/web/fastapi-healthcheck--*.md`

## Pipeline Integration Plan
- Add `tests/test_health.py` to CI
- Ensure lint/type hooks run on PR
- Document contract in API README and CHANGELOG

## Data & Migrations
N/A

## Observability, Rollout & Rollback Plan
- Release: config toggle to expose route
- Metrics: route latency and failure count
- Rollback: revert commit or disable flag
```

---

## 12) Checklist for the Agent (one‑shot summary)
- [ ] **Resolve mode** (PLAN_ONLY by default; EXECUTE only if user intent says so).
- [ ] **Parse request** → derive `FEATURE_TITLE`; one‑line problem statement.
- [ ] **Compute identifiers** → `FEATURE_SLUG`, `FEATURE_DIR`.
- [ ] **Scaffold** → base dirs; exec‑only dirs if EXECUTE.
- [ ] **Fill `plan.md`** → Overview, DoR, Clarifications, Constraints, Dependencies, Checklist, DoD, Tests, Experts, Web Research Summary, Risks, Pipeline, Data, Observability.
- [ ] **Clarification Gate** → if any Critical question unresolved → `NEEDS_CLARIFICATION`.
- [ ] **Index experts** → grep `experts/`; capture excerpts.
- [ ] **Built‑in Web Search** → introspect tools; call `<web.search>`; fetch with `<web.open>`; write under `references/web/`; summarize in plan.
- [ ] **EXECUTE?** If PLAN_ONLY → end with `READY_FOR_APPROVAL`. If EXECUTE and no blockers → start Closed Loop.
- [ ] **Closed Loop (EXECUTE)** → run, diagnose, plan, change, re‑test, decide; log each run; update Decision Log.
- [ ] **Pipeline integration** → generalize fixes; update shared modules, CI, docs.
- [ ] **Finalize** → DoD all green; mark task done; summarize lessons in proposals file.
