"""Tests for ``gakkari.cli`` — the one-shot --notice renderer."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from gakkari.cli import render_notice
from gakkari.models import Subscription
from gakkari.strings import disp_width

TODAY = date(2026, 6, 1)  # a Monday


def sub(**kw) -> Subscription:
    base = dict(
        name="X", amount=Decimal("9.99"), currency="USD",
        billing_period="monthly", next_renewal_date=TODAY,
        tax_mode="none",
    )
    base.update(kw)
    return Subscription(**base)


# ── Rule width: cells, not characters (AUDIT-2026-08-23.md, entry 23) ──


def test_rule_matches_header_width_en():
    out = render_notice(TODAY, "en", [sub()])
    header, rule = out.split("\n")[:2]
    assert set(rule) == {"─"}
    assert disp_width(rule) == disp_width(header)


def test_rule_matches_header_width_ja():
    # JA title + JA sub name — the regression case: full-width glyphs made
    # the char-count rule ~10 cells too short.
    out = render_notice(TODAY, "ja", [sub(name="スボティファイ")])
    header, rule = out.split("\n")[:2]
    assert "【週間】更新予定スレ" in header
    assert set(rule) == {"─"}
    assert disp_width(rule) == disp_width(header)
    assert len(rule) > len(header)  # more chars than the header needs


# ── Content ─────────────────────────────────────────────────────────────


def test_today_and_upcoming_render():
    subs = [
        sub(name="Today Sub"),
        sub(name="Later Sub", next_renewal_date=date(2026, 6, 3)),
    ]
    out = render_notice(TODAY, "en", subs)
    assert "!! TODAY (1):" in out
    assert "Today Sub" in out
    assert "+2d 2026-06-03 (水)" in out
    assert "Later Sub" in out


def test_empty_day_localized():
    out_en = render_notice(TODAY, "en", [])
    assert "TODAY: nothing scheduled" in out_en
    assert "No upcoming renewals this week." in out_en

    out_ja = render_notice(TODAY, "ja", [])
    assert "本日：予定なし" in out_ja
    assert "今週の更新予定はありません。" in out_ja
    assert "!! TODAY" not in out_ja  # no hardcoded EN headers in JA mode


def test_cancelled_and_paused_respect_caller_filter():
    # The CLI passes statuses=("active", "paused") from the DB layer; the
    # renderer itself just renders what it is given.
    out = render_notice(TODAY, "en", [sub(status="paused")])
    assert "X" in out  # paused still surfaces, same as the notice panel
