from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

BILLING_PERIODS = ("monthly", "yearly", "quarterly", "weekly", "half_yearly")
STATUSES = ("active", "paused", "cancelled")
TAX_MODES = ("none", "inclusive", "exclusive")
PRICE_DISPLAY_MODES = ("net", "gross")

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


@dataclass
class Settings:
    base_currency: str = "USD"
    price_display_mode: str = "gross"
    due_soon_days: int = 7
    mascot_enabled: bool = True
    notices_enabled: bool = True
    language: str = "en"
    id: int | None = None
