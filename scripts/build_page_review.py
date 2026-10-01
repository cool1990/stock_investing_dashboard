#!/usr/bin/env python3
"""Build review pages from financials + consensus. Sample copy is not reused."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.anchor import latest_8k_202_date  # noqa: E402
from scripts.lib.fiscal import (  # noqa: E402
    FiscalCalendar,
    latest_quarter_ended_before,
    parse_period_label,
    prior_quarter_period,
    prior_year_period,
    shift_period,
)
from scripts.lib.io import load_company, read_json, write_json, write_page  # noqa: E402
from scripts.lib.metrics import (  # noqa: E402
    NOT_CONNECTED,
    guide_vs_consensus,
    pre_release_level,
    same_basis_eps,
)
from scripts.lib.snapshots import latest_snapshot  # noqa: E402


def ratio_change(cur, base) -> tuple[float | None, str]:
    if cur is None or base is None or base == 0:
        return None, "na"
    if base <= 0 or (cur < 0 and base > 0):
        return None, "na"
    r = cur / base - 1
    tone = "up" if r > 0.0005 else "down" if r < -0.0005 else "flat"
    return r, tone


def release_dates(ticker: str, cfg: dict) -> dict[str, str]:
    cal = FiscalCalendar(list(cfg["fiscal"]["quarter_end_months"]))
    data = read_json(ROOT / "data" / "filings" / "watchlist.json", default={"items": []}) or {}
    out: dict[str, str] = {}
    rows = []
    for item in data.get("items") or []:
        if str(item.get("t") or "").upper() != ticker:
            continue
        if "2.02" not in (item.get("items") or []):
            continue
        filed = str(item.get("d") or "")[:10]
        if not filed:
            continue
        try:
            period = latest_quarter_ended_before(cal, filed)
        except ValueError:
            continue
        rows.append((filed, period))
    for filed, period in sorted(rows):
        out.setdefault(period, filed)
    return out


def latest_reported(fin: dict) -> str | None:
    found = []
    for period, slot in (fin.get("periods") or {}).items():
        if (slot.get("q") or {}).get("revenue") is not None:
            found.append(period)
    if not found:
        return None
    return sorted(found, key=parse_period_label)[-1]


def _fmt_rel(v: float | None) -> str | None:
    if v is None:
        return None
    return f"{v * 100:+.1f}%".replace("+", "+").replace("-", "−")


def _series(fin: dict, field: str, *, scale: float = 1.0, non_gaap: bool = False) -> dict:
    periods = sorted(
        [p for p, s in (fin.get("periods") or {}).items() if (s.get("q") or {}).get("revenue") is not None],
        key=parse_period_label,
    )
    labels = periods[-12:]

    def val_of(period: str):
        slot = (fin.get("periods") or {}).get(period) or {}
        raw = (slot.get("non_gaap") or {}).get(field) if non_gaap else (slot.get("q") or {}).get(field)
        return None if raw is None else float(raw) / scale

    yoy, qoq, values = [], [], []
    for p in labels:
        cur = val_of(p)
        try:
            yb = val_of(prior_year_period(p))
        except ValueError:
            yb = None
        try:
            qb = val_of(prior_quarter_period(p))
        except ValueError:
            qb = None
        yr, _ = ratio_change(cur, yb)
        qr, _ = ratio_change(cur, qb)
        values.append(None if cur is None else round(cur, 4))
        yoy.append(round(yr, 4) if yr is not None else None)
        qoq.append(round(qr, 4) if qr is not None else None)
    return {"labels": labels, "v": values, "yoy": yoy, "qoq": qoq}


def build_metrics(fin: dict, cfg: dict, period: str) -> dict:
    rev = _series(fin, "revenue", scale=1000.0)
    metrics = {}
    if any(v is not None for v in rev["v"]):
        struct = []
        segs = ((cfg.get("segments") or {}).get(period)) or []
        if segs:
            total = sum(float(s["rev_m"]) for s in segs) or None
            rows = []
            try:
                prev_map = {s["label"]: float(s["rev_m"]) for s in (cfg.get("segments") or {}).get(prior_quarter_period(period), [])}
            except ValueError:
                prev_map = {}
            try:
                yoy_map = {s["label"]: float(s["rev_m"]) for s in (cfg.get("segments") or {}).get(prior_year_period(period), [])}
            except Exception:
                yoy_map = {}
            for s in segs:
                rev_m = float(s["rev_m"])
                share = rev_m / total if total else None
                qoq, _ = ratio_change(rev_m, prev_map.get(s["label"]))
                yoy, _ = ratio_change(rev_m, yoy_map.get(s["label"]))
                bits = [f"占 {share * 100:.1f}%" if share is not None else ""]
                if yoy is not None:
                    bits.append(f"同比 {_fmt_rel(yoy)}")
                if qoq is not None:
                    bits.append(f"环比 {_fmt_rel(qoq)}")
                rows.append(
                    {
                        "label": s["label"],
                        "val": f"${rev_m / 1000:.2f}B",
                        "sub": " · ".join(b for b in bits if b),
                        "pct": round(share * 100, 1) if share is not None else None,
                        "tone": 1,
                    }
                )
            struct.append(
                {
                    "title": "按业务单元",
                    "src": f"{period} 8-K EX-99.1",
                    "rows": rows,
                    "note": {"text": "收入取自业绩新闻稿，不使用样例拆解。", "refs": []},
                }
            )
        metrics["rev"] = {
            "label": "营收",
            "basis": "GAAP · $B",
            "q": rev,
            "y": {"labels": [], "v": [], "yoy": [], "qoq": []},
            "hist_note": "由财务报表重算。",
            "struct": struct,
        }
    return metrics


def fcf_view(slot: dict) -> tuple[float | None, str]:
    q = slot.get("q") or {}
    derived = slot.get("derived") or {}
    if q.get("fcf_adj") is not None and derived.get("fcf_adj") == "override":
        return float(q["fcf_adj"]), "公司口径"
    if q.get("fcf_gross") is not None:
        return float(q["fcf_gross"]), "CFO−毛Capex"
    if q.get("cfo") is not None and q.get("capex_gross") is not None:
        return float(q["cfo"]) - float(q["capex_gross"]), "CFO−毛Capex"
    if q.get("fcf_adj") is not None:
        return float(q["fcf_adj"]), "公司口径" if derived.get("fcf_adj") == "override" else "推算"
    return None, "na"


def card(key, label, basis, value, unit, cur, prior, yoy_raw, *, pp=False, why=NOT_CONNECTED):
    if pp:
        def one(a, b):
            if a is None or b is None:
                return None, "na"
            d = a - b
            tone = "up" if d > 0.05 else "down" if d < -0.05 else "flat"
            return d / 100.0, tone

        yoy, yt = one(cur, yoy_raw)
        qoq, qt = one(cur, prior)
    else:
        yoy, yt = ratio_change(cur, yoy_raw)
        qoq, qt = ratio_change(cur, prior)
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
        "why": {"text": why, "refs": [], "status": "not_connected"},
    }


def guidance_block(cfg: dict, period: str, fin: dict, snap: dict | None) -> tuple[dict, list, list]:
    nxt = shift_period(period, 1)
    guide = ((cfg.get("guidance") or {}).get(nxt)) or {}
    slot = (fin.get("periods") or {}).get(period) or {}
    q = slot.get("q") or {}
    ng = slot.get("non_gaap") or {}
    try:
        yoy_slot = (fin.get("periods") or {}).get(prior_year_period(nxt)) or {}
    except ValueError:
        yoy_slot = {}
    yq = yoy_slot.get("q") or {}
    yng = yoy_slot.get("non_gaap") or {}

    rev_b = (q.get("revenue") / 1000.0) if q.get("revenue") is not None else None
    yoy_rev_b = (yq.get("revenue") / 1000.0) if yq.get("revenue") is not None else None
    eps_cur = ng.get("eps_diluted") if ng.get("eps_diluted") is not None else q.get("eps_diluted")
    eps_yoy = yng.get("eps_diluted") if yng.get("eps_diluted") is not None else yq.get("eps_diluted")

    def rel(cur, base):
        r, tone = ratio_change(cur, base)
        return (round(r, 4) if r is not None else None), tone

    rev_qoq, rev_qoq_t = rel(guide.get("rev_mid"), rev_b)
    rev_yoy, rev_yoy_t = rel(guide.get("rev_mid"), yoy_rev_b)
    eps_qoq, eps_qoq_t = rel(guide.get("eps_mid"), eps_cur)
    eps_yoy, eps_yoy_t = rel(guide.get("eps_mid"), eps_yoy)

    snap_slot = ((snap or {}).get("periods") or {}).get(nxt) or {}
    pre_eps = pre_release_level(snap_slot, "eps")
    # Revenue has no 30-day level. Only compare when we are not using the
    # post-release print that has already moved to the guide.
    pre_rev = None
    if snap and snap.get("reported_through") and shift_period(snap["reported_through"], 1) != nxt:
        pre_rev = pre_release_level(snap_slot, "rev")
    # If the snapshot predates this release, current avg is still pre-release.
    g_vs, g_tone = guide_vs_consensus(guide.get("rev_mid"), pre_rev, guide.get("eps_mid"), pre_eps)

    rows = [
        {
            "metric": "营收",
            "name": "营收",
            "v": f"${guide['rev_mid']}B" if guide.get("rev_mid") is not None else None,
            "value": f"${guide['rev_mid']}B" if guide.get("rev_mid") is not None else None,
            "qoq": rev_qoq,
            "qoq_tone": rev_qoq_t,
            "yoy": rev_yoy,
            "yoy_tone": rev_yoy_t,
            "vs_cons": g_vs[0],
            "vs_cons_tone": g_tone[0],
        },
        {
            "metric": "EPS",
            "name": "摊薄 EPS",
            "v": f"${guide['eps_mid']}" if guide.get("eps_mid") is not None else None,
            "value": f"${guide['eps_mid']}" if guide.get("eps_mid") is not None else None,
            "qoq": eps_qoq,
            "qoq_tone": eps_qoq_t,
            "yoy": eps_yoy,
            "yoy_tone": eps_yoy_t,
            "vs_cons": g_vs[1],
            "vs_cons_tone": g_tone[1],
        },
    ]
    if guide.get("gm_mid") is not None and q.get("revenue") and ng.get("gross_profit"):
        cur_gm = float(ng["gross_profit"]) / float(q["revenue"]) * 100
        d = float(guide["gm_mid"]) - cur_gm
        rows.append(
            {
                "metric": "毛利率",
                "name": "毛利率（Non-GAAP）",
                "v": f"{guide['gm_mid']}%",
                "value": f"{guide['gm_mid']}%",
                "qoq": f"{d:+.1f}pp".replace("-", "−"),
                "qoq_tone": "up" if d > 0.05 else "down" if d < -0.05 else "flat",
                "yoy": None,
                "yoy_tone": "na",
                "vs_cons": None,
                "vs_cons_tone": "na",
            }
        )
    block = {
        "groups": [{"title": f"下季指引 {nxt}", "rows": rows}],
        "reasons": {"text": NOT_CONNECTED, "refs": [], "status": "not_connected"},
    }
    return block, g_vs, g_tone


def build_one(ticker: str, period: str, cfg: dict, fin: dict, releases: dict[str, str]) -> dict:
    periods = fin.get("periods") or {}
    slot = periods.get(period) or {}
    q = slot.get("q") or {}
    prior = periods.get(prior_quarter_period(period)) or {}
    yoy_p = periods.get(prior_year_period(period)) or {}
    pq, py = prior.get("q") or {}, yoy_p.get("q") or {}
    ng = slot.get("non_gaap") or {}
    png = prior.get("non_gaap") or {}
    yng = yoy_p.get("non_gaap") or {}

    rev = q.get("revenue")
    rev_b = rev / 1000.0 if rev is not None else None
    gp = q.get("gross_profit")
    gm = (gp / rev * 100) if gp is not None and rev else None
    op = q.get("op_income")
    opm = (op / rev * 100) if op is not None and rev else None
    ni = q.get("net_income")
    nim = (ni / rev * 100) if ni is not None and rev else None
    use_ng = ng.get("eps_diluted") is not None
    eps = ng.get("eps_diluted") if use_ng else q.get("eps_diluted")
    prior_eps = same_basis_eps(png.get("eps_diluted"), pq.get("eps_diluted"), non_gaap_card=use_ng)
    yoy_eps = same_basis_eps(yng.get("eps_diluted"), py.get("eps_diluted"), non_gaap_card=use_ng)

    fcf, fcf_basis = fcf_view(slot)
    prior_fcf, prior_basis = fcf_view(prior)
    yoy_fcf, yoy_basis = fcf_view(yoy_p)
    if fcf_basis != prior_basis:
        prior_fcf = None
    if fcf_basis != yoy_basis:
        yoy_fcf = None

    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    eps_surp = rev_surp = None
    eps_tone = rev_tone = "na"
    for row in (((cons.get("history") or {}).get("eps") or {}).get("q")) or []:
        if row.get("period") == period and row.get("actual") is not None and row.get("consensus"):
            eps_surp = row["actual"] / row["consensus"] - 1
            eps_tone = "up" if eps_surp > 0 else "down"
            break
    for row in (((cons.get("history") or {}).get("rev") or {}).get("q")) or []:
        if row.get("period") == period and row.get("actual") is not None and row.get("consensus"):
            rev_surp = row["actual"] / row["consensus"] - 1
            rev_tone = "up" if rev_surp > 0 else "down"
            break

    prior_gm = (pq["gross_profit"] / pq["revenue"] * 100) if pq.get("gross_profit") and pq.get("revenue") else None
    yoy_gm = (py["gross_profit"] / py["revenue"] * 100) if py.get("gross_profit") and py.get("revenue") else None
    prior_opm = (pq["op_income"] / pq["revenue"] * 100) if pq.get("op_income") and pq.get("revenue") else None
    yoy_opm = (py["op_income"] / py["revenue"] * 100) if py.get("op_income") and py.get("revenue") else None
    prior_nim = (pq["net_income"] / pq["revenue"] * 100) if pq.get("net_income") and pq.get("revenue") else None
    yoy_nim = (py["net_income"] / py["revenue"] * 100) if py.get("net_income") and py.get("revenue") else None

    cards = [
        card("rev", "营收", "GAAP", round(rev_b, 2) if rev_b is not None else None, "B", rev, pq.get("revenue"), py.get("revenue")),
        card("gm", "毛利率", "GAAP", round(gm, 1) if gm is not None else None, "%", gm, prior_gm, yoy_gm, pp=True),
        card("opm", "营业利润率", "GAAP", round(opm, 1) if opm is not None else None, "%", opm, prior_opm, yoy_opm, pp=True),
        card("nim", "净利润率", "GAAP", round(nim, 1) if nim is not None else None, "%", nim, prior_nim, yoy_nim, pp=True),
        card(
            "eps",
            "摊薄 EPS",
            "Non-GAAP" if use_ng else "GAAP",
            eps,
            "$",
            eps,
            prior_eps,
            yoy_eps,
        ),
        card(
            "fcf",
            "自由现金流",
            fcf_basis,
            round(fcf / 1000.0, 2) if fcf is not None else None,
            "B",
            fcf,
            prior_fcf,
            yoy_fcf,
        ),
    ]
    if rev_surp is not None:
        cards[0]["vs_cons"] = round(rev_surp, 4)
        cards[0]["vs_cons_tone"] = rev_tone
    if eps_surp is not None:
        cards[4]["vs_cons"] = round(eps_surp, 4)
        cards[4]["vs_cons_tone"] = eps_tone

    snap = latest_snapshot(ticker)
    guidance, g_vs, g_tone = guidance_block(cfg, period, fin, snap)
    released = releases.get(period)
    watches = []
    gm_row = next((r for r in guidance["groups"][0]["rows"] if r["metric"] == "毛利率"), None)
    if gm_row and isinstance(gm_row.get("qoq"), str):
        watches.append(
            {
                "title": "下季毛利率指引",
                "text": f"Non-GAAP 指引相对本季 {gm_row['qoq']}（由新闻稿数字算出，未人工确认）",
                "confirmed": False,
                "resolved": False,
            }
        )
    return {
        "period": period,
        "content_origin": "pipeline",
        "release": {
            "date": released,
            "timing": cfg.get("release_timing", "after_close"),
            "press_url": (cfg.get("ir") or {}).get("press_url"),
            "remarks_url": None,
        },
        "verdict": {
            "label": "超预期" if (eps_surp or 0) > 0 or (rev_surp or 0) > 0 else "待判定",
            "line": {
                "rev_surp": round(rev_surp, 4) if rev_surp is not None else None,
                "rev_surp_tone": rev_tone,
                "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
                "eps_surp_tone": eps_tone,
                "guide_vs_cons": g_vs,
                "guide_vs_cons_tone": g_tone,
            },
            "summary": {
                "text": NOT_CONNECTED + "：解读文案没有自动数据源，需手动 AI 任务。此页不使用样例总结。",
                "refs": [],
                "prompt_version": "review_summary_v2",
                "status": "not_connected",
            },
            "watch": watches,
        },
        "cards": cards,
        "metrics": build_metrics(fin, cfg, period),
        "guidance": guidance,
        "talk": {"mgmt": [], "qa": []},
        "ai_status": "not_connected",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="", help="default: latest reported quarter")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    fin = read_json(ROOT / "data" / "financials" / f"{ticker}.json", default={}) or {}
    releases = release_dates(ticker, cfg)
    target = args.period or latest_reported(fin)
    if not target:
        print(f"no reported period for {ticker}", file=sys.stderr)
        return 1
    periods = [
        p
        for p, slot in (fin.get("periods") or {}).items()
        if (slot.get("q") or {}).get("revenue") is not None
    ]
    periods = sorted(periods, key=parse_period_label)
    # Keep recent quarters so #/T/review/FQx links resolve.
    build_set = periods[-8:]
    if target not in build_set:
        build_set.append(target)
    pages = {}
    for period in build_set:
        pages[period] = build_one(ticker, period, cfg, fin, releases)
        write_json(ROOT / "data" / "pages" / ticker / f"review-{period}.json", pages[period])
        write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / f"review-{period}.json", pages[period])
    latest = pages.get(target) or pages[build_set[-1]]
    write_page(f"{ticker}/review.json", latest)
    print(f"wrote review {ticker} latest={latest['period']} ({len(pages)} periods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
