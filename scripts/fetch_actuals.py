#!/usr/bin/env python3
"""Fetch reported EPS (Yahoo) and revenue (SEC XBRL) into data/actuals."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.http import get  # noqa: E402
from scripts.lib.io import load_company, read_json, retry, update_status, write_json  # noqa: E402


def fetch_eps(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)
    dates = retry(lambda: t.get_earnings_dates(limit=40))
    quarters: dict = {}
    if dates is not None:
        for idx, row in dates.iterrows():
            reported = row.get("Reported EPS")
            if reported is None or (hasattr(reported, "__float__") and str(reported) == "nan"):
                continue
            # Index is usually timezone-aware timestamp = earnings date
            try:
                release = idx.tz_convert("America/New_York").date().isoformat()
            except Exception:  # noqa: BLE001
                release = str(idx)[:10]
            # Period label left for build_history / manual mapping; store by release for now
            quarters[release] = {
                "eps": float(reported),
                "eps_estimate": float(row["EPS Estimate"])
                if row.get("EPS Estimate") == row.get("EPS Estimate")
                else None,
                "release_date": release,
                "source": "yahoo",
            }
    return quarters


def fetch_revenue_sec(cik: int) -> dict:
    cik_str = str(cik).zfill(10)
    concepts = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
    ]
    out: dict = {}
    for concept in concepts:
        url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_str}/us-gaap/{concept}.json"
        try:
            r = get(url, sec=True, timeout=30)
            if r.status_code != 200:
                continue
            units = r.json().get("units", {}).get("USD", [])
            for item in units:
                if item.get("form") not in ("10-Q", "10-K", "8-K"):
                    continue
                if item.get("fp") not in ("Q1", "Q2", "Q3", "FY"):
                    continue
                # Prefer quarterly frames
                val = item.get("val")
                if val is None:
                    continue
                end = item.get("end")
                out[end] = {
                    "rev_usd": val,
                    "rev": round(val / 1e9, 2),
                    "fp": item.get("fp"),
                    "fy": item.get("fy"),
                    "form": item.get("form"),
                    "filed": item.get("filed"),
                    "source": f"sec:{concept}",
                }
            if out:
                break
        except Exception as e:  # noqa: BLE001
            update_status("sec_revenue", False, str(e))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    out_path = ROOT / "data" / "actuals" / f"{ticker}.json"
    existing = read_json(
        out_path,
        default={"eps_basis": cfg.get("eps_basis", "non_gaap"), "quarters": {}, "years": {}, "raw": {}},
    )

    yahoo_ok = False
    sec_ok = False
    try:
        eps_by_release = fetch_eps(ticker)
        existing.setdefault("raw", {})["yahoo_eps_by_release"] = eps_by_release
        update_status("yahoo_actuals", True, f"{len(eps_by_release)} rows")
        yahoo_ok = True
    except Exception as e:  # noqa: BLE001
        update_status("yahoo_actuals", False, str(e))
        print(f"yahoo actuals failed: {e}", file=sys.stderr)

    try:
        rev = fetch_revenue_sec(int(cfg["cik"]))
        existing.setdefault("raw", {})["sec_revenue_by_end"] = rev
        update_status("sec_revenue", True, f"{len(rev)} rows")
        sec_ok = True
    except Exception as e:  # noqa: BLE001
        update_status("sec_revenue", False, str(e))
        print(f"sec revenue failed: {e}", file=sys.stderr)

    # Preserve curated quarters/years if present; never wipe with empty
    overrides = (cfg.get("overrides") or {}).get("actuals") or {}
    for period, vals in overrides.items():
        if period.startswith("FQ"):
            existing.setdefault("quarters", {})[period] = {
                **existing.get("quarters", {}).get(period, {}),
                **vals,
                "source": "override",
            }
        elif period.startswith("FY"):
            existing.setdefault("years", {})[period] = {
                **existing.get("years", {}).get(period, {}),
                **vals,
                "source": "override",
            }

    existing["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(out_path, existing)
    print(f"wrote {out_path}")
    if not yahoo_ok and not sec_ok:
        print(f"ERROR: both actuals sources failed for {ticker}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
