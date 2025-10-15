# LEAN‑Tailored Python Optimization Playbook (for a Coding Agent)

*Audience*: Advanced coding agent optimizing **Python** algorithms on **QuantConnect LEAN** (local + CLI).  
*Scope*: runtime speed, memory efficiency, realistic modeling, and maintainability — **no code snippets**, only principles and checklists.  
*Goal*: Maximize **bars/sec** in backtests, minimize **tick→decision** latency in live, and keep results **correct** and **reproducible**.

---

## 0) Prime Directives (LEAN context)
- **Correctness first.** Never accept speed that changes fills or portfolio state. Keep a golden baseline backtest for diffing.
- **Profile → change → re‑measure.** Only optimize the **hot path** surfaced by a profile.
- **Exploit LEAN’s engine.** Prefer built‑in constructs (Slice, Consolidators, Indicators, RollingWindow, UniverseSettings) over ad‑hoc pandas logic.
- **Minimize event volume.** Tune **Resolution**, E/M hours, universe breadth, and consolidation to reduce handler invocations.
- **Document assumptions & reality models.** Fees, slippage, fill, normalization, mapping — state choices explicitly.

---

## 1) Backtest Hot‑Path (OnData & Timeslices)
- **Treat `OnData` as the hot path.** Keep it: *parse → update state → decide → enqueue order* only.
- **Reduce event count:** prefer coarser **Resolution** when possible; disable **ExtendedMarketHours** unless needed; consolidate intraday bars.
- **Use typed data flows vs sprawling pandas.** Operate on **Slice**, `TradeBar`/`QuoteBar`, and indicator states; avoid row‑wise loops.
- **Avoid blocking operations in `OnData`.** No disk, network, heavy logging, or big allocations on the decision path.
- **Schedule non‑critical work.** Use **Scheduled Events** for periodic maintenance/analytics outside data events.

---

## 2) Data Acquisition & Transform Strategy
- **History vs. Rolling:** Use **RollingWindow** (and indicators’ built‑in windows) to maintain state; avoid repeated `History()` calls during runtime. Prime once during warm‑up or security add.
- **Batch history** when needed: request many symbols/time at once and fan out; cache results for reuse within the run.
- **Consolidate early:** build higher‑TF bars with **Time Period/Calendar/Mixed‑Mode Consolidators** to shrink event frequency.
- **Normalize once:** pick **DataNormalizationMode** (e.g., ADJUSTED/RAW/…); don’t mix modes mid‑run.
- **Map once:** set **DataMappingMode** / **ContractDepthOffset** for continuous futures up front; don’t thrash mappings.

---

## 3) Initialization & Warm‑Up
- Keep heavy configuration in **Initialize**: cash, timezone, start/end, brokerage model, universe & **UniverseSettings**.
- **Warm up** indicators/windows with **SetWarmUp** (bars or time). Consider per‑security priming when symbols join.
- **SecurityInitializer**: apply per‑security models (fees/slippage/fill/filters/normalization) and optionally **seed last price** for immediate trading after subscription (useful for futures/options contracts).

---

## 4) Universe Selection (Breadth & Churn Control)
- **Coarse → Fine → `OnSecuritiesChanged`.** Seed new members there (history, indicators, rolling windows, metadata), not in `OnData`.
- **Control churn:** set **MinimumTimeInUniverse** to avoid re‑allocations and warm‑up thrash; disable **FillForward** only if you really need gaps.
- **Resolution discipline:** Universe **Resolution** should match signal needs; finer than necessary explodes event volume.
- **Extended hours:** enable only if strategy requires it (more events ≠ more edge).

---

## 5) Indicators & Rolling Windows
- Prefer **built‑in indicators** and **RollingWindow** for trailing state (O(1) incremental updates).
- If features need multiple TFs, consolidate once and feed indicators from consolidated streams (not multiple `History()` calls).
- Keep **window sizes just large enough**; large windows = memory + cache misses.

---

## 6) Memory & I/O
- **Minimize subscriptions** (symbols × resolutions × data types). Unsubscribe when unneeded.
- **Columnar mindset:** compute per‑series states, not row‑wise dataframes. Avoid large, chained pandas ops in the engine loop.
- **Local data hygiene:** follow LEAN **zip+CSV** format; partition by asset/resolution/date; keep only required datasets present.
- **Object Store/Artifacts:** persist expensive, immutable artifacts between runs (e.g., symbol lists, pre‑computed masks) and load at start — not during `OnData`.

