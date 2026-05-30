from __future__ import annotations

from datetime import date
from decimal import Decimal

from gakkari.models import Subscription
from gakkari.ui.subscription_modal import _status_options


def _sub(status: str) -> Subscription:
    return Subscription(
        name="X", amount=Decimal("1"), currency="USD",
        billing_period="monthly", next_renewal_date=date(2026, 6, 1),
        status=status,
    )


def _values(sub):
    return [v for _, v in _status_options(sub, "en")]


def test_new_sub_hides_cancelled():
    vals = _values(None)
    assert "active" in vals and "paused" in vals and "cancelled" not in vals


def test_active_sub_hides_cancelled():
    assert "cancelled" not in _values(_sub("active"))


def test_editing_cancelled_includes_cancelled():
    # Regression: an archived (cancelled) sub must offer 'cancelled' as an
    # option, otherwise the Select rejects the value and the edit modal
    # crashes on mount (InvalidSelectValueError).
    assert "cancelled" in _values(_sub("cancelled"))
