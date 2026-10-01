#!/usr/bin/env python3
"""Build price reaction page from consensus history + daily closes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import load_company, read_json, write_json  # noqa: E402


def tone(p: float | None) -> str:
    if p is None:
        return "na"
    if abs(p) < 0.0005:
        return "flat"
    return "up" if p > 0 else "down"


def next_day(closes: dict, release: str, timing: str) -> tuple[float | None, str | None, float | None]:
    days = sorted(closes.keys())
    prior = [d for d in days if d <= release]
    if not prior:
        return None, None, None
    rd = prior[-1]
    idx = days.index(rd)
    pre = closes[rd]
    if timing == "after_close":
        if idx + 1 >= len(days):
            return pre, None, None
        t1 = days[idx + 1]
        return pre, t1, closes[t1] / pre - 1 if pre else None
    if idx == 0:
        return pre, rd, None
    return closes[days[idx - 1]], rd, pre / closes[days[idx - 1]] - 1 if closes[days[idx - 1]] else None


def t_plus_n(closes: dict, start: str, n: int) -> float | None:
    days = sorted(closes.keys())
    if start not in days:
        prior = [d for d in days if d >= start]
        if not prior:
            return None
        start = prior[0]
    if start not in days:
        return None
    idx = days.index(start)
    if idx + n >= len(days) or idx < 0:
        return None
    a, b = closes[days[idx]], closes[days[idx + n]]
    return b / a - 1 if a else None


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

    hist = (((cons.get("history") or {}).get("eps") or {}).get("q")) or []
    events = []
    d1_list = []
    d5_list = []
    beat_down = 0
    beat_n = 0

    for row in reversed(hist[-12:]):
        release = row.get("release_date")
        if not release:
            continue
        pre, rd, d1 = next_day(closes, release, timing)
        t5 = t_plus_n(closes, rd or release, 5) if rd else None
        surp = None
        st = "na"
        if row.get("actual") is not None and row.get("consensus"):
            surp = row["actual"] / row["consensus"] - 1
            st = "up" if surp > 0 else "down"
            beat_n += 1
            if surp > 0 and d1 is not None and d1 < 0:
                beat_down += 1
        if d1 is not None:
            d1_list.append(d1)
        if t5 is not None:
            d5_list.append(t5)
        events.append(
            {
                "q": row["period"],
                "d": release,
                "timing": "after_close" if timing == "after_close" else "before_open",
                "rd": rd,
                "pre_close": round(pre, 2) if pre else None,
                "ah": None,
                "ah_tone": "na",
                "ah_note": "none",
                "open": None,
                "close": round(d1, 4) if d1 is not None else None,
                "close_tone": tone(d1),
                "t5": round(t5, 4) if t5 is not None else None,
                "t5_tone": tone(t5),
                "iv": None,
                "eps_surp": round(surp, 4) if surp is not None else None,
                "eps_surp_tone": st,
                "rev_surp": None,
                "rev_surp_tone": "na",
                "guide_vs_cons": None,
                "guide_vs_cons_tone": "na",
                "note": {"text": None, "confirmed": False},
            }
        )

    def kpi(vals: list[float]) -> dict:
        if not vals:
            return {"latest": None, "latest_tone": "na", "avg8": None, "up8": None}
        latest = vals[0]
        window = vals[:8]
        avg = sum(window) / len(window)
        up = sum(1 for v in window if v > 0)
        return {
            "latest": round(latest, 4),
            "latest_tone": tone(latest),
            "avg8": round(avg, 4),
            "up8": up,
        }

    # price series last ~180 trading days
    keys = sorted(closes.keys())[-180:]
    page = {
        "windows": ["ah", "d1", "d5"],
        "kpi": {
            "ah": {"latest": None, "latest_tone": "na", "avg8": None, "up8": None},
            "d1": kpi(d1_list),
            "d5": kpi(d5_list),
        },
        "vol": {
            "avg_abs_move": round(sum(abs(v) for v in d1_list[:8]) / min(8, len(d1_list)), 4)
            if d1_list
            else None,
            "avg_iv": None,
        },
        "beat_but_down": {
            "n": beat_down if beat_n else None,
            "of": min(8, beat_n) if beat_n else 8,
            "note": "近 8 季中 EPS 超预期但次日下跌的次数（盘后发布按次日收盘计）",
        },
        "series": {"dates": keys, "close_adj": [closes[k] for k in keys]},
        "events": events,
    }
    out = ROOT / "data" / "pages" / ticker / "price.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "price.json", page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
