#!/usr/bin/env python3
"""Refresh every watchlist ticker, then rebuild shared pages.

Filings run first so the 8-K anchor is on disk before consensus labels.
A required step that exits non-zero fails the whole run. Nasdaq secondary
quotes stay optional.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def tickers() -> list[str]:
    with (ROOT / "config" / "watchlist.yaml").open(encoding="utf-8") as f:
        wl = yaml.safe_load(f)
    return list((wl.get("tickers") or {}).keys())


def run(args: list[str], *, optional: bool = False) -> bool:
    print("+", " ".join(args), flush=True)
    code = subprocess.call(args, cwd=ROOT)
    if code != 0:
        print(f"FAILED ({code}): {' '.join(args)}", file=sys.stderr)
        return optional
    return True


def main() -> int:
    names = tickers()
    ok = True
    ok = run([sys.executable, "scripts/fetch_filings.py", "--tickers", ",".join(names)]) and ok
    for t in names:
        for script in (
            "scripts/fetch_consensus.py",
            "scripts/fetch_actuals.py",
            "scripts/fetch_prices.py",
            "scripts/fetch_financials.py",
        ):
            extra = ["--force"] if script.endswith("fetch_financials.py") else []
            ok = run([sys.executable, script, "--ticker", t, *extra]) and ok
        run([sys.executable, "scripts/fetch_secondary.py", "--ticker", t], optional=True)
        for script in (
            "scripts/build_history.py",
            "scripts/build_page_consensus.py",
            "scripts/build_page_financials.py",
            "scripts/build_page_header.py",
            "scripts/build_page_price.py",
            "scripts/build_page_review.py",
            "scripts/build_page_call.py",
        ):
            ok = run([sys.executable, script, "--ticker", t]) and ok
        run([sys.executable, "scripts/ai_prepare.py", "--ticker", t, "--kind", "both"], optional=True)
    ok = run([sys.executable, "scripts/build_page_watchlist.py"]) and ok
    ok = run([sys.executable, "scripts/build_calendar_ics.py"]) and ok
    ok = run([sys.executable, "scripts/build_sources.py"]) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
