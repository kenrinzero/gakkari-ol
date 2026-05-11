from __future__ import annotations

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from gakkari.db import DB_PATH
from gakkari.strings import t


def _default_path(fmt: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DB_PATH.parent / f"gakkari_export_{stamp}.{fmt}"


class ExportModal(ModalScreen[tuple[str, Path] | None]):

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    CSS = """
    ExportModal {
        align: center middle;
    }

    #dialog {
        width: 70;
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

    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self._lang = lang

    def compose(self) -> ComposeResult:
        lang = self._lang
        with Vertical(id="dialog"):
            yield Label(t("export_title", lang), id="dialog-title")

            yield Label(t("export_format", lang), classes="field-label")
            yield Select(
                [("CSV", "csv"), ("JSON", "json")],
                value="csv",
                id="format",
                allow_blank=False,
            )

            yield Label(t("export_path", lang), classes="field-label")
            yield Input(value=str(_default_path("csv")), id="path")

            with Horizontal(id="button-row"):
                yield Button(t("modal_save", lang), id="save", variant="primary")
                yield Button(t("modal_cancel", lang), id="cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "format":
            return
        fmt = event.value
        if fmt is Select.BLANK:
            return
        path_input = self.query_one("#path", Input)
        # Swap extension on existing path so the user does not need to retype.
        p = Path(path_input.value)
        path_input.value = str(p.with_suffix(f".{fmt}"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _save(self) -> None:
        fmt = self.query_one("#format", Select).value
        if fmt is Select.BLANK:
            fmt = "csv"
        path_str = self.query_one("#path", Input).value.strip()
        if not path_str:
            return
        self.dismiss((fmt, Path(path_str)))
