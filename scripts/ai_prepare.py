#!/usr/bin/env python3
"""Prepare manual AI task packs (default: latest call + review summary)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.ai import write_task_pack  # noqa: E402
from scripts.lib.io import read_json  # noqa: E402


CALL_SCHEMA = {
    "type": "object",
    "required": ["period", "speakers", "qa"],
    "properties": {
        "period": {"type": "string"},
        "speakers": {"type": "array"},
        "qa": {"type": "array"},
        "guidance": {"type": "array"},
    },
}

REVIEW_SCHEMA = {
    "type": "object",
    "required": ["period", "summary"],
    "properties": {
        "period": {"type": "string"},
        "summary": {"type": "object"},
        "watch": {"type": "array"},
        "talk": {"type": "object"},
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="")
    parser.add_argument("--kind", choices=["call", "review", "both"], default="both")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    review = read_json(ROOT / "data" / "pages" / ticker / "review.json", default={}) or {}
    period = args.period or review.get("period") or ""
    if not period:
        print(f"no review period for {ticker}; skip AI pack", file=sys.stderr)
        return 0

    written = []
    if args.kind in ("call", "both"):
        d = write_task_pack(
            ticker,
            "call",
            period,
            prompt_file="scripts/prompts/call_v1.md",
            inputs={
                "review_numbers.json": {
                    "period": period,
                    "cards": review.get("cards"),
                    "guidance": review.get("guidance"),
                },
                "notes.txt": (
                    "准备稿未获取时不得把第三方文字稿当作官方准备稿。\n"
                    "输出中文摘要；每条要点带 src 页码或时间戳占位。\n"
                ),
            },
            schema=CALL_SCHEMA,
        )
        written.append(str(d))

    if args.kind in ("review", "both"):
        d = write_task_pack(
            ticker,
            "review",
            period,
            prompt_file="scripts/prompts/review_summary_v2.md",
            inputs={
                "numbers.json": {
                    "period": period,
                    "verdict_line": (review.get("verdict") or {}).get("line"),
                    "cards": review.get("cards"),
                },
                "notes.txt": "根据数字写 2–4 句中文总结，禁止编造未提供的数字；引用 press 原文短句。\n",
            },
            schema=REVIEW_SCHEMA,
        )
        written.append(str(d))

    for w in written:
        print(f"prepared {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
