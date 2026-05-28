from __future__ import annotations

from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"
_CACHE: dict[str, str] = {}

# Each tier: (name, min_panel_width, min_panel_height).
# min_panel_height is intentionally lower than the art's true line count —
# we'd rather show a partly-clipped figure than nothing.
# Tiers ordered largest first; first one whose minimums fit wins.
_TIERS: tuple[tuple[str, int, int], ...] = (
    ("90", 79, 60),
    ("70", 62, 45),
    ("50", 45, 30),
    ("40", 36, 22),
)


def _trim(text: str) -> str:
    lines = text.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return ""
    indent = min(len(l) - len(l.lstrip()) for l in non_empty)
    trimmed = [l[indent:].rstrip() if l.strip() else "" for l in lines]
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    return "\n".join(trimmed)


def _read(name: str) -> str:
    if name not in _CACHE:
        path = _ASSETS / f"mascot_{name}.txt"
        try:
            _CACHE[name] = _trim(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError):
            # Mascot is decoration — a missing/unreadable asset must not crash
            # the app. Cache an empty string so we don't retry the dead path.
            _CACHE[name] = ""
    return _CACHE[name]


def load_mascot(inner_width: int, inner_height: int) -> str | None:
    for name, min_w, min_h in _TIERS:
        if inner_width >= min_w and inner_height >= min_h:
            art = _read(name)
            return art if art else None
    return None


def load_mascot_by_width(inner_width: int) -> str | None:
    """Width-only tier pick — for views with vertical room to spare.

    The dedicated mascot screen has the whole terminal, so height almost
    never becomes a real ceiling; using ``load_mascot`` there would always
    pick the smallest tier on short windows. Here we pick the largest tier
    whose width fits, and trust the caller to bottom-anchor + crop so a
    partly-clipped figure degrades gracefully on a short terminal.
    """
    for name, min_w, _ in _TIERS:
        if inner_width >= min_w:
            art = _read(name)
            return art if art else None
    return None
