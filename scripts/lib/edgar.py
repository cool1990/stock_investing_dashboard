"""SEC EDGAR companyfacts helpers (XBRL tags → period values)."""

from __future__ import annotations

import time
from typing import Any, Iterable, Optional

from scripts.lib.fiscal import (
    FiscalCalendar,
    classify_duration_days,
    days_between,
    fiscal_quarter_for_end_date,
    period_label,
    period_label_from_xbrl,
)
from scripts.lib.http import get
from scripts.lib.io import ROOT, read_json, write_json
from pathlib import Path

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def cik10(cik: int | str) -> str:
    return str(int(cik)).zfill(10)


def companyfacts_path(ticker: str) -> Path:
    return ROOT / "data" / "raw" / ticker.upper() / "companyfacts.json"


# Re-download companyfacts once a day unless --force. A cache that never
# expires hides the next 10-Q/10-K from local rebuilds.
COMPANYFACTS_MAX_AGE_S = 18 * 3600


def fetch_companyfacts(cik: int | str, *, ticker: str, force: bool = False) -> dict:
    """Download and cache companyfacts JSON under data/raw/<T>/."""
    path = companyfacts_path(ticker)
    if path.exists() and not force:
        age = time.time() - path.stat().st_mtime
        if age < COMPANYFACTS_MAX_AGE_S:
            cached = read_json(path)
            if cached:
                return cached
    url = COMPANYFACTS_URL.format(cik=cik10(cik))
    resp = get(url, sec=True, timeout=120.0)
    data = resp.json()
    write_json(path, data)
    return data


def iter_us_gaap_facts(facts: dict) -> Iterable[tuple[str, list[dict]]]:
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    for tag, payload in us_gaap.items():
        units = payload.get("units") or {}
        rows: list[dict] = []
        for unit_name, items in units.items():
            if not isinstance(items, list):
                continue
            for item in items:
                row = dict(item)
                row["_unit"] = unit_name
                rows.append(row)
        yield tag, rows


def _is_filing_form(form: str | None) -> bool:
    if not form:
        return False
    return form.startswith("10-Q") or form.startswith("10-K")


def pick_latest(items: list[dict], *, label: str | None = None) -> Optional[dict]:
    """Prefer the latest filing (restatements win). Same-day, prefer fy/fp match."""
    if not items:
        return None
    fy_l = fq_l = None
    if label:
        try:
            from scripts.lib.fiscal import parse_period_label

            fy_l, fq_l = parse_period_label(label)
        except ValueError:
            fy_l = fq_l = None

    def key(it: dict) -> tuple:
        filed = it.get("filed") or ""
        fp = str(it.get("_fp") or it.get("fp") or "").upper()
        match = 0
        fy = it.get("_fy") if it.get("_fy") is not None else it.get("fy")
        try:
            fy_i = int(fy) if fy is not None else None
        except (TypeError, ValueError):
            fy_i = None
        if fy_l is not None and fy_i == fy_l:
            if fq_l == 4 and fp == "FY":
                match = 1
            elif fq_l is not None and fp == f"Q{fq_l}":
                match = 1
        return (filed, match)

    return sorted(items, key=key)[-1]


def fact_bucket(item: dict) -> Optional[str]:
    """Return ``q`` / ``ytd`` / ``y`` / ``bs`` for a companyfacts item."""
    start = item.get("start")
    end = item.get("end")
    if not end:
        return None
    if not start:
        return "bs"
    days = days_between(start, end)
    return classify_duration_days(days)


def period_for_fact(cal: FiscalCalendar, item: dict) -> Optional[str]:
    """Map a fact to FQn-YY using period end date (handles comparative columns)."""
    end = item.get("end")
    if not end:
        return None
    fy, fq = fiscal_quarter_for_end_date(cal, end)
    return period_label(fy, fq)


