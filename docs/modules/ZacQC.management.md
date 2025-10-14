# ZacQC.management
**Path:** `ZacQC/management`  
**Purpose:** Risk and momentum management subsystems.  
**Public API:** `risk_manager`, `rally_detector`

## Quick Start
```python
from ZacQC.management.risk_manager import RiskManager

risk_manager = RiskManager(qc_algo)
```

## Public API
### Classes
- _See submodules._

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Integrates with core and trading layers to gate order placement.  
- **Invariants:** Expects algorithm to expose `symbols`, `symbol_managers`, and order-cancellation utilities.

## Examples
```python
from ZacQC.management.rally_detector import RallyDetector

detector = RallyDetector(qc_algo, qc_algo.parameters)
```

## Known Limitations / TODOs
- Additional documentation for rally parameter tuning pending.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.trading.conditions_checker.md)

Last updated: 2025-10-14
