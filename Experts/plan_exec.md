output_contract:
  allowed_sections:
    - Task Overview
    - Definition of Ready (DoR)
    - Clarification Questions
    - Constraints & Requirements
    - Dependencies
    - User Stories
    - Checklist of Subtasks
    - Definition of Done (DoD)
    - Tests to Run
    - Experts to Scan (keywords)
    - Risks & Mitigations
    - Pipeline Integration Plan
    - Data & Migrations
    - Observability, Rollout & Rollback Plan
    - Implementation Plan
stop_tokens:
  needs_clarification: NEEDS_CLARIFICATION
  blocked: BLOCKED
---

# Ultimate Codex CLI Task Planning Template — **v2**

This single file has two clearly separated parts:
- Part 1 — Plan Template (copy into `plan.md`)
- Part 2 — Agent Guide (Plan Authoring Only)
- Part 3 — Examples & Appendices (optional, for reference)

---

## How to Use (Quick Start)
- Derive `FEATURE_TITLE` and slug → create `tasks/<slug>-<UTC>`.
- Copy the Plan Template block (Part 1) into `plan.md`.
- Follow the Agent Guide (Part 2): Bootstrap → quick research (local first, then web if needed) → draft and finalize plan with multiple User Stories (each with its own Implementation Plan, Execution Protocol, and Runbook & Logs; add a cross‑cutting Implementation Plan if needed).
- Keep logs/artifacts under the feature folder; on every loop update: Decision Log, Tasks Checklist statuses, referenced expertise, and proposed expert additions (when gaps appear).

---

## Part 1 — plan.md Template (Copy/Paste)
Copy everything between the BEGIN/END markers into your `plan.md`, then fill it in.

