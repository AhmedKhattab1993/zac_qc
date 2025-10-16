import json
import os
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server import backtest_server
from server.backtest_server import BacktestManager
from server.trading_calendar import USEquityTradingCalendar


def _load_polygon_key() -> str | None:
    if api_key := os.environ.get("POLYGON_API_KEY"):
        return api_key

    lean_path = PROJECT_ROOT / "lean.json"
    if not lean_path.exists():
        return None

    with lean_path.open() as handle:
        data = json.load(handle)
    return data.get("polygon-api-key")


@pytest.mark.live
def test_backtest_manager_native_live_download(tmp_path, monkeypatch):
    if not os.environ.get("RUN_POLYGON_LIVE_TESTS"):
        pytest.skip("Set RUN_POLYGON_LIVE_TESTS=1 to exercise the live BacktestManager downloader test.")

    api_key = _load_polygon_key()
    if not api_key:
        pytest.fail("Polygon API key is required for live BacktestManager downloader test.")

    calendar = USEquityTradingCalendar(api_key)
    target_day = calendar.get_previous_trading_day(date.today())
    if target_day is None:
        pytest.fail("Trading calendar did not return a previous trading day.")

    symbols = ["AAPL"]
    start_str = target_day.isoformat()

    def fake_config(_):
        return {
            "symbols": symbols,
            "start_date": start_str,
            "end_date": start_str,
        }

    monkeypatch.setenv("USE_POLYGON_NATIVE_DOWNLOADER", "1")
    monkeypatch.setenv("POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK", "0")
    monkeypatch.setattr(backtest_server, "load_config_strict", fake_config, raising=False)
    monkeypatch.setattr(backtest_server.json, "load", lambda handle: {"polygon-api-key": api_key}, raising=False)
    monkeypatch.setattr(
        backtest_server.BacktestManager,
        "_start_lean_execution",
        lambda self, algo, params: None,
        raising=False,
    )

    manager = BacktestManager(data_root=tmp_path / "data")

    result = manager._execute_backtest_sync("ZacQC", {})
    assert result is None or isinstance(result, dict) and "error" not in result

    assert manager._last_download_method == "native"
    summary = manager._last_download_summary
    assert summary is not None
    assert any(event.status == "downloaded" for event in summary.events)

    minute_path = tmp_path / "data" / "equity" / "usa" / "minute" / "aapl" / f"{target_day:%Y%m%d}_trade.zip"
    assert minute_path.exists(), "Expected minute zip archive to be written"
