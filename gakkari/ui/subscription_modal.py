from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from gakkari.models import BILLING_PERIODS, STATUSES, TAX_MODES, Subscription
from gakkari.strings import fmt_period, fmt_status, fmt_tax_mode, t


class SubscriptionModal(ModalScreen[Subscription | None]):

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    CSS = """
    SubscriptionModal {
        align: center middle;
    }

    #dialog {
        width: 60;
        max-height: 90%;
        border: thick #CC8800;
        background: #0D0800;
        color: #FFB000;
        padding: 1 2;
        overflow-y: auto;
    }

    #dialog-title {
        text-style: bold;
        color: #FF8C00;
        margin-bottom: 1;
    }

    .field-label {
        color: #CC6600;
        margin-top: 1;
    }

    Input {
        background: #000000;
        color: #FFB000;
        border: tall #2A1500;
    }

    Input:focus {
        border: tall #CC8800;
    }

    Input.-disabled {
        opacity: 0.4;
    }

    Select {
        background: #000000;
        color: #FFB000;
    }

    #button-row {
        height: auto;
        margin-top: 2;
        align-horizontal: right;
    }

    #button-row Button {
        margin-left: 1;
    }
    """

    def __init__(self, sub: Subscription | None = None, lang: str = "en") -> None:
        super().__init__()
        self._sub = sub
        self._lang = lang

    def compose(self) -> ComposeResult:
        lang = self._lang
        is_edit = self._sub is not None
        title = t("modal_edit_title", lang) if is_edit else t("modal_add_title", lang)

        period_options = [(fmt_period(p, lang), p) for p in BILLING_PERIODS]
        tax_options = [(fmt_tax_mode(m, lang), m) for m in TAX_MODES]
        status_options = [
            (fmt_status(s, lang), s) for s in STATUSES if s != "cancelled"
        ]

        with Vertical(id="dialog"):
            yield Label(title, id="dialog-title")

            yield Label(t("field_name", lang), classes="field-label")
            yield Input(placeholder="Netflix", id="name")

            yield Label(t("field_amount", lang), classes="field-label")
            yield Input(placeholder="9.99", id="amount")

            yield Label(t("field_currency", lang), classes="field-label")
            yield Input(placeholder="USD", id="currency")

            yield Label(t("field_period", lang), classes="field-label")
            yield Select(period_options, value="monthly", id="period")

            yield Label(t("field_renewal", lang), classes="field-label")
            yield Input(
                placeholder=date.today().isoformat(), id="next_renewal"
            )

            yield Label(t("field_category", lang), classes="field-label")
            yield Input(placeholder="Tools", id="category")

            yield Label(t("field_notes", lang), classes="field-label")
            yield Input(placeholder="", id="notes")

            yield Label(t("field_tax_mode", lang), classes="field-label")
            yield Select(tax_options, value="none", id="tax_mode")

            yield Label(t("field_tax_rate", lang), classes="field-label")
            yield Input(placeholder="0", id="tax_rate", disabled=True)

            yield Label(t("field_status", lang), classes="field-label")
            yield Select(status_options, value="active", id="status")

            with Horizontal(id="button-row"):
                yield Button(t("modal_save", lang), id="save", variant="primary")
                yield Button(t("modal_cancel", lang), id="cancel")

    def on_mount(self) -> None:
        if self._sub is None:
            return
        s = self._sub
        self.query_one("#name", Input).value = s.name
        self.query_one("#amount", Input).value = str(s.amount)
        self.query_one("#currency", Input).value = s.currency
        self.query_one("#period", Select).value = s.billing_period
        self.query_one("#next_renewal", Input).value = s.next_renewal_date.isoformat()
        self.query_one("#category", Input).value = s.category
        self.query_one("#notes", Input).value = s.notes
        self.query_one("#tax_mode", Select).value = s.tax_mode
        self.query_one("#tax_rate", Input).value = str(s.tax_rate)
        self.query_one("#status", Select).value = s.status
        self._update_tax_rate_state()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "tax_mode":
            self._update_tax_rate_state()

    def _update_tax_rate_state(self) -> None:
        tax_mode = self.query_one("#tax_mode", Select).value
        tax_input = self.query_one("#tax_rate", Input)
        tax_input.disabled = tax_mode in ("none", Select.BLANK)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _save(self) -> None:
        lang = self._lang
        errors: list[str] = []

        name = self.query_one("#name", Input).value.strip()
        if not name:
            errors.append(t("err_name_required", lang))

        amount_str = self.query_one("#amount", Input).value.strip()
        try:
            amount = Decimal(amount_str)
            if amount < 0:
                errors.append(t("err_amount_negative", lang))
        except (InvalidOperation, ValueError):
            errors.append(t("err_amount_invalid", lang))
            amount = None

        currency = self.query_one("#currency", Input).value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors.append(t("err_currency_invalid", lang))

        period = self.query_one("#period", Select).value
        if period is Select.BLANK:
            period = "monthly"

        date_str = self.query_one("#next_renewal", Input).value.strip()
        try:
            next_renewal = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            errors.append(t("err_date_invalid", lang))
            next_renewal = None

        category = self.query_one("#category", Input).value.strip()
        notes = self.query_one("#notes", Input).value

        tax_mode = self.query_one("#tax_mode", Select).value
        if tax_mode is Select.BLANK:
            tax_mode = "none"

        tax_rate_str = self.query_one("#tax_rate", Input).value.strip()
        if tax_mode == "none":
            tax_rate = Decimal("0")
        else:
            try:
                tax_rate = Decimal(tax_rate_str)
            except (InvalidOperation, ValueError):
                errors.append(t("err_tax_rate_invalid", lang))
                tax_rate = None

        status = self.query_one("#status", Select).value
        if status is Select.BLANK:
            status = "active"

        if errors:
            self.notify(
                "\n".join(errors),
                title=t("err_fix_before_save", lang),
                severity="error",
                timeout=6,
            )
            return

        sub = Subscription(
            name=name,
            amount=amount,
            currency=currency,
            billing_period=period,
            next_renewal_date=next_renewal,
            category=category,
            notes=notes,
            tax_mode=tax_mode,
            tax_rate=tax_rate,
            status=status,
            id=self._sub.id if self._sub else None,
        )
        self.dismiss(sub)
