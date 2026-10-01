#!/usr/bin/env python3
"""Fetch SEC XBRL companyfacts → data/financials/<T>.json.

Builds per-period q / ytd / bs maps. Single-quarter flow items:
  - reported quarterly duration when present
  - else ytd_diff (this YTD − prior YTD)
  - Q4: fy_minus_9m (FY annual − Q3 YTD)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.edgar import (  # noqa: E402
    calendar_from_company,
    extract_tag_series,
    fetch_companyfacts,
)
from scripts.lib.fiscal import parse_period_label, period_label, prior_quarter_period  # noqa: E402
from scripts.lib.io import load_company, update_status, write_json  # noqa: E402

# Fields treated as flow (IS/CF) — need q / ytd; BS fields use bs only.
FLOW_FIELDS = {
    "revenue",
    "cogs",
    "gross_profit",
    "rnd",
    "sga",
    "op_income",
    "interest_other",
    "tax",
    "net_income",
    "eps_diluted",
    "shares_diluted",
    "cfo",
    "capex_gross",
    "da",
    "sbc",
    "buyback",
    "dividends",
    "debt_repay",
    "other_op_expense",
}

# Cash-flow outflow tags are positive in XBRL; store positive here, negate at page build.
OUTFLOW_FIELDS = {"capex_gross", "buyback", "dividends", "debt_repay"}

EPS_FIELDS = {"eps_diluted"}
SHARES_FIELDS = {"shares_diluted"}


def _sorted_periods(labels: set[str]) -> list[str]:
    def key(lab: str) -> tuple:
        fy, fq = parse_period_label(lab)
        return (fy, fq or 0)

    return sorted(labels, key=key)


def _get_ytd(series: dict, period: str) -> Optional[float]:
    slot = series.get(period) or {}
    if slot.get("ytd") is not None:
        return slot["ytd"]
    if slot.get("y") is not None:
        return slot["y"]
    # Q1 YTD == Q when only quarterly reported
    fy, fq = parse_period_label(period)
    if fq == 1 and slot.get("q") is not None:
        return slot["q"]
    return None


def resolve_quarterly(
    series: dict,
    period: str,
    *,
    allow_diff: bool = True,
) -> tuple[Optional[float], Optional[str]]:
    """Return (value, derived_flag) for a single quarter."""
    slot = series.get(period) or {}
    if slot.get("q") is not None:
        return slot["q"], "reported"

    if not allow_diff:
        return None, None

    fy, fq = parse_period_label(period)
    if fq is None:
        return None, None

    if fq == 1:
        ytd = _get_ytd(series, period)
        if ytd is not None:
            return ytd, "ytd_eq_q1"
        return None, None

    if fq == 4:
        # Prefer FY annual − Q3 YTD
        fy_label = period  # FQ4-yy
        annual = (series.get(fy_label) or {}).get("y")
        if annual is None:
            # Also try same period ytd which may be from_fy
            annual = (series.get(fy_label) or {}).get("ytd")
        q3 = period_label(fy, 3)
        q3_ytd = _get_ytd(series, q3)
        if annual is not None and q3_ytd is not None:
            return annual - q3_ytd, "fy_minus_9m"
        return None, None

    # Q2 / Q3: this YTD − prior quarter YTD
    ytd = _get_ytd(series, period)
    prev = prior_quarter_period(period)
    prev_ytd = _get_ytd(series, prev)
    if ytd is not None and prev_ytd is not None:
        return ytd - prev_ytd, "ytd_diff"
    return None, None


def build_financials(ticker: str, *, force: bool = False) -> dict:
    cfg = load_company(ticker)
    cal = calendar_from_company(cfg)
    xbrl_map: dict[str, list[str]] = cfg.get("xbrl_map") or {}
    if not xbrl_map:
        raise RuntimeError(f"{ticker}: xbrl_map is empty; run diagnose_xbrl_tags.py and fill MU.yaml")

    facts = fetch_companyfacts(cfg["cik"], ticker=ticker, force=force)
    series_by_field: dict[str, dict[str, dict]] = {}

    for field, tags in xbrl_map.items():
        if not tags:
            continue
        series_by_field[field] = extract_tag_series(
            facts,
            list(tags),
            cal,
            prefer_units=("USD/shares", "USD") if field in EPS_FIELDS else ("USD",),
            scale_millions=field not in EPS_FIELDS and field not in SHARES_FIELDS,
            shares=field in SHARES_FIELDS,
            eps=field in EPS_FIELDS,
        )

    # Collect periods from revenue / total_assets / net_income
    period_set: set[str] = set()
    for field in ("revenue", "total_assets", "net_income", "cfo"):
        period_set.update(series_by_field.get(field, {}).keys())

    overrides = ((cfg.get("overrides") or {}).get("financials")) or {}
    period_set.update(overrides.keys())

    # Filter from backfill_from
    backfill = cfg.get("backfill_from") or "FQ1-22"
    bf_fy, bf_fq = parse_period_label(backfill)
    periods = [
        p
        for p in _sorted_periods(period_set)
        if parse_period_label(p) >= (bf_fy, bf_fq or 0)
    ]

    out_periods: dict[str, dict[str, Any]] = {}
    for period in periods:
        fy, fq = parse_period_label(period)
        # Meta from revenue or assets
        meta_src = (
            (series_by_field.get("revenue") or {}).get(period)
            or (series_by_field.get("total_assets") or {}).get(period)
            or {}
        )
        entry: dict[str, Any] = {
            "end": meta_src.get("end"),
            "fy": fy,
            "fp": "FY" if fq == 4 and (meta_src.get("fp") == "FY") else f"Q{fq}",
            "form": meta_src.get("form"),
            "filed": meta_src.get("filed"),
            "q": {},
            "ytd": {},
            "bs": {},
            "derived": {},
        }
        # Prefer end from BS if missing
        if not entry["end"]:
            for f in ("total_assets", "cash", "equity"):
                e = (series_by_field.get(f) or {}).get(period, {}).get("end")
                if e:
                    entry["end"] = e
                    break

        for field, series in series_by_field.items():
            slot = series.get(period) or {}
            if field in FLOW_FIELDS or field in EPS_FIELDS or field in SHARES_FIELDS:
                # EPS: never subtract; use reported q / ytd / y directly
                if field in EPS_FIELDS:
                    if slot.get("q") is not None:
                        entry["q"][field] = round(slot["q"], 4)
                        entry["derived"][field] = "reported"
                    if slot.get("ytd") is not None:
                        entry["ytd"][field] = round(slot["ytd"], 4)
                    elif slot.get("y") is not None:
                        entry["ytd"][field] = round(slot["y"], 4)
                    continue

                if field in SHARES_FIELDS:
                    if slot.get("q") is not None:
                        entry["q"][field] = slot["q"]
                    if slot.get("ytd") is not None:
                        entry["ytd"][field] = slot["ytd"]
                    elif slot.get("y") is not None:
                        entry["ytd"][field] = slot["y"]
                    continue

                q_val, how = resolve_quarterly(series, period, allow_diff=True)
                if q_val is not None:
                    entry["q"][field] = round(q_val, 4) if abs(q_val) < 1e6 else round(q_val, 2)
                    if how:
                        entry["derived"][field] = how
                ytd_val = _get_ytd(series, period)
                if ytd_val is not None:
                    entry["ytd"][field] = round(ytd_val, 4) if abs(ytd_val) < 1e6 else round(ytd_val, 2)
            else:
                # Balance sheet
                if slot.get("bs") is not None:
                    entry["bs"][field] = round(slot["bs"], 4)

        # Apply overrides (fill or replace specific fields)
        ov = overrides.get(period) or {}
        for section in ("q", "ytd", "bs"):
            for k, v in (ov.get(section) or {}).items():
                entry[section][k] = v
                entry["derived"][k] = "override"
        if ov.get("end"):
            entry["end"] = ov["end"]
        if ov.get("non_gaap"):
            entry["non_gaap"] = ov["non_gaap"]

        out_periods[period] = entry

    return {
        "ticker": ticker.upper(),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "units": "USD millions (EPS in USD; shares absolute)",
        "source": "sec_companyfacts",
        "periods": out_periods,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    out = ROOT / "data" / "financials" / f"{ticker}.json"
    try:
        data = build_financials(ticker, force=args.force)
        n = len(data["periods"])
        if n == 0:
            raise RuntimeError("no periods extracted")
        write_json(out, data)
        update_status("sec_financials", True, f"{n} periods")
        print(f"wrote {out} ({n} periods)")
        return 0
    except Exception as e:  # noqa: BLE001
        update_status("sec_financials", False, str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 0 if out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
