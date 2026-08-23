from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from gakkari.models import PRICE_DISPLAY_MODES, Settings
from gakkari.strings import t


class SettingsModal(ModalScreen[Settings | None]):

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    CSS = """
    SettingsModal {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: auto;
        border: thick #CC8800;
        background: #0D0800;
        color: #FFB000;
        padding: 1 2;
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

    Input, Select {
        background: #000000;
        color: #FFB000;
        border: tall #2A1500;
    }

    Input:focus {
        border: tall #CC8800;
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

    def __init__(self, settings: Settings, lang: str = "en") -> None:
        super().__init__()
        self._settings = settings
        self._lang = lang

    def compose(self) -> ComposeResult:
        lang = self._lang
        mode_options = [
            (t(f"display_{m}", lang), m) for m in PRICE_DISPLAY_MODES
        ]
        with Vertical(id="dialog"):
            yield Label(t("settings_title", lang), id="dialog-title")

            yield Label(t("settings_base_currency", lang), classes="field-label")
            yield Input(value=self._settings.base_currency, id="base_currency")

            yield Label(t("settings_convert_currency", lang), classes="field-label")
            yield Input(
                value=self._settings.convert_currency, id="convert_currency"
            )

            yield Label(t("settings_display_mode", lang), classes="field-label")
            yield Select(
                mode_options,
                value=self._settings.price_display_mode,
                id="display_mode",
                allow_blank=False,
            )

            yield Label(t("settings_due_soon_days", lang), classes="field-label")
            yield Input(value=str(self._settings.due_soon_days), id="due_soon_days")

            yield Label(t("settings_monthly_income", lang), classes="field-label")
            yield Input(
                value=("" if self._settings.monthly_income == 0
                       else str(self._settings.monthly_income)),
                id="monthly_income",
            )

            yield Label(t("settings_income_currency", lang), classes="field-label")
            yield Input(
                value=self._settings.monthly_income_currency, id="income_currency"
            )

            with Horizontal(id="button-row"):
                yield Button(t("modal_save", lang), id="save", variant="primary")
                yield Button(t("modal_cancel", lang), id="cancel")

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

        currency = self.query_one("#base_currency", Input).value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors.append(t("err_currency_invalid", lang))

        # Blank convert currency means "follow base"; otherwise it must be a
        # 3-letter code just like the base currency.
        convert_currency = (
            self.query_one("#convert_currency", Input).value.strip().upper()
        )
        if convert_currency and (
            len(convert_currency) != 3 or not convert_currency.isalpha()
        ):
            errors.append(t("err_convert_currency_invalid", lang))

        mode = self.query_one("#display_mode", Select).value
        if mode is Select.BLANK:
            mode = self._settings.price_display_mode

        days_str = self.query_one("#due_soon_days", Input).value.strip()
        try:
            days = int(days_str)
            if days < 0:
                raise ValueError
        except ValueError:
            errors.append(t("err_days_invalid", lang))
            days = None

        # Blank monthly income means "unset" (0 → income mode shows a hint).
        income_str = self.query_one("#monthly_income", Input).value.strip()
        income = self._settings.monthly_income
        if income_str == "":
            income = Decimal("0")
        else:
            try:
                income = Decimal(income_str)
                if income < 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                errors.append(t("err_amount_invalid", lang))

        # Blank income currency means "follow base"; else a 3-letter code.
        income_currency = (
            self.query_one("#income_currency", Input).value.strip().upper()
        )
        if income_currency and (
            len(income_currency) != 3 or not income_currency.isalpha()
        ):
            errors.append(t("err_income_currency_invalid", lang))

        if errors:
            self.notify(
                "\n".join(errors),
                title=t("err_fix_before_save", lang),
                severity="error",
                timeout=6,
            )
            return

        # replace() carries over every field this modal doesn't edit
        # (notices/language and the view-state fields convert_column_
        # enabled / totals_view_mode / sort_mode), which a fresh Settings(...)
        # would silently reset to defaults.
        out = replace(
            self._settings,
            base_currency=currency,
            convert_currency=convert_currency,
            price_display_mode=mode,
            due_soon_days=days,
            monthly_income=income,
            monthly_income_currency=income_currency,
        )
        self.dismiss(out)
