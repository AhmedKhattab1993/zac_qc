# ZacQC.core.strategy
**Path:** `ZacQC/core/strategy.py`  
**Purpose:** Implements the ZacQC reference trading strategy state machine and trade management actions.  
**Public API:** `Strategy`

## Quick Start
```python
from ZacQC.core.strategy import Strategy

strategy = Strategy(algorithm=qc_algo, account_id="sim", symbol_name="AAPL")
strategy.Initialize()
```

## Public API
### Classes
- `Strategy(algorithm, account_id, symbol_name)` — Handles condition sequencing, timing gates, and trade lifecycle actions.  
  **Init params:** `algorithm`, `account_id`, `symbol_name`.  
  **Key methods:** `Initialize()`, `ProcessBasicStrategy(strategy, data, metrics)`, `trade_time_action(last_price)`.  
  **Raises:** Propagates exceptions from order management routines.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Coordinates with `trading.order_manager`, `trading.conditions_checker`, and Lean portfolio APIs.  
- **Invariants:** Condition state is mirrored across legacy (`cond1`-`cond5`) and reference (`c1`-`c5`) keys. Timing checks rely on `algorithm.Time`.  
- **Performance considerations:** Trailing order updates are throttled to 10-second intervals; avoid heavy logging unless debugging.

## Examples
```python
strategy.UpdateConditionState("cond1", True)
if strategy.GetConditionState("cond1"):
    strategy.AddPendingOrder("cond1", {"ticket": ticket})
```

## Known Limitations / TODOs
- Still carries deprecated range multiple helpers kept for parity with the legacy system.

## See Also
- [Parent package](../modules/ZacQC.core.md)
- [Related module](../modules/ZacQC.trading.order_manager.md)

Last updated: 2025-10-14
