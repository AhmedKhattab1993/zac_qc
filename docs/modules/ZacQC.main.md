# ZacQC.main
**Path:** `ZacQC/main.py`  
**Purpose:** Entry-point algorithm that wires together risk, strategy, and execution for the ZacQC reference system.  
**Public API:** `ZacReferenceAlgorithm`

## Quick Start
```python
from ZacQC.main import ZacReferenceAlgorithm
from AlgorithmImports import QCAlgorithm

class MyAlgorithm(ZacReferenceAlgorithm):
    def Initialize(self) -> None:
        super().Initialize()
        # Extend configuration here.
```

## Public API
### Classes
- `ZacReferenceAlgorithm()` — High-level QCAlgorithm implementation orchestrating the reference workflow.  
  **Init params:** None (QuantConnect invokes lifecycle).  
  **Key methods:** `Initialize()`, `OnData(data)`, `CustomEndOfDay()`, `CancelEntryOrdersAtAlgoOff()`.  
  **Raises:** Propagates exceptions from initialization and scheduling hooks.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** `config.parameters.TradingParameters`, `core.symbol_manager.SymbolManager`, `core.custom_fill_model.PreciseFillModel`, `management.risk_manager.RiskManager`, trading and data subsystems.  
- **Invariants:** Algorithm manages a symbol map (`symbols`) and associated managers (`symbol_managers`) that must stay in sync.  
- **Performance considerations:** Logging is heavily throttled via `enable_logging` flag to keep memory footprint low in backtests.

## Examples
```python
from ZacQC.main import ZacReferenceAlgorithm

class LiveVariant(ZacReferenceAlgorithm):
    def Initialize(self) -> None:
        super().Initialize()
        self.enable_logging = True
```

## Known Limitations / TODOs
- Relies on QuantConnect `AlgorithmImports`; cannot be executed outside Lean runtime.
- Assumes `config.parameters.TradingParameters` contains canonical defaults.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.core.symbol_manager.md)

Last updated: 2025-10-14
