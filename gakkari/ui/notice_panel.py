"""Right-column weekly notice panel (Phase 3).

Renders the rolling 7-day textboard view. Owns no data of its own — the
parent screen calls ``refresh(...)`` with the current subscription list,
today's date, language, enabled flag, and the panel's inner width.
"""

from __future__ import annotations

from datetime import date

from rich.console import Group
from rich.text import Text
from textual.widgets import Static

from gakkari.models import Subscription
from gakkari.notices import build_notice_posts
from gakkari.strings import t


class NoticePanel(Static):
    """A single Static that re-renders its full 7-post stack on each refresh."""

    DEFAULT_CSS = ""  # styling done at the MainScreen level via #right-panel

    def refresh_posts(
        self,
        subs: list[Subscription],
        today: date,
        lang: str,
        enabled: bool,
        width: int,
    ) -> None:
        if not enabled:
            self.update("")
            return
        width = max(20, width)  # narrow-terminal floor; below this it'll just crop
        posts = build_notice_posts(subs, today, lang)
        banner = self._banner(lang, width)
        rendered = [banner]
        for post in posts:
            rendered.append(self._render_post(post, width))
        rendered.append(self._end_marker(width))
        # Wrap the Group in a no_wrap-safe container by using Text on each
        # already-Text piece; rich Group preserves their wrapping settings.
        self.update(Group(*rendered))

    # ── internal ──────────────────────────────────────────────────────

    def _end_marker(self, width: int) -> Group:
        # Always-JA marker (same reasoning as the day labels — flavor over
        # localization for the 2ch ornaments).
        marker = Text("〜 終 〜", style="dim #886600", justify="center")
        return Group(Text(""), marker)

    def _banner(self, lang: str, width: int) -> Group:
        rule = Text("─" * width, style="dim #CC8800")
        title = Text(t("notice_thread_title", lang), style="bold #FFB000", justify="center")
        title.truncate(width, overflow="ellipsis")
        return Group(rule, title, rule, Text(""))

    def _render_post(self, post, width: int) -> Group:
        # Urgent only when today (post 1) actually has a renewal — future
        # renewals further down the stack stay calm-amber.
        urgent = post.post_no == 1 and post.is_renewal
        accent = "#FF4444" if urgent else "#FFB000"
        face_accent = "#FF4444" if urgent else "#CC8800"

        meta = Text(no_wrap=True, overflow="crop")
        meta.append(f"{post.post_no}", style=f"bold {accent}")
        meta.append(" ：")
        meta.append("OL", style=f"bold {accent}")
        meta.append(f" ：{post.date.isoformat()}({post.day_label}) ")
        meta.append(f"ID:{post.post_id}", style="dim #886600")

        # Body may be one or two lines (multi-renewal). Each line gets its
        # own Text so Rich doesn't try to merge them.
        body_style = f"bold {accent}" if urgent else accent
        body_lines = post.body.split("\n")
        body_texts = [
            Text(line, style=body_style, no_wrap=True, overflow="crop")
            for line in body_lines
        ]

        face = Text(post.face, style=f"italic {face_accent}", no_wrap=True, overflow="crop")
        rule = Text("─" * width, style="dim #554400")

        return Group(meta, *body_texts, face, rule)
