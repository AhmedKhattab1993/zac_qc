# Closed‑Loop Testing Playbook (Agent‑Facing)

> **Audience:** A CLI coding agent (e.g., Codex) operating locally.  
> **Scope:** Web apps, Python backend servers, and trading engines (QuantConnect/Nautilus).  
> **Constraint:** No cloud tools. No code snippets. Keep context usage low.

---

## 1) Your Mission
You iteratively **test → analyze → fix → verify** until the defined success criteria are met. You log each iteration concisely, add observability only when needed, and stop or escalate when progress stalls.

### Non‑negotiables
- **Local‑only:** Run everything on the local machine. Do not invoke cloud services.
- **Safety:** Never connect to live trading. Only backtest/paper/simulate. Do not mutate production data.
- **Determinism:** Favor deterministic runs (fixed seeds where applicable, stable data snapshots, reset state between runs).
- **Small changes:** Prefer minimal, targeted edits per loop to reduce new breakage.
- **Context economy:** Always summarize; never paste full logs unless essential.

---

## 2) Define “Done” Before You Start
Establish a concrete target so the loop can terminate:

- **Web/Python backend:** All targeted tests pass; key endpoints behave as expected; no unhandled exceptions in logs.
- **Trading engine (QC/Nautilus):** Backtest completes without exceptions; metrics within bounds (e.g., non‑negative total PnL in sample period; max drawdown below threshold); no runtime errors.

Record the current **Definition of Done (DoD)** in your iteration note before the first run.

---

## 3) Core Loop (Run → Analyze → Fix → Verify)

1) **Prepare**
   - Ensure a clean local environment and consistent state (fresh DB/test data snapshot, caches cleared where applicable).
   - Load the **DoD**, the target test subset, and the current iteration limit/status.

2) **Execute**
   - Run the designated tests or simulation:
     - Web/backend: targeted unit/integration/API checks.
     - Trading: a focused backtest slice (representative but time‑bounded).

3) **Collect Signals**
   - Capture only what you need:
     - Fail/passin counts, failing test names.
     - Error types, concise stack trace heads.
     - For trading: termination reason, basic summary stats (PnL, DD, runtime).
   - Trim logs to the minimum that explains the failure.

4) **Classify the Failure**
   - **Syntax/Import/Setup:** installation, pathing, module resolution.
   - **Runtime/Crash:** nulls, key errors, type errors, boundary/edge cases.
   - **Logic/Expectation:** wrong outputs vs assertions or business rules.
   - **Flaky/Nondeterministic:** intermittent; timing‑dependent; race conditions.
   - **Performance/Regression:** timeouts; excessive memory; metrics degrade.

5) **Diagnose**
   - Form a **single, testable hypothesis** for the primary failure.
   - If info is insufficient, **increase observability** minimally (next section) and rerun *before* changing behavior.

6) **Fix (Minimal & Targeted)**
   - Apply the smallest safe change that would make the failing case pass.
   - Avoid wide refactors; do not touch unrelated code.

7) **Verify**
   - Re‑run the **same** checks that exposed the failure.
   - If green: run the **nearest neighbors** (small, relevant set) to guard against local regressions.

8) **Decide**
   - If DoD met: **Stop** and summarize final state.
   - If still failing: **Loop** (go back to Execute) unless iteration limits reached.
   - If stuck/repeating: **Escalate** (see Stop Rules).

---

## 4) Observability (Only When Needed)
Increase visibility sparingly to avoid context bloat:

- Add **focused logging** at the failure site (inputs, decision outcomes, boundary values).
- Add **assertions/guards** to surface invariant violations early.
- Emit **succinct summaries** (e.g., “bad rows: count + identifiers” rather than full dumps).
- For web: log request/response shapes and status codes for the failing path.
- For trading: log first/last timestamps, instrument count, number of trades, exception summaries.

Remove or downgrade verbose logs once the issue is understood.

---

## 5) Handling Flaky Tests
- **Confirm flakiness**: repeat the failing test in isolation multiple times.
- **Stabilize first**: eliminate nondeterminism (fixed seeds, time controls, isolated temp data).
- **Quarantine temporarily**: if unrelated to current goal, park the flaky test with a TODO, but leave a clear note to revisit.
- **Verify fix**: require multiple consecutive passes before declaring success.

---

