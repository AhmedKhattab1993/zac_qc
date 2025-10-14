# ZacQC.data.data_manager
**Path:** `ZacQC/data/data_manager.py`  
**Purpose:** Owns consolidators, VWAP tracking, and daily aggregates for each symbol.  
**Public API:** `DataManager`

## Quick Start
```python
from ZacQC.data.data_manager import DataManager

data_manager = DataManager(algorithm=wrapped_algo, symbol_manager=symbol_manager)
data_manager.InitializeDataStorage()
```

## Public API
### Classes
- `DataManager(algorithm, symbol_manager=None)` — Handles intraday/daily data windows and exposes helper metrics.  
  **Init params:** `algorithm`, optional `symbol_manager`.  
  **Key methods:** `OnData(data)`, `UpdateVWAP(bar)`, `ResetDaily()`, `GetVol7DMA()`.  
  **Raises:** Errors from Lean history or consolidator setup.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Requires Lean consolidator infrastructure and interacts with `Strategy` for trailing order logging.  
- **Invariants:** `hasNewBar` flag ensures downstream processing runs only once per 15-second bar.  
- **Performance considerations:** Removes stale 15-second bars daily to limit memory usage.

## Examples
```python
if data_manager.OnData(slice):
    metrics = metrics_calculator.CalculateAllMetrics(slice)
```

## Known Limitations / TODOs
- VWAP calculation currently skips pre/post-market data; extend if extended hours are required.

## See Also
- [Parent package](../modules/ZacQC.data.md)
- [Related module](../modules/ZacQC.data.metrics_calculator.md)

Last updated: 2025-10-14
