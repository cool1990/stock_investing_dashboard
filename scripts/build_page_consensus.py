#!/usr/bin/env python3
"""Aggregate snapshots/actuals/history into data/pages/<T>/consensus.json.

Until live snapshots accumulate, preserves the curated sample page and only
refreshes notes / PE last_close / revision notes from rules.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fmt import format_pct  # noqa: E402
from scripts.lib.io import load_company, read_json, write_json  # noqa: E402


def revision_note(period: str, points: list, guide: float | None) -> str:
    """Generate Chinese footnote from revision trajectory rules."""
    if not points or len(points) < 5:
        return "修正轨迹数据不足。"
    # points: [[days_ago, value], ...] oldest first
    cur = points[-1][1]
    d90 = points[0][1]
    d30 = points[2][1]
    move_90 = (cur / d90 - 1) * 100 if d90 else 0
    move_30 = abs((cur / d30 - 1) * 100) if d30 else 0
    early = points[1][1]  # ~60d

    lines = []
    if abs((early / d90 - 1) * 100) > abs(move_30) + 5:
        lines.append(
            f"大部分上修发生在 60–90 天前（${d90:.2f} → ${early:.2f}），之后走势放缓。"
        )
    if move_30 < 1 and guide is not None and cur < guide:
        lines.append("近 30 天修正 < 1% 且共识低于指引 → 共识尚未消化指引。")
    elif move_30 < 1:
        lines.append("近 30 天修正很小，上修动能减弱。")
    if guide is not None:
        lines.append(f"公司指引中值 ${guide:.2f}，当前共识 {format_pct(cur, guide)}。")
    else:
        lines.append(f"{period} 无公司指引（美光通常只给下一季）。")
    lines.append(f"90 天累计修正 {format_pct(cur, d90)}。")
    return "".join(lines)


def bj_now() -> str:
    utc = datetime.now(timezone.utc)
    bj = utc + timedelta(hours=8)
    return bj.strftime("%Y-%m-%d %H:%M")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    page_path = ROOT / "data" / "pages" / ticker / "consensus.json"
    page = read_json(page_path)
    if page is None:
        print(f"missing curated page {page_path}; abort to avoid empty overwrite", file=sys.stderr)
        return 1

    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={})
    closes = prices.get("closes") or {}
    last_close = None
    if closes:
        last_close = closes[sorted(closes.keys())[-1]]

    page["meta"]["updated_at_bj"] = bj_now()
    page["meta"]["name_en"] = cfg.get("name_en", page["meta"].get("name_en"))
    page["meta"]["name_zh"] = cfg.get("name_zh", page["meta"].get("name_zh"))
    page["future"]["pe"]["last_close"] = last_close
    if last_close:
        page["meta"]["header"]["price"] = round(last_close, 2)

    # Refresh revision notes from rules
    for key, block in page.get("revision", {}).items():
        block["note"] = revision_note(key, block.get("points") or [], block.get("guide"))

    # Merge history next_day if available
    hist = read_json(ROOT / "data" / "history" / f"{ticker}.json", default=None)
    if hist:
        for metric in ("eps", "rev"):
            for period in ("q", "y"):
                by_p = {r["period"]: r for r in hist.get(metric, {}).get(period, [])}
                for row in page["history"][metric][period]:
                    if row["period"] in by_p and by_p[row["period"]].get("next_day") is not None:
                        row["next_day"] = by_p[row["period"]]["next_day"]

    write_json(page_path, page)
    # Mirror into web/public for local vite
    public = ROOT / "web" / "public" / "data" / "pages" / ticker / "consensus.json"
    write_json(public, page)
    print(f"wrote {page_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
