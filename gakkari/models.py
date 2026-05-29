from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

BILLING_PERIODS = ("monthly", "yearly", "quarterly", "weekly", "half_yearly")
STATUSES = ("active", "paused", "cancelled")
TAX_MODES = ("none", "inclusive", "exclusive")
PRICE_DISPLAY_MODES = ("net", "gross")
TOTALS_VIEW_MODES = ("estimate", "monthly_strict", "yearly_strict", "by_period")
SORT_MODES = ("date", "period", "name", "amount")

_MONTHLY_FACTORS: dict[str, Decimal] = {
    "monthly": Decimal("1"),
    "yearly": Decimal("1") / 12,
    "quarterly": Decimal("1") / 3,
    "weekly": Decimal("52") / 12,
    "half_yearly": Decimal("1") / 6,
}


@dataclass
class Subscription:
    name: str
    amount: Decimal
    currency: str
    billing_period: str
    next_renewal_date: date
    category: str = ""
    notes: str = ""
    tax_mode: str = "none"
    tax_rate: Decimal = field(default_factory=lambda: Decimal("0"))
    status: str = "active"
    trial_ends: date | None = None
    id: int | None = None

    def days_until_renewal(self, today: date | None = None) -> int:
        today = today or date.today()
        return (self.next_renewal_date - today).days

    def is_due_soon(self, threshold_days: int = 7, today: date | None = None) -> bool:
        d = self.days_until_renewal(today)
        return 0 <= d <= threshold_days

    def net_amount(self) -> Decimal:
        if self.tax_mode == "inclusive" and self.tax_rate:
            return self.amount / (1 + self.tax_rate / 100)
        return self.amount

    def gross_amount(self) -> Decimal:
        if self.tax_mode == "exclusive" and self.tax_rate:
            return self.amount * (1 + self.tax_rate / 100)
        if self.tax_mode == "inclusive":
            return self.amount
        return self.amount

    def display_amount(self, mode: str) -> Decimal:
        return self.net_amount() if mode == "net" else self.gross_amount()

    def monthly_equivalent(self, mode: str) -> Decimal:
        factor = _MONTHLY_FACTORS.get(self.billing_period, Decimal("1"))
        return self.display_amount(mode) * factor

    def next_renewal_after(self, from_date: date | None = None) -> date:
        """Return what next_renewal_date should be after one more billing cycle.

        Used by the `k` keybinding to advance a sub after it's been charged.
        Clamps the day-of-month down for short months (Jan 31 → Feb 28/29).
        """
        d = from_date or self.next_renewal_date
        if self.billing_period == "weekly":
            return d + timedelta(days=7)
        if self.billing_period == "monthly":
            return _add_months(d, 1)
        if self.billing_period == "quarterly":
            return _add_months(d, 3)
        if self.billing_period == "half_yearly":
            return _add_months(d, 6)
        if self.billing_period == "yearly":
            return _add_months(d, 12)
        # Unknown period — degrade to monthly to avoid crashing.
        return _add_months(d, 1)


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass
class RenewalLog:
    """One row per acknowledged renewal — written when the user presses `k`.

    Builds a running record of actual spending over time, separate from the
    forward-looking estimates the title bar shows.
    """
    subscription_id: int
    renewed_on: date
    amount: Decimal
    currency: str
    billing_period: str
    sub_name: str = ""  # populated by list_renewals via JOIN
    id: int | None = None


@dataclass
class Settings:
    base_currency: str = "USD"
    price_display_mode: str = "gross"
    due_soon_days: int = 7
    mascot_enabled: bool = True
    notices_enabled: bool = True
    language: str = "en"
    convert_column_enabled: bool = False
    convert_currency: str = ""  # `c` column target; blank → follow base_currency
    totals_view_mode: str = "estimate"
    sort_mode: str = "date"
    id: int | None = None
