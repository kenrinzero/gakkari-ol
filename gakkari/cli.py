"""Command-line interface for daily renewal summaries.

One-shot: read DB → format today's renewals + 7-day preview → print → exit.
Designed to be called from Windows Task Scheduler on login. The renderer
reuses the same data sources as the TUI's notice panel so output never
drifts from what the user sees in-app.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from gakkari.db import get_conn, init_db, list_subscriptions, load_settings
from gakkari.models import Subscription
from gakkari.notices import _DAY_LABELS, _FACES_EMPTY, _post_id
from gakkari.strings import fmt_period, t


def render_notice(today: date, lang: str, subs: list[Subscription]) -> str:
    today_subs = [s for s in subs if s.next_renewal_date == today]
    week_end = today + timedelta(days=7)
    upcoming = sorted(
        (s for s in subs if today < s.next_renewal_date < week_end),
        key=lambda s: s.next_renewal_date,
    )

    lines: list[str] = []

    day_label = _DAY_LABELS[today.weekday()]
    header = (
        f"[Gakkari OL] {t('notice_thread_title', lang)} — "
        f"{today.isoformat()} ({day_label})"
    )
    lines.append(header)
    lines.append("─" * len(header))
    lines.append("")

    if today_subs:
        lines.append(f"!! TODAY ({len(today_subs)}):")
        for s in today_subs:
            lines.append(
                f"  - {s.name}  {s.currency} {s.amount:,.2f}  "
                f"({fmt_period(s.billing_period, lang)})"
            )
    else:
        # Deterministic empty-day kaomoji for flavor — same hash as the panel.
        face = _FACES_EMPTY[int(_post_id(today, "empty"), 16) % len(_FACES_EMPTY)]
        lines.append(f"TODAY: nothing scheduled  {face}")
    lines.append("")

    if upcoming:
        lines.append("Upcoming (next 7 days):")
        for s in upcoming:
            n = (s.next_renewal_date - today).days
            day = _DAY_LABELS[s.next_renewal_date.weekday()]
            lines.append(
                f"  +{n}d {s.next_renewal_date.isoformat()} ({day})  "
                f"{s.name}  {s.currency} {s.amount:,.2f}"
            )
    else:
        lines.append("No upcoming renewals this week.")

    return "\n".join(lines)


def print_notice(lang_override: str | None = None) -> int:
    """Read DB, render today's notice, print to stdout. Returns exit code."""
    init_db()  # idempotent; creates schema if first run
    with get_conn() as conn:
        settings = load_settings(conn)
        subs = list_subscriptions(conn, statuses=("active", "paused"))
    lang = lang_override or getattr(settings, "language", "en") or "en"

    output = render_notice(date.today(), lang, subs)

    # Windows console host defaults to cp1252 which would crash on JA glyphs
    # and kaomoji. reconfigure() is a no-op when the stream isn't reconfigurable
    # (e.g. piped to a non-TTY) — that's fine; the surrounding shell will handle
    # encoding in that case.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(output)
    return 0
