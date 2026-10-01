#!/usr/bin/env python3
"""Build call page from AI draft (or sample seed) + index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json, write_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="FQ4-26")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    period = args.period

    draft_path = ROOT / "ai" / "tasks" / f"{ticker}_call_{period}" / "output" / "draft.json"
    sample = read_json(ROOT / "web" / "public" / "sample" / "call.json", default={}) or {}
    if draft_path.exists():
        page = json.loads(draft_path.read_text(encoding="utf-8"))
    else:
        page = dict(sample)
        page["period"] = period
        page["ai_status"] = "awaiting_ai_prepare"

    page.setdefault("links", sample.get("links") or {})
    # Official remarks missing → explicit flag (decision #4)
    page["remarks_status"] = "准备稿未获取"
    page.setdefault(
        "banner",
        "P4 手动模式：任务包见 ai/tasks/；准备稿未获取时原文 tab 不得静默使用第三方顶替。",
    )

    out = ROOT / "data" / "pages" / ticker / "call.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "call.json", page)
    write_json(ROOT / "data" / "pages" / ticker / f"call-{period}.json", page)

    index = {
        "ticker": ticker,
        "periods": [
            {
                "period": period,
                "label": period,
                "status": page.get("status") or page.get("ai_status"),
                "href": f"#/{ticker}/call/{period}",
            }
        ],
        "latest": period,
    }
    write_json(ROOT / "data" / "pages" / ticker / "call-index.json", index)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "call-index.json", index)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
