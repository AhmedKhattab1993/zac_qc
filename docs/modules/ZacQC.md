# ZacQC
**Path:** `ZacQC`  
**Purpose:** Root package for the ZacQC reference trading system.  
**Public API:** `main`, `core`, `trading`, `management`, `data`, `config`

## Quick Start
```python
from ZacQC.main import ZacReferenceAlgorithm

algorithm = ZacReferenceAlgorithm()
# QuantConnect runtime handles lifecycle; call Initialize via Lean.
```

## Public API
### Classes
- _None_

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Built on QuantConnect Lean (`AlgorithmImports`), uses package-local subsystems for data, metrics, risk, and execution.  
- **Invariants:** Each subpackage focuses on a single responsibility to mirror the original ZacQC architecture.  
- **Performance considerations:** Logging can emit high-volume diagnostics; disable `enable_logging` in production.

## Examples
```python
from ZacQC.trading.order_manager import OrderManager
from ZacQC.core.symbol_manager import SymbolManager
```

## Known Limitations / TODOs
- No consolidated `__init__.py` exporting subpackage shortcuts.
- Designed to run exclusively inside the Lean engine.

## See Also
- [Related module](../modules/ZacQC.main.md)
- [Related module](../modules/ZacQC.core.md)

Last updated: 2025-10-14
