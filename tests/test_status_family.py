"""RNV-STATUS-GUARD -- the family cannot drift back, and cannot lose its names.

RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

That second marker was added 2026-09-12 and it is not decoration. This file's
RETIRED table names five dead values in order to forbid them, and on the day
test_one_status_family_only was widened to sweep the whole repository in both
notations, this file was the single thing it found. Since RNV-COLOR-SYNC #53 A
(2026-10-17) the five values are written once, in tests/color_values.py,
which carries the same marker for the same reason, and the table reads them
by name. The marker is how a sweep is told the difference between a value
being USED and a value being NAMED -- the same distinction _code_only() below
draws inside a file, drawn one level up between files.

A guard rather than a test: this pins the SHAPE of the change, so a later edit
that reintroduces a Bootstrap value, writes a status color as a literal
again, or points a fill at a text job, fails here with a message saying which
of those happened and why it matters.
"""
from __future__ import annotations

import io
import json
import re
import tokenize
from pathlib import Path

import pytest

from utils import colors as C
from tests.color_values import (
    RETIRED_BOOTSTRAP_ERROR, RETIRED_BOOTSTRAP_SUCCESS, RETIRED_ORPHAN_ERROR_TEXT,
    RETIRED_ORPHAN_ERROR_TEXT_LIGHT, RETIRED_WARNING_AMBER)

ROOT = Path(__file__).resolve().parent.parent

#: RNV-COLOR-SYNC, 2026-10-16. Where each color comes from, as brand_map.json
#: says. The values are held by tests/test_colors_in_sync.py, against the
#: register at the pin; what this file holds is the name each one takes.
BRAND_MAP = json.loads((ROOT / "brand_map.json").read_text(encoding="utf-8"))["colors"]

RETIRED = {
    RETIRED_BOOTSTRAP_SUCCESS: "Bootstrap green, retired -- it and Bootstrap's red collapsed "
                               "to one olive under deuteranopia at about 4 apart",
    RETIRED_WARNING_AMBER: f"Bootstrap amber, retired -- 1.63 on {C.WHITE} and 1.49 on "
                           f"{C.APP_SURFACE_LIGHT_3} against a 3:1 fill floor",
    RETIRED_BOOTSTRAP_ERROR: "Bootstrap red, retired with its family",
    RETIRED_ORPHAN_ERROR_TEXT: f"orphan: derived from {RETIRED_BOOTSTRAP_ERROR}, which no longer exists",
    RETIRED_ORPHAN_ERROR_TEXT_LIGHT: f"orphan: derived from {RETIRED_BOOTSTRAP_ERROR}, which no longer exists",
}

#: Each registered value, by the register name brand_map.json writes it from.
#: RNV-COLOR-SYNC, 2026-10-16: each was written here as its hex code.
REGISTERED = {
    "STATUS_SUCCESS": "STATUS.success",
    "STATUS_ERROR": "STATUS.error",
    "STATUS_SUCCESS_TEXT": "STATUS.success-text",
    "STATUS_SUCCESS_TEXT_LIGHT": "STATUS.success-text-light",
    # RNV-RATING-SCALE (2026-09-12). The warning text pair, which the family
    # had been missing since it was chosen: success and error each carried a
    # dark text value and a light sibling, warning carried neither.
    "STATUS_WARNING_TEXT": "STATUS.warning-text",
    "STATUS_WARNING_TEXT_LIGHT": "STATUS.warning-text-light",
    "STATUS_ERROR_TEXT": "STATUS.error-text",
    "STATUS_ERROR_TEXT_LIGHT": "STATUS.error-text-light",
}

#: The fills this application draws. The register holds a third, the warning
#: fill; nothing here drew it, so since RNV-NAMED-AND-USED (2026-10-04) it
#: is not carried.
FILLS = ("STATUS_SUCCESS", "STATUS_ERROR")
TEXT_FLOOR = 4.5
FILL_FLOOR = 3.0


