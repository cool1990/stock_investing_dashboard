#!/usr/bin/env python3
"""Fetch recent 8-K / Form 4 from SEC submissions for watchlist tickers."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.http import get  # noqa: E402
from scripts.lib.io import load_company, update_status, write_json  # noqa: E402


def load_watchlist_tickers() -> list[str]:
    with (ROOT / "config" / "watchlist.yaml").open(encoding="utf-8") as f:
        wl = yaml.safe_load(f)
    return list((wl.get("tickers") or {}).keys())


def load_red_rules() -> list[dict]:
    with (ROOT / "config" / "red_rules.yaml").open(encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("rules") or []


def is_red_8k(items: list[str], rules: list[dict]) -> tuple[bool, str | None]:
    for rule in rules:
        m = rule.get("match") or {}
        if m.get("form") != "8-K":
            continue
        want = set(m.get("items") or [])
        if want and want.intersection(items):
            return True, rule.get("label")
    return False, None


def fetch_company_filings(ticker: str, cik: int, rules: list[dict], limit: int = 40) -> list[dict]:
    cik10 = str(int(cik)).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    resp = get(url, sec=True, timeout=60)
    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    acc = recent.get("accessionNumber") or []
    primary = recent.get("primaryDocument") or []
    items_col = recent.get("items") or []
    out = []
    for i, form in enumerate(forms):
        if i >= limit * 3:
            break
        if form not in ("8-K", "8-K/A", "4", "4/A"):
            continue
        items_raw = items_col[i] if i < len(items_col) else ""
        items = [x.strip() for x in str(items_raw).split(",") if x.strip()]
        red, why = False, None
        if form.startswith("8-K"):
            red, why = is_red_8k(items, rules)
        elif form.startswith("4"):
            # Mark Form 4 as non-red by default (value filter needs ownership XML — skip)
            red, why = False, None
        filed = dates[i] if i < len(dates) else None
        accession = (acc[i] if i < len(acc) else "").replace("-", "")
        doc = primary[i] if i < len(primary) else ""
        url_f = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
            if accession and doc
            else None
        )
        typ = f"{form}" + (f" · {items[0]}" if items else "")
        out.append(
            {
                "t": ticker,
                "d": filed,
                "form": form,
                "type": typ,
                "title": f"{ticker} {form}" + (f" items {','.join(items)}" if items else ""),
                "why": why,
                "red": red,
                "url": url_f,
                "items": items,
            }
        )
        if len(out) >= limit:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default="", help="comma list; default=watchlist")
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()] or load_watchlist_tickers()
    rules = load_red_rules()
    items: list[dict] = []
    errors = []
    for t in tickers:
        try:
            cfg = load_company(t)
        except Exception:
            # only MU may have company yaml; skip others for filings if no cik
            if t != "MU":
                continue
            raise
        try:
            cik = cfg["cik"]
            items.extend(fetch_company_filings(t, int(cik), rules))
        except FileNotFoundError:
            continue
        except Exception as e:  # noqa: BLE001
            errors.append(f"{t}: {e}")

    items.sort(key=lambda x: x.get("d") or "", reverse=True)
    out = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items,
    }
    path = ROOT / "data" / "filings" / "watchlist.json"
    write_json(path, out)
    if errors:
        update_status("edgar_filings", False, "; ".join(errors)[:200])
    else:
        update_status("edgar_filings", True, f"{len(items)} filings")
    print(f"wrote {path} ({len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
