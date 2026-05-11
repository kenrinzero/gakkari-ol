from __future__ import annotations

import unicodedata
from datetime import date
from decimal import Decimal

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Input,
    OptionList,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option

from gakkari import io as gio
from gakkari.currency import get_rate
from gakkari.db import (
    get_conn,
    insert_subscription,
    list_subscriptions,
    load_settings,
    save_settings,
    update_subscription,
)
from gakkari.mascot import load_mascot
from gakkari.models import Settings, Subscription
from gakkari.strings import fmt_category, fmt_date, fmt_period, fmt_status, t
from gakkari.ui.confirm_modal import ConfirmModal
from gakkari.ui.export_modal import ExportModal
from gakkari.ui.import_modal import ImportModal
from gakkari.ui.notice_panel import NoticePanel
from gakkari.ui.settings_modal import SettingsModal
from gakkari.ui.subscription_modal import SubscriptionModal

LINE_WIDTH_FALLBACK = 30


def _disp_width(s: str) -> int:
    """Visible terminal-cell width — JA glyphs occupy two cells, ASCII one.

    Python's ``len`` counts characters, which under-counts CJK width and
    caused JA entries to over-pad and push right-aligned content past the
    panel border. ``East_Asian_Width`` "W"ide and "F"ullwidth glyphs are
    double-width; ambiguous ("A") defaults to 1 to match Windows Terminal
    in a non-CJK locale.
    """
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


