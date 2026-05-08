from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from gakkari.db import get_conn, load_settings, save_settings
from gakkari.models import Subscription
from gakkari.strings import fmt_category, fmt_date, fmt_period, fmt_status, t

_SAMPLE_SUBS: list[Subscription] = [
    Subscription(
        id=1,
        name="Netflix",
        amount=Decimal("15.99"),
        currency="USD",
        billing_period="monthly",
        next_renewal_date=date.today() + timedelta(days=3),
        category="Entertainment",
        status="active",
    ),
    Subscription(
        id=2,
        name="GitHub Copilot",
        amount=Decimal("10.00"),
        currency="USD",
        billing_period="monthly",
        next_renewal_date=date.today() + timedelta(days=18),
        category="Tools",
        status="active",
    ),
    Subscription(
        id=3,
        name="Adobe CC",
        amount=Decimal("599.88"),
        currency="USD",
        billing_period="yearly",
        next_renewal_date=date.today() + timedelta(days=142),
        category="Tools",
        status="active",
    ),
]

FIELD_KEYS = [
    "field_amount",
    "field_currency",
    "field_period",
    "field_renewal",
    "field_category",
    "field_status",
]

SUB_COL_WIDTH = 14

# Sub columns at even indices (0, 2, 4, ...), sep columns at odd indices (1, 3, ...)
_SEP_CHAR = "│"
_SEP_STYLE = "#3A1E00"

_MONTHLY_FACTORS: dict[str, Decimal] = {
    "monthly":   Decimal("1"),
    "yearly":    Decimal("1") / 12,
    "quarterly": Decimal("1") / 3,
    "weekly":    Decimal("52") / 12,
}


def _is_sub_col(col: int) -> bool:
    return col % 2 == 0


def _sub_idx(col: int) -> int:
    return col // 2


