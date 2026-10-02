#!/usr/bin/env python3
"""Build data/pages/watchlist.json for every ticker in watchlist.yaml."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import parse_period_label  # noqa: E402
from scripts.lib.io import load_company, read_json, update_status, write_json  # noqa: E402
from scripts.lib.metrics import NOT_CONNECTED, keep_count  # noqa: E402


def bj_now() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def load_watchlist() -> dict:
    with (ROOT / "config" / "watchlist.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def tone_pct(p: float | None) -> str:
    if p is None:
        return "na"
    if abs(p) < 0.05:
        return "flat"
    return "up" if p > 0 else "down"


def _finite(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or abs(x) == float("inf"):
        return None
    return x


def price_stats(closes: dict) -> tuple[float | None, float | None, float | None]:
    if not closes:
        return None, None, None
    keys = [k for k in sorted(closes.keys()) if _finite(closes[k]) is not None]
    if not keys:
        return None, None, None
    last = _finite(closes[keys[-1]])
    d1 = None
    if last is not None and len(keys) >= 2:
        prev = _finite(closes[keys[-2]])
        if prev:
            d1 = (last / prev - 1) * 100
    ytd = None
    y0 = f"{keys[-1][:4]}-01-01"
    base_k = None
    for k in reversed(keys):
        if k <= y0:
            base_k = k
            break
    if last is not None and base_k:
        base = _finite(closes[base_k])
        if base:
            ytd = (last / base - 1) * 100
    return last, d1, ytd


def fmt_mcap(price: float | None, shares: float | None, mcap_raw: float | None) -> str | None:
    mcap_b = None
    if price and shares:
        mcap_b = price * shares / 1e9
    elif mcap_raw:
        mcap_b = float(mcap_raw) / 1e9
    if mcap_b is None:
        return None
    if mcap_b >= 1000:
        return f"${mcap_b / 1000:.2f}T"
    return f"${mcap_b:.1f}B"


def ntm_and_rev(ticker: str) -> tuple[float | None, float | None, str, float | None]:
    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    ntm = ((cons.get("future") or {}).get("pe") or {}).get("ntm_eps")
    header_fpe = ((cons.get("meta") or {}).get("header") or {}).get("forward_pe_ntm")
    rev = cons.get("revision") or {}
    keys = sorted((k for k in rev if str(k).startswith("FQ")), key=parse_period_label)
    rev30 = None
    if keys:
        points = (rev[keys[0]] or {}).get("points") or []
        by_d = {p[0]: p[1] for p in points}
        cur = by_d.get(0)
        if cur is None and points:
            cur = points[-1][1]
        d30 = by_d.get(30)
        if d30 is None and points:
            d30 = sorted(points, key=lambda x: abs(x[0] - 30))[0][1]
        if cur and d30:
            rev30 = cur / d30 - 1
    tone = "na" if rev30 is None else ("up" if rev30 > 0.01 else "down" if rev30 < -0.01 else "flat")
    return (float(ntm) if ntm else None), rev30, tone, (float(header_fpe) if header_fpe else None)


def next_quarter_eps(ticker: str) -> float | None:
    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    detail = (((cons.get("future") or {}).get("detail") or {}).get("eps")) or []
    for row in detail:
        if row.get("estimate") and row.get("avg") is not None:
            return float(row["avg"])
    return None


def timing_code(cfg: dict) -> str:
    raw = str(cfg.get("release_timing") or "after_close")
    if raw in ("盘后", "after", "after_close"):
        return "after_close"
    if raw in ("盘前", "before", "before_open"):
        return "before_open"
    return raw


def surprise(row: dict) -> tuple[float | None, str]:
    if row.get("actual") is None or not row.get("consensus"):
        return None, "na"
    surp = float(row["actual"]) / float(row["consensus"]) - 1
    return surp, "up" if surp > 0 else "down"


def unresolved_watch(ticker: str) -> int:
    page = read_json(ROOT / "data" / "pages" / ticker / "review.json", default={}) or {}
    n = 0
    for item in ((page.get("verdict") or {}).get("watch")) or []:
        if not item.get("confirmed") and not item.get("resolved"):
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-missing-prices", action="store_true", default=False)
    args = parser.parse_args()
    wl = load_watchlist()
    tickers_cfg = wl.get("tickers") or {}

    group_id_map = {"AI 硬件": "hw", "软件": "sw", "平台": "pf", "消费": "cn"}
    groups = [
        {"id": "all", "label": "全部"},
        {"id": "hw", "label": "AI 硬件"},
        {"id": "sw", "label": "软件"},
        {"id": "pf", "label": "平台"},
        {"id": "cn", "label": "消费"},
    ]

    filings = (read_json(ROOT / "data" / "filings" / "watchlist.json", default={"items": []}) or {}).get("items") or []
    now = datetime.now(timezone.utc).date()

    stocks = []
    calendar = []
    recent = []
    todo = 0
    for t, meta in tickers_cfg.items():
        prices = read_json(ROOT / "data" / "prices" / f"{t}.json", default=None)
        if prices is None and args.fetch_missing_prices:
            try:
                import yfinance as yf

                hist = yf.Ticker(t).history(period="1y", auto_adjust=False)
                closes = {}
                if hist is not None and not hist.empty:
                    for idx, row in hist.iterrows():
                        try:
                            d = idx.tz_convert("America/New_York").date().isoformat()
                        except Exception:  # noqa: BLE001
                            d = str(idx)[:10]
                        closes[d] = round(float(row["Close"]), 4)
                prices = {"closes": closes, "info": {}}
            except Exception as e:  # noqa: BLE001
                print(f"price fetch {t}: {e}", file=sys.stderr)
                prices = {"closes": {}, "info": {}}
        prices = prices or {"closes": {}, "info": {}}
        closes = prices.get("closes") or {}
        info = prices.get("info") or {}
        price, d1, ytd = price_stats(closes)
        shares = info.get("shares_outstanding") or info.get("shares")
        mcap = fmt_mcap(price, shares, info.get("market_cap") or info.get("mcap"))

        header = read_json(ROOT / "data" / "pages" / t / "stockHeader.json", default={}) or {}
        has_page = (ROOT / "data" / "pages" / t / "stockHeader.json").exists()
        next_raw = (header.get("header") or {}).get("next_earnings") or info.get("next_earnings")
        estimated = bool(info.get("next_earnings_estimated")) or (
            isinstance(next_raw, str) and "预估" in next_raw
        )
        next_day = str(next_raw)[:10] if next_raw and len(str(next_raw)) >= 10 else None
        last_report = header.get("latest_report") if has_page else None
        last_date = header.get("latest_report_date") if has_page else None
        if last_date == "—":
            last_date = None

        ntm, rev30, r_tone, header_fpe = ntm_and_rev(t)
        fpe = header_fpe if _finite(header_fpe) is not None else None
        if fpe is None and price and ntm and ntm > 0:
            fpe = round(price / ntm, 1)
        if _finite(fpe) is None:
            fpe = None

        try:
            cfg = load_company(t)
        except Exception:  # noqa: BLE001
            cfg = {}
        timing = timing_code(cfg)

        red7 = sum(
            1
            for f in filings
            if f.get("t") == t
            and f.get("red")
            and f.get("d")
            and (now - datetime.fromisoformat(f["d"]).date()).days <= 7
        )

        cons = read_json(ROOT / "data" / "pages" / t / "consensus.json", default={}) or {}
        hist_q = (((cons.get("history") or {}).get("eps") or {}).get("q")) or []
        hist_rev = {
            r.get("period"): r for r in (((cons.get("history") or {}).get("rev") or {}).get("q") or [])
        }
        eps_surp = react = None
        eps_tone = react_tone = "na"
        if hist_q:
            last = hist_q[-1]
            eps_surp, eps_tone = surprise(last)
            cand = _finite(last.get("next_day"))
            if cand is not None:
                react = cand
                react_tone = tone_pct(react * 100 if abs(react) < 2 else react)
            for row in reversed(hist_q):
                if not row.get("release_date"):
                    continue
                surp, tone = surprise(row)
                rev_row = hist_rev.get(row.get("period")) or {}
                rsurp, rtone = surprise(rev_row)
                recent.append(
                    {
                        "d": row["release_date"],
                        "t": t,
                        "q": row["period"],
                        "eps_surp": round(surp, 4) if surp is not None else None,
                        "eps_surp_tone": tone,
                        "rev_surp": round(rsurp, 4) if rsurp is not None else None,
                        "rev_surp_tone": rtone,
                    }
                )
                if sum(1 for r in recent if r["t"] == t) >= 2:
                    break

        stocks.append(
            {
                "t": t,
                "name": (meta.get("name_en") or t).split()[0],
                "group": group_id_map.get(meta.get("group", ""), "hw"),
                "sub": meta.get("sector"),
                "has_page": has_page,
                "price": round(price, 2) if price else None,
                "d1": round(d1 / 100.0, 6) if d1 is not None else None,
                "d1_tone": tone_pct(d1),
                "ytd": round(ytd / 100.0, 6) if ytd is not None else None,
                "ytd_tone": tone_pct(ytd),
                "mcap": mcap,
                "ntm_eps": round(ntm, 2) if ntm else None,
                "rev30": round(rev30, 4) if rev30 is not None else None,
                "rev30_tone": r_tone,
                "fpe": fpe,
                "short": None,
                "short_note": NOT_CONNECTED,
                "short_date": None,
                "last": {
                    "d": last_date,
                    "q": last_report,
                    "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
                    "eps_surp_tone": eps_tone,
                },
                "react": round(react, 4) if react is not None else None,
                "react_tone": react_tone,
                "next": {
                    "d": None if estimated else next_day,
                    "approx": next_day if estimated else None,
                    "estimated": estimated,
                },
                "red7d": red7,
            }
        )
        if next_day:
            try:
                nd = datetime.fromisoformat(next_day).date()
                if 0 <= (nd - now).days <= 60:
                    calendar.append(
                        {
                            "d": next_day,
                            "t": t,
                            "timing": timing,
                            "q": last_report or "—",
                            "estimated": estimated,
                            "cons_eps": next_quarter_eps(t),
                            "iv": None,
                            "iv_note": NOT_CONNECTED,
                        }
                    )
            except ValueError:
                pass
        todo += unresolved_watch(t)

    red_items = [
        f
        for f in filings
        if f.get("red") and f.get("d") and (now - datetime.fromisoformat(f["d"]).date()).days <= 7
    ]
    up = keep_count(sum(1 for s in stocks if s.get("rev30") is not None and s["rev30"] > 0.01))
    down = keep_count(sum(1 for s in stocks if s.get("rev30") is not None and s["rev30"] < -0.01))
    cal30 = sorted(
        [c for c in calendar if 0 <= (datetime.fromisoformat(c["d"]).date() - now).days <= 30],
        key=lambda x: x["d"],
    )

    news = []
    for f in sorted(filings, key=lambda x: x.get("d") or "", reverse=True)[:40]:
        news.append(
            {
                "d": f.get("d"),
                "t": f.get("t"),
                "type": f.get("type") or f.get("form"),
                "title": f.get("title"),
                "why": f.get("why"),
                "red": bool(f.get("red")),
                "url": f.get("url"),
            }
        )

    def fpe_key(s: dict):
        return (s["fpe"] is None, s["fpe"] if s["fpe"] is not None else 0, s["t"])

    page = {
        "as_of_bj": bj_now(),
        "groups": groups,
        "kpi": {
            "red7d": {
                "n": keep_count(len(red_items)),
                "tickers": keep_count(len({f["t"] for f in red_items})),
            },
            "earn30d": {
                "n": keep_count(len(cal30)),
                "next": {"t": cal30[0]["t"], "d": cal30[0]["d"]} if cal30 else None,
            },
            "rev30d": {"up": up, "down": down},
            "todo": keep_count(todo),
        },
        "stocks": sorted(stocks, key=fpe_key),
        "news": news,
        "calendar": sorted(calendar, key=lambda x: x["d"] or ""),
        "recent": sorted(recent, key=lambda x: x.get("d") or "", reverse=True)[:12],
        "red_rules_note": "红色规则见 config/red_rules.yaml。8-K 8.01 只有标题含关键词才标红。",
    }

    out = ROOT / "data" / "pages" / "watchlist.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / "watchlist.json", page)
    update_status("watchlist_page", True, f"{len(stocks)} tickers")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
