from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:  # pragma: no cover
    from server.trading_calendar import USEquityTradingCalendar

from .data_store import LeanDataStore
from .lean_schema import Resolution


class GapDetector:
    """Identify missing Lean trading days for a symbol/configuration."""

    def __init__(
        self,
        data_store: LeanDataStore,
        calendar: "USEquityTradingCalendar",
    ) -> None:
        self._data_store = data_store
        self._calendar = calendar

    def missing_days(
        self,
        symbol: str,
        resolution: Resolution,
        start: date,
        end: date,
    ) -> List[date]:
        """
        Return trading days lacking Lean archives for the given parameters.

        For daily data this checks CSV rows inside ``<symbol>.zip``.
        For minute/second data it checks per-day ``_trade.zip`` files.
        """

        trading_days = self._calendar.get_trading_days(start, end)
        if not trading_days:
            return []

        if resolution is Resolution.DAILY:
            existing = self._daily_days(symbol)
        else:
            existing = set(self._data_store.intraday_days_present(symbol, resolution))

        return [day for day in trading_days if day not in existing]

    # ----------------------------------------------------------------- helpers
    def _daily_days(self, symbol: str) -> Set[date]:
        rows = self._data_store.load_daily_rows(symbol)
        days: Set[date] = set()
        for token in rows.keys():
            try:
                day = date(
                    int(token[0:4]),
                    int(token[4:6]),
                    int(token[6:8]),
                )
            except (ValueError, IndexError):
                continue
            days.add(day)
        return days
