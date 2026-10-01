"""P1 acceptance: cumulative subtraction, FY23 n.m., qoq mode rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.fiscal import period_label, prior_quarter_period, prior_year_period
from scripts.lib.fmt import NM, format_change, format_growth
from scripts.fetch_financials import resolve_quarterly

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def financials() -> dict:
    path = ROOT / "data" / "financials" / "MU.json"
    if not path.exists():
        pytest.skip("data/financials/MU.json missing — run fetch_financials.py")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page() -> dict:
    path = ROOT / "data" / "pages" / "MU" / "financials.json"
    if not path.exists():
        pytest.skip("financials page JSON missing — run build_page_financials.py")
    return json.loads(path.read_text(encoding="utf-8"))


def test_fq4_26_income_statement_acceptance(financials: dict):
    p = financials["periods"]["FQ4-26"]
    assert p["q"]["revenue"] == 54229
    assert p["q"]["net_income"] == 37701
    assert p["q"]["eps_diluted"] == 32.87
    assert (p.get("non_gaap") or {}).get("eps_diluted") == 33.42


def test_fq4_26_cfo_fy_minus_9m(financials: dict):
    """43,973 = FY26 89,675 − 9M 45,702."""
    fy = financials["periods"]["FQ4-26"]["ytd"]["cfo"]
    q3 = financials["periods"]["FQ3-26"]["ytd"]["cfo"]
    q4 = financials["periods"]["FQ4-26"]["q"]["cfo"]
    assert fy == 89675
    assert q3 == 45702
    assert q4 == fy - q3 == 43973


def test_ytd_diff_q3_cfo(financials: dict):
    series = {
        "FQ2-26": {"ytd": 20314.0, "q": None, "y": None, "bs": None},
        "FQ3-26": {"ytd": 45702.0, "q": None, "y": None, "bs": None},
    }
    # Build minimal series dict shape used by resolve_quarterly
    full = {
        k: {"q": v["q"], "ytd": v["ytd"], "y": v["y"], "bs": v["bs"]}
        for k, v in series.items()
    }
    val, how = resolve_quarterly(full, "FQ3-26")
    assert how == "ytd_diff"
    assert val == 25388.0


def test_fy23_base_yields_nm():
    text, tone = format_change(778.0, -5833.0)
    assert text == NM
    assert tone == "na"
    assert format_growth(778.0, -5833.0) == NM


def test_page_fy2024_ni_yoy_is_nm(page: dict):
    annual = page["tables"]["is"]["y"]
    cols = annual["cols"]
    assert "FY2023" in cols and "FY2024" in cols
    i = cols.index("FY2024")
    row = next(r for r in annual["rows"] if r["name"] == "净利润" and r["kind"] == "b")
    assert row["v"][cols.index("FY2023")] == -5833.0
    assert row["yoy"][i] == NM
    assert row["yoy_tone"][i] == "na"


def test_qoq_disabled_outside_quarterly_view(page: dict):
    """环比只在单季视图下提供数组；累计/年度为 null。"""
    for stmt in ("is", "bs", "cf", "eq"):
        for mode in ("ytd", "y"):
            table = page["tables"][stmt][mode]
            for r in table["rows"]:
                if r["kind"] == "s":
                    continue
                assert r.get("qoq") is None, f"{stmt}/{mode}/{r['name']} should disable qoq"


def test_xbrl_tags_committed():
    path = ROOT / "data" / "raw" / "MU" / "xbrl_tags.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "RevenueFromContractWithCustomerExcludingAssessedTax" in text
    assert "NetCashProvidedByUsedInOperatingActivities" in text


def test_period_helpers():
    assert prior_year_period("FQ4-26") == "FQ4-25"
    assert prior_quarter_period("FQ1-26") == "FQ4-25"
    assert period_label(2026, 4) == "FQ4-26"
