from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from server.trading_calendar import USEquityTradingCalendar

from .data_store import LeanDataStore
from .gap_detection import GapDetector
from .lean_schema import (
    LEAN_TIMEZONE,
    Resolution,
    LeanBar,
    serialize_bars,
    scale_price,
    to_lean_time_millis,
)
from .polygon_client import PolygonAggregatorClient


@dataclass
class DownloadEvent:
    symbol: str
    resolution: Resolution
    trading_day: Optional[date]
    status: str
    bars: int = 0
    bytes_written: int = 0


@dataclass
class DownloadSummary:
    events: List[DownloadEvent] = field(default_factory=list)
    http_requests: int = 0
    cache_hits: int = 0

    def add_event(self, event: DownloadEvent) -> None:
        self.events.append(event)
        if event.status == "cache_hit":
            self.cache_hits += 1

    def downloaded_events(self) -> List[DownloadEvent]:
        return [event for event in self.events if event.status == "downloaded"]


class PolygonIncrementalDownloader:
    """High-level orchestrator for incremental Polygon downloads."""

    def __init__(
        self,
        api_key: str,
        *,
        data_store: LeanDataStore,
        calendar: "USEquityTradingCalendar",
        client: Optional[PolygonAggregatorClient] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._client = client or PolygonAggregatorClient(api_key)
        self._data_store = data_store
        self._calendar = calendar
        self._gap_detector = GapDetector(data_store, calendar)
        self._logger = logger or logging.getLogger("backtest_logger")
        self._api_key = api_key

    def download(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        resolutions: Sequence[Resolution],
    ) -> DownloadSummary:
        summary = DownloadSummary()
        starting_requests = self._client.request_count

        for symbol in symbols:
            for resolution in resolutions:
                missing = self._gap_detector.missing_days(symbol, resolution, start, end)
                if not missing:
                    summary.add_event(
                        DownloadEvent(
                            symbol=symbol,
                            resolution=resolution,
                            trading_day=None,
                            status="cache_hit",
                        )
                    )
                    self._log(
                        "cache_hit",
                        symbol,
                        resolution,
                        None,
                        {"message": "All data present locally"},
                    )
                    continue

                if resolution is Resolution.DAILY:
                    daily_events = self._download_daily(symbol, missing)
                    for event in daily_events:
                        summary.add_event(event)
                else:
                    for trading_day in missing:
                        event = self._download_intraday(symbol, resolution, trading_day)
                        summary.add_event(event)

        summary.http_requests = self._client.request_count - starting_requests
        return summary

    # ----------------------------------------------------------------- helpers
    def _download_daily(self, symbol: str, days: List[date]) -> List[DownloadEvent]:
        if not days:
            return []

        start_dt = datetime.combine(days[0], time.min, tzinfo=LEAN_TIMEZONE)
        end_dt = datetime.combine(days[-1], time.max, tzinfo=LEAN_TIMEZONE)

        results = self._client.get_aggregate_bars(
            symbol,
            multiplier=1,
            timespan="day",
            start=start_dt,
            end=end_dt,
        )

        day_set = set(days)
        rows: Dict[str, str] = {}
        events: List[DownloadEvent] = []

        for result in results:
            bar_time = datetime.fromtimestamp(result["t"] / 1000, tz=timezone.utc)
            trading_day = bar_time.date()
            if trading_day not in day_set:
                continue
            day_token = trading_day.strftime("%Y%m%d")
            row = ",".join(
                (
                    f"{day_token} 00:00",
                    str(scale_price(result["o"])),
                    str(scale_price(result["h"])),
                    str(scale_price(result["l"])),
                    str(scale_price(result["c"])),
                    str(int(result["v"])),
                )
            )
            rows[day_token] = row
            events.append(
                DownloadEvent(
                    symbol=symbol,
                    resolution=Resolution.DAILY,
                    trading_day=trading_day,
                    status="downloaded",
                    bars=1,
                )
            )

        if not rows:
            self._log(
                "empty",
                symbol,
                Resolution.DAILY,
                None,
                {"message": "Polygon returned no rows for requested days"},
            )
            return [
                DownloadEvent(
                    symbol=symbol,
                    resolution=Resolution.DAILY,
                    trading_day=None,
                    status="empty",
                )
            ]

        path = self._data_store.upsert_daily_rows(symbol, rows)
        file_size = path.stat().st_size

        for event in events:
            event.bytes_written = file_size

        self._log(
            "downloaded",
            symbol,
            Resolution.DAILY,
            None,
            {
                "days": len(events),
                "bytes": file_size,
            },
        )
        return events

    def _download_intraday(
        self,
        symbol: str,
        resolution: Resolution,
        trading_day: date,
    ) -> DownloadEvent:
        start_dt = datetime.combine(trading_day, time.min, tzinfo=LEAN_TIMEZONE)
        end_dt = datetime.combine(trading_day, time.max, tzinfo=LEAN_TIMEZONE)

        timespan = "minute" if resolution is Resolution.MINUTE else "second"

        results = self._client.get_aggregate_bars(
            symbol,
            multiplier=1,
            timespan=timespan,
            start=start_dt,
            end=end_dt,
        )

        bars = self._convert_results_to_lean_bars(results)
        if not bars:
            self._log(
                "empty",
                symbol,
                resolution,
                trading_day,
                {"message": "Polygon returned no intraday bars"},
            )
            return DownloadEvent(
                symbol=symbol,
                resolution=resolution,
                trading_day=trading_day,
                status="empty",
            )

        payload = serialize_bars(bars)
        path = self._data_store.write_intraday_day(symbol, resolution, trading_day, payload)
        file_size = path.stat().st_size

        self._log(
            "downloaded",
            symbol,
            resolution,
            trading_day,
            {"bars": len(bars), "bytes": file_size},
        )

        return DownloadEvent(
            symbol=symbol,
            resolution=resolution,
            trading_day=trading_day,
            status="downloaded",
            bars=len(bars),
            bytes_written=file_size,
        )

    def _convert_results_to_lean_bars(self, results: List[dict]) -> List[LeanBar]:
        bars: List[LeanBar] = []
        for result in results:
            ts = datetime.fromtimestamp(result["t"] / 1000, tz=timezone.utc)
            try:
                bar = LeanBar(
                    time_millis=to_lean_time_millis(ts),
                    open_price=scale_price(result["o"]),
                    high_price=scale_price(result["h"]),
                    low_price=scale_price(result["l"]),
                    close_price=scale_price(result["c"]),
                    volume=int(result["v"]),
                )
            except KeyError as exc:
                raise ValueError(f"Missing expected field in Polygon response: {exc}") from exc
            bars.append(bar)

        return bars

    def _log(
        self,
        event_type: str,
        symbol: str,
        resolution: Resolution,
        trading_day: Optional[date],
        extra: Dict[str, object],
    ) -> None:
        payload = {
            "event": event_type,
            "phase": "data_download",
            "symbol": symbol,
            "resolution": resolution.value,
        }
        if trading_day:
            payload["trading_day"] = trading_day.isoformat()
        payload.update(extra)

        self._logger.info(payload)
