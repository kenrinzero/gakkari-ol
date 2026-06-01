"""Tests for ``gakkari.notices`` — the rolling notice-board builder.

Covers the contract that ``build_notice_posts`` must drop cancelled
subscriptions from its post stream regardless of their
``next_renewal_date``, since a cancelled sub will not actually renew.
Paused and active subs still produce posts as expected.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from gakkari.models import Subscription
from gakkari.notices import build_notice_posts


TODAY = date(2026, 6, 1)


def sub(**kw) -> Subscription:
    base = dict(
        name="X", amount=Decimal("9.99"), currency="USD",
        billing_period="monthly",
        next_renewal_date=TODAY,
        tax_mode="none",
    )
    base.update(kw)
    return Subscription(**base)


# ── Core contract: cancelled is dropped at the data layer ──────────────


def test_cancelled_sub_emits_no_renewal_post():
    """Regression: a cancelled sub with a future renewal date must not
    appear on the notice board. Cancelling only flips ``status``; the
    date is leftover data and is not a real upcoming charge."""
    cancelled = sub(name="Hugging Face Pro", status="cancelled")
    posts = build_notice_posts([cancelled], TODAY, "en", window=7)
    assert not any(p.is_renewal for p in posts)
    assert not any("Hugging Face Pro" in p.body for p in posts)


def test_cancelled_within_window_still_ignored():
    """Cancelled sub renewing 5 days from today sits inside the 7-day
    window but the day-6 post must still be the empty-day fallback, not
    a renewal post."""
    soon = TODAY + timedelta(days=5)
    cancelled = sub(
        name="Recent Cancel", status="cancelled", next_renewal_date=soon
    )
    posts = build_notice_posts([cancelled], TODAY, "en", window=7)
    day6_post = posts[5]
    assert day6_post.date == soon
    assert not day6_post.is_renewal
    assert "Recent Cancel" not in day6_post.body


def test_cancelled_with_far_future_date_still_ignored():
    """Far-future cancelled renewal: not in the window, and the name
    never appears in any post body either way."""
    far = TODAY + timedelta(days=180)
    cancelled = sub(name="Old Sub", status="cancelled", next_renewal_date=far)
    posts = build_notice_posts([cancelled], TODAY, "en", window=14)
    assert not any("Old Sub" in p.body for p in posts)


# ── Paused and active still surface ────────────────────────────────────


def test_active_sub_emits_renewal_post():
    active = sub(name="ChatGPT Plus", status="active")
    posts = build_notice_posts([active], TODAY, "en", window=7)
    assert posts[0].is_renewal
    assert "ChatGPT Plus" in posts[0].body


def test_paused_sub_emits_renewal_post():
    """Paused is included: the user paused but the renewal cycle hasn't
    been changed, so the post is a useful heads-up."""
    paused = sub(name="Revolut Premium", status="paused")
    posts = build_notice_posts([paused], TODAY, "en", window=7)
    assert posts[0].is_renewal
    assert "Revolut Premium" in posts[0].body


# ── Mixed: only the cancelled one is filtered out ─────────────────────


def test_mixed_statuses_drop_only_cancelled():
    """Three subs, all renewing today, one of each status. The cancelled
    one is dropped; the active and paused ones produce a single bundled
    renewal post for day 1 (the builder picks a primary and folds the
    rest into a "+ N more" line)."""
    active = sub(name="Active Sub", status="active")
    paused = sub(name="Paused Sub", status="paused")
    cancelled = sub(name="Cancelled Sub", status="cancelled")
    posts = build_notice_posts(
        [active, paused, cancelled], TODAY, "en", window=7
    )
    renewal_posts = [p for p in posts if p.is_renewal]
    assert len(renewal_posts) == 1
    body_blob = "\n".join(p.body for p in renewal_posts)
    # Primary is one of the live subs; cancelled is not picked and not
    # bundled into the "+ N more" line either.
    assert "Cancelled Sub" not in body_blob
    assert "Active Sub" in body_blob or "Paused Sub" in body_blob
    # The "+ 1 more" line accounts for the second live sub.
    assert "+ 1 more" in body_blob


# ── Trial-expiry edge cases ────────────────────────────────────────────


def test_trial_expiry_on_cancelled_sub_is_ignored():
    """The louder "trial ends today!" post is suppressed for cancelled
    subs — the trial map is built from the same filtered set."""
    cancelled = sub(name="Trial Cancel", status="cancelled", trial_ends=TODAY)
    posts = build_notice_posts([cancelled], TODAY, "en", window=7)
    assert not any("Trial Cancel" in p.body for p in posts)


def test_trial_expiry_on_active_sub_still_fires():
    """Inverse sanity check: trial expiry on a live sub still surfaces
    (and still takes priority over a same-day renewal, per the existing
    logic — covered by the trial-body name appearing on the post)."""
    active = sub(name="Live Trial", status="active", trial_ends=TODAY)
    posts = build_notice_posts([active], TODAY, "en", window=7)
    assert posts[0].is_renewal
    assert "Live Trial" in posts[0].body
