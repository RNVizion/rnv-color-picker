#!/usr/bin/env python3
"""
RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP

Re-derive the six diff highlight colours against the floors they were never
measured against, and retire ten values with no consumer left.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

WHY

Two defects, neither of which any contrast check would have reported.

SEMANTIC_DIFF_REMOVED '#4d1a1a' was invisible to an achromat. Under
achromatopsia it collapses to #181818, on a panel that collapses to #191919 --
CIEDE2000 0.31. A deleted line carried no visible highlight at all. Its
contrast against the text read 12.97 and had been checked; the fill had never
been measured against the GROUND under a simulation. Pairs had been, which is
how it read as though everything had.

AND THE FIRST RE-DERIVATION GOT THE METRIC WRONG. It measured pair separation
in dE76 and read it against 8.40, which this fleet's register publishes in
CIEDE2000. On the binding pair the two read 10.43 and 8.08 -- the loose number
over the bar, the real one under it. Two values were approved on that
arithmetic and are not in this script.

WHAT THE RENDER CHANGED. Derived on the palette alone, the light triple was
measured against LIGHT['input_bg'] '#ffffff'. The compare panes take
LIGHT['bg'] '#f5f5f5', which the rendered widget shows and the palette does
not say. Against the real ground the light 'changed' cleared by 3%.

THE SIX

                    dark                    light
    added           #1a4d1a -> #426153      #d4edda -> #8eafa0
    removed         #4d1a1a -> #704a4a      #f8d7da -> #a17877
    changed         #4d4d1a -> #403f00      #fff3cd -> #d6cd8a

Hues are Chris's own, from the mixer, held to within 0.6 degrees. Dark clears
its three floors by 12%, 17% and 16%; light by 22%, 20% and 20%.

DARK OWES TWO PAIRS AND LIGHT OWES THREE, and that is the only reason the
dark triple exists at all. ui/compare_dialog.py paints DELETE on the left pane
and INSERT on the right, so added and removed can never share a widget. With
a #dddddd ink ceiling at grey 97 and an achromatopsia floor at grey 52, the
window is 45 steps and a three-level ladder needs 50. core/diff_engine.py is
the exception that costs light the third pair: it builds the HTML export from
DialogStyleManager.LIGHT in BOTH themes and puts delete and insert in the two
columns of one row.

THE TEN THAT GO

SEMANTIC_REGEX_GROUPS (eight values), SEMANTIC_DIFF_CURRENT and
SEMANTIC_DIFF_CURRENT_LIGHT, with every name that carried one:
DialogStyleManager.REGEX_GROUP_COLORS, RegexBuilderDialog._GROUP_COLORS,
'diff_current_bg' in both palettes, CompareDialog._CURRENT_COLOR_DARK and
_CURRENT_COLOR_LIGHT, their PROVENANCE and __all__ entries, and
test_regex_group_palette_is_named.

Each chain was proved twice: statically it terminates, and with four capture
groups on screen the Regex Builder painted regex_match_bg and nothing else.

THE GUARD

tests/test_diff_floors.py holds three floors per mode -- text >= 4.5 WCAG,
fill-against-ground >= 8.40 CIEDE2000, co-visible pair >= 8.40 -- each under
normal vision and the four simulations rnv-color-picker grades with. It reads
the ground and the ink from the palette KEY the widget uses, and it DERIVES
which pairs are owed by following ui/compare_dialog.py's own match statement:

    role  <-  palette key  <-  ClassVar  <-  local name  <-  the widget

so a re-wiring is followed rather than silently outvoted by a hard-coded list.
Before any of it counts, test_the_instrument_is_ciede2000 reproduces the
register's published 8.4035 for BRAND_GOLD -> #b49e75, and
test_the_instrument_can_fail proves the ground rule still catches '#4d1a1a'.

Ten tampers were run against it and all ten land red in the named test.
"""
from __future__ import annotations

import argparse
import ast
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-text-transformer"
SENTINEL_FILE = "tests/conftest.py"
SENTINEL = "RNV-DIFF-FLOORS"
GUARD = "tests/test_diff_floors.py"
DESCRIPTION = "re-derive the six diff colours against their real floors"
SUITES = [("\"pytest tests/\"",
           [sys.executable, "-m", "pytest", "tests/", "-q", "-p",
            "no:cacheprovider"]),
          ("\"the LOCKED file\"",
           [sys.executable, "-m", "pytest", "test_rnv_text_transformer.py",
            "-q", "-p", "no:cacheprovider", "--timeout=120"])]

SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

#: What must be true of the tree this script is about to write. Checked here
#: against the IN-MEMORY tree, before anything reaches disk, so a bad set of
#: edits is refused rather than applied and then reported.
WANT_DARK = {"diff_added_bg": "#426153", "diff_removed_bg": "#704a4a",
             "diff_changed_bg": "#403f00"}
WANT_LIGHT = {"diff_added_bg": "#8eafa0", "diff_removed_bg": "#a17877",
              "diff_changed_bg": "#d6cd8a"}
RETIRED = ("SEMANTIC_DIFF_CURRENT", "SEMANTIC_DIFF_CURRENT_LIGHT",
           "SEMANTIC_REGEX_GROUPS", "REGEX_GROUP_COLORS", "_GROUP_COLORS",
           "_CURRENT_COLOR_DARK", "_CURRENT_COLOR_LIGHT", "diff_current_bg")

