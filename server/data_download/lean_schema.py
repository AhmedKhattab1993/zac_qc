"""
QuantConnect Lean equity trade data schema helpers.

Lean stores equities trade bars in gzip-compressed CSV files wrapped in zip
archives. For sub-daily resolutions the archive lives under
``data/equity/usa/<resolution>/<symbol>/<YYYYMMDD>_trade.zip`` and contains a
single CSV named ``<YYYYMMDD>_<symbol>_<resolution>_trade.csv``. The CSV rows
are comma-separated without a header and follow the layout:

    time, open, high, low, close, volume

Where:

* ``time`` is the number of milliseconds after midnight (00:00:00) in the
  America/New_York timezone for the trading session's calendar day.
* ``open``/``high``/``low``/``close`` are integer prices scaled by
  ``DEFAULT_PRICE_SCALE`` (e.g. 1543300 → 154.33 USD).
* ``volume`` is the total traded share quantity for the bar.

Daily data lives under ``data/equity/usa/daily/<symbol>.zip`` with a CSV named
``<symbol>.csv`` where the first column is ``YYYYMMDD 00:00``.

The helpers in this module are the source of truth for the downloader to
transform Polygon aggregate bars into Lean-formatted archives.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from zoneinfo import ZoneInfo

LEAN_DATA_ROOT = Path("data") / "equity" / "usa"
LEAN_TIMEZONE = ZoneInfo("America/New_York")

# Lean stores prices as integers scaled by 1e4 for equities.
DEFAULT_PRICE_SCALE = 10_000

# Column order for Lean trade CSV rows.
LEAN_TRADE_CSV_COLUMNS: Sequence[str] = (
    "time",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


class Resolution(str, Enum):
    """Lean trade resolutions supported by the downloader."""

    DAILY = "daily"
    MINUTE = "minute"
    SECOND = "second"

    @property
    def requires_trading_day(self) -> bool:
        return self in (Resolution.MINUTE, Resolution.SECOND)


def normalize_symbol_folder(symbol: str) -> str:
    """Return the lowercase folder name used by Lean for a symbol."""

    return symbol.lower()


def build_trade_csv_filename(
    symbol: str,
    resolution: Resolution,
    trading_day: date | None,
) -> str:
    """
    Construct the internal CSV filename for a Lean trade archive.

    Parameters
    ----------
    symbol:
        Equity ticker symbol (case-insensitive).
    resolution:
        Target data resolution.
    trading_day:
        Calendar day of the data in the America/New_York timezone. Required
        for minute/second resolutions.
    """

    symbol_folder = normalize_symbol_folder(symbol)
    if resolution is Resolution.DAILY:
        return f"{symbol_folder}.csv"
    if trading_day is None:
        raise ValueError("trading_day is required for sub-daily resolutions")

    day_str = trading_day.strftime("%Y%m%d")
    return f"{day_str}_{symbol_folder}_{resolution.value}_trade.csv"


def build_trade_zip_path(
    base_dir: Path,
    symbol: str,
    resolution: Resolution,
    trading_day: date | None,
) -> Path:
    """
    Compute the on-disk location for a Lean trade archive.

    Parameters mirror :func:`build_trade_csv_filename`.
    """

    symbol_folder = normalize_symbol_folder(symbol)
    if resolution is Resolution.DAILY:
        return base_dir / "equity" / "usa" / "daily" / f"{symbol_folder}.zip"

    if trading_day is None:
        raise ValueError("trading_day is required for sub-daily resolutions")

    day_str = trading_day.strftime("%Y%m%d")
    return (
        base_dir
        / "equity"
        / "usa"
        / resolution.value
        / symbol_folder
        / f"{day_str}_trade.zip"
    )


@dataclass(frozen=True)
class LeanBar:
    """
    Representation of a Lean trade bar ready to be serialized.

    This structure centralizes scaling to guarantee we emit integers that Lean
    expects across all resolutions.
    """

    time_millis: int
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int

    def to_csv_row(self) -> str:
        return ",".join(
            (
                str(self.time_millis),
                str(self.open_price),
                str(self.high_price),
                str(self.low_price),
                str(self.close_price),
                str(self.volume),
            )
        )


def scale_price(value: float, price_scale: int = DEFAULT_PRICE_SCALE) -> int:
    """
    Convert a float price to Lean's integer representation.

    Rounds to the nearest integer using bankers' rounding to match Lean's
    behavior when ingesting Polygon data through the CLI.
    """

    return int(round(value * price_scale))


def to_lean_time_millis(timestamp: datetime) -> int:
    """
    Convert an aware datetime to Lean's millisecond offset representation.

    Lean expects timestamps relative to midnight in the America/New_York
    timezone. Inputs are normalized to US/Eastern and the offset is computed
    from midnight of that calendar day.
    """

    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    eastern_timestamp = timestamp.astimezone(LEAN_TIMEZONE)
    midnight = eastern_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = eastern_timestamp - midnight
    return int(delta.total_seconds() * 1000)


def serialize_bars(rows: Iterable[LeanBar]) -> str:
    """Serialize bars to Lean's newline-delimited CSV payload."""

    return "\n".join(bar.to_csv_row() for bar in rows)

