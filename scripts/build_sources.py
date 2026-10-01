#!/usr/bin/env python3
"""Build data/pages/sources.json from config/sources.yaml + data/_status.json."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json, write_json  # noqa: E402

# Map sources.yaml ids → _status.json keys
STATUS_KEYS = {
    "yahoo_consensus": "yahoo_consensus",
    "yahoo_eps": "yahoo_actuals",
    "edgar_xbrl": "sec_financials",
    "edgar_filings": "edgar_filings",
    "prices": "yahoo_prices",
    "press": "press",
    "remarks": "remarks",
    "transcript": "transcript",
}


def reliability_label(raw: str) -> str:
    s = raw or ""
    if "高" in s or "稳定" in s:
        return "稳定" if "稳定" in s else "稳定"
    if "中" in s or "有条件" in s:
        return "有条件"
    if "低" in s or "不稳" in s:
        return "不稳定"
    return s or "有条件"


def main() -> int:
    with (ROOT / "config" / "sources.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    status = read_json(ROOT / "data" / "_status.json", default={"sources": {}}) or {}
    src_status = status.get("sources") or {}

    rows = []
    for s in cfg.get("sources") or []:
        sid = s.get("id")
        st_key = STATUS_KEYS.get(sid, sid)
        st = src_status.get(st_key) or {}
        ok = st.get("ok")
        state = "ok" if ok is True else "error" if ok is False else "unknown"
        rows.append(
            {
                "id": sid,
                "name": s.get("name"),
                "used": s.get("used"),
                "reliability": reliability_label(str(s.get("reliability") or "")),
                "source": s.get("source"),
                "freq": s.get("freq"),
                "missing": s.get("missing"),
                "status": {
                    "state": state,
                    "last_ok": st.get("updated_at_utc") if ok else None,
                    "last_err": st.get("updated_at_utc") if ok is False else None,
                    "err_msg": st.get("message") if ok is False else None,
                },
            }
        )

    page = {
        "intro": cfg.get("updated_note")
        or "本页列出数据来源与管道运行状态。失败时保留旧页面数据。",
        "legend": [
            {"k": "稳定", "desc": "官方、结构化，几乎不变"},
            {"k": "有条件", "desc": "依赖抓取或推算，可能缺失或延迟"},
            {"k": "不稳定", "desc": "第三方或 AI，需人工校验"},
        ],
        "rows": rows,
        "conventions": [
            "颜色：蓝=上调/超预期，橙=下调/低于预期，灰=n.m./缺失",
            "负号统一用 −（U+2212）",
            "浏览器不直连第三方 API",
        ],
    }
    out = ROOT / "data" / "pages" / "sources.json"
    write_json(out, page)
    write_json(ROOT / "web" / "public" / "data" / "pages" / "sources.json", page)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