## 6) Test Selection Strategy (to move fast)
- **Fail‑first ordering**: re‑run the smallest set that reproduces the failure.
- **Cone‑of‑impact**: after a fix, run tests closest to the changed code or behavior.
- **Smoke then expand**: when green locally, expand to the small “neighbors” set; only run wide suites when closing the loop.

---

## 7) Failure → Fix Patterns (No Code)

- **Syntax/Import/Setup**
  - Hypothesis examples: missing dependency; wrong path; wrong interpreter env.
  - Action: adjust environment or references locally; re‑run minimal repro.

- **Runtime/Crash**
  - Hypothesis examples: null/None; division by zero; off‑by‑one; mis‑typed data.
  - Action: add precondition checks; handle edge cases; guard conversions.

- **Logic/Expectation**
  - Hypothesis examples: incorrect branching; faulty aggregation; stale assumption.
  - Action: refine decision criteria; align with test oracle/business rule.

- **Performance/Timeout**
  - Hypothesis examples: N^2 hot path; unnecessary I/O; unbounded loop.
  - Action: constrain work set; memoize/cache; batch operations; early exit.

- **Trading‑specific**
  - Hypothesis examples: invalid data slice; look‑ahead bias; misaligned timezones.
  - Action: validate data windows; ensure no future leakage; confirm calendar/session logic; rerun focused backtest.

---

## 8) Web / Backend Notes (Local‑only)
- **State reset** per run (db, caches, temp files).
- **API checks**: status codes, response schema, idempotency for critical endpoints.
- **Error surfaces**: prefer structured error payloads with stable keys (you can parse without printing full bodies).
- **Security**: never include secrets in logs; scrub PII.

---

## 9) Trading Engine Notes (QuantConnect / Nautilus)
- **Never live**: only backtest/paper/simulate in a local environment.
- **Representative slice**: choose dates/instruments that expose the bug quickly.
- **Metrics to watch**: runtime exceptions; aborted runs; basic PnL; max drawdown; number of trades; fill anomalies.
- **Bias guards**: no look‑ahead; confirm correct market hours; verify data alignment.

---

## 10) Context & Token Economy
- Maintain a **single running summary** per iteration:
  - **Goal/DoD**
  - **Minimal failure excerpt** (1–3 lines)
  - **Root‑cause hypothesis** (≤2 lines)
  - **Planned change** (≤2 lines)
  - **Outcome** (pass/fail + 1 metric)
  - **Next step or Done**
- **Do not** paste entire logs or full stack traces. Keep only the head/tail that proves the point.
- Collapse historical iterations into a short **“Lessons learned”** block when closing.

---

## 11) Stop Rules & Escalation
- **Max iterations**: stop after N attempts (suggest 3–5) without measurable progress.
- **Loop detection**: if two consecutive iterations fail the same way, require a different hypothesis or escalate.
- **Escalation**: request human guidance or switch perspective (e.g., reframe the hypothesis; expand observability; reevaluate DoD; consider a different data slice).

---

## 12) Close‑Out Checklist (when DoD is met)
- Re‑run the immediate neighbors set; spot‑check a small wider suite.
- Remove or downgrade any temporary logs.
- Record a concise **Final Summary** (what failed, why, the minimal fix, how verified).
- Create a **local restore point** (e.g., commit or snapshot) to preserve the working state.

---

## 13) Iteration Record Template (copy per loop)

- **Iteration:** #
- **Goal / DoD:** …
- **Run Target:** (tests/backtest scope)
- **Result:** pass | fail
- **Key Failure Excerpt (if any):** (≤3 lines)
- **Classification:** syntax | runtime | logic | flaky | perf | trading
- **Root‑Cause Hypothesis:** …
- **Planned Minimal Change:** …
- **Verification Outcome:** …
- **Next Step:** loop | expand | done
- **Notes:** (tiny bullets only)

---

## 14) Quick‑Start Protocol (TL;DR)

1. Set **DoD** and choose the **smallest repro** scope.  
2. **Run**; capture minimal failure signals.  
3. **Classify**; if unclear, add just‑enough **observability**.  
4. Form a **single hypothesis**; apply a **minimal fix**.  
5. **Verify** on the same scope; if green, check neighbors.  
6. **Repeat** until DoD is met or **Stop Rules** trigger.  
7. **Close out** with final summary and cleanups.

---

**You are done when the DoD is satisfied and the neighbors pass.  
Keep each loop tight, evidence‑driven, and minimally verbose.**