---

## 7) Live‑Trading Latency Hygiene
- Keep the order path minimal; push reporting/analytics to background/scheduled tasks.
- Reuse buffers/objects to limit GC; avoid per‑tick allocations.
- Avoid chatty logging; emit concise signals/metrics only.
- Warm caches/JITs before open; stabilize CPU frequency; avoid noisy neighbors for consistent p99.

---

## 8) Reality Modeling (Speed with Realism)
- **Brokerage/Fees/Slippage/Fill:** set models once (per security via **SecurityInitializer**). Keep them realistic yet not needlessly complex.
- **Normalization/Mapping:** choose modes that match research; changing them mid‑run causes drift and recomputation.
- **Determinism:** prefer stable, deterministic settings for comparable backtests.

---

## 9) Lean CLI Optimization (Local)
- Use **`lean optimize`** for parameter sweeps; constrain **target** and **search ranges** tightly.
- **Concurrency budget:** cap `--max-concurrent-backtests` to avoid thrashing local CPU/RAM/IO.
- **Artifacts discipline:** store each optimization’s config, objective, and results; diff against the golden baseline.
- Prefer **grid/Euler** search only as far as they produce stable optima; watch for overfitting (walk‑forward validation).

---

## 10) Observability & Guardrails
- **Metrics:** bars/sec, tick→decision p99, peak RSS, GC pauses, `History()` time, symbol count, event count.
- **Logs:** use `Log` for durable, rate‑limited messages; keep noise down (log quotas apply in cloud contexts).
- **End‑of‑run hooks:** use **OnEndOfAlgorithm** to export summaries/artifacts.
- **CI gates:** fail builds on SLO regressions; diff key stats vs. baseline run.

---

## 11) Symptom → Action
| Symptom | Likely Cause | Action |
|---|---|---|
| Bars/sec low, CPU idle | Too many events / I/O bound | Coarsen Resolution, disable E/M hours, consolidate, batch I/O, prefetch |
| `OnData` slow | Pandas work / allocations | Move to indicators & windows, reuse buffers, hoist invariants |
| Memory bloat | Too many subscriptions/copies | Trim universe; avoid repeated `History()`, drop refs after warm‑up |
| Slow warm‑up | Per‑symbol ad‑hoc history | Batch history on add; cache and fan‑out; seed via initializer |
| Fill/PNL drift after “optimization” | Model/normalization mismatch | Pin fee/slippage/fill/normalization in initializer; re‑validate |
| Parallel optimize thrashes | Over‑concurrency | Lower `--max-concurrent-backtests`; reduce result payloads |

---

## 12) SLOs (Define per project)
- **Backtest**: ≥ *X* bars/sec on dataset *D*; peak RAM ≤ *R* GB; history prep ≤ *H*% of wall time.
- **Live**: p99 tick→decision ≤ *L* ms; zero dropped ticks; GC pauses ≤ *G* ms p99.
- **I/O**: sustained read ≥ *T* MB/s (warm); cold start ≤ *C* s.

---

## 13) Optimization Loop (Closed‑Loop)
1) **Baseline** (lock config, models, data modes) → record metrics & outputs.  
2) **Hypothesize** (smallest change; expected impact).  
3) **Apply** (isolate hot section; keep code clear).  
4) **Measure** (same bench; collect profiles).  
5) **Validate** (no output drift; spot numeric issues).  
6) **Decide** (keep/revert); **Document** (metrics deltas & risks).

---

### Quick Checklists

**Speed**  
- Consolidate; reduce Resolution; no E/M hours unless needed.  
- Batch `History()`; prefer RollingWindow/indicators.  
- Hoist invariants; reuse buffers; avoid per‑tick pandas.

**Memory**  
- Limit subscriptions; right‑size windows; drop stale refs.  
- Cache immutable artifacts; keep local zip+CSV tidy and minimal.

**Correctness**  
- SecurityInitializer: set fees/slippage/fill/normalization once.  
- OnSecuritiesChanged: seed state; avoid in‑loop history.  
- Golden baseline diffs on every “optimization”.

**CLI Optimize**  
- Narrow ranges; set `--max-concurrent-backtests`.  
- Store configs/results; perform walk‑forward checks.

---

### Final Reminder
Prefer LEAN primitives over ad‑hoc dataframes; minimize event volume; warm‑up and seed correctly; batch heavy I/O; keep the trade path lean; and validate *every* speedup against a deterministic baseline.