class MainScreen(Screen):

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("right", "open_notes", "Notes", key_display="→", priority=True),
        Binding("slash", "focus_filter", "Filter", key_display="/"),
        Binding("g", "toggle_gross_net", "Gross/Net"),
        Binding("p", "toggle_paused", "Paused"),
        Binding("s", "settings", "Settings"),
        Binding("x", "export", "Export"),
        Binding("i", "import_subs", "Import"),
        Binding("l", "toggle_language", "Lang"),
        Binding("m", "toggle_mascot", "Mascot"),
        Binding("n", "toggle_notices", "Notices"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("escape", "back", "Back", key_display="Esc", priority=True),
        Binding("ctrl+s", "save_notes", "Ctrl+S Save", priority=True),
    ]

    CSS = """
    Screen {
        background: #000000;
        color: #FFB000;
    }

    Footer {
        background: #0D0800;
        color: #664400;
    }

    #layout {
        height: 1fr;
    }

    #left-panel, #right-panel {
        width: 33%;
        background: #000000;
        border: double #1A0D00;
        color: #221100;
    }

    #left-panel {
        color: #CC8800;
        content-align: center bottom;
    }

    #right-panel {
        color: #FFB000;
        padding: 0 1;
    }

    #center-panel {
        width: 34%;
        background: #000000;
        border: double #CC8800;
        padding: 0;
    }

    #title-bar {
        height: auto;
        min-height: 1;
        background: #CC8800;
        color: #000000;
        text-style: bold;
        text-align: center;
        padding: 0 1;
    }

    #filter-bar {
        height: 1;
        background: #000000;
        color: #FFB000;
        border: none;
        padding: 0 1;
    }

    #filter-bar:focus {
        background: #1A0D00;
    }

    #switcher {
        height: 1fr;
    }

    #list-view {
        background: #000000;
        color: #FFB000;
        height: 1fr;
        scrollbar-color: #CC8800;
        scrollbar-background: #1A0D00;
        scrollbar-color-hover: #FF8C00;
        scrollbar-color-active: #FF8C00;
        scrollbar-corner-color: #000000;
    }

    #list-view > .option-list--option-highlighted {
        background: #331A00;
        color: #FFB000;
    }

    #list-view > .option-list--option-hover {
        background: #1A0D00;
    }

    #notes-view {
        height: 1fr;
        background: #000000;
    }

    #notes-header {
        height: 1;
        background: #1A0D00;
        color: #CC8800;
        padding: 0 1;
    }

    #notes-editor {
        height: 1fr;
        background: #000000;
        color: #FFB000;
        border: none;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._lang: str = "en"
        self._settings: Settings = Settings()
        self._all_subs: list[Subscription] = []
        self._subs: list[Subscription] = []
        self._notes_active: bool = False
        self._notes_sub_idx: int = -1
        self._mascot_enabled: bool = True
        self._notices_enabled: bool = True
        self._filter_text: str = ""
        self._show_paused: bool = True
        self._fallback_currencies: set[str] = set()
        self._last_seen_date: date = date.today()

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            yield Static("", id="left-panel")
            with Vertical(id="center-panel"):
                yield Static("がっかりOL", id="title-bar")
                yield Input(placeholder="", id="filter-bar")
                with ContentSwitcher(initial="list-view", id="switcher"):
                    yield OptionList(id="list-view")
                    with Vertical(id="notes-view"):
                        yield Static("", id="notes-header")
                        yield TextArea(
                            "",
                            id="notes-editor",
                            show_line_numbers=False,
                        )
            yield NoticePanel("", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        try:
            with get_conn() as conn:
                self._settings = load_settings(conn)
                self._lang = self._settings.language
                self._mascot_enabled = self._settings.mascot_enabled
                self._notices_enabled = self._settings.notices_enabled
        except Exception:
            pass
        self.query_one("#filter-bar", Input).placeholder = t(
            "filter_placeholder", self._lang
        )
        self._render_mascot()
        # OptionList must own focus so single-letter bindings (a/e/d/g/p/...)
        # fire instead of being typed into the filter Input.
        self.query_one("#list-view", OptionList).focus()
        # Defer the data load until layout has settled — that way entries are
        # rendered at the real OptionList width (not the 30-col fallback) and
        # we avoid doing the work twice.
        self.call_after_refresh(self._load_subs)
        # Detect date rollover while the app is left open. 60-second cadence
        # is plenty — nothing here needs sub-minute reactivity.
        self.set_interval(60.0, self._check_date_rollover)

    def on_resize(self) -> None:
        self.call_after_refresh(self._render_mascot)
        # Entry widths track the panel width; rebuild so rows fill the new
        # geometry instead of staying at the pre-resize width.
        self.call_after_refresh(self._refresh_view)
        # Notice panel rule widths follow the panel width too.
        self.call_after_refresh(self._refresh_notice_panel)

    def _render_mascot(self) -> None:
        try:
            panel = self.query_one("#left-panel", Static)
        except Exception:
            return
        if not self._mascot_enabled:
            panel.update("")
            return
        # Derive panel size from the terminal/app size (always current),
        # not from the widget's own measurements (which lag during resize
        # and can pick the wrong art tier on the way down from fullscreen).
        term = self.app.size
        # Layout: #left-panel { width: 33%; border: double; }
        inner_w = max(0, int(term.width * 0.33) - 2)
        # Footer eats one row, border eats two more.
        inner_h = max(0, term.height - 3)
        text = load_mascot(inner_w, inner_h)
        if not text:
            panel.update("")
            return
        # Center the art horizontally inside its tier's "frame" — each line
        # gets equal left padding based on the art's own max width (not the
        # panel's), so the figure stays as a coherent block rather than each
        # row drifting independently.
        lines = text.split("\n")
        art_w = max((len(l) for l in lines), default=0)
        h_pad = max(0, (inner_w - art_w) // 2)
        prefix = " " * h_pad
        centered = [prefix + l for l in lines]
        # Bottom-align: prepend blank lines so the figure sits grounded at
        # the bottom of the panel.
        v_pad = max(0, inner_h - len(centered))
        block = "\n".join([""] * v_pad + centered)
        # no_wrap + crop: each art line stays on its own row; never wraps
        # into garbled fragments if a line exceeds inner_w.
        panel.update(Text(block, no_wrap=True, overflow="crop"))

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if self._notes_active and action in (
            "add", "edit", "delete", "open_notes", "help", "toggle_mascot",
            "toggle_notices", "focus_filter", "toggle_gross_net",
            "toggle_paused", "settings", "export", "import_subs",
        ):
            return False
        if not self._notes_active and action == "save_notes":
            return False
        return True

    # ── Data loading ────────────────────────────────────────────────────

    def _load_subs(self) -> None:
        with get_conn() as conn:
            self._all_subs = list_subscriptions(
                conn, statuses=("active", "paused")
            )
        self._refresh_view()
        self._refresh_notice_panel()

    def _refresh_view(self) -> None:
        needle = self._filter_text.strip().lower()
        self._subs = [
            s for s in self._all_subs
            if (self._show_paused or s.status != "paused")
            and (
                not needle
                or needle in s.name.lower()
                or needle in s.category.lower()
            )
        ]
        self._rebuild_list()
        self._update_title()

    def _line_width(self) -> int:
        try:
            ol = self.query_one("#list-view", OptionList)
            w = ol.size.width - 2
            return w if w > 10 else LINE_WIDTH_FALLBACK
        except Exception:
            return LINE_WIDTH_FALLBACK

    def _rebuild_list(self) -> None:
        option_list = self.query_one("#list-view", OptionList)
        option_list.clear_options()
        if not self._subs:
            option_list.add_option(
                Option(
                    Text(t("no_subs", self._lang), style="#554400"),
                    disabled=True,
                )
            )
            return
        for sub in self._subs:
            option_list.add_option(Option(self._render_entry(sub)))
        option_list.highlighted = 0

    def _update_title(self) -> None:
        title = self.query_one("#title-bar", Static)
        mode = self._settings.price_display_mode
        base = self._settings.base_currency
        indicators = f" · {t(f'display_{mode}', self._lang)}"
        if self._show_paused and any(s.status == "paused" for s in self._all_subs):
            indicators += f" · {t('paused_shown', self._lang)}"
        if not self._subs:
            self._fallback_currencies = set()
            title.update(f"がっかりOL{indicators}")
            return
        monthly = self._total_monthly_in_base(self._subs)
        yearly = monthly * 12
        count = len(self._subs)
        warning = ""
        if self._fallback_currencies:
            warning = f" · ⚠ {t('rate_fallback_warning', self._lang)}"
        title.update(
            f"がっかりOL{indicators}  "
            f"{count} {t('summary_subs', self._lang)} · "
            f"{base} {monthly:,.2f}/{t('summary_monthly', self._lang)} · "
            f"{base} {yearly:,.0f}/{t('summary_yearly', self._lang)}"
            f"{warning}"
        )

    def _total_monthly_in_base(self, subs: list[Subscription]) -> Decimal:
        active = [s for s in subs if s.status == "active"]
        # Recompute each call: previously-fallback currencies may now be
        # valid (or removed), so don't accumulate stale flags.
        fallback: set[str] = set()
        if not active:
            self._fallback_currencies = fallback
            return Decimal("0")
        base = self._settings.base_currency
        mode = self._settings.price_display_mode
        total = Decimal("0")
        with get_conn() as conn:
            for sub in active:
                rate = get_rate(conn, sub.currency, base)
                # rate==1 for a non-base currency means the lookup failed
                # and currency.py cached the safe fallback. Surface it so
                # totals aren't silently wrong (e.g. user typed YEN not JPY).
                if rate == Decimal("1") and sub.currency != base:
                    fallback.add(sub.currency)
                total += sub.monthly_equivalent(mode) * rate
        self._fallback_currencies = fallback
        return total

    def _render_entry(self, sub: Subscription) -> Text:
        w = self._line_width()
        today = date.today()
        mode = self._settings.price_display_mode
        due_threshold = self._settings.due_soon_days
        text = Text()

        # Line 1: name + amount + notes dot
        name = sub.name
        amount_str = f"{sub.display_amount(mode):,.2f} {sub.currency}"
        notes_dot = " ●" if sub.notes else " ◌"
        right1 = amount_str + notes_dot
        pad1 = max(1, w - _disp_width(name) - _disp_width(right1))
        text.append(name, style="bold #FF8C00")
        text.append(" " * pad1)
        text.append(amount_str, style="#FFB000")
        if sub.notes:
            text.append(notes_dot, style="#CC8800")
        else:
            text.append(notes_dot, style="#2A1500")
        text.append("\n")

        # Line 2: period · date + due-soon marker
        period_str = fmt_period(sub.billing_period, self._lang)
        date_str = fmt_date(sub.next_renewal_date, self._lang)
        left2 = f"{period_str} · {date_str}"
        days = sub.days_until_renewal(today)
        if sub.is_due_soon(due_threshold, today):
            if days == 0:
                right2 = f"⚠ {t('renewal_today', self._lang)}"
            elif days == 1:
                right2 = f"⚠ {t('renewal_tomorrow', self._lang)}"
            else:
                right2 = f"⚠ {days}{t('due_days', self._lang)}"
        else:
            right2 = ""
        pad2 = max(1, w - _disp_width(left2) - _disp_width(right2))
        text.append(left2, style="#CC6600")
        text.append(" " * pad2)
        if right2:
            text.append(right2, style="bold #FF4444")
        text.append("\n")

        # Line 3: category + status
        cat_str = fmt_category(sub.category, self._lang) if sub.category else "—"
        status_str = fmt_status(sub.status, self._lang)
        pad3 = max(1, w - _disp_width(cat_str) - _disp_width(status_str))
        text.append(cat_str, style="#554400")
        text.append(" " * pad3)
        text.append(status_str, style="#554400")

        return text

    def _current_sub(self) -> Subscription | None:
        option_list = self.query_one("#list-view", OptionList)
        idx = option_list.highlighted
        if idx is None or idx >= len(self._subs):
            return None
        return self._subs[idx]

    # ── CRUD actions ────────────────────────────────────────────────────

    @work
    async def action_add(self) -> None:
        result = await self.app.push_screen_wait(
            SubscriptionModal(sub=None, lang=self._lang)
        )
        if result is not None:
            with get_conn() as conn:
                new_id = insert_subscription(conn, result)
            self._load_subs()
            option_list = self.query_one("#list-view", OptionList)
            for i, sub in enumerate(self._subs):
                if sub.id == new_id:
                    option_list.highlighted = i
                    break

    @work
    async def action_edit(self) -> None:
        sub = self._current_sub()
        if sub is None:
            return
        result = await self.app.push_screen_wait(
            SubscriptionModal(sub=sub, lang=self._lang)
        )
        if result is not None:
            with get_conn() as conn:
                update_subscription(conn, result)
            prev_idx = self.query_one("#list-view", OptionList).highlighted
            self._load_subs()
            option_list = self.query_one("#list-view", OptionList)
            if self._subs:
                option_list.highlighted = min(
                    prev_idx or 0, len(self._subs) - 1
                )

    @work
    async def action_delete(self) -> None:
        sub = self._current_sub()
        if sub is None:
            return
        msg = f"{t('modal_confirm_delete', self._lang)}\n\"{sub.name}\""
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(msg, lang=self._lang)
        )
        if confirmed:
            prev_idx = self.query_one("#list-view", OptionList).highlighted
            sub.status = "cancelled"
            with get_conn() as conn:
                update_subscription(conn, sub)
            self._load_subs()
            option_list = self.query_one("#list-view", OptionList)
            if self._subs:
                option_list.highlighted = min(
                    prev_idx or 0, len(self._subs) - 1
                )

    # ── Notes flow ──────────────────────────────────────────────────────

    def action_open_notes(self) -> None:
        sub = self._current_sub()
        if sub is None:
            return
        idx = self.query_one("#list-view", OptionList).highlighted
        self._notes_active = True
        self._notes_sub_idx = idx

        header = self.query_one("#notes-header", Static)
        header.update(
            f"[bold #FF8C00]{sub.name}[/] — {t('notes_header', self._lang)}"
        )

        editor = self.query_one("#notes-editor", TextArea)
        editor.text = sub.notes or ""

        self.query_one("#switcher", ContentSwitcher).current = "notes-view"
        editor.focus()
        self.refresh_bindings()

    def action_back(self) -> None:
        if self._notes_active:
            self._save_current_notes()
            self._notes_active = False
            self._notes_sub_idx = -1
            self.query_one("#switcher", ContentSwitcher).current = "list-view"
            self.query_one("#list-view", OptionList).focus()
            self.refresh_bindings()
            return
        filter_input = self.query_one("#filter-bar", Input)
        if filter_input.has_focus or filter_input.value:
            filter_input.value = ""
            self.query_one("#list-view", OptionList).focus()

    def action_save_notes(self) -> None:
        self._save_current_notes()
        self.notify(t("modal_save", self._lang), timeout=2)

    def _save_current_notes(self) -> None:
        if self._notes_sub_idx < 0 or self._notes_sub_idx >= len(self._subs):
            return
        sub = self._subs[self._notes_sub_idx]
        editor = self.query_one("#notes-editor", TextArea)
        new_notes = editor.text
        if new_notes == sub.notes:
            return
        sub.notes = new_notes
        with get_conn() as conn:
            update_subscription(conn, sub)
        option_list = self.query_one("#list-view", OptionList)
        option_list.replace_option_prompt_at_index(
            self._notes_sub_idx, self._render_entry(sub)
        )

    # ── Language toggle ─────────────────────────────────────────────────

    def action_toggle_language(self) -> None:
        self._lang = "ja" if self._lang == "en" else "en"
        self.query_one("#filter-bar", Input).placeholder = t(
            "filter_placeholder", self._lang
        )
        self._rebuild_list()
        self._update_title()
        self._refresh_notice_panel()
        if self._notes_active and 0 <= self._notes_sub_idx < len(self._subs):
            sub = self._subs[self._notes_sub_idx]
            header = self.query_one("#notes-header", Static)
            header.update(
                f"[bold #FF8C00]{sub.name}[/] — {t('notes_header', self._lang)}"
            )
        self._save_language_setting()
        self.refresh_bindings()

    def _save_language_setting(self) -> None:
        self._settings.language = self._lang
        self._persist_settings()

    # ── Phase 2: filter, gross/net, paused, settings, export/import ─────

    def action_focus_filter(self) -> None:
        self.query_one("#filter-bar", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter-bar":
            return
        self._filter_text = event.value
        self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-bar":
            self.query_one("#list-view", OptionList).focus()

    def action_toggle_gross_net(self) -> None:
        new_mode = (
            "net" if self._settings.price_display_mode == "gross" else "gross"
        )
        self._settings.price_display_mode = new_mode
        self._persist_settings()
        self._refresh_view()

    def action_toggle_paused(self) -> None:
        self._show_paused = not self._show_paused
        self._refresh_view()

    @work
    async def action_settings(self) -> None:
        result = await self.app.push_screen_wait(
            SettingsModal(self._settings, lang=self._lang)
        )
        if result is None:
            return
        self._settings = result
        self._persist_settings()
        self._refresh_view()

    @work
    async def action_export(self) -> None:
        result = await self.app.push_screen_wait(ExportModal(lang=self._lang))
        if result is None:
            return
        fmt, path = result
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            subs = list(self._all_subs)
            if fmt == "json":
                gio.export_json(path, subs)
            else:
                gio.export_csv(path, subs)
        except Exception as e:
            self.notify(str(e), severity="error", timeout=6)
            return
        self.notify(
            t("export_success", self._lang).format(count=len(subs), path=path),
            timeout=4,
        )

    @work
    async def action_import_subs(self) -> None:
        path = await self.app.push_screen_wait(ImportModal(lang=self._lang))
        if path is None:
            return
        try:
            subs, errs = gio.import_auto(path)
        except Exception as e:
            self.notify(str(e), severity="error", timeout=6)
            return
        if subs:
            with get_conn() as conn:
                for sub in subs:
                    insert_subscription(conn, sub)
        if errs:
            msg = t("import_partial", self._lang).format(
                count=len(subs), errors=len(errs)
            )
            self.notify(msg, severity="warning", timeout=6)
        else:
            msg = t("import_success", self._lang).format(count=len(subs))
            self.notify(msg, timeout=4)
        self._load_subs()

    def _persist_settings(self) -> None:
        try:
            with get_conn() as conn:
                save_settings(conn, self._settings)
        except Exception:
            pass

    # ── Mascot toggle ───────────────────────────────────────────────────

    def action_toggle_mascot(self) -> None:
        self._mascot_enabled = not self._mascot_enabled
        self._settings.mascot_enabled = self._mascot_enabled
        self._render_mascot()
        self._persist_settings()

    # ── Notice panel ────────────────────────────────────────────────────

    def action_toggle_notices(self) -> None:
        self._notices_enabled = not self._notices_enabled
        self._settings.notices_enabled = self._notices_enabled
        self._refresh_notice_panel()
        self._persist_settings()

    def _check_date_rollover(self) -> None:
        today = date.today()
        if today == self._last_seen_date:
            return
        self._last_seen_date = today
        # Both the center list (due-soon markers) and the notice panel
        # ("today" framing) depend on today's date.
        self._refresh_view()
        self._refresh_notice_panel()

    def _refresh_notice_panel(self) -> None:
        try:
            panel = self.query_one("#right-panel", NoticePanel)
        except Exception:
            return
        # Derive inner width from the terminal size (matches mascot reasoning:
        # widget.content_size lags during resize transitions).
        term = self.app.size
        # 33% column minus 2 cols of border minus 2 cols of horizontal padding.
        width = max(20, int(term.width * 0.33) - 4)
        panel.refresh_posts(
            self._all_subs,
            date.today(),
            self._lang,
            self._notices_enabled,
            width,
        )

    # ── Misc ────────────────────────────────────────────────────────────

    def action_help(self) -> None:
        self.notify(
            t("help_text", self._lang),
            title=t("title_shortcuts", self._lang),
            timeout=6,
        )

    def action_quit(self) -> None:
        self.app.exit()
