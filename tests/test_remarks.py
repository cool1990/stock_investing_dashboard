"""Prepared-remarks segmentation and call-page wiring (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_page_call import empty_page, usable_draft, usable_remarks
from scripts.lib.remarks import initials, role_zh, segment_prepared_remarks

SAMPLE = """
Micron Technology, Inc.
Fiscal Q4 2026 Earnings Call Prepared Remarks

SATYA KUMAR, CORPORATE VICE PRESIDENT OF INVESTOR RELATIONS AND FINANCE
Welcome to Micron's fourth quarter call.

SANJAY MEHROTRA, CHAIRMAN AND CHIEF EXECUTIVE OFFICER
Thank you Satya. We delivered record revenue.

MARK MURPHY, EXECUTIVE VICE PRESIDENT AND CHIEF FINANCIAL OFFICER
Revenue was $54.2 billion.
""".strip()


def test_segment_prepared_remarks_splits_speakers():
    executives, paras = segment_prepared_remarks(SAMPLE)
    names = [e["name"] for e in executives]
    assert names == ["Satya Kumar", "Sanjay Mehrotra", "Mark Murphy"]
    assert executives[1]["role_zh"] == "董事长、总裁兼 CEO"
    assert executives[2]["ini"] == "MM"
    assert len(paras) == 3
    assert paras[0]["who"] == "Satya Kumar"
    assert paras[0]["src"] == "remarks"
    assert "Welcome" in paras[0]["en"]
    assert "record revenue" in paras[1]["en"]


def test_role_and_initials_helpers():
    assert initials("Sanjay Mehrotra") == "SM"
    assert role_zh("CHIEF FINANCIAL OFFICER") == "执行副总裁兼 CFO"
    assert role_zh("CORPORATE VICE PRESIDENT OF INVESTOR RELATIONS AND FINANCE") == (
        "投资者关系与财务副总裁"
    )


def test_usable_remarks_and_draft_gates():
    assert usable_remarks(
        {
            "content_origin": "remarks_fetch",
            "transcript": {"paras": [{"id": "p1", "en": "hi"}]},
        }
    )
    assert not usable_remarks({"content_origin": "remarks_fetch", "transcript": {"paras": []}})
    assert not usable_remarks({"content_origin": "seed", "transcript": {"paras": [{"en": "x"}]}})
    assert usable_draft({"origin": "reviewed"})
    assert not usable_draft({"origin": "sample", "status": "sample"})
    assert empty_page("FQ4-26")["content_origin"] == "not_connected"


def test_build_page_call_prefers_remarks(tmp_path: Path, monkeypatch):
    import scripts.build_page_call as mod

    root = tmp_path
    ticker = "MU"
    period = "FQ4-26"
    (root / "data" / "financials").mkdir(parents=True)
    (root / "data" / "calls" / ticker).mkdir(parents=True)
    (root / "data" / "pages" / ticker).mkdir(parents=True)
    (root / "web" / "public" / "data" / "pages" / ticker).mkdir(parents=True)
    (root / "ai" / "tasks").mkdir(parents=True)

    (root / "data" / "financials" / f"{ticker}.json").write_text(
        json.dumps({"periods": {period: {"q": {"revenue": 1}}}}),
        encoding="utf-8",
    )
    record = {
        "ticker": ticker,
        "period": period,
        "status": "原文可查",
        "content_origin": "remarks_fetch",
        "links": {"remarks_pdf": "https://example.com/r.pdf", "webcast": None, "third_party": None},
        "executives": [{"ini": "SM", "name": "Sanjay Mehrotra", "role_zh": "CEO"}],
        "guidance": [],
        "prev_period": "FQ3-26",
        "speakers": [],
        "qa_topics": [],
        "qa": [],
        "transcript": {
            "sources": [{"id": "remarks", "label": "官方准备稿"}],
            "paras": [
                {
                    "id": "p1",
                    "src": "remarks",
                    "who": "Sanjay Mehrotra",
                    "en": "Hello",
                    "zh": None,
                }
            ],
        },
        "banner": "ready",
        "remarks_status": "已获取",
    }
    (root / "data" / "calls" / ticker / f"{period}.json").write_text(
        json.dumps(record), encoding="utf-8"
    )

    import scripts.lib.io as io

    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(io, "ROOT", root)
    monkeypatch.setattr("sys.argv", ["build_page_call.py", "--ticker", ticker, "--period", period])
    assert mod.main() == 0
    page = json.loads((root / "data" / "pages" / ticker / "call.json").read_text(encoding="utf-8"))
    assert page["content_origin"] == "remarks_fetch"
    assert page["links"]["remarks_pdf"] == "https://example.com/r.pdf"
    assert page["transcript"]["paras"][0]["en"] == "Hello"
