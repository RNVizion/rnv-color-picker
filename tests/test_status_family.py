"""RNV-STATUS-GUARD -- the family cannot drift back, and cannot lose its names.

RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

That second marker was added 2026-09-12 and it is not decoration. This file's
RETIRED table names five dead values in order to forbid them, and on the day
test_one_status_family_only was widened to sweep the whole repository in both
notations, this file was the single thing it found. The marker is how a sweep
is told the difference between a value being USED and a value being NAMED --
the same distinction _code_only() below draws inside a file, drawn one level
up between files.

A guard rather than a test: this pins the SHAPE of the change, so a later edit
that reintroduces a Bootstrap value, writes a status colour as a literal
again, or points a fill at a text job, fails here with a message saying which
of those happened and why it matters.
"""
from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

from utils import config as C

ROOT = Path(__file__).resolve().parent.parent

RETIRED = {
    "#28a745": "Bootstrap green, retired -- it and Bootstrap's red collapsed "
               "to one olive under deuteranopia at about 4 apart",
    "#ffc107": "Bootstrap amber, retired -- 1.63 on #ffffff and 1.49 on "
               "#f5f5f5 against a 3:1 fill floor",
    "#dc3545": "Bootstrap red, retired with its family",
    "#e56b77": "orphan: derived from #dc3545, which no longer exists",
    "#c82131": "orphan: derived from #dc3545, which no longer exists",
}

REGISTERED = {
    "STATUS_SUCCESS": "#926c89",
    "STATUS_WARNING": "#a2703c",
    "STATUS_ERROR": "#c75b64",
    "STATUS_SUCCESS_TEXT": "#ad85a3",
    "STATUS_SUCCESS_TEXT_LIGHT": "#825d79",
    # RNV-RATING-SCALE (2026-09-12). The warning text pair, which the family
    # had been missing since it was chosen: success and error each carried a
    # dark text value and a light sibling, warning carried neither.
    "STATUS_WARNING_TEXT": "#bc8752",
    "STATUS_WARNING_TEXT_LIGHT": "#8e5e2b",
    "STATUS_ERROR_TEXT": "#dd6f77",
    "STATUS_ERROR_TEXT_LIGHT": "#ae4650",
}

FILLS = ("STATUS_SUCCESS", "STATUS_WARNING", "STATUS_ERROR")
TEXT_FLOOR = 4.5
FILL_FLOOR = 3.0


def _code_only(text: str) -> str:
    """Source with comments and DOCSTRINGS removed -- and nothing else.

    Why this exists: every value these guards forbid is named, in words, in
    the provenance explaining why it was retired. A sweep that cannot tell a
    value being USED from a value being MENTIONED forces the fix to be silence
    about what changed, which is the opposite of what the provenance is for.

    Why it is fussier than it looks: an earlier version dropped every STRING
    token. In Python a colour value IS a string literal -- `X = "#926c89"` --
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
    differ from each other would pass on wrong colours.

    RENAMED 2026-09-12 from test_the_five_values_are_the_registered_ones. It
    was parametrised over REGISTERED and had been running over SEVEN since
    2026-09-03, so the name had been wrong for nine days -- a count written in
    prose beside the thing it counts, which nothing compares. The register hit
    the identical defect in the same week: its PERMANENT comment said "six"
    while the dict held seven. The fix in both places is to stop writing the
    number down."""
    assert getattr(C, name) == value


@pytest.mark.parametrize("dead", sorted(RETIRED))
def test_no_retired_value_is_live_in_the_config(dead):
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    assert dead not in _code_only(src), (
        f"utils/config.py uses {dead} again -- {RETIRED[dead]}")


@pytest.mark.parametrize("dead", sorted(RETIRED))
def test_no_retired_value_is_in_any_palette(dead):
    for mode, palette in PALETTES.items():
        bad = {k: v for k, v in palette.items()
               if isinstance(v, str) and v.lower() == dead}
        assert not bad, f"{mode} still holds {dead} on {sorted(bad)} -- {RETIRED[dead]}"


