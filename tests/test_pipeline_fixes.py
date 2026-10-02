"""Regression tests for the review findings. No network."""

from datetime import date, datetime
from pathlib import Path

from scripts.build_calendar_ics import et_offset_hours, to_utc_stamp
from scripts.fetch_filings import is_red_8k
from scripts.lib.fiscal import (
    FiscalCalendar,
    latest_quarter_ended_before,
    months_remaining_in_fy,
    reported_through_from_year_ago,
    yahoo_relative_to_absolute,
)
from scripts.lib.metrics import (
    beat_but_down,
    guide_vs_consensus,
    keep_count,
    kpi_latest,
    pre_release_level,
    roe_percent,
    same_basis_eps,
)
from scripts.lib.ntm import ntm_from_annuals, ntm_from_quarters
from scripts.lib.overrides import apply_financial_overrides, derive_q4_eps
from scripts.lib.prices import dividend_yield_percent, reaction_window
from scripts.lib.snapshots import is_dated_snapshot

MU = FiscalCalendar([11, 2, 5, 8])


def test_reported_through_fixes_the_pre_release_gap():
    # Sep 15 is after FQ4-26's nominal end and before the Sep 30 8-K.
    # Last reported quarter is still FQ3-26, so 0q is FQ4-26, not FQ1-27.
    assert latest_quarter_ended_before(MU, date(2026, 6, 24)) == "FQ3-26"
    assert latest_quarter_ended_before(MU, date(2026, 9, 30)) == "FQ4-26"
    assert (
        yahoo_relative_to_absolute(MU, "0q", date(2026, 9, 15), reported_through="FQ3-26")
        == "FQ4-26"
    )
    assert (
        yahoo_relative_to_absolute(MU, "0y", date(2026, 9, 15), reported_through="FQ3-26")
        == "FY26"
    )
    assert (
        yahoo_relative_to_absolute(MU, "0q", date(2026, 10, 1), reported_through="FQ4-26")
        == "FQ1-27"
    )
    assert (
        yahoo_relative_to_absolute(MU, "0y", date(2026, 10, 1), reported_through="FQ4-26")
        == "FY27"
    )
    # Dec 10 still sits on the Sep 30 8-K until the next 2.02 lands.
    assert (
        yahoo_relative_to_absolute(MU, "0q", date(2026, 12, 10), reported_through="FQ4-26")
        == "FQ1-27"
    )
    assert (
        yahoo_relative_to_absolute(MU, "+1q", date(2026, 12, 10), reported_through="FQ4-26")
        == "FQ2-27"
    )
    fallback = yahoo_relative_to_absolute(MU, "0q", date(2026, 9, 15))
    anchored = yahoo_relative_to_absolute(
        MU, "0q", date(2026, 9, 15), reported_through="FQ3-26"
    )
    assert anchored == "FQ4-26"
    assert fallback != anchored


def test_year_ago_eps_anchors_the_unreported_quarter():
    assert reported_through_from_year_ago(3.03, {"FQ4-25": 3.03, "FQ3-26": 25.11}) == "FQ3-26"


def test_ntm_blends_fiscal_years_and_hides_a_two_quarter_sum():
    months = months_remaining_in_fy(MU, date(2026, 10, 1))
    val, method = ntm_from_annuals([("FY27", 171.9011), ("FY28", 189.61601)], months)
    expect = months / 12 * 171.9011 + (1 - months / 12) * 189.61601
    assert method.startswith("fy_time_weight")
    assert val is not None and abs(val - expect) < 1e-6
    assert val > 160  # not the old 38.02+41.55 ≈ 79.6
    assert ntm_from_quarters([38.02, 41.55]) == (None, "incomplete_ntm_hidden")
    four, how = ntm_from_quarters([1, 2, 3, 4, 9])
    assert four == 10 and how == "sum_next_4_quarters"


def test_dated_snapshot_glob_ignores_secondary_latest():
    names = ["2026-09-01.json", "_secondary_latest.json", "2026-10-01.json"]
    dated = [n for n in sorted(names) if is_dated_snapshot(Path(n))]
    assert sorted(names)[-1] == "_secondary_latest.json"
    assert dated[-1] == "2026-10-01.json"


