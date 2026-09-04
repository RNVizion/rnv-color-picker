"""#252525 no longer exists in this application. RNV-COLLAPSE-GUARD

Ruled 2026-09-02: #252525 collapses onto APP_CARD #2a2a2a. The value was on
neither the surface ladder nor the ink grid, and its neighbours were not a
visible step away. This guard pins the ruling in both directions: the keys
hold the new value, and they hold it THROUGH the constant.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_HEX = "#252525"
NEW_HEX = "#2a2a2a"
CONST = "APP_CARD"
KEYS = ['scrollbar_bg', 'list_bg']
EXPECT = {'dark': ['scrollbar_bg', 'list_bg'], 'image': ['list_bg']}
PALETTE_FILE = "utils/config.py"


def _palettes():
    from utils.config import DARK_THEME_COLORS as D, IMAGE_MODE_COLORS as I; P={'dark':D,'image':I}
    return P


def test_the_ruled_keys_hold_the_new_value():
    for mode, keys in EXPECT.items():
        palette = _palettes()[mode]
        for key in keys:
            assert palette[key] == NEW_HEX, (
                f"{mode}[{key}] is {palette[key]}, ruled onto {NEW_HEX}")


def test_the_old_value_is_gone_from_every_palette():
    for mode, palette in _palettes().items():
        holders = [k for k, v in palette.items() if str(v).lower() == OLD_HEX]
        assert not holders, f"{mode} still holds {OLD_HEX} under {holders}"


def test_the_keys_are_wired_through_the_constant_not_rewritten():
    """Swapping one literal for another passes the value check and defeats
    the point. The constant is what a later substitution changes."""
    src = (ROOT / PALETTE_FILE).read_text(encoding="utf-8-sig")
    for key in KEYS:
        assert re.search(r"'%s':\s+%s\b" % (key, CONST), src), (
            f"{key} is not written as {CONST} in {PALETTE_FILE}")


def test_the_old_value_is_not_written_anywhere_in_source():
    """A sweep for the literal AS A STRING -- quoted. The palette file records
    "was #252525" in a comment beside each ruled key, and that mention is the
    provenance, not a use. The first version of this test matched the bare
    text and failed on its own script's comment: use versus mention, again.
    Excludes this guard and the delivery script, which quote the value in
    order to forbid it."""
    strays = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in {".git", "build", "dist", ".venv", "__pycache__"} for p in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "RNV-COLLAPSE-GUARD" in text or "RNV-COLLAPSE-TOOL-DO-NOT-SWEEP" in text:
            continue
        if re.search(r"""['"]%s['"]""" % OLD_HEX, text, re.I):
            strays.append(str(path.relative_to(ROOT)))
    assert not strays, f"{OLD_HEX} is still written as a literal in: {strays}"
