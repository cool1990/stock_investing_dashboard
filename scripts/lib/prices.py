"""Unadjusted reaction windows and quote helpers."""

from __future__ import annotations

from datetime import datetime


def drop_incomplete_session(series: dict, now_et: datetime) -> dict:
    """Drop today's bar when the regular session has not closed (16:00 ET)."""
    out = dict(series)
    today = now_et.date().isoformat()
    if today in out and (now_et.hour < 16 or (now_et.hour == 16 and now_et.minute < 1)):
        out.pop(today, None)
    return out


def dividend_yield_percent(
    trailing_rate: float | None,
    price: float | None,
    yahoo_yield: float | None,
) -> float | None:
    """Percent yield. Yahoo's ``dividendYield`` is already in percent units.

    Prefer annual dividend dollars / price. If that ratio looks like a
    yield that was multiplied an extra time (>> the Yahoo percent field),
    keep the Yahoo percent.
    """
    from_rate = None
    if trailing_rate and price:
        from_rate = float(trailing_rate) / float(price) * 100.0
    from_yahoo = None
    if yahoo_yield not in (None, 0):
        from_yahoo = float(yahoo_yield)
    if from_rate is None:
        return round(from_yahoo, 2) if from_yahoo is not None else None
    if from_yahoo is not None and from_rate > 1 and from_yahoo < 1:
        return round(from_yahoo, 2)
    return round(from_rate, 2)


def reaction_window(closes: dict, release: str, timing: str) -> dict:
    """Baseline is the last regular close before the reaction session.

    After-close releases: baseline = release-day close (or prior session).
    T+0 is the next session. T+5 is five trading sessions after T+0,
    still divided by the baseline — not by the reaction close.
    """
    days = sorted(closes)
    empty = {
        "pre_day": None,
        "pre": None,
        "react_day": None,
        "d1": None,
        "t5": None,
    }
    if not days or not release:
        return empty
    if timing == "after_close":
        prior = [d for d in days if d <= release]
        if not prior:
            return empty
        pre_day = prior[-1]
        idx = days.index(pre_day)
        pre = float(closes[pre_day])
        if idx + 1 >= len(days) or not pre:
            return {**empty, "pre_day": pre_day, "pre": pre}
        react = days[idx + 1]
        d1 = float(closes[react]) / pre - 1
        t5 = None
        if idx + 6 < len(days):
            t5 = float(closes[days[idx + 6]]) / pre - 1
        return {"pre_day": pre_day, "pre": pre, "react_day": react, "d1": d1, "t5": t5}
    # before the open: reaction day is the release session; baseline is the prior close
    prior = [d for d in days if d < release]
    on_day = [d for d in days if d >= release]
    if not prior or not on_day:
        return empty
    pre_day = prior[-1]
    react = on_day[0]
    pre = float(closes[pre_day])
    if not pre:
        return {**empty, "pre_day": pre_day, "pre": pre, "react_day": react}
    idx = days.index(react)
    d1 = float(closes[react]) / pre - 1
    t5 = None
    if idx + 5 < len(days):
        t5 = float(closes[days[idx + 5]]) / pre - 1
    return {"pre_day": pre_day, "pre": pre, "react_day": react, "d1": d1, "t5": t5}


def open_gap(opens: dict, react_day: str | None, pre: float | None) -> float | None:
    """Next-session open / baseline − 1. Documented stand-in when no AH print exists."""
    if not react_day or pre is None or react_day not in opens or not pre:
        return None
    return float(opens[react_day]) / float(pre) - 1
