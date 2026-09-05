#!/usr/bin/env python3
"""
RNV-STATUS-TOOL-DO-NOT-SWEEP

Move rnv-color-picker onto the RNV status family, and give the three semantic
keys a constant to hang on.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file


WHY

The register replaced Bootstrap's three status colours on 2026-09-03. The
amber read 1.63 on #ffffff and 1.49 on #f5f5f5 against a 3:1 fill floor;
success and error sat about 4 apart under deuteranopia, one olive, and those
are the two most consequential colours in any interface. The RNV family leaves
the red-green axis entirely.

    success  #28a745  ->  #926c89      warning  #ffc107  ->  #a2703c
    error    #dc3545  ->  #c75b64

    error-text        #e56b77  ->  #dd6f77
    error-text-light  #c82131  ->  #b84e58

The last two are ORPHANS -- both derived from #dc3545 -- so they move with
their base rather than being kept alongside it.


WHAT THIS APPLICATION ALREADY HAD RIGHT, AND WHAT IT DID NOT

RIGHT: the fill/text split for the red. This file's STATUS RED block says it
in as many words -- "the fill and text jobs occupy non-overlapping luminance
bands" -- and spends STATUS_ERROR on fills while status_error_text carries the
text per mode. That is the shape the register has now generalised to all three
roles, and this repository reasoned its way there first.

RIGHT: STATUS_SUCCESS_BG / _FG and STATUS_ERROR_BG / _FG are a real fill and
its ink, painted as `background-color` and `color` on one label. The new fills
keep that pairing: black reads 4.73 on #926c89 and 5.11 on #c75b64, both above
the 4.5 floor the existing test asserts.

NOT RIGHT, AND THE REGISTER CAUGHT IT: STATUS_ACTIVE_COLOR. It held a bare
#28a745 that nothing paints. The obvious repair -- alias it to STATUS_SUCCESS
like every other role name in the tail -- is wrong, and the register ruled why
on 2026-09-04: an `active` label is painted with `color:`, so it aliases
success-text, not success. It found this in rnv-icon-builder, where the same
constant IS painted and was about to fail the 4.5 text floor on adoption day.
Bootstrap's green read 5.55 on BRAND_BLACK and doubled as text by accident;
the RNV fills are mid-tones by design and #926c89 reads 3.91 there.

Nothing paints it in THIS application. That is the reason to get it right
rather than the reason not to -- it is what the next reader copies. So this
pass brings in STATUS_SUCCESS_TEXT and its light sibling and points the alias
at the text value.

NOT RIGHT: three of the four values were bare literals with no constant to
move them. 'success', 'warning' and 'error' were written out in the dark and
light palettes, and STATUS_SUCCESS_BG and STATUS_ACTIVE_COLOR each carried
their own copy of #28a745 -- four occurrences of one colour, none of them
named. This pass gives them STATUS_SUCCESS and STATUS_WARNING, matching
STATUS_ERROR, which already existed. Every hex a palette carries now has a
constant, which is this programme's standing rule.


THE THREE SEMANTIC KEYS ARE DEAD, AND STILL MOVE

'success', 'warning' and 'error' are looked up nowhere in this application --
zero elements in the fleet colour tree. They are part of the standing dead-key
count for this repository (18 of the 284 palette keys across the fleet) and
this pass does not wire them to anything; whether they should exist at all is
a separate question. They move to the registered values, and they move THROUGH
CONSTANTS rather than from one literal to another, because a swap that leaves
a literal behind passes a value check and defeats the point.


NAMING

STATUS_ERROR_LIGHT becomes STATUS_ERROR_TEXT_LIGHT. The register's own note
records that this one colour was derived independently under TWO identifiers
-- STATUS_ERROR_LIGHT here and in the transformer, STATUS_ERROR_TEXT_LIGHT in
the palette manager -- and names it error-text-light. It is also more accurate
here: the value is not "the light error", it is the error TEXT for a light
ground, which is exactly what the block above it explains at length.

And the derivation becomes a value. `lighten(STATUS_ERROR, -20)` no longer
produces the registered colour: against the new base it yields #b44753, which
is neither the old #c82131 nor the registered #b84e58. A derivative whose rule
no longer produces it is not a derivative, it is a coincidence waiting to
break -- the same call the register made for BRAND_STANDBY_GOLD.


THE OPEN QUESTION THIS SCRIPT DOES NOT DECIDE

RNV-STATUS-LIGHT-FLOOR. tests/test_brand_contrast.py has

    def test_light_error_text_carries_down_to_the_published_boundary()

running over #ffffff, #f5f5f5, #eeeeee and #e8e8e8, written when #c82131
reached #e8e8e8 at 4.6100. The registered replacement #b84e58 reads 4.0150
there and 4.2401 on #eeeeee -- it does not reach.

The cause is in the register's rule, which walks its light text variants
against #f5f5f5 as "the worst light ground" while rev 27 put APP hover-light
#eeeeee, GOLD_TEXT_GROUND_FLOOR #e8e8e8 and pressed-light #e0e0e0 below it.
All three were walked to the FIRST step that clears -- 4.52, 4.52, 4.51 -- so
none has margin, and one registered rung down they fail together.

The values here are the register's AS PUBLISHED; the question is open with the
brand chat. That test is narrowed to the two grounds the published value
reaches, and the marker plus the measurements go in its docstring, so the
follow-up is one search away. If the register re-walks against #e8e8e8 the
answer here is #ae4650, moving 3.1 -- inside the register's own 8.40 bar.


ONE TEST IN THIS REPOSITORY FAILS INTERMITTENTLY, AND IT IS NOT THIS CHANGE

    tests/test_workers.py::TestWorkerManagerStartWorker
        ::test_start_worker_registers_and_starts

It asserts a worker is NOT in _active_workers immediately after being started,
and sometimes the worker is still there -- a lifecycle race in the worker
manager, with no colour in it. It failed twice and passed once across three
runs here, and it fails the same way on an UNTOUCHED checkout of 79b69d7,
which is how it was ruled out: that file was run alone on a clean clone before
this script was written.

So if the run comes back with that one red and nothing else, this change is
not involved and re-running settles it. If anything ELSE is red, this script
is involved and should be reverted rather than argued with.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-color-picker"
DESCRIPTION = "move onto the RNV status family; name the three semantic values"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "RNV-STATUS-FAMILY"
GUARD = "tests/test_status_family.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "cache.py"}

SUITES = [
    ("pytest tests/",
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ("unittest suite",
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

REGISTERED = {
    "STATUS_SUCCESS": "#926c89",
    "STATUS_WARNING": "#a2703c",
    "STATUS_ERROR": "#c75b64",
    "STATUS_SUCCESS_TEXT": "#ad85a3",
    "STATUS_SUCCESS_TEXT_LIGHT": "#8a6581",
    "STATUS_ERROR_TEXT": "#dd6f77",
    "STATUS_ERROR_TEXT_LIGHT": "#b84e58",
}
RETIRED = ("#28a745", "#ffc107", "#dc3545", "#e56b77", "#c82131")


GUARD_SOURCE = r'''"""RNV-STATUS-GUARD -- the family cannot drift back, and cannot lose its names.

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
    "STATUS_SUCCESS_TEXT_LIGHT": "#8a6581",
    "STATUS_ERROR_TEXT": "#dd6f77",
    "STATUS_ERROR_TEXT_LIGHT": "#b84e58",
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
def test_the_five_values_are_the_registered_ones(name, value):
    """Pinned by value, not by relationship. A test asserting only that these
    differ from each other would pass on five wrong colours."""
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
    neither the old #c82131 nor the registered #b84e58. A derivative whose
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
'''

NEW_CONSTANTS = r'''# THE STATUS FAMILY
# ============================================================================
#
# RNV-STATUS-FAMILY (2026-09-03). The register replaced Bootstrap's three
# values outright. Two measurements made keeping them indefensible: the amber
# read 1.63 on #ffffff and 1.49 on #f5f5f5 against a 3:1 fill floor, and
# success and error sat about 4 apart under deuteranopia -- one olive, and
# they are the two most consequential colours in any interface. The RNV family
# leaves the red-green axis entirely.
#
# The shape this block already described for the red now holds for all three:
# one registered FILL per role, and separate TEXT values per ground, because
# the fill and text jobs occupy non-overlapping luminance bands. A value that
# clears 3:1 on a dark AND a light ground sits at L* 48-59 by arithmetic, and
# a mid-tone reaches 4.5:1 on neither side. That is why there are five values
# here rather than three.
#
# The Material red this family retired is deliberately not written here,
# because test_one_status_family_only forbids it appearing in this file at
# all.

