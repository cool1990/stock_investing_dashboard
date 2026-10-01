#!/usr/bin/env python3
"""Build review page numeric blocks from financials + consensus (AI text left pending)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fmt import format_change  # noqa: E402
from scripts.lib.fiscal import prior_quarter_period, prior_year_period  # noqa: E402
from scripts.lib.io import load_company, read_json, write_json  # noqa: E402


def ratio_change(cur, base) -> tuple[float | None, str]:
    if cur is None or base is None or base == 0:
        return None, "na"
    if base <= 0 or (cur < 0 and base > 0):
        return None, "na"
    r = cur / base - 1
    tone = "up" if r > 0.0005 else "down" if r < -0.0005 else "flat"
    return r, tone


def pp_change(cur, base) -> tuple[float | None, str]:
    if cur is None or base is None:
        return None, "na"
    d = cur - base
    tone = "up" if d > 0.05 else "down" if d < -0.05 else "flat"
    return d / 100.0, tone  # store as fraction of 1 for pp*100 display? sample uses 0.413 for +41.3pp on gm
    # sample gm yoy: 0.413 meaning +41.3pp — so store as pp/100? Actually 0.413 * 100 = 41.3pp if frontend treats as ratio
    # Looking at sample: "yoy": 0.413 for gm — frontend likely multiplies by 100 for pp
    # Actually for gm yoy from 45.5 to 86.8 = +41.3pp → stored as 0.413
    return (cur - base) / 100.0, tone


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="FQ4-26")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    period = args.period
    cfg = load_company(ticker)
    fin = read_json(ROOT / "data" / "financials" / f"{ticker}.json", default={}) or {}
    periods = fin.get("periods") or {}
    slot = periods.get(period) or {}
    q = slot.get("q") or {}
    ytd = slot.get("ytd") or {}
    prior = periods.get(prior_quarter_period(period)) or {}
    yoy_p = periods.get(prior_year_period(period)) or {}
    pq, py = prior.get("q") or {}, yoy_p.get("q") or {}

    # Prefer curated page; always keep sample metrics/talk skeleton as fallback
    sample = read_json(ROOT / "web" / "public" / "sample" / "review.json", default={}) or {}
    existing = read_json(ROOT / "data" / "pages" / ticker / "review.json", default=None) or {}
    if not existing.get("metrics"):
        existing = {**sample, **existing, "metrics": sample.get("metrics") or {}}
    if not (existing.get("talk") or {}).get("mgmt") and sample.get("talk"):
        existing.setdefault("talk", sample.get("talk"))

    rev = q.get("revenue")
    rev_b = rev / 1000.0 if rev is not None else None
    gp = q.get("gross_profit")
    gm = (gp / rev * 100) if gp is not None and rev else q.get("gross_margin")
    op = q.get("op_income")
    opm = (op / rev * 100) if op is not None and rev else q.get("op_margin")
    ni = q.get("net_income")
    nim = (ni / rev * 100) if ni is not None and rev else q.get("ni_margin")
    eps = (slot.get("non_gaap") or {}).get("eps_diluted") or q.get("eps_diluted")
    cfo = q.get("cfo")
    capex = q.get("capex_gross")
    fcf = (cfo - capex) if cfo is not None and capex is not None else q.get("fcf_adj")
    fcf_b = fcf / 1000.0 if fcf is not None else None

    # consensus surprise from history
    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    hist = (((cons.get("history") or {}).get("eps") or {}).get("q")) or []
    eps_surp = rev_surp = None
    eps_tone = rev_tone = "na"
    for row in hist:
        if row.get("period") == period:
            if row.get("actual") is not None and row.get("consensus"):
                eps_surp = row["actual"] / row["consensus"] - 1
                eps_tone = "up" if eps_surp > 0 else "down"
            break
    rev_hist = (((cons.get("history") or {}).get("rev") or {}).get("q")) or []
    for row in rev_hist:
        if row.get("period") == period and row.get("actual") is not None and row.get("consensus"):
            rev_surp = row["actual"] / row["consensus"] - 1
            rev_tone = "up" if rev_surp > 0 else "down"
            break

    def card(key, label, basis, value, unit, cur_raw, prior_raw, yoy_raw, is_pp=False):
        if is_pp:
            yoy, yt = (None, "na")
            qoq, qt = (None, "na")
            if cur_raw is not None and yoy_raw is not None:
                yoy = (cur_raw - yoy_raw) / 100.0
                yt = "up" if cur_raw - yoy_raw > 0.05 else "down" if cur_raw - yoy_raw < -0.05 else "flat"
            if cur_raw is not None and prior_raw is not None:
                qoq = (cur_raw - prior_raw) / 100.0
                qt = "up" if cur_raw - prior_raw > 0.05 else "down" if cur_raw - prior_raw < -0.05 else "flat"
        else:
            yoy, yt = ratio_change(cur_raw, yoy_raw)
            qoq, qt = ratio_change(cur_raw, prior_raw)
        return {
            "key": key,
            "label": label,
            "basis": basis,
            "value": value,
            "unit": unit,
            "yoy": round(yoy, 4) if yoy is not None else None,
            "yoy_tone": yt,
            "qoq": round(qoq, 4) if qoq is not None else None,
            "qoq_tone": qt,
            "vs_cons": None,
            "vs_cons_tone": "na",
            "why": {"text": None, "refs": [], "status": "pending_ai"},
        }

    prior_gm = (pq.get("gross_profit") / pq["revenue"] * 100) if pq.get("gross_profit") and pq.get("revenue") else None
    yoy_gm = (py.get("gross_profit") / py["revenue"] * 100) if py.get("gross_profit") and py.get("revenue") else None
    prior_opm = (pq.get("op_income") / pq["revenue"] * 100) if pq.get("op_income") and pq.get("revenue") else None
    yoy_opm = (py.get("op_income") / py["revenue"] * 100) if py.get("op_income") and py.get("revenue") else None
    prior_nim = (pq.get("net_income") / pq["revenue"] * 100) if pq.get("net_income") and pq.get("revenue") else None
    yoy_nim = (py.get("net_income") / py["revenue"] * 100) if py.get("net_income") and py.get("revenue") else None

    cards = [
        card("rev", "营收", "GAAP", round(rev_b, 2) if rev_b else None, "B", rev, pq.get("revenue"), py.get("revenue")),
        card("gm", "毛利率", "GAAP", round(gm, 1) if gm else None, "%", gm, prior_gm, yoy_gm, is_pp=True),
        card("opm", "营业利润率", "GAAP", round(opm, 1) if opm else None, "%", opm, prior_opm, yoy_opm, is_pp=True),
        card("nim", "净利润率", "GAAP", round(nim, 1) if nim else None, "%", nim, prior_nim, yoy_nim, is_pp=True),
        card("eps", "摊薄 EPS", "Non-GAAP" if (slot.get("non_gaap") or {}).get("eps_diluted") else "GAAP",
             eps, "$", eps, pq.get("eps_diluted"), py.get("eps_diluted")),
        card("fcf", "自由现金流", "GAAP 近似", round(fcf_b, 2) if fcf_b else None, "B", fcf, pq.get("fcf_adj"), py.get("fcf_adj")),
    ]
    if rev_surp is not None:
        cards[0]["vs_cons"] = round(rev_surp, 4)
        cards[0]["vs_cons_tone"] = rev_tone
    if eps_surp is not None:
        cards[4]["vs_cons"] = round(eps_surp, 4)
        cards[4]["vs_cons_tone"] = eps_tone

    guide = (cfg.get("guidance") or {}).get("FQ1-27") or {}
    # Start from sample/curated skeleton so metrics/guidance/talk match frontend schema
    page = dict(existing) if existing else {}
    page["period"] = period
    page["release"] = {
        "date": slot.get("end") or (existing.get("release") or {}).get("date"),
        "timing": cfg.get("release_timing", "after_close"),
        "press_url": "https://investors.micron.com/",
        "remarks_url": "https://investors.micron.com/",
    }
    page["verdict"] = {
        "label": "超预期" if (eps_surp or 0) > 0 or (rev_surp or 0) > 0 else "待判定",
        "line": {
            "rev_surp": round(rev_surp, 4) if rev_surp is not None else None,
            "rev_surp_tone": rev_tone,
            "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
            "eps_surp_tone": eps_tone,
            "guide_vs_cons": [None, None],
            "guide_vs_cons_tone": ["na", "na"],
        },
        "summary": {
            "text": None,
            "refs": [],
            "prompt_version": "review_summary_v2",
            "status": "pending_ai",
        },
        "watch": (existing.get("verdict") or {}).get("watch")
        or [
            {
                "title": "毛利率走势",
                "text": "关注下季指引是否低于本季",
                "confirmed": False,
                "resolved": False,
            }
        ],
    }
    page["cards"] = cards
    page["metrics"] = existing.get("metrics") or sample.get("metrics") or {}
    if not page["metrics"]:
        page["metrics"] = sample.get("metrics") or {}
    # Guidance in frontend schema: groups[].rows
    g_rows = [
        {
            "metric": "营收",
            "name": "营收",
            "v": f"${guide['rev_mid']}B" if guide.get("rev_mid") else None,
            "value": f"${guide['rev_mid']}B" if guide.get("rev_mid") else None,
            "qoq": None,
            "yoy": None,
            "vs_cons": None,
            "vs_cons_tone": "na",
        },
        {
            "metric": "EPS",
            "name": "摊薄 EPS",
            "v": f"${guide['eps_mid']}" if guide.get("eps_mid") else None,
            "value": f"${guide['eps_mid']}" if guide.get("eps_mid") else None,
            "qoq": None,
            "yoy": None,
            "vs_cons": None,
            "vs_cons_tone": "na",
        },
    ]
    page["guidance"] = {
        "groups": [{"title": "下季指引 FQ1-27", "rows": g_rows}],
        "reasons": {
            "text": None,
            "refs": [],
            "status": "pending_ai",
        },
    }
    talk = existing.get("talk") or {}
    page["talk"] = {
        "mgmt": talk.get("mgmt") or [],
        "qa": talk.get("qa") or [],
    }
    page["ai_status"] = "numbers_ready_copy_pending"

    # Enrich guidance vs cons from snapshot
    snap_files = sorted((ROOT / "data" / "snapshots" / ticker).glob("*.json"))
    if snap_files:
        snap = read_json(snap_files[-1]) or {}
        eps_avg = ((snap.get("periods") or {}).get("FQ1-27") or {}).get("eps", {}).get("avg")
        rev_avg = ((snap.get("periods") or {}).get("FQ1-27") or {}).get("rev", {}).get("avg")
        if guide.get("eps_mid") and eps_avg:
            vs = guide["eps_mid"] / eps_avg - 1
            g_rows[1]["vs_cons"] = round(vs, 4)
            g_rows[1]["vs_cons_tone"] = "up" if vs > 0 else "down"
            page["verdict"]["line"]["guide_vs_cons"][0] = round(vs, 4)
            page["verdict"]["line"]["guide_vs_cons_tone"][0] = "up" if vs > 0 else "down"
        if guide.get("rev_mid") and rev_avg:
            vs = guide["rev_mid"] / rev_avg - 1
            g_rows[0]["vs_cons"] = round(vs, 4)
            g_rows[0]["vs_cons_tone"] = "up" if vs > 0 else "down"
            page["verdict"]["line"]["guide_vs_cons"][1] = round(vs, 4)
            page["verdict"]["line"]["guide_vs_cons_tone"][1] = "up" if vs > 0 else "down"

    out = ROOT / "data" / "pages" / ticker / "review.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "review.json", page)
    # also period-specific path for router if used
    write_json(ROOT / "data" / "pages" / ticker / f"review-{period}.json", page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
