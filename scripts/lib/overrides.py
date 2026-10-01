"""Company YAML overrides: None means 'leave the XBRL value', not 'wipe it'."""

from __future__ import annotations


def drop_none(obj: dict) -> dict:
    out: dict = {}
    for key, val in obj.items():
        if val is None:
            continue
        if isinstance(val, dict):
            nested = drop_none(val)
            if nested:
                out[key] = nested
        else:
            out[key] = val
    return out


def apply_financial_overrides(entry: dict, ov: dict) -> None:
    for section in ("q", "ytd", "bs"):
        for key, val in (ov.get(section) or {}).items():
            if val is None:
                continue
            entry.setdefault(section, {})[key] = val
            entry.setdefault("derived", {})[key] = "override"
    cleaned = drop_none(ov.get("non_gaap") or {})
    if cleaned:
        base = dict(entry.get("non_gaap") or {})
        for key, val in cleaned.items():
            if isinstance(val, dict) and isinstance(base.get(key), dict):
                base[key] = {**base[key], **val}
            else:
                base[key] = val
        entry["non_gaap"] = base
    if ov.get("end"):
        entry["end"] = ov["end"]


def derive_q4_eps(net_income_millions: float | None, shares: float | None) -> float | None:
    """Q4 diluted EPS ≈ quarterly net income / diluted shares.

    Net income is in millions of dollars; shares are absolute. This is a
    stand-in until the press release or 10-K states the figure (rounding
    can be off by a cent).
    """
    if net_income_millions is None or not shares:
        return None
    return round(float(net_income_millions) * 1_000_000.0 / float(shares), 2)
