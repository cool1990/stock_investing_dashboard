"""Decide which fiscal quarter Yahoo's ``0q`` still refers to."""

from __future__ import annotations

from datetime import date, datetime

from scripts.lib.fiscal import (
    FiscalCalendar,
    latest_quarter_ended_before,
    reported_through_from_year_ago,
)
from scripts.lib.io import ROOT, read_json


def _as_date(d: date | datetime | str) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def latest_8k_202_date(ticker: str, as_of: date | datetime | str) -> date | None:
    """Latest 8-K item 2.02 on or before ``as_of`` from the filings cache."""
    as_of_d = _as_date(as_of)
    data = read_json(ROOT / "data" / "filings" / "watchlist.json", default={"items": []}) or {}
    best: date | None = None
    for item in data.get("items") or []:
        if str(item.get("t") or "").upper() != ticker.upper():
            continue
        if "2.02" not in (item.get("items") or []):
            continue
        try:
            filed = date.fromisoformat(str(item.get("d"))[:10])
        except ValueError:
            continue
        if filed <= as_of_d and (best is None or filed > best):
            best = filed
    return best


def actual_eps_by_period(ticker: str) -> dict[str, float]:
    """Non-GAAP EPS when present, else GAAP. Used to align Yahoo yearAgoEps."""
    out: dict[str, float] = {}
    fin = read_json(ROOT / "data" / "financials" / f"{ticker.upper()}.json", default={}) or {}
    for period, slot in (fin.get("periods") or {}).items():
        ng = (slot.get("non_gaap") or {}).get("eps_diluted")
        gaap = (slot.get("q") or {}).get("eps_diluted")
        if ng is not None:
            out[period] = float(ng)
        elif gaap is not None:
            out[period] = float(gaap)
    hist = read_json(ROOT / "data" / "history" / f"{ticker.upper()}.json", default={}) or {}
    for row in ((hist.get("eps") or {}).get("q") or []):
        if row.get("actual") is not None and row.get("period"):
            out.setdefault(row["period"], float(row["actual"]))
    page = read_json(ROOT / "data" / "pages" / ticker.upper() / "consensus.json", default={}) or {}
    for row in (((page.get("history") or {}).get("eps") or {}).get("q") or []):
        if row.get("actual") is not None and row.get("period"):
            out.setdefault(row["period"], float(row["actual"]))
    return out


def resolve_reported_through(
    ticker: str,
    cal: FiscalCalendar,
    as_of: date | datetime | str,
    year_ago_eps: float | None = None,
) -> tuple[str | None, str]:
    """Last reported quarter, so Yahoo 0q = the following quarter.

    8-K item 2.02 wins. yearAgoEps is the fallback when no filing is on disk
    (the gap before the release, if filings have not been fetched yet).
    """
    filed = latest_8k_202_date(ticker, as_of)
    if filed is not None:
        return latest_quarter_ended_before(cal, filed), "8k_2.02"
    if year_ago_eps is not None:
        actuals = actual_eps_by_period(ticker)
        hit = reported_through_from_year_ago(float(year_ago_eps), actuals)
        if hit:
            return hit, "year_ago_eps"
    return None, "heuristic"
