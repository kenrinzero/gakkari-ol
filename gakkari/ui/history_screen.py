from __future__ import annotations

from datetime import date
from decimal import Decimal

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from gakkari import totals
from gakkari.currency import get_rate_status
from gakkari.db import get_conn, list_renewals, list_subscriptions, load_settings
from gakkari.models import RenewalLog, Settings, Subscription
from gakkari.strings import fmt_date, t


class HistoryScreen(Screen):
    """Chronological renewal log with a running total in base currency.

    Rows are written when the user presses `k` on the main screen. This view
    is read-only — to "undo" a renewal log entry the user would need to edit
    the underlying subscription manually (kept out of scope on purpose).
    """

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", priority=True),
        Binding("h", "back", show=False),
        Binding("q", "back", show=False),
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

    #history-layout {
        height: 1fr;
        background: #000000;
        border: double #CC8800;
        padding: 0;
    }

    #history-title {
        height: auto;
        min-height: 1;
        background: #CC8800;
        color: #000000;
        text-style: bold;
        text-align: center;
        padding: 0 1;
    }

    #history-list {
        background: #000000;
        color: #FFB000;
        height: 1fr;
        scrollbar-color: #CC8800;
        scrollbar-background: #1A0D00;
        scrollbar-color-hover: #FF8C00;
        scrollbar-color-active: #FF8C00;
        scrollbar-corner-color: #000000;
    }

    #history-list > .option-list--option-highlighted {
        background: #331A00;
        color: #FFB000;
    }
    """

    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self._lang = lang
        self._settings: Settings = Settings()

    def compose(self) -> ComposeResult:
        with Vertical(id="history-layout"):
            yield Static("", id="history-title")
            yield OptionList(id="history-list")
        yield Footer()

    def on_mount(self) -> None:
        entries: list[RenewalLog] = []
        subs: list[Subscription] = []
        try:
            with get_conn() as conn:
                self._settings = load_settings(conn)
                entries = list_renewals(conn)
                subs = list_subscriptions(conn, statuses=("active",))
        except Exception as e:
            self.notify(
                t("history_load_error", self._lang).format(err=e),
                severity="warning",
                timeout=6,
            )
        self._fill(entries, subs)
        self.query_one("#history-list", OptionList).focus()

    def _fill(
        self, entries: list[RenewalLog], subs: list[Subscription]
    ) -> None:
        title = self.query_one("#history-title", Static)
        listing = self.query_one("#history-list", OptionList)
        listing.clear_options()
        if not entries:
            title.update(t("history_title_empty", self._lang))
            listing.add_option(
                Option(
                    Text(t("history_empty_msg", self._lang), style="#554400"),
                    disabled=True,
                )
            )
            return

        base = self._settings.base_currency
        rates, stale, missing = self._rate_cache(entries, subs, base)
        total = Decimal("0")
        # Per-month subtotal + count, summed in base (entries arrive DESC).
        month_total: dict[tuple[int, int], Decimal] = {}
        month_count: dict[tuple[int, int], int] = {}
        for e in entries:
            in_base = e.amount * rates.get(e.currency, Decimal("1"))
            total += in_base
            key = (e.renewed_on.year, e.renewed_on.month)
            month_total[key] = month_total.get(key, Decimal("0")) + in_base
            month_count[key] = month_count.get(key, 0) + 1

        # Same freshness indicators as the main title bar — the running total
        # can rest on a stale or never-fetched rate, and the user must see it.
        warning = ""
        if missing:
            warning += f" · ⚠ {t('rate_fallback_warning', self._lang)}"
        if stale:
            warning += f" · ⌛ {t('rate_stale_warning', self._lang)}"
        title.update(
            t("history_title", self._lang).format(
                count=len(entries), base=base, total=f"{total:,.2f}",
            )
            + warning
        )
        # Current amortized monthly estimate — shown on the current month's
        # header so actual-so-far reads against what you committed to.
        estimate = totals.total_monthly_in_base(
            subs, rates, self._settings.price_display_mode
        )
        today = date.today()
        cur_key: tuple[int, int] | None = None
        for e in entries:
            key = (e.renewed_on.year, e.renewed_on.month)
            if key != cur_key:
                cur_key = key
                listing.add_option(
                    Option(
                        self._month_header(
                            key, month_total[key], month_count[key],
                            base, today, estimate,
                        ),
                        disabled=True,
                    )
                )
            listing.add_option(Option(self._render_entry(e, base, rates)))

    def _month_header(
        self,
        key: tuple[int, int],
        subtotal: Decimal,
        count: int,
        base: str,
        today: date,
        estimate: Decimal,
    ) -> Text:
        y, m = key
        text = Text()
        text.append(f"{y}-{m:02d}  ", style="bold #CC8800")
        text.append(f"{base} {subtotal:,.2f} ({count})", style="#997000")
        if (y, m) == (today.year, today.month):
            text.append(
                "  · "
                + t("history_month_est", self._lang).format(
                    base=base, est=f"{estimate:,.2f}"
                ),
                style="#554400",
            )
        return text

    def _rate_cache(
        self,
        entries: list[RenewalLog],
        subs: list[Subscription],
        base: str,
    ) -> tuple[dict[str, Decimal], set[str], set[str]]:
        """Rates to base plus the stale/missing sets, mirroring MainScreen."""
        rates: dict[str, Decimal] = {base: Decimal("1")}
        stale: set[str] = set()
        missing: set[str] = set()
        needed = {e.currency for e in entries if e.currency and e.currency != base}
        needed |= {s.currency for s in subs if s.currency and s.currency != base}
        if not needed:
            return rates, stale, missing
        with get_conn() as conn:
            for cur in needed:
                rate, status = get_rate_status(conn, cur, base)
                rates[cur] = rate
                if status == "stale":
                    stale.add(cur)
                elif status == "missing":
                    missing.add(cur)
        return rates, stale, missing

    def _render_entry(
        self,
        e: RenewalLog,
        base: str,
        rates: dict[str, Decimal],
    ) -> Text:
        text = Text()
        date_str = fmt_date(e.renewed_on, self._lang)
        name = e.sub_name or f"#{e.subscription_id}"
        amount_str = f"{e.amount:,.2f} {e.currency}"
        text.append(date_str, style="#CC6600")
        text.append("  ")
        text.append(name, style="bold #FF8C00")
        text.append("\n  ")
        text.append(amount_str, style="#FFB000")
        if e.currency != base:
            rate = rates.get(e.currency, Decimal("1"))
            converted = e.amount * rate
            text.append(f"  ≈ {converted:,.2f} {base}", style="#CC6600")
        return text

    def action_back(self) -> None:
        self.app.pop_screen()
