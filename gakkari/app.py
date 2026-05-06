from __future__ import annotations

from textual.app import App

from gakkari.db import init_db
from gakkari.ui.main_screen import MainScreen


class GakkariApp(App):
    TITLE = "Gakkari OL"
    SUB_TITLE = "がっかり"
    CSS_PATH = None

    SCREENS = {"main": MainScreen}

    def on_mount(self) -> None:
        init_db()
        self.push_screen(MainScreen())