def _code_only(text: str) -> str:
    """Source with comments and DOCSTRINGS removed -- and nothing else.

    Why this exists: every value these guards forbid is named, in words, in
    the provenance explaining why it was retired. A sweep that cannot tell a
    value being USED from a value being MENTIONED forces the fix to be silence
    about what changed, which is the opposite of what the provenance is for.

    Why it is fussier than it looks: an earlier version dropped every STRING
    token. In Python a color value IS a string literal -- `STATUS_SUCCESS = "<its hex>"` --
    so that version removed the uses along with the mentions and the sweep
    could never find anything. It passed on every input, including a file that
    had just put a retired value back. This file's own guard-the-guard is what
    caught it, which is the entire reason for writing guards that check the
    guard can still see.

    So: a STRING token is dropped only when it STARTS a statement -- a
    docstring, or a bare string expression, which is prose either way. A string
    on the right of an assignment, in a dict, or in a call is kept, because
    that is what a value looks like.
    """
    out = []
    # ENCODING behaves like the start of a line for this purpose.
    at_statement_start = True
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING and at_statement_start:
                at_statement_start = False
                continue
            if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                            tokenize.DEDENT, tokenize.ENCODING):
                at_statement_start = True
            else:
                at_statement_start = False
            out.append(tok.string)
    except (tokenize.TokenError, IndentationError):
        # Falling back to the raw text can only make a sweep STRICTER, never
        # looser, so it fails safe.
        return text
    return " ".join(out)


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(value: str) -> float:
    h = value.lstrip("#")
    if len(h) == 8:          # Qt writes #AARRGGBB -- alpha FIRST
        h = h[2:]
    t = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return 0.2126 * _lin(t[0]) + 0.7152 * _lin(t[1]) + 0.0722 * _lin(t[2])


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


PALETTES = {
    "dark": C.DARK_THEME_COLORS,
    "light": C.LIGHT_THEME_COLORS,
    "image": C.IMAGE_MODE_COLORS,
}


@pytest.mark.parametrize("name,value", sorted(REGISTERED.items()))
def test_every_value_is_the_registered_one(name, value):
    """Pinned by value, not by relationship. A test asserting only that these
    differ from each other would pass on wrong colors.

    RENAMED 2026-09-12 from test_the_five_values_are_the_registered_ones. It
    was parametrized over REGISTERED and had been running over SEVEN since
    2026-09-03, so the name had been wrong for nine days -- a count written in
    prose beside the thing it counts, which nothing compares. The register hit
    the identical defect in the same week: its PERMANENT comment said "six"
    while the dict held seven. The fix in both places is to stop writing the
    number down.

    RNV-COLOR-SYNC, 2026-10-16: pinned by the register name brand_map.json
    writes it from; tests/test_colors_in_sync.py holds the value."""
    assert BRAND_MAP[name] == value


@pytest.mark.parametrize("dead", sorted(RETIRED))
def test_no_retired_value_is_live_in_the_config(dead):
    src = (ROOT / "utils" / "colors.py").read_text(encoding="utf-8-sig")
    assert dead not in _code_only(src), (
        f"utils/colors.py uses {dead} again -- {RETIRED[dead]}")


@pytest.mark.parametrize("dead", sorted(RETIRED))
def test_no_retired_value_is_in_any_palette(dead):
    for mode, palette in PALETTES.items():
        bad = {k: v for k, v in palette.items()
               if isinstance(v, str) and v.lower() == dead}
        assert not bad, f"{mode} still holds {dead} on {sorted(bad)} -- {RETIRED[dead]}"


# RNV-NAMED-AND-USED (2026-10-04): a test stood here that held the palettes'
# semantic keys to the fills by name. The keys went: no line of this
# application looked one up. What it paints from the family is the badges,
# the error text and the rating scale, each held below; and
# tests/test_named_and_used.py fails for any palette color nothing reads.


def test_the_error_text_is_named_in_all_three_palettes():
    """It was a bare literal in dark and image -- the same value written twice,
    which is how two palettes drift apart."""
    src = (ROOT / "utils" / "colors.py").read_text(encoding="utf-8-sig")
    assert src.count("'status_error_text': STATUS_ERROR_TEXT,") == 2
    assert src.count("'status_error_text': STATUS_ERROR_TEXT_LIGHT,") == 1


@pytest.mark.parametrize("name", FILLS)
# RNV-COLOR-SYNC, 2026-10-16: the grounds by name, where they were hex codes.
@pytest.mark.parametrize("ground", [C.BRAND_BLACK, C.APP_CARD,
                                    C.APP_SURFACE_LIGHT_3, C.WHITE])
