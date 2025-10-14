# ZacQC.trading.trail_order_manager
**Path:** `ZacQC/trading/trail_order_manager.py`  
**Purpose:** Provides IB-style stop-trailing order behaviour for entry orders.  
**Public API:** `TrailOrderManager`

## Quick Start
```python
from ZacQC.trading.trail_order_manager import TrailOrderManager

trail_manager = TrailOrderManager(algorithm=wrapped_algo)
ticket = trail_manager.PlaceStopTrailOrder(symbol, "BUY", 100, 185.0, 1.5, "cond1")
```

## Public API
### Classes
- `TrailOrderManager(algorithm)` — Tracks and updates trailing orders according to IB semantics.  
  **Init params:** `algorithm`.  
  **Key methods:** `PlaceStopTrailOrder(...)`, `UpdateAllTrailOrders()`, `CancelAllTrailOrders(symbol=None)`.  
  **Raises:** Surfaces QuantConnect order update failures.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Uses Lean order tickets and expects `algorithm.data_manager` to expose daily high/low values.  
- **Invariants:** Maintains `active_trail_orders` map keyed by order ID; entries removed automatically when filled or cancelled.  
- **Performance considerations:** Global 15-second throttle ensures updates align with IB behaviour.

## Examples
```python
trail_manager.UpdateAllTrailOrders()
trail_manager.CancelAllTrailOrders(symbol)
```

## Known Limitations / TODOs
- Parameter names follow legacy casing (`param4`, `param5`) and should be harmonised with `TradingParameters`.

## See Also
- [Parent package](../modules/ZacQC.trading.md)
- [Related module](../modules/ZacQC.trading.order_manager.md)

Last updated: 2025-10-14
