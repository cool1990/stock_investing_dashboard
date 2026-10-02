"""Shared IO helpers for data scripts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml

ROOT = Path(__file__).resolve().parents[2]
T = TypeVar("T")


def load_company(ticker: str) -> dict[str, Any]:
    path = ROOT / "config" / "companies" / f"{ticker.upper()}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_page(rel: str, data: Any) -> None:
    """Write a page JSON to both ``data/pages`` and the dev-server copy."""
    rel_path = Path(rel)
    write_json(ROOT / "data" / "pages" / rel_path, data)
    write_json(ROOT / "web" / "public" / "data" / "pages" / rel_path, data)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def update_status(source: str, ok: bool, message: str = "") -> None:
    status_path = ROOT / "data" / "_status.json"
    status = read_json(status_path, default={"sources": {}})
    status.setdefault("sources", {})
    status["sources"][source] = {
        "ok": ok,
        "message": message,
        "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_json(status_path, status)


def retry(fn: Callable[[], T], attempts: int = 3, base_delay: float = 1.5) -> T:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2**i))
    assert last is not None
    raise last
