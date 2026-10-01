#!/usr/bin/env python3
"""Build data/pages/watchlist.json from watchlist.yaml + prices + consensus + filings."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fmt import format_change  # noqa: E402
from scripts.lib.io import read_json, retry, update_status, write_json  # noqa: E402


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


def price_stats(closes: dict) -> tuple[float | None, float | None, float | None]:
    if not closes:
        return None, None, None
    keys = sorted(closes.keys())
    last = float(closes[keys[-1]])
    d1 = None
    if len(keys) >= 2:
        prev = float(closes[keys[-2]])
        if prev:
            d1 = (last / prev - 1) * 100
    ytd = None
    y0 = f"{keys[-1][:4]}-01-01"
    base_k = None
    for k in reversed(keys):
        if k <= y0:
            base_k = k
            break
    if base_k and closes[base_k]:
        ytd = (last / float(closes[base_k]) - 1) * 100
    return last, d1, ytd


def fetch_ticker_quote(ticker: str) -> dict:
    """Lightweight quote for non-MU names when prices file missing."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    hist = retry(lambda: t.history(period="1y"))
    closes = {}
    if hist is not None and not hist.empty:
        for idx, row in hist.iterrows():
            try:
                d = idx.tz_convert("America/New_York").date().isoformat()
            except Exception:  # noqa: BLE001
                d = str(idx)[:10]
            closes[d] = round(float(row["Close"]), 4)
    info = {}
    try:
        raw = t.fast_info
        info["shares"] = getattr(raw, "shares", None) or None
        info["mcap"] = getattr(raw, "market_cap", None) or None
    except Exception:  # noqa: BLE001
        pass
    return {"closes": closes, "info": info}


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


def mu_ntm_and_rev() -> tuple[float | None, float | None, str]:
    cons = read_json(ROOT / "data" / "pages" / "MU" / "consensus.json", default={}) or {}
    ntm = (cons.get("future") or {}).get("pe", {}).get("ntm_eps")
    # 30d revision from FQ1-27 revision points if present
    rev_block = (cons.get("revision") or {}).get("FQ1-27") or {}
    points = rev_block.get("points") or []
    rev30 = None
    if len(points) >= 2:
        # find ~30d and current
        by_d = {p[0]: p[1] for p in points}
        cur = by_d.get(0) or points[-1][1]
        d30 = by_d.get(30)
        if d30 is None:
            # nearest
            for d, v in sorted(points, key=lambda x: abs(x[0] - 30)):
                d30 = v
                break
        if cur and d30:
            rev30 = cur / d30 - 1
    return ntm, rev30, "na" if rev30 is None else ("up" if rev30 > 0.01 else "down" if rev30 < -0.01 else "flat")


