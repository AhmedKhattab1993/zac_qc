"""
Data download utilities for ZacQC backtest services.

This package contains helpers for reading and writing market data
files that follow QuantConnect Lean's on-disk layout. Modules are
introduced incrementally alongside the Polygon downloader work.
"""

from .lean_schema import (
    DEFAULT_PRICE_SCALE,
    LEAN_TRADE_CSV_COLUMNS,
    Resolution,
    build_trade_csv_filename,
    build_trade_zip_path,
    normalize_symbol_folder,
)

__all__ = [
    "DEFAULT_PRICE_SCALE",
    "LEAN_TRADE_CSV_COLUMNS",
    "Resolution",
    "build_trade_csv_filename",
    "build_trade_zip_path",
    "normalize_symbol_folder",
]

