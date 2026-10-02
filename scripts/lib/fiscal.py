"""Fiscal period helpers for US stocks with configurable quarter-end months."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class FiscalCalendar:
    """quarter_end_months maps Q1..Q4 end months, e.g. MU: [11, 2, 5, 8]."""

    quarter_end_months: list[int]

    def __post_init__(self) -> None:
        if len(self.quarter_end_months) != 4:
            raise ValueError("quarter_end_months must have 4 entries")

    @property
    def fy_end_month(self) -> int:
        return self.quarter_end_months[3]


FP_TO_FQ = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "FY": 4}


def _as_date(d: date | datetime | str) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def _nearest_quarter_index(months: list[int], month: int) -> int:
    best_i = 0
    best_dist = 99
    for i, m in enumerate(months):
        dist = min((month - m) % 12, (m - month) % 12)
        if dist < best_dist:
            best_dist = dist
            best_i = i
    return best_i


def fiscal_quarter_for_end_date(cal: FiscalCalendar, end: date | datetime | str) -> tuple[int, int]:
    """Return (fiscal_year_2digit_or_full, fiscal_quarter).

    FY label year = calendar year of the fiscal-year end (Q4 end month).
    MU examples:
      2021-12-02 (≈Nov Q1) → FY22 Q1
      2026-02-26 → FY26 Q2
      2026-08-28 → FY26 Q4
    """
    end_d = _as_date(end)
    months = cal.quarter_end_months
    q_idx = _nearest_quarter_index(months, end_d.month)
    fq = q_idx + 1
    q_month = months[q_idx]
    fy_end_m = cal.fy_end_month

    # A November/December quarter can close in early January. The calendar
    # year of that close is already the next year, so do not add one again.
    year = end_d.year
    if end_d.month < q_month and (q_month - end_d.month) > 6:
        year -= 1
    # If this quarter's month is after the FY-end month in the calendar year,
    # the fiscal year label is next calendar year (e.g. Nov is after Aug → FY+1).
    if q_month > fy_end_m:
        fy = year + 1
    else:
        fy = year
    return fy, fq


def period_label(fy: int, fq: Optional[int] = None) -> str:
    yy = fy % 100
    if fq is None:
        return f"FY{yy:02d}"
    return f"FQ{fq}-{yy:02d}"


def period_label_from_xbrl(fy: int | str, fp: str, *, annual: bool = False) -> str:
    """Map SEC XBRL ``fy`` + ``fp`` (Q1/Q2/Q3/FY) to FQn-YY / FYyy.

    Prefer filing ``fp``/``fy`` over end-date heuristics (10-Q/10-K are authoritative).
    When ``annual=True`` and ``fp=FY``, return ``FY26`` style label.
    """
    fy_i = int(fy)
    fp_u = str(fp).upper()
    if annual and fp_u == "FY":
        return period_label(fy_i)
    fq = FP_TO_FQ.get(fp_u)
    if fq is None:
        raise ValueError(f"Unsupported XBRL fp={fp!r}")
    return period_label(fy_i, fq)


def annual_label(fy: int | str) -> str:
    """Financials page annual column label, e.g. FY2026."""
    return f"FY{int(fy)}"


def parse_period_label(label: str) -> tuple[int, Optional[int]]:
    """Parse ``FQ1-22`` / ``FY22`` / ``FY2022`` → (fy, fq|None)."""
    s = label.strip().upper()
    if s.startswith("FQ") and "-" in s:
        left, right = s[2:].split("-", 1)
        fq = int(left)
        yy = int(right)
        fy = 2000 + yy if yy < 100 else yy
        return fy, fq
    if s.startswith("FY"):
        yy = int(s[2:])
        fy = 2000 + yy if yy < 100 else yy
        return fy, None
    raise ValueError(f"Bad period label: {label}")


def prior_year_period(label: str) -> str:
    fy, fq = parse_period_label(label)
    if fq is None:
        if label.upper().startswith("FY") and len(label) > 4:
            return annual_label(fy - 1)
        return period_label(fy - 1)
    return period_label(fy - 1, fq)


def prior_quarter_period(label: str) -> str:
    fy, fq = parse_period_label(label)
    if fq is None:
        raise ValueError(f"No prior quarter for annual label {label}")
    if fq == 1:
        return period_label(fy - 1, 4)
    return period_label(fy, fq - 1)


def ytd_months_for_fp(fp: str) -> int:
    """Cumulative months represented by a YTD duration for Q1/Q2/Q3/FY."""
    fp_u = str(fp).upper()
    return {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12, "FY": 12}[fp_u]


def classify_duration_days(days: int) -> str | None:
    """Classify a duration fact as ``q`` / ``ytd`` / ``y`` by day span."""
    if 70 <= days <= 110:
        return "q"
    if 150 <= days <= 210:
        return "ytd"  # ~6M
    if 240 <= days <= 300:
        return "ytd"  # ~9M
    if 330 <= days <= 400:
        return "y"  # ~12M / FY
    return None


def days_between(start: date | datetime | str, end: date | datetime | str) -> int:
    return (_as_date(end) - _as_date(start)).days


def shift_period(label: str, steps: int) -> str:
    """Move a quarterly (or annual) label by ``steps`` quarters (or years)."""
    fy, fq = parse_period_label(label)
    if fq is None:
        return period_label(fy + steps)
    if steps >= 0:
        for _ in range(steps):
            if fq == 4:
                fy, fq = fy + 1, 1
            else:
                fq += 1
    else:
        for _ in range(-steps):
            if fq == 1:
                fy, fq = fy - 1, 4
            else:
                fq -= 1
    return period_label(fy, fq)


def quarter_end_date(cal: FiscalCalendar, fy: int, fq: int) -> date:
    """Nominal quarter end: day 28 of that quarter's end month."""
    month = cal.quarter_end_months[fq - 1]
    year = fy - 1 if month > cal.fy_end_month else fy
    return date(year, month, 28)


