# Documentation Index

ZacQC is a reference implementation of the Zac trading system adapted for QuantConnect Lean. The documentation below provides per-module reference material and design notes.

## Getting Started
- Install Lean CLI and dependencies as per QuantConnect documentation.
- Clone this repository and run inside the Lean environment.
- Launch `ZacQC.main.ZacReferenceAlgorithm` through Lean CLI or the QuantConnect IDE.

## Module Index
| Module | Summary |
|---|---|
| [`ZacQC`](modules/ZacQC.md) | Root package linking core, trading, data, management, and config subsystems |
| [`ZacQC.main`](modules/ZacQC.main.md) | Reference QCAlgorithm orchestrating trading |
| [`ZacQC.main_minimal`](modules/ZacQC.main_minimal.md) | Smoke-test QCAlgorithm |
| [`ZacQC.config`](modules/ZacQC.config.md) | Configuration package |
| [`ZacQC.config.parameters`](modules/ZacQC.config.parameters.md) | Canonical trading parameters |
| [`ZacQC.core`](modules/ZacQC.core.md) | Core abstractions and shared logic |
| [`ZacQC.core.strategy`](modules/ZacQC.core.strategy.md) | Strategy state machine |
| [`ZacQC.core.symbol_manager`](modules/ZacQC.core.symbol_manager.md) | Per-symbol orchestration |
| [`ZacQC.core.utils`](modules/ZacQC.core.utils.md) | Utility helpers |
| [`ZacQC.core.custom_fill_model`](modules/ZacQC.core.custom_fill_model.md) | Spread-less fill model |
| [`ZacQC.trading`](modules/ZacQC.trading.md) | Trading subsystem umbrella |
| [`ZacQC.trading.order_manager`](modules/ZacQC.trading.order_manager.md) | Entry/exit order orchestration |
| [`ZacQC.trading.trail_order_manager`](modules/ZacQC.trading.trail_order_manager.md) | IB-style trail orders |
| [`ZacQC.trading.conditions_checker`](modules/ZacQC.trading.conditions_checker.md) | Entry condition logic |
| [`ZacQC.management`](modules/ZacQC.management.md) | Risk and rally management umbrella |
| [`ZacQC.management.risk_manager`](modules/ZacQC.management.risk_manager.md) | Daily P&L enforcement |
| [`ZacQC.management.rally_detector`](modules/ZacQC.management.rally_detector.md) | Momentum gate checks |
| [`ZacQC.data`](modules/ZacQC.data.md) | Data ingestion umbrella |
| [`ZacQC.data.data_manager`](modules/ZacQC.data.data_manager.md) | Consolidators & VWAP tracking |
| [`ZacQC.data.metrics_calculator`](modules/ZacQC.data.metrics_calculator.md) | Derived metric calculations |
| [`server`](modules/server.md) | Flask services and trading calendar utilities |
| [`server.backtest_server`](modules/server.backtest_server.md) | Backtest orchestration API |
| [`server.trading_calendar`](modules/server.trading_calendar.md) | Trading day calculations |

## End-to-End Testing
- The backtest server now honours the following environment overrides (all optional, defaulting to the production paths):
  - `BACKTEST_DATA_ROOT`: custom Lean data directory. Tests set this to a temporary folder so downloads do not touch the shared `data/` tree.
  - `BACKTEST_CONFIG_PATH`: alternative `parameters.py` module loaded by both the Flask server and the Lean algorithm. When set, the algorithm mirrors the override via the same environment variable.
  - `BACKTEST_SYMBOLS`: comma-separated symbol list used during data availability checks.
- Use the support CLI to scaffold Playwright scenarios, e.g. `python -m tests.e2e.support.cli missing-data --workspace /tmp/zac-e2e` or `... cached-data ...`.
- Pytest smoke for the harness: `pytest -q tests/e2e/support/test_backtest_harness.py`.
- Playwright specs (Chromium, single worker):
  - Missing data path: `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@missing-data" --project=chromium --workers=1 --retries=0`
  - Cached data path: `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@cached-data" --project=chromium --workers=1 --retries=0`
- Test artifacts, server logs, and Lean stdout snapshots are stored under `tasks/playwright-backtest-data-availability-*/runs/`.

## Contributing
- Ensure docstrings follow NumPy style for public symbols.
- Update per-module documentation and refresh the index when adding new modules.
- Run backtests after modifying trading logic to confirm behaviour.

Last updated: 2025-10-16
