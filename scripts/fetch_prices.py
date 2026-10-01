#!/usr/bin/env python3
"""Fetch daily close prices + key quote info for StockHeader."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import retry, update_status, write_json  # noqa: E402


def fetch_prices(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)
    hist = retry(lambda: t.history(period="max"))
    closes = {}
    if hist is not None and not hist.empty:
        for idx, row in hist.iterrows():
            try:
                d = idx.tz_convert("America/New_York").date().isoformat()
            except Exception:  # noqa: BLE001
                d = str(idx)[:10]
            closes[d] = round(float(row["Close"]), 4)

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
        # Dividend yield: prefer trailing rate / price (Yahoo dividendYield units vary)
        try:
            px = None
            if closes:
                px = closes[sorted(closes.keys())[-1]]
            trail = raw.get("trailingAnnualDividendRate")
            if trail and px:
                info["dividend_yield"] = round(float(trail) / float(px) * 100, 2)
            elif raw.get("dividendYield") not in (None, 0):
                y = float(raw["dividendYield"])
                info["dividend_yield"] = round(y * 100, 2) if y <= 1 else round(y, 2)
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
        print(f"ERROR (kept old data): {e}", file=sys.stderr)
        return 0 if out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
