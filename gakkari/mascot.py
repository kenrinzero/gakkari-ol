from __future__ import annotations

from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"
_CACHE: dict[str, str] = {}

# Art tiers, largest first. ``load_mascot_fit`` measures each tier's actual
# size and picks the largest that fully fits the terminal, so the old per-tier
# minimum width/height thresholds are no longer needed.
_TIERS: tuple[str, ...] = ("90", "70", "50", "40")


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


def load_mascot_fit(inner_width: int, inner_height: int) -> str | None:
    """Largest tier whose *actual* art fits fully inside the given box.

    The dedicated mascot screen wants the biggest figure that still shows in
    full — no clipped head. Each tier's true measured size is checked against
    both width and height (the figures are much taller than the old looser
    thresholds, so width-only picking cropped the head on wide-but-short
    windows). Tiers are largest-first, so the first that fits wins. If even
    the smallest tier is too big for the box, its art is returned anyway so the
    caller can bottom-anchor + crop rather than show nothing.
    """
    smallest = ""
    for name in _TIERS:  # largest first
        art = _read(name)
        if not art:
            continue
        smallest = art  # largest-first => last assignment is the smallest tier
        lines = art.split("\n")
        height = len(lines)
        width = max((len(line) for line in lines), default=0)
        if width <= inner_width and height <= inner_height:
            return art
    return smallest or None
