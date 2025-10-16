"""
Support utilities for end-to-end backtest scenarios.

These helpers generate reduced trading parameter modules and temporary Lean
data roots for Playwright tests so we can run the real Lean CLI against small,
deterministic workloads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from server.data_download.data_store import LeanDataStore
from server.data_download.lean_schema import Resolution

_MODULE_TEMPLATE = """\"\"\"Auto-generated trading parameters for E2E tests.\"\"\"
import os

_PREV = os.environ.pop("BACKTEST_CONFIG_PATH", None)
try:
    from ZacQC.config.parameters import TradingParameters as _BaseTradingParameters
    _params = _BaseTradingParameters()
finally:
    if _PREV is not None:
        os.environ["BACKTEST_CONFIG_PATH"] = _PREV

{assignments}

parameters = _params
"""


@dataclass
class BacktestEnvironment:
    """Encapsulates filesystem paths and environment variables for a scenario."""

    root: Path
    data_root: Path
    config_path: Path
    env: Dict[str, str]
    symbols: Sequence[str]
    start_date: str
    end_date: str

    def merged_env(self, base_env: Mapping[str, str] | None = None) -> Dict[str, str]:
        """Return environment variables merged with an optional base mapping."""
        result = dict(base_env or {})
        result.update(self.env)
        return result


def create_backtest_environment(
    workspace: Path,
    *,
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    starting_cash: int = 100_000,
    extra_overrides: Mapping[str, Any] | None = None,
) -> BacktestEnvironment:
    """
    Materialise a backtest environment with a reduced parameters module.

    The returned object includes a dedicated Lean data root and configuration
    file that can be targeted by the server via environment variables.
    """

    if not symbols:
        raise ValueError("symbols must contain at least one entry")

    workspace.mkdir(parents=True, exist_ok=True)
    data_root = workspace / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "parameters.py"

    write_parameters_override(
        config_path,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        starting_cash=starting_cash,
        extra_overrides=extra_overrides or {},
    )

    env = {
        "BACKTEST_DATA_ROOT": str(data_root),
        "BACKTEST_CONFIG_PATH": str(config_path),
        "BACKTEST_SYMBOLS": ",".join(symbols),
    }

    return BacktestEnvironment(
        root=workspace,
        data_root=data_root,
        config_path=config_path,
        env=env,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )


def write_parameters_override(
    destination: Path,
    *,
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    starting_cash: int,
    extra_overrides: Mapping[str, Any],
) -> Path:
    """
    Generate a Python module that exposes a fully-populated ``parameters`` object.

    The module instantiates the real TradingParameters class while temporarily
    clearing ``BACKTEST_CONFIG_PATH`` to avoid recursion, then mutates the
    relevant attributes (symbols, dates, cash, plus optional overrides).
    """

    assignment_lines = [
        f"_params.symbols = {list(symbols)!r}",
        f"_params.start_date = {start_date!r}",
        f"_params.end_date = {end_date!r}",
        f"_params.starting_cash = {starting_cash!r}",
    ]

    extra_lines = [f"_params.{key} = {value!r}" for key, value in extra_overrides.items()]
    all_lines = assignment_lines + extra_lines
    rendered = _MODULE_TEMPLATE.format(assignments="\n".join(all_lines))

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination


def seed_seconds_fixture(
    *,
    data_root: Path,
    symbol: str,
    trading_day: date,
    rows: Sequence[str],
) -> Path:
    """
    Persist a seconds-resolution Lean archive with the provided CSV rows.

    Returns the path to the generated ``*.zip`` archive.
    """

    if not rows:
        raise ValueError("rows must include at least one CSV payload line")

    payload = "\n".join(rows) + "\n"
    store = LeanDataStore(data_root)
    return store.write_intraday_day(symbol, Resolution.SECOND, trading_day, payload)
