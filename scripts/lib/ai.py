"""AI manual-mode helpers: task packs under ai/tasks/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_ai_config() -> dict:
    path = ROOT / "config" / "ai.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def task_dir(ticker: str, kind: str, period: str) -> Path:
    return ROOT / "ai" / "tasks" / f"{ticker}_{kind}_{period}"


def write_task_pack(
    ticker: str,
    kind: str,
    period: str,
    *,
    prompt_file: str,
    inputs: dict[str, Any],
    schema: dict[str, Any],
) -> Path:
    d = task_dir(ticker, kind, period)
    d.mkdir(parents=True, exist_ok=True)
    (d / "input").mkdir(exist_ok=True)
    (d / "output").mkdir(exist_ok=True)
    meta = {
        "ticker": ticker,
        "kind": kind,
        "period": period,
        "provider": load_ai_config().get("provider", "manual"),
        "prompt": prompt_file,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready_for_cursor",
        "instruction": (
            "手动模式：用 Cursor 打开 prompt，阅读 input/，按 schema 写出 output/draft.json，"
            "再运行 python3 scripts/ai_check.py --task "
            f"{ticker}_{kind}_{period}"
        ),
    }
    (d / "task.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / "schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, payload in inputs.items():
        p = d / "input" / name
        if isinstance(payload, (dict, list)):
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            p.write_text(str(payload), encoding="utf-8")
    return d