GUARD_SOURCE = r'''"""RNV-DIFF-FLOORS -- a highlight nobody can see is not a highlight.

Installed 2026-09-13, after two of the six diff values were found to fail in
ways no contrast check would ever have reported.

WHAT WENT WRONG, TWICE, AND WHY THIS FILE MEASURES THE WAY IT DOES

  1. SEMANTIC_DIFF_REMOVED was '#4d1a1a'. Under achromatopsia it collapses to
     #181818, on a panel that collapses to #191919 -- CIEDE2000 **0.31**. A
     deleted line carried no visible highlight at all. Contrast against the
     TEXT was 12.97 and had been checked; the fill had never been measured
     against the GROUND under a simulation, because the pairs were and it
     read as though everything had been.

  2. The first re-derivation measured pair separation in dE76 and read it
     against 8.40, which this fleet's register publishes in CIEDE2000. On the
     binding pair the two metrics read 10.43 and 8.08. The looser number was
     over the bar and the real one was under it.

So this guard measures three floors, each under five kinds of vision, and it
validates its own instrument before it trusts a single figure.

  text     WCAG 2.1, fill against the ink actually drawn on it      >= 4.5
  ground   CIEDE2000, fill against the pane it sits on              >= 8.40
  pair     CIEDE2000, between two roles that can share a widget     >= 8.40

THE GROUND IS READ FROM THE PALETTE THE WIDGET USES, NOT THE ONE THAT SOUNDS
RIGHT. LIGHT['input_bg'] is #ffffff and LIGHT['bg'] is #f5f5f5; the compare
panes take the latter, which a rendered frame shows and the palette does not.
Derived against white, SEMANTIC_DIFF_CHANGED_LIGHT cleared the real ground by
3% -- inside the bar, and the wrong bar.

WHICH PAIRS ARE OWED IS DERIVED, NOT LISTED. A hard-coded pair list is a
statement about ui/compare_dialog.py that stops being true the moment someone
re-wires which pane paints what, and stays green while it stops being true.
So this file reads that function's own `match` statement and follows every
chain to its end:

    role  <-  palette key  <-  ClassVar  <-  local name  <-  the widget

Two roles that reach the same widget owe each other the pair floor. Today
that makes DELETE+REPLACE on the left pane and INSERT+REPLACE on the right,
so added and removed owe each other nothing in the dialog -- they cannot be
on screen together.

core/diff_engine.py is the exception, and it is why LIGHT owes all three. It
builds one HTML document from DialogStyleManager.LIGHT in BOTH themes, and
puts .diff-delete and .diff-insert in the two columns of a single row.

8.40 IS THE REGISTER'S OWN BAR, not a number chosen here: BRAND_GOLD to
#b49e75 is its published walk into "perceptible at a glance" at 8.4035, and
test_the_instrument_is_ciede2000 reproduces exactly that figure before any
other test in this file is allowed to mean anything.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path

from utils.dialog_styles import DialogStyleManager

ROOT = Path(__file__).resolve().parent.parent
DIALOG = ROOT / "ui" / "compare_dialog.py"
EXPORT = ROOT / "core" / "diff_engine.py"

TEXT_FLOOR = 4.5
DE_FLOOR = 8.40

#: The pane's ground and the ink drawn on it, per mode, by palette KEY --
#: so a palette that re-points the key is followed rather than second-guessed.
GROUND_KEY, INK_KEY = "bg", "text"

#: rnv-color-picker's ColorAccessibility.COLORBLIND_MATRICES, verbatim, so
#: that a colour graded acceptable here is graded acceptable by the tool in
#: the next repository along. Achromatopsia is its 601 luma with int()
#: truncation, which is the same code path.
MATRICES = {
    "protanopia":   ((0.567, 0.433, 0.000), (0.558, 0.442, 0.000),
                     (0.000, 0.242, 0.758)),
    "deuteranopia": ((0.625, 0.375, 0.000), (0.700, 0.300, 0.000),
                     (0.000, 0.300, 0.700)),
    "tritanopia":   ((0.950, 0.050, 0.000), (0.000, 0.433, 0.567),
                     (0.000, 0.475, 0.525)),
}
VISION = ("normal", "protanopia", "deuteranopia", "tritanopia", "achromatopsia")


# ----------------------------------------------------------------- the instrument
def _rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def contrast(a: str, b: str) -> float:
    """WCAG 2.1, truncated to four places the way the register publishes."""
    def lum(c):
        def f(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, bl = c
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bl)
    la, lb = lum(_rgb(a)), lum(_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return math.floor((hi + 0.05) / (lo + 0.05) * 10000) / 10000


def simulate(hex_: str, kind: str) -> str:
    if kind == "normal":
        return hex_.lower()
    r, g, b = _rgb(hex_)
    if kind == "achromatopsia":
        y = int(0.299 * r + 0.587 * g + 0.114 * b)
        return _hex((y, y, y))
    m = MATRICES[kind]
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    return _hex(tuple(int(max(0.0, min(1.0, row[0] * rf + row[1] * gf
                                       + row[2] * bf)) * 255) for row in m))


def _lab(hex_: str) -> tuple[float, float, float]:
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in _rgb(hex_))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b)
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def g_(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    fx, fy, fz = g_(x), g_(y), g_(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ciede2000(one: str, two: str) -> float:
    """CIEDE2000. NOT dE76 -- the difference is what this round is about."""
    l1, a1, b1 = _lab(one)
    l2, a2, b2 = _lab(two)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    cb = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7))) if cb else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
    dlp, dcp = l2 - l1, c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    else:
        d = h2p - h1p
        dhp = d - 360 if d > 180 else (d + 360 if d < -180 else d)
    dhp2 = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)
    lbp, cbp = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbp = h1p + h2p
    else:
        s = h1p + h2p
        hbp = ((s + 360) / 2 if s < 360 else (s - 360) / 2) \
            if abs(h1p - h2p) > 180 else s / 2
    t = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    rc = 2 * math.sqrt(cbp ** 7 / (cbp ** 7 + 25 ** 7)) if cbp else 0.0
    sl = 1 + (0.015 * (lbp - 50) ** 2) / math.sqrt(20 + (lbp - 50) ** 2)
    sc, sh = 1 + 0.045 * cbp, 1 + 0.015 * cbp * t
    rt = -math.sin(math.radians(2 * dth)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dhp2 / sh) ** 2
                     + rt * (dcp / sc) * (dhp2 / sh))


def worst(one: str, two: str) -> tuple[float, str]:
    """The closest these two ever get, and the eye that gets them there."""
    return min(((ciede2000(simulate(one, v), simulate(two, v)), v)
                for v in VISION), key=lambda p: p[0])


# ------------------------------------------------------- what shares a widget
def _dialog_tree() -> ast.Module:
    return ast.parse(DIALOG.read_text(encoding="utf-8"), str(DIALOG))


def _classvar_keys() -> dict[str, tuple[str, str]]:
    """_ADDED_COLOR_DARK -> ('DARK', 'diff_added_bg'), read off the class."""
    out = {}
    for node in ast.walk(_dialog_tree()):
        if not isinstance(node, ast.AnnAssign) or not node.value:
            continue
        if not isinstance(node.target, ast.Name):
            continue
        v = node.value
        if (isinstance(v, ast.Subscript)
                and isinstance(v.value, ast.Attribute)
                and getattr(v.value.value, "id", "") == "DialogStyleManager"
                and isinstance(v.slice, ast.Constant)):
            out[node.target.id] = (v.value.attr, v.slice.value)
    return out


def _highlight_fn() -> ast.FunctionDef:
    for node in ast.walk(_dialog_tree()):
        if (isinstance(node, ast.FunctionDef)
                and node.name == "_highlight_differences"):
            return node
    raise AssertionError(
        "ui/compare_dialog.py has no _highlight_differences. This guard "
        "derives which roles can share a widget from that function; if it "
        "was renamed, point this at the new one rather than hard-coding a "
        "pair list, which is what it exists to avoid.")


def _locals_to_classvars(fn: ast.FunctionDef) -> dict[str, dict[str, str]]:
    """{'DARK': {'added_color': '_ADDED_COLOR_DARK', ...}, 'LIGHT': {...}}

    The function picks its three QColors inside `if is_dark: ... else: ...`,
    so the branch says which palette the names belong to.
    """
    def harvest(stmts):
        found = {}
        for stmt in stmts:
            for node in ast.walk(stmt):
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                call = node.value
                if not isinstance(target, ast.Name):
                    continue
                if (isinstance(call, ast.Call)
                        and getattr(call.func, "id", "") == "QColor"
                        and call.args
                        and isinstance(call.args[0], ast.Attribute)):
                    found[target.id] = call.args[0].attr
        return found

    for node in fn.body:
        if isinstance(node, ast.If):
            dark, light = harvest(node.body), harvest(node.orelse)
            if dark and light:
                return {"DARK": dark, "LIGHT": light}
    raise AssertionError(
        "could not find the dark/light branch in _highlight_differences")


def _widget_colours(fn: ast.FunctionDef) -> dict[str, set[str]]:
    """{'input_edit': {'removed_color', 'changed_color'}, ...}

    Every _highlight_range call, keyed by the widget it paints. Two colours
    under one key can be on screen at the same moment.
    """
    out: dict[str, set[str]] = {}
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "_highlight_range"):
            continue
        args = node.args
        if len(args) < 4:
            continue
        widget, colour = args[0], args[-1]
        if isinstance(widget, ast.Attribute) and isinstance(colour, ast.Name):
            out.setdefault(widget.attr, set()).add(colour.id)
    return out


def covisible_keys(mode: str) -> set[frozenset]:
    """Palette-key pairs that can be on screen together, in this mode."""
    fn = _highlight_fn()
    names = _locals_to_classvars(fn)[mode]
    keys = _classvar_keys()
    pairs = set()
    for colours in _widget_colours(fn).values():
        resolved = {keys[names[c]][1] for c in colours
                    if c in names and names[c] in keys}
        for one in resolved:
            for two in resolved:
                if one != two:
                    pairs.add(frozenset((one, two)))
    return pairs


def export_keys() -> set[frozenset]:
    """The HTML export puts delete and insert in one row, always light."""
    src = EXPORT.read_text(encoding="utf-8")
    if ".diff-insert" not in src or ".diff-delete" not in src:
        return set()
    if "DialogStyleManager.LIGHT" not in src:
        return set()
    return {frozenset(("diff_html_insert_bg", "diff_html_delete_bg"))}


def palette(mode: str) -> dict:
    return DialogStyleManager.DARK if mode == "DARK" else DialogStyleManager.LIGHT


DIFF_KEYS = ("diff_added_bg", "diff_removed_bg", "diff_changed_bg")


# ------------------------------------------------------------------- the tests
def test_the_instrument_is_ciede2000():
    """Before any figure here means anything, the metric has to be the one
    the bar is published in.

    BRAND_GOLD #d2bc93 walked -30 to #b49e75 is the register's own step into
    "perceptible at a glance", published at 8.4035. dE76 for the same pair is
    11.0877 -- which is exactly the substitution that let a pair reading 8.08
    be reported as 10.43 and shipped.
    """
    got = ciede2000("#d2bc93", "#b49e75")
    assert abs(got - 8.4035) < 0.0005, (
        f"CIEDE2000(#d2bc93, #b49e75) = {got:.4f}, and the register publishes "
        f"8.4035. Either the arithmetic changed or this is no longer "
        f"CIEDE2000 -- dE76 for this pair is 11.0877.")

    l1, l2 = _lab("#d2bc93"), _lab("#b49e75")
    de76 = math.sqrt(sum((x - y) ** 2 for x, y in zip(l1, l2)))
    assert abs(de76 - got) > 2.0, (
        "CIEDE2000 and dE76 are returning the same number for a pair where "
        "they differ by 2.68. One of them is not what it claims to be.")


def test_the_instrument_can_fail():
    """A floor nothing can breach is decoration.

    '#4d1a1a' is the value this round retired, and the reason: under
    achromatopsia it is #181818 against a #191919 panel. If the ground rule
    below cannot see that, it cannot see anything.
    """
    ground = palette("DARK")[GROUND_KEY]
    distance, eye = worst("#4d1a1a", ground)
    assert distance < DE_FLOOR, (
        f"the retired dark red reads {distance:.2f} from {ground} at its "
        f"worst ({eye}), which is over the floor -- so the ground rule is "
        f"not measuring what it was written to measure.")
    assert eye == "achromatopsia", (
        f"the retired dark red is closest to the panel under {eye}, not "
        f"achromatopsia. The simulation set has changed shape.")


def test_every_fill_clears_the_ink_drawn_on_it():
    """WCAG 4.5 against the ink, per mode."""
    bad = []
    for mode in ("DARK", "LIGHT"):
        pal = palette(mode)
        ink = pal[INK_KEY]
        for key in DIFF_KEYS:
            ratio = contrast(pal[key], ink)
            if ratio < TEXT_FLOOR:
                bad.append(f"{mode}[{key}] {pal[key]} on ink {ink}: "
                           f"{ratio:.4f} < {TEXT_FLOOR}")
    assert not bad, "text does not clear its fill:\n  " + "\n  ".join(bad)


def test_every_fill_is_visible_against_its_own_pane():
    """The rule the old dark red failed at 0.31.

    Measured under all five, because the failure was invisible under four of
    them: '#4d1a1a' reads 15.87 from the panel in normal vision.
    """
    bad = []
    for mode in ("DARK", "LIGHT"):
        pal = palette(mode)
        ground = pal[GROUND_KEY]
        for key in DIFF_KEYS:
            distance, eye = worst(pal[key], ground)
            if distance < DE_FLOOR:
                bad.append(f"{mode}[{key}] {pal[key]} against {ground}: "
                           f"{distance:.2f} < {DE_FLOOR} under {eye}")
    assert not bad, (
        "these highlights disappear into the pane behind them:\n  "
        + "\n  ".join(bad)
        + "\n\nA fill that matches its ground is not a highlight, whatever "
          "its contrast against the text reads.")


def test_roles_that_share_a_widget_stay_apart():
    """The pair floor, on the pairs ui/compare_dialog.py actually creates."""
    bad = []
    for mode in ("DARK", "LIGHT"):
        pal = palette(mode)
        pairs = covisible_keys(mode)
        if mode == "LIGHT":
            pairs = pairs | export_keys()
        for pair in sorted(pairs, key=sorted):
            one, two = sorted(pair)
            distance, eye = worst(pal[one], pal[two])
            if distance < DE_FLOOR:
                bad.append(f"{mode} {one} {pal[one]} vs {two} {pal[two]}: "
                           f"{distance:.2f} < {DE_FLOOR} under {eye}")
    assert not bad, (
        "these two can be on screen together and are not far enough "
        "apart:\n  " + "\n  ".join(bad))


def test_the_pairs_were_derived_and_not_assumed():
    """A sweep that finds nothing passes every rule above.

    This is the check the image-budget round shipped without: a glob that
    matched no file in three of five repositories, and a green suite.
    """
    fn = _highlight_fn()
    widgets = _widget_colours(fn)
    assert len(widgets) >= 2, (
        f"_highlight_differences paints {len(widgets)} widget(s). It paints "
        f"two panes, so the walk is not reading the calls.")

    names = _locals_to_classvars(fn)
    for mode in ("DARK", "LIGHT"):
        assert len(names[mode]) == 3, (
            f"{mode} resolves {len(names[mode])} colours, not three. The "
            f"branch this reads has changed shape.")

    keys = _classvar_keys()
    assert all(v in keys for m in names.values() for v in m.values()), (
        "a local colour name resolves to a ClassVar this guard cannot find "
        "in the class body")

    for mode in ("DARK", "LIGHT"):
        pairs = covisible_keys(mode)
        assert pairs, f"{mode} yielded no co-visible pair at all"
        resolved = {k for pair in pairs for k in pair}
        assert resolved <= set(DIFF_KEYS), (
            f"{mode} co-visibility reached keys this guard does not measure: "
            f"{sorted(resolved - set(DIFF_KEYS))}")

    # The one asymmetry worth stating out loud, because it is the reason the
    # dark triple fits at all: DELETE paints one pane and INSERT the other.
    dark = covisible_keys("DARK")
    assert frozenset(("diff_added_bg", "diff_removed_bg")) not in dark, (
        "added and removed now share a widget. That is allowed, but the dark "
        "triple was derived on the basis that they do not -- with a "
        "#dddddd ink ceiling at grey 97 and an achromatopsia floor at grey "
        "52, a three-level ladder needs 50 steps and there are 45. Re-derive "
        "the dark three before landing this.")

    assert export_keys(), (
        "core/diff_engine.py no longer pairs .diff-insert with .diff-delete "
        "out of DialogStyleManager.LIGHT. If the export moved, the third "
        "light pair may no longer be owed -- check before relaxing it.")


# THE TEN RETIRED VALUES ARE NOT GUARDED HERE, DELIBERATELY.
#
# A draft of this file ended with a rule that spelled the four retired
# identifiers out in order to forbid them. It landed RED -- in
# tests/test_semantic_naming.py, whose own sweep for retired names found all
# four here and could not tell forbidding a name from using one. That guard
# already carries a marker convention for files that mention what they
# retire, and a fourth marker was available.
#
# This comment does not spell them either, for the same reason: prose is
# swept as readily as code, and the draft's first correction removed the rule
# and left the paragraph that explained it, which landed red all over again.
#
# Taking it would have been the wrong fix. tests/test_semantic_naming.py owns
# the retired-name rule for this repository, the eight names this round
# retires are now in its RETIRED tuple, and a second guard asserting the same
# thing is how a suite grows two checks that will one day disagree. The
# duplication was the defect; the marker would only have hidden it.
#
# So this file guards the floors, and that one guards the names.
'''


