import sys
import types
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if "flask" not in sys.modules:
    flask_stub = types.ModuleType("flask")
    class FlaskStub:
        def __init__(self, *args, **kwargs):
            self.config = {}

        def before_request(self, func):
            return func

        def after_request(self, func):
            def wrapper(response):
                return func(response)
            return wrapper

        def route(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def run(self, *args, **kwargs):
            return None

    flask_stub.Flask = FlaskStub
    flask_stub.request = types.SimpleNamespace()
    flask_stub.jsonify = lambda *args, **kwargs: None
    flask_stub.send_from_directory = lambda *args, **kwargs: None
    flask_stub.send_file = lambda *args, **kwargs: None
    sys.modules["flask"] = flask_stub

if "flask_cors" not in sys.modules:
    flask_cors_stub = types.ModuleType("flask_cors")
    flask_cors_stub.CORS = lambda *args, **kwargs: None
    sys.modules["flask_cors"] = flask_cors_stub

if "pandas" not in sys.modules:
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.Timestamp = lambda *args, **kwargs: args[0]
    pandas_stub.Timedelta = lambda *args, **kwargs: 0
    sys.modules["pandas"] = pandas_stub

if "pandas_market_calendars" not in sys.modules:
    calendar_stub = types.SimpleNamespace(
        valid_days=lambda start_date=None, end_date=None: [],
        schedule=lambda start_date=None, end_date=None: {},
    )
    pmc_stub = types.ModuleType("pandas_market_calendars")
    pmc_stub.get_calendar = lambda *args, **kwargs: calendar_stub
    sys.modules["pandas_market_calendars"] = pmc_stub

from server import backtest_server
from server.backtest_server import BacktestManager
from server.data_download.polygon_downloader import DownloadEvent, DownloadSummary
from server.data_download.polygon_client import PolygonAPIError


class StubDownloader:
    def __init__(self, status_map):
        self.status_map = status_map
        self.calls = []
        self.calendar = None

    def download(self, symbols, start, end, resolutions):
        self.calls.append((tuple(symbols), start, end, tuple(res.value for res in resolutions)))
        summary = DownloadSummary()
        for symbol in symbols:
            for resolution in resolutions:
                status = self.status_map.get(resolution.value, "downloaded")
                trading_day = start if status == "downloaded" else None
                bars = 1 if status == "downloaded" else 0
                bytes_written = 64 if status == "downloaded" else 0
                summary.add_event(
                    DownloadEvent(
                        symbol=symbol,
                        resolution=resolution,
                        trading_day=trading_day,
                        status=status,
                        bars=bars,
                        bytes_written=bytes_written,
                    )
                )
        if any(self.status_map.get(res.value, "downloaded") == "downloaded" for res in resolutions):
            summary.http_requests = 1
        return summary


class FailingDownloader:
    def __init__(self):
        self.calls = 0

    def download(self, symbols, start, end, resolutions):
        self.calls += 1
        raise PolygonAPIError("simulated failure")


class StubCalendar:
    def get_trading_days(self, start, end):
        return [start, end]


def _patch_common_dependencies(monkeypatch, *, config_symbols):
    monkeypatch.setattr(
        backtest_server,
        "load_config_strict",
        lambda path: {
            "symbols": config_symbols,
            "start_date": "2024-09-05",
            "end_date": "2024-09-06",
        },
    )
    monkeypatch.setattr(backtest_server.json, "load", lambda handle: {"polygon-api-key": "TEST"})
    monkeypatch.setattr(backtest_server, "USEquityTradingCalendar", lambda api_key=None: StubCalendar())
    monkeypatch.setattr(backtest_server.BacktestManager, "_start_lean_execution", lambda self, algo, params: None)


def test_backtest_manager_native_downloader_success(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_POLYGON_NATIVE_DOWNLOADER", "1")
    monkeypatch.setenv("POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK", "1")

    symbols = ["AAPL"]
    downloader = StubDownloader({"daily": "downloaded", "minute": "downloaded", "second": "downloaded"})

    def downloader_factory(api_key, calendar):
        downloader.calendar = calendar
        return downloader

    manager = BacktestManager(data_root=tmp_path / "data", downloader_factory=downloader_factory)

    _patch_common_dependencies(monkeypatch, config_symbols=symbols)
    monkeypatch.setattr(
        backtest_server.BacktestManager,
        "_check_data_availability",
        lambda self, *_args, **_kwargs: (False, symbols),
        raising=False,
    )

    manager._execute_backtest_sync("Algo", {})

    assert manager._last_download_method == "native"
    assert len(downloader.calls) == 3  # daily, minute, second

    extended_start = date(2023, 9, 5)
    actual_start = date(2024, 9, 5)
    actual_end = date(2024, 9, 6)

    daily_call = downloader.calls[0]
    assert daily_call[1] == extended_start
    assert daily_call[2] == actual_end
    assert daily_call[3] == ("daily",)

    second_call = downloader.calls[-1]
    assert second_call[1] == actual_start
    assert second_call[3] == ("second",)


def test_backtest_manager_native_downloader_cache_only(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_POLYGON_NATIVE_DOWNLOADER", "1")
    monkeypatch.setenv("POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK", "1")

    symbols = ["MSFT"]
    downloader = StubDownloader({"daily": "cache_hit", "minute": "cache_hit"})

    def downloader_factory(api_key, calendar):
        return downloader

    manager = BacktestManager(data_root=tmp_path / "data", downloader_factory=downloader_factory)

    _patch_common_dependencies(monkeypatch, config_symbols=symbols)
    monkeypatch.setattr(
        backtest_server.BacktestManager,
        "_check_data_availability",
        lambda self, *_args, **_kwargs: (True, []),
        raising=False,
    )

    manager._execute_backtest_sync("Algo", {})

    assert manager._last_download_method == "native"
    assert len(downloader.calls) == 2  # daily + minute
    assert manager._last_download_summary.cache_hits == 2


def test_backtest_manager_native_failure_falls_back_to_cli(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_POLYGON_NATIVE_DOWNLOADER", "1")
    monkeypatch.setenv("POLYGON_DOWNLOADER_ALLOW_CLI_FALLBACK", "1")

    symbols = ["IBM"]
    downloader = FailingDownloader()

    def downloader_factory(api_key, calendar):
        return downloader

    manager = BacktestManager(data_root=tmp_path / "data", downloader_factory=downloader_factory)

    _patch_common_dependencies(monkeypatch, config_symbols=symbols)
    monkeypatch.setattr(
        backtest_server.BacktestManager,
        "_check_data_availability",
        lambda self, *_args, **_kwargs: (False, symbols),
        raising=False,
    )

    cli_calls = {}

    def fake_cli(self, symbols_arg, start_arg, end_arg, download_symbols_arg, api_key_arg):
        cli_calls["count"] = cli_calls.get("count", 0) + 1
        self.download_start_time = datetime.now()
        self.download_end_time = self.download_start_time
        self._last_download_summary = None
        return True

    monkeypatch.setattr(backtest_server.BacktestManager, "_run_cli_download", fake_cli, raising=False)

    manager._execute_backtest_sync("Algo", {})

    assert downloader.calls == 1
    assert cli_calls.get("count") == 1
    assert manager._last_download_method == "cli_fallback"
