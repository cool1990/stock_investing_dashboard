"""Number formatting matching the frontend rules."""

from __future__ import annotations

from typing import Optional

MINUS = "\u2212"  # −
MISSING = "[ ]"
NM = "n.m."


def format_growth(current: Optional[float], base: Optional[float]) -> str:
    """YoY/PoP growth per 01_common.md §6.

    n.m. when base <= 0, or current < 0 and base > 0 (sign flip).
    [ ] when either side is missing.
    """
    if current is None or base is None:
        return MISSING
    if base <= 0 or (current < 0 and base > 0):
        return NM
    p = (current / base - 1) * 100
    sign = "+" if p >= 0 else MINUS
    return f"{sign}{round(abs(p))}%"


def format_pct(current: Optional[float], base: Optional[float]) -> str:
    if current is None or base is None or base == 0:
        return "—"
    p = (current / base - 1) * 100
    sign = "+" if p >= 0 else MINUS
    abs_p = abs(p)
    body = str(round(abs_p)) if abs_p >= 100 else f"{abs_p:.1f}"
    return f"{sign}{body}%"


def format_num(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return MISSING
    if v < 0:
        return f"{MINUS}{abs(v):.{digits}f}"
    return f"{v:.{digits}f}"