<!-- BEGIN: plan.md template -->
```markdown
# Plan

## Task Overview
<3–5 sentences: user request, problem, goal, domain/stack, assumptions>

## Definition of Ready (DoR)
- Clarifications resolved: <list>
- Test strategy agreed (matrix)
- Rollout strategy (flag/canary/batch)
- Data/backfill owner assigned (if applicable)

## Clarification Questions
<!-- Ask before executing. Mark each as Critical or Nice-to-have. One per bullet. -->
- [Critical] <question>
- [Critical] <question>
- [Nice] <question>

## Constraints & Requirements
- Performance: <targets/budgets>
- Security/Compliance: <requirements>
- Compatibility: <versions, OS, API contracts>
- Delivery: <deadline/timebox>
- Reliability/Availability: <SLO/SLA>
- Observability: <logs/metrics/traces you’ll emit>
- Cost: <budget guardrail>
- E2E Runtime Budgets: <total ≤ X min; per‑spec ≤ Y sec; flakiness ≤ Z%>

## Dependencies
- Internal: <modules/services>
- External: <APIs/SDKs/infra>

## User Stories
Duplicate the following story block for each user story in scope. Execute the closed loop per story; NEVER proceed to the next story unless the current story’s Acceptance Criteria (AC) are satisfied and evidenced. Do not advance based solely on partial work; the story must also meet its DoD.

Note — Never‑Stop Continuity: Unless a blocking condition occurs, do not stop execution. After completing a story’s Exit Checklist, immediately begin the next story and continue until all User Stories are finished. Allowed pauses: `NEEDS_CLARIFICATION`, `BLOCKED`, time‑box reached, or 3 loops without measurable progress. When pausing, append a Decision Log entry and state the blocker explicitly.

### Story [S-1]: <short, actionable title>
- Story ID: S-1 | Priority: <P0/P1/P2> | Owner: <name> | Due: <date>
- User Story: As a <role>, I want <capability>, so that <value>.
- Dependencies: <internal/external> | Non‑goals: <optional>

#### Acceptance Criteria
- Given <context>, When <action>, Then <outcome>
- Given <...>, When <...>, Then <...>

#### Story Definition of Ready (DoR)
- Clarifications: <list>
- Test strategy: <unit/integration/e2e mapped to AC>
- Data/backfill: <if applicable>

#### Tasks Checklist
- [ ] <task 1>
- [ ] <task 2>
- [ ] <task 3>

#### Story Tests to Run
- Unit/Integration: <exact commands or test files>
- E2E (Playwright, if applicable):
  - Fast: `E2E_MODE=fast npx playwright test tests/e2e/<story>.spec.ts -g "@smoke" --workers=2 --retries=1 --timeout=30000`
  - Monitoring: `(/usr/bin/time -v || time -lp) npx playwright test ... 2>&1 | tee "$FEATURE_DIR/runs/S-1/<RUN_ID>/stdout.log"`
  - Budget: finish ≤ 60 s for this story’s spec; if exceeded, adjust params or raise `BLOCKED` with evidence.

#### Story Definition of Done (DoD)
- <AC satisfied; tests pass; docs updated; perf/quality gates>

#### Story Exit Checklist (AC Gate — do not proceed unless all checked)
- [ ] All Acceptance Criteria (AC) demonstrably satisfied
- [ ] Evidence captured in Runbook (test reports/screenshots/logs)
- [ ] “Story Tests to Run” all passing in this repo
- [ ] Story Definition of Done fully met
- [ ] Tasks Checklist reflects final state
- [ ] Decision Log includes final "Done" entry for this story
- [ ] Expertise captured; proposals filed if new guidance is warranted
- [ ] E2E (if applicable) ran in Fast mode within runtime budget; monitoring logs attached

#### Story Implementation Plan
- <3–7 steps; files/modules to change; interface/contract updates>

#### Story Execution Protocol (Closed Loop)
Note: Applies to both bug fixes and new features.
Optional pre-steps:
- Bug fix — 0) Reproduce & write failing test
- Feature — 0) Define smallest shippable slice & acceptance tests (flag if needed)
1) Run & Capture — execute tests/commands for S‑1; save logs & metrics; update Decision Log; update Tasks Checklist status; capture new insights in `$FEATURE_DIR/referenced-expertise.md`; if gaps found, add bullets to `$FEATURE_DIR/proposals/expert-additions.md`.
2) Diagnose — one‑line failure summary; smallest viable fix; re‑scan `experts/` and internal docs if needed.
3) Plan — 3–5 step micro‑plan; files/functions; rollback note; update risk/impact.
4) Change — implement minimal delta; commits small; reference `[S‑1/T‑x]`.
5) Re‑Test & Compare — re‑run failing tests; compare metrics; paste deltas.
6) Decide — if AC met AND Story Exit Checklist is fully checked → mark S‑1 done; else loop/refine/escalate.

Stop conditions (allowed pauses): `NEEDS_CLARIFICATION`, `BLOCKED`, 3 loops without measurable progress, or time‑box exceeded. On pause → summarize blockers for S‑1 in the Decision Log and emit the appropriate stop token.

#### Story Runbook & Logs
- Test matrix: <commands/environments>
- Logs: `$FEATURE_DIR/runs/S-1/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-1/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-1]`
- Artifacts: `$FEATURE_DIR/artifacts/` (screenshots under `artifacts/screenshots/`)
 
#### Story Progress & Hygiene (per loop)
- Update Tasks Checklist statuses (reflect current progress accurately)
- Append Decision Log entry `[S-1]` with: timestamp, Attempt, Result, Evidence, Next step or Exit decision
- Capture expertise: update `$FEATURE_DIR/referenced-expertise.md`; link context excerpts under `references/excerpts/`
- Propose additions: update `$FEATURE_DIR/proposals/expert-additions.md` if guidance gaps exist
- If E2E applies: record runtime vs budget and monitoring summary in the Decision Log
 
#### Links/Artifacts
- <PRs, tickets, docs>

## Checklist of Subtasks
- Gate: confirm current story’s “Story Exit Checklist” is complete before starting the next story
- Never‑Stop: after finishing a story, immediately start the next one (unless blocked)
- All User Stories completed (each Exit Checklist fully checked)
- Per-loop hygiene: update Tasks Checklist statuses, append Decision Log, capture expertise, propose expert additions if needed
- Plan & Setup (repo/env ready, confirm requirements)
- Design Solution (modules, data flow, interfaces)
- Implement Core Functionality (primary logic, edge cases)
- Integrate Components (wire modules, data contracts)
- Testing (unit/integration/e2e as applicable)
- Optimization (refactor/perf/quality passes)
- Documentation & Final Review (README, examples)

## Definition of Done (DoD)
- Functional: <behaviors pass acceptance tests>
- Quality: <lint/type checks pass; coverage ≥ X%; key perf ≥ Y>
- UX/API: <stable interface/contract; clear errors>
- Docs: <usage notes + examples>
- Tests: <exact tests that must pass>

## Tests to Run
- Unit: <e.g., `pytest -q`, `npm test`, `go test ./...`}>
- Integration: <e.g., `pytest -q tests/integration`, `pnpm vitest`>
- E2E (Playwright, if web UI):
  - Setup: `npx playwright install --with-deps`
  - Modes:
    - Fast (default, smoke): `E2E_MODE=fast npx playwright test --project=chromium -g "@smoke" --workers=2 --retries=1 --timeout=30000 --reporter=list,junit`
    - Full (nightly/PR opt‑in): `E2E_MODE=full npx playwright test --project=chromium --retries=2 --timeout=45000 --reporter=junit`
  - Runtime budgets: total ≤ 5 min in Fast mode; each spec ≤ 60 s; raise `BLOCKED` if exceeded and capture evidence.
  - Parameterization guidance: prefer headless; stub external calls; limit data range/time windows; reduce fixtures size; minimize retries/workers for stability; capture trace/video only on failure.
  - Monitoring during run: wrap with `/usr/bin/time -v` (or `time -lp` on macOS) and `tee` logs; consider `docker stats`/`pidstat` if containerized.
  - Practices: add `data-testid` selectors; stub network where appropriate; use fixtures for auth/data; keep tests deterministic, idempotent, and parallel‑safe.

## Experts to Scan (keywords)
<!-- One query per line for scanning local experts/docs. -->
<keyword 1>
<keyword 2>
<keyword 3>

## Risks & Mitigations
- Risk: <...> → Mitigation: <...>
- Risk: <...> → Mitigation: <...>

## Pipeline Integration Plan
- Cross-cutting updates: <shared modules/utilities to modify>
- Interfaces/contracts: <versioning, backward compatibility>
- Tests: <add regression tests to CI to prevent reoccurrence>
- CI/CD: <lint/type/format hooks; pipelines to update>
- Config/migrations: <schema/config migrations and rollbacks>
- Documentation: <README/CHANGELOG/Runbooks>

## Data & Migrations
- Schema changes: <up/down scripts; backfill plan; idempotency>
- Privacy: <PII handling; retention>

## Observability, Rollout & Rollback Plan
- Release strategy: <feature flag/canary/date‑based>
- Metrics/SLOs: <success/failure guardrails, abort criteria>
- Rollback path: <how to revert code/config/data; max exposure window>
 
## Implementation Plan (optional, cross‑cutting)
- Steps: <3–7 concrete cross‑cutting steps; files/modules to touch; interfaces/contracts to change>
- Rollback: <minimal rollback plan if changes fail>
- Risks/Impact: <key risks that affect implementation>
```
<!-- END: plan.md template -->

