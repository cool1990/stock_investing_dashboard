"""Shared numeric decisions used by page builders and tests."""

from __future__ import annotations


NOT_CONNECTED = "未接入"


def roe_percent(
    ni: float | None,
    begin: float | None,
    end: float | None,
    *,
    annual: bool,
) -> float | None:
    """ROE in percent. Annual figures are not multiplied by 4."""
    if ni is None or begin is None or end is None or (begin + end) == 0:
        return None
    mult = 1.0 if annual else 4.0
    return round(float(ni) * mult / ((float(begin) + float(end)) / 2.0) * 100, 2)


def guide_vs_consensus(
    guide_rev: float | None,
    pre_rev: float | None,
    guide_eps: float | None,
    pre_eps: float | None,
) -> tuple[list, list]:
    """``[rev, eps]`` per docs/03_review.md. Consensus must be pre-release."""

    def one(guide: float | None, cons: float | None) -> tuple[float | None, str]:
        if guide is None or not cons:
            return None, "na"
        vs = float(guide) / float(cons) - 1
        tone = "up" if vs > 0.0005 else "down" if vs < -0.0005 else "flat"
        return round(vs, 4), tone

    rv, rt = one(guide_rev, pre_rev)
    ev, et = one(guide_eps, pre_eps)
    return [rv, ev], [rt, et]


def pre_release_level(slot: dict, metric: str) -> float | None:
    """Prefer the 30-day-ago print over the post-release consensus.

    After earnings, the live average converges on guidance. ``eps_trend.d30``
    is still the pre-release level when the snapshot is taken within a few
    weeks of the release. Revenue has no trend series on Yahoo.
    """
    if metric == "eps":
        d30 = ((slot or {}).get("eps_trend") or {}).get("d30")
        if d30 is not None:
            return float(d30)
    avg = ((slot or {}).get(metric) or {}).get("avg")
    return float(avg) if avg is not None else None


def same_basis_eps(non_gaap: float | None, gaap: float | None, *, non_gaap_card: bool) -> float | None:
    """Do not divide a Non-GAAP print by last quarter's GAAP EPS."""
    if non_gaap_card:
        return non_gaap
    return gaap


def kpi_latest(events: list[dict], field: str):
    """The current print, even when it is still missing.

    Falling through to the previous quarter makes last quarter look like
    this quarter.
    """
    if not events:
        return None
    return events[0].get(field)


def beat_but_down(events: list[dict], limit: int = 8) -> tuple[int, int]:
    """Count beat-and-fell among periods that have both surprise and a return.

    Denominator is that count, not a hard-coded 8.
    """
    window = []
    for event in events:
        if event.get("eps_surp") is not None and event.get("close") is not None:
            window.append(event)
        if len(window) >= limit:
            break
    n = sum(1 for e in window if e["eps_surp"] > 0 and e["close"] < 0)
    return n, len(window)


def keep_count(n: int) -> int:
    """Zero is a real count. Do not coerce it to null."""
    return n
