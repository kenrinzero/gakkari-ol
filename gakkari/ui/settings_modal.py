from __future__ import annotations

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

            yield Label(t("settings_display_mode", lang), classes="field-label")
            yield Select(
                mode_options,
                value=self._settings.price_display_mode,
                id="display_mode",
                allow_blank=False,
            )

            yield Label(t("settings_due_soon_days", lang), classes="field-label")
            yield Input(value=str(self._settings.due_soon_days), id="due_soon_days")

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

        mode = self.query_one("#display_mode", Select).value
        if mode is Select.BLANK:
            mode = self._settings.price_display_mode

        days_str = self.query_one("#due_soon_days", Input).value.strip()
        try:
            days = int(days_str)
            if days < 0:
                raise ValueError
        except ValueError:
            errors.append(t("err_amount_invalid", lang))
            days = None

        if errors:
            self.notify(
                "\n".join(errors),
                title=t("err_fix_before_save", lang),
                severity="error",
                timeout=6,
            )
            return

        out = Settings(
            id=self._settings.id,
            base_currency=currency,
            price_display_mode=mode,
            due_soon_days=days,
            mascot_enabled=self._settings.mascot_enabled,
            notices_enabled=self._settings.notices_enabled,
            language=self._settings.language,
        )
        self.dismiss(out)
