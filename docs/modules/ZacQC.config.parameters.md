# ZacQC.config.parameters
**Path:** `ZacQC/config/parameters.py`  
**Purpose:** Defines canonical trading parameters and update helpers.  
**Public API:** `TradingParameters`

## Quick Start
```python
from ZacQC.config.parameters import TradingParameters

params = TradingParameters()
params.update_parameter("SameConditionTimeC1", 15)
```

## Public API
### Classes
- `TradingParameters()` — Immutable-style configuration object exposing reference defaults.  
  **Init params:** None.  
  **Key methods:** `update_parameter(param_name, value)`.  
  **Raises:** None.

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Standard library only (`json`, `os`, `datetime`).  
- **Invariants:** Attribute names match historical sheet headers to preserve compatibility.  
- **Performance considerations:** Instantiation is inexpensive; typically created once per algorithm.

## Examples
```python
params = TradingParameters()
params.update_parameter("symbols", ["AAPL", "MSFT"])
```

## Known Limitations / TODOs
- `_load_from_config` helper remains disabled; enable when dynamic overrides are required.

## See Also
- [Parent package](../modules/ZacQC.config.md)
- [Related module](../modules/ZacQC.main.md)

Last updated: 2025-10-14
