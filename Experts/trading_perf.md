# Python Optimization Playbook for a Trading Coding Agent
*Audience: an advanced coding agent optimizing Python for backtesting and live trading.*  
*Scope: runtime speed, memory efficiency, and maintainability. No code samples—principles and actionable checklists only.*

---

## 0) Prime Directives
- **Correctness first.** Never ship an optimization that changes outcomes. Maintain a known-good baseline and compare outputs after every change.
- **Profile before you optimize.** Identify the top bottlenecks; optimize only what matters.
- **Optimize the hot path, not everything.** Keep non‑critical code clean and simple.
- **Measure end‑to‑end.** Your target metrics are *bars/sec (backtests)*, *tick→decision latency (live)*, *peak RSS*, and *GC stall time*.
- **Stop early.** When SLOs are met, halt further micro‑tuning.

---

## 1) 30‑Second Optimization Triage
1. Confirm baseline metrics (bars/sec, latency, peak memory).  
2. Profile to find the top 1–3 offenders.  
3. Pick the smallest change with the largest impact.  
4. Re‑measure. If gains plateau or correctness changes, revert.

**Do not**: refactor broadly without a profile; optimize cold paths; add complexity that the maintainer won’t understand.

---

## 2) Profiling Protocol (No Code Assumed)
- **Macro profiling:** measure wall‑clock for full runs (backtests over representative periods). Track *bars/sec* and *wall time*.
- **Micro profiling:** time specific stages—data load, indicator calc, signal gen, order routing, logging, persistence.
- **Sampling profiler:** identify functions with the highest exclusive time.
- **Line‑level profiler:** confirm the exact hot lines in the hot functions.
- **Memory profiler:** capture peak RSS and allocations around load, transform, and rolling calcs.
- **I/O tracing:** measure read/write throughput, open file handle counts, and cache hit rates.
- **Artifacts:** store a before/after profile snapshot with each optimization PR for regression detection.

---

## 3) Hot Path Priorities (Trading‑Specific)
**Backtesting core loop**
- Prefer vectorized transforms and batch operations over per‑row work.
- Collapse multiple passes over data into a single pass when safe.
- Precompute invariants (e.g., static calendars, session masks, map lookups).
- Hoist pure computations out of loops; cache repeated intermediate results.
- Use rolling windows *incrementally* (update in O(1) per step) rather than recomputing full windows.

**Live trading decision/execute path**
- Keep the hot path minimal: parse → update state → decide → enqueue order.
- Ban blocking operations: network calls, disk I/O, heavy logging, large allocations.
- Pre‑allocate reusable buffers/objects; avoid per‑tick allocations that trigger GC.
- Keep clocks monotonic and stable; avoid expensive time conversions on the hot path.

---

## 4) Data & Memory Strategy
- **Columnar over row‑oriented.** Use column‑wise transforms; avoid per‑row iteration.
- **Load only what you use.** Select needed columns and date ranges. Partition by symbol and by time (e.g., month shards) to minimize load.
- **Right‑size dtypes.** Downcast numerics to the smallest safe types; use categorical for low‑cardinality text (symbols, venues).
- **Avoid copies.** Prefer in‑place transforms and views; beware of hidden copies in chained operations.
- **Chunking & streaming.** Process long histories in bounded chunks; maintain rolling state across chunk boundaries.
- **Memory maps / zero‑copy.** Use memory‑mapped data or columnar buffers for large read‑mostly datasets.
- **Lifecycle hygiene.** Drop references as soon as data is no longer needed; force cleanup between phases of long backtests.

**Budgeting rubric**
- Set explicit per‑process RAM budgets (e.g., 60% of container limit).
- Trigger chunked processing once an input exceeds N× available RAM.
- Alert if peak RSS exceeds budget or if GC pauses surpass threshold T.

---

## 5) Computation Strategy (Speed Without Obscurity)
- **Vectorize first.** Replace Python‑level loops with vector/array ops whenever feasible.
- **Batch operations.** Aggregate indicator and signal steps to reduce passes over data.
- **Stable numerics.** Prefer operations that minimize cancellation and precision loss; track and bound numerical error across optimizations.
- **Algorithmic wins > micro‑tweaks.** Changing complexity class (e.g., hashing lookups vs nested scans) beats shaving microseconds.
- **Cache consciously.** Memoize expensive pure functions only when hit rate is high and memory budget allows; time‑box cache TTLs.

---

## 6) Native Acceleration Decision Tree
1. **Can it be vectorized cleanly?** → Do that.
2. **Tight numeric loop left?** → Apply a JIT (compile the function) to the hot function only.
3. **Still too slow or heavy data marshalling?** → Move the kernel to a native extension and keep Python orchestration.
4. **Ultra‑low latency required (< sub‑millisecond end‑to‑end)?** → Keep Python for strategy logic; delegate execution micro‑path to a specialized native service.
5. **Always** keep the Python API ergonomic; hide native details behind stable interfaces.

*Guardrails*
- Only JIT/compile functions proven hot by profile.
- Verify identical outputs vs baseline across randomized seeds and edge cases.
- Document assumptions, valid ranges, and precision trade‑offs.

---

## 7) Concurrency & Parallelism (Choose by Workload)
- **CPU‑bound fan‑out** (e.g., parameter sweeps, per‑symbol sims): use multi‑process parallelism with coarse tasks to amortize IPC overhead. Pin workers to cores if possible.
- **I/O‑bound** (market data, logging, network): overlap using async or threads; keep CPU work off those threads.
- **Pipelines**: decouple ingestion → transform → decide → persist with bounded queues; apply backpressure when downstream slows.
- **State isolation**: avoid shared mutable state; prefer message passing. If sharing is required, use read‑only memory maps or copy‑on‑write data.
- **Granularity rule**: task size should be ≫ scheduling/IPC overhead; merge tiny tasks.

