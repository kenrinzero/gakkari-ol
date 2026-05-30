from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gakkari.models import Subscription, _add_months


def sub(**kw) -> Subscription:
    base = dict(
        name="X", amount=Decimal("10"), currency="USD",
        billing_period="monthly", next_renewal_date=date(2026, 1, 15),
        tax_mode="none",
    )
    base.update(kw)
    return Subscription(**base)


@pytest.mark.parametrize("start,months,expected", [
    (date(2026, 1, 31), 1, date(2026, 2, 28)),   # non-leap month-end clamp
    (date(2024, 1, 31), 1, date(2024, 2, 29)),   # leap-year clamp
    (date(2026, 12, 15), 1, date(2027, 1, 15)),  # year roll-over
    (date(2026, 11, 30), 3, date(2027, 2, 28)),  # multi-month + clamp + roll
    (date(2024, 2, 29), 12, date(2025, 2, 28)),  # leap-day anniversary clamp
    (date(2026, 3, 31), 1, date(2026, 4, 30)),   # 31 -> 30
])
def test_add_months(start, months, expected):
    assert _add_months(start, months) == expected


@pytest.mark.parametrize("period,start,expected", [
    ("weekly", date(2026, 1, 15), date(2026, 1, 22)),
    ("monthly", date(2026, 1, 15), date(2026, 2, 15)),
    ("quarterly", date(2026, 1, 15), date(2026, 4, 15)),
    ("half_yearly", date(2026, 1, 15), date(2026, 7, 15)),
    ("yearly", date(2026, 1, 15), date(2027, 1, 15)),
    ("bogus", date(2026, 1, 15), date(2026, 2, 15)),  # unknown -> monthly
])
def test_next_renewal_after(period, start, expected):
    assert sub(billing_period=period, next_renewal_date=start).next_renewal_after() == expected


def test_tax_inclusive():
    s = sub(amount=Decimal("110"), tax_mode="inclusive", tax_rate=Decimal("10"))
    assert s.net_amount() == Decimal("100")
    assert s.gross_amount() == Decimal("110")


def test_tax_exclusive():
    s = sub(amount=Decimal("100"), tax_mode="exclusive", tax_rate=Decimal("10"))
    assert s.net_amount() == Decimal("100")
    assert s.gross_amount() == Decimal("110")


def test_tax_none():
    s = sub(amount=Decimal("50"), tax_mode="none")
    assert s.net_amount() == s.gross_amount() == Decimal("50")


def test_tax_stays_decimal():
    s = sub(amount=Decimal("110"), tax_mode="inclusive", tax_rate=Decimal("10"))
    assert isinstance(s.net_amount(), Decimal)
    assert isinstance(s.gross_amount(), Decimal)


@pytest.mark.parametrize("period,factor", [
    ("monthly", Decimal("1")),
    ("yearly", Decimal("1") / 12),
    ("quarterly", Decimal("1") / 3),
    ("weekly", Decimal("52") / 12),
    ("half_yearly", Decimal("1") / 6),
])
def test_monthly_equivalent(period, factor):
    s = sub(amount=Decimal("12"), billing_period=period, tax_mode="none")
    assert s.monthly_equivalent("gross") == Decimal("12") * factor


def test_monthly_equivalent_unknown_degrades_to_monthly():
    s = sub(amount=Decimal("12"), billing_period="bogus", tax_mode="none")
    assert s.monthly_equivalent("gross") == Decimal("12")


def test_is_due_soon_boundaries():
    today = date(2026, 1, 1)
    assert sub(next_renewal_date=date(2026, 1, 8)).is_due_soon(7, today) is True   # exactly 7
    assert sub(next_renewal_date=date(2026, 1, 9)).is_due_soon(7, today) is False  # 8
    assert sub(next_renewal_date=date(2026, 1, 1)).is_due_soon(7, today) is True   # today
    assert sub(next_renewal_date=date(2025, 12, 31)).is_due_soon(7, today) is False  # overdue
