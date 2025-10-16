import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.data_download.data_store import LeanDataStore
from server.data_download.lean_schema import Resolution
from server.data_download.polygon_downloader import PolygonIncrementalDownloader


class StubClient:
    def __init__(self, responses):
        self._responses = responses
        self._request_count = 0
        self.calls = []

    def get_aggregate_bars(self, symbol, multiplier, timespan, start, end, **kwargs):
        self._request_count += 1
        key = (symbol, timespan)
        if timespan in {"minute", "second"}:
            key = (symbol, timespan, start.astimezone(timezone.utc).date())
        self.calls.append(key)
        return self._responses.get(key, [])

    @property
    def request_count(self):
        return self._request_count


class StubCalendar:
    def __init__(self, trading_days):
        self._days = trading_days

    def get_trading_days(self, start, end):
        return [day for day in self._days if start <= day <= end]


def _epoch_ms(dt):
    return int(dt.timestamp() * 1000)


def test_downloader_writes_intraday_archive(tmp_path):
    root = tmp_path / "data"
    store = LeanDataStore(root)

    trading_day = date(2024, 9, 5)
    responses = {
        ("AAPL", "minute", trading_day): [
            {
                "t": _epoch_ms(datetime(2024, 9, 5, 13, 30, tzinfo=timezone.utc)),
                "o": 154.0,
                "h": 155.0,
                "l": 153.5,
                "c": 154.5,
                "v": 100,
            }
        ]
    }

    client = StubClient(responses)
    calendar = StubCalendar([trading_day])
    downloader = PolygonIncrementalDownloader(
        api_key="dummy",
        data_store=store,
        calendar=calendar,
        client=client,
    )

    summary = downloader.download(["AAPL"], trading_day, trading_day, [Resolution.MINUTE])

    target = root / "equity" / "usa" / "minute" / "aapl" / "20240905_trade.zip"
    assert target.exists()

    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
        assert names == ["20240905_aapl_minute_trade.csv"]
        content = archive.read(names[0]).decode().strip()
        assert content == "34200000,1540000,1550000,1535000,1545000,100"

    assert client.request_count == 1
    assert len(summary.events) == 1
    assert summary.events[0].status == "downloaded"
    assert summary.events[0].bars == 1


def test_downloader_skips_when_data_present(tmp_path):
    root = tmp_path / "data"
    store = LeanDataStore(root)
    trading_day = date(2024, 9, 5)
    store.write_intraday_day(
        "AAPL",
        Resolution.MINUTE,
        trading_day,
        "34200000,1540000,1550000,1535000,1545000,100",
    )

    client = StubClient({})
    calendar = StubCalendar([trading_day])
    downloader = PolygonIncrementalDownloader(
        api_key="dummy",
        data_store=store,
        calendar=calendar,
        client=client,
    )

    summary = downloader.download(["AAPL"], trading_day, trading_day, [Resolution.MINUTE])

    assert client.request_count == 0
    assert summary.cache_hits == 1
    assert summary.events[0].status == "cache_hit"


def test_downloader_updates_daily_archive(tmp_path):
    root = tmp_path / "data"
    store = LeanDataStore(root)

    existing_rows = {
        "20240905": "20240905 00:00,1540000,1550000,1535000,1545000,100",
    }
    store.upsert_daily_rows("AAPL", existing_rows)

    missing_day = date(2024, 9, 6)
    responses = {
        ("AAPL", "day"): [
            {
                "t": _epoch_ms(datetime(2024, 9, 6, 0, 0, tzinfo=timezone.utc)),
                "o": 156.0,
                "h": 157.0,
                "l": 155.0,
                "c": 156.5,
                "v": 200,
            }
        ]
    }

    client = StubClient(responses)
    calendar = StubCalendar([date(2024, 9, 5), missing_day])
    downloader = PolygonIncrementalDownloader(
        api_key="dummy",
        data_store=store,
        calendar=calendar,
        client=client,
    )

    summary = downloader.download(["AAPL"], missing_day, missing_day, [Resolution.DAILY])

    target = root / "equity" / "usa" / "daily" / "aapl.zip"
    with zipfile.ZipFile(target, "r") as archive:
        content = archive.read("aapl.csv").decode().strip().splitlines()
    assert content == [
        "20240905 00:00,1540000,1550000,1535000,1545000,100",
        "20240906 00:00,1560000,1570000,1550000,1565000,200",
    ]

    assert any(event.trading_day == missing_day for event in summary.events)
    assert summary.events[0].status == "downloaded"
    assert client.request_count == 1

