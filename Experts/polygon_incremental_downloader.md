# Polygon Incremental Downloader Rollout Guide

This guide explains how to operate the native Polygon incremental downloader that now powers ZacQC backtest data preparation. It covers feature flags, fallback behaviour, telemetry signals, and validation steps.

## Feature Flags & Defaults

- `USE_POLYGON_NATIVE_DOWNLOADER` (default `true`): when enabled, `BacktestManager` uses the native downloader instead of invoking `lean data download`. Leave this on in staging/production.
- `POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK` (default `true`): when enabled, a failure inside the native downloader (e.g., Polygon outage) triggers the legacy Lean CLI flow as a safety net. Set to `0`/`false` to force hard failures for testing.
- Both flags are read from environment variables. No config file changes are required.

## Polygon Credentials

- The downloader reads the Polygon API key from `lean.json['polygon-api-key']`. You may override it via the `POLYGON_API_KEY` environment variable for test runs.
- Confirm the key is present before running live or benchmark suites.

## Logging & Telemetry

- Structured events ship through `backtest_logger` with `phase="data_download"`:
  - `polygon_downloader_start` — symbols, date window, extended window.
  - `polygon_downloader_step` — per-resolution step, symbol count, window.
  - `polygon_downloader_complete` — total duration, HTTP requests, cache hits, bytes written per resolution.
- UI log entries provide human-readable mirrors of the structured events (e.g., `⏱️ [DATA DOWNLOAD] Native step…`). Use these to verify cache hits vs. downloads in support cases.

## Fallback Behaviour

- If the native downloader raises `PolygonAPIError`/`PolygonRateLimitError`, the system:
  1. Emits a failure entry in logs.
  2. Falls back to the Lean CLI when `POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK=1`.
  3. Switches to hard error (no fallback) when the flag is disabled.
- CLI downloads continue to pass `--no-update` so Lean does not self-update during rollback.

## Validation & Smoke Tests

| Scenario | Command | Notes |
| --- | --- | --- |
| Unit/Integration | `pytest -q tests/integration/test_backtest_manager_downloader.py` | Exercises success/cache/fallback paths with stubs. |
| Live Backtest Smoke | `RUN_POLYGON_LIVE_TESTS=1 pytest -q tests/integration/test_backtest_manager_downloader_live.py` | Requires real Polygon key; verifies native downloader writes Lean archives. |
| Polygon Downloader Live | `RUN_POLYGON_LIVE_TESTS=1 pytest -q tests/integration/test_polygon_downloader_live.py` | Useful for lower-level troubleshooting. |

## Operational Runbook

1. Ensure `lean.json` contains a valid `polygon-api-key`.
2. Set `USE_POLYGON_NATIVE_DOWNLOADER=1` (default). Optionally set `POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK=0` during validation to surface native errors directly.
3. Trigger a backtest via the usual API/CLI. Monitor `backtest_logger` for `polygon_downloader_*` entries and confirm:
   - Cache hits appear when data already exists.
   - HTTP request counts stay within expectations.
4. For incidents, gather the structured logs above and check whether the CLI fallback engaged. Toggle the fallback flag to isolate issues.
5. After changes, re-run the integration suite listed above. For release candidates, capture live smoke results and archive them under `tasks/polygon-incremental-data-downloader-*/benchmarks/` if benchmarking.

This document should be updated alongside any further downloader changes, including new feature flags, telemetry fields, or benchmark procedures.

## Benchmarking

- Script: `benchmarks/polygon_downloader_benchmark.py` runs a native-vs-CLI comparison over a short (default 1-day minute) window and writes JSON reports into `tasks/polygon-incremental-data-downloader-20251016T075149Z/benchmarks/`.
- Usage:
  ```bash
  RUN_POLYGON_BENCHMARKS=1 pytest -q tests/benchmarks/test_downloader_benchmarks_live.py
  ```
  or call `run_default_benchmark` directly from a Python shell.
- Requirements:
  - Polygon API key via `POLYGON_API_KEY` or `lean.json`.
  - Lean CLI installed and authenticated. The CLI benchmark step needs Lean's metadata folders (`data/market-hours`, `data/symbol-properties`, `data/equity/usa/map_files`). We copy these automatically into a temp workspace, but full CLI execution may still fail if additional Lean assets are missing. When that happens, the report records the error message and the pytest benchmark skips with the failure reason.
- Output Interpretation:
  - `native.duration_seconds` / `native.http_requests` show actual live performance of the incremental downloader (request count should stay low thanks to caching).
  - `cli.duration_seconds` is only populated when CLI download succeeds. If `cli.error` is present, capture the report for documentation and, if needed, rerun the CLI benchmark from a fully-provisioned Lean workspace.
