import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.data_download.data_store import LeanDataStore
from server.data_download.lean_schema import Resolution
from server.data_download.polygon_downloader import PolygonIncrementalDownloader


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
def test_polygon_downloader_live_one_day(tmp_path):
    if not os.environ.get("RUN_POLYGON_LIVE_TESTS"):
        pytest.skip("Set RUN_POLYGON_LIVE_TESTS=1 to exercise the live Polygon downloader test.")

    api_key = _load_polygon_key()
    if not api_key:
        pytest.fail("Polygon API key is required for live downloader tests.")

    try:
        from server.data_download.polygon_client import PolygonAggregatorClient
        from server.trading_calendar import USEquityTradingCalendar
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        pytest.fail(f"Required dependency missing for live Polygon test: {exc}")

    store = LeanDataStore(tmp_path / "data")
    calendar = USEquityTradingCalendar(api_key)
    downloader = PolygonIncrementalDownloader(
        api_key=api_key,
        data_store=store,
        calendar=calendar,
        client=PolygonAggregatorClient(api_key),
    )

    target_day = calendar.get_previous_trading_day(date.today())
    summary = downloader.download(["AAPL"], target_day, target_day, [Resolution.MINUTE])

    assert any(event.status == "downloaded" for event in summary.events), "Expected at least one download event"
