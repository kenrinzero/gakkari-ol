from __future__ import annotations

from datetime import date
from decimal import Decimal

from gakkari import totals
from gakkari.models import Subscription

RC = {"EUR": Decimal("1"), "USD": Decimal("0.5")}


def sub(**kw) -> Subscription:
    base = dict(
        name="X", amount=Decimal("10"), currency="EUR",
        billing_period="monthly", next_renewal_date=date(2026, 6, 1),
        status="active", tax_mode="none",
    )
    base.update(kw)
    return Subscription(**base)


def test_total_monthly_in_base_folds_periods():
    subs = [
        sub(amount=Decimal("10"), billing_period="monthly"),
        sub(amount=Decimal("120"), billing_period="yearly"),  # -> 10/mo
    ]
    assert totals.total_monthly_in_base(subs, RC, "gross") == Decimal("20")


def test_total_monthly_skips_non_active():
    subs = [sub(status="paused"), sub(status="cancelled", amount=Decimal("99"))]
    assert totals.total_monthly_in_base(subs, RC, "gross") == Decimal("0")


def test_rate_applied():
    assert totals.total_monthly_in_base(
        [sub(amount=Decimal("10"), currency="USD")], RC, "gross"
    ) == Decimal("5")


def test_total_strict():
    subs = [
        sub(billing_period="monthly", amount=Decimal("10")),
        sub(billing_period="yearly", amount=Decimal("120")),
    ]
    assert totals.total_strict(subs, "monthly", RC, "gross") == Decimal("10")
    assert totals.total_strict(subs, "yearly", RC, "gross") == Decimal("120")


def test_by_period_ordered_shortest_first():
    subs = [
        sub(billing_period="yearly", amount=Decimal("1")),
        sub(billing_period="weekly", amount=Decimal("2")),
    ]
    assert [p for p, _ in totals.totals_by_period(subs, RC, "gross")] == ["weekly", "yearly"]


def test_by_category_monthly_equiv_sorted_desc():
    subs = [
        sub(category="a", amount=Decimal("10"), billing_period="monthly"),
        sub(category="b", amount=Decimal("120"), billing_period="yearly"),  # 10/mo
        sub(category="a", amount=Decimal("5"), billing_period="monthly"),
    ]
    assert totals.totals_by_category(subs, RC, "gross") == [
        ("a", Decimal("15")), ("b", Decimal("10")),
    ]


def test_cashout_forecast_cumulative_and_inclusive():
    subs = [sub(amount=Decimal("10"), billing_period="monthly", next_renewal_date=date(2026, 6, 5))]
    res = dict(totals.cashout_forecast(subs, RC, "gross", date(2026, 6, 1)))
    # 30 end=7/1 -> 6/5; 60 end=7/31 -> 6/5,7/5; 90 end=8/30 -> 6/5,7/5,8/5
    assert res == {30: Decimal("10"), 60: Decimal("20"), 90: Decimal("30")}


def test_forecast_boundary_inclusive():
    # a charge exactly on the 30-day horizon end (6/1 + 30 = 7/1) is counted
    subs = [sub(amount=Decimal("7"), billing_period="yearly", next_renewal_date=date(2026, 7, 1))]
    assert dict(totals.cashout_forecast(subs, RC, "gross", date(2026, 6, 1)))[30] == Decimal("7")


def test_forecast_ignores_past_charges():
    subs = [sub(amount=Decimal("9"), billing_period="yearly", next_renewal_date=date(2026, 5, 1))]
    # only next year's 2027-05-01 renewal exists ahead, well beyond 90 days
    assert dict(totals.cashout_forecast(subs, RC, "gross", date(2026, 6, 1)))[90] == Decimal("0")


def test_sort_amount_desc_cross_currency():
    cheap = sub(name="cheap", amount=Decimal("10"), currency="USD")  # 5 in base
    dear = sub(name="dear", amount=Decimal("8"), currency="EUR")     # 8 in base
    assert [s.name for s in totals.sort_subs([cheap, dear], "amount", RC, "gross")] == ["dear", "cheap"]


def test_sort_name_case_insensitive():
    res = totals.sort_subs([sub(name="Beta"), sub(name="alpha")], "name", RC, "gross")
    assert [s.name for s in res] == ["alpha", "Beta"]


def test_sort_date_default():
    a = sub(name="a", next_renewal_date=date(2026, 6, 10))
    b = sub(name="b", next_renewal_date=date(2026, 6, 2))
    assert [s.name for s in totals.sort_subs([a, b], "date", RC, "gross")] == ["b", "a"]
