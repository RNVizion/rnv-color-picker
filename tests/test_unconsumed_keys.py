"""
`text_secondary` is defined and painted nowhere, and the palette says so.

It is a redundant twin of `text_muted`, which carries the same value in both
palettes and does the job in six places. Rather than delete it, the values are
kept correct and a NOT CONSUMED note sits beside each, so wiring it up is one
line and not a colour decision.

That arrangement only helps while the note is true. These tests hold both
halves together: the key stays unpainted, and the note stays present. If
someone wires it up, the note becomes a lie and the run says so.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_PY = ROOT / "utils" / "config.py"
KEY = "text_secondary"


def _source(path: pathlib.Path) -> str:
    # Five files in this repo begin with a UTF-8 BOM. Reading them as plain
    # utf-8 makes ast.parse refuse them and makes a sweep silently skip them,
    # so the encoding here is deliberate.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _references(key: str) -> list[str]:
    sites = []
    for path in ROOT.rglob("*.py"):
        parts = path.parts
        if any(p in parts for p in (".git", "__pycache__", "tests")):
            continue
        if path.name.startswith("test_") or path == CONFIG_PY:
            continue
        # A delivery script sitting at the root mentions the key it moves.
        # Sweeping it makes the guard fail on the very run that installs it --
        # the same trap the repos' placement guards already exempt `up*.py` for.
        if path.parent == ROOT and path.name.startswith("up"):
            continue
        if key in _source(path):
            sites.append(path.relative_to(ROOT).as_posix())
    return sorted(sites)


def test_the_sweep_is_actually_reading_something():
    """Guard the guard. A walk that finds nothing passes forever."""
    walked = [p for p in ROOT.rglob("*.py")
              if not any(x in p.parts for x in (".git", "__pycache__"))]
    assert len(walked) > 20, f"the sweep only found {len(walked)} files"
    # and it must be able to see a key that IS painted
    assert _references("text_muted"), (
        "the sweep cannot find text_muted, which is painted in six places -- "
        "it would not find text_secondary either")


def test_the_key_is_still_unpainted():
    sites = _references(KEY)
    assert sites == [], (
        f"{KEY} is now referenced in {sites}. If it is being painted, delete "
        f"the NOT CONSUMED notes in utils/config.py -- they are no longer true.")


def test_the_note_is_still_there():
    source = _source(CONFIG_PY)
    notes = len(re.findall(r"#\s*NOT CONSUMED", source))
    assert notes == 2, (
        f"expected a NOT CONSUMED note beside each of the two {KEY} values, "
        f"found {notes}")


def test_the_twin_still_carries_the_same_values():
    """The note says text_muted does this job. If they drift apart, wiring
    text_secondary up would no longer be the one-line change it promises."""
    from utils.config import DARK_THEME_COLORS, LIGHT_THEME_COLORS
    for name, theme in (("DARK", DARK_THEME_COLORS),
                        ("LIGHT", LIGHT_THEME_COLORS)):
        assert theme[KEY] == theme["text_muted"], (
            f"{name}: {KEY} is {theme[KEY]} but text_muted is "
            f"{theme['text_muted']} -- the note beside {KEY} is out of date")
