#!/usr/bin/env python3
"""Fetch company prepared-remarks PDFs into data/calls/<T>/<period>.json.

Minimal path (MU): discover the earnings-call event on the IR Q4 feed,
download the Prepared Remarks PDF, and segment it into speaker paragraphs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fiscal import parse_period_label, prior_quarter_period  # noqa: E402
from scripts.lib.io import load_company, update_status, write_json  # noqa: E402
from scripts.lib.remarks import extract_pdf_text, segment_prepared_remarks  # noqa: E402

_ORD = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}


def period_event_tokens(period: str) -> tuple[str, int]:
    fy, fq = parse_period_label(period)
    if fq is None:
        raise ValueError(f"prepared remarks need a quarterly period, got {period}")
    return _ORD[fq], fy


def discover_micron_event(feed_url: str, period: str) -> dict:
    ord_name, fy = period_event_tokens(period)
    want = re.compile(
        rf"{ord_name}\s+Quarter\s+{fy}\s+Financial\s+Call",
        re.I,
    )
    events: list[dict] = []
    for page in range(0, 6):
        url = feed_url
        if "pageNumber=" in feed_url:
            url = re.sub(r"pageNumber=\d+", f"pageNumber={page}", feed_url)
        else:
            sep = "&" if "?" in feed_url else "?"
            url = f"{feed_url}{sep}pageNumber={page}&pageSize=50"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        batch = resp.json().get("GetEventListResult") or []
        if not batch:
            break
        events.extend(batch)
    for event in events:
        title = event.get("Title") or ""
        if want.search(title):
            return event
    raise RuntimeError(f"no IR event matched {period} ({ord_name} Quarter {fy} Financial Call)")


def pick_remarks_attachment(event: dict) -> tuple[str, str | None]:
    remarks_url = None
    webcast = event.get("WebCastLink") or None
    for att in event.get("Attachments") or []:
        title = str(att.get("Title") or "")
        url = att.get("Url")
        if not url:
            continue
        if re.search(r"Prepared\s+Remarks", title, re.I):
            remarks_url = url
            break
    if not remarks_url:
        raise RuntimeError(f"event has no Prepared Remarks attachment: {event.get('Title')}")
    return remarks_url, webcast


def parse_event_start(raw: str | None) -> str | None:
    if not raw:
        return None
    # "09/30/2026 16:30:00"
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(raw[:19], fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return str(raw)[:16]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def build_call_record(ticker: str, period: str, cfg: dict, event: dict, pdf_path: Path, pdf_url: str) -> dict:
    text = extract_pdf_text(pdf_path)
    executives, paras = segment_prepared_remarks(text)
    # Prefer config executives if present (stable Chinese titles).
    cfg_exec = cfg.get("executives") or []
    if cfg_exec:
        by_name = {e["name"].lower(): e for e in executives}
        merged = []
        for e in cfg_exec:
            hit = by_name.get(str(e.get("name", "")).lower())
            merged.append({**e, **({"role_en": hit.get("role_en")} if hit else {})})
        # keep any PDF-only speakers after config ones
        cfg_names = {e["name"].lower() for e in cfg_exec}
        for e in executives:
            if e["name"].lower() not in cfg_names:
                merged.append(e)
        executives = merged

    _, webcast = pick_remarks_attachment(event)
    try:
        prev = prior_quarter_period(period)
    except ValueError:
        prev = ""

    return {
        "ticker": ticker,
        "period": period,
        "date_et": parse_event_start(event.get("StartDate")),
        "duration_min": None,
        "status": "原文可查",
        "content_origin": "remarks_fetch",
        "ai_status": "not_connected",
        "links": {
            "remarks_pdf": pdf_url,
            "webcast": webcast,
            "third_party": None,
            "event_page": urljoin(
                "https://investors.micron.com",
                event.get("LinkToDetailPage") or "",
            )
            if event.get("LinkToDetailPage")
            else None,
        },
        "executives": [
            {"ini": e.get("ini"), "name": e.get("name"), "role_zh": e.get("role_zh")}
            for e in executives
        ],
        "guidance": [],
        "prev_period": prev,
        "speakers": [],
        "qa_topics": [],
        "qa": [],
        "transcript": {
            "sources": [
                {
                    "id": "remarks",
                    "label": "官方准备稿",
                    "note": "来自公司 IR Prepared Remarks PDF",
                }
            ],
            "paras": paras,
        },
        "corrections": [],
        "remarks_status": "已获取",
        "banner": (
            f"{period} 已接入官方准备稿（{len(paras)} 段）。"
            "要点 / 问答摘要仍未接入，需 AI 任务包。"
        ),
        "source": {
            "event_title": event.get("Title"),
            "pdf": pdf_url,
            "pdf_local": str(pdf_path.relative_to(ROOT)),
            "chars": len(text),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--period", default="")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    ir = cfg.get("ir") or {}
    period = args.period
    if not period:
        # default: latest quarter with revenue in financials
        from scripts.lib.io import read_json

        fin = read_json(ROOT / "data" / "financials" / f"{ticker}.json", default={}) or {}
        periods = [
            p
            for p, slot in (fin.get("periods") or {}).items()
            if (slot.get("q") or {}).get("revenue") is not None
        ]
        if not periods:
            print("no financial period to attach remarks to", file=sys.stderr)
            return 1
        from scripts.lib.fiscal import parse_period_label as _p

        period = sorted(periods, key=_p)[-1]

    feed = ir.get("events_feed")
    if not feed:
        print(f"{ticker}: ir.events_feed not configured", file=sys.stderr)
        return 1

    try:
        event = discover_micron_event(feed, period)
        pdf_url, _webcast = pick_remarks_attachment(event)
        pdf_path = ROOT / "data" / "raw" / ticker / "remarks" / f"{period}.pdf"
        download(pdf_url, pdf_path)
        record = build_call_record(ticker, period, cfg, event, pdf_path, pdf_url)
        out = ROOT / "data" / "calls" / ticker / f"{period}.json"
        write_json(out, record)
        # keep a short text extract for AI task packs / audit
        text_path = ROOT / "data" / "raw" / ticker / "remarks" / f"{period}.txt"
        text_path.write_text(
            "\n\n".join(f"{p['who']}: {p['en']}" for p in record["transcript"]["paras"]) + "\n",
            encoding="utf-8",
        )
        update_status("remarks", True, f"{ticker} {period} {len(record['transcript']['paras'])} paras")
        print(f"wrote {out} ({len(record['transcript']['paras'])} paras)")
        return 0
    except Exception as e:  # noqa: BLE001
        update_status("remarks", False, str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
