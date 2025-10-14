# ZacQC.core.utils
**Path:** `ZacQC/core/utils.py`  
**Purpose:** Utility helpers for market session checks, formatting, and simple validations shared across modules.  
**Public API:** `TradingUtils`

## Quick Start
```python
from ZacQC.core.utils import TradingUtils

utils = TradingUtils(algorithm=qc_algo)
if utils.IsMarketHours():
    price = utils.GetCurrentPrice(qc_algo.symbol)
```

## Public API
### Classes
- `TradingUtils(algorithm)` — Collection of convenience helpers bound to a QCAlgorithm.  
  **Init params:** `algorithm`.  
  **Key methods:** `IsMarketHours(dt=None)`, `ValidateOrder(symbol, quantity, price)`, `CalculatePercentageChange(old_value, new_value)`.  
  **Raises:** None.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Uses Lean-provided time and security access via the algorithm.  
- **Invariants:** Methods assume `self.algorithm` exposes `Time`, `Securities`, and `IsMarketOpen`.  
- **Performance considerations:** Pure Python helpers; negligible footprint.

## Examples
```python
from ZacQC.core.utils import TradingUtils

utils = TradingUtils(qc_algo)
pct = utils.CalculatePercentageChange(100, 105)
qc_algo.Log(f"Change: {utils.FormatPercentage(pct)}")
```

## Known Limitations / TODOs
- Formatting helpers treat inputs as already scaled percentages; callers must supply the appropriate units.

## See Also
- [Parent package](../modules/ZacQC.core.md)
- [Related module](../modules/ZacQC.main.md)

Last updated: 2025-10-14
