# ZacQC.core.custom_fill_model
**Path:** `ZacQC/core/custom_fill_model.py`  
**Purpose:** Custom Lean fill model that removes bid/ask spread to replicate reference fills.  
**Public API:** `PreciseFillModel`

## Quick Start
```python
from ZacQC.core.custom_fill_model import PreciseFillModel

equity = qc_algo.AddEquity("AAPL", Resolution.Second)
equity.SetFillModel(PreciseFillModel(qc_algo))
```

## Public API
### Classes
- `PreciseFillModel(algorithm=None)` — Lean `FillModel` that fills at exact trade prices.  
  **Init params:** optional `algorithm` for logging.  
  **Key methods:** `MarketFill(asset, order)`, `StopMarketFill(asset, order)`, `LimitFill(asset, order)`.  
  **Raises:** None.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Inherits from `QuantConnect.Orders.Fills.FillModel` and consumes `TradeBar` cache data.  
- **Invariants:** Treats all fills as spread-less; suitable only for backtests requiring precise P&L comparisons.  
- **Performance considerations:** Light-weight operations; minimal overhead beyond default model.

## Examples
```python
from ZacQC.core.custom_fill_model import PreciseFillModel

equity = qc_algo.AddEquity("MSFT", Resolution.Minute)
equity.SetFillModel(PreciseFillModel())
```

## Known Limitations / TODOs
- Does not simulate slippage or partial fills; not recommended for live trading.

## See Also
- [Parent package](../modules/ZacQC.core.md)
- [Related module](../modules/ZacQC.main.md)

Last updated: 2025-10-14