---

## Part 2 — Agent Guide (Plan Authoring Only)

### Agent Contract
- Ask Clarification Questions and emit `NEEDS_CLARIFICATION` if any critical item is unresolved.
- Always scan local `experts/` and internal docs; capture relevant excerpts.
- If local sources are insufficient, perform a brief, targeted web search before drafting the plan; integrate only essential findings into relevant plan sections (Constraints, Dependencies, Risks). No separate web‑research section is required.
- Produce a structured Plan (Part 1) with multiple User Stories. Each story must include its own Implementation Plan, Execution Protocol, and Runbook & Logs; add a cross‑cutting Implementation Plan only if needed. Do not execute code in this phase.
- Never add performance-improvement acceptance criteria or metrics unless the user explicitly requests them.
- Never advance to the next user story until the current story’s Acceptance Criteria are satisfied and evidenced; use the “Story Exit Checklist” as the gate.
- Enforce process hygiene every loop: update the Tasks Checklist, append a Decision Log entry, capture any new expertise in `referenced-expertise.md`, and propose additions in `proposals/expert-additions.md` when guidance gaps appear.
- Keep E2E fast and monitored: select Fast parameters by default, enforce runtime budgets, and capture monitoring output alongside test reports.
- Emit an Expert Augmentation proposal if new guidance is warranted.

### Plan Flow & Clarification Gate
- If any critical clarification is unanswered → emit `NEEDS_CLARIFICATION` before starting.
- Flow: Clarify → Bootstrap → Local‑first research → Define User Stories → Draft & finalize plan (per‑story Implementation Plan, Execution Protocol, Runbook & Logs).
- Per‑story gating: Do not advance to the next story until the “Story Exit Checklist” is complete (all AC satisfied and evidenced).

