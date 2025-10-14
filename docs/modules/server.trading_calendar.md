# server.trading_calendar
**Path:** `server/trading_calendar.py`  
**Purpose:** Utility for determining US equity trading sessions, early closes, and holidays.  
**Public API:** `USEquityTradingCalendar`

## Quick Start
```python
from server.trading_calendar import USEquityTradingCalendar

calendar = USEquityTradingCalendar()
calendar.is_trading_day(date(2025, 1, 2))
```

## Public API
### Classes
- `USEquityTradingCalendar(polygon_api_key=None)` — Provides trading-day helpers backed by `pandas_market_calendars`.  
  **Init params:** optional `polygon_api_key` (unused; retained for compatibility).  
  **Key methods:** `is_trading_day(check_date)`, `get_market_hours(check_date)`, `get_market_holidays(year)`.  
  **Raises:** Propagates exceptions from `pandas_market_calendars` on calendar fetch failures.

### Functions
- `test_trading_calendar()` — Manual smoke test printing sample calendar output.

### Constants / Enums
- _None_

## Design Notes
- **Dependencies:** `pandas` for timestamps and `pandas_market_calendars` for NYSE schedule data.  
- **Invariants:** All outputs are timezone-aware UTC datetimes; holiday detection infers non-trading weekdays.

## Examples
```python
calendar.get_trading_days(date(2025, 1, 1), date(2025, 1, 31))
calendar.is_early_close_day(date(2025, 11, 28))
```

## Known Limitations / TODOs
- Holiday detection relies on heuristic candidate generation; verify against official lists when precision is critical.

## See Also
- [Parent package](../modules/server.md)
- [Related module](../modules/server.backtest_server.md)

Last updated: 2025-10-14
