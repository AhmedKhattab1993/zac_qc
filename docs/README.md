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

## Contributing
- Ensure docstrings follow NumPy style for public symbols.
- Update per-module documentation and refresh the index when adding new modules.
- Run backtests after modifying trading logic to confirm behaviour.

Last updated: 2025-10-14
