from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence

from server.data_download.data_store import LeanDataStore
from server.data_download.lean_schema import Resolution
from server.data_download.polygon_client import PolygonAggregatorClient
from server.data_download.polygon_downloader import PolygonIncrementalDownloader
from server.trading_calendar import USEquityTradingCalendar


@dataclass
class MethodResult:
    method: str
    duration_seconds: float | None
    http_requests: int | None = None
    cache_hits: int | None = None
    downloaded_events: int | None = None
    bytes_written: int | None = None
    error: str | None = None


@dataclass
class BenchmarkReport:
    symbols: Sequence[str]
    start_date: str
    end_date: str
    resolutions: Sequence[str]
    native: MethodResult
    cli: MethodResult
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class PolygonDownloaderBenchmark:
    """Utility to compare native downloader performance against Lean CLI."""

    def __init__(
        self,
        *,
        project_root: Path,
        workspace_root: Path,
        api_key: str,
    ) -> None:
        self._project_root = project_root
        self._workspace_root = workspace_root
        self._api_key = api_key

    # ------------------------------------------------------------------ public
    def run(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        resolutions: Sequence[Resolution],
    ) -> BenchmarkReport:
        native_result = self._run_native(symbols, start, end, resolutions)
        self._reset_workspace()
        cli_result = self._run_cli(symbols, start, end, resolutions)

        timestamp = datetime.utcnow().isoformat()
        report = BenchmarkReport(
            symbols=list(symbols),
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            resolutions=[res.value for res in resolutions],
            native=native_result,
            cli=cli_result,
            timestamp=timestamp,
        )
        return report

    # ----------------------------------------------------------------- helpers
    def _workspace_lean_json(self) -> Path:
        return self._workspace_root / "lean.json"

    def bootstrap_workspace(self) -> None:
        """Copy lean.json into the workspace with data-folder pointing inside."""

        self._workspace_root.mkdir(parents=True, exist_ok=True)
        data_dir = self._workspace_root / "data"
        data_dir.mkdir(exist_ok=True)

        lean_json = self._project_root / "lean.json"
        with lean_json.open("r") as handle:
            payload = json.load(handle)

        payload["data-folder"] = str(Path("data"))
        payload["polygon-api-key"] = self._api_key

        with self._workspace_lean_json().open("w") as handle:
            json.dump(payload, handle, indent=2)

        metadata_dirs = ["market-hours", "symbol-properties"]
        for name in metadata_dirs:
            source = self._project_root / "data" / name
            if source.exists():
                shutil.copytree(source, data_dir / name, dirs_exist_ok=True)

        equity_dir = data_dir / "equity" / "usa"
        equity_dir.mkdir(parents=True, exist_ok=True)
        source_map_files = self._project_root / "data" / "equity" / "usa" / "map_files"
        if source_map_files.exists():
            shutil.copytree(source_map_files, equity_dir / "map_files", dirs_exist_ok=True)

    def _reset_workspace(self) -> None:
        data_dir = self._workspace_root / "data"
        if data_dir.exists():
            shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    def _run_native(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        resolutions: Sequence[Resolution],
    ) -> MethodResult:
        calendar = USEquityTradingCalendar(self._api_key)
        store = LeanDataStore(self._workspace_root / "data")
        client = PolygonAggregatorClient(self._api_key)
        downloader = PolygonIncrementalDownloader(
            api_key=self._api_key,
            data_store=store,
            calendar=calendar,
            client=client,
        )

        start_ts = time.perf_counter()
        summary = downloader.download(symbols, start, end, resolutions)
        duration = time.perf_counter() - start_ts

        downloaded_events = len(summary.downloaded_events())
        bytes_written = (
            sum(event.bytes_written for event in summary.downloaded_events())
            if downloaded_events
            else 0
        )

        return MethodResult(
            method="native",
            duration_seconds=round(duration, 3),
            http_requests=summary.http_requests,
            cache_hits=summary.cache_hits,
            downloaded_events=downloaded_events,
            bytes_written=bytes_written,
        )

    def _run_cli(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        resolutions: Sequence[Resolution],
    ) -> MethodResult:
        start_token = start.strftime("%Y%m%d")
        from datetime import timedelta

        end_token = end.strftime("%Y%m%d")
        cli_end_token = (end + timedelta(days=1)).strftime("%Y%m%d")
        duration_accum = 0.0
        error_message: str | None = None

        for resolution in resolutions:
            resolution_token = resolution.value.title()
            cmd = [
                "lean",
                "data",
                "download",
                "--data-provider-historical",
                "Polygon",
                "--data-type",
                "Trade",
                "--resolution",
                resolution_token,
                "--security-type",
                "Equity",
                "--ticker",
                ",".join(symbols),
                "--start",
                start_token,
                "--end",
                cli_end_token,
                "--polygon-api-key",
                self._api_key,
                "--no-update",
            ]

            start_ts = time.perf_counter()
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    text=True,
                    input="usa\n\n",
                    cwd=self._workspace_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                duration_accum += time.perf_counter() - start_ts
            except subprocess.CalledProcessError as exc:  # pragma: no cover - depends on external CLI
                error_message = exc.output.strip() if exc.output else str(exc)
                break

        return MethodResult(
            method="cli",
            duration_seconds=round(duration_accum, 3) if not error_message else None,
            error=error_message,
        )


def run_default_benchmark(
    *,
    project_root: Path,
    output_dir: Path,
    api_key: str,
) -> BenchmarkReport:
    symbols = ["AAPL"]
    today = date.today()
    calendar = USEquityTradingCalendar(api_key)
    start_day = calendar.get_previous_trading_day(today)
    if start_day is None:
        raise RuntimeError("Failed to determine previous trading day for benchmark.")

    workspace = Path(tempfile.mkdtemp(prefix="polygon-benchmark-"))
    benchmark = PolygonDownloaderBenchmark(
        project_root=project_root,
        workspace_root=workspace,
        api_key=api_key,
    )
    benchmark.bootstrap_workspace()

    resolutions = [Resolution.MINUTE]
    report = benchmark.run(symbols, start_day, start_day, resolutions)

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"benchmark_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    (output_dir / filename).write_text(report.to_json())

    return report
