"""Forward EPS (next twelve months) from annual consensus."""

from __future__ import annotations


def ntm_from_annuals(
    annuals: list[tuple[str, float]],
    months_remaining: float,
) -> tuple[float | None, str]:
    """Time-weight the current fiscal year and the next one.

    ``annuals`` is ``[(FY27, eps), (FY28, eps)]`` in fiscal-year order
    (the snapshot's 0y then +1y). Incomplete quarter sums are not used:
    two quarters are not a twelve-month estimate.
    """
    if len(annuals) >= 2:
        w = max(0.0, min(1.0, float(months_remaining) / 12.0))
        cur_name, cur_eps = annuals[0]
        nxt_name, nxt_eps = annuals[1]
        val = w * float(cur_eps) + (1.0 - w) * float(nxt_eps)
        return val, (
            f"fy_time_weight {cur_name}*{w:.4f}+{nxt_name}*{(1.0 - w):.4f}"
        )
    return None, "incomplete_ntm_hidden"


def ntm_from_quarters(values: list[float]) -> tuple[float | None, str]:
    if len(values) >= 4:
        return float(sum(values[:4])), "sum_next_4_quarters"
    return None, "incomplete_ntm_hidden"
