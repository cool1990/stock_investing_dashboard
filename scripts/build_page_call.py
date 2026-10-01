#!/usr/bin/env python3
"""Build the call page. Sample transcripts are never presented as official."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import parse_period_label  # noqa: E402
from scripts.lib.io import read_json, write_json, write_page  # noqa: E402
from scripts.lib.metrics import NOT_CONNECTED  # noqa: E402


def empty_page(period: str) -> dict:
    return {
        "period": period,
        "date_et": None,
        "duration_min": None,
        "status": "not_connected",
        "ai_status": "not_connected",
        "content_origin": "not_connected",
        "links": {"remarks_pdf": None, "webcast": None, "third_party": None},
        "executives": [],
        "guidance": [],
        "prev_period": "",
        "speakers": [],
        "qa_topics": [],
        "qa": [],
        "transcript": {"sources": [], "paras": []},
        "banner": "电话会原文、时长与 AI 摘要未接入。此页不使用样例稿。",
        "remarks_status": NOT_CONNECTED,
    }


def usable_draft(draft: dict) -> bool:
    origin = str(draft.get("origin") or draft.get("content_origin") or "")
    status = str(draft.get("ai_status") or draft.get("status") or "")
    if origin == "reviewed":
        return True
    if "sample" in status or "seed" in status or status == "official_transcript":
        return False
    return False


def latest_period(ticker: str) -> str:
    fin = read_json(ROOT / "data" / "financials" / f"{ticker}.json", default={}) or {}
    periods = [
        p
        for p, slot in (fin.get("periods") or {}).items()
        if (slot.get("q") or {}).get("revenue") is not None
    ]
    if not periods:
        return ""
    return sorted(periods, key=parse_period_label)[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    period = args.period or latest_period(ticker)
    if not period:
        print(f"no period for {ticker} call page", file=sys.stderr)
        return 1

    draft_path = ROOT / "ai" / "tasks" / f"{ticker}_call_{period}" / "output" / "draft.json"
    page = empty_page(period)
    if draft_path.exists():
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        if usable_draft(draft):
            page = draft
            page["period"] = period
            page["content_origin"] = "reviewed"
        else:
            page["banner"] = "已有任务包草稿，但 origin 不是 reviewed，因此不展示为电话会原文。"

    write_page(f"{ticker}/call.json", page)
    write_json(ROOT / "data" / "pages" / ticker / f"call-{period}.json", page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / f"call-{period}.json", page)
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
    print(f"wrote call {ticker} {period} origin={page.get('content_origin')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