class MainScreen(Screen):
    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("l", "toggle_language", "Lang"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
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

    #center-panel {
        width: 34%;
        background: #000000;
        border: double #CC8800;
        padding: 0;
    }

    #title-bar {
        height: 1;
        background: #CC8800;
        color: #000000;
        text-style: bold;
        text-align: center;
    }

    DataTable {
        background: #000000;
        color: #FFB000;
        height: 9;
        border-bottom: solid #2A1500;
        scrollbar-size-horizontal: 1;
        scrollbar-color: #CC8800;
        scrollbar-background: #1A0D00;
        scrollbar-color-hover: #FF8C00;
        scrollbar-color-active: #FF8C00;
        scrollbar-corner-color: #000000;
    }

    DataTable > .datatable--header {
        background: #1A0D00;
        color: #CC8800;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #CC6600;
        color: #000000;
    }

    DataTable > .datatable--highlight {
        background: #331A00;
        color: #FFB000;
    }

    #detail-pane {
        height: 10;
        background: #000000;
        color: #FFB000;
        padding: 1 2;
        border-bottom: solid #2A1500;
    }

    #bottom-section {
        height: 1fr;
        background: #000000;
    }

    #summary-pane {
        width: 1fr;
        background: #000000;
        color: #CC6600;
        padding: 1 1;
        border-right: solid #2A1500;
    }

    #notes-pane {
        width: 1fr;
        background: #000000;
        color: #FFB000;
        padding: 1 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._lang: str = "en"
        self._subs: list[Subscription] = _SAMPLE_SUBS
        self._prev_col: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            yield Static("", id="left-panel")
            with Vertical(id="center-panel"):
                yield Static("がっかりOL", id="title-bar")
                yield DataTable(
                    cursor_type="column",
                    show_cursor=True,
                    zebra_stripes=False,
                )
                yield Static("", id="detail-pane")
                with Horizontal(id="bottom-section"):
                    yield Static("", id="summary-pane")
                    yield Static("", id="notes-pane")
            yield Static("", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        try:
            with get_conn() as conn:
                settings = load_settings(conn)
                self._lang = settings.language
        except Exception:
            pass
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)

        for i, sub in enumerate(self._subs):
            table.add_column(sub.name[:SUB_COL_WIDTH], width=SUB_COL_WIDTH)
            if i < len(self._subs) - 1:
                table.add_column(Text(_SEP_CHAR, style=_SEP_STYLE), width=1)

        sep_cell = Text(_SEP_CHAR, style=_SEP_STYLE)
        today = date.today()
        for field_key in FIELD_KEYS:
            cells: list = []
            for i, sub in enumerate(self._subs):
                cell_str = self._cell_value(sub, field_key, today)
                if sub.is_due_soon(7, today):
                    cells.append(Text(cell_str, style="bold #FF4444"))
                else:
                    cells.append(cell_str)
                if i < len(self._subs) - 1:
                    cells.append(sep_cell)
            table.add_row(*cells)

        if self._subs:
            table.move_cursor(column=0)
        self._update_detail()
        self._update_summary()

    def _cell_value(self, sub: Subscription, field_key: str, today: date) -> str:
        if field_key == "field_amount":
            return f"{sub.amount:,.2f}"
        if field_key == "field_currency":
            return sub.currency
        if field_key == "field_period":
            return fmt_period(sub.billing_period, self._lang)
        if field_key == "field_renewal":
            days = sub.days_until_renewal(today)
            if days == 0:
                return t("renewal_today", self._lang)
            if days == 1:
                return t("renewal_tomorrow", self._lang)
            return fmt_date(sub.next_renewal_date, self._lang)
        if field_key == "field_category":
            return fmt_category(sub.category, self._lang)
        if field_key == "field_status":
            return fmt_status(sub.status, self._lang)
        return ""

    def _update_detail(self) -> None:
        detail = self.query_one("#detail-pane", Static)
        notes = self.query_one("#notes-pane", Static)
        table = self.query_one(DataTable)
        col = table.cursor_column
        if not _is_sub_col(col) or _sub_idx(col) >= len(self._subs):
            detail.update("")
            notes.update("")
            return
        sub = self._subs[_sub_idx(col)]
        today = date.today()
        days = sub.days_until_renewal(today)
        if days == 0:
            renewal_str = t("renewal_today", self._lang)
        elif days == 1:
            renewal_str = t("renewal_tomorrow", self._lang)
        else:
            renewal_str = fmt_date(sub.next_renewal_date, self._lang)
        due_marker = f"  [bold #FF4444]{t('due_soon', self._lang)}[/]" if sub.is_due_soon(7, today) else ""
        detail.update("\n".join([
            f"[bold #FF8C00]{sub.name}[/]{due_marker}",
            f"[#2A1500]{'─' * 30}[/]",
            f"[#554400]{t('field_amount', self._lang):<14}[/] {sub.amount:,.2f} {sub.currency}",
            f"[#554400]{t('field_period', self._lang):<14}[/] {fmt_period(sub.billing_period, self._lang)}",
            f"[#554400]{t('field_renewal', self._lang):<14}[/] {renewal_str}",
            f"[#554400]{t('field_category', self._lang):<14}[/] {fmt_category(sub.category, self._lang)}",
            f"[#554400]{t('field_status', self._lang):<14}[/] {fmt_status(sub.status, self._lang)}",
        ]))
        if sub.notes:
            notes.update(sub.notes)
        else:
            notes.update(f"[#2A1500]{t('no_notes', self._lang)}[/]")

    def _update_summary(self) -> None:
        pane = self.query_one("#summary-pane", Static)
        today = date.today()
        active = [s for s in self._subs if s.status == "active"]
        upcoming = sorted(active, key=lambda s: s.days_until_renewal(today))
        monthly = sum(
            s.amount * _MONTHLY_FACTORS.get(s.billing_period, Decimal("1"))
            for s in active
        )
        yearly = monthly * 12
        lines: list[str] = [f"> {len(self._subs)} {t('summary_subs', self._lang)}"]
        lines.append(f"> {t('summary_monthly', self._lang)}")
        lines.append(f"  ${monthly:,.2f}")
        lines.append(f"> {t('summary_yearly', self._lang)}")
        lines.append(f"  ${yearly:,.2f}")
        pane.update("\n".join(lines))

    def on_data_table_column_highlighted(
        self, event: DataTable.ColumnHighlighted
    ) -> None:
        col = event.cursor_column
        table = self.query_one(DataTable)
        if not _is_sub_col(col):
            target = col + 1 if col > self._prev_col else col - 1
            table.move_cursor(column=target)
            return
        self._prev_col = col
        self._update_detail()

    def action_add(self) -> None:
        self.notify("Add flow coming in Phase 1.", title=t("bind_add", self._lang))

    def action_edit(self) -> None:
        self.notify("Edit flow coming in Phase 1.", title=t("bind_edit", self._lang))

    def action_delete(self) -> None:
        self.notify(
            "Delete flow coming in Phase 1.", title=t("bind_delete", self._lang)
        )

    def action_toggle_language(self) -> None:
        self._lang = "ja" if self._lang == "en" else "en"
        self._rebuild_table()
        self._save_language_setting()

    def _save_language_setting(self) -> None:
        try:
            with get_conn() as conn:
                settings = load_settings(conn)
                settings.language = self._lang
                save_settings(conn, settings)
        except Exception:
            pass

    def action_help(self) -> None:
        self.notify(
            t("help_text", self._lang),
            title=t("title_shortcuts", self._lang),
            timeout=6,
        )

    def action_quit(self) -> None:
        self.app.exit()