EDITS = [('tests/conftest.py', "# RNV-GOLD-HOVER, 2026-09-12 -- every hover on the main surface takes the\n# mode's gold: BRAND_GOLD in dark and image, BRAND_DARK_GOLD in light. The\n", "# RNV-DIFF-FLOORS, 2026-09-13 -- tests/test_diff_floors.py holds the six diff\n# highlight values to three floors per mode: the ink on the fill clears WCAG\n# 4.5, the fill clears CIEDE2000 8.40 from the pane behind it, and any two\n# roles that can share a widget clear 8.40 from each other -- each under\n# normal vision and the four simulations rnv-color-picker grades with. It\n# measures against the ground and the ink the widget actually draws, because\n# the light panes take LIGHT['bg'] and not LIGHT['input_bg'], and the palette\n# does not say so. Ten values with no consumer left went with it.\n# RNV-GOLD-HOVER, 2026-09-12 -- every hover on the main surface takes the\n# mode's gold: BRAND_GOLD in dark and image, BRAND_DARK_GOLD in light. The\n", 1), ('utils/colors.py', '# Diff highlighting borrows the Bootstrap alert palette; the regex colours\n# are this app alone.\n', '# The regex colours are this app alone. The diff colours were the Bootstrap\n# alert palette until RNV-DIFF-FLOORS; they are now derived, and they are\n# held to three floors per mode by tests/test_diff_floors.py:\n#\n#   text     WCAG 2.1 against the ink drawn on the fill        >= 4.5\n#   ground   CIEDE2000 from the pane the fill sits on          >= 8.40\n#   pair     CIEDE2000 between roles that share a widget       >= 8.40\n#\n# each under normal vision and the four simulations rnv-color-picker grades\n# with. 8.40 is this fleet\'s register\'s own "perceptible at a glance" --\n# BRAND_GOLD to #b49e75 reads 8.4035.\n#\n# WHAT WAS WRONG WITH THE OLD SIX. \'#4d1a1a\' collapsed to #181818 under\n# achromatopsia, on a panel that collapses to #191919: CIEDE2000 0.31, so a\n# deleted line carried no visible highlight at all. The added/changed pair\n# read 8.08 dark and 7.81 light, both under the bar. A first re-derivation\n# missed both, because it measured pairs in dE76 and read them against a bar\n# published in CIEDE2000, and never measured a fill against its ground under\n# any simulation at all.\n#\n# THE LIGHT GROUND IS #f5f5f5, NOT WHITE. LIGHT[\'input_bg\'] is #ffffff, but\n# the compare panes take LIGHT[\'bg\'] -- which is what the rendered widget\n# shows, and what the palette does not tell you. Derived against white,\n# SEMANTIC_DIFF_CHANGED_LIGHT cleared the real ground by 3%.\n#\n# DARK OWES TWO PAIRS AND LIGHT OWES THREE. ui/compare_dialog.py paints\n# DELETE on the left pane and INSERT on the right, so added and removed never\n# share a widget. core/diff_engine.py is the exception that costs light the\n# third pair: it reads LIGHT in both themes and puts delete and insert in the\n# two columns of one row.\n#\n# The hues are Chris\'s, from the mixer, held to within 0.6 degrees.\n', 1), ('utils/colors.py', "SEMANTIC_DIFF_ADDED: Final[str] = '#1a4d1a'\n\nSEMANTIC_DIFF_REMOVED: Final[str] = '#4d1a1a'\n\nSEMANTIC_DIFF_CHANGED: Final[str] = '#4d4d1a'\n\nSEMANTIC_DIFF_CURRENT: Final[str] = '#4d1a4d'\n#: Bootstrap alert-success background\nSEMANTIC_DIFF_ADDED_LIGHT: Final[str] = '#d4edda'\n#: Bootstrap alert-danger background\nSEMANTIC_DIFF_REMOVED_LIGHT: Final[str] = '#f8d7da'\n#: Bootstrap alert-warning background\nSEMANTIC_DIFF_CHANGED_LIGHT: Final[str] = '#fff3cd'\n\nSEMANTIC_DIFF_CURRENT_LIGHT: Final[str] = '#e2d4f0'\n\nSEMANTIC_REGEX_MATCH: Final[str] = '#4a4a00'\n\nSEMANTIC_REGEX_MATCH_LIGHT: Final[str] = '#ffff99'\n\n\n#: Dark-only capture-group highlighting; index 0 is group 1.\nSEMANTIC_REGEX_GROUPS: Final[tuple[str, ...]] = (\n    '#3d5c5c',\n    '#5c3d5c',\n    '#5c5c3d',\n    '#3d5c3d',\n    '#5c3d3d',\n    '#3d3d5c',\n    '#5c4d3d',\n    '#3d5c4d',\n)\n", "#: Inserted line, right pane. text 5.0420, ground 17.75, worst pair 9.75.\nSEMANTIC_DIFF_ADDED: Final[str] = '#426153'\n\n#: Deleted line, left pane. text 5.5869, ground 19.45.\nSEMANTIC_DIFF_REMOVED: Final[str] = '#704a4a'\n\n#: Replaced line, BOTH panes -- so it owes a pair to each of the other two,\n#: and it is the value the dark ceiling binds. text 8.0150, ground 9.82.\nSEMANTIC_DIFF_CHANGED: Final[str] = '#403f00'\n\n#: text 8.7897, ground 20.07, worst pair 10.07. Also the HTML export's insert.\nSEMANTIC_DIFF_ADDED_LIGHT: Final[str] = '#8eafa0'\n\n#: text 5.4683, ground 28.24. Also the HTML export's delete.\nSEMANTIC_DIFF_REMOVED_LIGHT: Final[str] = '#a17877'\n\n#: text 12.9587, ground 10.12.\nSEMANTIC_DIFF_CHANGED_LIGHT: Final[str] = '#d6cd8a'\n\nSEMANTIC_REGEX_MATCH: Final[str] = '#4a4a00'\n\nSEMANTIC_REGEX_MATCH_LIGHT: Final[str] = '#ffff99'\n", 1), ('utils/colors.py', "    'SEMANTIC_DIFF_ADDED': 'app-semantic',\n    'SEMANTIC_DIFF_REMOVED': 'app-semantic',\n    'SEMANTIC_DIFF_CHANGED': 'app-semantic',\n    'SEMANTIC_DIFF_CURRENT': 'app-semantic',\n    'SEMANTIC_DIFF_ADDED_LIGHT': 'app-semantic',\n    'SEMANTIC_DIFF_REMOVED_LIGHT': 'app-semantic',\n    'SEMANTIC_DIFF_CHANGED_LIGHT': 'app-semantic',\n    'SEMANTIC_DIFF_CURRENT_LIGHT': 'app-semantic',\n    'SEMANTIC_REGEX_MATCH': 'app-semantic',\n    'SEMANTIC_REGEX_MATCH_LIGHT': 'app-semantic',\n    'SEMANTIC_REGEX_GROUPS': 'app-semantic',\n", "    'SEMANTIC_DIFF_ADDED': 'app-semantic',\n    'SEMANTIC_DIFF_REMOVED': 'app-semantic',\n    'SEMANTIC_DIFF_CHANGED': 'app-semantic',\n    'SEMANTIC_DIFF_ADDED_LIGHT': 'app-semantic',\n    'SEMANTIC_DIFF_REMOVED_LIGHT': 'app-semantic',\n    'SEMANTIC_DIFF_CHANGED_LIGHT': 'app-semantic',\n    'SEMANTIC_REGEX_MATCH': 'app-semantic',\n    'SEMANTIC_REGEX_MATCH_LIGHT': 'app-semantic',\n", 1), ('utils/colors.py', "    'SEMANTIC_DIFF_ADDED',\n    'SEMANTIC_DIFF_REMOVED',\n    'SEMANTIC_DIFF_CHANGED',\n    'SEMANTIC_DIFF_CURRENT',\n    'SEMANTIC_DIFF_ADDED_LIGHT',\n    'SEMANTIC_DIFF_REMOVED_LIGHT',\n    'SEMANTIC_DIFF_CHANGED_LIGHT',\n    'SEMANTIC_DIFF_CURRENT_LIGHT',\n    'SEMANTIC_REGEX_MATCH',\n    'SEMANTIC_REGEX_MATCH_LIGHT',\n    'SEMANTIC_REGEX_GROUPS',\n]\n", "    'SEMANTIC_DIFF_ADDED',\n    'SEMANTIC_DIFF_REMOVED',\n    'SEMANTIC_DIFF_CHANGED',\n    'SEMANTIC_DIFF_ADDED_LIGHT',\n    'SEMANTIC_DIFF_REMOVED_LIGHT',\n    'SEMANTIC_DIFF_CHANGED_LIGHT',\n    'SEMANTIC_REGEX_MATCH',\n    'SEMANTIC_REGEX_MATCH_LIGHT',\n]\n", 1), ('utils/__init__.py', '    SEMANTIC_DIFF_ADDED,\n    SEMANTIC_DIFF_REMOVED,\n    SEMANTIC_DIFF_CHANGED,\n    SEMANTIC_DIFF_CURRENT,\n    SEMANTIC_DIFF_ADDED_LIGHT,\n    SEMANTIC_DIFF_REMOVED_LIGHT,\n    SEMANTIC_DIFF_CHANGED_LIGHT,\n    SEMANTIC_DIFF_CURRENT_LIGHT,\n    SEMANTIC_REGEX_MATCH,\n    SEMANTIC_REGEX_MATCH_LIGHT,\n    SEMANTIC_REGEX_GROUPS,\n', '    SEMANTIC_DIFF_ADDED,\n    SEMANTIC_DIFF_REMOVED,\n    SEMANTIC_DIFF_CHANGED,\n    SEMANTIC_DIFF_ADDED_LIGHT,\n    SEMANTIC_DIFF_REMOVED_LIGHT,\n    SEMANTIC_DIFF_CHANGED_LIGHT,\n    SEMANTIC_REGEX_MATCH,\n    SEMANTIC_REGEX_MATCH_LIGHT,\n', 1), ('utils/__init__.py', "    'SEMANTIC_DIFF_ADDED',\n    'SEMANTIC_DIFF_REMOVED',\n    'SEMANTIC_DIFF_CHANGED',\n    'SEMANTIC_DIFF_CURRENT',\n    'SEMANTIC_DIFF_ADDED_LIGHT',\n    'SEMANTIC_DIFF_REMOVED_LIGHT',\n    'SEMANTIC_DIFF_CHANGED_LIGHT',\n    'SEMANTIC_DIFF_CURRENT_LIGHT',\n    'SEMANTIC_REGEX_MATCH',\n    'SEMANTIC_REGEX_MATCH_LIGHT',\n    'SEMANTIC_REGEX_GROUPS',\n", "    'SEMANTIC_DIFF_ADDED',\n    'SEMANTIC_DIFF_REMOVED',\n    'SEMANTIC_DIFF_CHANGED',\n    'SEMANTIC_DIFF_ADDED_LIGHT',\n    'SEMANTIC_DIFF_REMOVED_LIGHT',\n    'SEMANTIC_DIFF_CHANGED_LIGHT',\n    'SEMANTIC_REGEX_MATCH',\n    'SEMANTIC_REGEX_MATCH_LIGHT',\n", 1), ('utils/dialog_styles.py', '    SEMANTIC_DIFF_ADDED,\n    SEMANTIC_DIFF_REMOVED,\n    SEMANTIC_DIFF_CHANGED,\n    SEMANTIC_DIFF_CURRENT,\n    SEMANTIC_DIFF_ADDED_LIGHT,\n    SEMANTIC_DIFF_REMOVED_LIGHT,\n    SEMANTIC_DIFF_CHANGED_LIGHT,\n    SEMANTIC_DIFF_CURRENT_LIGHT,\n    SEMANTIC_REGEX_MATCH,\n    SEMANTIC_REGEX_MATCH_LIGHT,\n    SEMANTIC_REGEX_GROUPS,\n', '    SEMANTIC_DIFF_ADDED,\n    SEMANTIC_DIFF_REMOVED,\n    SEMANTIC_DIFF_CHANGED,\n    SEMANTIC_DIFF_ADDED_LIGHT,\n    SEMANTIC_DIFF_REMOVED_LIGHT,\n    SEMANTIC_DIFF_CHANGED_LIGHT,\n    SEMANTIC_REGEX_MATCH,\n    SEMANTIC_REGEX_MATCH_LIGHT,\n', 1), ('utils/dialog_styles.py', "        'diff_changed_bg': SEMANTIC_DIFF_CHANGED,\n        'diff_current_bg': SEMANTIC_DIFF_CURRENT,\n", "        'diff_changed_bg': SEMANTIC_DIFF_CHANGED,\n", 1), ('utils/dialog_styles.py', "        'diff_changed_bg': SEMANTIC_DIFF_CHANGED_LIGHT,\n        'diff_current_bg': SEMANTIC_DIFF_CURRENT_LIGHT,\n", "        'diff_changed_bg': SEMANTIC_DIFF_CHANGED_LIGHT,\n", 1), ('utils/dialog_styles.py', '\n    # ==================== REGEX GROUP HIGHLIGHT PALETTE ====================\n    # Dark-only visualization palette for regex capture group highlighting.\n    # Each color corresponds to a different capture group (group 1 → index 0, etc.).\n    REGEX_GROUP_COLORS: ClassVar[list[str]] = list(SEMANTIC_REGEX_GROUPS)\n\n    # ==================== PUBLIC METHODS ====================\n', '\n    # ==================== PUBLIC METHODS ====================\n', 1), ('ui/compare_dialog.py', "    _CHANGED_COLOR_DARK: ClassVar[str] = DialogStyleManager.DARK['diff_changed_bg']\n    _CURRENT_COLOR_DARK: ClassVar[str] = DialogStyleManager.DARK['diff_current_bg']\n\n    _ADDED_COLOR_LIGHT:   ClassVar[str] = DialogStyleManager.LIGHT['diff_added_bg']\n    _REMOVED_COLOR_LIGHT: ClassVar[str] = DialogStyleManager.LIGHT['diff_removed_bg']\n    _CHANGED_COLOR_LIGHT: ClassVar[str] = DialogStyleManager.LIGHT['diff_changed_bg']\n    _CURRENT_COLOR_LIGHT: ClassVar[str] = DialogStyleManager.LIGHT['diff_current_bg']\n", "    _CHANGED_COLOR_DARK: ClassVar[str] = DialogStyleManager.DARK['diff_changed_bg']\n\n    _ADDED_COLOR_LIGHT:   ClassVar[str] = DialogStyleManager.LIGHT['diff_added_bg']\n    _REMOVED_COLOR_LIGHT: ClassVar[str] = DialogStyleManager.LIGHT['diff_removed_bg']\n    _CHANGED_COLOR_LIGHT: ClassVar[str] = DialogStyleManager.LIGHT['diff_changed_bg']\n", 1), ('ui/regex_builder_dialog.py', "    _MATCH_COLOR_LIGHT: ClassVar[str]       = DialogStyleManager.LIGHT['regex_match_bg']\n    _GROUP_COLORS:      ClassVar[list[str]] = DialogStyleManager.REGEX_GROUP_COLORS\n", "    _MATCH_COLOR_LIGHT: ClassVar[str]       = DialogStyleManager.LIGHT['regex_match_bg']\n", 1), ('tests/test_brand_mirror.py', 'def test_regex_group_palette_is_named():\n    assert tuple(DialogStyleManager.REGEX_GROUP_COLORS) == \\\n        tuple(colors.SEMANTIC_REGEX_GROUPS)\n\n\n', '', 1), ('tests/test_semantic_naming.py', "VALUES = {'SEMANTIC_DIFF_ADDED': '#1a4d1a', 'SEMANTIC_DIFF_REMOVED': '#4d1a1a', 'SEMANTIC_DIFF_CHANGED': '#4d4d1a', 'SEMANTIC_DIFF_CURRENT': '#4d1a4d', 'SEMANTIC_DIFF_ADDED_LIGHT': '#d4edda', 'SEMANTIC_DIFF_REMOVED_LIGHT': '#f8d7da', 'SEMANTIC_DIFF_CHANGED_LIGHT': '#fff3cd', 'SEMANTIC_DIFF_CURRENT_LIGHT': '#e2d4f0', 'SEMANTIC_REGEX_MATCH': '#4a4a00', 'SEMANTIC_REGEX_MATCH_LIGHT': '#ffff99'}\nGROUPS = ('#3d5c5c', '#5c3d5c', '#5c5c3d', '#3d5c3d', '#5c3d3d', '#3d3d5c', '#5c4d3d', '#3d5c4d')\n", "# RNV-DIFF-FLOORS (2026-09-13) moved the six diff values and retired ten\n# others. The six moved for a measured reason, not a taste -- the floors\n# are held by tests/test_diff_floors.py and the reason is in\n# utils/colors.py. This table is the pin, so it moves WITH them: a value\n# that changes without this file changing is still the defect this guard\n# was written for.\nVALUES = {'SEMANTIC_DIFF_ADDED': '#426153', 'SEMANTIC_DIFF_REMOVED': '#704a4a', 'SEMANTIC_DIFF_CHANGED': '#403f00', 'SEMANTIC_DIFF_ADDED_LIGHT': '#8eafa0', 'SEMANTIC_DIFF_REMOVED_LIGHT': '#a17877', 'SEMANTIC_DIFF_CHANGED_LIGHT': '#d6cd8a', 'SEMANTIC_REGEX_MATCH': '#4a4a00', 'SEMANTIC_REGEX_MATCH_LIGHT': '#ffff99'}\n", 1), ('tests/test_semantic_naming.py', '    assert tuple(colors.SEMANTIC_REGEX_GROUPS) == GROUPS\n', '', 1), ('tests/test_semantic_naming.py', "'REGEX_GROUP_PALETTE', '_DRAG_HIGHLIGHT_GOLD', 'GREY_60')\n", "'REGEX_GROUP_PALETTE', '_DRAG_HIGHLIGHT_GOLD', 'GREY_60',\n           # Retired by RNV-DIFF-FLOORS: ten values with no\n           # consumer left, and every name that carried one.\n           # The two CURRENT names reached a palette key and\n           # a pair of ClassVars and stopped; the eight\n           # groups reached REGEX_GROUP_COLORS, then\n           # _GROUP_COLORS, and were never painted -- with\n           # four capture groups on screen the Regex Builder\n           # drew regex_match_bg and nothing else.\n           #\n           # THIS TUPLE IS WHERE THAT RULE LIVES. The floors\n           # guard installed alongside them held the same\n           # names in a rule of its own and landed red here,\n           # on the sweep below, which cannot tell\n           # forbidding a name from using one. The fix was to\n           # delete the duplicate rather than mark the file:\n           # two guards over one fact are two guards that can\n           # disagree.\n           'SEMANTIC_DIFF_CURRENT', 'SEMANTIC_DIFF_CURRENT_LIGHT',\n           'SEMANTIC_REGEX_GROUPS', 'REGEX_GROUP_COLORS',\n           '_GROUP_COLORS', '_CURRENT_COLOR_DARK',\n           '_CURRENT_COLOR_LIGHT', 'diff_current_bg')\n", 1), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_added_bg": "#1a4d1a",\n    "diff_changed_bg": "#4d4d1a",\n    "diff_current_bg": "#4d1a4d",\n', '    "diff_added_bg": "#426153",\n    "diff_changed_bg": "#403f00",\n', 1), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_added_bg": "#d4edda",\n    "diff_changed_bg": "#fff3cd",\n    "diff_current_bg": "#e2d4f0",\n', '    "diff_added_bg": "#8eafa0",\n    "diff_changed_bg": "#d6cd8a",\n', 1), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_removed_bg": "#4d1a1a",\n', '    "diff_removed_bg": "#704a4a",\n', 1), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_removed_bg": "#f8d7da",\n', '    "diff_removed_bg": "#a17877",\n', 1), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_html_delete_bg": "#f8d7da",\n', '    "diff_html_delete_bg": "#a17877",\n', 2), ('tests/__snapshots__/test_snapshots.ambr', '    "diff_html_insert_bg": "#d4edda",\n', '    "diff_html_insert_bg": "#8eafa0",\n', 2), ('tests/__snapshots__/test_snapshots.ambr', '  .diff-insert { background-color: #d4edda; }\n  .diff-delete { background-color: #f8d7da; }\n  .diff-replace-left { background-color: #f8d7da; }\n  .diff-replace-right { background-color: #d4edda; }\n', '  .diff-insert { background-color: #8eafa0; }\n  .diff-delete { background-color: #a17877; }\n  .diff-replace-left { background-color: #a17877; }\n  .diff-replace-right { background-color: #8eafa0; }\n', 1)]


def edits(tree) -> None:
    for rel, old, new, times in EDITS:
        tree.sub(rel, old, new, times)
    by_file: dict = {}
    for rel, *_ in EDITS:
        by_file[rel] = by_file.get(rel, 0) + 1
    print("  " + ", ".join(f"{n} in {rel}" for rel, n in sorted(by_file.items())))


# --------------------------------------------------- the arithmetic, again
# Deliberately a second copy of what the guard holds. checks() runs against
# the in-memory tree, before utils/colors.py on disk carries the new values,
# so it cannot import the guard and ask it -- and a check that reads the old
# file would pass on the wrong numbers.
MATRICES = {
    "protanopia":   ((0.567, 0.433, 0.000), (0.558, 0.442, 0.000),
                     (0.000, 0.242, 0.758)),
    "deuteranopia": ((0.625, 0.375, 0.000), (0.700, 0.300, 0.000),
                     (0.000, 0.300, 0.700)),
    "tritanopia":   ((0.950, 0.050, 0.000), (0.000, 0.433, 0.567),
                     (0.000, 0.475, 0.525)),
}
VISION = ("normal", "protanopia", "deuteranopia", "tritanopia", "achromatopsia")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hx(t):
    return "#%02x%02x%02x" % t


def _contrast(a, b):
    def lum(c):
        def f(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
    la, lb = lum(_rgb(a)), lum(_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return math.floor((hi + 0.05) / (lo + 0.05) * 10000) / 10000


def _sim(h, kind):
    if kind == "normal":
        return h.lower()
    r, g, b = _rgb(h)
    if kind == "achromatopsia":
        y = int(0.299 * r + 0.587 * g + 0.114 * b)
        return _hx((y, y, y))
    m = MATRICES[kind]
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    return _hx(tuple(int(max(0.0, min(1.0, row[0] * rf + row[1] * gf
                                      + row[2] * bf)) * 255) for row in m))


def _lab(h):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in _rgb(h))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b)
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def g_(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    fx, fy, fz = g_(x), g_(y), g_(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _de2000(one, two):
    l1, a1, b1 = _lab(one)
    l2, a2, b2 = _lab(two)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    cb = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7))) if cb else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
    dlp, dcp = l2 - l1, c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    else:
        d = h2p - h1p
        dhp = d - 360 if d > 180 else (d + 360 if d < -180 else d)
    dhp2 = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)
    lbp, cbp = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbp = h1p + h2p
    else:
        s = h1p + h2p
        hbp = ((s + 360) / 2 if s < 360 else (s - 360) / 2) \
            if abs(h1p - h2p) > 180 else s / 2
    t = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    rc = 2 * math.sqrt(cbp ** 7 / (cbp ** 7 + 25 ** 7)) if cbp else 0.0
    sl = 1 + (0.015 * (lbp - 50) ** 2) / math.sqrt(20 + (lbp - 50) ** 2)
    sc, sh = 1 + 0.045 * cbp, 1 + 0.015 * cbp * t
    rt = -math.sin(math.radians(2 * dth)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dhp2 / sh) ** 2
                     + rt * (dcp / sc) * (dhp2 / sh))


