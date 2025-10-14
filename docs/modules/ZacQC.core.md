# ZacQC.core
**Path:** `ZacQC/core`  
**Purpose:** Core abstractions managing strategies, symbol orchestration, utilities, and fill modelling.  
**Public API:** `strategy`, `symbol_manager`, `utils`, `custom_fill_model`

## Quick Start
```python
from ZacQC.core.strategy import Strategy
from ZacQC.core.symbol_manager import SymbolManager

# Typically instantiated by ZacReferenceAlgorithm; manual setup:
strategy = Strategy(algorithm=qc_algo, account_id="paper", symbol_name="AAPL")
strategy.Initialize()
```

## Public API
### Classes
- `Strategy(algorithm, account_id, symbol_name)` — Reference trading strategy with sequential condition tracking.  
  **Init params:** `algorithm`, `account_id`, `symbol_name`.  
  **Key methods:** `Initialize()`, `ProcessBasicStrategy(...)`, `trade_time_action(...)`.  
  **Raises:** Propagates exceptions from underlying Lean calls.
- `SymbolManager(algorithm, symbol_name, symbol)` — Coordinates data, metrics, and order management per symbol.  
  **Init params:** `algorithm`, `symbol_name`, `symbol`.  
  **Key methods:** `Initialize()`, `OnData(data)`, `CustomEndOfDay()`.  
  **Raises:** Surfaces initialization errors for data feeds.
- `TradingUtils(algorithm)` — Helper utilities for time windows and formatting.  
  **Init params:** `algorithm`.  
  **Key methods:** `IsMarketHours(dt)`, `ValidateOrder(symbol, quantity, price)`.  
  **Raises:** None.
- `PreciseFillModel(algorithm=None)` — Custom fill model aligning fills with reference behaviour.  
  **Init params:** optional `algorithm` for logging.  
  **Key methods:** `MarketFill(...)`, `StopMarketFill(...)`.  
  **Raises:** None.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Relies on QuantConnect Lean APIs (`AlgorithmImports`), trading subsystem (`trading.order_manager`, `trading.conditions_checker`), and data metrics packages.  
- **Invariants:** `SymbolManager` maintains 1:1 mapping between `symbol` and subordinate managers; strategies must be initialised before processing data.  
- **Performance considerations:** Trailing order updates and timing checks are throttled to minimise per-tick overhead.

## Examples
```python
from ZacQC.core.custom_fill_model import PreciseFillModel

equity = qc_algo.AddEquity("NVDA", Resolution.Second)
equity.SetFillModel(PreciseFillModel(qc_algo))
```

## Known Limitations / TODOs
- `Strategy` contains legacy compatibility helpers that could be pruned as the reference system stabilises.
- `SymbolManager` expects `AlgorithmWrapper` delegation; direct use requires manual wiring.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.trading.md)

Last updated: 2025-10-14
