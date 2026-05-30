"""Pure totals & sort math, lifted out of MainScreen so it can be unit-tested
without a running Textual app.

Every function takes its inputs explicitly — the subscription list, a
``rate_cache`` mapping currency → rate-to-base (``Decimal``), and the active
display mode (``"net"`` / ``"gross"``). None of them touch the DB, the network,
or screen state. Amounts are always returned in base currency as ``Decimal``.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from gakkari.models import Subscription

# Shortest-first; controls "sort by period" grouping and per-period ordering.
PERIOD_ORDER: dict[str, int] = {
    "weekly": 0,
    "monthly": 1,
    "quarterly": 2,
    "half_yearly": 3,
    "yearly": 4,
}

_FORECAST_STEP_CAP = 1000  # guard against pathological loops on overdue subs


def _rate(rate_cache: dict[str, Decimal], currency: str) -> Decimal:
    return rate_cache.get(currency, Decimal("1"))


def total_monthly_in_base(
    subs: list[Subscription], rate_cache: dict[str, Decimal], display_mode: str
) -> Decimal:
    """Normalized monthly total in base — every period folded to its monthly
    equivalent. Only active subs count."""
    total = Decimal("0")
    for s in subs:
        if s.status != "active":
            continue
        total += s.monthly_equivalent(display_mode) * _rate(rate_cache, s.currency)
    return total


def total_strict(
    subs: list[Subscription],
    period: str,
    rate_cache: dict[str, Decimal],
    display_mode: str,
) -> Decimal:
    """Sum of active subs whose actual billing_period matches `period`."""
    total = Decimal("0")
    for s in subs:
        if s.status != "active" or s.billing_period != period:
            continue
        total += s.display_amount(display_mode) * _rate(rate_cache, s.currency)
    return total


def totals_by_period(
    subs: list[Subscription], rate_cache: dict[str, Decimal], display_mode: str
) -> list[tuple[str, Decimal]]:
    """Per-period subtotals (raw per-cadence amount) in PERIOD_ORDER."""
    bucket: dict[str, Decimal] = {}
    for s in subs:
        if s.status != "active":
            continue
        amt = s.display_amount(display_mode) * _rate(rate_cache, s.currency)
        bucket[s.billing_period] = bucket.get(s.billing_period, Decimal("0")) + amt
    return sorted(bucket.items(), key=lambda kv: PERIOD_ORDER.get(kv[0], 99))


def totals_by_category(
    subs: list[Subscription], rate_cache: dict[str, Decimal], display_mode: str
) -> list[tuple[str, Decimal]]:
    """Per-category MONTHLY-EQUIVALENT subtotals in base, largest first.

    Uses monthly-equivalent (not raw amount) so a yearly sub doesn't visually
    dwarf monthly ones. Uncategorized subs bucket under "" (the caller renders
    that as a dash).
    """
    bucket: dict[str, Decimal] = {}
    for s in subs:
        if s.status != "active":
            continue
        amt = s.monthly_equivalent(display_mode) * _rate(rate_cache, s.currency)
        bucket[s.category] = bucket.get(s.category, Decimal("0")) + amt
    return sorted(bucket.items(), key=lambda kv: kv[1], reverse=True)


def cashout_forecast(
    subs: list[Subscription],
    rate_cache: dict[str, Decimal],
    display_mode: str,
    today: date,
    horizons: tuple[int, ...] = (30, 60, 90),
) -> list[tuple[int, Decimal]]:
    """Concrete (non-amortized) cash-out within each horizon, in base currency.

    Unlike `estimate` (which amortizes a yearly sub to 1/12 per month), this
    walks each active sub's real billing cycles forward from its
    next_renewal_date and counts every charge that lands within each horizon.
    Buckets are cumulative — a charge 20 days out counts toward 30, 60 and 90 —
    so the totals are non-decreasing and read as "money out by day N".
    """
    sums = {h: Decimal("0") for h in horizons}
    ends = {h: today + timedelta(days=h) for h in horizons}
    longest = today + timedelta(days=max(horizons))
    for s in subs:
        if s.status != "active":
            continue
        amt = s.display_amount(display_mode) * _rate(rate_cache, s.currency)
        d = s.next_renewal_date
        steps = 0
        while d <= longest and steps < _FORECAST_STEP_CAP:
            if d >= today:
                for h in horizons:
                    if d <= ends[h]:
                        sums[h] += amt
            d = s.next_renewal_after(d)
            steps += 1
    return [(h, sums[h]) for h in horizons]


def sort_subs(
    subs: list[Subscription],
    mode: str,
    rate_cache: dict[str, Decimal],
    display_mode: str,
) -> list[Subscription]:
    """Return subs ordered by `mode` (date | period | name | amount).

    "amount" compares monthly-equivalent × rate-to-base so cross-currency
    ordering is meaningful, highest cost first.
    """
    if mode == "period":
        return sorted(
            subs,
            key=lambda s: (PERIOD_ORDER.get(s.billing_period, 99), s.next_renewal_date),
        )
    if mode == "name":
        return sorted(subs, key=lambda s: s.name.lower())
    if mode == "amount":
        return sorted(
            subs,
            key=lambda s: s.monthly_equivalent(display_mode) * _rate(rate_cache, s.currency),
            reverse=True,
        )
    return sorted(subs, key=lambda s: s.next_renewal_date)
