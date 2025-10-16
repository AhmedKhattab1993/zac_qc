"""
Command-line utilities to prepare backtest environments for Playwright specs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .backtest_harness import (
    BacktestEnvironment,
    create_backtest_environment,
    seed_seconds_fixture,
)

DEFAULT_SYMBOL = "SPY"
DEFAULT_TRADING_DAY = date(2025, 10, 8)
DEFAULT_START_DATE = DEFAULT_TRADING_DAY.strftime("%Y-%m-%d")
DEFAULT_END_DATE = DEFAULT_START_DATE


def _prepare_missing_data(workspace: Path) -> BacktestEnvironment:
    return create_backtest_environment(
        workspace,
        symbols=[DEFAULT_SYMBOL],
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        starting_cash=25_000,
    )


def _prepare_cached_data(workspace: Path) -> BacktestEnvironment:
    env = create_backtest_environment(
        workspace,
        symbols=[DEFAULT_SYMBOL],
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        starting_cash=25_000,
    )

    seed_seconds_fixture(
        data_root=env.data_root,
        symbol=DEFAULT_SYMBOL,
        trading_day=DEFAULT_TRADING_DAY,
        rows=[
            "20251008 09:30:00,430.1,430.1,430.1,430.1,10",
            "20251008 09:30:01,430.2,430.2,430.2,430.2,15",
            "20251008 09:30:02,430.05,430.05,430.05,430.05,12",
        ],
    )

    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Lean backtest environments for Playwright E2E specs.")
    parser.add_argument("scenario", choices=["missing-data", "cached-data"], help="Scenario identifier.")
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Target directory where data/config fixtures will be written.",
    )

    args = parser.parse_args(argv)
    workspace: Path = args.workspace

    if args.scenario == "missing-data":
        env = _prepare_missing_data(workspace)
    else:
        env = _prepare_cached_data(workspace)

    payload = {
        "env": env.env,
        "data_root": str(env.data_root),
        "config_path": str(env.config_path),
        "symbols": list(env.symbols),
        "start_date": env.start_date,
        "end_date": env.end_date,
        "trading_day": DEFAULT_TRADING_DAY.strftime("%Y-%m-%d"),
    }

    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
