# ZacQC.main_minimal
**Path:** `ZacQC/main_minimal.py`  
**Purpose:** Smoke-test algorithm verifying ZacQC dependencies without full orchestration.  
**Public API:** `MinimalTradingAlgorithm`

## Quick Start
```python
from ZacQC.main_minimal import MinimalTradingAlgorithm

class Harness(MinimalTradingAlgorithm):
    def Initialize(self) -> None:
        super().Initialize()
```

## Public API
### Classes
- `MinimalTradingAlgorithm()` — Bare-bones QCAlgorithm useful for integration tests.  
  **Init params:** None.  
  **Key methods:** `Initialize()`, `OnData(data)`.  
  **Raises:** None.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Only relies on `config.TradingParameters` to mirror primary algorithm imports.  
- **Invariants:** Performs no trading; intended for environment validation.

## Examples
```python
algo = MinimalTradingAlgorithm()
algo.Initialize()
```

## Known Limitations / TODOs
- Not configured for live trading; use purely as a scaffolding tool.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.main.md)

Last updated: 2025-10-14
