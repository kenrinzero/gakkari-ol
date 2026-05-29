from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

from gakkari.mascot import load_mascot_by_width
from gakkari.strings import t


class MascotScreen(Screen):
    """Full-screen mascot view. `m` from MainScreen opens it; Esc returns.

    Vertical placement (center when the art fits, head-clip/feet-anchor when
    it doesn't) is baked into the art ``Text`` at build time, so it has to be
    rebuilt whenever the terminal size changes. ``compose`` builds it once for
    the initial size and ``on_resize`` rebuilds it on every genuine change —
    otherwise a window grown after opening would leave the art pinned to the
    top with a tall gap below it.
    """

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", priority=True),
        Binding("m", "back", show=False),
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

    #mascot-layout {
        height: 1fr;
        background: #000000;
        border: double #CC8800;
        padding: 0;
    }

    #mascot-art {
        height: 1fr;
        content-align: center top;
        color: #CC8800;
    }
    /* content-align is "center top" but we pad lines manually so the art
       sits center-vertically when it fits, and bottom-anchored when it
       has to clip the head. */

    #mascot-hint {
        height: 1;
        background: #1A0D00;
        color: #CC6600;
        text-align: center;
        padding: 0 1;
    }
    """

    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self._lang = lang
        # Terminal size the current art Text was built for; on_resize compares
        # against it to skip redundant rebuilds (incl. the initial Resize that
        # fires right after mount with the same size compose already used).
        self._art_size: tuple[int, int] = (0, 0)

    def compose(self) -> ComposeResult:
        art_content = self._compose_art()
        self._art_size = (self.app.size.width, self.app.size.height)
        hint_text = (
            f"{t('mascot_screen_title', self._lang)} - "
            f"{t('mascot_screen_hint', self._lang)}"
        )
        with Vertical(id="mascot-layout"):
            yield Static(art_content, id="mascot-art")
            yield Static(hint_text, id="mascot-hint", markup=False)
        yield Footer()

    def on_resize(self, event: events.Resize) -> None:
        size = (self.app.size.width, self.app.size.height)
        if size == self._art_size:
            return
        self._art_size = size
        # Rebuilding via update() (rather than at construction) is safe here:
        # on_resize only fires once the screen is mounted and laid out, well
        # past the early-mount window where update() tripped a pilot crash.
        self.query_one("#mascot-art", Static).update(self._compose_art())

    def _compose_art(self) -> Text:
        # Width-only tier pick: the dedicated screen has the whole terminal,
        # so width is the real constraint — using load_mascot's height check
        # would always fall back to the smallest tier on short windows.
        term = self.app.size
        inner_w = max(0, term.width - 2)
        inner_h = max(0, term.height - 4)
        text = load_mascot_by_width(inner_w)
        if not text:
            return Text(
                t("mascot_screen_too_small", self._lang),
                style="#664400",
            )
        # Two-mode vertical placement, handled manually because Textual's
        # overflow: crop drops bottom rows and content-align: bottom only
        # kicks in when content already fits — neither does what we want
        # on a terminal that's much taller than even the largest tier.
        #   - Art fits: center vertically (equal pad top + bottom).
        #   - Art too tall: keep the last inner_h rows so the feet stay
        #     anchored at the bottom and the head clips off the top.
        lines = text.split("\n")
        if inner_h > 0 and len(lines) > inner_h:
            lines = lines[-inner_h:]
        elif inner_h > len(lines):
            extra = inner_h - len(lines)
            top_pad = extra // 2
            bot_pad = extra - top_pad
            lines = [""] * top_pad + lines + [""] * bot_pad
        return Text("\n".join(lines), no_wrap=True, overflow="crop")

    def action_back(self) -> None:
        self.app.pop_screen()
