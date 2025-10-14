# ZacQC.trading.conditions_checker
**Path:** `ZacQC/trading/conditions_checker.py`  
**Purpose:** Evaluates ZacQC reference entry conditions and integrates rally detection.  
**Public API:** `ConditionsChecker`

## Quick Start
```python
from ZacQC.trading.conditions_checker import ConditionsChecker

checker = ConditionsChecker(algorithm=qc_algo)
conditions = checker.CheckAllConditions(strategy, metrics)
```

## Public API
### Classes
- `ConditionsChecker(algorithm)` — Applies sequential state machine logic for five entry conditions.  
  **Init params:** `algorithm`.  
  **Key methods:** `CheckAllConditions(strategy, metrics)`, `IsConditionEnabled(condition)`, `update_rally_data(symbol, bar_data)`.  
  **Raises:** Propagates errors from the rally detector.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Uses `management.RiskManager` for gating and `management.RallyDetector` for momentum checks.  
- **Invariants:** Respects time-based cut-off (15:59) to avoid conflicts with EOD liquidation.  
- **Performance considerations:** Sequential checks short-circuit on disabled conditions to minimise computation.

## Examples
```python
checker.update_rally_data("AAPL", bar)
enabled = checker.IsConditionEnabled("cond3")
```

## Known Limitations / TODOs
- Condition-specific methods (`CheckCondition1`...`5`) mirror legacy logic and remain verbose.

## See Also
- [Parent package](../modules/ZacQC.trading.md)
- [Related module](../modules/ZacQC.management.rally_detector.md)

Last updated: 2025-10-14
