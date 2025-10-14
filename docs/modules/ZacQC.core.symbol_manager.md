# ZacQC.core.symbol_manager
**Path:** `ZacQC/core/symbol_manager.py`  
**Purpose:** Encapsulates per-symbol coordination across data ingestion, metrics, conditions, and orders.  
**Public API:** `SymbolManager`

## Quick Start
```python
from ZacQC.core.symbol_manager import SymbolManager

symbol_manager = SymbolManager(algorithm=qc_algo, symbol_name="AAPL", symbol=qc_algo.symbol)
symbol_manager.Initialize()
```

## Public API
### Classes
- `SymbolManager(algorithm, symbol_name, symbol)` — Orchestrates data pipelines and trading workflow for a single instrument.  
  **Init params:** `algorithm`, `symbol_name`, `symbol`.  
  **Key methods:** `Initialize()`, `OnData(data)`, `CustomEndOfDay()`, `ValidateTimingConstraints(condition)`.  
  **Raises:** Re-raises exceptions from initialization or downstream risk checks.
- `AlgorithmWrapper(algorithm, symbol)` — Internal proxy that exposes symbol-scoped context to components.  
  **Init params:** `algorithm`, `symbol`.  
  **Key methods:** `__getattr__(name)`; returns attributes from wrapped algorithm.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Instantiates `data.DataManager`, `data.MetricsCalculator`, `trading.ConditionsChecker`, `trading.OrderManager`.  
- **Invariants:** Maintains synchronized `strategies`, `order_manager`, and `data_manager` references; expects Lean scheduling to invoke `OnData`.  
- **Performance considerations:** Multiple guard clauses prevent redundant work; heavy logging can be toggled via `algorithm.enable_logging`.

## Examples
```python
symbol_manager.OnData(current_slice)
symbol_manager.CustomEndOfDay()
```

## Known Limitations / TODOs
- Still contains deprecated range multiple helpers slated for removal.

## See Also
- [Parent package](../modules/ZacQC.core.md)
- [Related module](../modules/ZacQC.trading.order_manager.md)

Last updated: 2025-10-14
