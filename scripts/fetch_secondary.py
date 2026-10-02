#!/usr/bin/env python3
"""Optional secondary consensus (Nasdaq). Failures are non-fatal."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json, update_status, write_json  # noqa: E402


def fetch_nasdaq(ticker: str) -> dict:
    import requests

    url = f"https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; stock_investing_dashboard/0.1)",
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    out = ROOT / "data" / "secondary" / f"{ticker}.json"
    try:
        raw = fetch_nasdaq(ticker)
        write_json(
            out,
            {
                "ticker": ticker,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": "nasdaq",
                "raw": raw,
            },
        )
        update_status("nasdaq_secondary", True, "ok")
        print(f"wrote {out}")
    except Exception as e:  # noqa: BLE001
        update_status("nasdaq_secondary", False, str(e))
        print(f"secondary skipped: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
