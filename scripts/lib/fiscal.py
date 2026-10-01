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

    # If this quarter's month is after the FY-end month in the calendar year,
    # the fiscal year label is next calendar year (e.g. Nov is after Aug → FY+1).
    if q_month > fy_end_m:
        fy = end_d.year + 1
    else:
        fy = end_d.year
    return fy, fq


def period_label(fy: int, fq: Optional[int] = None) -> str:
    yy = fy % 100
    if fq is None:
        return f"FY{yy:02d}"
    return f"FQ{fq}-{yy:02d}"


def yahoo_relative_to_absolute(
    cal: FiscalCalendar,
    relative: str,
    as_of: date | datetime | str,
    end_date: date | datetime | str | None = None,
) -> str:
    """Map Yahoo labels 0q/+1q/0y/+1y to absolute FQ*/FY* names."""
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

    # Infer "current" quarter as the next quarter end on/after as_of
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
