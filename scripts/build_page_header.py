#!/usr/bin/env python3
"""Build data/pages/<T>/stockHeader.json from prices + company config + financials."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import (  # noqa: E402
    FiscalCalendar,
    latest_quarter_ended_before,
    parse_period_label,
)
from scripts.lib.io import load_company, read_json, write_json  # noqa: E402
from scripts.lib.metrics import NOT_CONNECTED  # noqa: E402


def bj_now() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def last_close(closes: dict) -> tuple[Optional[str], Optional[float]]:
    if not closes:
        return None, None
    d = sorted(closes.keys())[-1]
    return d, float(closes[d])


def pct_change(closes: dict, end_date: str, start_date: str) -> Optional[float]:
    if start_date not in closes or end_date not in closes:
        # find nearest prior trading day for start
        keys = sorted(closes.keys())
        start_px = None
        for k in reversed(keys):
            if k <= start_date:
                start_px = closes[k]
                break
        end_px = closes.get(end_date)
        if start_px is None or end_px is None or start_px == 0:
            return None
        return (end_px / start_px - 1) * 100
    a, b = closes[start_date], closes[end_date]
    if a == 0:
        return None
    return (b / a - 1) * 100


def nearest_prior(closes: dict, day: str) -> Optional[str]:
    keys = sorted(closes.keys())
    for k in reversed(keys):
        if k <= day:
            return k
    return None


def fmt_pct(p: Optional[float]) -> Optional[str]:
    if p is None:
        return None
    sign = "+" if p >= 0 else "−"
    return f"{sign}{abs(p):.1f}%"


def fmt_money_b(v: Optional[float]) -> Optional[str]:
    if v is None:
        return None
    return f"${v:.1f}B"


def release_dates(ticker: str, cfg: dict) -> dict[str, str]:
    months = ((cfg.get("fiscal") or {}).get("quarter_end_months")) or []
    if len(months) != 4:
        return {}
    cal = FiscalCalendar(list(months))
    data = read_json(ROOT / "data" / "filings" / "watchlist.json", default={"items": []}) or {}
    out: dict[str, str] = {}
    rows = []
    for item in data.get("items") or []:
        if str(item.get("t") or "").upper() != ticker.upper():
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


def latest_report(financials: dict, releases: dict[str, str]) -> tuple[str, str]:
    """Latest quarter with revenue, and the 8-K 2.02 date — not the period end."""
    periods = financials.get("periods") or {}
    reported = [
        p
        for p, slot in periods.items()
        if ((slot or {}).get("q") or {}).get("revenue") is not None
    ]
    if not reported:
        return "—", "—"
    best = sorted(reported, key=lambda p: parse_period_label(p))[-1]
    return best, releases.get(best) or "—"


def build_header(ticker: str) -> dict:
    cfg = load_company(ticker)
    prices = read_json(ROOT / "data" / "prices" / f"{ticker}.json", default={}) or {}
    closes = prices.get("closes") or {}
    info = prices.get("info") or {}
    financials = read_json(ROOT / "data" / "financials" / f"{ticker}.json", default={}) or {}

    day, price = last_close(closes)
    price_1d = None
    price_ytd = None
    week52 = None
    if day and price is not None:
        keys = sorted(closes.keys())
        idx = keys.index(day)
        if idx > 0:
            prev = closes[keys[idx - 1]]
            if prev:
                price_1d = (price / prev - 1) * 100
        ytd_start = nearest_prior(closes, f"{day[:4]}-01-01")
        if ytd_start:
            base = closes[ytd_start]
            if base:
                price_ytd = (price / base - 1) * 100
        # 52w
        window = [closes[k] for k in keys if k <= day][-252:]
        if window:
            lo, hi = min(window), max(window)
            week52 = f"${lo:.0f} – ${hi:.0f}"

    shares = info.get("shares_outstanding")  # absolute
    market_cap_b = None
    if price is not None and shares:
        market_cap_b = price * shares / 1e9
    elif info.get("market_cap"):
        market_cap_b = float(info["market_cap"]) / 1e9

    # Net cash from latest BS that has the components (FQ4 may lack BS until 10-K)
    net_cash_b = cfg.get("header", {}).get("net_cash_b")
    periods = financials.get("periods") or {}
    if periods:
        for latest in sorted(periods.keys(), key=lambda p: parse_period_label(p), reverse=True):
            bs = (periods[latest] or {}).get("bs") or {}
            cash = bs.get("cash")
            st = bs.get("st_investments")
            lt = bs.get("lt_securities")
            st_d = bs.get("st_debt")
            lt_d = bs.get("lt_debt")
            if all(v is not None for v in (cash, st, lt, st_d, lt_d)):
                net_cash_b = (cash + st + lt - st_d - lt_d) / 1000.0
                break

    ev_b = None
    if market_cap_b is not None and net_cash_b is not None:
        ev_b = market_cap_b - net_cash_b

    report, report_date = latest_report(financials, release_dates(ticker, cfg))
    hdr_cfg = cfg.get("header") or {}
    nxt = hdr_cfg.get("next_earnings") or info.get("next_earnings")
    if nxt and info.get("next_earnings_estimated") and "预估" not in str(nxt):
        nxt = f"{nxt}（预估）"
    div_q = hdr_cfg.get("dividend_quarterly")
    dy = info.get("dividend_yield")

    # Forward PE from consensus page if available
    cons = read_json(ROOT / "data" / "pages" / ticker / "consensus.json", default={}) or {}
    fpe = (cons.get("meta") or {}).get("header", {}).get("forward_pe_ntm")
    if fpe is None:
        ntm = ((cons.get("future") or {}).get("pe") or {}).get("ntm_eps")
        if price is not None and ntm and ntm > 0:
            fpe = round(price / float(ntm), 1)

    header = {
        "price": round(price, 2) if price is not None else None,
        "price_1d": fmt_pct(price_1d),
        "price_ytd": fmt_pct(price_ytd),
        "market_cap": fmt_money_b(market_cap_b),
        "ev": fmt_money_b(ev_b),
        "net_cash_b": round(net_cash_b, 2) if net_cash_b is not None else None,
        "forward_pe_ntm": fpe if fpe is not None else hdr_cfg.get("forward_pe_ntm"),
        "short_interest": hdr_cfg.get("short_interest") or NOT_CONNECTED,
        "next_earnings": nxt,
        "implied_move": hdr_cfg.get("implied_move") or NOT_CONNECTED,
        "week52": week52,
        "ev_ebitda_ntm": hdr_cfg.get("ev_ebitda_ntm") or NOT_CONNECTED,
        "dividend_quarterly": div_q,
        "dividend_yield": f"{dy:.2f}%" if isinstance(dy, (int, float)) else dy,
        "target_price": info.get("target_price"),
        "ratings": info.get("ratings"),
        "inst_insider": hdr_cfg.get("inst_insider") or NOT_CONNECTED,
        "days_to_cover": hdr_cfg.get("days_to_cover") or NOT_CONNECTED,
    }

    return {
        "ticker": ticker.upper(),
        "name_en": cfg.get("name_en"),
        "name_zh": cfg.get("name_zh"),
        "exchange": cfg.get("exchange"),
        "sector": cfg.get("sector"),
        "updated_at_bj": bj_now(),
        "latest_report": report,
        "latest_report_date": report_date,
        "release_timing": cfg.get("release_timing", "after_close"),
        "header": header,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    page = build_header(ticker)
    out = ROOT / "data" / "pages" / ticker / "stockHeader.json"
    write_json(out, page)
    public = ROOT / "web" / "public" / "data" / "pages" / ticker / "stockHeader.json"
    write_json(public, page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