*Latency hygiene (live)*
- Warm caches and JITs before market open.
- Smooth CPU frequency scaling; avoid noisy neighbors on shared hosts.
- Keep GC pressure low: reuse buffers, avoid temporary churn, batch allocations off the hot path.

---

## 8) I/O & Storage Efficiency
- **Partitioning**: by symbol and by time window to constrain scan ranges.
- **Column pruning**: read only required fields (price, volume, etc.).
- **Compression vs CPU**: choose formats and codecs that fit your CPU budget and access patterns.
- **Indexing**: maintain time‑ordered storage; avoid random seeks in large historical scans.
- **Warmable caches**: prime working sets ahead of backtests; invalidate predictably (by partition).

*Throughput checklist*
- Track sustained read/write MB/s and open handles.
- Batch small writes; flush on safe boundaries (bar close, batch end).
- Avoid sync fs calls on hot paths; move fs sync to maintenance threads.

---

## 9) Domain‑Specific Optimizations (Trading)
- **Rolling features**: update incrementally (O(1) per step); don’t recompute full windows.
- **Calendar logic**: compute session masks once; reuse across strategies.
- **Price/size normalization**: convert to canonical units once at load; avoid repeated conversions.
- **Sparse signals**: operate only on candidate indices (where preconditions hold) rather than scanning all bars.
- **Order simulation**: short‑circuit early when fills are impossible (e.g., price bands not crossed).

---

## 10) Maintainability Without Compromise
- **Clarity first** in non‑hot code; isolate “clever” optimizations in small, well‑named modules.
- **Invariant docs**: specify pre/postconditions, valid ranges, and tolerance of numeric drift.
- **Tests as contracts**: golden files for backtests, property tests for arithmetic, metamorphic tests for invariants (e.g., scaling prices doesn’t change signal direction).
- **Shadow runs**: for major changes, run baseline and optimized versions in parallel and diff outputs.
- **Observability**: emit timings, allocations, and cache/queue stats; set alerts on SLO breaches.

---

## 11) SLOs & Acceptance Criteria (Define Before Tuning)
- **Backtesting**: target bars/sec ≥ X for dataset D; total runtime ≤ H hours; peak RAM ≤ R GB.
- **Live**: tick→decision ≤ L ms p99; order enqueue jitter ≤ J ms; zero dropped ticks; GC pauses ≤ G ms p99.
- **I/O**: sustained read ≥ T MB/s on warm cache; cold start ≤ C seconds.
- **Stability**: no divergence from baseline outputs beyond tolerance ε on regression suite.

---

## 12) Optimization Workflow (Closed‑Loop)
1. **Baseline**: record metrics, capture profiles, and lock a correctness snapshot.
2. **Hypothesis**: identify a change and expected impact.
3. **Apply**: smallest viable change; keep scope tight.
4. **Measure**: repeat the same benchmarks; compare to baseline.
5. **Validate**: full correctness checks; investigate any drift.
6. **Decide**: keep if impact ≥ target and complexity ≤ budget; otherwise revert.
7. **Document**: summarize change, metrics deltas, residual risks, and roll‑forward plan.

---

## 13) Tuning Checklists

**A. Quick Speed Wins**
- Replace row-wise work with vector/array ops.
- Batch transforms to reduce passes.
- Hoist invariant work out of loops.
- Cache high‑hit pure computations.
- Pre‑allocate and reuse buffers in hot paths.

**B. Quick Memory Wins**
- Downcast numerics; use categorical for IDs/labels.
- Read only needed columns/ranges; process in chunks.
- Avoid hidden copies; prefer in‑place transforms.
- Free large intermediates early; reset between phases.

**C. Live Latency Hygiene**
- No blocking I/O or heavy logging on the execute path.
- Warm caches/JITs before open; prebuild objects.
- Defer non‑critical compute to background workers.
- Monitor p99 tail and GC pauses; alert on regressions.

**D. Safety Nets**
- Golden backtest outputs; diff after each change.
- Hard SLO gates in CI; fail builds on SLO regression.
- Feature flags to toggle optimized vs baseline path.

---

## 14) Symptom → Action Table

| Symptom | Likely Cause | Actions |
|---|---|---|
| Bars/sec flat despite CPU headroom | I/O bound | Partition reads, column prune, batch I/O, warm caches |
| High p99 decision latency | Allocations/GC or blocking I/O | Reuse buffers, move I/O off hot path, reduce logging |
| Memory bloat over run | Hidden copies/leaks | Audit transforms for copies, drop refs, chunk processing |
| Single core pegged | Python loop on hot path | Vectorize or JIT the kernel; hoist invariants |
| Parallel speedup poor | Granularity too fine / IPC overhead | Coarsen tasks, reduce serialization, pin cores |
| Output drift after tuning | Numeric or logic changes | Tighten tests, compare per‑step state, revert if needed |

---

## 15) Exit Criteria
- SLOs met with headroom.
- No correctness drift beyond ε on the full regression suite.
- Complexity increase is justified and documented.
- Observability in place to catch regressions in the wild.

---

### Final Reminder
Optimize with purpose. Keep the hot path lean, data movement minimal, and correctness provable. When in doubt, choose clarity first—*then* make it fast where the profile says it matters.
