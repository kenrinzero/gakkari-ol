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
        height: int = 0,
    ) -> None:
        width = max(20, width)  # narrow-terminal floor; below this it'll just crop
        if not enabled:
            # Off-state isn't blank — flip the panel into a categorized
            # keybindings tutorial so the column stays useful for onboarding.
            self.update(self._render_tutorial(lang, width))
            return
        window = self._pick_window(height)
        posts = build_notice_posts(subs, today, lang, window=window)
        banner = self._banner(lang, width)
        rendered = [banner]
        for post in posts:
            rendered.append(self._render_post(post, width))
        rendered.append(self._end_marker(width))
        # Wrap the Group in a no_wrap-safe container by using Text on each
        # already-Text piece; rich Group preserves their wrapping settings.
        self.update(Group(*rendered))

    # ── internal ──────────────────────────────────────────────────────

    # Avg lines per post = meta(1) + body(~1) + face(1) + rule(1). Some posts
    # have a 2-line body (renewals with "+N more"), but multi-renewal days are
    # rare enough that 4 is a useful average for sizing the rolling window.
    _LINES_PER_POST = 4
    _BANNER_LINES = 4   # top rule + title + bottom rule + blank
    _END_LINES = 2      # blank + 〜 終 〜
    _WINDOW_MIN = 7
    _WINDOW_MAX = 14

    def _pick_window(self, height: int) -> int:
        """Pick how many days to render. 1 week on small terminals, up to 2
        weeks when there's vertical room. Height ≤ 0 falls back to the
        minimum so callers that don't pass a height still get sensible
        behaviour."""
        if height <= 0:
            return self._WINDOW_MIN
        room = max(0, height - self._BANNER_LINES - self._END_LINES)
        fits = room // self._LINES_PER_POST
        return max(self._WINDOW_MIN, min(self._WINDOW_MAX, fits))

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

    def _render_tutorial(self, lang: str, width: int) -> Group:
        """Build a textboard-styled keybindings cheatsheet for the off-state."""
        rule = Text("─" * width, style="dim #CC8800")
        title = Text(
            t("tutorial_title", lang),
            style="bold #FFB000",
            justify="center",
        )
        title.truncate(width, overflow="ellipsis")
        blocks: list = [rule, title, rule, Text("")]

        sections: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
            ("tutorial_section_editing", (
                ("a", "bind_add"),
                ("e", "bind_edit"),
                ("d", "bind_delete"),
                ("k", "bind_advance"),
                ("u", "bind_undo"),
                ("→", "bind_notes"),
            )),
            ("tutorial_section_views", (
                ("/", "bind_filter"),
                ("g", "bind_gross_net"),
                ("p", "bind_paused"),
                ("v", "bind_archive"),
                ("o", "bind_sort"),
                ("t", "bind_totals"),
                ("c", "bind_convert"),
            )),
            ("tutorial_section_screens", (
                ("h", "bind_history"),
                ("n", "bind_notices"),
            )),
            ("tutorial_section_app", (
                ("s", "bind_settings"),
                ("x", "bind_export"),
                ("i", "bind_import"),
                ("l", "bind_lang"),
                ("q", "bind_quit"),
            )),
        )

        for section_key, items in sections:
            blocks.append(Text(t(section_key, lang), style="bold #CC8800"))
            for key, label_key in items:
                line = Text("  ", no_wrap=True, overflow="crop")
                line.append(key.ljust(3), style="bold #FFB000")
                line.append(t(label_key, lang), style="#CC6600")
                blocks.append(line)
            blocks.append(Text(""))  # spacer between sections

        return Group(*blocks)

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
