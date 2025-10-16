from datetime import date
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.backtest_server import load_config_strict
from server.data_download.data_store import LeanDataStore
from server.data_download.lean_schema import Resolution
from tests.e2e.support.backtest_harness import (
    BacktestEnvironment,
    create_backtest_environment,
    seed_seconds_fixture,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "backtest-env"


def test_missing_data_download(workspace: Path):
    env = create_backtest_environment(
        workspace,
        symbols=["SPY"],
        start_date="2025-10-08",
        end_date="2025-10-08",
        starting_cash=25_000,
    )

    assert isinstance(env, BacktestEnvironment)
    assert env.data_root.exists()
    assert env.config_path.exists()
    assert env.env["BACKTEST_DATA_ROOT"] == str(env.data_root)
    assert env.env["BACKTEST_CONFIG_PATH"] == str(env.config_path)
    assert env.env["BACKTEST_SYMBOLS"] == "SPY"

    config = load_config_strict(str(env.config_path))
    assert config["symbols"] == ["SPY"]
    assert config["start_date"] == "2025-10-08"
    assert config["end_date"] == "2025-10-08"
    assert config["starting_cash"] == 25_000

    # Empty data directory is expected for the missing-data scenario
    assert not any(env.data_root.iterdir())


def test_cached_data_fixture(workspace: Path):
    env = create_backtest_environment(
        workspace,
        symbols=["SPY"],
        start_date="2025-10-08",
        end_date="2025-10-08",
    )

    trading_day = date(2025, 10, 8)
    archive_path = seed_seconds_fixture(
        data_root=env.data_root,
        symbol="SPY",
        trading_day=trading_day,
        rows=[
            "20251008 09:30:00,430.1,430.1,430.1,430.1,10",
            "20251008 09:30:01,430.2,430.2,430.2,430.2,15",
        ],
    )

    assert archive_path.exists()

    store = LeanDataStore(env.data_root)
    present_days = store.intraday_days_present("SPY", Resolution.SECOND)
    assert trading_day in present_days