def _worst(one, two):
    return min(_de2000(_sim(one, v), _sim(two, v)) for v in VISION)


def _constants(text):
    """NAME -> '#rrggbb' for every Final[str] hex in utils/colors.py."""
    out = {}
    for node in ast.walk(ast.parse(text)):
        if (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and re.fullmatch(r"#[0-9a-fA-F]{6}", node.value.value)):
            out[node.target.id] = node.value.value.lower()
    return out


def _palette(text, which, consts):
    """DialogStyleManager.DARK / .LIGHT as key -> hex, resolved through the
    constants, so the ground this checks against is the one the widget draws
    rather than the one that sounds right."""
    out = {}
    for node in ast.walk(ast.parse(text)):
        if (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                and node.target.id == which and isinstance(node.value, ast.Dict)):
            for k, v in zip(node.value.keys, node.value.values):
                if not isinstance(k, ast.Constant):
                    continue
                if isinstance(v, ast.Name) and v.id in consts:
                    out[k.value] = consts[v.id]
                elif (isinstance(v, ast.Constant) and isinstance(v.value, str)
                      and re.fullmatch(r"#[0-9a-fA-F]{6}", v.value)):
                    out[k.value] = v.value.lower()
    return out


def checks(tree) -> None:
    root = Path.cwd()
    colors_txt = tree.files["utils/colors.py"]
    styles_txt = tree.files["utils/dialog_styles.py"]
    consts = _constants(colors_txt)

    # 1. every retired name is gone from EVERY python file in the checkout.
    #    The first pass of this round cut one name out of one import list and
    #    left two more in another; the tree stopped importing at all. A sweep
    #    is cheaper than that discovery.
    #
    #    It honours the repository's own marker convention, because a sweep
    #    that cannot tell a use from a mention fails on the guard that forbids
    #    the names -- tests/test_semantic_naming.py holds every one of them in
    #    its RETIRED tuple, which is the whole point of that file. The first
    #    draft of THIS check did not, and would have refused the very tree it
    #    was written to write.
    MARKERS = ("RNV-SEMANTIC-GUARD", "RNV-NAMING-TOOL-DO-NOT-SWEEP",
               "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP")
    survivors = []
    for path in sorted(root.rglob("*.py")):
        if ".git" in path.parts or path.name.startswith("up"):
            continue
        rel = path.relative_to(root).as_posix()
        text = tree.files.get(rel)
        if text is None:
            text = path.read_text(encoding="utf-8", errors="replace")
        if any(m in text for m in MARKERS):
            continue
        for name in RETIRED:
            if re.search(r"\b" + re.escape(name) + r"\b", text):
                survivors.append(f"{rel}: {name}")
    if survivors:
        raise SystemExit("retired names survive the edits:\n  "
                         + "\n  ".join(survivors))

    # 2. the six landed, and the palettes point at them.
    for which, want in (("DARK", WANT_DARK), ("LIGHT", WANT_LIGHT)):
        pal = _palette(styles_txt, which, consts)
        for key, value in want.items():
            if pal.get(key) != value:
                raise SystemExit(
                    f"{which}[{key}] resolves to {pal.get(key)}, not {value}")

    # 3. the three floors, measured the way the guard measures them, against
    #    the tree this script is about to write rather than the one on disk.
    bad = []
    for which in ("DARK", "LIGHT"):
        pal = _palette(styles_txt, which, consts)
        ground, ink = pal["bg"], pal["text"]
        keys = ("diff_added_bg", "diff_removed_bg", "diff_changed_bg")
        for key in keys:
            ratio = _contrast(pal[key], ink)
            if ratio < 4.5:
                bad.append(f"{which}[{key}] on ink {ink}: {ratio:.4f} < 4.5")
            distance = _worst(pal[key], ground)
            if distance < 8.40:
                bad.append(f"{which}[{key}] against {ground}: "
                           f"{distance:.2f} < 8.40")
        # dark: changed shares a pane with each of the other two, and added
        # with removed never. light: all three, because of the HTML export.
        pairs = [("diff_removed_bg", "diff_changed_bg"),
                 ("diff_added_bg", "diff_changed_bg")]
        if which == "LIGHT":
            pairs.append(("diff_added_bg", "diff_removed_bg"))
        for one, two in pairs:
            distance = _worst(pal[one], pal[two])
            if distance < 8.40:
                bad.append(f"{which} {one} vs {two}: {distance:.2f} < 8.40")
    if bad:
        raise SystemExit("the floors do not hold:\n  " + "\n  ".join(bad))

    # 4. the guard's own instrument, before its figures are trusted.
    got = _de2000("#d2bc93", "#b49e75")
    if abs(got - 8.4035) >= 0.0005:
        raise SystemExit(f"CIEDE2000(#d2bc93, #b49e75) = {got:.4f}, and the "
                         f"register publishes 8.4035")

    # 5. the sentinel is in the file the already-applied check reads. Shipped
    #    broken once in this programme; never again without a check.
    if SENTINEL not in tree.files[SENTINEL_FILE]:
        raise SystemExit(f"'{SENTINEL}' is not in {SENTINEL_FILE}, so the "
                         f"already-applied check can never fire")

    print(f"  guards: 6 values placed, {len(RETIRED)} retired names gone from "
          f"every file, three floors hold in both modes, instrument reads "
          f"{got:.4f}")



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
        self.deleted: set[str] = set()

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        """Mark a file for removal. Nothing leaves disk until flush().

        Added for the round that retired the last CI deselect: with no
        deselects left, tests/test_ci_deselects.py swept an empty set and
        would have passed over nothing. Its own failure message said to
        delete it in the commit that removed the last one, so the harness
        needed to be able to.
        """
        if not (self.root / rel).exists() and rel not in self.files:
            raise SystemExit(f"cannot delete {rel}: it is not in this checkout")
        self.files.pop(rel, None)
        self.deleted.add(rel)

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
        for rel in sorted(self.deleted):
            p = self.root / rel
            if p.exists():
                p.unlink()
                touched.append(f"{rel} (deleted)")
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
    # A script that changes the ENVIRONMENT its suites run in does it here,
    # not in checks(): checks() runs against the in-memory tree before
    # anything is on disk. The register pin is the case that needed it -- it
    # writes a dependency line and then runs tests that import what the line
    # declares, and DECLARING IS NOT INSTALLING.
    #
    # In verify() rather than apply() so that `--verify` gets it too; that is
    # the entry point someone uses to re-check a repository, and it has to
    # prepare the same environment.
    hook = globals().get("post_write")
    if hook is not None:
        hook()
        print()

    # GUARD_CMD is OPTIONAL and exists for a repository with no pytest. Every
    # round until 2026-09-12 ran inside one of the five applications, where a
    # guard is a test file; rnv-brand has no tests directory, no pytest
    # dependency, and a deliberate ZERO-IMPORT policy in engine/brand.py --
    # its own idiom is a function that runs AT IMPORT and raises. Installing
    # pytest there to satisfy this harness would change the shape of someone
    # else's repository to suit a tool, which is backwards. GUARD still names
    # the file that holds the check; GUARD_CMD says how to run it.
    guard_cmd = globals().get("GUARD_CMD") or [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", GUARD]
    code = _step("guard", guard_cmd)
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
    # GUARD_SOURCE is OPTIONAL. Every round until 2026-09-12 installed a new
    # guard file, so the harness assumed one; the ramp-condense round adopts
    # three that already exist -- the mixer's SPLITS table and two RETIRED
    # tuples -- and adding a fourth rule for what they already watch is how a
    # suite grows checks that disagree. GUARD still names the file verify()
    # runs first; it just does not have to be a file this script wrote.
    source = globals().get("GUARD_SOURCE")
    if source is not None:
        tree.write(GUARD, source)
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
