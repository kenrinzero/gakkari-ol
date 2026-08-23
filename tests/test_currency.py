"""Tests for ``gakkari.currency`` — the fresh/stale/missing fallback ladder.

The live fetch is monkeypatched out; these test the cache and fallback
behaviour, which is the part the UI's ⚠/⌛ indicators depend on.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx

from gakkari.currency import get_rate_status
from gakkari.db import get_conn, upsert_rate

TODAY = date(2026, 6, 1)


def test_identity_pair_is_fresh_without_cache(db):
    with get_conn() as c:
        rate, status = get_rate_status(c, "EUR", "EUR", today=TODAY)
    assert rate == Decimal("1") and status == "fresh"


def test_same_day_cache_hit_is_fresh_without_network(db, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network must not be called on a same-day cache hit")

    monkeypatch.setattr(httpx, "get", no_network)
    with get_conn() as c:
        upsert_rate(c, "USD", "EUR", Decimal("0.9"), TODAY)
        rate, status = get_rate_status(c, "USD", "EUR", today=TODAY)
    assert rate == Decimal("0.9") and status == "fresh"


def test_failed_fetch_reuses_last_cached_rate_as_stale(db, monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", offline)
    with get_conn() as c:
        upsert_rate(c, "USD", "EUR", Decimal("0.9"), date(2026, 5, 30))
        rate, status = get_rate_status(c, "USD", "EUR", today=TODAY)
    assert rate == Decimal("0.9") and status == "stale"


def test_failed_fetch_without_any_cache_is_missing_1_to_1(db, monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", offline)
    with get_conn() as c:
        rate, status = get_rate_status(c, "USD", "JPY", today=TODAY)
    assert rate == Decimal("1") and status == "missing"
