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
    insert_renewal,
    insert_subscription,
    list_subscriptions,
    load_settings,
    save_settings,
    update_subscription,
)
from gakkari.models import Settings, Subscription
from gakkari.strings import fmt_category, fmt_date, fmt_period, fmt_status, t
from gakkari.ui.confirm_modal import ConfirmModal
from gakkari.ui.export_modal import ExportModal
from gakkari.ui.history_screen import HistoryScreen
from gakkari.ui.import_modal import ImportModal
from gakkari.ui.mascot_screen import MascotScreen
from gakkari.ui.notice_panel import NoticePanel
from gakkari.ui.settings_modal import SettingsModal
from gakkari.ui.subscription_modal import SubscriptionModal

LINE_WIDTH_FALLBACK = 30

# Shortest-first; controls "sort by period" grouping.
_PERIOD_ORDER: dict[str, int] = {
    "weekly": 0,
    "monthly": 1,
    "quarterly": 2,
    "half_yearly": 3,
    "yearly": 4,
}
_SORT_CYCLE: tuple[str, ...] = ("date", "period", "name", "amount")
_TOTALS_CYCLE: tuple[str, ...] = (
    "estimate",
    "monthly_strict",
    "yearly_strict",
    "by_period",
)


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
        Binding("k", "advance_renewal", "Kept it"),
        Binding("right", "open_notes", "Notes", key_display="→", priority=True),
        Binding("slash", "focus_filter", "Filter", key_display="/"),
        Binding("g", "toggle_gross_net", "Gross/Net"),
        Binding("p", "toggle_paused", "Paused"),
        Binding("v", "toggle_cancelled", "Archive"),
        Binding("o", "cycle_sort", "Sort"),
        Binding("t", "cycle_totals", "Totals"),
        Binding("c", "toggle_convert", "Convert"),
        Binding("s", "settings", "Settings"),
        Binding("x", "export", "Export"),
        Binding("i", "import_subs", "Import"),
        Binding("l", "toggle_language", "Lang"),
        Binding("m", "toggle_mascot", "Mascot"),
        Binding("n", "toggle_notices", "Notices"),
        Binding("h", "open_history", "History"),
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

    #center-panel {
        width: 60%;
        background: #000000;
        border: double #CC8800;
        padding: 0;
    }

    #right-panel {
        width: 40%;
        background: #000000;
        border: double #1A0D00;
        color: #FFB000;
        padding: 0 1;
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
        self._notices_enabled: bool = True
        self._filter_text: str = ""
        self._show_paused: bool = True
        self._show_cancelled: bool = False
        self._fallback_currencies: set[str] = set()
        self._rate_cache: dict[str, Decimal] = {}
        self._last_seen_date: date = date.today()

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
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
                self._notices_enabled = self._settings.notices_enabled
        except Exception as e:
            self.notify(
                t("settings_load_error", self._lang).format(err=e),
                severity="warning",
                timeout=6,
            )
        self.query_one("#filter-bar", Input).placeholder = t(
            "filter_placeholder", self._lang
        )
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
        # Entry widths track the panel width; rebuild so rows fill the new
        # geometry instead of staying at the pre-resize width.
        self.call_after_refresh(self._refresh_view)
        # Notice panel rule widths follow the panel width too.
        self.call_after_refresh(self._refresh_notice_panel)

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if self._notes_active and action in (
            "add", "edit", "delete", "open_notes", "help", "toggle_mascot",
            "toggle_notices", "focus_filter", "toggle_gross_net",
            "toggle_paused", "settings", "export", "import_subs",
            "cycle_sort", "cycle_totals", "toggle_convert", "advance_renewal",
            "toggle_cancelled", "open_history",
        ):
            return False
        if not self._notes_active and action == "save_notes":
            return False
        return True

    # ── Data loading ────────────────────────────────────────────────────

    def _load_subs(self) -> None:
        # Load every status — cancelled rows stay in memory so the archive
        # toggle (`v`) can surface them without a DB re-read.
        with get_conn() as conn:
            self._all_subs = list_subscriptions(
                conn, statuses=("active", "paused", "cancelled")
            )
        self._refresh_view()
        self._refresh_notice_panel()

    def _refresh_view(self) -> None:
        needle = self._filter_text.strip().lower()
        filtered = [
            s for s in self._all_subs
            if (self._show_paused or s.status != "paused")
            and (self._show_cancelled or s.status != "cancelled")
            and (
                not needle
                or needle in s.name.lower()
                or needle in s.category.lower()
            )
        ]
        # Fetch all rates we'll need this pass once, then hand the dict to
        # sort/render/totals — avoids N HTTP calls and keeps fallback set
        # in sync with what's actually on screen.
        self._rate_cache = self._build_rate_cache(filtered)
        self._subs = self._sort_subs(filtered)
        self._rebuild_list()
        self._update_title()

    def _build_rate_cache(self, subs: list[Subscription]) -> dict[str, Decimal]:
        base = self._settings.base_currency
        rates: dict[str, Decimal] = {base: Decimal("1")}
        needed = {s.currency for s in subs if s.currency and s.currency != base}
        fallback: set[str] = set()
        if needed:
            with get_conn() as conn:
                for cur in needed:
                    r = get_rate(conn, cur, base)
                    if r == Decimal("1") and cur != base:
                        fallback.add(cur)
                    rates[cur] = r
        self._fallback_currencies = fallback
        return rates

    def _sort_subs(self, subs: list[Subscription]) -> list[Subscription]:
        mode = self._settings.sort_mode
        if mode == "period":
            return sorted(
                subs,
                key=lambda s: (
                    _PERIOD_ORDER.get(s.billing_period, 99),
                    s.next_renewal_date,
                ),
            )
        if mode == "name":
            return sorted(subs, key=lambda s: s.name.lower())
        if mode == "amount":
            # Compare in base currency × monthly-equivalent — only meaningful
            # cross-currency ordering. Highest-cost first matches the
            # "what's burning my money" reading order.
            disp = self._settings.price_display_mode
            return sorted(
                subs,
                key=lambda s: s.monthly_equivalent(disp)
                * self._rate_cache.get(s.currency, Decimal("1")),
                reverse=True,
            )
        return sorted(subs, key=lambda s: s.next_renewal_date)

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
        disp = self._settings.price_display_mode
        base = self._settings.base_currency
        lang = self._lang
        indicators = f" · {t(f'display_{disp}', lang)}"
        if self._show_paused and any(s.status == "paused" for s in self._all_subs):
            indicators += f" · {t('paused_shown', lang)}"
        if self._show_cancelled and any(s.status == "cancelled" for s in self._all_subs):
            indicators += f" · {t('cancelled_shown', lang)}"
        if self._settings.sort_mode != "date":
            sort_label = t(f"sort_{self._settings.sort_mode}", lang)
            indicators += f" · {t('indicator_sort', lang).format(mode=sort_label)}"
        if self._settings.convert_column_enabled:
            indicators += f" · {t('indicator_conv', lang).format(base=base)}"
        if not self._subs:
            self._fallback_currencies = set()
            title.update(f"がっかりOL{indicators}")
            return
        count = len(self._subs)
        warning = ""
        if self._fallback_currencies:
            warning = f" · ⚠ {t('rate_fallback_warning', lang)}"
        totals_str = self._format_totals(self._subs, base, lang)
        title.update(
            f"がっかりOL{indicators}  "
            f"{count} {t('summary_subs', lang)} · "
            f"{totals_str}"
            f"{warning}"
        )

    def _format_totals(
        self, subs: list[Subscription], base: str, lang: str
    ) -> str:
        mode = self._settings.totals_view_mode
        if mode == "monthly_strict":
            total = self._total_strict(subs, "monthly")
            label = t("totals_mode_monthly_strict", lang)
            return f"{base} {total:,.2f} · {label}"
        if mode == "yearly_strict":
            total = self._total_strict(subs, "yearly")
            label = t("totals_mode_yearly_strict", lang)
            return f"{base} {total:,.2f} · {label}"
        if mode == "by_period":
            breakdown = self._totals_by_period(subs)
            if not breakdown:
                return f"{base} 0 · {t('totals_mode_by_period', lang)}"
            parts = [
                f"{base} {amt:,.0f} {fmt_period(p, lang)}"
                for p, amt in breakdown
            ]
            return " · ".join(parts)
        # estimate (default): existing monthly+yearly normalized pair
        monthly = self._total_monthly_in_base(subs)
        yearly = monthly * 12
        return (
            f"{base} {monthly:,.2f}/{t('summary_monthly', lang)} · "
            f"{base} {yearly:,.0f}/{t('summary_yearly', lang)}"
        )

    def _total_monthly_in_base(self, subs: list[Subscription]) -> Decimal:
        """Normalized monthly total — all periods folded to monthly equivalent."""
        active = [s for s in subs if s.status == "active"]
        if not active:
            return Decimal("0")
        mode = self._settings.price_display_mode
        total = Decimal("0")
        for sub in active:
            rate = self._rate_cache.get(sub.currency, Decimal("1"))
            total += sub.monthly_equivalent(mode) * rate
        return total

    def _total_strict(self, subs: list[Subscription], period: str) -> Decimal:
        """Sum of active subs whose actual billing_period matches `period`."""
        mode = self._settings.price_display_mode
        total = Decimal("0")
        for sub in subs:
            if sub.status != "active" or sub.billing_period != period:
                continue
            rate = self._rate_cache.get(sub.currency, Decimal("1"))
            total += sub.display_amount(mode) * rate
        return total

    def _totals_by_period(
        self, subs: list[Subscription]
    ) -> list[tuple[str, Decimal]]:
        """Per-period subtotals in `_PERIOD_ORDER` order (only non-empty periods)."""
        mode = self._settings.price_display_mode
        bucket: dict[str, Decimal] = {}
        for sub in subs:
            if sub.status != "active":
                continue
            rate = self._rate_cache.get(sub.currency, Decimal("1"))
            amt = sub.display_amount(mode) * rate
            bucket[sub.billing_period] = bucket.get(sub.billing_period, Decimal("0")) + amt
        ordered = sorted(
            bucket.items(),
            key=lambda kv: _PERIOD_ORDER.get(kv[0], 99),
        )
        return ordered

    def _render_entry(self, sub: Subscription) -> Text:
        w = self._line_width()
        today = date.today()
        mode = self._settings.price_display_mode
        base = self._settings.base_currency
        due_threshold = self._settings.due_soon_days
        text = Text()

        name = sub.name
        amount_str = f"{sub.display_amount(mode):,.2f} {sub.currency}"
        notes_dot = " ●" if sub.notes else " ◌"
        conv_str = ""
        if self._settings.convert_column_enabled:
            if sub.currency == base:
                conv_str = "  —"
            else:
                rate = self._rate_cache.get(sub.currency, Decimal("1"))
                conv = sub.display_amount(mode) * rate
                conv_str = f"  ≈ {conv:,.2f} {base}"
        right1 = amount_str + conv_str + notes_dot
        pad1 = max(1, w - _disp_width(name) - _disp_width(right1))
        text.append(name, style="bold #FF8C00")
        text.append(" " * pad1)
        text.append(amount_str, style="#FFB000")
        if conv_str:
            text.append(conv_str, style="#CC6600")
        if sub.notes:
            text.append(notes_dot, style="#CC8800")
        else:
            text.append(notes_dot, style="#2A1500")
        text.append("\n")

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

        cat_str = fmt_category(sub.category, self._lang) if sub.category else "—"
        status_str = fmt_status(sub.status, self._lang)
        pad3 = max(1, w - _disp_width(cat_str) - _disp_width(status_str))
        text.append(cat_str, style="#554400")
        text.append(" " * pad3)
        text.append(status_str, style="#554400")

        # Cancelled rows are for-reference only — flatten the rich palette
        # to a single dim color so the row reads as archived/dead.
        if sub.status == "cancelled":
            return Text(text.plain, style="#554400")
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

    def action_advance_renewal(self) -> None:
        sub = self._current_sub()
        if sub is None or sub.status == "cancelled" or sub.id is None:
            return
        old_date = sub.next_renewal_date
        sub.next_renewal_date = sub.next_renewal_after(old_date)
        # Log the renewal at the *old* date — that's when the charge happened.
        # The amount stored is whatever the user is currently being billed
        # (display_amount picks net/gross per current mode).
        renewal_amount = sub.display_amount(self._settings.price_display_mode)
        with get_conn() as conn:
            update_subscription(conn, sub)
            insert_renewal(
                conn,
                subscription_id=sub.id,
                renewed_on=old_date,
                amount=renewal_amount,
                currency=sub.currency,
                billing_period=sub.billing_period,
            )
        self._load_subs()
        self.notify(
            t("advance_notify", self._lang).format(
                name=sub.name,
                old=fmt_date(old_date, self._lang),
                new=fmt_date(sub.next_renewal_date, self._lang),
            ),
            timeout=4,
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

    def action_toggle_cancelled(self) -> None:
        self._show_cancelled = not self._show_cancelled
        self._refresh_view()

    def action_cycle_sort(self) -> None:
        cur = self._settings.sort_mode
        idx = _SORT_CYCLE.index(cur) if cur in _SORT_CYCLE else 0
        self._settings.sort_mode = _SORT_CYCLE[(idx + 1) % len(_SORT_CYCLE)]
        self._persist_settings()
        self._refresh_view()

    def action_cycle_totals(self) -> None:
        cur = self._settings.totals_view_mode
        idx = _TOTALS_CYCLE.index(cur) if cur in _TOTALS_CYCLE else 0
        self._settings.totals_view_mode = _TOTALS_CYCLE[(idx + 1) % len(_TOTALS_CYCLE)]
        self._persist_settings()
        self._update_title()

    def action_toggle_convert(self) -> None:
        self._settings.convert_column_enabled = (
            not self._settings.convert_column_enabled
        )
        self._persist_settings()
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
        except Exception as e:
            self.notify(
                t("settings_save_error", self._lang).format(err=e),
                severity="warning",
                timeout=6,
            )

    # ── Mascot screen ───────────────────────────────────────────────────

    def action_toggle_mascot(self) -> None:
        # `m` opens the dedicated mascot screen; Esc inside returns.
        self.app.push_screen(MascotScreen(lang=self._lang))

    # ── History screen ──────────────────────────────────────────────────

    def action_open_history(self) -> None:
        self.app.push_screen(HistoryScreen(lang=self._lang))

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
        # 40% column minus 2 cols of border minus 2 cols of horizontal padding.
        width = max(20, int(term.width * 0.40) - 4)
        # Inner height = full screen minus border (2) minus footer (1). Notice
        # panel uses this to decide window size — short terminals stay at 7
        # days, taller ones expand up to 14.
        height = max(0, term.height - 3)
        panel.refresh_posts(
            self._all_subs,
            date.today(),
            self._lang,
            self._notices_enabled,
            width,
            height,
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
