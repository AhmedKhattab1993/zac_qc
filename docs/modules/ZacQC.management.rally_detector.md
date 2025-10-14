# ZacQC.management.rally_detector
**Path:** `ZacQC/management/rally_detector.py`  
**Purpose:** Implements phase 3 rally detection to validate momentum before order placement.  
**Public API:** `RallyDetector`

## Quick Start
```python
from ZacQC.management.rally_detector import RallyDetector

detector = RallyDetector(qc_algo, qc_algo.parameters)
detector.update_price_data("AAPL", bar)
is_valid = detector.check_long_rally_condition("AAPL", metrics_calculator)
```

## Public API
### Classes
- `RallyDetector(algorithm, params)` — Maintains 15-second price cache and evaluates rally thresholds.  
  **Init params:** `algorithm`, `params`.  
  **Key methods:** `update_price_data(symbol, bar_data)`, `check_long_rally_condition(symbol, metrics)`, `check_short_rally_condition(symbol, metrics)`.  
  **Raises:** Propagates exceptions from Lean data access.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Requires access to strategy metrics (`metric_range_price`, `metric_range_multiplier`).  
- **Invariants:** Caches only current-day market-hours data to keep calculations accurate.  
- **Performance considerations:** Prunes cache to last four hours of 15-second bars to bound memory usage.

## Examples
```python
result, reset = detector.check_long_rally_with_reset("AAPL", metrics_calculator)
if reset:
    strategy.reset_condition_state("c1")
```

## Known Limitations / TODOs
- Extensive logging remains enabled for diagnostics; introduce verbosity controls for production.

## See Also
- [Parent package](../modules/ZacQC.management.md)
- [Related module](../modules/ZacQC.trading.conditions_checker.md)

Last updated: 2025-10-14
