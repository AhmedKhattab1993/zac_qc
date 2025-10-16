#!/usr/bin/env python3
"""
Benchmark harness for ZacQC Lean backtests.

Features:
- Runs Lean backtests with deterministic configuration.
- Captures wall-clock/CPU timings via /usr/bin/time -l alongside Python timers.
- Archives Lean outputs (summary, order events, logs) under the feature task directory.
- Computes aggregate statistics (min/median/max) and optional speedup vs baseline.
- Attempts to enforce single-core execution (best effort; logged if unavailable).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


FEATURE_SLUG = "zacqc-backtest-speedup-20251015T215526Z"
DEFAULT_PROJECT_PATH = "ZacQC"
BASELINE_LABEL = "baseline"


def resolve_paths(script_path: Path) -> Tuple[Path, Path, Path]:
    """Return (feature_dir, repo_root, tasks_dir)."""
    feature_dir = script_path.resolve().parents[1]
    tasks_dir = feature_dir.parent
    repo_root = tasks_dir.parent
    return feature_dir, repo_root, tasks_dir


def sanitize_key(raw_key: str) -> str:
    """Sanitize resource usage key for JSON storage."""
    key = raw_key.strip().lower().replace("/", "_per_")
    key = key.replace("%", "pct")
    return "_".join(part for part in key.split() if part)


def parse_time_output(path: Path) -> Dict[str, float]:
    """Parse /usr/bin/time -l output into a dict while storing raw lines."""
    metrics: Dict[str, float] = {"raw_log_path": str(path)}
    if not path.exists():
        metrics["parse_error"] = "time_output_missing"
        return metrics

    lines = path.read_text().splitlines()
    metrics["raw_lines"] = lines

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        if len(tokens) >= 2 and tokens[1] == "real":
            # Format: "<real> real <user> user <sys> sys"
            try:
                metrics["real_time_seconds"] = float(tokens[0])
                metrics["user_time_seconds"] = float(tokens[2])
                metrics["sys_time_seconds"] = float(tokens[4])
            except (IndexError, ValueError):
                metrics["parse_warning"] = "failed_real_line_parse"
            continue

        key = sanitize_key(" ".join(tokens[1:]))
        value_token = tokens[0]
        try:
            value = float(value_token) if "." in value_token else int(value_token)
        except ValueError:
            value = value_token
        metrics[key] = value

    return metrics


def attempt_single_core_prefix() -> Tuple[List[str], str]:
    """
    Attempt to build a command prefix enforcing single-core execution.
    Returns (prefix_list, status_message).
    """
    import shutil as _shutil  # local import to avoid unused warning if not needed

    taskset_path = _shutil.which("taskset")
    if taskset_path:
        return ([taskset_path, "-c", "0"], "taskset")

    # macOS and other BSD variants typically lack sched_setaffinity/taskset.
    # We fall back to documenting the limitation; algorithm is still single-threaded logically.
    return ([], "unavailable")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_if_exists(src: Optional[Path], dest: Path) -> Optional[str]:
    if src and src.exists():
        ensure_dir(dest.parent)
        shutil.copy2(src, dest)
        return str(dest)
    return None


def locate_first(path: Path, pattern: str) -> Optional[Path]:
    matches = sorted(path.rglob(pattern))
    return matches[0] if matches else None


def load_existing_metrics(feature_dir: Path, label: str) -> Optional[Dict]:
    metrics_path = feature_dir / "benchmarks" / label / "latest.json"
    if metrics_path.exists():
        with metrics_path.open() as handle:
            return json.load(handle)
    return None


def aggregate_runs(runs: List[Dict]) -> Dict:
    wall_times: List[float] = []
    fallback_wall_times: List[float] = []
    for run in runs:
        timing = run.get("timing", {})
        real_val = timing.get("real_time_seconds")
        if real_val is not None:
            wall_times.append(real_val)
        fallback_val = timing.get("python_wall_time_seconds")
        if fallback_val is not None:
            fallback_wall_times.append(fallback_val)

    if not wall_times and fallback_wall_times:
        wall_times = fallback_wall_times.copy()

    if not wall_times:
        return {"runs": len(runs), "wall_time_seconds": {}}

    summary = {
        "runs": len(runs),
        "wall_time_seconds": {
            "min": min(wall_times),
            "max": max(wall_times),
            "median": statistics.median(wall_times),
            "mean": statistics.mean(wall_times),
        },
    }
    return summary


def compute_speedup(current: Dict, baseline: Dict) -> Dict:
    cur = current["summary"]["wall_time_seconds"]["median"]
    base = baseline["summary"]["wall_time_seconds"]["median"]
    if base <= 0:
        return {"baseline_median": base, "current_median": cur, "speedup_pct": None, "meets_target": None}
    speedup_pct = (1 - (cur / base)) * 100
    meets = speedup_pct >= 25.0
    return {
        "baseline_median": base,
        "current_median": cur,
        "speedup_pct": speedup_pct,
        "meets_target": meets,
    }


def describe_single_core(status: str) -> str:
    if status == "taskset":
        return "Enforced via taskset -c 0"
    if status == "unavailable":
        return (
            "Single-core affinity not available on this host; "
            "set environment NUM_*_THREADS=1 for libraries (applied) and documented limitation."
        )
    return status


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run ZacQC Lean backtest benchmarks and archive metrics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--label", default=BASELINE_LABEL, help="Benchmark label (e.g., baseline, optimized)")
    parser.add_argument("--project", default=DEFAULT_PROJECT_PATH, help="Path to Lean project (relative to repo root)")
    parser.add_argument("--runs", type=int, default=3, help="Number of repeated executions")
    parser.add_argument("--lean-config", default=None, help="Optional lean.json override")
    parser.add_argument("--extra-lean-args", nargs=argparse.REMAINDER, help="Additional arguments passed to `lean backtest`")
    parser.add_argument("--no-single-core", action="store_true", help="Skip attempts to enforce single-core execution")
    args = parser.parse_args(argv)

    script_path = Path(__file__)
    feature_dir, repo_root, _ = resolve_paths(script_path)

    benchmarks_dir = feature_dir / "benchmarks" / args.label
    runs_root = feature_dir / "runs" / args.label
    ensure_dir(benchmarks_dir)
    ensure_dir(runs_root)

    batch_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    batch_dir = runs_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)

    project_path = Path(args.project)
    if not project_path.is_absolute():
        project_path = (repo_root / project_path).resolve()
    if not project_path.exists():
        print(f"[ERROR] Project path not found: {project_path}", file=sys.stderr)
        return 2

    lean_args = ["lean", "backtest", str(project_path)]
    if args.lean_config:
        lean_args.extend(["--lean-config", args.lean_config])
    lean_args.append("--no-update")

    single_core_status = "skipped" if args.no_single_core else "pending"

    env = os.environ.copy()
    # Hint to common math libraries to stay single threaded.
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    env.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    env.setdefault("NUMEXPR_NUM_THREADS", "1")

    cmd_prefix: List[str] = []
    if not args.no_single_core:
        cmd_prefix, single_core_status = attempt_single_core_prefix()

    if args.extra_lean_args:
        lean_args.extend(args.extra_lean_args)

    run_records: List[Dict] = []

    for run_index in range(1, args.runs + 1):
        run_dir = batch_dir / f"run_{run_index:02d}"
        run_dir.mkdir(parents=True, exist_ok=False)

        lean_output_dir = run_dir / "lean-output"
        lean_output_dir.mkdir()

        stdout_path = run_dir / "lean.stdout.log"
        stderr_path = run_dir / "lean.stderr.log"
        time_output_path = run_dir / "time.txt"

        run_lean_args = list(cmd_prefix) + [
            "/usr/bin/time",
            "-l",
            "-o",
            str(time_output_path),
        ] + lean_args + ["--output", str(lean_output_dir)]

        start_wall = time.perf_counter()
        with stdout_path.open("w") as stdout_file, stderr_path.open("w") as stderr_file:
            completed = subprocess.run(
                run_lean_args,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=repo_root,
                env=env,
            )
        end_wall = time.perf_counter()

        timing = parse_time_output(time_output_path)
        timing["python_wall_time_seconds"] = end_wall - start_wall

        summary_src = locate_first(lean_output_dir, "*-summary.json")
        orders_src = locate_first(lean_output_dir, "*-order-events.json")
        log_src = locate_first(lean_output_dir, "log.txt")

        summary_dest = run_dir / "summary.json"
        orders_dest = run_dir / "order-events.json"
        log_dest = run_dir / "lean.log.txt"

        copy_if_exists(summary_src, summary_dest)
        copy_if_exists(orders_src, orders_dest)
        copy_if_exists(log_src, log_dest)

        run_records.append(
            {
                "run_index": run_index,
                "started_at_utc": datetime.utcnow().isoformat() + "Z",
                "exit_code": completed.returncode,
                "timing": timing,
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "lean_output_dir": str(lean_output_dir),
                "summary_path": str(summary_dest) if summary_dest.exists() else None,
                "order_events_path": str(orders_dest) if orders_dest.exists() else None,
                "lean_log_path": str(log_dest) if log_dest.exists() else None,
            }
        )

        if completed.returncode != 0:
            print(
                textwrap.dedent(
                    f"""
                    [WARN] Run {run_index} exited with code {completed.returncode}.
                    Check logs under {run_dir}.
                    """
                ).strip()
            )

    summary = aggregate_runs(run_records)

    metrics_payload = {
        "label": args.label,
        "batch_id": batch_id,
        "project": str(project_path),
        "runs_dir": str(batch_dir),
        "single_core": describe_single_core(single_core_status),
        "summary": summary,
        "runs": run_records,
    }

    if args.label != BASELINE_LABEL:
        baseline_metrics = load_existing_metrics(feature_dir, BASELINE_LABEL)
        if baseline_metrics:
            metrics_payload["baseline_comparison"] = compute_speedup(metrics_payload, baseline_metrics)
        else:
            metrics_payload["baseline_comparison"] = {"error": "baseline_metrics_not_found"}

    latest_path = benchmarks_dir / "latest.json"
    archive_path = benchmarks_dir / f"{batch_id}.json"

    ensure_dir(latest_path.parent)
    with archive_path.open("w") as archive_file:
        json.dump(metrics_payload, archive_file, indent=2)
    with latest_path.open("w") as latest_file:
        json.dump(metrics_payload, latest_file, indent=2)

    print(f"[INFO] Completed {args.runs} run(s). Metrics saved to {archive_path}")
    print(json.dumps(metrics_payload["summary"], indent=2))

    if args.label != BASELINE_LABEL and "baseline_comparison" in metrics_payload:
        print("[INFO] Baseline comparison:")
        print(json.dumps(metrics_payload["baseline_comparison"], indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
