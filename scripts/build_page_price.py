#!/usr/bin/env python3
"""Build the price-reaction page from consensus history and unadjusted closes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import load_company, read_json, write_page  # noqa: E402
from scripts.lib.metrics import NOT_CONNECTED, beat_but_down, kpi_latest  # noqa: E402
from scripts.lib.prices import open_gap, reaction_window  # noqa: E402


def tone(p: float | None) -> str:
    if p is None:
        return "na"
    if abs(p) < 0.0005:
        return "flat"
    return "up" if p > 0 else "down"


def _surprise(actual, consensus) -> tuple[float | None, str]:
    if actual is None or not consensus:
        return None, "na"
    surp = float(actual) / float(consensus) - 1
    return surp, "up" if surp > 0 else "down" if surp < 0 else "flat"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    timing = cfg.get("release_timing", "after_close")
    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={}) or {}
    closes = prices.get("closes") or {}
    opens = prices.get("opens") or {}
    closes_adj = prices.get("closes_adj") or closes

    hist_eps = (((cons.get("history") or {}).get("eps") or {}).get("q")) or []
    hist_rev = {r.get("period"): r for r in (((cons.get("history") or {}).get("rev") or {}).get("q") or [])}
    events = []

    for row in reversed(hist_eps):
        release = row.get("release_date")
        if not release:
            continue
        window = reaction_window(closes, release, timing)
        pre = window["pre"]
        d1 = window["d1"]
        t5 = window["t5"]
        react = window["react_day"]
        if react is None and window.get("pre_day"):
            later_opens = [d for d in sorted(opens) if d > window["pre_day"]]
            react = later_opens[0] if later_opens else None
        gap = open_gap(opens, react, pre)
        eps_surp, eps_tone = _surprise(row.get("actual"), row.get("consensus"))
        rev_row = hist_rev.get(row.get("period")) or {}
        rev_surp, rev_tone = _surprise(rev_row.get("actual"), rev_row.get("consensus"))
        events.append(
            {
                "q": row["period"],
                "d": release,
                "timing": "after_close" if timing == "after_close" else "before_open",
                "rd": react,
                "pre_close": round(pre, 2) if pre else None,
                "ah": round(gap, 4) if gap is not None else None,
                "ah_tone": tone(gap),
                "ah_note": "近似（次日开盘）" if gap is not None else NOT_CONNECTED,
                "open": round(float(opens[react]), 2) if react and react in opens else None,
                "close": round(d1, 4) if d1 is not None else None,
                "close_tone": tone(d1),
                "t5": round(t5, 4) if t5 is not None else None,
                "t5_tone": tone(t5),
                "iv": None,
                "iv_note": NOT_CONNECTED,
                "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
                "eps_surp_tone": eps_tone,
                "rev_surp": round(rev_surp, 4) if rev_surp is not None else None,
                "rev_surp_tone": rev_tone,
                "guide_vs_cons": None,
                "guide_vs_cons_tone": "na",
                "note": {"text": None, "confirmed": False},
            }
        )

    def kpi(field: str) -> dict:
        latest = kpi_latest(events, field)
        vals = [e[field] for e in events if e.get(field) is not None][:8]
        if latest is None and not vals:
            return {"latest": None, "latest_tone": "na", "avg8": None, "up8": 0}
        avg = sum(vals) / len(vals) if vals else None
        up = sum(1 for v in vals if v > 0)
        return {
            "latest": round(latest, 4) if latest is not None else None,
            "latest_tone": tone(latest),
            "avg8": round(avg, 4) if avg is not None else None,
            "up8": up,
        }

    d1_vals = [e["close"] for e in events if e.get("close") is not None][:8]
    beat_n, beat_of = beat_but_down(events)
    keys = sorted(closes_adj.keys())[-180:]
    page = {
        "windows": ["ah", "d1", "d5"],
        "kpi": {
            "ah": kpi("ah"),
            "d1": kpi("close"),
            "d5": kpi("t5"),
        },
        "vol": {
            "avg_abs_move": round(sum(abs(v) for v in d1_vals) / len(d1_vals), 4) if d1_vals else None,
            "avg_iv": None,
            "iv_note": NOT_CONNECTED,
        },
        "beat_but_down": {
            "n": beat_n,
            "of": beat_of,
            "note": f"近 {beat_of} 期中，EPS 超预期且次日收跌的次数（分母只计同时有超预期和次日涨跌的期）",
        },
        "series": {"dates": keys, "close_adj": [closes_adj[k] for k in keys]},
        "events": events,
        "notes": {
            "ah": "盘后价没有分钟线快照。历史用次日开盘 / 发布前收盘 − 1，标注「近似」。",
            "t5": "T+5 = 反应日后第 5 个交易日收盘 / 发布前收盘 − 1，使用未复权价。",
            "iv": NOT_CONNECTED,
        },
    }
    write_page(f"{ticker}/price.json", page)
    print(f"wrote data/pages/{ticker}/price.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
