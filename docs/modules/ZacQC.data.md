# ZacQC.data
**Path:** `ZacQC/data`  
**Purpose:** Data ingestion and metric calculation layer for the ZacQC reference algorithm.  
**Public API:** `data_manager`, `metrics_calculator`

## Quick Start
```python
from ZacQC.data.data_manager import DataManager
from ZacQC.data.metrics_calculator import MetricsCalculator

wrapped_algo = AlgorithmWrapper(qc_algo, qc_algo.symbol)  # provided by SymbolManager
data_manager = DataManager(wrapped_algo)
metrics = MetricsCalculator(wrapped_algo)
```

## Public API
### Classes
- _See submodules._

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Consume QuantConnect consolidators, Lean history API, and provide metrics for trading conditions.  
- **Invariants:** `DataManager` updates `metrics_calculator` via shared references; both expect the algorithm to set `data_manager` attribute.

## Examples
```python
from ZacQC.data.metrics_calculator import MetricsCalculator

metrics_calc = MetricsCalculator(qc_algo)
current_metrics = metrics_calc.CalculateAllMetrics(slice)
```

## Known Limitations / TODOs
- Historical loading currently fetches only 50 daily bars; adjust for longer lookbacks if needed.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.core.symbol_manager.md)

Last updated: 2025-10-14