def load_filings() -> list[dict]:
    path = ROOT / "data" / "filings" / "watchlist.json"
    return read_json(path, default={"items": []}).get("items") or []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-missing-prices", action="store_true", default=True)
    args = parser.parse_args()
    wl = load_watchlist()
    tickers_cfg = wl.get("tickers") or {}

    group_id_map = {
        "AI 硬件": "hw",
        "软件": "sw",
        "平台": "pf",
    }
    groups = [
        {"id": "all", "label": "全部"},
        {"id": "hw", "label": "AI 硬件"},
        {"id": "sw", "label": "软件"},
        {"id": "pf", "label": "平台"},
    ]

    ntm_mu, rev30_mu, rev30_tone = mu_ntm_and_rev()
    filings = load_filings()
    now = datetime.now(timezone.utc).date()

    stocks = []
    calendar = []
    for t, meta in tickers_cfg.items():
        prices = read_json(ROOT / "data" / "prices" / f"{t}.json", default=None)
        if prices is None and args.fetch_missing_prices:
            try:
                q = fetch_ticker_quote(t)
                write_json(
                    ROOT / "data" / "prices" / f"{t}.json",
                    {
                        "ticker": t,
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "source": "yahoo",
                        "closes": q["closes"],
                        "info": q.get("info") or {},
                    },
                )
                prices = read_json(ROOT / "data" / "prices" / f"{t}.json")
            except Exception as e:  # noqa: BLE001
                print(f"price fetch {t}: {e}", file=sys.stderr)
                prices = {"closes": {}, "info": {}}

        closes = (prices or {}).get("closes") or {}
        info = (prices or {}).get("info") or {}
        price, d1, ytd = price_stats(closes)
        shares = info.get("shares_outstanding") or info.get("shares")
        mcap = fmt_mcap(price, shares, info.get("market_cap") or info.get("mcap"))

        header = read_json(ROOT / "data" / "pages" / t / "stockHeader.json", default={}) or {}
        next_d = (header.get("header") or {}).get("next_earnings")
        last_report = header.get("latest_report")
        last_date = header.get("latest_report_date")

        ntm = ntm_mu if t == "MU" else None
        rev30 = rev30_mu if t == "MU" else None
        r_tone = rev30_tone if t == "MU" else "na"
        fpe = None
        if price and ntm and ntm > 0:
            fpe = round(price / ntm, 1)

        red7 = sum(
            1
            for f in filings
            if f.get("t") == t
            and f.get("red")
            and f.get("d")
            and (now - datetime.fromisoformat(f["d"]).date()).days <= 7
        )

        # surprise from consensus history for MU
        eps_surp = None
        eps_tone = "na"
        react = None
        react_tone = "na"
        if t == "MU":
            cons = read_json(ROOT / "data" / "pages" / "MU" / "consensus.json", default={}) or {}
            hist_q = (((cons.get("history") or {}).get("eps") or {}).get("q")) or []
            if hist_q:
                last = hist_q[-1]
                if last.get("actual") is not None and last.get("consensus"):
                    eps_surp = last["actual"] / last["consensus"] - 1
                    eps_tone = "up" if eps_surp > 0 else "down"
                if last.get("next_day") is not None:
                    react = last["next_day"]
                    react_tone = tone_pct(react * 100 if abs(react) < 2 else react)

        stocks.append(
            {
                "t": t,
                "name": (meta.get("name_en") or t).split()[0],
                "group": group_id_map.get(meta.get("group", ""), "hw"),
                "sub": meta.get("sector"),
                "has_page": t == "MU",
                "price": round(price, 2) if price else None,
                "d1": round(d1, 2) if d1 is not None else None,
                "d1_tone": tone_pct(d1),
                "ytd": round(ytd, 1) if ytd is not None else None,
                "ytd_tone": tone_pct(ytd),
                "mcap": mcap,
                "ntm_eps": round(ntm, 2) if ntm else None,
                "rev30": round(rev30, 4) if rev30 is not None else None,
                "rev30_tone": r_tone,
                "fpe": fpe,
                "short": None,
                "short_date": None,
                "last": {
                    "d": last_date if t == "MU" else None,
                    "q": last_report if t == "MU" else None,
                    "eps_surp": round(eps_surp, 4) if eps_surp is not None else None,
                    "eps_surp_tone": eps_tone,
                },
                "react": round(react, 4) if react is not None else None,
                "react_tone": react_tone,
                "next": {
                    "d": next_d if next_d and len(str(next_d)) >= 10 else None,
                    "approx": None if next_d and len(str(next_d)) >= 10 else (str(next_d)[:7] if next_d else None),
                },
                "red7d": red7 or None,
            }
        )
        if next_d and len(str(next_d)) >= 10:
            try:
                nd = datetime.fromisoformat(str(next_d)[:10]).date()
                if 0 <= (nd - now).days <= 60:
                    calendar.append(
                        {
                            "d": str(next_d)[:10],
                            "t": t,
                            "timing": "盘后",
                            "q": last_report or "—",
                            "cons_eps": ntm if t == "MU" else None,
                            "iv": None,
                        }
                    )
            except ValueError:
                pass

    # KPIs
    red_items = [
        f
        for f in filings
        if f.get("red") and f.get("d") and (now - datetime.fromisoformat(f["d"]).date()).days <= 7
    ]
    up = sum(1 for s in stocks if s.get("rev30") is not None and s["rev30"] > 0.01)
    down = sum(1 for s in stocks if s.get("rev30") is not None and s["rev30"] < -0.01)
    cal30 = [c for c in calendar if 0 <= (datetime.fromisoformat(c["d"]).date() - now).days <= 30]

    news = []
    for f in sorted(filings, key=lambda x: x.get("d") or "", reverse=True)[:30]:
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

    # Recent releases from MU history
    recent = []
    cons = read_json(ROOT / "data" / "pages" / "MU" / "consensus.json", default={}) or {}
    for row in list(reversed((((cons.get("history") or {}).get("eps") or {}).get("q")) or []))[:6]:
        if not row.get("release_date"):
            continue
        surp = None
        tone = "na"
        if row.get("actual") is not None and row.get("consensus"):
            surp = row["actual"] / row["consensus"] - 1
            tone = "up" if surp > 0 else "down"
        recent.append(
            {
                "d": row["release_date"],
                "t": "MU",
                "q": row["period"],
                "eps_surp": round(surp, 4) if surp is not None else None,
                "eps_surp_tone": tone,
                "rev_surp": None,
                "rev_surp_tone": "na",
            }
        )

    page = {
        "as_of_bj": bj_now(),
        "groups": groups,
        "kpi": {
            "red7d": {
                "n": len(red_items) if filings else None,
                "tickers": len({f["t"] for f in red_items}) if filings else None,
            },
            "earn30d": {
                "n": len(cal30) if cal30 else None,
                "next": {"t": cal30[0]["t"], "d": cal30[0]["d"]} if cal30 else None,
            },
            "rev30d": {"up": up or None, "down": down or None},
            "todo": None,
        },
        "stocks": stocks,
        "news": news,
        "calendar": sorted(calendar, key=lambda x: x["d"] or ""),
        "recent": recent,
        "red_rules_note": "红色规则见 config/red_rules.yaml（8-K 2.02/5.02 等）。",
    }

    out = ROOT / "data" / "pages" / "watchlist.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / "watchlist.json", page)
    update_status("watchlist_page", True, f"{len(stocks)} tickers")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
