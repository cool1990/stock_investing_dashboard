#!/usr/bin/env python3
"""Fetch Yahoo consensus into an immutable daily snapshot."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.anchor import resolve_reported_through  # noqa: E402
from scripts.lib.fiscal import FiscalCalendar, yahoo_relative_to_absolute  # noqa: E402
from scripts.lib.io import load_company, retry, update_status, write_json  # noqa: E402


def _num(v):
    if v is None:
        return None
    try:
        if hasattr(v, "item"):
            v = v.item()
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_yahoo(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)

    def get_ee():
        return t.earnings_estimate

    def get_re():
        return t.revenue_estimate

    def get_trend():
        return t.eps_trend

    def get_rev():
        return t.eps_revisions

    ee = retry(get_ee)
    re = retry(get_re)
    trend = retry(get_trend)
    revisions = retry(get_rev)

    cfg = load_company(ticker)
    cal = FiscalCalendar(list(cfg["fiscal"]["quarter_end_months"]))
    as_of = datetime.now(timezone.utc).date()
    year_ago_0q = None
    if ee is not None and "0q" in getattr(ee, "index", []):
        year_ago_0q = _num(ee.loc["0q"].get("yearAgoEps"))
    reported_through, period_method = resolve_reported_through(
        ticker, cal, as_of, year_ago_0q
    )

    periods: dict = {}

    def ensure(period: str, ptype: str) -> dict:
        periods.setdefault(
            period,
            {
                "type": ptype,
                "eps": {},
                "rev": {},
                "eps_trend": {},
                "revisions": {},
            },
        )
        return periods[period]

    for label in ("0q", "+1q", "0y", "+1y"):
        end = None
        if ee is not None and label in ee.index:
            row = ee.loc[label]
            end = row.get("period") or row.get("endDate") or None
            try:
                if end is not None and hasattr(end, "date"):
                    end = end.date()
            except Exception:  # noqa: BLE001
                end = None
            period = yahoo_relative_to_absolute(
                cal, label, as_of, end_date=end, reported_through=reported_through
            )
            ptype = "q" if label.endswith("q") else "y"
            slot = ensure(period, ptype)
            slot["eps"] = {
                "avg": _num(row.get("avg")),
                "low": _num(row.get("low")),
                "high": _num(row.get("high")),
                "n": int(row.get("numberOfAnalysts") or row.get("yearAgoEps") or 0) or _num(row.get("numberOfAnalysts")),
                "year_ago": _num(row.get("yearAgoEps")),
            }
            # fix n extraction
            n = row.get("numberOfAnalysts")
            slot["eps"]["n"] = int(n) if n is not None and str(n) != "nan" else None

        if re is not None and label in re.index:
            row = re.loc[label]
            end = row.get("period") or row.get("endDate") or end
            try:
                if end is not None and hasattr(end, "date"):
                    end = end.date()
            except Exception:  # noqa: BLE001
                pass
            period = yahoo_relative_to_absolute(
                cal, label, as_of, end_date=end, reported_through=reported_through
            )
            ptype = "q" if label.endswith("q") else "y"
            slot = ensure(period, ptype)
            # Yahoo revenue often in absolute dollars
            def to_b(x):
                n = _num(x)
                if n is None:
                    return None
                return round(n / 1e9, 2) if n > 1e6 else round(n, 2)

            n = row.get("numberOfAnalysts")
            slot["rev"] = {
                "avg": to_b(row.get("avg")),
                "low": to_b(row.get("low")),
                "high": to_b(row.get("high")),
                "n": int(n) if n is not None and str(n) != "nan" else None,
                "year_ago": to_b(row.get("yearAgoRevenue")),
            }

        if trend is not None and label in trend.index:
            row = trend.loc[label]
            period = yahoo_relative_to_absolute(
                cal, label, as_of, end_date=end, reported_through=reported_through
            )
            ptype = "q" if label.endswith("q") else "y"
            slot = ensure(period, ptype)
            slot["eps_trend"] = {
                "d7": _num(row.get("7daysAgo")),
                "d30": _num(row.get("30daysAgo")),
                "d60": _num(row.get("60daysAgo")),
                "d90": _num(row.get("90daysAgo")),
                "current": _num(row.get("current")),
            }

        if revisions is not None and label in revisions.index:
            row = revisions.loc[label]
            period = yahoo_relative_to_absolute(
                cal, label, as_of, end_date=end, reported_through=reported_through
            )
            ptype = "q" if label.endswith("q") else "y"
            slot = ensure(period, ptype)
            slot["revisions"] = {
                "up7": _num(row.get("upLast7days")),
                "up30": _num(row.get("upLast30days")),
                "down7": _num(row.get("downLast7Days") or row.get("downLast7days")),
                "down30": _num(row.get("downLast30days")),
            }

    return {
        "ticker": ticker.upper(),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "yahoo",
        "period_method": period_method,
        "reported_through": reported_through,
        "price_close": None,
        "periods": periods,
        "secondary": {"source": "nasdaq", "periods": {}},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    try:
        snap = fetch_yahoo(ticker)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = ROOT / "data" / "snapshots" / ticker / f"{day}.json"
        if out.exists():
            # immutable: do not overwrite; write side copy with time suffix only if changed
            print(f"snapshot already exists: {out}")
        else:
            write_json(out, snap)
            print(f"wrote {out}")
        update_status("yahoo_consensus", True, f"{ticker} periods={len(snap['periods'])}")
        return 0
    except Exception as e:  # noqa: BLE001
        update_status("yahoo_consensus", False, str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