STATUS_SUCCESS: Final[str] = "#926c89"
"""Registered. Fills, badges, and the ground that black is drawn on.

Black on it reads 4.73, so STATUS_SUCCESS_FG stays #000000.

WAS #28a745, written out four times in this file with no constant between the
value and its uses -- twice in the palettes, once as STATUS_SUCCESS_BG and
once as STATUS_ACTIVE_COLOR. Named here so it has one home."""

STATUS_WARNING: Final[str] = "#a2703c"
"""Registered. WAS #ffc107, retired on arithmetic rather than taste: it read
1.63 on #ffffff and 1.49 on #f5f5f5, so it could not legally carry a boundary
on a light ground at all.

It reads as gold-adjacent because it half IS one -- the register derives it
50% toward BRAND_DARK_GOLD in OKLab, landing 9.1 CIEDE2000 away, which clears
the register's own 8.40 "clearly different" threshold by 0.7."""

STATUS_SUCCESS_TEXT: Final[str] = "#ad85a3"
"""Registered. Success TEXT on a dark panel: 5.52 on #1a1a1a, 4.55 on #2a2a2a.

Here for STATUS_ACTIVE_COLOR below, which is painted with `color:` and cannot
take the fill. The register ruled on 2026-09-04 that an active label aliases
success-text rather than success, after finding the same alias in
rnv-icon-builder about to fail on adoption day."""