### Process Hygiene (must-do, every loop)
- Update checkboxes in the story’s Tasks Checklist to reflect actual progress.
- Add a Decision Log entry under `$FEATURE_DIR/decision-log.md` using the template in Appendix C.
- Record newly referenced expertise and links in `$FEATURE_DIR/referenced-expertise.md`; store excerpts under `references/excerpts/`.
- If new guidance is needed for future work, add concise bullets under `$FEATURE_DIR/proposals/expert-additions.md`.
- If E2E ran, record runtime vs budget and monitoring outputs in the Decision Log.

### Recommended Practices (baked into plan.md)
- Testing
  - Require a smoke test (live or end-to-end) in every user story whenever the feature can be validated via a quick real execution; list the exact command/spec under “Story Tests to Run”.
  - Prefer Playwright for E2E on web UIs; add `data-testid` attributes; keep tests deterministic; run headless in CI with JUnit/HTML reports.
  - Use fixtures for auth/data; stub external network calls; keep tests parallel‑safe.
  - E2E speed & stability: run Fast mode by default (smoke/@smoke tag), limit data/time ranges, stub external calls, cap workers (e.g., `--workers=2`), set strict per‑spec timeouts, and enable trace/video only on failure.
- Sub‑Agent Delegation (Codex CLI)
  - Delegate mechanical tasks (scaffold tests, generate page objects/mocks, seed test data, update CI) as “Sub‑Agent Delegation” items under each story.
  - Specify inputs (AC, endpoints, mock data) and acceptance (files, paths, tests that must pass).
- Data & Environments
  - Use `.env.test` and ephemeral resources; avoid PII in logs; ensure idempotent migrations/seeders.
  - Proactively inspect config files, `.env` files, and JSON settings for available API keys or credentials needed to execute smoke tests, and reference their locations in the plan.
- Reliability & Observability
  - Set timeouts/retries thoughtfully; add structured logs around critical paths; capture artifacts under `$FEATURE_DIR/runs/S-*/<RUN_ID>/`.
 - Process Hygiene
  - After every loop, update Tasks Checklist, append to `decision-log.md`, record new expertise in `referenced-expertise.md`, and add bullets to `proposals/expert-additions.md` when guidance gaps are discovered.

### 1) Workspace & Bootstrap (what and how)
Create a dedicated feature folder and write all plans, logs, and artifacts there.

Naming
- Feature title: short human title (e.g., `Auth refresh token`)
- Feature slug: kebab‑case (e.g., `auth-refresh-token`)
- Feature dir: `tasks/<FEATURE_SLUG>-<YYYYMMDDTHHMMSSZ>` (UTC)

Structure
```
tasks/
  <FEATURE_SLUG>-<YYYYMMDDTHHMMSSZ>/      # = $FEATURE_DIR
    plan.md                               # Plan, Checklist, DoD, Tests, Experts
    decision-log.md                       # One line per loop
    referenced-expertise.md               # Expert files used + takeaways
    references/
      excerpts/                           # Snippets pulled from experts/
    proposals/
      expert-additions.md                 # Suggested new/updated expert topics
    runs/                                 # One subfolder per loop
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

Bootstrap (how to create it)
```bash
# 1) Define feature variables
FEATURE_TITLE="<short human title here>"
FEATURE_SLUG="$(printf '%s' "$FEATURE_TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')"
FEATURE_DIR="tasks/${FEATURE_SLUG}-$(date -u +%Y%m%dT%H%M%SZ)"

# 2) Create base scaffold
mkdir -p "$FEATURE_DIR"/{references/excerpts,proposals,runs,benchmarks,patches,artifacts,artifacts/screenshots}
: > "$FEATURE_DIR/plan.md"
: > "$FEATURE_DIR/referenced-expertise.md"
: > "$FEATURE_DIR/proposals/expert-additions.md"
: > "$FEATURE_DIR/decision-log.md"

# 3) Optional index at repo root
if [ -f TASKS.md ]; then
  echo "- [${FEATURE_TITLE}](${FEATURE_DIR}) — $(date -u +%F)" >> TASKS.md
fi

