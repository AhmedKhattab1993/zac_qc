import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ensure project root is importable when tests run in isolation.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.data_download.lean_schema import (
    DEFAULT_PRICE_SCALE,
    LEAN_TRADE_CSV_COLUMNS,
    Resolution,
    LeanBar,
    build_trade_csv_filename,
    build_trade_zip_path,
    normalize_symbol_folder,
    scale_price,
    serialize_bars,
    to_lean_time_millis,
)


def test_trade_csv_columns_match_lean_spec() -> None:
    assert LEAN_TRADE_CSV_COLUMNS == ("time", "open", "high", "low", "close", "volume")


@pytest.mark.parametrize(
    ("symbol", "resolution", "day", "expected"),
    [
        ("AAPL", Resolution.DAILY, None, "aapl.csv"),
        ("MSFT", Resolution.MINUTE, datetime(2024, 9, 5).date(), "20240905_msft_minute_trade.csv"),
        ("SPY", Resolution.SECOND, datetime(2024, 9, 5).date(), "20240905_spy_second_trade.csv"),
    ],
)
def test_build_trade_csv_filename(symbol, resolution, day, expected) -> None:
    if resolution.requires_trading_day:
        assert build_trade_csv_filename(symbol, resolution, day) == expected
    else:
        assert build_trade_csv_filename(symbol, resolution, day) == expected


def test_build_trade_csv_filename_requires_day_for_intraday() -> None:
    with pytest.raises(ValueError):
        build_trade_csv_filename("AAPL", Resolution.MINUTE, None)


def test_build_trade_zip_path_daily() -> None:
    base = Path("/tmp/lean")
    expected = base / "equity" / "usa" / "daily" / "aapl.zip"
    assert build_trade_zip_path(base, "AAPL", Resolution.DAILY, None) == expected


def test_build_trade_zip_path_intraday() -> None:
    base = Path("/tmp/lean")
    trading_day = datetime(2024, 9, 5).date()
    expected = base / "equity" / "usa" / "minute" / "aapl" / "20240905_trade.zip"
    assert build_trade_zip_path(base, "AAPL", Resolution.MINUTE, trading_day) == expected


def test_normalize_symbol_folder_lowercases() -> None:
    assert normalize_symbol_folder("AaPl") == "aapl"


def test_scale_price_uses_default_scale() -> None:
    assert scale_price(154.33) == 1_543_300


def test_scale_price_rounds_midpoint_to_even() -> None:
    assert scale_price(1.23495, DEFAULT_PRICE_SCALE) == 12_350


def test_to_lean_time_millis_requires_tz_aware() -> None:
    with pytest.raises(ValueError):
        to_lean_time_millis(datetime(2024, 9, 5, 9, 30))


def test_to_lean_time_millis_converts_to_eastern() -> None:
    timestamp = datetime.fromisoformat("2024-09-05T09:30:00-04:00")
    assert to_lean_time_millis(timestamp) == 34_200_000


def test_serialize_bars_orders_columns() -> None:
    bar = LeanBar(
        time_millis=34_200_000,
        open_price=1_234_500,
        high_price=1_235_000,
        low_price=1_233_000,
        close_price=1_234_800,
        volume=123_456,
    )
    assert serialize_bars([bar]) == "34200000,1234500,1235000,1233000,1234800,123456"
