#!/usr/bin/env python3
"""Merge latest Yahoo snapshot + prices into data/pages/<T>/consensus.json."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fmt import format_change, format_pct  # noqa: E402
from scripts.lib.io import load_company, read_json, write_json  # noqa: E402


def bj_now() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def latest_snapshot(ticker: str) -> dict | None:
    d = ROOT / "data" / "snapshots" / ticker
    if not d.exists():
        return None
    files = sorted(d.glob("*.json"))
    if not files:
        return None
    return read_json(files[-1])


def ntm_eps_from_snap(snap: dict) -> float | None:
    """Sum next 4 quarterly EPS averages if present; else None."""
    periods = snap.get("periods") or {}
    qs = []
    for name, slot in periods.items():
        if slot.get("type") != "q":
            continue
        avg = (slot.get("eps") or {}).get("avg")
        if avg is not None:
            qs.append((name, float(avg)))
    qs.sort(key=lambda x: x[0])
    if len(qs) < 1:
        return None
    # Prefer first up to 4 upcoming quarters in snapshot order
    vals = [v for _, v in qs[:4]]
    if len(vals) < 4:
        # incomplete NTM — still sum available and note via method
        return sum(vals) if vals else None
    return sum(vals)


def revision_note(period: str, points: list, guide: float | None) -> str:
    if not points or len(points) < 5:
        return "修正轨迹数据不足。"
    cur = points[-1][1]
    d90 = points[0][1]
    d30 = points[2][1]
    move_30 = abs((cur / d30 - 1) * 100) if d30 else 0
    early = points[1][1]
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


def apply_snapshot(page: dict, snap: dict, cfg: dict) -> None:
    periods = snap.get("periods") or {}
    guide_map = cfg.get("guidance") or {}

    # Update detail rows when matching periods exist
    for metric in ("eps", "rev"):
        for row in page.get("future", {}).get("detail", {}).get(metric) or []:
            p = row.get("period")
            if p not in periods:
                continue
            slot = periods[p]
            src = slot.get(metric) or {}
            for k in ("avg", "low", "high", "n", "year_ago"):
                if src.get(k) is not None:
                    row[k] = src[k]
            tr = slot.get("eps_trend") or {}
            if metric == "eps" and tr:
                row["trend"] = {
                    "d7": tr.get("d7"),
                    "d30": tr.get("d30"),
                    "d60": tr.get("d60"),
                    "d90": tr.get("d90"),
                }
            rev = slot.get("revisions") or {}
            if rev:
                row["revisions"] = {
                    "up30": rev.get("up30"),
                    "down30": rev.get("down30"),
                }
            g = guide_map.get(p) or {}
            if metric == "eps" and g.get("eps_mid") is not None:
                row["guide"] = g["eps_mid"]
            if metric == "rev" and g.get("rev_mid") is not None:
                row["guide"] = g["rev_mid"]

            # Patch future grid estimate cells for matching FY/FQ
            # e.g. FQ1-27 → FY27 index 0
            if p.startswith("FQ") and metric in page["future"]:
                try:
                    fq = int(p[2])
                    yy = p.split("-")[1]
                    fy_key = f"FY{yy}"
                    arr = page["future"][metric].get(fy_key)
                    if arr and 1 <= fq <= 4 and src.get("avg") is not None:
                        arr[fq - 1] = round(float(src["avg"]), 2) if metric == "eps" else round(float(src["avg"]), 2)
                except (ValueError, IndexError):
                    pass
            if p.startswith("FY") and metric in page["future"]:
                arr = page["future"][metric].get(p)
                if arr and src.get("avg") is not None:
                    arr[4] = round(float(src["avg"]), 2)

    # Revision charts from eps_trend
    for key, block in (page.get("revision") or {}).items():
        if key not in periods:
            continue
        tr = periods[key].get("eps_trend") or {}
        cur = tr.get("current") or (periods[key].get("eps") or {}).get("avg")
        if cur is None:
            continue
        points = []
        for days, k in ((90, "d90"), (60, "d60"), (30, "d30"), (7, "d7"), (0, "current")):
            v = tr.get(k) if k != "current" else cur
            if v is not None:
                points.append([days, round(float(v), 4)])
        if points:
            # oldest first for chart
            points = sorted(points, key=lambda x: -x[0] if x[0] else 0)
            # convert to days_ago descending already; chart expects oldest first with days_ago
            points = [[d, v] for d, v in sorted(points, key=lambda x: -x[0])]
            # remap: store as [[days_ago, val], ...] oldest first
            block["points"] = [[abs(d), v] for d, v in points]
        rev = periods[key].get("revisions") or {}
        if rev.get("up30") is not None:
            block["up30"] = int(rev["up30"] or 0)
        if rev.get("down30") is not None:
            block["down30"] = int(rev["down30"] or 0)
        g = (guide_map.get(key) or {}).get("eps_mid")
        block["guide"] = g
        block["note"] = revision_note(key, block.get("points") or [], g)

    ntm = ntm_eps_from_snap(snap)
    if ntm is not None:
        page["future"]["pe"]["ntm_eps"] = round(ntm, 2)
        page["future"]["pe"]["ntm_method"] = "sum_next_quarters_in_snapshot"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    page_path = ROOT / "data" / "pages" / ticker / "consensus.json"
    page = read_json(page_path)
    if page is None:
        print(f"missing curated page {page_path}", file=sys.stderr)
        return 1

    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={}) or {}
    closes = prices.get("closes") or {}
    last_close = closes[sorted(closes.keys())[-1]] if closes else None

    page["meta"]["updated_at_bj"] = bj_now()
    page["meta"]["name_en"] = cfg.get("name_en", page["meta"].get("name_en"))
    page["meta"]["name_zh"] = cfg.get("name_zh", page["meta"].get("name_zh"))
    page["future"]["pe"]["last_close"] = round(last_close, 2) if last_close else None
    if last_close:
        page["meta"]["header"]["price"] = round(last_close, 2)

    snap = latest_snapshot(ticker)
    if snap:
        apply_snapshot(page, snap, cfg)
        day = Path(sorted((ROOT / "data" / "snapshots" / ticker).glob("*.json"))[-1]).stem
        page["meta"]["snapshot_note"] = (
            f"共识快照：Yahoo {day}（绝对财期）。详情表与修正轨迹已用最新快照刷新。"
        )

    # NTM forward PE display string for header
    ntm = page["future"]["pe"].get("ntm_eps")
    if last_close and ntm and ntm > 0:
        page["meta"]["header"]["forward_pe_ntm"] = round(last_close / ntm, 1)

    hist = read_json(ROOT / "data" / "history" / f"{ticker}.json", default=None)
    if hist:
        for metric in ("eps", "rev"):
            for period in ("q", "y"):
                by_p = {r["period"]: r for r in hist.get(metric, {}).get(period, [])}
                for row in page["history"][metric][period]:
                    if row["period"] in by_p and by_p[row["period"]].get("next_day") is not None:
                        row["next_day"] = by_p[row["period"]]["next_day"]

    write_json(page_path, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "consensus.json", page)
    print(f"wrote {page_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