echo "[Bootstrap] Created: $FEATURE_DIR"
```

 

### 2) Expert Guidance Capture (local-first)
Goal: collect relevant internal guidance fast, with low noise. Prefer ripgrep when available; fallback to grep. Broaden sources, ignore noise, capture context, and dedupe.

```bash
set -Eeuo pipefail

# 0) Defaults and toggles
DEFAULT_KW="python concurrency|async|caching|database|testing|security|fastapi|pytest|observability|feature flags|semver|migration|backfill|rollback"
INCLUDE_CODE_SOURCES="${INCLUDE_CODE_SOURCES:-false}"   # set to true to include src/

OUT_MD="$FEATURE_DIR/referenced-expertise.md"
OUT_EXCERPTS="$FEATURE_DIR/references/excerpts/${FEATURE_SLUG}-refs.txt"
mkdir -p "$(dirname "$OUT_EXCERPTS")"

# 1) Build sources list (experts, docs, READMEs/CHANGELOGs, AGENTS.md)
SOURCES=(experts docs README* CHANGELOG*)
mapfile -t AGENTS < <(find . -type f -iname 'AGENTS.md' 2>/dev/null || true)
if [ ${#AGENTS[@]} -gt 0 ]; then SOURCES+=("${AGENTS[@]}"); fi
if [ "$INCLUDE_CODE_SOURCES" = "true" ] && [ -d src ]; then SOURCES+=(src); fi

# 2) Derive keywords from plan (escape regex; join with |)
PLAN_KW=$(sed -n "/^## Experts to Scan (keywords)/,/^## /p" "$FEATURE_DIR/plan.md" \
  | sed '1d;$d' | sed '/^\s*$/d' | sed -E 's/[\\^$.|?*+()\[\]{}]/\\&/g' || true)
if [ -n "$PLAN_KW" ]; then
  KEYWORDS=$(printf '%s\n' "$PLAN_KW" | paste -sd'|' -)
else
  KEYWORDS="$DEFAULT_KW"
fi

# 3) Common options and ignores
RG_OPTS=( -n -H -S -I -i --no-heading --line-number \
  --glob '!**/.git' --glob '!**/node_modules' --glob '!**/dist' --glob '!**/build' \
  --glob '!**/target' --glob '!**/venv' --glob '!**/.venv' --glob '!**/*.pem' \
  --glob '!**/*.key' --glob '!**/.env' )

# 4) Run scan → referenced-expertise.md (deduped) + context excerpts file
{
  echo "# Referenced Expertise"; echo;
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "## Scan @ $TS"; echo "- Keywords: $KEYWORDS"; echo;

  if command -v rg >/dev/null 2>&1; then
    rg "${RG_OPTS[@]}" -e "$KEYWORDS" "${SOURCES[@]}" 2>/dev/null \
      | sort -u | sed 's/^/ - /'
    echo; echo "### Context excerpts (-C2)"; echo '```'
    rg "${RG_OPTS[@]}" -C 2 -e "$KEYWORDS" "${SOURCES[@]}" 2>/dev/null | tee "$OUT_EXCERPTS"
    echo '```'
  else
    # grep fallback (best-effort ignores)
    GREP_BASE=(grep -RInE --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist \
      --exclude-dir=build --exclude-dir=target --exclude-dir=venv --exclude-dir=.venv \
      --exclude='*.pem' --exclude='*.key' --exclude='.env')
    "${GREP_BASE[@]}" "$KEYWORDS" "${SOURCES[@]}" 2>/dev/null | sort -u | sed 's/^/ - /'
    echo; echo "### Context excerpts (-C2)"; echo '```'
    "${GREP_BASE[@]}" -C 2 "$KEYWORDS" "${SOURCES[@]}" 2>/dev/null | tee "$OUT_EXCERPTS"
    echo '```'
  fi

  echo; echo "### Top files (by hits)"
  awk -F: '{print $1}' "$OUT_EXCERPTS" 2>/dev/null | sort | uniq -c | sort -nr | head -n 10 \
    | sed 's/^/ - /'
} >> "$OUT_MD"
```

Optional: derive keywords
- Parse “Experts to Scan (keywords)” in `plan.md`; treat each line as a keyword to search within the repo (`experts/`, `docs/`, `README*`, `CHANGELOG*`).
- If empty, synthesize 3–5 keywords from Task Overview, Constraints, and Dependencies.
- Tip: add synonyms from Dependencies/Constraints (e.g., `fastapi|starlette`, `pytest|unit test`).

If local sources are thin, perform a short web scan to answer concrete unknowns (APIs, version constraints, edge cases). Capture only the takeaways needed to complete the plan; cite links inline where appropriate. Control with `ENABLE_WEB_RESEARCH=auto|always|never` in your environment or runbook.

### 3) Plan Authoring Checklist (one‑shot)
- [ ] Parse request → derive `FEATURE_TITLE`; one‑line problem statement.
- [ ] Compute identifiers → `FEATURE_SLUG`, `FEATURE_DIR`.
- [ ] Scaffold → base dirs and files.
- [ ] Fill `plan.md` → Overview, DoR, Clarifications, Constraints, Dependencies, Checklist, DoD, Tests, Experts, Risks, Pipeline, Data, Observability, Implementation Plan, Execution Protocol, Runbook & Logs.
- [ ] Clarification Gate → if any Critical question unresolved → `NEEDS_CLARIFICATION`.
- [ ] Index experts → scan `experts/`; capture excerpts.
- [ ] Summarize key insights in plan (Constraints/Dependencies/Risks) and note open questions.

### 4) Plan Handoff & Locations
- Plan: `$FEATURE_DIR/plan.md`
- Referenced expertise index: `$FEATURE_DIR/referenced-expertise.md`
- Excerpts: `$FEATURE_DIR/references/excerpts/`
- Proposals (expert augmentation): `$FEATURE_DIR/proposals/expert-additions.md`
- Optional run index (repo root): `TASKS.md`

---

## Part 3 — Examples & Appendices

### Example: Minimal Plan (FastAPI health)
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
- Add route `GET /health` with JSON `{status, build, db}`
- Implement DB ping with 100ms timeout
- Unit tests for success and DB‑down cases
- Update README with endpoint docs

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

### Example: User Story (S‑1) — Health Endpoint Returns Build and DB Status
```markdown
## User Stories

### Story [S-1]: Health endpoint returns build and DB status
- Story ID: S-1 | Priority: P1 | Owner: Backend Team | Due: 2025-10-31
- User Story: As an SRE, I want `/health` to expose build info and DB connectivity, so that probes and dashboards can reflect service health.
- Dependencies: app factory, DB pool util | Non‑goals: deep dependency health

#### Acceptance Criteria
- Given the app is running, When I call `GET /health`, Then I get 200 and JSON with `{status: "ok", build: {version, sha}, db: {status: "up"}}` when DB is reachable.
- Given DB is down, When I call `GET /health`, Then I get 503 and JSON `{status: "degraded", db: {status: "down"}}`.

#### Story Definition of Ready (DoR)
- Clarifications: confirm response schema; confirm 503 on DB failure
- Test strategy: unit tests + simulated DB down
- Data/backfill: N/A

#### Tasks Checklist
- [ ] Add route `GET /health`
- [ ] Implement DB ping with 100ms timeout
- [ ] Include build info from env/CI (`VERSION`, `GIT_SHA`)
- [ ] Add tests for ok and DB‑down cases
- [ ] Update README with endpoint docs

#### Story Tests to Run
- pytest -q tests/test_health.py::test_ok tests/test_health.py::test_db_down
  # If a UI exists for this flow, run a Fast E2E smoke for this story (≤60s):
  # E2E_MODE=fast npx playwright test tests/e2e/health.spec.ts -g "@smoke" --workers=2 --retries=1 --timeout=30000

#### Story Definition of Done (DoD)
- AC satisfied; response matches schema; 503 on DB failure; tests pass; docs updated

#### Story Exit Checklist (AC Gate — do not proceed unless all checked)
- [ ] All Acceptance Criteria satisfied for S‑1
- [ ] Evidence captured in Runbook (test report, logs)
- [ ] Listed tests passing: ok and db_down
- [ ] DoD items verified
- [ ] Tasks Checklist reflects final state
- [ ] Decision Log includes final "Done" entry `[S‑1]`
- [ ] Expertise captured; proposals filed if needed

#### Story Implementation Plan
- Wire new `GET /health` in router; return schema `{status, build, db}`
- Add DB ping util using pool with 100ms timeout; map failure → 503
- Inject `VERSION`/`GIT_SHA` from env; default to `unknown`
- Write two tests: ok, db_down (mock/patched pool)
- Update README with example curl

#### Story Execution Protocol (Closed Loop)
1) Run & Capture — execute listed tests; save logs; update Decision Log `[S‑1]`; update Tasks Checklist; capture expertise; add proposals if needed; if E2E ran, record runtime vs budget and attach monitoring outputs.
2) Diagnose — summarize failures; pick smallest viable fix.
3) Plan — micro‑plan with files/functions to change; note rollback.
4) Change — implement minimal delta; reference `[S‑1/T‑x]`.
5) Re‑Test & Compare — rerun failing tests; verify schema/HTTP codes.
6) Decide — if AC met AND Story Exit Checklist is fully checked → mark S‑1 done; else loop/refine (Never‑Stop unless blocked/time‑box/3‑loop rule applies).