def test_t5_uses_pre_close_not_the_reaction_close():
    closes = {
        "2026-09-30": 100,
        "2026-10-01": 110,
        "2026-10-02": 111,
        "2026-10-05": 112,
        "2026-10-06": 113,
        "2026-10-07": 120,
        "2026-10-08": 130,
    }
    window = reaction_window(closes, "2026-09-30", "after_close")
    assert window["pre"] == 100
    assert abs(window["d1"] - 0.10) < 1e-9
    assert abs(window["t5"] - 0.30) < 1e-9


def test_dividend_yield_is_already_percent():
    assert dividend_yield_percent(None, 1065, 0.06) == 0.06
    assert dividend_yield_percent(53.25, 1065, 0.05) == 0.05


def test_none_override_does_not_wipe_xbrl():
    entry = {"q": {"eps_diluted": 32.87}, "ytd": {}, "non_gaap": {"gross_profit": 1}}
    apply_financial_overrides(
        entry,
        {
            "q": {"eps_diluted": None, "revenue": 54229},
            "non_gaap": {"net_income": None, "eps_diluted": 33.42, "ytd": {"eps_diluted": 75.52}},
        },
    )
    assert entry["q"]["eps_diluted"] == 32.87
    assert entry["q"]["revenue"] == 54229
    assert entry["non_gaap"]["gross_profit"] == 1
    assert entry["non_gaap"]["eps_diluted"] == 33.42
    assert entry["non_gaap"]["ytd"]["eps_diluted"] == 75.52
    assert "net_income" not in entry["non_gaap"]


def test_annual_roe_is_not_multiplied_by_four():
    assert roe_percent(100, 200, 200, annual=True) == 50.0
    assert roe_percent(100, 200, 200, annual=False) == 200.0


def test_guide_vs_consensus_is_rev_then_eps_and_uses_pre_release():
    slot = {"eps": {"avg": 38.02}, "eps_trend": {"d30": 34.89147}, "rev": {"avg": 61.32}}
    assert pre_release_level(slot, "eps") == 34.89147
    vals, tones = guide_vs_consensus(61.5, None, 38.15, pre_release_level(slot, "eps"))
    assert vals[0] is None
    assert vals[1] == round(38.15 / 34.89147 - 1, 4)
    assert tones == ["na", "up"]


def test_eps_change_stays_on_one_basis_and_kpi_does_not_fall_through():
    assert same_basis_eps(25.11, 24.67, non_gaap_card=True) == 25.11
    assert same_basis_eps(None, 24.67, non_gaap_card=True) is None
    events = [{"eps_surp": None, "close": -0.01}, {"eps_surp": 0.02, "close": 0.1}]
    assert kpi_latest(events, "eps_surp") is None
    n, of = beat_but_down(
        [{"eps_surp": 0.1, "close": -0.01}] * 5
        + [{"eps_surp": 0.1, "close": None}]
        + [{"eps_surp": 0.1, "close": 0.02}] * 2,
    )
    assert (n, of) == (5, 7)
    assert keep_count(0) == 0


def test_q4_eps_from_ni_and_shares():
    assert derive_q4_eps(37701, 1_147_000_000) == 32.87


def test_keywords_any_blocks_bare_item_801():
    rules = [
        {
            "match": {"form": "8-K", "items": ["8.01"], "keywords_any": ["lawsuit", "诉讼"]},
            "label": "监管/诉讼",
        }
    ]
    assert is_red_8k(["8.01"], rules, text="8.01") == (False, None)
    assert is_red_8k(["8.01"], rules, text="shareholder lawsuit")[0] is True


def test_ics_dst_offset():
    assert et_offset_hours(date(2026, 1, 15)) == 5
    assert et_offset_hours(date(2026, 7, 15)) == 4
    assert to_utc_stamp("2026-01-15", 16, 5) == "20260115T210500Z"
    assert to_utc_stamp("2026-07-15", 16, 5) == "20260715T200500Z"


def test_incomplete_session_dropped_before_the_close():
    from scripts.lib.prices import drop_incomplete_session

    series = {"2026-10-01": 10, "2026-10-02": 11}
    noon = datetime(2026, 10, 2, 12, 0)
    assert "2026-10-02" not in drop_incomplete_session(series, noon)
    after = datetime(2026, 10, 2, 16, 5)
    assert drop_incomplete_session(series, after)["2026-10-02"] == 11


def test_watchlist_price_stats_skip_nan_closes():
    from scripts.build_page_watchlist import price_stats

    last, d1, ytd = price_stats({"2026-09-29": 100.0, "2026-09-30": 110.0, "2026-10-01": float("nan")})
    assert last == 110.0
    assert abs(d1 - 10.0) < 1e-9
