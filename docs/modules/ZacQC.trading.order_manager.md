# ZacQC.trading.order_manager
**Path:** `ZacQC/trading/order_manager.py`  
**Purpose:** Implements entry, exit, and risk management order orchestration for the reference strategy.  
**Public API:** `OrderManager`

## Quick Start
```python
from ZacQC.trading.order_manager import OrderManager

order_manager = OrderManager(algorithm=wrapped_algo)
order_manager.ExecuteLongEntry(strategy, "cond1", current_price, metrics)
```

## Public API
### Classes
- `OrderManager(algorithm)` — Coordinates trailing entries, SL/TP placement, and risk gating.  
  **Init params:** `algorithm`.  
  **Key methods:** `ExecuteLongEntry(...)`, `ExecuteShortEntry(...)`, `OnOrderEvent(order_event, strategies)`, `CloseAllPositions()`.  
  **Raises:** Propagates QuantConnect transaction errors.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Requires access to `management.risk_manager.RiskManager`, `data.DataManager`, and `Strategy` state.  
- **Invariants:** Maintains bidirectional mappings between entry orders and downstream SL/TP orders to avoid duplicates.  
- **Performance considerations:** Hard constraint flags (`orders_sent_this_cycle`) prevent high-frequency order spam.

## Examples
```python
if order_manager.ExecuteLongEntry(strategy, "cond2", price, metrics):
    qc_algo.Log("Trailing long order submitted.")
```

## Known Limitations / TODOs
- Some helper methods still assume symbol-scoped algorithm wrapper; avoid direct usage without `SymbolManager`.

## See Also
- [Parent package](../modules/ZacQC.trading.md)
- [Related module](../modules/ZacQC.trading.trail_order_manager.md)

Last updated: 2025-10-14
