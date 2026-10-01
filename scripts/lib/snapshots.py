"""Dated consensus snapshots. Secondary dumps must not sort after them."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.lib.io import ROOT, read_json

_DATED = re.compile(r"\d{4}-\d{2}-\d{2}")


def is_dated_snapshot(path: Path) -> bool:
    return _DATED.fullmatch(path.stem) is not None


def snapshot_files(ticker: str) -> list[Path]:
    d = ROOT / "data" / "snapshots" / ticker.upper()
    if not d.exists():
        return []
    return sorted(p for p in d.glob("*.json") if is_dated_snapshot(p))


def latest_snapshot_path(ticker: str) -> Path | None:
    files = snapshot_files(ticker)
    return files[-1] if files else None


def latest_snapshot(ticker: str) -> dict | None:
    path = latest_snapshot_path(ticker)
    if path is None:
        return None
    return read_json(path)
