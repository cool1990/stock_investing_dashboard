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

    # Prefer existing sample/curated for AI text skeleton
    existing = read_json(ROOT / "data" / "pages" / ticker / "review.json", default=None)
    if existing is None:
        existing = read_json(ROOT / "web" / "public" / "sample" / "review.json", default={}) or {}

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
    page = {
        "period": period,
        "release": {
            "date": slot.get("end") or existing.get("release", {}).get("date"),
            "timing": cfg.get("release_timing", "after_close"),
            "press_url": "https://investors.micron.com/",
            "remarks_url": "https://investors.micron.com/",
        },
        "verdict": {
            "label": "超预期" if (eps_surp or 0) > 0 or (rev_surp or 0) > 0 else "待判定",
            "line": {
                "rev_surp": round(rev_surp, 4) if rev_surp is not None else None,
                "rev_surp_tone": rev_tone,
                "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
                "eps_surp_tone": eps_tone,
                "guide_vs_cons": None,
                "guide_vs_cons_tone": "na",
            },
            "summary": {
                "text": None,
                "refs": [],
                "prompt_version": "review_summary_v2",
                "status": "pending_ai",
                "placeholder": "AI 文案待手动任务包生成（P4）",
            },
            "watch": existing.get("verdict", {}).get("watch")
            or [
                {"title": "毛利率走势", "text": "关注下季指引是否低于本季", "confirmed": False, "resolved": False}
            ],
        },
        "cards": cards,
        "bridge": existing.get("bridge") or {"rows": [], "note": "拆解表待新闻稿解析（P3 深化）"},
        "guidance": {
            "next_q": "FQ1-27",
            "rows": [
                {
                    "metric": "营收",
                    "guide": f"${guide['rev_mid']}B" if guide.get("rev_mid") else None,
                    "cons": None,
                    "vs": None,
                    "vs_tone": "na",
                },
                {
                    "metric": "EPS",
                    "guide": f"${guide['eps_mid']}" if guide.get("eps_mid") else None,
                    "cons": None,
                    "vs": None,
                    "vs_tone": "na",
                },
            ],
            "note": "指引来自 config/companies/MU.yaml；共识对比在快照齐全后填充。",
        },
        "talk": existing.get("talk") or {"status": "pending_ai", "items": []},
        "ai_status": "numbers_ready_copy_pending",
    }

    # Enrich guidance vs cons from snapshot
    snap_files = sorted((ROOT / "data" / "snapshots" / ticker).glob("*.json"))
    if snap_files:
        snap = read_json(snap_files[-1]) or {}
        eps_avg = ((snap.get("periods") or {}).get("FQ1-27") or {}).get("eps", {}).get("avg")
        rev_avg = ((snap.get("periods") or {}).get("FQ1-27") or {}).get("rev", {}).get("avg")
        if guide.get("eps_mid") and eps_avg:
            vs = guide["eps_mid"] / eps_avg - 1
            page["guidance"]["rows"][1]["cons"] = round(eps_avg, 2)
            page["guidance"]["rows"][1]["vs"] = round(vs, 4)
            page["guidance"]["rows"][1]["vs_tone"] = "up" if vs > 0 else "down"
            page["verdict"]["line"]["guide_vs_cons"] = [round(vs, 4), None]
            page["verdict"]["line"]["guide_vs_cons_tone"] = ["up" if vs > 0 else "down", "na"]
        if guide.get("rev_mid") and rev_avg:
            vs = guide["rev_mid"] / rev_avg - 1
            page["guidance"]["rows"][0]["cons"] = round(rev_avg, 2)
            page["guidance"]["rows"][0]["vs"] = round(vs, 4)
            page["guidance"]["rows"][0]["vs_tone"] = "up" if vs > 0 else "down"
            gvc = page["verdict"]["line"].get("guide_vs_cons") or [None, None]
            if not isinstance(gvc, list):
                gvc = [None, None]
            gvc[1] = round(vs, 4)
            page["verdict"]["line"]["guide_vs_cons"] = gvc

    out = ROOT / "data" / "pages" / ticker / "review.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "review.json", page)
    # also period-specific path for router if used
    write_json(ROOT / "data" / "pages" / ticker / f"review-{period}.json", page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
