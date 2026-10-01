#!/usr/bin/env python3
"""Build data/pages/<T>/financials.json from data/financials/<T>.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import (  # noqa: E402
    annual_label,
    days_between,
    parse_period_label,
    period_label,
    prior_quarter_period,
    prior_year_period,
    ytd_months_for_fp,
)
from scripts.lib.fmt import format_change  # noqa: E402
from scripts.lib.io import load_company, read_json, write_json  # noqa: E402

MODE_NOTES = {
    "q": "单季：流量科目由 10-Q 累计数相减得到；资产负债表取季末余额，环比为较上季末。",
    "ytd": "累计 = 财年初至该季末。同比与上年同期累计相比。",
    "y": "年度：财年（截至 8 月底 / 9 月初）。",
    "bs_ytd": "资产负债表、权益表是时点数，累计视图与单季相同。",
}


def _round_amt(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(float(v), 2)


def _get(periods: dict, period: str, section: str, field: str) -> Optional[float]:
    slot = periods.get(period) or {}
    return (slot.get(section) or {}).get(field)


def _derived(
    periods: dict,
    period: str,
    section: str,
    fn: Callable[[dict[str, Optional[float]]], Optional[float]],
    fields: list[str],
) -> Optional[float]:
    vals = {f: _get(periods, period, section, f) for f in fields}
    if any(vals[f] is None for f in fields):
        # allow partial for some formulas
        pass
    return fn(vals)


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def period_days(periods: dict, period: str) -> Optional[int]:
    end = (periods.get(period) or {}).get("end")
    if not end:
        return None
    try:
        prev = prior_quarter_period(period)
    except ValueError:
        return None
    prev_end = (periods.get(prev) or {}).get("end")
    if not prev_end:
        return None
    return days_between(prev_end, end)


def enrich_derived(periods: dict) -> None:
    """Add derived metrics into q/ytd/bs in-place."""
    for period, slot in periods.items():
        q = slot.setdefault("q", {})
        ytd = slot.setdefault("ytd", {})
        bs = slot.setdefault("bs", {})

        for section, bag in (("q", q), ("ytd", ytd)):
            rev = bag.get("revenue")
            gp = bag.get("gross_profit")
            if gp is None and bag.get("revenue") is not None and bag.get("cogs") is not None:
                gp = bag["revenue"] - bag["cogs"]
                bag["gross_profit"] = gp
            if bag.get("gross_margin") is None:
                bag["gross_margin"] = safe_div(gp, rev)
                if bag["gross_margin"] is not None:
                    bag["gross_margin"] *= 100
            # other op expense (推算) = GP - R&D - SG&A - op_income
            if bag.get("other_op_expense_derived") is None:
                if all(bag.get(k) is not None for k in ("gross_profit", "rnd", "sga", "op_income")):
                    bag["other_op_expense_derived"] = (
                        bag["gross_profit"] - bag["rnd"] - bag["sga"] - bag["op_income"]
                    )
            if bag.get("op_margin") is None:
                m = safe_div(bag.get("op_income"), rev)
                bag["op_margin"] = m * 100 if m is not None else None
            if bag.get("ni_margin") is None:
                m = safe_div(bag.get("net_income"), rev)
                bag["ni_margin"] = m * 100 if m is not None else None
            # FCF (company approx without gov subsidy): CFO - capex
            cfo = bag.get("cfo")
            capex = bag.get("capex_gross")
            if bag.get("fcf_adj") is None and cfo is not None and capex is not None:
                bag["fcf_adj"] = cfo - capex
            if bag.get("fcf_margin") is None:
                m = safe_div(bag.get("fcf_adj"), rev)
                bag["fcf_margin"] = m * 100 if m is not None else None
            # net capex = capex for now (gov subsidy awaits press release)
            if bag.get("capex_net") is None and capex is not None:
                bag["capex_net"] = capex

        # BS derived
        cash = bs.get("cash")
        st = bs.get("st_investments")
        lt = bs.get("lt_securities")
        if bs.get("cash_investments") is None and any(v is not None for v in (cash, st, lt)):
            if cash is not None and st is not None and lt is not None:
                bs["cash_investments"] = cash + st + lt
        st_debt = bs.get("st_debt")
        lt_debt = bs.get("lt_debt")
        if bs.get("interest_debt") is None and st_debt is not None and lt_debt is not None:
            bs["interest_debt"] = st_debt + lt_debt
        if (
            bs.get("net_cash") is None
            and bs.get("cash_investments") is not None
            and bs.get("interest_debt") is not None
        ):
            bs["net_cash"] = bs["cash_investments"] - bs["interest_debt"]
        # DIO on quarterly COGS
        inv = bs.get("inventory")
        cogs_q = q.get("cogs")
        days = period_days(periods, period)
        if bs.get("dio") is None and inv is not None and cogs_q and days:
            bs["dio"] = inv / cogs_q * days


def change_arrays(
    values: list[Optional[float]],
    bases: list[Optional[float]],
    *,
    kind: str = "pct",
) -> tuple[list[str], list[str]]:
    texts, tones = [], []
    for cur, base in zip(values, bases):
        t, tone = format_change(cur, base, kind=kind)
        texts.append(t)
        tones.append(tone)
    return texts, tones


def row(
    name: str,
    kind: str,
    fmt: str,
    values: list[Optional[float]],
    yoy_base: list[Optional[float]],
    qoq_base: list[Optional[float]] | None,
    *,
    formula: str | None = None,
    change_kind: str = "pct",
    include_qoq: bool = True,
) -> dict:
    yoy, yoy_tone = change_arrays(values, yoy_base, kind=change_kind)
    out: dict[str, Any] = {
        "kind": kind,
        "name": name,
        "fmt": fmt,
        "v": values,
        "yoy": yoy,
        "yoy_tone": yoy_tone,
        "formula": formula,
    }
    if include_qoq and qoq_base is not None:
        qoq, qoq_tone = change_arrays(values, qoq_base, kind=change_kind)
        out["qoq"] = qoq
        out["qoq_tone"] = qoq_tone
    else:
        out["qoq"] = None
        out["qoq_tone"] = None
    return out


def sec_row(name: str) -> dict:
    return {
        "kind": "s",
        "name": name,
        "fmt": "sec",
        "v": [],
        "yoy": None,
        "qoq": None,
        "yoy_tone": None,
        "qoq_tone": None,
        "formula": None,
    }


def build_quarter_cols(periods: dict) -> list[str]:
    return sorted(periods.keys(), key=lambda p: parse_period_label(p))


def annual_periods(periods: dict) -> list[str]:
    """Return FQ4-* periods that have annual (ytd/y) revenue or net_income."""
    out = []
    for p in build_quarter_cols(periods):
        fy, fq = parse_period_label(p)
        if fq != 4:
            continue
        slot = periods[p]
        if (slot.get("ytd") or {}).get("revenue") is not None or (slot.get("q") or {}).get(
            "revenue"
        ) is not None:
            # Need full-year figure
            y = (slot.get("ytd") or {}).get("revenue")
            if y is not None:
                out.append(p)
    return out


def series_vals(
    cols: list[str],
    getter: Callable[[str], Optional[float]],
) -> list[Optional[float]]:
    return [_round_amt(getter(c)) for c in cols]


def yoy_bases_q(cols: list[str], getter: Callable[[str], Optional[float]]) -> list[Optional[float]]:
    return [getter(prior_year_period(c)) for c in cols]


def qoq_bases(cols: list[str], getter: Callable[[str], Optional[float]]) -> list[Optional[float]]:
    bases = []
    for c in cols:
        try:
            bases.append(getter(prior_quarter_period(c)))
        except ValueError:
            bases.append(None)
    return bases


def build_is(periods: dict, mode: str) -> dict:
    if mode == "y":
        cols_q = annual_periods(periods)
        cols = [annual_label(parse_period_label(p)[0]) for p in cols_q]
        col_end = [(periods[p] or {}).get("end") for p in cols_q]
        section = "ytd"

        def g(field: str):
            def _inner(label: str) -> Optional[float]:
                # label is FY2026 → find FQ4
                fy = int(label.replace("FY", ""))
                p = period_label(fy, 4)
                return _get(periods, p, section, field)

            return _inner

        title = "利润表（年度）"
        include_qoq = False
        col_keys = cols
        # For yoy base mapping use annual labels
        def yoy_base_fn(field: str):
            gg = g(field)

            def _b(label: str) -> Optional[float]:
                fy = int(label.replace("FY", ""))
                return gg(annual_label(fy - 1))

            return _b

        qoq_fn = None
    else:
        cols = build_quarter_cols(periods)
        col_end = [(periods[c] or {}).get("end") for c in cols]
        section = "q" if mode == "q" else "ytd"
        title = "利润表（季度）" if mode == "q" else "利润表（累计）"
        include_qoq = mode == "q"
        col_keys = cols

        def g(field: str):
            return lambda p: _get(periods, p, section, field)

        def yoy_base_fn(field: str):
            gg = g(field)
            return lambda p: gg(prior_year_period(p))

        def qoq_fn(field: str):
            gg = g(field)
            return lambda p: gg(prior_quarter_period(p)) if include_qoq else None

    def add_amt(name, field, kind=""):
        vals = series_vals(col_keys, g(field))
        yb = [yoy_base_fn(field)(c) for c in col_keys]
        qb = [qoq_fn(field)(c) for c in col_keys] if include_qoq and qoq_fn else None
        return row(name, kind, "amt", vals, yb, qb, include_qoq=include_qoq)

    def add_ratio(name, field, formula):
        vals = series_vals(col_keys, g(field))
        yb = [yoy_base_fn(field)(c) for c in col_keys]
        qb = [qoq_fn(field)(c) for c in col_keys] if include_qoq and qoq_fn else None
        return row(
            name,
            "d",
            "pct",
            vals,
            yb,
            qb,
            formula=formula,
            change_kind="pp",
            include_qoq=include_qoq,
        )

    def add_eps(name, field, kind="b"):
        vals = series_vals(col_keys, g(field))
        yb = [yoy_base_fn(field)(c) for c in col_keys]
        qb = [qoq_fn(field)(c) for c in col_keys] if include_qoq and qoq_fn else None
        return row(name, kind, "eps", vals, yb, qb, include_qoq=include_qoq)

    # Non-GAAP from overrides
    def g_ng(field: str):
        def _inner(p: str) -> Optional[float]:
            if mode == "y":
                fy = int(p.replace("FY", ""))
                key = period_label(fy, 4)
            else:
                key = p
            ng = (periods.get(key) or {}).get("non_gaap") or {}
            return ng.get(field)

        return _inner

    rows = [
        add_amt("营业收入", "revenue", "b"),
        add_amt("销售成本", "cogs"),
        add_amt("毛利", "gross_profit", "b"),
        add_ratio("毛利率", "gross_margin", "毛利 ÷ 营业收入"),
        add_amt("研发费用", "rnd"),
        add_amt("销售及管理费用", "sga"),
        add_amt("其他营业费用（推算）", "other_op_expense_derived", "d")
        if True
        else None,
        add_amt("营业利润", "op_income", "b"),
        add_ratio("营业利润率", "op_margin", "营业利润 ÷ 营业收入"),
        add_amt("利息及其他收支", "interest_other"),
        add_amt("所得税", "tax"),
        add_amt("净利润", "net_income", "b"),
        add_ratio("净利润率", "ni_margin", "净利润 ÷ 营业收入"),
        add_eps("摊薄 EPS", "eps_diluted", "b"),
        sec_row("Non-GAAP"),
    ]
    # Fix other_op kind
    rows[6] = row(
        "其他营业费用（推算）",
        "d",
        "amt",
        series_vals(col_keys, g("other_op_expense_derived")),
        [yoy_base_fn("other_op_expense_derived")(c) for c in col_keys],
        [qoq_fn("other_op_expense_derived")(c) for c in col_keys] if include_qoq and qoq_fn else None,
        formula="毛利 − 研发 − SG&A − 营业利润",
        include_qoq=include_qoq,
    )

    # Non-GAAP rows
    for name, field, kind in [
        ("营业利润", "op_income", "i"),
        ("净利润", "net_income", "i"),
        ("摊薄 EPS", "eps_diluted", "i"),
    ]:
        vals = series_vals(col_keys, g_ng(field))
        yb = [
            g_ng(field)(prior_year_period(c) if mode != "y" else annual_label(int(c.replace("FY", "")) - 1))
            for c in col_keys
        ]
        qb = None
        if include_qoq:
            qb = []
            for c in col_keys:
                try:
                    qb.append(g_ng(field)(prior_quarter_period(c)))
                except ValueError:
                    qb.append(None)
        rows.append(
            row(
                name,
                kind,
                "eps" if field == "eps_diluted" else "amt",
                vals,
                yb,
                qb,
                include_qoq=include_qoq,
            )
        )

    # Fix col headers for ytd mode months
    if mode == "ytd":
        display_cols = []
        for c in cols:
            fy, fq = parse_period_label(c)
            months = {1: 3, 2: 6, 3: 9, 4: 12}[fq or 4]
            display_cols.append(f"{c} · {months}M")
        # Keep raw cols for range; store display in col_labels
        return {
            "title": title,
            "cols": cols,
            "col_labels": display_cols,
            "col_end": col_end,
            "rows": rows,
            "note": "GAAP 来自 SEC XBRL；Non-GAAP 仅来自新闻稿/覆盖值，不可用 XBRL 补。",
        }

    return {
        "title": title,
        "cols": cols,
        "col_end": col_end,
        "rows": rows,
        "note": "GAAP 来自 SEC XBRL；单季流量由累计相减或 FY−9M；Non-GAAP 来自新闻稿覆盖。",
    }


def build_bs(periods: dict, mode: str) -> dict:
    # BS: ytd same as q; annual = FY ends (FQ4)
    if mode == "y":
        cols_q = [p for p in annual_periods(periods)]
        cols = [annual_label(parse_period_label(p)[0]) for p in cols_q]
        col_end = [(periods[p] or {}).get("end") for p in cols_q]
        include_qoq = False

        def g(field: str):
            def _inner(label: str) -> Optional[float]:
                fy = int(label.replace("FY", ""))
                return _get(periods, period_label(fy, 4), "bs", field)

            return _inner

        def yoy_base_fn(field: str):
            gg = g(field)

            def _b(label: str) -> Optional[float]:
                fy = int(label.replace("FY", ""))
                return gg(annual_label(fy - 1))

            return _b

        qoq_fn = None
        title = "资产负债表（年度）"
        col_keys = cols
    else:
        cols = build_quarter_cols(periods)
        col_end = [(periods[c] or {}).get("end") for c in cols]
        include_qoq = mode == "q"
        title = "资产负债表（季度）" if mode == "q" else "资产负债表（累计=时点）"
        col_keys = cols

        def g(field: str):
            return lambda p: _get(periods, p, "bs", field)

        def yoy_base_fn(field: str):
            gg = g(field)
            return lambda p: gg(prior_year_period(p))

        def qoq_fn(field: str):
            gg = g(field)

            def _q(p: str) -> Optional[float]:
                try:
                    return gg(prior_quarter_period(p))
                except ValueError:
                    return None

            return _q

    def add(name, field, kind="", formula=None, fmt="amt", change_kind="pct"):
        vals = series_vals(col_keys, g(field))
        yb = [yoy_base_fn(field)(c) for c in col_keys]
        qb = [qoq_fn(field)(c) for c in col_keys] if include_qoq and qoq_fn else None
        return row(
            name,
            kind,
            fmt,
            vals,
            yb,
            qb,
            formula=formula,
            change_kind=change_kind,
            include_qoq=include_qoq,
        )

    rows = [
        sec_row("资产"),
        add("现金及现金等价物", "cash"),
        add("短期投资", "st_investments"),
        add("应收账款", "receivables"),
        add("存货", "inventory"),
        add("长期有价证券", "lt_securities"),
        add("固定资产净值", "ppe_net"),
        add("总资产", "total_assets", "b"),
        sec_row("负债与权益"),
        add("短期债务", "st_debt"),
        add("长期债务", "lt_debt"),
        add("客户合同负债（非流动）", "contract_liab_noncurrent"),
        add("总负债", "total_liabilities", "b"),
        add("股东权益", "equity", "b"),
        sec_row("关键衍生指标"),
        add("现金及投资合计", "cash_investments", "d", "现金 + 短期投资 + 长期有价证券"),
        add("有息债务合计", "interest_debt", "d", "短期债务 + 长期债务"),
        add("净现金", "net_cash", "d", "现金及投资合计 − 有息债务合计"),
        add("存货天数 DIO", "dio", "d", "存货 ÷ 本季销售成本 × 本季天数", "days", "days"),
    ]
    return {
        "title": title,
        "cols": cols,
        "col_end": col_end,
        "rows": rows,
        "note": "时点数取季末余额；环比为较上季末。",
    }


def build_cf(periods: dict, mode: str) -> dict:
    if mode == "y":
        cols_q = annual_periods(periods)
        cols = [annual_label(parse_period_label(p)[0]) for p in cols_q]
        col_end = [(periods[p] or {}).get("end") for p in cols_q]
        section = "ytd"
        include_qoq = False
        title = "现金流量表（年度）"
        col_keys = cols

        def g(field: str, sign: float = 1.0):
            def _inner(label: str) -> Optional[float]:
                fy = int(label.replace("FY", ""))
                v = _get(periods, period_label(fy, 4), section, field)
                return None if v is None else v * sign

            return _inner

        def yoy_base_fn(field: str, sign: float = 1.0):
            gg = g(field, sign)

            def _b(label: str) -> Optional[float]:
                fy = int(label.replace("FY", ""))
                return gg(annual_label(fy - 1))

            return _b

        qoq_fn = None
    else:
        cols = build_quarter_cols(periods)
        col_end = [(periods[c] or {}).get("end") for c in cols]
        section = "q" if mode == "q" else "ytd"
        include_qoq = mode == "q"
        title = "现金流量表（季度）" if mode == "q" else "现金流量表（累计）"
        col_keys = cols

        def g(field: str, sign: float = 1.0):
            def _inner(p: str) -> Optional[float]:
                v = _get(periods, p, section, field)
                return None if v is None else v * sign

            return _inner

        def yoy_base_fn(field: str, sign: float = 1.0):
            gg = g(field, sign)
            return lambda p: gg(prior_year_period(p))

        def qoq_fn(field: str, sign: float = 1.0):
            gg = g(field, sign)

            def _q(p: str) -> Optional[float]:
                try:
                    return gg(prior_quarter_period(p))
                except ValueError:
                    return None

            return _q

    def add(name, field, kind="", sign=1.0, formula=None, fmt="amt", change_kind="pct"):
        vals = series_vals(col_keys, g(field, sign))
        yb = [yoy_base_fn(field, sign)(c) for c in col_keys]
        qb = [qoq_fn(field, sign)(c) for c in col_keys] if include_qoq and qoq_fn else None
        return row(
            name,
            kind,
            fmt,
            vals,
            yb,
            qb,
            formula=formula,
            change_kind=change_kind,
            include_qoq=include_qoq,
        )

    rows = [
        sec_row("经营活动"),
        add("净利润", "net_income"),
        add("折旧及摊销", "da"),
        add("股权激励", "sbc"),
        add("经营活动现金流", "cfo", "b"),
        sec_row("投资活动"),
        add("购建固定资产", "capex_gross", sign=-1.0),
        add(
            "净 Capex（支出，公司口径）",
            "capex_net",
            "d",
            sign=-1.0,
            formula="购建 PP&E − 政府补贴（补贴待新闻稿；P1 暂等于毛 Capex）",
        ),
        sec_row("筹资活动"),
        add("偿还债务", "debt_repay", sign=-1.0),
        add("回购", "buyback", sign=-1.0),
        add("股息", "dividends", sign=-1.0),
        sec_row("自由现金流"),
        add("调整后 FCF（公司口径）", "fcf_adj", "b", formula="经营现金流 − 净 Capex"),
        add("FCF 率", "fcf_margin", "d", formula="调整后 FCF ÷ 营业收入", fmt="pct", change_kind="pp"),
    ]
    return {
        "title": title,
        "cols": cols,
        "col_end": col_end,
        "rows": rows,
        "note": "支出类 XBRL 原值为正，表中按流出为负显示。营运资本变动待后续拆分。",
    }


def build_eq(periods: dict, mode: str) -> dict:
    if mode == "y":
        cols_q = annual_periods(periods)
        cols = [annual_label(parse_period_label(p)[0]) for p in cols_q]
        col_end = [(periods[p] or {}).get("end") for p in cols_q]
        include_qoq = False
        col_keys = cols
        title = "股东权益变动表（年度）"

        def equity_at(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            return _get(periods, period_label(fy, 4), "bs", "equity")

        def ni_at(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            return _get(periods, period_label(fy, 4), "ytd", "net_income")

        def buyback_at(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            v = _get(periods, period_label(fy, 4), "ytd", "buyback")
            return None if v is None else -v

        def div_at(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            v = _get(periods, period_label(fy, 4), "ytd", "dividends")
            return None if v is None else -v

        def sbc_at(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            return _get(periods, period_label(fy, 4), "ytd", "sbc")

        def begin_eq(label: str) -> Optional[float]:
            fy = int(label.replace("FY", ""))
            return _get(periods, period_label(fy - 1, 4), "bs", "equity")

    else:
        cols = build_quarter_cols(periods)
        col_end = [(periods[c] or {}).get("end") for c in cols]
        include_qoq = mode == "q"
        col_keys = cols
        title = "股东权益变动表（季度）" if mode == "q" else "股东权益变动表（累计=时点）"
        section_flow = "q" if mode == "q" else "ytd"

        def equity_at(p: str) -> Optional[float]:
            return _get(periods, p, "bs", "equity")

        def ni_at(p: str) -> Optional[float]:
            return _get(periods, p, section_flow, "net_income")

        def buyback_at(p: str) -> Optional[float]:
            v = _get(periods, p, section_flow, "buyback")
            return None if v is None else -v

        def div_at(p: str) -> Optional[float]:
            v = _get(periods, p, section_flow, "dividends")
            return None if v is None else -v

        def sbc_at(p: str) -> Optional[float]:
            return _get(periods, p, section_flow, "sbc")

        def begin_eq(p: str) -> Optional[float]:
            try:
                return _get(periods, prior_quarter_period(p), "bs", "equity")
            except ValueError:
                return None

    def pack(name, getter, kind="", formula=None, fmt="amt", change_kind="pct"):
        vals = series_vals(col_keys, getter)
        if mode == "y":
            yb = [getter(annual_label(int(c.replace("FY", "")) - 1)) for c in col_keys]
            qb = None
        else:
            yb = [getter(prior_year_period(c)) for c in col_keys]
            qb = []
            if include_qoq:
                for c in col_keys:
                    try:
                        qb.append(getter(prior_quarter_period(c)))
                    except ValueError:
                        qb.append(None)
            else:
                qb = None
        return row(name, kind, fmt, vals, yb, qb, formula=formula, change_kind=change_kind, include_qoq=include_qoq)

    end_vals = series_vals(col_keys, equity_at)
    begin_vals = series_vals(col_keys, begin_eq)
    ni_vals = series_vals(col_keys, ni_at)
    sbc_vals = series_vals(col_keys, sbc_at)
    buy_vals = series_vals(col_keys, buyback_at)
    div_vals = series_vals(col_keys, div_at)

    other_vals: list[Optional[float]] = []
    for b, e, ni, sbc, buy, div in zip(begin_vals, end_vals, ni_vals, sbc_vals, buy_vals, div_vals):
        if e is None or b is None or ni is None:
            other_vals.append(None)
            continue
        known = ni + (sbc or 0) + (buy or 0) + (div or 0)
        other_vals.append(round(e - b - known, 2))

    # ROE annualized: q NI * 4 / avg equity
    roe_vals: list[Optional[float]] = []
    for b, e, ni in zip(begin_vals, end_vals, ni_vals):
        if ni is None or b is None or e is None or (b + e) == 0:
            roe_vals.append(None)
        else:
            roe_vals.append(round(ni * 4 / ((b + e) / 2) * 100, 2))

    def yoy_of(vals_map):
        # rebuild via pack helpers — simpler inline
        pass

    rows = [
        pack("期初股东权益", begin_eq, "b"),
        pack("净利润", ni_at),
        pack("股权激励", sbc_at),
        pack("回购", buyback_at),
        pack("股息", div_at),
        row(
            "其他合计（推算）",
            "d",
            "amt",
            other_vals,
            [None] * len(col_keys),
            [None] * len(col_keys) if include_qoq else None,
            formula="期末 − 期初 − 净利润 − SBC − 回购 − 股息",
            include_qoq=include_qoq,
        ),
        pack("期末股东权益", equity_at, "b"),
        row(
            "年化 ROE",
            "d",
            "pct",
            roe_vals,
            [None] * len(col_keys),
            [None] * len(col_keys) if include_qoq else None,
            formula="单季净利润 × 4 ÷ 平均股东权益",
            change_kind="pp",
            include_qoq=include_qoq,
        ),
    ]
    return {
        "title": title,
        "cols": cols,
        "col_end": col_end,
        "rows": rows,
        "note": "其他合计为推算项；完整 OCI 科目待后续接入。",
    }


def build_page(ticker: str) -> dict:
    cfg = load_company(ticker)
    raw = read_json(ROOT / "data" / "financials" / f"{ticker}.json")
    if not raw or not raw.get("periods"):
        raise RuntimeError(f"missing financials for {ticker}; run fetch_financials.py first")
    periods = raw["periods"]
    enrich_derived(periods)

    tables = {
        "is": {
            "q": build_is(periods, "q"),
            "ytd": build_is(periods, "ytd"),
            "y": build_is(periods, "y"),
        },
        "bs": {
            "q": build_bs(periods, "q"),
            "ytd": build_bs(periods, "ytd"),
            "y": build_bs(periods, "y"),
        },
        "cf": {
            "q": build_cf(periods, "q"),
            "ytd": build_cf(periods, "ytd"),
            "y": build_cf(periods, "y"),
        },
        "eq": {
            "q": build_eq(periods, "q"),
            "ytd": build_eq(periods, "ytd"),
            "y": build_eq(periods, "y"),
        },
    }

    return {
        "ticker": ticker.upper(),
        "updated_at": raw.get("updated_at"),
        "tables": tables,
        "mode_notes": MODE_NOTES,
        "meta": {
            "name_en": cfg.get("name_en"),
            "name_zh": cfg.get("name_zh"),
            "backfill_from": cfg.get("backfill_from"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    page = build_page(ticker)
    out = ROOT / "data" / "pages" / ticker / "financials.json"
    write_json(out, page)
    public = ROOT / "web" / "public" / "data" / "pages" / ticker / "financials.json"
    write_json(public, page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
