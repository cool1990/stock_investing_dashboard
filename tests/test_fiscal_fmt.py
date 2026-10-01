from datetime import date

from scripts.lib.fiscal import (
    FiscalCalendar,
    fiscal_quarter_for_end_date,
    period_label,
    yahoo_relative_to_absolute,
)
from scripts.lib.fmt import MINUS, NM, format_growth

MU = FiscalCalendar([11, 2, 5, 8])


def test_mu_fq_from_end_dates():
    assert fiscal_quarter_for_end_date(MU, date(2021, 12, 2)) == (2022, 1)
    assert period_label(2022, 1) == "FQ1-22"
    assert fiscal_quarter_for_end_date(MU, date(2025, 11, 27)) == (2026, 1)
    assert fiscal_quarter_for_end_date(MU, date(2026, 2, 26)) == (2026, 2)
    assert fiscal_quarter_for_end_date(MU, date(2026, 5, 28)) == (2026, 3)
    assert fiscal_quarter_for_end_date(MU, date(2026, 8, 28)) == (2026, 4)
    assert period_label(2026, 4) == "FQ4-26"
    assert period_label(2026) == "FY26"


def test_yahoo_relative_with_end_date():
    assert (
        yahoo_relative_to_absolute(MU, "0q", date(2026, 10, 1), end_date=date(2026, 11, 26))
        == "FQ1-27"
    )
    assert (
        yahoo_relative_to_absolute(MU, "+1q", date(2026, 10, 1), end_date=date(2026, 11, 26))
        == "FQ2-27"
    )
    assert (
        yahoo_relative_to_absolute(MU, "0y", date(2026, 10, 1), end_date=date(2027, 8, 31))
        == "FY27"
    )
    assert (
        yahoo_relative_to_absolute(MU, "+1y", date(2026, 10, 1), end_date=date(2027, 8, 31))
        == "FY28"
    )


def test_growth_acceptance_cases():
    # 01_common: base<=0, or current<0 and base>0 → n.m.
    assert format_growth(-0.95, 0.04) == NM
    assert format_growth(8.29, 1.30) == "+538%"
    assert format_growth(33.42, 3.03) == "+1003%"
    assert format_growth(0.62, 0.42) == "+48%"
    assert format_growth(0.5, 1.0) == f"{MINUS}50%"
    assert format_growth(1.0, -1.0) == NM  # base <= 0
    assert format_growth(-1.0, -2.0) == NM  # base <= 0
