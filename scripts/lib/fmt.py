"""Number formatting matching the frontend rules."""

from __future__ import annotations

from typing import Optional

MINUS = "\u2212"  # −
MISSING = "[ ]"
NM = "n.m."
DASH = "—"

Tone = str  # up / down / flat / na


def format_growth(current: Optional[float], base: Optional[float]) -> str:
    """YoY/PoP growth (integer %) for consensus-style grids.

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
        return DASH
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


def _tone_for_signed(p: float, *, flat_eps: float = 0.05) -> Tone:
    if abs(p) < flat_eps:
        return "flat"
    return "up" if p > 0 else "down"


def format_change(
    current: Optional[float],
    base: Optional[float],
    *,
    kind: str = "pct",
) -> tuple[str, Tone]:
    """Financials YoY/QoQ display string + color class (01 §6).

    kind:
      - pct: percentage change; |p|>=1000 → int, else 1 decimal
      - pp: percentage-point change (current/base already in percent units)
      - days: day delta, e.g. ``+9 天``
    Missing current → ``[ ]``; missing base only → ``—``; n.m. rules as format_growth.
    """
    if current is None:
        return MISSING, "na"
    if base is None:
        return DASH, "na"
    if kind == "pp":
        delta = current - base
        sign = "+" if delta >= 0 else MINUS
        return f"{sign}{abs(delta):.1f}pp", _tone_for_signed(delta)
    if kind == "days":
        delta = current - base
        sign = "+" if delta >= 0 else MINUS
        return f"{sign}{int(round(abs(delta)))} 天", _tone_for_signed(delta)

    if base <= 0 or (current < 0 and base > 0):
        return NM, "na"
    p = (current / base - 1) * 100
    sign = "+" if p >= 0 else MINUS
    abs_p = abs(p)
    body = str(round(abs_p)) if abs_p >= 1000 else f"{abs_p:.1f}"
    return f"{sign}{body}%", _tone_for_signed(p)


def tone_from_text(text: str) -> Tone:
    if text in (MISSING, DASH, NM) or text.startswith("["):
        return "na"
    if text.startswith("+"):
        return "up"
    if text.startswith(MINUS) or text.startswith("-"):
        return "down"
    return "flat"
