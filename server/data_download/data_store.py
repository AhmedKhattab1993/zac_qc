from __future__ import annotations

import os
import tempfile
import zipfile
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List

from .lean_schema import Resolution, build_trade_csv_filename, build_trade_zip_path


class LeanDataStore:
    """Filesystem helper for reading and writing Lean trade archives."""

    def __init__(self, root: Path) -> None:
        self._root = root

    # ------------------------------------------------------------------ reads
    def intraday_days_present(
        self,
        symbol: str,
        resolution: Resolution,
    ) -> List[date]:
        """
        Return trading days with existing Lean archives for ``symbol``.

        Only minute/second resolutions are supported here.
        """

        if resolution is Resolution.DAILY:
            raise ValueError("intraday_days_present expects sub-daily resolution")

        folder = build_trade_zip_path(self._root, symbol, resolution, date.today()).parent
        if not folder.exists():
            return []

        days: List[date] = []
        for entry in folder.iterdir():
            if entry.suffix != ".zip":
                continue
            try:
                day_str = entry.stem.split("_")[0]
                day = date(
                    int(day_str[0:4]),
                    int(day_str[4:6]),
                    int(day_str[6:8]),
                )
            except (ValueError, IndexError):
                continue
            try:
                with zipfile.ZipFile(entry, "r") as archive:
                    names = archive.namelist()
                    if not names:
                        continue
                    with archive.open(names[0]) as handle:
                        if not handle.read(1):
                            continue
            except zipfile.BadZipFile:
                continue
            days.append(day)
        return sorted(days)

    def load_daily_rows(self, symbol: str) -> OrderedDict[str, str]:
        """
        Load existing daily rows keyed by ``YYYYMMDD``.

        Returns an ordered dictionary preserving chronological order.
        """

        archive_path = build_trade_zip_path(self._root, symbol, Resolution.DAILY, None)
        if not archive_path.exists():
            return OrderedDict()

        csv_name = build_trade_csv_filename(symbol, Resolution.DAILY, None)
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            if csv_name not in zip_file.namelist():
                return OrderedDict()
            raw = zip_file.read(csv_name).decode("utf-8").strip()

        rows = OrderedDict()
        if not raw:
            return rows

        for line in raw.splitlines():
            day_token = line.split(",", 1)[0].split(" ", 1)[0]
            rows[day_token] = line

        return rows

    # ------------------------------------------------------------------ writes
    def write_intraday_day(
        self,
        symbol: str,
        resolution: Resolution,
        trading_day: date,
        payload: str,
    ) -> Path:
        """Persist a single trading day's CSV payload as a Lean archive."""

        target_path = build_trade_zip_path(self._root, symbol, resolution, trading_day)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        csv_name = build_trade_csv_filename(symbol, resolution, trading_day)
        temp_file = self._create_temp_file(target_path.parent, suffix=".zip")

        try:
            with zipfile.ZipFile(temp_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(csv_name, payload)
            os.replace(temp_file, target_path)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        return target_path

    def upsert_daily_rows(
        self,
        symbol: str,
        rows: Dict[str, str],
    ) -> Path:
        """Merge ``rows`` into the symbol's daily archive."""

        archive_path = build_trade_zip_path(self._root, symbol, Resolution.DAILY, None)
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        existing_rows = self.load_daily_rows(symbol)
        existing_rows.update(rows)

        ordered_rows = OrderedDict(sorted(existing_rows.items()))
        csv_payload = "\n".join(ordered_rows.values())

        csv_name = build_trade_csv_filename(symbol, Resolution.DAILY, None)
        temp_file = self._create_temp_file(archive_path.parent, suffix=".zip")

        try:
            with zipfile.ZipFile(temp_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(csv_name, csv_payload)
            os.replace(temp_file, archive_path)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        return archive_path

    # ----------------------------------------------------------------- helpers
    def _create_temp_file(self, directory: Path, suffix: str) -> str:
        fd, temp_path = tempfile.mkstemp(dir=directory, suffix=suffix, prefix=".tmp-lean-")
        os.close(fd)
        return temp_path
