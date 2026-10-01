#!/usr/bin/env python3
"""Fetch daily close prices."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json, retry, update_status, write_json  # noqa: E402


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
    return {
        "ticker": ticker.upper(),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "yahoo",
        "closes": closes,
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
        # Keep previous file
        update_status("yahoo_prices", False, str(e))
        print(f"ERROR (kept old data): {e}", file=sys.stderr)
        return 0 if out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