def test_a_fill_clears_the_fill_floor_and_cannot_carry_text(name, ground):
    """Both halves, because both are load-bearing.

    A fill has to clear 3:1 on every ground -- that is its job. And it must
    NOT clear 4.5:1, because every fill in this family sits at L* 48-59, which
    is exactly what lets one value work on a dark and a light ground. If one
    ever clears the text floor the register has moved it out of the band, and
    somebody needs to know rather than quietly benefiting.
    """
    value = getattr(C, name)
    assert contrast(value, ground) >= FILL_FLOOR, f"{name} on {ground}"
    assert contrast(value, ground) < TEXT_FLOOR, (
        f"{name} now reads {contrast(value, ground):.4f} on {ground} and "
        f"CLEARS the text floor. Do not relax this -- find out whether the "
        f"register moved it out of the fill band.")


@pytest.mark.parametrize("mode,ground", [
    ("dark", "dialog_bg"), ("light", "dialog_bg"), ("image", "dialog_bg"),
])
def test_the_error_text_clears_its_own_panel(mode, ground):
    palette = PALETTES[mode]
    ratio = contrast(palette["status_error_text"], palette[ground])
    assert ratio >= TEXT_FLOOR, (
        f"{mode} error text {palette['status_error_text']} on "
        f"{palette[ground]} = {ratio:.4f}")


def test_the_badges_still_pair_with_black():
    """STATUS_SUCCESS_BG / _FG and STATUS_ERROR_BG / _FG are real pairs --
    background-color and color on one label in ui/settings_panel.py.

    Black reads 4.73 on the new success fill and 5.11 on the new error fill.
    White would fail on both, at 4.44 and 4.11, which is why the _FG values
    did not move with the fills.
    """
    for bg, fg in (("STATUS_SUCCESS_BG", "STATUS_SUCCESS_FG"),
                   ("STATUS_ERROR_BG", "STATUS_ERROR_FG")):
        assert contrast(getattr(C, fg), getattr(C, bg)) >= TEXT_FLOOR


def test_the_role_aliases_point_at_the_color_constants():
    """The naming rule: a constant names a COLOR, an alias names a ROLE.

    STATUS_ERROR_BG was already this shape. STATUS_SUCCESS_BG held its own
    copy of the green instead, and so did an alias for an active label,
    which nothing painted; that alias went on 2026-10-04 (RNV-NAMED-AND-
    USED).
    """
    assert C.STATUS_SUCCESS_BG == C.STATUS_SUCCESS
    assert C.STATUS_ERROR_BG == C.STATUS_ERROR


def test_the_two_spellings_did_not_come_back():
    """The register recorded that this one color was derived independently
    under TWO identifiers across three applications -- STATUS_ERROR_LIGHT here
    and in the transformer, STATUS_ERROR_TEXT_LIGHT in the palette manager.
    One name now."""
    src = (ROOT / "utils" / "colors.py").read_text(encoding="utf-8-sig")
    assert not re.search(r"\bSTATUS_ERROR_LIGHT\b", _code_only(src)), (
        "STATUS_ERROR_LIGHT is back; the name is STATUS_ERROR_TEXT_LIGHT")


def test_the_light_text_is_not_computed_from_the_fill():
    """lighten(STATUS_ERROR, -20) against the current base gives
    EXAMPLE_OLD_RULE_ERROR_TEXT_LIGHT -- neither the old
    RETIRED_ORPHAN_ERROR_TEXT_LIGHT nor the registered STATUS_ERROR_TEXT_LIGHT.
    A derivative whose
    rule no longer produces it is not a derivative."""
    assert C.STATUS_ERROR_TEXT_LIGHT != C.lighten(C.STATUS_ERROR, -20)
    src = (ROOT / "utils" / "colors.py").read_text(encoding="utf-8-sig")
    assert "lighten(STATUS_ERROR" not in _code_only(src)


def test_this_guard_is_actually_looking():
    """Guard the guard. Every sweep above walks palettes or source; if either
    ever turned up empty they would pass while checking nothing."""
    for mode, palette in PALETTES.items():
        assert len(palette) > 40, f"{mode} has only {len(palette)} keys"
    src = (ROOT / "utils" / "colors.py").read_text(encoding="utf-8-sig")
    assert len(_code_only(src)) > 5000, "the tokenizer returned almost nothing"
    # RNV-COLOR-SYNC, 2026-10-16: the success fill by name, where it was
    # its hex code; the sync writes it into the code as a literal.
    assert C.STATUS_SUCCESS in _code_only(src), (
        "the code-only sweep cannot see a value that is definitely in the code")
