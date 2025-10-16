## 2025-10-16 — [S-2] Native downloader integration

- Enabled feature-flagged native Polygon downloader in `server/backtest_server.py`, added structured logging, and wired CLI fallback guarded by `POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK`.
- Introduced downloader factory + data root injection on `BacktestManager` for easier testing; recorded per-resolution metrics and cache hit telemetry.
- Added `tests/integration/test_backtest_manager_downloader.py` covering success, cache-only, and fallback scenarios using stubs.
- Added `tests/integration/test_backtest_manager_downloader_live.py` guarded by `RUN_POLYGON_LIVE_TESTS` to exercise the native path end-to-end against Polygon.
- Authored `Experts/polygon_incremental_downloader.md` capturing feature flags, fallback guidance, telemetry fields, and validation steps for rollout.
- Updated Polygon client request formatting to send UTC calendar-day tokens, enabling Polygon aggregate endpoints to accept native downloader queries.
- Live validation: `RUN_POLYGON_LIVE_TESTS=1 pytest -q tests/integration/test_polygon_downloader_live.py` and `RUN_POLYGON_LIVE_TESTS=1 pytest -q tests/integration/test_backtest_manager_downloader_live.py` (pass).
- Added `benchmarks/polygon_downloader_benchmark.py` plus `tests/benchmarks/test_downloader_benchmarks_live.py`; benchmark output stored under `tasks/.../benchmarks/benchmark_*.json`.
- Current benchmark (AAPL minute, 1 day) shows native downloader completing in ~0.68s with 1 HTTP request; CLI baseline failed in this environment due to missing Lean metadata, error captured in the benchmark report.
- Documentation updated (`Experts/polygon_incremental_downloader.md`) with benchmarking instructions and fallback guidance.
- Regression runs: `pytest -q tests/unit`, `pytest -q tests/integration`.
