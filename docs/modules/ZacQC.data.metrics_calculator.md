# ZacQC.data.metrics_calculator
**Path:** `ZacQC/data/metrics_calculator.py`  
**Purpose:** Computes the minimal metric set required by trading conditions and risk checks.  
**Public API:** `MetricsCalculator`

## Quick Start
```python
from ZacQC.data.metrics_calculator import MetricsCalculator

metrics_calc = MetricsCalculator(algorithm=wrapped_algo)
metrics = metrics_calc.CalculateAllMetrics(slice)
```

## Public API
### Classes
- `MetricsCalculator(algorithm)` — Aggregates derived metrics from `DataManager` windows.  
  **Init params:** `algorithm`.  
  **Key methods:** `CalculateAllMetrics(data)`, `CalculateGapMetric()`, `CalculateLiquidityMetric(current_price)`.  
  **Raises:** Logs and swallows most exceptions to keep trading running.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Accesses `DataManager` via `algorithm.data_manager` and uses NumPy for averages.  
- **Invariants:** Maintains cached metrics in `self.metrics`; `actual_p1/2` mirror reference parameters exactly.  
- **Performance considerations:** Reuses previously computed rolling values to avoid redundant calculations each tick.

## Examples
```python
change = metrics_calc.CalculateMaxDownPercentage(max_seconds=900)
metrics_calc.metrics['custom_max_drawdown'] = change
```

## Known Limitations / TODOs
- VWAP calculations are simplified relative to the original implementation; further parity work may be required.

## See Also
- [Parent package](../modules/ZacQC.data.md)
- [Related module](../modules/ZacQC.trading.conditions_checker.md)

Last updated: 2025-10-14
