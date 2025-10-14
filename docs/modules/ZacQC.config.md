# ZacQC.config
**Path:** `ZacQC/config`  
**Purpose:** Houses trading parameter configuration used by all subsystems.  
**Public API:** `parameters`

## Quick Start
```python
from ZacQC.config.parameters import TradingParameters

params = TradingParameters()
params.update_parameter("Max_Daily_PNL", 0.3)
```

## Public API
### Classes
- _See submodules._

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Independent of Lean; acts as pure configuration storage.  
- **Invariants:** Defaults mirror canonical values from the legacy Google Sheets.

## Examples
```python
from ZacQC.config.parameters import TradingParameters

params = TradingParameters()
print(params.symbols)
```

## Known Limitations / TODOs
- `_load_from_config` currently unused; consider removing or wiring to CLI overrides.

## See Also
- [Parent package](../modules/ZacQC.md)
- [Related module](../modules/ZacQC.config.parameters.md)

Last updated: 2025-10-14
