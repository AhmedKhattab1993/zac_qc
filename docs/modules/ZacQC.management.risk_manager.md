# ZacQC.management.risk_manager
**Path:** `ZacQC/management/risk_manager.py`  
**Purpose:** Enforces daily P&L limits and orchestrates liquidation when thresholds are hit.  
**Public API:** `RiskManager`

## Quick Start
```python
from ZacQC.management.risk_manager import RiskManager

risk_manager = RiskManager(qc_algo)
if not risk_manager.ValidateTradingConditions():
    qc_algo.Log("Trading halted by risk controls.")
```

## Public API
### Classes
- `RiskManager(algorithm)` — Tracks realised/unrealised P&L and blocks trading once limits are reached.  
  **Init params:** `algorithm`.  
  **Key methods:** `ValidateTradingConditions(metrics=None)`, `CheckDailyPnLLimit()`, `HandleTargetPnLReached()`.  
  **Raises:** Propagates errors from Lean liquidation routines.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Uses Lean portfolio statistics and interacts with symbol managers for order cancellation.  
- **Invariants:** Sets `daily_starting_value` once per day; `daily_limit_reached` flag must prevent further orders.  
- **Performance considerations:** Logging throttled to 60-second and 1-hour intervals to reduce noise.

## Examples
```python
if risk_manager.CheckDailyPnLLimit():
    qc_algo.Debug("Limit hit, will skip new entries.")
```

## Known Limitations / TODOs
- Calculation still mirrors legacy logic; future refactor could consolidate QC and custom P&L computations.

## See Also
- [Parent package](../modules/ZacQC.management.md)
- [Related module](../modules/ZacQC.main.md)

Last updated: 2025-10-14
