from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from gakkari.models import Subscription

SAMPLE_SUBSCRIPTIONS: list[Subscription] = [
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
        name="Adobe Creative Cloud",
        amount=Decimal("599.88"),
        currency="USD",
        billing_period="yearly",
        next_renewal_date=date.today() + timedelta(days=142),
        category="Tools",
        status="active",
    ),
]

COLUMNS = [
    ("Name", 24),
    ("Amount", 10),
    ("Curr", 6),
    ("Period", 11),
    ("Next Renewal", 14),
    ("Category", 16),
    ("Status", 10),
]


class MainScreen(Screen):
    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }

    #layout {
        height: 1fr;
    }

    #left-panel, #right-panel {
        width: 30%;
        border: tall $primary-darken-3;
        color: $text-disabled;
    }

    #center-panel {
        width: 40%;
        height: 1fr;
    }

    #subtitle {
        color: $text-muted;
        padding: 0 2;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
        border: tall $primary-darken-2;
    }

    DataTable > .datatable--header {
        background: $primary-darken-3;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $primary-darken-1;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            yield Static("", id="left-panel")
            with Vertical(id="center-panel"):
                yield Static("Subscription tracker  ·  がっかりOL", id="subtitle")
                yield DataTable(cursor_type="row", zebra_stripes=True)
            yield Static("", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label, width in COLUMNS:
            table.add_column(label, width=width)
        self._populate(table, SAMPLE_SUBSCRIPTIONS)

    def _populate(self, table: DataTable, subs: list[Subscription]) -> None:
        table.clear()
        today = date.today()
        for sub in subs:
            days = sub.days_until_renewal(today)
            if days == 0:
                renewal_str = "Today"
            elif days == 1:
                renewal_str = "Tomorrow"
            else:
                renewal_str = sub.next_renewal_date.strftime("%Y-%m-%d")

            amount_str = f"{sub.amount:,.2f}"
            values = (
                sub.name,
                amount_str,
                sub.currency,
                sub.billing_period,
                renewal_str,
                sub.category,
                sub.status,
            )
            if sub.is_due_soon(7, today):
                row = tuple(Text(v, style="bold yellow") for v in values)
            else:
                row = values
            table.add_row(*row, key=str(sub.id))

    def action_add(self) -> None:
        self.notify("Add flow coming in Phase 1.", title="Add")

    def action_edit(self) -> None:
        self.notify("Edit flow coming in Phase 1.", title="Edit")

    def action_delete(self) -> None:
        self.notify("Delete flow coming in Phase 1.", title="Delete")

    def action_help(self) -> None:
        self.notify(
            "a  Add · e  Edit · d  Delete · q  Quit",
            title="Keyboard shortcuts",
            timeout=6,
        )

    def action_quit(self) -> None:
        self.app.exit()
