import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.polygon_downloader_benchmark import run_default_benchmark


@pytest.mark.live
def test_polygon_downloader_benchmark_live(tmp_path):
    if not os.environ.get("RUN_POLYGON_BENCHMARKS"):
        pytest.skip("Set RUN_POLYGON_BENCHMARKS=1 to execute live downloader benchmark.")

    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        lean_path = PROJECT_ROOT / "lean.json"
        if lean_path.exists():
            with lean_path.open("r") as handle:
                api_key = json.load(handle).get("polygon-api-key")
    if not api_key:
        pytest.fail("Polygon API key required for downloader benchmark.")

    report = run_default_benchmark(
        project_root=PROJECT_ROOT,
        output_dir=PROJECT_ROOT
        / "tasks"
        / "polygon-incremental-data-downloader-20251016T075149Z"
        / "benchmarks",
        api_key=api_key,
    )

    if report.cli.error:
        pytest.skip(f"CLI benchmark unavailable: {report.cli.error}")

    assert report.native.duration_seconds is not None
    assert report.cli.duration_seconds is not None
    assert report.native.duration_seconds <= report.cli.duration_seconds
    assert report.native.http_requests is not None