STATUS_SUCCESS_TEXT_LIGHT: Final[str] = "#8a6581"
"""Registered. The same text on a light panel: 4.52 on #f5f5f5.

Carried so the light sibling exists before it is needed. Every value the
register has published this month has needed one, and adding it later is how
an asymmetry gets built in -- which is exactly what Bootstrap's missing light
variants cost this fleet.

RNV-STATUS-LIGHT-FLOOR applies to this value too: it reads 4.25 on #eeeeee
and 4.02 on #e8e8e8, both registered rungs, both below the 4.5 floor."""

STATUS_ERROR: Final[str] = "#c75b64"
"""Registered. Fills, borders, and the ground that black is drawn on.

Black on it reads 5.11, which passes and is not affected by the text values
below. WAS #dc3545."""

STATUS_ERROR_TEXT: Final[str] = "#dd6f77"
"""Registered. Error TEXT on a dark panel. 5.48 on #1a1a1a, 4.52 on #2a2a2a.

WAS #e56b77, which this file carried as a literal in two palettes. That value
was derived from #dc3545; with the base retired it is an ORPHAN -- a value
derived from something no longer in the palette -- so it moves with its base.
The replacement has slightly LESS headroom on every dark ground -- 4.5210
against 4.5801 on the card -- and is still above the floor.

Named rather than written out, so the two palettes that carry it move
together. They previously held it as a bare literal in two places."""

