#!/usr/bin/env python3
"""Build history rows: pre-release consensus, surprise, next-day move, dual-source warn."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import load_company, read_json, write_json  # noqa: E402


def _finite(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or abs(x) == float("inf"):
        return None
    return x


def next_day_move(closes: dict, release_date: str, timing: str) -> float | None:
    days = sorted(closes.keys())
    if release_date not in closes and release_date not in days:
        # find nearest trading day on/before release
        prior = [d for d in days if d <= release_date]
        if not prior:
            return None
        release_date = prior[-1]
    if release_date not in closes:
        return None
    idx = days.index(release_date) if release_date in days else -1
    if idx < 0:
        return None
    if timing == "after_close":
        if idx + 1 >= len(days):
            return None
        t = _finite(closes[days[idx]])
        t1 = _finite(closes[days[idx + 1]])
        if t is None or t1 is None or t == 0:
            return None
        return t1 / t - 1
    # before open: T close / T-1 close - 1
    if idx == 0:
        return None
    t = _finite(closes[days[idx]])
    tm1 = _finite(closes[days[idx - 1]])
    if t is None or tm1 is None or tm1 == 0:
        return None
    return t / tm1 - 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    actuals = read_json(ROOT / "data" / "actuals" / f"{ticker}.json", default={})
    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={"closes": {}})
    page = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default=None)

    # Prefer curated history already in page JSON for MU sample; enrich next_day when prices exist
    history = {
        "eps": {"q": [], "y": []},
        "rev": {"q": [], "y": []},
        "meta": {"ticker": ticker},
    }

    if page and "history" in page:
        for metric in ("eps", "rev"):
            for period in ("q", "y"):
                rows = []
                for r in page["history"][metric][period]:
                    row = dict(r)
                    if _finite(row.get("next_day")) is None and row.get("release_date"):
                        row["next_day"] = next_day_move(
                            prices.get("closes", {}),
                            row["release_date"],
                            cfg.get("release_timing", "after_close"),
                        )
                    else:
                        row["next_day"] = _finite(row.get("next_day"))
                    rows.append(row)
                history[metric][period] = rows
    else:
        # Fallback: build from actuals.quarters if curated labels exist
        for period, vals in (actuals.get("quarters") or {}).items():
            history["eps"]["q"].append(
                {
                    "period": period,
                    "release_date": vals.get("release_date"),
                    "consensus": vals.get("eps_estimate"),
                    "actual": vals.get("eps"),
                    "guide": None,
                    "next_day": None,
                    "secondary": None,
                    "pre_release_source": vals.get("source", "yahoo_fallback"),
                }
            )

    out = ROOT / "data" / "history" / f"{ticker}.json"
    write_json(out, history)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
