#!/usr/bin/env python3
"""Fetch daily close prices + key quote info for StockHeader."""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import retry, update_status, write_json  # noqa: E402
from scripts.lib.prices import dividend_yield_percent, drop_incomplete_session  # noqa: E402


def fetch_prices(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)
    # Unadjusted OHLC for reaction math; Adj Close for the chart (splits).
    hist = retry(lambda: t.history(period="max", auto_adjust=False))
    closes: dict[str, float] = {}
    closes_adj: dict[str, float] = {}
    opens: dict[str, float] = {}
    if hist is not None and not hist.empty:
        for idx, row in hist.iterrows():
            try:
                d = idx.tz_convert("America/New_York").date().isoformat()
            except Exception:  # noqa: BLE001
                d = str(idx)[:10]
            close = float(row["Close"])
            if not math.isfinite(close):
                continue
            closes[d] = round(close, 4)
            if "Open" in row:
                op = float(row["Open"])
                if math.isfinite(op):
                    opens[d] = round(op, 4)
            adj = None
            for col in ("Adj Close", "AdjClose"):
                if col in row:
                    try:
                        cand = float(row[col])
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(cand):
                        adj = cand
                        break
            closes_adj[d] = round(adj, 4) if adj is not None else closes[d]
    now_et = datetime.now(ZoneInfo("America/New_York"))
    # An unfinished session is not a close. Keep the open so the next-open
    # gap can still stand in for the after-hours print.
    closes = drop_incomplete_session(closes, now_et)
    closes_adj = drop_incomplete_session(closes_adj, now_et)

    info: dict = {}
    try:
        raw = retry(lambda: t.info) or {}
        shares = raw.get("sharesOutstanding") or raw.get("impliedSharesOutstanding")
        mcap = raw.get("marketCap")
        info = {
            "shares_outstanding": int(shares) if shares else None,
            "market_cap": float(mcap) if mcap else None,
            "currency": raw.get("currency"),
            "dividend_yield": None,
            "target_price": (
                round(float(raw["targetMeanPrice"]), 2) if raw.get("targetMeanPrice") else None
            ),
            "next_earnings": None,
        }
        # dividendYield from current yfinance is already a percent (0.06 → 0.06%).
        try:
            px = closes[sorted(closes.keys())[-1]] if closes else None
            info["dividend_yield"] = dividend_yield_percent(
                raw.get("trailingAnnualDividendRate"),
                px,
                raw.get("dividendYield"),
            )
        except Exception:  # noqa: BLE001
            pass
        # earnings date
        try:
            cal = t.calendar
            if cal is not None:
                if hasattr(cal, "get"):
                    ed = cal.get("Earnings Date")
                    if isinstance(ed, (list, tuple)) and ed:
                        info["next_earnings"] = str(ed[0])[:10]
                    elif ed is not None:
                        info["next_earnings"] = str(ed)[:10]
                if info.get("next_earnings"):
                    info["next_earnings_estimated"] = True
        except Exception:  # noqa: BLE001
            pass
        # analyst ratings summary if present
        rec = raw.get("recommendationKey")
        n_analysts = raw.get("numberOfAnalystOpinions")
        if rec or n_analysts:
            info["ratings"] = f"{rec or '—'} · {n_analysts or '[ ]'} 家"
    except Exception as e:  # noqa: BLE001
        info = {"error": str(e)}

    return {
        "ticker": ticker.upper(),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "yahoo",
        "closes": closes,
        "closes_adj": closes_adj,
        "opens": opens,
        "info": info,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    out = ROOT / "data" / "prices" / f"{ticker}.json"
    try:
        data = fetch_prices(ticker)
        if not data["closes"]:
            raise RuntimeError("empty closes")
        write_json(out, data)
        update_status("yahoo_prices", True, f"{len(data['closes'])} days")
        print(f"wrote {out}")
        return 0
    except Exception as e:  # noqa: BLE001
        update_status("yahoo_prices", False, str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
