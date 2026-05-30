from __future__ import annotations

from datetime import date
from decimal import Decimal

from gakkari.db import (
    _backup_dir,
    backup_db,
    delete_renewal,
    get_cached_rate,
    get_conn,
    get_last_rate,
    init_db,
    insert_renewal,
    insert_subscription,
    list_renewals,
    list_subscriptions,
    update_subscription,
    upsert_rate,
)
from gakkari.models import Subscription


def make(**kw) -> Subscription:
    base = dict(
        name="N", amount=Decimal("9.99"), currency="USD",
        billing_period="monthly", next_renewal_date=date(2026, 6, 1),
    )
    base.update(kw)
    return Subscription(**base)


def test_subscription_roundtrip(db):
    with get_conn() as c:
        sid = insert_subscription(c, make(payment_method="Visa", trial_ends=date(2026, 7, 1)))
    with get_conn() as c:
        s = list_subscriptions(c)[0]
    assert s.id == sid
    assert s.amount == Decimal("9.99") and isinstance(s.amount, Decimal)
    assert s.payment_method == "Visa"
    assert s.trial_ends == date(2026, 7, 1) and isinstance(s.trial_ends, date)
    assert isinstance(s.next_renewal_date, date)


def test_soft_delete_hidden_by_default(db):
    with get_conn() as c:
        insert_subscription(c, make())
        s = list_subscriptions(c)[0]
        s.status = "cancelled"
        update_subscription(c, s)
    with get_conn() as c:
        assert list_subscriptions(c) == []  # default excludes cancelled
        assert len(list_subscriptions(c, statuses=("active", "paused", "cancelled"))) == 1


def test_renewal_insert_then_delete(db):
    with get_conn() as c:
        sid = insert_subscription(c, make())
        rid = insert_renewal(
            c, subscription_id=sid, renewed_on=date(2026, 5, 1),
            amount=Decimal("9.99"), currency="USD", billing_period="monthly",
        )
    with get_conn() as c:
        assert len(list_renewals(c)) == 1
        delete_renewal(c, rid)
    with get_conn() as c:
        assert list_renewals(c) == []


def test_rate_cache_and_last_rate(db):
    with get_conn() as c:
        upsert_rate(c, "USD", "EUR", Decimal("0.9"), date(2026, 5, 30))
        assert get_cached_rate(c, "USD", "EUR", date(2026, 5, 30)) == Decimal("0.9")
        assert get_cached_rate(c, "USD", "EUR", date(2026, 5, 31)) is None  # stale by day
        rate, fetched = get_last_rate(c, "USD", "EUR")
        assert rate == Decimal("0.9") and fetched == date(2026, 5, 30)
        assert get_last_rate(c, "GBP", "EUR") is None


def test_init_db_idempotent(db):
    init_db()  # re-run over an existing DB must not raise
    init_db()
    with get_conn() as c:
        assert list_subscriptions(c) == []


def test_backup_create_skip_prune(db):
    with get_conn() as c:
        insert_subscription(c, make())
    first = backup_db(date(2026, 5, 30))
    assert first is not None and first.exists()
    assert backup_db(date(2026, 5, 30)) is None  # same day -> skip
    for d in range(20, 29):  # 9 more distinct days -> prune to newest 7
        backup_db(date(2026, 5, d))
    snaps = sorted(_backup_dir().glob("gakkari-*.db"))
    assert len(snaps) == 7
    assert snaps[-1].name == "gakkari-2026-05-30.db"