def extract_tag_series(
    facts: dict,
    tags: list[str],
    cal: FiscalCalendar,
    *,
    prefer_units: tuple[str, ...] = ("USD",),
    scale_millions: bool = True,
    shares: bool = False,
    eps: bool = False,
) -> dict[str, dict[str, Any]]:
    """Extract values keyed by period label.

    Tag order is a per-period preference: a later tag fills periods the
    earlier tag does not cover (companies change tags). Within one tag,
    the latest ``filed`` date wins so a subsequent filing's restatement
    replaces the original number. Period keys come from the fact's ``end``
    date, so comparative columns land on the right quarter.
    """
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    rows: list[dict] = []
    for pref, tag in enumerate(tags):
        payload = us_gaap.get(tag)
        if not payload:
            continue
        units = payload.get("units") or {}
        unit_keys = [u for u in prefer_units if u in units] + [
            u for u in units if u not in prefer_units
        ]
        if shares:
            unit_keys = [u for u in unit_keys if u.lower() == "shares"] + [
                u for u in unit_keys if u.lower() != "shares"
            ]
        if eps:
            unit_keys = [u for u in unit_keys if "share" in u.lower()] + [
                u for u in unit_keys if "share" not in u.lower()
            ]
        for uk in unit_keys:
            items = units.get(uk) or []
            if not items:
                continue
            for it in items:
                row = dict(it)
                row["_unit"] = uk
                row["_tag"] = tag
                row["_pref"] = pref
                rows.append(row)
            break

    if not rows:
        return {}

    grouped: dict[tuple[str, str, int], list[dict]] = {}

    for item in rows:
        if not _is_filing_form(item.get("form")):
            continue
        end = item.get("end")
        if not end:
            continue
        bucket = fact_bucket(item)
        if bucket is None:
            continue
        label = period_for_fact(cal, item)
        if label is None:
            continue

        val = item.get("val")
        if val is None:
            continue
        unit = item.get("_unit") or "USD"
        if eps or "share" in unit.lower() and "usd" in unit.lower():
            num = float(val)
        elif shares or unit.lower() == "shares":
            num = float(val)
        elif scale_millions and unit.upper() == "USD":
            num = float(val) / 1_000_000.0
        else:
            num = float(val)

        # Filing fy/fp for metadata (current period filings preferred later)
        fp = str(item.get("fp") or "").upper()
        fy = item.get("fy")
        enriched = {
            **item,
            "_value": num,
            "_raw": float(val),
            "_bucket": bucket,
            "_label": label,
            "_fp": fp,
            "_fy": int(fy) if fy is not None else None,
        }
        grouped.setdefault((label, bucket, int(item.get("_pref") or 0)), []).append(enriched)

    # Lowest preference index that actually has this period wins; then latest filing.
    by_period: dict[tuple[str, str], list[tuple[int, list[dict]]]] = {}
    for (label, bucket, pref), items in grouped.items():
        by_period.setdefault((label, bucket), []).append((pref, items))

    out: dict[str, dict[str, Any]] = {}
    for (label, bucket), options in by_period.items():
        options.sort(key=lambda x: x[0])
        _pref, items = options[0]
        best = pick_latest(items, label=label)
        if best is None:
            continue
        slot = out.setdefault(
            label,
            {
                "q": None,
                "ytd": None,
                "y": None,
                "bs": None,
                "end": best.get("end"),
                "fy": best.get("_fy"),
                "fp": best.get("_fp"),
                "form": best.get("form"),
                "filed": best.get("filed"),
                "tag": best.get("_tag"),
                "derived": {},
            },
        )
        slot[bucket] = best["_value"]
        # Refresh meta from the chosen fact when it's "current" for that period
        if best.get("end"):
            slot["end"] = best["end"]
        if best.get("filed") and (not slot.get("filed") or best["filed"] >= slot["filed"]):
            slot["filed"] = best["filed"]
            slot["form"] = best.get("form")
            slot["fp"] = best.get("_fp")
            slot["fy"] = best.get("_fy")

    # FY ~12M also fills ytd for the Q4 period
    for label, slot in list(out.items()):
        if slot.get("y") is not None and slot.get("ytd") is None:
            slot["ytd"] = slot["y"]
            slot.setdefault("derived", {})["ytd"] = "from_fy"

    return out


def list_tag_coverage(facts: dict, *, min_forms: int = 1) -> list[dict]:
    rows: list[dict] = []
    for tag, items in iter_us_gaap_facts(facts):
        filing_items = [i for i in items if _is_filing_form(i.get("form"))]
        if len(filing_items) < min_forms:
            continue
        ends = sorted({i.get("end") for i in filing_items if i.get("end")})
        fps = sorted({str(i.get("fp")) for i in filing_items if i.get("fp")})
        units = sorted({str(i.get("_unit")) for i in filing_items})
        rows.append(
            {
                "tag": tag,
                "n": len(filing_items),
                "units": ",".join(units),
                "fps": ",".join(fps),
                "end_min": ends[0] if ends else "",
                "end_max": ends[-1] if ends else "",
            }
        )
    rows.sort(key=lambda r: (-r["n"], r["tag"]))
    return rows


def calendar_from_company(cfg: dict) -> FiscalCalendar:
    months = (cfg.get("fiscal") or {}).get("quarter_end_months") or [11, 2, 5, 8]
    return FiscalCalendar(list(months))
