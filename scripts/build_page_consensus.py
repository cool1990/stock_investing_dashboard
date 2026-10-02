#!/usr/bin/env python3
"""Merge the latest dated Yahoo snapshot + prices into consensus.json."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import FiscalCalendar, months_remaining_in_fy, parse_period_label  # noqa: E402
from scripts.lib.fmt import format_pct  # noqa: E402
from scripts.lib.io import load_company, read_json, write_page  # noqa: E402
from scripts.lib.ntm import ntm_from_annuals, ntm_from_quarters  # noqa: E402
from scripts.lib.snapshots import latest_snapshot, latest_snapshot_path  # noqa: E402


def bj_now() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def ntm_eps_from_snap(snap: dict, cal: FiscalCalendar, as_of) -> tuple[float | None, str]:
    """Twelve-month EPS. Two quarters are not summed and shown as NTM."""
    periods = snap.get("periods") or {}
    annuals: list[tuple[str, float]] = []
    quarters: list[tuple[str, float]] = []
    for name, slot in periods.items():
        avg = (slot.get("eps") or {}).get("avg")
        if avg is None:
            continue
        if str(name).startswith("FY") or slot.get("type") == "y":
            annuals.append((name, float(avg)))
        elif str(name).startswith("FQ") or slot.get("type") == "q":
            quarters.append((name, float(avg)))
    annuals.sort(key=lambda x: parse_period_label(x[0])[0])
    if len(annuals) >= 2:
        months = months_remaining_in_fy(cal, as_of)
        return ntm_from_annuals(annuals[:2], months)
    quarters.sort(key=lambda x: parse_period_label(x[0]))
    return ntm_from_quarters([v for _, v in quarters])


def revision_note(period: str, points: list, guide: float | None) -> str:
    if not points or len(points) < 2:
        return "修正轨迹数据不足。"
    cur = points[-1][1]
    d90 = points[0][1]
    d30 = None
    for d, v in points:
        if d == 30:
            d30 = v
            break
    if d30 is None and len(points) >= 3:
        d30 = points[min(2, len(points) - 1)][1]
    move_30 = abs((cur / d30 - 1) * 100) if d30 else 0
    lines = []
    if len(points) >= 3:
        early = points[1][1]
        if d90 and abs((early / d90 - 1) * 100) > abs(move_30) + 5:
            lines.append(
                f"大部分上修发生在 60–90 天前（${d90:.2f} → ${early:.2f}），之后走势放缓。"
            )
    if d30 and move_30 < 1 and guide is not None and cur < guide:
        lines.append("近 30 天修正 < 1% 且共识低于指引。")
    elif d30 and move_30 < 1:
        lines.append("近 30 天修正很小。")
    elif d30:
        lines.append(f"近 30 天修正 {format_pct(cur, d30)}。")
    if guide is not None:
        lines.append(f"公司指引中值 ${guide:.2f}，相对当前共识 {format_pct(cur, guide)}。")
    else:
        lines.append(f"{period} 无公司指引。")
    if d90:
        lines.append(f"90 天累计修正 {format_pct(cur, d90)}。")
    return "".join(lines)


def _empty_hist() -> dict:
    return {
        "q": [],
        "y": [],
        "stats_q": {
            "beat_count": "0 / 0",
            "beat_sub": "暂无已公布季度",
            "avg_surprise": "—",
            "avg_surprise_sub": "由历史行重算",
            "vs_guide": "—",
            "vs_guide_sub": "没有指引的季度不计入",
            "cons_vs_guide": "—",
            "cons_vs_guide_sub": "没有指引的季度不计入",
        },
        "stats_y": {
            "fy26_vs_cons": "—",
            "fy26_sub": "年度行由历史重算",
            "fy25_vs_cons": "—",
            "fy25_sub": "年度行由历史重算",
        },
        "note_q": "历史统计由管道根据已录入的发布前共识重算。",
        "note_y": "年度行没有全年指引时，相对指引为空。",
    }


def empty_consensus_page(ticker: str, cfg: dict) -> dict:
    months = list((cfg.get("fiscal") or {}).get("quarter_end_months") or [3, 6, 9, 12])
    labels = [f"Q{i + 1} · {months[i]}月" for i in range(4)] + ["全年"]
    return {
        "meta": {
            "ticker": ticker,
            "name_en": cfg.get("name_en"),
            "name_zh": cfg.get("name_zh"),
            "exchange": cfg.get("exchange"),
            "sector": cfg.get("sector"),
            "updated_at_bj": bj_now(),
            "latest_report": "—",
            "latest_report_date": "—",
            "release_timing": cfg.get("release_timing", "after_close"),
            "snapshot_note": "尚无共识快照。",
            "quarter_labels": labels,
            "header": {},
        },
        "future": {
            "years": [],
            "est_years": [],
            "eps": {},
            "rev": {},
            "detail": {"eps": [], "rev": [], "eps_note": "", "rev_note": ""},
            "pe": {
                "ttm_eps": None,
                "ntm_eps": None,
                "ntm_method": "incomplete_ntm_hidden",
                "fy": {},
                "last_close": None,
                "note": "NTM 在缺少两个财年共识、且不足 4 个季度时不显示。",
            },
        },
        "revision": {},
        "history": {"eps": _empty_hist(), "rev": _empty_hist()},
    }


def _ensure_year(page: dict, fy_key: str, *, estimate: bool) -> None:
    future = page["future"]
    if fy_key not in future["years"]:
        future["years"].append(fy_key)
        future["years"].sort(key=lambda y: int(y[2:]))
    if estimate and fy_key not in future["est_years"]:
        future["est_years"].append(fy_key)
        future["est_years"].sort(key=lambda y: int(y[2:]))
    for metric in ("eps", "rev"):
        arr = future[metric].setdefault(fy_key, [None, None, None, None, None])
        while len(arr) < 5:
            arr.append(None)


def _fmt_surprise(rows: list[dict]) -> str:
    usable = [
        r
        for r in rows
        if r.get("actual") is not None and r.get("consensus")
    ]
    last = usable[-8:]
    if not last:
        return "0 / 0", "暂无已公布季度", "—", "由历史行重算"
    beats = sum(1 for r in last if float(r["actual"]) > float(r["consensus"]))
    surps = [float(r["actual"]) / float(r["consensus"]) - 1 for r in last]
    avg = sum(surps) / len(surps)
    latest = surps[-1]
    return (
        f"{beats} / {len(last)}",
        f"近 {len(last)} 期高于共识 {beats} 次",
        format_pct(1 + avg, 1),
        f"最近一期 {format_pct(1 + latest, 1)}",
    )


def _vs(rows: list[dict], num_key: str, den_key: str) -> tuple[str, str]:
    pairs = [
        r
        for r in rows
        if r.get(num_key) is not None and r.get(den_key)
    ]
    if not pairs:
        return "—", "没有同时具备两侧数字的期间"
    ratios = [float(r[num_key]) / float(r[den_key]) - 1 for r in pairs]
    avg = sum(ratios) / len(ratios)
    return format_pct(1 + avg, 1), f"有指引的 {len(pairs)} 期平均"


def recompute_history_stats(page: dict) -> None:
    for metric in ("eps", "rev"):
        block = page["history"][metric]
        q = block.get("q") or []
        y = block.get("y") or []
        beat, beat_sub, avg, avg_sub = _fmt_surprise(q)
        vs_g, vs_g_sub = _vs(q, "actual", "guide")
        c_g, c_g_sub = _vs(q, "consensus", "guide")
        block["stats_q"] = {
            "beat_count": beat,
            "beat_sub": beat_sub,
            "avg_surprise": avg,
            "avg_surprise_sub": avg_sub,
            "vs_guide": vs_g,
            "vs_guide_sub": vs_g_sub,
            "cons_vs_guide": c_g,
            "cons_vs_guide_sub": c_g_sub,
        }
        def year_line(label: str) -> tuple[str, str]:
            row = next((r for r in y if r.get("period") == label), None)
            if not row or row.get("actual") is None or not row.get("consensus"):
                return "—", f"{label} 尚未同时具备实际与发布前共识"
            return (
                format_pct(float(row["actual"]), float(row["consensus"])),
                "发布前共识 vs 实际，由历史行重算",
            )

        reported_years = [r for r in y if r.get("actual") is not None and r.get("period")]
        latest_y = reported_years[-1] if reported_years else None
        prior_y = reported_years[-2] if len(reported_years) >= 2 else None
        latest_v, latest_sub = year_line(latest_y["period"]) if latest_y else ("—", "没有已公布年度")
        prior_v, prior_sub = year_line(prior_y["period"]) if prior_y else ("—", "没有更早的年度")
        block["stats_y"] = {
            "latest_label": latest_y["period"] if latest_y else "最近财年",
            "latest_vs_cons": latest_v,
            "latest_sub": latest_sub,
            "prior_label": prior_y["period"] if prior_y else "上一财年",
            "prior_vs_cons": prior_v,
            "prior_sub": prior_sub,
        }
        warns = []
        for r in q:
            sec = r.get("secondary")
            cons = r.get("consensus")
            if sec and cons and abs(float(sec) / float(cons) - 1) > 0.03:
                warns.append(r.get("period"))
        if warns:
            block["note_q"] = "两个来源的发布前共识相差超过 3%：" + "、".join(warns) + "。"
        else:
            block["note_q"] = "历史统计由管道根据已录入的发布前共识重算，不再沿用样例说明。"
        block["note_y"] = "年度统计由历史行重算。没有全年指引时，相对指引为空。"


def apply_snapshot(page: dict, snap: dict, cfg: dict, as_of) -> None:
    periods = snap.get("periods") or {}
    guide_map = cfg.get("guidance") or {}
    future = page["future"]

    def upsert_detail(metric: str) -> None:
        existing = {row.get("period"): dict(row) for row in future["detail"].get(metric) or []}
        order = sorted(periods, key=lambda p: (0 if str(p).startswith("FQ") else 1, p))
        rows = []
        seen = set()
        for p in order:
            slot = periods[p]
            src = slot.get(metric) or {}
            if src.get("avg") is None and p not in existing:
                continue
            row = existing.get(p) or {"period": p, "end": "", "guide": None}
            seen.add(p)
            for k in ("avg", "low", "high", "n", "year_ago"):
                if src.get(k) is not None:
                    row[k] = src[k]
            if metric == "eps":
                tr = slot.get("eps_trend") or {}
                if tr:
                    row["trend"] = {
                        "d7": tr.get("d7"),
                        "d30": tr.get("d30"),
                        "d60": tr.get("d60"),
                        "d90": tr.get("d90"),
                    }
            rev = slot.get("revisions") or {}
            if rev:
                row["revisions"] = {"up30": rev.get("up30"), "down30": rev.get("down30")}
            g = guide_map.get(p) or {}
            if metric == "eps" and g.get("eps_mid") is not None:
                row["guide"] = g["eps_mid"]
            if metric == "rev" and g.get("rev_mid") is not None:
                row["guide"] = g["rev_mid"]
            rows.append(row)
            if src.get("avg") is None:
                continue
            avg = float(src["avg"])
            if str(p).startswith("FQ"):
                try:
                    fq = int(p[2])
                    fy_key = f"FY{p.split('-')[1]}"
                    _ensure_year(page, fy_key, estimate=True)
                    if 1 <= fq <= 4:
                        future[metric][fy_key][fq - 1] = round(avg, 2)
                except (ValueError, IndexError):
                    pass
            elif str(p).startswith("FY"):
                _ensure_year(page, p, estimate=True)
                future[metric][p][4] = round(avg, 2)
        for p, row in existing.items():
            if p not in seen:
                rows.append(row)
        rows.sort(key=lambda r: str(r.get("period")))
        future["detail"][metric] = rows

    upsert_detail("eps")
    upsert_detail("rev")
    future["detail"]["eps_note"] = "详情行覆盖快照中的每一个财期；指引来自公司配置。"
    future["detail"]["rev_note"] = "营收修正家数来自 Yahoo；没有序列的字段留空，不沿用样例说明。"

    revision = page.setdefault("revision", {})
    for key, slot in periods.items():
        tr = slot.get("eps_trend") or {}
        cur = tr.get("current") or (slot.get("eps") or {}).get("avg")
        if cur is None:
            continue
        points = []
        for days, k in ((90, "d90"), (60, "d60"), (30, "d30"), (7, "d7"), (0, "current")):
            v = cur if k == "current" else tr.get(k)
            if v is not None:
                points.append([days, round(float(v), 4)])
        points = sorted(points, key=lambda x: -x[0])
        block = revision.setdefault(key, {})
        if points:
            block["points"] = points
        rev = slot.get("revisions") or {}
        if rev.get("up30") is not None:
            block["up30"] = int(rev["up30"] or 0)
        if rev.get("down30") is not None:
            block["down30"] = int(rev["down30"] or 0)
        g = (guide_map.get(key) or {}).get("eps_mid")
        block["guide"] = g
        block["n"] = (slot.get("eps") or {}).get("n") or block.get("n")
        block["note"] = revision_note(key, block.get("points") or [], g)

    cal = FiscalCalendar(list(cfg["fiscal"]["quarter_end_months"]))
    ntm, method = ntm_eps_from_snap(snap, cal, as_of)
    pe = future["pe"]
    pe["ntm_eps"] = round(ntm, 2) if ntm is not None else None
    pe["ntm_method"] = method
    for name, slot in periods.items():
        if not str(name).startswith("FY"):
            continue
        avg = (slot.get("eps") or {}).get("avg")
        if avg is not None:
            pe.setdefault("fy", {})[name] = round(float(avg), 2)
    pe["note"] = (
        "NTM 用当前财年与下一财年共识按剩余月数加权。"
        "不足 4 个季度且缺少两个财年共识时不显示，避免把两个季度加总当成一年。"
        if ntm is not None
        else "NTM 不完整，页面不显示 Forward PE。"
    )


def ttm_from_page(page: dict) -> float | None:
    future = page["future"]
    est = set(future.get("est_years") or [])
    seq: list[float] = []
    for year in future.get("years") or []:
        if year in est:
            continue
        for v in (future.get("eps") or {}).get(year, [])[:4]:
            if v is not None:
                seq.append(float(v))
    if len(seq) >= 4:
        return round(sum(seq[-4:]), 2)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    page_path = ROOT / "data" / "pages" / ticker / "consensus.json"
    page = read_json(page_path)
    if page is None:
        page = empty_consensus_page(ticker, cfg)

    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={}) or {}
    closes = prices.get("closes") or {}
    last_close = None
    for day in sorted(closes.keys(), reverse=True):
        try:
            px = float(closes[day])
        except (TypeError, ValueError):
            continue
        if px == px and abs(px) != float("inf"):
            last_close = px
            break

    page.setdefault("meta", {})
    page["meta"]["updated_at_bj"] = bj_now()
    page["meta"]["name_en"] = cfg.get("name_en", page["meta"].get("name_en"))
    page["meta"]["name_zh"] = cfg.get("name_zh", page["meta"].get("name_zh"))
    page["meta"]["ticker"] = ticker
    page.setdefault("future", {}).setdefault("pe", {})
    page["future"]["pe"]["last_close"] = round(last_close, 2) if last_close is not None else None
    page["meta"].setdefault("header", {})
    if last_close is not None:
        page["meta"]["header"]["price"] = round(last_close, 2)

    snap = latest_snapshot(ticker)
    snap_path = latest_snapshot_path(ticker)
    if snap and snap_path:
        as_of = datetime.now(timezone.utc).date()
        apply_snapshot(page, snap, cfg, as_of)
        page["meta"]["snapshot_note"] = (
            f"共识快照：Yahoo {snap_path.stem}（绝对财期，方法 {snap.get('period_method') or 'snapshot'}）。"
            "详情表遍历快照中的全部财期。"
        )

    ttm = ttm_from_page(page)
    if ttm is not None:
        page["future"]["pe"]["ttm_eps"] = ttm

    ntm = page["future"]["pe"].get("ntm_eps")
    if last_close is not None and ntm and ntm > 0:
        page["meta"]["header"]["forward_pe_ntm"] = round(last_close / ntm, 1)
    else:
        page["meta"]["header"]["forward_pe_ntm"] = None

    hist = read_json(ROOT / "data" / "history" / f"{ticker}.json", default=None)
    if hist and page.get("history"):
        for metric in ("eps", "rev"):
            for period in ("q", "y"):
                by_p = {r["period"]: r for r in hist.get(metric, {}).get(period, [])}
                block = page["history"].setdefault(metric, _empty_hist())
                rows = block.get(period) or []
                if not rows and by_p:
                    rows = list(by_p.values())
                    block[period] = rows
                for row in rows:
                    src = by_p.get(row.get("period")) or {}
                    if src.get("next_day") is not None:
                        row["next_day"] = src["next_day"]
    if page.get("history"):
        recompute_history_stats(page)

    write_page(f"{ticker}/consensus.json", page)
    print(f"wrote data/pages/{ticker}/consensus.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
