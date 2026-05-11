from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from gakkari.strings import t


class ImportModal(ModalScreen[Path | None]):

    BINDINGS = [
        Binding("escape", "cancel", show=False),
    ]

    CSS = """
    ImportModal {
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

    Input {
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
            yield Label(t("import_title", lang), id="dialog-title")
            yield Label(t("import_path", lang), classes="field-label")
            yield Input(placeholder="path/to/export.csv", id="path")
            with Horizontal(id="button-row"):
                yield Button(t("modal_save", lang), id="ok", variant="primary")
                yield Button(t("modal_cancel", lang), id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._submit()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        path_str = self.query_one("#path", Input).value.strip()
        if not path_str:
            return
        path = Path(path_str)
        if not path.is_file():
            self.notify(
                t("import_file_missing", self._lang),
                severity="error",
                timeout=4,
            )
            return
        self.dismiss(path)