#### Story Runbook & Logs
- Test matrix: pytest -q
- Logs: `$FEATURE_DIR/runs/S-1/<RUN_ID>/{stdout.log,stderr.log}`
- Run summaries: `$FEATURE_DIR/runs/S-1/<RUN_ID>/test-report.md`
- Decision log entry tag: `[S-1]`
- Artifacts: `$FEATURE_DIR/artifacts/`
 
#### Story Progress & Hygiene (per loop)
- [ ] Update Tasks Checklist statuses
- [ ] Append Decision Log entry `[S-1]` with Attempt, Result, Evidence, Next step/Exit
- [ ] Capture expertise in `referenced-expertise.md`; link relevant excerpts
- [ ] Propose additions in `proposals/expert-additions.md` if warranted

#### Links/Artifacts
- PR: <link>
- Ticket: <link>
```

### Appendix A: Loop‑Ready Task Skeleton
```markdown
### Task [T-1]: <clear, actionable title>
- Status: todo | in‑progress | blocked | done
- Owner: Codex
- DoD: <copy relevant items from the global DoD or customize>
- Tests to run: <exact commands/files>
- Perf target (if any): <e.g., p95 < 120ms>
- Experts to scan (keywords): <e.g., "python concurrency", "sql indexes">
- Links/Artifacts: <$FEATURE_DIR/runs/...>

