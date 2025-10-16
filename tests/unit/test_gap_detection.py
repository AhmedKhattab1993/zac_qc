import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.data_download.data_store import LeanDataStore
from server.data_download.gap_detection import GapDetector
from server.data_download.lean_schema import Resolution


class StubCalendar:
    def __init__(self, trading_days):
        self._days = trading_days

    def get_trading_days(self, start, end):
        return [day for day in self._days if start <= day <= end]


def test_gap_detector_identifies_missing_intraday_day(tmp_path):
    root = tmp_path / "data"
    store = LeanDataStore(root)

    # Persist one day so the other is treated as missing.
    trading_day = date(2024, 9, 5)
    payload = "34200000,1234500,1234600,1234400,1234550,100"
    store.write_intraday_day("AAPL", Resolution.MINUTE, trading_day, payload)

    calendar = StubCalendar([date(2024, 9, 5), date(2024, 9, 6)])
    detector = GapDetector(store, calendar)

    missing = detector.missing_days("AAPL", Resolution.MINUTE, date(2024, 9, 5), date(2024, 9, 6))
    assert missing == [date(2024, 9, 6)]


def test_gap_detector_reads_daily_archive(tmp_path):
    root = tmp_path / "data"
    store = LeanDataStore(root)

    existing_rows = {
        "20240905": "20240905 00:00,1234500,1234600,1234400,1234550,100",
    }
    store.upsert_daily_rows("AAPL", existing_rows)

    calendar = StubCalendar([date(2024, 9, 5), date(2024, 9, 6)])
    detector = GapDetector(store, calendar)

    missing = detector.missing_days("AAPL", Resolution.DAILY, date(2024, 9, 5), date(2024, 9, 6))
    assert missing == [date(2024, 9, 6)]