def latest_quarter_ended_before(cal: FiscalCalendar, day: date | datetime | str) -> str:
    """Latest fiscal quarter whose nominal end is strictly before ``day``.

    An 8-K item 2.02 filed on ``day`` reports this quarter (earnings land
    weeks after the period ends).
    """
    day_d = _as_date(day)
    best_end: date | None = None
    best: str | None = None
    for fy in range(day_d.year - 2, day_d.year + 2):
        for fq in (1, 2, 3, 4):
            ed = quarter_end_date(cal, fy, fq)
            if ed < day_d and (best_end is None or ed > best_end):
                best_end = ed
                best = period_label(fy, fq)
    if best is None:
        raise ValueError(f"no fiscal quarter before {day_d}")
    return best


def match_year_ago_period(
    year_ago: float,
    actuals: dict[str, float],
    *,
    tol: float = 0.02,
) -> str | None:
    """Return the historical quarter whose EPS matches Yahoo ``yearAgoEps``."""
    best: str | None = None
    best_rel = 1e9
    for period, val in actuals.items():
        if val is None:
            continue
        try:
            _fy, fq = parse_period_label(period)
        except ValueError:
            continue
        if fq is None:
            continue
        rel = abs(float(year_ago) - float(val)) / max(abs(float(val)), 0.05)
        if rel < best_rel:
            best_rel = rel
            best = period
    if best is not None and best_rel <= tol:
        return best
    return None


def reported_through_from_year_ago(year_ago: float, actuals: dict[str, float]) -> str | None:
    """Last *reported* quarter implied by 0q's year-ago EPS.

    If year-ago matches FQ4-25, 0q is FQ4-26, so the last reported quarter
    is FQ3-26.
    """
    matched = match_year_ago_period(year_ago, actuals)
    if matched is None:
        return None
    current = shift_period(matched, 4)
    return shift_period(current, -1)


def yahoo_relative_to_absolute(
    cal: FiscalCalendar,
    relative: str,
    as_of: date | datetime | str,
    end_date: date | datetime | str | None = None,
    *,
    reported_through: str | None = None,
) -> str:
    """Map Yahoo labels 0q/+1q/0y/+1y to absolute FQ*/FY* names.

    ``reported_through`` is the last quarter that has already reported
    (the 8-K 2.02 quarter). Yahoo's ``0q`` is the next unreported quarter,
    which is *not* "the next quarter-end on or after as_of" during the
    weeks between period-end and the earnings release.
    """
    as_of_d = _as_date(as_of)
    rel = relative.strip().lower()

    if end_date is not None:
        fy, fq = fiscal_quarter_for_end_date(cal, end_date)
        if rel in ("0q", "+0q", "currentq"):
            return period_label(fy, fq)
        if rel in ("+1q", "nextq"):
            return period_label(fy + 1, 1) if fq == 4 else period_label(fy, fq + 1)
        if rel in ("0y", "+0y", "currenty"):
            return period_label(fy if fq == 4 else fy)  # end_date for yearly is FY end
        if rel in ("+1y", "nexty"):
            return period_label(fy + 1)
        raise ValueError(f"Unknown relative label: {relative}")

    if reported_through:
        if rel in ("0q", "+0q", "currentq"):
            return shift_period(reported_through, 1)
        if rel in ("+1q", "nextq"):
            return shift_period(reported_through, 2)
        zq = shift_period(reported_through, 1)
        fy, _fq = parse_period_label(zq)
        if rel in ("0y", "+0y", "currenty"):
            return period_label(fy)
        if rel in ("+1y", "nexty"):
            return period_label(fy + 1)
        raise ValueError(f"Unknown relative label: {relative}")

    # Last resort when neither Yahoo's period end nor an 8-K / year-ago
    # anchor is available. This mis-labels the gap between quarter-end and
    # the earnings release; callers should pass reported_through.
    months = cal.quarter_end_months
    candidates: list[tuple[date, int, int]] = []
    for year in range(as_of_d.year - 1, as_of_d.year + 2):
        for m in months:
            ed = date(year, m, 28)
            fy, fq = fiscal_quarter_for_end_date(cal, ed)
            candidates.append((ed, fy, fq))
    candidates.sort(key=lambda x: x[0])
    current = candidates[0]
    for c in candidates:
        if c[0] >= as_of_d:
            current = c
            break
        current = c
    _, fy, fq = current

    if rel in ("0q", "+0q", "currentq"):
        return period_label(fy, fq)
    if rel in ("+1q", "nextq"):
        return period_label(fy + 1, 1) if fq == 4 else period_label(fy, fq + 1)
    if rel in ("0y", "+0y", "currenty"):
        return period_label(fy)
    if rel in ("+1y", "nexty"):
        return period_label(fy + 1)
    raise ValueError(f"Unknown relative label: {relative}")


def months_remaining_in_fy(cal: FiscalCalendar, as_of: date | datetime | str) -> float:
    as_of_d = _as_date(as_of)
    fy_end_m = cal.fy_end_month
    fy_end_y = as_of_d.year if as_of_d.month <= fy_end_m else as_of_d.year + 1
    if fy_end_m == 12:
        end = date(fy_end_y + 1, 1, 1)
    else:
        end = date(fy_end_y, fy_end_m + 1, 1)
    days = (end - as_of_d).days
    return max(0.0, min(12.0, days / 30.4375))