Checklist
- [ ] Plan created for [T‑1] (files/functions to change, rollback)
- [ ] Implementation landed (referenced commits)
- [ ] Tests added/updated and passing
- [ ] DoD verified & documented
- [ ] Notes merged into README/CHANGELOG
```

### Appendix B: Expert Augmentation Report (lessons → experts)
```markdown
# Proposed Additions/Updates to `experts/`

## <Proposed-Topic-Title>
- Keywords: <comma list>
- Rationale: <what problem we hit; why existing expertise was insufficient>
- Proposed outline:
  - <bullet>
  - <bullet>
- Example snippet (if any):
  ```lang
  <short, generic example>
  ```
- Sources/lessons: <what run or reference led to this>

## <Another-Topic>
...
```

### Appendix D: E2E Runtime & Monitoring Cheatsheet (optional)
```bash
# Fast smoke run with runtime capture (Linux)
/usr/bin/time -v npx playwright test --project=chromium -g "@smoke" \
  --workers=2 --retries=1 --timeout=30000 --reporter=list,junit \
  2>&1 | tee "$FEATURE_DIR/runs/S-*/$(date -u +%Y%m%dT%H%M%SZ)/stdout.log"

# macOS variant (fallback if /usr/bin/time -v not available)
time -lp npx playwright test --project=chromium -g "@smoke" --workers=2 --retries=1 --timeout=30000

# Containerized monitoring (optional)
docker stats --no-stream

# Record slow tests (pytest example)
pytest -q --durations=10
```

### Appendix C: Decision Log Entry Template
```markdown
## [S-<id>] <short outcome> — <YYYY-MM-DDTHH:MM:SSZ>
- Attempt: <what you ran/changed>
- Result: <pass/fail, key deltas>
- Evidence: <paths to reports/logs/artifacts>
- Decision: <continue/refine/escalate/done/blocked>
- Next step: <1–2 lines or link to micro‑plan>
- Runtime (if E2E): <total vs budget; slowest spec>
- Monitoring: <brief notes, e.g., CPU/mem spikes; links to logs>
```
