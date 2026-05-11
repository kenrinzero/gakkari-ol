"""Weekly notice board (Phase 3) — pure logic.

Builds a rolling 7-day window of textboard-style posts from the active
subscription list. The renderer in ``ui/notice_panel.py`` consumes the
returned ``NoticePost`` list without re-reading the strings table.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

from gakkari.models import Subscription
from gakkari.strings import t

# Always-JA single-char weekday labels — preserve 2ch flavor regardless of UI lang.
_DAY_LABELS = ("月", "火", "水", "木", "金", "土", "日")

# Period-accurate kaomoji pools (textboard research §7). Picked per post
# by hashing the post_id, so the same day always reads the same face — no
# jitter on refresh.
_FACES_RENEWAL = (
    "Σ(ﾟДﾟ)",
    "ｷﾀ━━━(ﾟ∀ﾟ)━━━!!",
    "(*´Д｀)",
    "Σ(ﾟДﾟ;)",
    "(゜∀゜)",
)

_FACES_EMPTY = (
    "(´_ゝ｀)",
    "(´・ω・｀)",
    "( ´_ゝ｀)ﾌｰﾝ",
    "orz",
    "( ´∀｀)",
)

# Representative single faces — kept for any caller that wants a default.
FACE_SHOCK = _FACES_RENEWAL[0]
FACE_CALM = _FACES_EMPTY[0]

_EMPTY_KEYS = ("notice_empty_1", "notice_empty_2", "notice_empty_3")

# Max visible columns the body line should occupy before name truncation
# kicks in. The renderer also crops, but truncating in the builder keeps
# the data consistent across renders and avoids mid-glyph cuts.
_BODY_MAX = 38


@dataclass(frozen=True)
class NoticePost:
    post_no: int
    date: date
    day_label: str
    post_id: str
    body: str
    face: str
    is_renewal: bool


def _post_id(d: date, body: str) -> str:
    raw = f"{d.isoformat()}|{body}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:8]


def _truncate_name(name: str, room: int) -> str:
    if room <= 1 or len(name) <= room:
        return name
    return name[: max(1, room - 1)] + "…"


def _renewal_body(name: str, lang: str) -> str:
    # Each post is read from the perspective of its own date — "today" always
    # means the post's date, never the calendar today. Avoids the off-by-one
    # confusion where the May 12 post talked about "tomorrow" from May 11.
    template = t("notice_renews_today", lang)
    # Leave ~14 cols for the "renews today!" / "今日更新！" suffix.
    return template.format(name=_truncate_name(name, _BODY_MAX - 14))


def _empty_body(d: date, lang: str) -> str:
    # Deterministic pick by date so the same day always reads the same.
    seed = _post_id(d, "empty")
    pool = [t(k, lang) for k in _EMPTY_KEYS]
    return pool[int(seed, 16) % len(pool)]


def build_notice_posts(
    subs: list[Subscription],
    today: date,
    lang: str,
    *,
    window: int = 7,
) -> list[NoticePost]:
    """Build exactly ``window`` posts for today..today+window-1.

    Cancelled subs are assumed already filtered. Paused subs are included
    (their next_renewal_date is still meaningful — the user paused but the
    renewal cycle hasn't been changed).
    """
    by_date: dict[date, list[Subscription]] = {}
    for sub in subs:
        by_date.setdefault(sub.next_renewal_date, []).append(sub)

    posts: list[NoticePost] = []
    for i in range(window):
        d = today + timedelta(days=i)
        renewing = by_date.get(d, [])
        if not renewing:
            body = _empty_body(d, lang)
            face_pool = _FACES_EMPTY
            is_renewal = False
        else:
            primary = renewing[0]
            body_line = _renewal_body(primary.name, lang)
            if len(renewing) > 1:
                more = t("notice_plus_n_more", lang).format(n=len(renewing) - 1)
                body = f"{body_line}\n{more}"
            else:
                body = body_line
            face_pool = _FACES_RENEWAL
            is_renewal = True
        pid = _post_id(d, body)
        face = face_pool[int(pid, 16) % len(face_pool)]
        posts.append(
            NoticePost(
                post_no=i + 1,
                date=d,
                day_label=_DAY_LABELS[d.weekday()],
                post_id=pid,
                body=body,
                face=face,
                is_renewal=is_renewal,
            )
        )
    return posts
