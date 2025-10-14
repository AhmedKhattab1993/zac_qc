# server
**Path:** `server`  
**Purpose:** REST and utility services supporting ZacQC operations outside the Lean runtime.  
**Public API:** `backtest_server`, `trading_calendar`

## Quick Start
```python
from server.backtest_server import app

if __name__ == "__main__":
    app.run()
```

## Public API
### Classes
- _See submodules._

### Functions
- _None_

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** Flask for HTTP, Lean CLI for backtests, and `pandas_market_calendars` for calendar logic.  
- **Invariants:** Server expects ZacQC project directories to exist relative to repo root.

## Examples
```python
from server.trading_calendar import USEquityTradingCalendar

calendar = USEquityTradingCalendar()
calendar.is_trading_day(date.today())
```

## Known Limitations / TODOs
- Flask app is intended for trusted environments; add authentication before production use.

## See Also
- [Related module](../modules/server.backtest_server.md)
- [Related module](../modules/server.trading_calendar.md)

Last updated: 2025-10-14