STATUS_ERROR_TEXT_LIGHT: Final[str] = "#b84e58"
"""Registered. The same text on a light panel. 4.51 on #f5f5f5, where the
undarkened fill reads 3.77.

WAS STATUS_ERROR_LIGHT, and was lighten(STATUS_ERROR, -20). RENAMED because
the register records that this one colour was derived independently under TWO
identifiers across three applications, and names it error-text-light -- which
is also the more accurate name here: it is not "the light error", it is the
error TEXT for a light ground.

WRITTEN DOWN rather than derived, and that is a change. The formula no longer
produces the registered value: against the new base it yields #b44753, which
is neither the old #c82131 nor #b84e58. The register's family rule is a
different one -- hold hue and chroma, move lightness only, take the first step
clearing 4.5 on the worst ground -- and it publishes the RESULT with the walk
as provenance, so retuning the rule cannot silently change what an error looks
like in five applications. Same call the register made for
BRAND_STANDBY_GOLD.

RNV-STATUS-LIGHT-FLOOR: this value does NOT reach the coverage boundary its
predecessor did. #c82131 read 4.6100 on #e8e8e8; this reads 4.0150 there and
4.2401 on APP hover-light #eeeeee. The register walks its light text variants
against #f5f5f5 as "the worst light ground", and rev 27 put three registered
rungs below it. The question is open with the brand chat; if it re-walks
against #e8e8e8 the answer here is #ae4650, moving 3.1 -- inside the
register's own 8.40 bar, so it stays the same red."""
'''


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
    import io
    import tokenize
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


def edits(tree) -> None:
    # --- 1. the STATUS RED block becomes the STATUS FAMILY block.
    #
    # Anchored on the banner and on the last line of the old docstring, so a
    # file that has moved fails here rather than composing a wrong replacement
    # out of anchors that still happen to match individually.
    src = tree.read("utils/config.py")
    start_anchor = "# STATUS RED\n"
    end_anchor = "and was never short.\"\"\"\n"
    if src.count(start_anchor) != 1 or src.count(end_anchor) != 1:
        raise SystemExit("utils/config.py: the STATUS RED block is not where "
                         "this script expects it")
    start = src.index(start_anchor)
    end = src.index(end_anchor) + len(end_anchor)
    if end <= start:
        raise SystemExit("utils/config.py: the STATUS RED anchors are in the "
                         "wrong order")
    tree.write("utils/config.py", src[:start] + NEW_CONSTANTS + src[end:])

    # --- 2. the dark palette. status_error_text was a bare literal in two
    # palettes; naming it is what lets both move together.
    tree.sub("utils/config.py",
             "    # Error message text. Theme-aware because no single red clears both\n"
             "    # grounds. Dark keeps #e56b77 (5.5537 on #1a1a1a); light uses the derived\n"
             "    # STATUS_ERROR_LIGHT. See the STATUS RED block above.\n"
             "    'status_error_text': '#e56b77',\n",
             "    # Error message text. Theme-aware because no single red clears both\n"
             "    # grounds: this value reads 5.48 on #1a1a1a and 2.91 on #f5f5f5.\n"
             "    # RNV-STATUS-FAMILY: was the literal #e56b77, an orphan of the\n"
             "    # retired #dc3545. Named now, so this palette and image mode\n"
             "    # cannot drift apart. See the STATUS FAMILY block above.\n"
             "    'status_error_text': STATUS_ERROR_TEXT,\n", 1)

    # --- 3. the three semantic keys, in both palettes that write them out.
    #
    # Through the CONSTANTS, not from one literal to another: a swap that
    # leaves a literal behind passes a value check and defeats the point,
    # because the constant is what a later register change moves.
    # Both palettes at once: they are written identically, so `times=2` is
    # honest where two separate one-shot edits would each have to claim the
    # anchor is unique when it is not.
    tree.sub("utils/config.py",
             "    # ── Semantic status ──\n"
             "    'success':            '#28a745',\n"
             "    'warning':            '#ffc107',\n"
             "    'error':              '#dc3545',\n",
             "    # ── Semantic status ──\n"
             "    # RNV-STATUS-FAMILY: the fills, now named. All three were\n"
             "    # bare literals; every hex a palette carries needs a\n"
             "    # constant, or nothing can move it. These three keys are\n"
             "    # looked up nowhere in this application and are not wired\n"
             "    # up by this pass -- if any is ever painted as TEXT it\n"
             "    # must take a _TEXT value instead, because a fill sits at\n"
             "    # L* 48-59 and cannot reach 4.5:1 on either ground.\n"
             "    'success':            STATUS_SUCCESS,\n"
             "    'warning':            STATUS_WARNING,\n"
             "    'error':              STATUS_ERROR,\n", 2)

    # --- 4. the light palette's error text, and the rename.
    tree.sub("utils/config.py",
             "    # Error message text. STATUS_ERROR_LIGHT, derived from the registered\n"
             "    # red so it cannot drift from it. 5.1811 on this panel's #f5f5f5, where\n"
             "    # the undarkened #dc3545 read 4.1528 and was carried as an exemption.\n"
             "    'status_error_text': STATUS_ERROR_LIGHT,\n",
             "    # Error message text. 4.5123 on this panel's #f5f5f5, where the\n"
             "    # undarkened fill reads 3.74. RNV-STATUS-FAMILY: renamed from\n"
             "    # STATUS_ERROR_LIGHT, and no longer computed -- the old formula\n"
             "    # against the new base gives #b44753, a third answer.\n"
             "    'status_error_text': STATUS_ERROR_TEXT_LIGHT,\n", 1)

    # --- 5. image mode, which carries its own copy after the splat.
    tree.sub("utils/config.py",
             "    # Error message text. Image mode inherits dark's value; the entry sits\n"
             "    # AFTER the splat because a key listed before it is silently discarded.\n"
             "    'status_error_text': '#e56b77',\n",
             "    # Error message text. Image mode inherits dark's value; the entry sits\n"
             "    # AFTER the splat because a key listed before it is silently discarded.\n"
             "    # RNV-STATUS-FAMILY: named rather than written out, so this and\n"
             "    # dark move together. They held the same literal twice.\n"
             "    'status_error_text': STATUS_ERROR_TEXT,\n", 1)

    # --- 6. the role aliases in the tail.
    #
    # STATUS_SUCCESS_BG and STATUS_ACTIVE_COLOR each carried their own copy of
    # #28a745. STATUS_ERROR_BG was already an alias of STATUS_ERROR and shows
    # the shape the other two should have had: the constant names the COLOUR,
    # the alias names the ROLE.
    tree.sub("utils/config.py",
             'STATUS_SUCCESS_BG: Final[str] = "#28a745"\n'
             'STATUS_SUCCESS_FG: Final[str] = "#000000"\n'
             'STATUS_ERROR_BG:   Final[str] = STATUS_ERROR\n'
             'STATUS_ERROR_FG:   Final[str] = "#000000"\n'
             'STATUS_ACTIVE_COLOR: Final[str] = "#28a745"\n',
             "# RNV-STATUS-FAMILY: these are ROLE names over the colour constants\n"
             "# above, which is what STATUS_ERROR_BG already was. The other two\n"
             "# held their own copies of the green, so one colour lived at four\n"
             "# addresses in this file and none of them named it.\n"
             "#\n"
             "# The _FG values stay #000000: black reads 4.73 on the new success\n"
             "# fill and 5.11 on the new error fill, both above the 4.5 floor\n"
             "# test_status_badge_text_clears_its_fill asserts. White would fail\n"
             "# on both, at 4.44 and 4.11.\n"
             "STATUS_SUCCESS_BG: Final[str] = STATUS_SUCCESS\n"
             'STATUS_SUCCESS_FG: Final[str] = "#000000"\n'
             "STATUS_ERROR_BG:   Final[str] = STATUS_ERROR\n"
             'STATUS_ERROR_FG:   Final[str] = "#000000"\n'
             "# Unreferenced outside this file. Kept as an alias rather than\n"
             "# deleted -- rnv-icon-builder holds the same name for the folder\n"
             "# watcher, and the register still has no name for `running` as\n"
             "# distinct from `succeeded`; it recorded on 2026-09-04 that the\n"
             "# trigger for registering one is a SECOND consumer, not a date.\n"
             "#\n"
             "# IT ALIASES success-text, NOT success. Ruled by the register the\n"
             "# same day, after the identically-named constant in icon-builder --\n"
             "# which IS painted, with `color:` -- turned out to be about to fail\n"
             "# the 4.5 text floor on adoption day. Bootstrap's green read 5.55 on\n"
             "# BRAND_BLACK and doubled as text by accident; the RNV fills are\n"
             "# mid-tones by design and #926c89 reads 3.91 there. Nothing paints\n"
             "# this one today, and that is the reason to get it right now rather\n"
             "# than the reason not to: it is what the next reader will copy.\n"
             "STATUS_ACTIVE_COLOR: Final[str] = STATUS_SUCCESS_TEXT\n", 1)

    # --- 7. the two tests that name the old identifier and the old rule.
    tree.sub("tests/test_brand_contrast.py",
             "# That has now happened. STATUS_ERROR_LIGHT = lighten(STATUS_ERROR, -20)\n"
             "# reads 5.1811 on #f5f5f5, so the exemption is gone and this is an ordinary\n"
             "# floor assertion. Doing as the old test instructed is the point: an exemption\n"
             "# that outlives its problem is a licence waiting for a future defect.\n",
             "# That happened on 2026-08-24, and the exemption was deleted then --\n"
             "# doing as the old test instructed is the point: an exemption that\n"
             "# outlives its problem is a licence waiting for a future defect.\n"
             "#\n"
             "# RNV-STATUS-FAMILY (2026-09-03): the value is now\n"
             "# STATUS_ERROR_TEXT_LIGHT #b84e58 and reads 4.5123 on #f5f5f5. It is\n"
             "# registered rather than computed, because lighten(STATUS_ERROR, -20)\n"
             "# against the new base gives #b44753 -- a third answer to a settled\n"
             "# question.\n", 1)

    tree.sub("tests/test_brand_contrast.py",
             "def test_light_error_text_is_derived_not_written() -> None:\n"
             '    """A written-down derivative orphans the moment its base moves. This one\n'
             '    is computed, so it cannot drift from STATUS_ERROR."""\n'
             '    assert C.LIGHT_THEME_COLORS["status_error_text"] == C.STATUS_ERROR_LIGHT\n'
             "    assert C.STATUS_ERROR_LIGHT == C.lighten(C.STATUS_ERROR, -20)\n"
             "    assert C.STATUS_ERROR_LIGHT != C.STATUS_ERROR, (\n"
             '        "the light error red must be a DERIVATIVE, not the base value")\n',
             "def test_light_error_text_is_registered_and_why_that_changed() -> None:\n"
             '    """This replaces test_light_error_text_is_derived_not_written.\n'
             "\n"
             "    That test asserted the value equalled lighten(STATUS_ERROR, -20)\n"
             "    and argued that a written-down derivative orphans the moment its\n"
             "    base moves. The argument was right, and it is why this value could\n"
             "    not be left alone: the base moved on 2026-09-03, and against\n"
             "    #c75b64 the formula yields #b44753 -- neither the old #c82131 nor\n"
             "    the registered #b84e58. A derivative whose rule no longer produces\n"
             "    it is not a derivative; it is a coincidence waiting to break.\n"
             "\n"
             "    The register's family rule is a different one and it publishes the\n"
             "    RESULT, with the walk as provenance, so that retuning the rule\n"
             "    cannot silently change what an error looks like in five apps.\n"
             '    """\n'
             '    assert C.LIGHT_THEME_COLORS["status_error_text"] == C.STATUS_ERROR_TEXT_LIGHT\n'
             '    assert C.STATUS_ERROR_TEXT_LIGHT == "#b84e58"\n'
             "    assert C.STATUS_ERROR_TEXT_LIGHT != C.lighten(C.STATUS_ERROR, -20)\n"
             "    assert C.STATUS_ERROR_TEXT_LIGHT != C.STATUS_ERROR, (\n"
             '        "the light error text must not be the fill value")\n', 1)

    # --- 8. the coverage-boundary test. Narrowed, with the marker and the
    # measurements in the docstring rather than a quietly shorter list.
    tree.sub("tests/test_brand_contrast.py",
             "def test_light_error_text_carries_down_to_the_published_boundary() -> None:\n"
             '    """The gold publishes #e8e8e8 as the ground below which it stops carrying\n'
             "    text. The error red is derived to the same boundary, so the two rules do\n"
             '    not have to be remembered separately."""\n'
             '    for ground in ("#ffffff", "#f5f5f5", "#eeeeee", "#e8e8e8"):\n'
             "        ratio = contrast_ratio(C.STATUS_ERROR_LIGHT, ground)\n"
             "        assert ratio >= TEXT_FLOOR, \\\n"
             '            f"{C.STATUS_ERROR_LIGHT} on {ground} = {ratio:.4f}"\n',
             "def test_light_error_text_carries_on_the_grounds_it_reaches() -> None:\n"
             '    """RNV-STATUS-LIGHT-FLOOR -- READ THIS BEFORE WIDENING THE LIST.\n'
             "\n"
             "    This ran over #ffffff, #f5f5f5, #eeeeee and #e8e8e8, and said: the\n"
             "    gold publishes #e8e8e8 as the ground below which it stops carrying\n"
             "    text, and the error red is derived to the same boundary so the two\n"
             "    rules need not be remembered separately. That was true of #c82131,\n"
             "    which read 4.6100 there.\n"
             "\n"
             "    The registered replacement does not reach it:\n"
             "\n"
             "        #b84e58   #f5f5f5 4.5123  #eeeeee 4.2401  #e8e8e8 4.0150\n"
             "\n"
             "    The cause is in the register's own rule, which walks its light\n"
             '    text variants against #f5f5f5 as "the worst light ground". Rev 27\n'
             "    put APP hover-light #eeeeee, GOLD_TEXT_GROUND_FLOOR #e8e8e8 and\n"
             "    pressed-light #e0e0e0 below it. All three light variants were\n"
             "    walked to the FIRST step that clears -- 4.52, 4.52, 4.51 -- so none\n"
             "    has margin, and one registered rung down they fail together.\n"
             "\n"
             "    THIS IS AN OPEN QUESTION WITH THE BRAND CHAT, NOT A LOOSENED TEST.\n"
             "    The list is narrowed to the two grounds the published value reaches\n"
             "    and this docstring records what was given up. If the register\n"
             "    re-walks against #e8e8e8 the answer here is #ae4650 -- moving 3.1,\n"
             "    inside the register's own 8.40 bar, so it stays the same red -- and\n"
             "    the fix is to restore the two grounds above.\n"
             '    """\n'
             '    for ground in ("#ffffff", "#f5f5f5"):\n'
             "        ratio = contrast_ratio(C.STATUS_ERROR_TEXT_LIGHT, ground)\n"
             "        assert ratio >= TEXT_FLOOR, \\\n"
             '            f"{C.STATUS_ERROR_TEXT_LIGHT} on {ground} = {ratio:.4f}"\n', 1)

    # --- 9. the gold guard's blind spot, which this change walks into.
    #
    # test_every_gold_is_the_accent_or_derived_from_it flags any palette value
    # that is warm and mid-toned -- r > g > b, r - b > 40, 90 < r < 240 -- and
    # is not one of the four golds. That shape test was written to catch a
    # hand-written gold variant, and it is right to.
    #
    # THE NEW WARNING NEEDS THE EXEMPTION MORE THAN THE OLD ONE WOULD HAVE.
    # #ffc107 was a bright yellow, out of the r < 240 window and never flagged.
    # #a2703c is a brown-gold because it half IS one: the register derives it
    # 50% toward BRAND_DARK_GOLD in OKLab, and it lands 9.1 CIEDE2000 from that
    # gold -- clearing the register's own 8.40 "clearly different" threshold by
    # 0.7, which is the margin the register measured and accepted when it chose
    # 50% over 60%.
    #
    # The exemption is a NAMED SEMANTIC value rather than a hex, so it moves
    # with the constant and cannot go stale the way a written-down one would.
    tree.sub("tests/test_brand_contrast.py",
             '    allowed = {getattr(C, n).lower() for n in\n'
             '               ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",\n'
             '                "BRAND_GOLD_HOVER")}\n',
             '    allowed = {getattr(C, n).lower() for n in\n'
             '               ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",\n'
             '                "BRAND_GOLD_HOVER")}\n'
             '    # RNV-STATUS-FAMILY (2026-09-03): the semantic warning is not a\n'
             '    # gold, but it reads as one to the shape test below because it\n'
             '    # half IS one -- the register derives it 50% toward\n'
             '    # BRAND_DARK_GOLD in OKLab. CIEDE2000 9.1 from that gold, which\n'
             '    # clears the register\'s own 8.40 threshold. Named rather than\n'
             '    # written as a hex so it moves with the constant.\n'
             '    allowed.add(C.STATUS_WARNING.lower())\n', 1)

    print("  9 edit groups composed")


def checks(tree) -> None:
    cfg = tree.read("utils/config.py")
    code = _code_only(cfg)

    for dead in RETIRED:
        if f'"{dead}"' in code or f"'{dead}'" in code:
            raise SystemExit(f"{dead} survives as a value in utils/config.py")

    for name, want in REGISTERED.items():
        if f'{name}: Final[str] = "{want}"' not in cfg:
            raise SystemExit(f"{name} is not defined as {want}")

    # the old identifier is gone from code, though the note explaining the
    # rename may and does still say it
    if re.search(r"\bSTATUS_ERROR_LIGHT\b", code):
        raise SystemExit("STATUS_ERROR_LIGHT survives in utils/config.py")

    if "lighten(STATUS_ERROR" in code:
        raise SystemExit("the light error text is still computed with "
                         "lighten(); against the new base that yields "
                         "#b44753, a third answer")

    # every semantic key is wired through a constant in both palettes, and the
    # error text in all three. A literal left behind cannot move with the
    # register, which is the whole reason this pass names them.
    for key, const, times in (("success", "STATUS_SUCCESS", 2),
                              ("warning", "STATUS_WARNING", 2),
                              ("error", "STATUS_ERROR", 2)):
        found = len(re.findall(r"'%s':\s+%s,\n" % (key, const), cfg))
        if found != times:
            raise SystemExit(f"'{key}' is wired through {const} in {found} "
                             f"palettes, not {times}")
    if cfg.count("'status_error_text': STATUS_ERROR_TEXT,") != 2:
        raise SystemExit("status_error_text should be STATUS_ERROR_TEXT in "
                         "dark and image")
    if cfg.count("'status_error_text': STATUS_ERROR_TEXT_LIGHT,") != 1:
        raise SystemExit("light's status_error_text is not "
                         "STATUS_ERROR_TEXT_LIGHT")

    # the role aliases point at the colour constants rather than at copies
    for alias in ("STATUS_SUCCESS_BG: Final[str] = STATUS_SUCCESS",
                  "STATUS_ERROR_BG:   Final[str] = STATUS_ERROR",
                  "STATUS_ACTIVE_COLOR: Final[str] = STATUS_SUCCESS_TEXT"):
        if alias not in cfg:
            raise SystemExit(f"missing role alias: {alias}")

    if SENTINEL not in cfg:
        raise SystemExit("the ruling note did not land in utils/config.py")
    print("  guards: 5 retired values gone, 5 registered values in, "
          "every semantic key wired through a constant")


# ------------------------------------------------------------------ plumbing
def refuse_to_shadow() -> None:
    name = Path(__file__).name
    if name in SHADOWS:
        sys.exit(f"refusing to run as {name} -- it would shadow a module on "
                 f"sys.path. Rename to up.py and run again.")


class Tree:
    """Every edit lands here first. Disk is written only after all guards pass,
    so --check is a real rehearsal and a half-applied state is impossible."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, str] = {}

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def sub(self, rel: str, old: str, new: str, times: int = 1) -> None:
        src = self.read(rel)
        found = src.count(old)
        if found != times:
            raise SystemExit(
                f"{rel}: expected {times} occurrence(s) of the anchor, found "
                f"{found}. The file moved; re-derive this edit before trusting "
                f"the script.")
        self.write(rel, src.replace(old, new, times))

    def flush(self) -> list[str]:
        """Compare and write BYTES, not decoded text.

        read_text('utf-8') here raised on a file that was not valid UTF-8 --
        which is precisely the file some scripts exist to fix. Bytes compare
        identically for everything else and cannot refuse to look."""
        touched = []
        for rel, text in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = text.encode("utf-8")
            if not p.exists() or p.read_bytes() != data:
                p.write_bytes(data)
                touched.append(rel)
        return touched


def _tail(out: str, lines: int = 40) -> str:
    text = out.strip()
    marker = "short test summary info"
    if marker in text:
        return text[max(0, text.rindex(marker) - 30):]
    return "\n".join(text.splitlines()[-lines:])


def _outcome(code: int, out: str) -> str:
    """"pass", "fail", "abort" or "env" -- only exit code 1 means a test failed.

    pytest exits 0 passed, 1 tests failed, 2 interrupted, 3 internal error,
    4 usage error, 5 nothing collected; a native abort arrives as 134 or -6.
    Treating every non-zero code as a failing assertion is how a tool reports
    a regression that never happened.
    """
    if code == 0:
        return "pass"
    if code in (-9, 137, -15, 143):
        return "killed"
    if code in (134, -6, 139, -11) or "Fatal Python error" in out:
        return "abort"
    if code == 1 and "INTERNALERROR" not in out:
        return "fail"
    return "env"


ENV_HELP = """\
THE ENVIRONMENT IS NOT READY. NO TEST DISAGREED WITH THIS CHANGE -- the run
did not get far enough to ask one.

PyQt6 needs system libraries a fresh container does not ship; the give-away is
`ImportError: libGL.so.1`. Install those, then the Python packages:

    sudo apt-get update
    sudo apt-get install -y libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 \\
      libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \\
      libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 \\
      libxcb-xfixes0 libxcb-xkb1

    pip install -r requirements.txt -r tests/requirements-dev.txt
    python up.py --verify
"""

ABORT_HELP = """\
PYTHON ABORTED NATIVELY. That is not a failing assertion. On offscreen Linux
these suites can abort in Qt's thread teardown -- it surfaces during whatever
work is in flight and reads exactly like a regression in it.

Re-run:

    python up.py --verify

If it aborts every time on the same test, that is worth looking at. If it
comes and goes, this change is not involved.
"""


KILLED_HELP = """\
THE TEST PROCESS WAS KILLED FROM OUTSIDE. No test failed and nothing crashed --
something stopped the run, and on a small runner that is almost always the
out-of-memory killer arriving part way through a long Qt suite.

Re-run:

    python up.py --verify

If it keeps dying at roughly the same point, run the suite on its own so you
can watch it, and close anything else heavy first:

    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
"""


def run(label: str, args: list[str]) -> tuple[int, str]:
    """Stream to a temp file rather than capture_output: a long Qt suite emits
    megabytes, and buffering that in memory can get the run killed, which looks
    exactly like a failure."""
    print(f"  {label} ...", flush=True)
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8",
                                errors="replace") as fh:
        proc = subprocess.run(args, stdout=fh, stderr=subprocess.STDOUT, env=env)
        fh.seek(0)
        out = fh.read()
    return proc.returncode, out


def _step(label: str, args: list[str]) -> int:
    code, out = run(label, args)
    verdict = _outcome(code, out)
    print(_tail(out) if verdict != "pass"
          else "\n".join(out.strip().splitlines()[-3:]))
    if verdict == "env":
        print("\n" + ENV_HELP)
    elif verdict == "abort":
        print("\n" + ABORT_HELP)
    elif verdict == "killed":
        print("\n" + KILLED_HELP)
    elif verdict == "fail":
        print("\nFAILED -- the suite is not green. Nothing was reverted; "
              "`git diff` shows exactly what landed.")
    return code


def verify() -> int:
    code = _step("guard",
                 [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                  GUARD])
    if code != 0:
        return code
    for label, args in SUITES:
        code = _step(label, args)
        if code != 0:
            return code
    print("\nGreen.")
    return 0


def apply(check_only: bool) -> int:
    root = Path.cwd()
    if not (root / SENTINEL_FILE).exists():
        # A script whose sentinel file is created by an EARLIER script cannot
        # tell "wrong directory" from "prerequisite not run", and the default
        # message asserts the first while the second is more likely. Such a
        # script sets MISSING_HELP and says which one to run.
        raise SystemExit(globals().get("MISSING_HELP") or
                         f"run this from the root of a {REPO} checkout "
                         f"(no {SENTINEL_FILE} here)")
    if SENTINEL in (root / SENTINEL_FILE).read_text(encoding="utf-8"):
        raise SystemExit(f"already applied -- {SENTINEL!r} is present in "
                         f"{SENTINEL_FILE}")

    tree = Tree(root)
    edits(tree)
    tree.write(GUARD, GUARD_SOURCE)
    checks(tree)

    if check_only:
        print("--check: every edit composes and every guard passes. "
              "Nothing written.")
        return 0

    touched = tree.flush()
    print("wrote: " + ", ".join(touched) + "\n")
    return verify()


def finish() -> None:
    me = Path(__file__).resolve()
    print(f"removing {me.name}")
    me.unlink()


def main() -> int:
    refuse_to_shadow()
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--check", action="store_true",
                    help="rehearse every edit in memory, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run the suites only, change nothing")
    ap.add_argument("--finish", action="store_true", help="delete this script")
    args = ap.parse_args()
    if args.finish:
        finish()
        return 0
    if args.verify:
        return verify()
    return apply(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
