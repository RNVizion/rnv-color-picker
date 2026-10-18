"""RETIRED_GREY_25 no longer exists in this application. RNV-COLLAPSE-GUARD

Ruled 2026-09-02: RETIRED_GREY_25 collapses onto APP_CARD. The value was on
neither the surface ladder nor the ink grid, and its neighbours were not a
visible step away. This guard pins the ruling in both directions: the keys
hold the new value, and they hold it THROUGH the constant.
"""
from __future__ import annotations

import re
from pathlib import Path
from tests.colour_values import RETIRED_GREY_25

ROOT = Path(__file__).resolve().parent.parent
OLD_HEX = RETIRED_GREY_25
#: RNV-COLOUR-SYNC, 2026-10-16: the keys are held to the value of the constant
#: they were ruled onto, by its name. It was written out here as NEW_HEX,
#: the card rung's value on the day, APP_CARD's; it is the register's now.
CONST = "APP_CARD"
KEYS = ['scrollbar_bg', 'list_bg']
EXPECT = {'dark': ['scrollbar_bg', 'list_bg'], 'image': ['list_bg']}
PALETTE_FILE = "utils/config.py"


def _palettes():
    from utils.config import DARK_THEME_COLORS as D, IMAGE_MODE_COLORS as I; P={'dark':D,'image':I}
    return P


def _new_value():
    """The value the keys were ruled onto: the constant's, as it is now."""
    from utils import config
    return getattr(config, CONST)


def test_the_ruled_keys_hold_the_new_value():
    new = _new_value()
    for mode, keys in EXPECT.items():
        palette = _palettes()[mode]
        for key in keys:
            assert palette[key] == new, (
                f"{mode}[{key}] is {palette[key]}, ruled onto {CONST} {new}")


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
    RETIRED_GREY_25 as "was ..." in a comment beside each ruled key, and that
    mention is the provenance, not a use. The first version of this test
    matched the bare text and failed on its own script's comment: use versus
    mention, again. Excludes the files that carry this guard's marker: this
    guard, tests/colour_values.py, which names the value, and the delivery
    script, which quotes the value in order to forbid it."""
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