@pytest.mark.parametrize("key,const", [
    ("success", "STATUS_SUCCESS"),
    ("warning", "STATUS_WARNING"),
    ("error", "STATUS_ERROR"),
])
def test_every_semantic_key_is_wired_through_a_constant(key, const):
    """Swapping one literal for another passes a value check and defeats the
    point: the constant is what a later register change moves.

    Before 2026-09-03 all three of these were bare literals in two palettes,
    and the green additionally had two more copies in the file tail -- one
    colour at four addresses, none of them naming it.
    """
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    found = len(re.findall(r"'%s':\s+%s,\n" % (key, const), src))
    assert found == 2, (
        f"'{key}' is wired through {const} in {found} palettes, not 2")


def test_the_error_text_is_named_in_all_three_palettes():
    """It was a bare literal in dark and image -- the same value written twice,
    which is how two palettes drift apart."""
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    assert src.count("'status_error_text': STATUS_ERROR_TEXT,") == 2
    assert src.count("'status_error_text': STATUS_ERROR_TEXT_LIGHT,") == 1


@pytest.mark.parametrize("name", FILLS)
@pytest.mark.parametrize("ground", ["#1a1a1a", "#2a2a2a", "#f5f5f5", "#ffffff"])
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
    ("dark", "panel_bg"), ("light", "panel_bg"), ("image", "panel_bg"),
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


def test_the_role_aliases_point_at_the_colour_constants():
    """The naming rule: a constant names a COLOUR, an alias names a ROLE.

    STATUS_ERROR_BG was already this shape. STATUS_SUCCESS_BG and
    STATUS_ACTIVE_COLOR each held their own copy of the green instead.
    """
    assert C.STATUS_SUCCESS_BG == C.STATUS_SUCCESS
    assert C.STATUS_ERROR_BG == C.STATUS_ERROR
    assert C.STATUS_ACTIVE_COLOR == C.STATUS_SUCCESS_TEXT
    assert C.STATUS_ACTIVE_COLOR != C.STATUS_SUCCESS, (
        "the active alias points at the FILL. An `active` label is painted "
        "with `color:` -- the register ruled on 2026-09-04 that it aliases "
        "success-text -- and the fill reads 3.91 on BRAND_BLACK against a 4.5 "
        "text floor. Nothing paints this constant in THIS app, which is why "
        "it has to be right: it is what the next reader copies.")


def test_the_two_spellings_did_not_come_back():
    """The register recorded that this one colour was derived independently
    under TWO identifiers across three applications -- STATUS_ERROR_LIGHT here
    and in the transformer, STATUS_ERROR_TEXT_LIGHT in the palette manager.
    One name now."""
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    assert not re.search(r"\bSTATUS_ERROR_LIGHT\b", _code_only(src)), (
        "STATUS_ERROR_LIGHT is back; the name is STATUS_ERROR_TEXT_LIGHT")


def test_the_light_text_is_not_computed_from_the_fill():
    """lighten(STATUS_ERROR, -20) against the current base gives #b44753 --
    neither the old #c82131 nor the registered #ae4650. A derivative whose
    rule no longer produces it is not a derivative."""
    assert C.STATUS_ERROR_TEXT_LIGHT != C.lighten(C.STATUS_ERROR, -20)
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    assert "lighten(STATUS_ERROR" not in _code_only(src)


def test_this_guard_is_actually_looking():
    """Guard the guard. Every sweep above walks palettes or source; if either
    ever turned up empty they would pass while checking nothing."""
    for mode, palette in PALETTES.items():
        assert len(palette) > 40, f"{mode} has only {len(palette)} keys"
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    assert len(_code_only(src)) > 5000, "the tokeniser returned almost nothing"
    assert "#926c89" in _code_only(src), (
        "the code-only sweep cannot see a value that is definitely in the code")
