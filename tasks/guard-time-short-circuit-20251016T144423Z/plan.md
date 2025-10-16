# Plan

## Task Overview
Implement a guard-time short circuit inside `SymbolManager.OnData` so ZacQC skips metrics and strategy evaluation when the algorithm window is closed and no position or pending order exists. This targets runtime savings during "algo-off" periods without touching order outcomes. Work happens in the QuantConnect Lean Python stack under `ZacQC/`, leveraging earlier performance instrumentation. Assumption: the existing Lean benchmarks remain the verification path.

## Definition of Ready (DoR)
- Clarifications resolved: None pending; guard logic defined.
- Test strategy agreed (matrix)
- Rollout strategy (flag/canary/batch)
- Data/backfill owner assigned (if applicable)

## Clarification Questions
- [Nice] Do we need additional telemetry around the short-circuit hit rate for future tuning?

## Constraints & Requirements
- Performance: Maintain order parity; target ≥10% runtime drop in algo-off segments.
- Security/Compliance: No external dependencies.
- Compatibility: Python 3.10 Lean runtime; maintain QuantConnect API contracts.
- Delivery: Aim to land within current sprint (week of 2025-10-16).
- Reliability/Availability: No change to trading logic outputs.
- Observability: Reuse existing performance logs; consider optional counter for skip events.
- Cost: No extra infrastructure costs.
- E2E Runtime Budgets: Lean backtest ≤ 75 s wall clock post-change.
 - Isolation & Namespacing:
   - Git worktree: branch `feat/guard-time-short-circuit-20251016T144423Z` at `/Users/ahmedkhattab/Desktop/Projects/Zac/zac_qc/.worktrees/guard-time-short-circuit-20251016T144423Z`
   - Feature dir: `tasks/guard-time-short-circuit-20251016T144423Z`
   - Env vars: `FEATURE_SLUG=guard-time-short-circuit`, `FEATURE_DIR=tasks/guard-time-short-circuit-20251016T144423Z`, `ENV_DIR=/Users/ahmedkhattab/Desktop/Projects/Zac/zac_qc/.worktrees/guard-time-short-circuit-20251016T144423Z`
   - Ports: allocate if services are introduced (not expected)
   - Tool caches (as applicable): set per need when running tooling

## Dependencies
- Internal: `ZacQC/core/symbol_manager.py`, `ZacQC/trading/conditions_checker.py`, `ZacQC/config/parameters.py`
- External: QuantConnect Lean CLI for regression backtests

## User Stories

### Story [S-1]: Guard window short-circuit
- Story ID: S-1 | Priority: P1 | Owner: Codex | Due: 2025-10-18
- User Story: As a ZacQC maintainer, I want non-trading portions of the day to skip heavy processing so that backtests finish faster without impacting fills.
- Dependencies: Internal modules only | Non-goals: Change to guard window configuration

#### Acceptance Criteria
- Given the algorithm is outside `Algo_Off_Before/After` and has no open trades or pending orders, When a 15-second bar arrives, Then `SymbolManager.OnData` exits before metrics and strategy processing.
- Given there is an open trade or pending order, When the guard window is closed, Then the pipeline still runs to manage exits.
- Given the canonical backtest, When run before and after the change, Then order/trade outputs remain identical.

#### Story Definition of Ready (DoR)
- Clarifications: None outstanding
- Test strategy: Baseline vs modified Lean backtest diff; unit coverage unchanged
- Data/backfill: Not applicable

#### Tasks Checklist
- [x] Instrument entry guard detection
- [x] Implement skip logic conditioned on guard window and position/pending orders
- [x] Capture benchmark before/after and diff outputs
- [ ] Update telemetry or logs if required

#### Story Tests to Run
- Unit/Integration: `lean backtest ZacQC`
- E2E (Playwright, if applicable): N/A

#### Story Definition of Done (DoD)
- All AC met; Lean backtest diff clean; runtime improvement measured; documentation of guard behavior recorded.

#### Story Exit Checklist (AC Gate — do not proceed unless all checked)
- [x] AC verified via logs/backtest diff
- [x] Runtime comparison captured
- [x] Documentation/plan updated

## Checklist of Subtasks
- [x] Draft implementation plan referencing affected modules
- [x] Apply code changes in isolated branch
- [x] Run backtest benchmark and collect metrics
- [x] Document results in task folder

## Definition of Done (DoD)
- Code merged into feature branch with passing backtest and no order diffs
- Runtime improvement recorded and shared
- Plan updated with execution notes

## Tests to Run
- `lean backtest ZacQC`

## Experts to Scan (keywords)
- "lean backtest performance"
- "python short circuit trading loop"

## Risks & Mitigations
- Risk: Skip logic accidentally bypasses cleanup with pending orders → Mitigation: Check positions and order tickets before short circuit.
- Risk: Runtime gains insufficient → Mitigation: add telemetry to evaluate hit rate and revisit conditions.

## Pipeline Integration Plan
- Develop in feature worktree branch, merge via PR into main after validation.

## Data & Migrations
- None

## Observability, Rollout & Rollback Plan
- Observability: reuse existing `PERF_FINAL` logs; optional counter for skip path.
- Rollout: single release via merge.
- Rollback: revert PR or disable skip with feature flag (if introduced).

## Implementation Plan
- Add helper in `SymbolManager` to detect active guard + outstanding work; integrate early return.
- Ensure guard leverages `conditions_checker.is_entry_order_enabled` and portfolio/order state.
- Update performance summaries or debug logging for optional instrumentation.
- Run Lean backtest before/after to confirm parity and timing.
