#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Adopt the dark ladder ends and the light plate in rnv-color-picker, and wire
the four translucent register values the last pass could not see.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

WHAT MOVES: NOTHING. Not one rendered pixel.

Thirteen entries change how they are SPELLED. Every value stays what it was.

    dark   hover_bg, button_hover_bg, list_hover_bg       -> APP_PANEL_HOVER
    dark   image_viewer_bg                                -> APP_CANVAS
    image  window_bg, scroll_area_bg                      -> APP_WINDOW_OVERLAY
    image  image_viewer_bg                                -> APP_CANVAS_OVERLAY
    image  zoom_label_bg                                  -> APP_PANEL_OVERLAY
    light  hover_bg, button_hover_bg, tab_hover_bg,
           list_hover_bg                                  -> APP_HOVER_LIGHT
    light  image_viewer_bg                                -> IMAGE_CANVAS_LIGHT

checks() proves it rather than asserting it: it resolves every entry of every
palette from the ORIGINAL file and the EDITED one and refuses to write unless
all three palettes are equal entry for entry.

A DEFECT IN THE LAST PASS, FIXED HERE

The 2026-08-29 wiring pass claimed no registered value was left spelled as a
literal in a dark palette. It was true of six-digit spellings only. Qt writes a
translucent colour as #AARRGGBB, and the guard compared whole strings, so
#ED000000 never matched #000000. Four registered values sat in
IMAGE_MODE_COLORS -- which is a DARK dict here -- and the test reported clean.

That is the same shape as the three failures already recorded in this
programme: a check whose reach was narrower than the change's extent, passing
because it covered what it could rather than what mattered. The sweep in
tests/test_register_wiring.py now normalises both lengths, and the four values
become named overlay constants whose relationship to their bases is asserted.

A COINCIDENCE, NAMED

Light image_viewer_bg is #e8e8e8, which rnv-brand rev 24 registered as
GOLD_TEXT_GROUND_FLOOR. It is NOT that role. It is the empty canvas behind a
loaded image -- a QGraphicsView background brush with the user's own picture on
it, and nothing gold, red, or textual is ever drawn on it. It shares a hex with
the floor and shares nothing else, so it is named IMAGE_CANVAS_LIGHT, declared
app-owned, and recorded as a coincidence asserted in both directions: one that
stops coinciding fails, and so does one that turns out to be mirrored.

THIS PASS WIRES A LIGHT VALUE, WHICH THE LAST ONE PROMISED NOT TO

tests/test_register_wiring.py carries test_the_light_palettes_were_left_alone,
written so widening scope into light would have to be deliberate. This is that
deliberate act, and the test is rewritten here in the open. It would not have
fired on its own: it flagged names in its REGISTERED map, and that map never
contained APP_HOVER_LIGHT.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-color-picker"
DESCRIPTION = "adopt the ladder ends, the light plate, and the overlays"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "APP_HOVER_LIGHT,"
MIRROR = "tests/test_app_mirror.py"
WIRING = "tests/test_register_wiring.py"
GUARD = "tests/test_ladder_and_plate.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ('pytest tests/ (about 1 minute)',
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ('unittest suite',
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

#: palette -> {value: constant}. An ALLOWLIST, not a sweep: a value-keyed
#: substitution with no allowlist can install a name whose meaning is wrong for
#: the palette it lands in, which has happened once in this programme.
SUBSTITUTE = {
    "DARK_THEME_COLORS": {"#3a3a3a": "APP_PANEL_HOVER",
                          "#0a0a0a": "APP_CANVAS"},
    "IMAGE_MODE_COLORS": {"#ed000000": "APP_WINDOW_OVERLAY",
                          "#ed0a0a0a": "APP_CANVAS_OVERLAY",
                          "#ed1a1a1a": "APP_PANEL_OVERLAY"},
    "LIGHT_THEME_COLORS": {"#eeeeee": "APP_HOVER_LIGHT",
                           "#e8e8e8": "IMAGE_CANVAS_LIGHT"},
}
EXPECTED_SUBS = 13

ALL_DICTS = ("DARK_THEME_COLORS", "LIGHT_THEME_COLORS", "IMAGE_MODE_COLORS")

CONSTANTS = '\nAPP_CANVAS: Final[str] = "#0a0a0a"\n"""engine/brand.py APP["canvas"]. The n=-1 rung of the dark surface ladder.\n\nREGISTERED 2026-08-29 in rnv-brand rev 22, app-owned here until then.\n\n    BRAND_BLACK + n * 0x10,  n in -1..+2\n    #0a0a0a canvas   #1a1a1a panel   #2a2a2a card   #3a3a3a panel-hover\n\nNOT WEB_BLACK. The web ground is #0a0a0f -- same lightness, blue channel\nlifted. App neutrals are pure grey, R = G = B, without exception, and the web\ncarries a tint the apps do not. The two are one byte apart on purpose, and that\nbyte is why invert(#0a0a0a) = #f5f5f5 once looked like a light-ground rule and\nwas not: the register\'s canvas inverts to #f5f5f0.\n"""\n\nAPP_PANEL_HOVER: Final[str] = "#3a3a3a"\n"""engine/brand.py APP["panel-hover"]. The n=+2 rung, and the dark interaction\nplate.\n\nREGISTERED 2026-08-29, app-owned here until then. The register had called the\nladder "two-thirds specified" because APP_BORDER #333333 is not #3a3a3a and so\nlooked like a missing rung. It is not a rung at all: #333333 is grey(3) on the\nINK grid, which governs inks and EDGES, and a border is an edge. The ladder was\ncomplete when the question was first asked.\n"""\n\nAPP_HOVER_LIGHT: Final[str] = "#eeeeee"\n"""engine/brand.py APP["hover-light"]. grey(14). The light interaction plate.\n\nREGISTERED 2026-08-29 as #e8e8e8 and MOVED to #eeeeee on 2026-08-30 in rev 23,\nbefore any app had been wired to it. Nothing here changes value -- the four\nentries below already held #eeeeee.\n\n#e8e8e8 is the ground BRAND_DARK_GOLD_DEEP is calibrated against, and rev 24\nregistered it under its own name for exactly that reason. Putting the hover\nplate on it would have pinned every hover in the app to the one value the gold\ncannot afford to lose, clearing the 4.5 floor by 0.0334. A boundary is not a\nplate. This value is a grid step inside it and gold reads 4.7875 on it.\n"""\n\nIMAGE_CANVAS_LIGHT: Final[str] = "#e8e8e8"\n"""APP-OWNED. The image viewer\'s ground in light mode.\n\nA COINCIDENCE, NOT A MIRROR, and the distinction is the whole reason this\nconstant exists rather than the literal that was here before. rnv-brand rev 24\nregistered #e8e8e8 as GOLD_TEXT_GROUND_FLOOR -- the darkest light ground on\nwhich the gold family carries text, and the value BRAND_DARK_GOLD_DEEP is\nderived against.\n\nThis is not that role. It is the empty canvas behind a loaded image in\nRNV_Color_Picker.py: a QGraphicsView background brush with the user\'s own\nimage drawn on it. No gold, no error red, no text of any kind is ever drawn on\nit. It shares a hex with the floor and shares nothing else.\n\nSO IT MUST NOT FOLLOW. If the register ever moves GOLD_TEXT_GROUND_FLOOR, this\nvalue stays where it is, and tests/test_ladder_and_plate.py asserts the\ncoincidence in both directions so that neither the sharing nor the separation\ncan rot silently.\n"""\n\nIMAGE_OVERLAY_ALPHA: Final[str] = "ED"\n"""The alpha byte image mode composites its chrome at -- 0xED, about 93%.\n\nWHY THE OVERLAYS BELOW ARE WRITTEN OUT RATHER THAN COMPOSED. Qt wants the\neight-digit #AARRGGBB form, and building it from the six-digit constant would\nmake the palette entries resolve to an expression rather than a value, which\nthis app\'s own before/after comparison cannot check. The relationship is\nenforced by tests/test_ladder_and_plate.py instead: it asserts that each\noverlay\'s last six digits ARE the register value it claims, and that its alpha\nbyte is this one. If the register moves a base, those tests fail and these move\nwith it.\n\nTHEY WERE INVISIBLE BEFORE. The 2026-08-29 wiring pass claimed no registered\nvalue was left spelled as a literal in a dark palette. That was true of\nsix-digit spellings only: its sweep compared whole strings, so #ED000000 never\nmatched #000000 and four of these sat in IMAGE_MODE_COLORS while the test\nreported clean. The sweep now normalises both lengths.\n"""\n\nAPP_WINDOW_OVERLAY: Final[str] = "#ED000000"\n"""TRUE_BLACK, and APP["window"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_CANVAS_OVERLAY: Final[str] = "#ED0A0A0A"\n"""APP_CANVAS, and APP["canvas"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_PANEL_OVERLAY: Final[str] = "#ED1A1A1A"\n"""BRAND_BLACK, and APP["panel"], at IMAGE_OVERLAY_ALPHA."""\n'
PROVENANCE = '    "APP_CANVAS": "register",\n    "APP_PANEL_HOVER": "register",\n    "APP_HOVER_LIGHT": "register",\n    "APP_WINDOW_OVERLAY": "register-overlay",\n    "APP_CANVAS_OVERLAY": "register-overlay",\n    "APP_PANEL_OVERLAY": "register-overlay",\n    "IMAGE_CANVAS_LIGHT": "app-canvas",\n'
PINNED = "    'APP_CANVAS': '#0a0a0a',\n    'APP_PANEL_HOVER': '#3a3a3a',\n    'APP_HOVER_LIGHT': '#eeeeee',\n"
OLD_LIGHT_TEST = 'def test_the_light_palettes_were_left_alone():\n    """This pass is the DARK half, on the register\'s stated order. The light\n    ladder is unruled -- nine surfaces inside three grid steps, and which of\n    them are real distinctions is a judgement the register has not made. If a\n    later pass wires light, this test is the thing that has to be deleted on\n    purpose."""\n    named = []\n    for dict_name, node in _dicts(LIGHT_DICTS).items():\n        for key, value in zip(node.keys, node.values):\n            if isinstance(value, ast.Name) and value.id in REGISTERED:\n                named.append(f\'{dict_name}[{key.value!r}] -> {value.id}\')\n    assert not named, (\n        \'the light palettes now reference the register:\\n  \' + \'\\n  \'.join(named)\n        + \'\\n\\nThat is the light half, and it is not ruled yet.\')'
NEW_LIGHT_TEST = '#: The light half is ruled one value at a time. This is the allowlist, and it\n#: is what a later pass has to extend ON PURPOSE.\nLIGHT_RULED = (\'APP_HOVER_LIGHT\',)\n\n\ndef test_the_light_palettes_reference_only_what_the_register_has_ruled():\n    """This began life as "the light palettes were left alone", which was true\n    while the light half was entirely unruled. rnv-brand rev 23 ruled one value\n    of it -- APP["hover-light"] -- so the test becomes an allowlist rather than\n    a prohibition. The light LADDER is still unruled: nine surfaces inside three\n    grid steps, and which of them are real distinctions is a judgement the\n    register has not made.\n\n    THE EARLIER FORM COULD NOT HAVE CAUGHT THIS PASS. It flagged names found in\n    REGISTERED, and REGISTERED was a four-value snapshot that did not contain\n    the value being wired -- so light could have been wired underneath it and it\n    would have reported clean. REGISTERED is widened in the same commit."""\n    named = []\n    for dict_name, node in _dicts(LIGHT_DICTS).items():\n        for key, value in zip(node.keys, node.values):\n            if (isinstance(value, ast.Name) and value.id in REGISTERED\n                    and value.id not in LIGHT_RULED):\n                named.append(f\'{dict_name}[{key.value!r}] -> {value.id}\')\n    assert not named, (\n        \'the light palettes reference register values that are not ruled \'\n        \'yet:\\n  \' + \'\\n  \'.join(named)\n        + \'\\n\\nAdd the name to LIGHT_RULED in the same commit that wires it, \'\n          \'or do not wire it.\')\n\n\ndef test_the_ruled_light_value_is_actually_wired():\n    """The allowlist permits; this requires. An allowlist entry nothing uses is\n    a licence with no subject -- the same shape as a dead exemption."""\n    used = set()\n    for node in _dicts(LIGHT_DICTS).values():\n        for value in node.values:\n            if isinstance(value, ast.Name) and value.id in LIGHT_RULED:\n                used.add(value.id)\n    assert used == set(LIGHT_RULED), (\n        f\'LIGHT_RULED lists {sorted(LIGHT_RULED)} but the light palettes use \'\n        f\'{sorted(used)}\')'
OLD_SWEEP = "            if isinstance(value, ast.Constant) and isinstance(value.value, str):\n                if value.value.lower() in by_value:\n                    literals.append(\n                        f'{dict_name}[{key.value!r}] = {value.value} '\n                        f'(should read {by_value[value.value.lower()]})')"
NEW_SWEEP = '            if isinstance(value, ast.Constant) and isinstance(value.value, str):\n                # Qt spells a translucent colour #AARRGGBB. This sweep compared\n                # whole strings, so an eight-digit spelling of a registered\n                # value never matched a six-digit register entry --\n                # IMAGE_MODE_COLORS kept four of them (#ED000000 twice,\n                # #ED0A0A0A, #ED1A1A1A) while this test reported clean and the\n                # pass it guards claimed completeness. Both lengths normalise\n                # to the RGB half now.\n                spelled = value.value.lower()\n                rgb = \'#\' + spelled[3:] if len(spelled) == 9 else spelled\n                if rgb in by_value:\n                    literals.append(\n                        f\'{dict_name}[{key.value!r}] = {value.value} \'\n                        f\'(should read {by_value[rgb]}\'\n                        f\'{" as an overlay" if rgb != spelled else ""})\')'
OLD_REG = "REGISTERED = {'TRUE_BLACK': '#000000', 'BRAND_BLACK': '#1a1a1a', 'APP_CARD': '#2a2a2a', 'APP_BORDER': '#333333'}"
NEW_REG = "REGISTERED = {'TRUE_BLACK': '#000000', 'BRAND_BLACK': '#1a1a1a', 'APP_CARD': '#2a2a2a', 'APP_BORDER': '#333333',\n              'APP_CANVAS': '#0a0a0a', 'APP_PANEL_HOVER': '#3a3a3a',\n              'APP_HOVER_LIGHT': '#eeeeee'}"

#: Every line this pass adds, counted from the text that adds it. A
#: substitution that eats or adds a line ending leaves every value identical
#: and every test green while the file is quietly reflowed; only shape sees it.
#: CONSTANTS supplies its own leading newline and the anchor it replaces gave
#: one up, hence the -1.
EXPECTED_ADDED = {
    SENTINEL_FILE: CONSTANTS.count("\n") - 1 + PROVENANCE.count("\n"),
    MIRROR: PINNED.count("\n"),
    WIRING: (NEW_LIGHT_TEST.count("\n") - OLD_LIGHT_TEST.count("\n")
             + NEW_SWEEP.count("\n") - OLD_SWEEP.count("\n")
             + NEW_REG.count("\n") - OLD_REG.count("\n")),
}


def _resolve(source: str) -> dict:
    """Every palette, resolved to plain values, whether an entry is written as
    a literal or a name. This is what makes "nothing moved" checkable."""
    # Five files here begin with a UTF-8 BOM and Tree.read decodes as plain
    # utf-8, so it arrives as a leading U+FEFF that ast.parse refuses. Stripped
    # here rather than in the reader, because the BOM must survive into the
    # file that is written back.
    tree = ast.parse(source.lstrip("\ufeff"))
    consts = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                consts[target.id] = node.value.value
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            name = getattr(target, "id", None)
            if name in ALL_DICTS and isinstance(node.value, ast.Dict):
                palette = {}
                for key, value in zip(node.value.keys, node.value.values):
                    if not isinstance(key, ast.Constant):
                        continue
                    if isinstance(value, ast.Constant):
                        palette[key.value] = value.value
                    elif isinstance(value, ast.Name):
                        palette[key.value] = consts.get(value.id, f"<{value.id}>")
                    else:
                        palette[key.value] = ast.unparse(value)
                out[name] = palette
    return out


def _bounds(lines):
    """The palettes carry identically-spelled key lines, so a plain string
    replace cannot tell dark from light. Every edit is scoped to its own."""
    starts = {}
    pattern = re.compile(r"^(" + "|".join(ALL_DICTS) + r")\s*[:=]")
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            starts[m.group(1)] = i
    if len(starts) != len(ALL_DICTS):
        raise SystemExit(f"expected {len(ALL_DICTS)} palettes, found {sorted(starts)}")
    order = sorted(starts.items(), key=lambda kv: kv[1])
    return {n: (st, order[i + 1][1] if i + 1 < len(order) else len(lines))
            for i, (n, st) in enumerate(order)}


def edits(tree) -> None:
    tree.sub(SENTINEL_FILE,
             '\nAPP_PROVENANCE: Final[dict[str, str]] = {',
             CONSTANTS + 'APP_PROVENANCE: Final[dict[str, str]] = {')
    tree.sub(SENTINEL_FILE, '    "APP_TEXT_DIM": "register",\n',
             '    "APP_TEXT_DIM": "register",\n' + PROVENANCE)

    source = tree.read(SENTINEL_FILE)
    lines = source.splitlines(keepends=True)
    bounds = _bounds(lines)
    swapped = 0
    for dict_name, table in SUBSTITUTE.items():
        start, end = bounds[dict_name]
        for i in range(start, end):
            line = lines[i]
            # Match the line WITHOUT its ending and put the ending back
            # verbatim. Python's `$` also matches just before a trailing
            # newline, so a pattern ending in `(,.*)$` silently drops it -- and
            # the result is still valid Python, so every test passes while the
            # palette is reflowed onto one line.
            body = line.rstrip("\r\n")
            ending = line[len(body):]
            # Six OR eight digits. The eight-digit form is the one the last
            # pass could not see.
            m = re.match(r"^(\s*'[a-z_0-9]+':\s*)'(#[0-9a-fA-F]{6}|"
                         r"#[0-9a-fA-F]{8})'(,.*)$", body)
            if not m:
                continue
            const = table.get(m.group(2).lower())
            if const:
                lines[i] = f"{m.group(1)}{const}{m.group(3)}{ending}"
                swapped += 1
    if swapped != EXPECTED_SUBS:
        raise SystemExit(f"expected {EXPECTED_SUBS} substitutions, made "
                         f"{swapped}. The palettes have already been wired, or "
                         f"their shape changed -- re-derive this script.")
    tree.write(SENTINEL_FILE, "".join(lines))
    print(f"  substituted {swapped} literals for their names")

    tree.sub(MIRROR, "    'APP_TEXT_DIM': '#aaaaaa',\n",
             "    'APP_TEXT_DIM': '#aaaaaa',\n" + PINNED)

    tree.sub(WIRING, OLD_REG, NEW_REG)
    tree.sub(WIRING, OLD_SWEEP, NEW_SWEEP)
    tree.sub(WIRING, OLD_LIGHT_TEST, NEW_LIGHT_TEST)


def checks(tree) -> None:
    for rel, added in EXPECTED_ADDED.items():
        before = (Path.cwd() / rel).read_text(encoding="utf-8-sig")
        after = tree.read(rel)
        delta = after.count("\n") - before.count("\n")
        if delta != added:
            raise SystemExit(
                f"{rel} changed shape by {delta} lines; this pass adds exactly "
                f"{added}. A substitution that eats or adds a line ending "
                f"leaves every value identical and every test green.")

    original = (Path.cwd() / SENTINEL_FILE).read_text(encoding="utf-8-sig")
    edited = tree.read(SENTINEL_FILE)

    before, after = _resolve(original), _resolve(edited)
    if set(before) != set(after):
        raise SystemExit(f"a palette appeared or vanished: {set(before) ^ set(after)}")
    moved = []
    for name in before:
        for key in set(before[name]) | set(after[name]):
            was, now = before[name].get(key), after[name].get(key)
            if was != now:
                moved.append(f"{name}[{key!r}]: {was} -> {now}")
    if moved:
        raise SystemExit("THIS PASS MUST NOT MOVE A VALUE, and it moved these:\n  "
                         + "\n  ".join(moved))

    # Completeness, at BOTH spellings. The six-digit-only version of this check
    # is the defect this pass exists to fix, so it is not repeated here.
    wanted = {v for table in SUBSTITUTE.values() for v in table}
    lines = edited.splitlines()
    bounds = _bounds([l + "\n" for l in lines])
    survivors = []
    for name in ALL_DICTS:
        start, end = bounds[name]
        for i in range(start, end):
            m = re.match(r"^\s*'([a-z_0-9]+)':\s*'(#[0-9a-fA-F]{6}|"
                         r"#[0-9a-fA-F]{8})',", lines[i])
            if m and m.group(2).lower() in wanted:
                survivors.append(f"{name}[{m.group(1)!r}] = {m.group(2)}")
    if survivors:
        raise SystemExit("a value this pass names is still a literal:\n  "
                         + "\n  ".join(survivors))

    # The plate must not land on the floor. If #e8e8e8 ever reaches a hover key
    # here, the reason APP["hover-light"] moved has been undone.
    for name, palette in after.items():
        for key, value in palette.items():
            if ("hover" in key and isinstance(value, str)
                    and value.lower() == "#e8e8e8"):
                raise SystemExit(
                    f"{name}[{key!r}] is #e8e8e8 -- that is "
                    f"GOLD_TEXT_GROUND_FLOOR, not an interaction plate.")

    if SENTINEL not in edited:
        raise SystemExit(f"expected {SENTINEL!r} in the edited palette")


GUARD_SOURCE = '"""The dark ladder, the light plate, the translucent overlays, and one\ndeliberate coincidence.\n\nWHAT THIS PASS DID. rnv-brand rev 22 registered the two ends of the dark\nsurface ladder -- APP["canvas"] #0a0a0a and APP["panel-hover"] #3a3a3a -- rev\n23 registered APP["hover-light"] #eeeeee, and rev 24 registered #e8e8e8 as\nGOLD_TEXT_GROUND_FLOOR. All were app-owned here. No value changed: the pass\nchanges provenance and spelling, not pixels.\n\n    BRAND_BLACK + n * 0x10,  n in -1..+2\n    #0a0a0a canvas   #1a1a1a panel   #2a2a2a card   #3a3a3a panel-hover\n\nWHY THE LADDER WAS NOT "TWO-THIRDS SPECIFIED". The register said it was,\nbecause APP["border"] #333333 is not #3a3a3a and so looked like a missing rung.\nIt is not a rung -- #333333 is grey(3) on the INK grid, which governs inks and\nEDGES, and a border is an edge. Measured against the wrong family.\n\nWHY THE PLATE IS #eeeeee AND NOT #e8e8e8. #e8e8e8 is the ground\nBRAND_DARK_GOLD_DEEP is calibrated against -- the smallest uniform step that\nclears it is -14, and -13 gives 4.4675 and fails. The hover plate on that value\nwould have pinned every hover in the app to the one ground the gold cannot\nafford to lose, with 0.0334 of margin. A boundary is not a plate.\n\nWHY THE OVERLAYS ARE HERE AT ALL. Qt spells a translucent colour #AARRGGBB.\nThe 2026-08-29 wiring pass swept for six-digit literals, so #ED000000 never\nmatched #000000 and four registered values sat in IMAGE_MODE_COLORS while the\nguard reported clean. They are named now, and the sweep normalises both\nlengths.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\n\nimport pytest\n\nfrom utils import config as colors\nfrom utils.config import (DARK_THEME_COLORS as DARK,\n                          IMAGE_MODE_COLORS as IMAGE,\n                          LIGHT_THEME_COLORS as LIGHT)\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nSRC = ROOT / \'utils/config.py\'\n\nGRID_STEP = 0x11\nLADDER_STEP = 0x10\nTEXT_FLOOR = 4.5\n\n#: Constant name -> the APP key it mirrors, and the value both hold.\nNEW = {\n    \'APP_CANVAS\': (\'canvas\', \'#0a0a0a\'),\n    \'APP_PANEL_HOVER\': (\'panel-hover\', \'#3a3a3a\'),\n    \'APP_HOVER_LIGHT\': (\'hover-light\', \'#eeeeee\'),\n}\n\n#: Overlay constant -> (the six-digit constant it composites, its APP key).\nOVERLAYS = {\n    \'APP_WINDOW_OVERLAY\': (\'TRUE_BLACK\', \'window\'),\n    \'APP_CANVAS_OVERLAY\': (\'APP_CANVAS\', \'canvas\'),\n    \'APP_PANEL_OVERLAY\': (\'BRAND_BLACK\', \'panel\'),\n}\n\n#: palette dict name -> the keys in it that must now name a constant.\nWIRED = {\n    \'DARK_THEME_COLORS\': (\'hover_bg\', \'button_hover_bg\', \'list_hover_bg\',\n                          \'image_viewer_bg\'),\n    \'IMAGE_MODE_COLORS\': (\'window_bg\', \'scroll_area_bg\', \'image_viewer_bg\',\n                          \'zoom_label_bg\'),\n    \'LIGHT_THEME_COLORS\': (\'hover_bg\', \'button_hover_bg\', \'tab_hover_bg\',\n                           \'list_hover_bg\', \'image_viewer_bg\'),\n}\n\n#: dict NAME -> the live dict. Looking a key up in the wrong palette is how a\n#: per-mode difference gets checked against the other mode\'s value and passes.\nPALETTES = {\'DARK_THEME_COLORS\': DARK, \'IMAGE_MODE_COLORS\': IMAGE,\n            \'LIGHT_THEME_COLORS\': LIGHT}\n\n#: App-owned values that DELIBERATELY share a hex with a register entry.\n#: Sharing a VALUE is not playing the same ROLE, and a value check cannot tell\n#: the difference -- so the intentional ones are named, with what they share\n#: and why they must NOT follow if the register moves.\n#:\n#: name -> (register constant, why it is not the same role)\nCOINCIDENT = {\n    \'IMAGE_CANVAS_LIGHT\': (\n        \'GOLD_TEXT_GROUND_FLOOR\',\n        \'The register value is the darkest light ground on which the gold \'\n        \'family carries TEXT -- it is the constraint BRAND_DARK_GOLD_DEEP is \'\n        \'derived against. This is the empty canvas behind a loaded image: a \'\n        \'QGraphicsView background brush in RNV_Color_Picker.py with the \'\n        "user\'s own picture drawn on it. No gold, no error red, and no text "\n        \'of any kind is ever drawn on it. If the register moves the floor, \'\n        \'this must NOT follow -- which is why it is named here rather than \'\n        \'mirrored.\'),\n}\n\n\ndef grey(n: int) -> str:\n    v = n * GRID_STEP\n    return \'#%02x%02x%02x\' % (v, v, v)\n\n\ndef _luminance(value: str) -> float:\n    channels = [int(value.lstrip(\'#\')[i:i + 2], 16) / 255 for i in (0, 2, 4)]\n    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4\n                for c in channels]\n    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]\n\n\ndef _contrast(a: str, b: str) -> float:\n    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)\n    return (high + 0.05) / (low + 0.05)\n\n\ndef _dict_node(name: str) -> ast.Dict:\n    tree = ast.parse(SRC.read_text(encoding=\'utf-8-sig\'))\n    for node in ast.walk(tree):\n        if isinstance(node, (ast.Assign, ast.AnnAssign)):\n            target = node.targets[0] if isinstance(node, ast.Assign) else node.target\n            if getattr(target, \'id\', None) == name and isinstance(node.value, ast.Dict):\n                return node.value\n    raise AssertionError(f\'{name} is not a dict literal in utils/config.py\')\n\n\ndef _entry(node: ast.Dict, key: str):\n    for k, v in zip(node.keys, node.values):\n        if isinstance(k, ast.Constant) and k.value == key:\n            return v\n    return None\n\n\n# ------------------------------------------------------------- guard the guard\n\ndef test_everything_this_file_reads_still_exists():\n    """Renaming a key must fail loudly here rather than let the rest of this\n    file pass quietly over nothing."""\n    for name in list(NEW) + list(OVERLAYS) + list(COINCIDENT):\n        assert hasattr(colors, name), f\'utils.config has no {name}\'\n    for dict_name, keys in WIRED.items():\n        assert dict_name in PALETTES, f\'{dict_name} is not in PALETTES\'\n        for key in keys:\n            assert key in PALETTES[dict_name], f\'{dict_name} has no {key!r}\'\n\n\ndef test_the_wiring_map_is_not_empty():\n    """Every sweep below iterates WIRED. An empty map passes all of them."""\n    assert WIRED and all(WIRED.values())\n    assert sum(len(v) for v in WIRED.values()) >= 13\n\n\n# ------------------------------------------------------------------- the values\n\ndef test_the_new_constants_hold_the_registered_values():\n    """The local half of the mirror. Runs everywhere, including where\n    engine.brand is not importable -- which is why it is not optional."""\n    drift = {n: getattr(colors, n) for n, (_, v) in NEW.items()\n             if getattr(colors, n) != v}\n    assert not drift, (\n        f\'these constants no longer hold their registered values: {drift}\\n\'\n        f\'If the brand moved, update this file in the same commit that updates \'\n        f\'utils/config.py -- never one without the other.\')\n\n\ndef test_the_new_constants_match_rnv_brand():\n    """The upstream half. Skips where rnv-brand is not importable."""\n    brand = pytest.importorskip(\n        \'engine.brand\',\n        reason=\'rnv-brand not importable here; the local pin is doing the work\')\n    drift = []\n    for name, (key, _) in NEW.items():\n        theirs, mine = brand.APP[key], getattr(colors, name)\n        if mine.lower() != theirs.lower():\n            drift.append(f\'{name}: ours {mine}, theirs APP[{key!r}] {theirs}\')\n    assert not drift, \'drift from rnv-brand:\\n  \' + \'\\n  \'.join(drift)\n\n\ndef test_provenance_is_declared_for_everything_this_pass_named():\n    """A classification that lives only in a test drifts from the thing it\n    classifies, so it lives in the module and is read from there. This is also\n    the first thing to read APP_PROVENANCE, whose docstring has claimed since\n    the ink pass that a test reads it. Nothing did."""\n    for name in NEW:\n        assert colors.APP_PROVENANCE.get(name) == \'register\', name\n    for name in OVERLAYS:\n        assert colors.APP_PROVENANCE.get(name) == \'register-overlay\', name\n    for name in COINCIDENT:\n        group = colors.APP_PROVENANCE.get(name)\n        assert group and group.startswith(\'app-\'), (\n            f\'{name} is a coincidence, so it must be declared app-owned. \'\n            f\'Declaring it register-owned would exempt a mirrored value from \'\n            f\'the mirror.\')\n\n\n# ------------------------------------------------------------------ the ladder\n\ndef test_the_dark_rungs_are_exact_steps_on_the_ladder():\n    """BRAND_BLACK + n * 0x10. Two of these were app-owned on the argument that\n    the ladder might not be real. It is, and this is what says so."""\n    base = int(colors.BRAND_BLACK.lstrip(\'#\'), 16)\n    for n, name in ((-1, \'APP_CANVAS\'), (0, \'BRAND_BLACK\'), (1, \'APP_CARD\'),\n                    (2, \'APP_PANEL_HOVER\')):\n        want = base + n * (LADDER_STEP * 0x010101)\n        assert int(getattr(colors, name).lstrip(\'#\'), 16) == want, (\n            f\'{name} is {getattr(colors, name)}, not rung n={n}\')\n\n\ndef test_the_border_is_an_edge_and_not_a_rung():\n    """The distinction that made the ladder look incomplete."""\n    assert colors.APP_BORDER == grey(3)\n    base = int(colors.BRAND_BLACK.lstrip(\'#\'), 16)\n    rungs = {base + n * (LADDER_STEP * 0x010101) for n in range(-1, 3)}\n    assert int(colors.APP_BORDER.lstrip(\'#\'), 16) not in rungs\n\n\ndef test_the_canvas_is_not_the_web_ground():\n    """One byte apart, deliberately. App neutrals are pure grey R = G = B; the\n    web ground #0a0a0f carries a tint the apps do not. That byte is why\n    invert(#0a0a0a) = #f5f5f5 once looked like a light-ground rule and was\n    not."""\n    r, g, b = (int(colors.APP_CANVAS.lstrip(\'#\')[i:i + 2], 16) for i in (0, 2, 4))\n    assert r == g == b, f\'APP_CANVAS {colors.APP_CANVAS} is not a pure grey\'\n    brand = pytest.importorskip(\'engine.brand\', reason=\'rnv-brand not importable\')\n    assert colors.APP_CANVAS.lower() != brand.WEB_BLACK.lower()\n\n\n# ---------------------------------------------------------------- the overlays\n\ndef test_every_overlay_is_its_base_at_the_declared_alpha():\n    """The overlays are written out because Qt wants eight digits and composing\n    them would make the palette resolve to an expression. This is the\n    relationship that composition would have given, asserted instead -- so a\n    register move fails here rather than diverging silently."""\n    for name, (base_name, _key) in OVERLAYS.items():\n        overlay = getattr(colors, name)\n        base = getattr(colors, base_name)\n        assert len(overlay) == 9, f\'{name} is {overlay}, not #AARRGGBB\'\n        assert overlay[1:3].upper() == colors.IMAGE_OVERLAY_ALPHA.upper(), (\n            f\'{name} composites at {overlay[1:3]}, not IMAGE_OVERLAY_ALPHA\')\n        assert overlay[3:].lower() == base[1:].lower(), (\n            f\'{name} is {overlay}, whose colour half is not {base_name} \'\n            f\'{base}. An overlay that stops tracking its base is the exact \'\n            f\'drift this naming exists to prevent.\')\n\n\ndef test_every_overlay_base_is_still_a_register_value():\n    """Guard the guard. If a base stopped being registered, these would be\n    tracking something app-owned under a name that says otherwise."""\n    brand = pytest.importorskip(\'engine.brand\', reason=\'rnv-brand not importable\')\n    for name, (base_name, key) in OVERLAYS.items():\n        assert brand.APP[key].lower() == getattr(colors, base_name).lower(), (\n            f\'{name} claims to composite APP[{key!r}], which the register now \'\n            f\'holds as {brand.APP[key]} rather than {getattr(colors, base_name)}\')\n\n\ndef test_no_translucent_register_value_is_left_as_a_literal():\n    """The defect this pass fixes, asserted from the other side. The previous\n    guard compared whole strings, so an eight-digit spelling of a registered\n    value never matched a six-digit register entry."""\n    registered = {getattr(colors, n).lower()\n                  for n in (\'TRUE_BLACK\', \'WHITE\', \'BRAND_BLACK\', \'APP_CARD\',\n                            \'APP_BORDER\', \'APP_TEXT\', \'APP_TEXT_DIM\',\n                            \'APP_CANVAS\', \'APP_PANEL_HOVER\', \'APP_HOVER_LIGHT\')}\n    looked, found = 0, []\n    for dict_name in PALETTES:\n        node = _dict_node(dict_name)\n        for k, v in zip(node.keys, node.values):\n            if not (isinstance(v, ast.Constant) and isinstance(v.value, str)):\n                continue\n            if len(v.value) == 9 and v.value.startswith(\'#\'):\n                looked += 1\n                if \'#\' + v.value[3:].lower() in registered:\n                    found.append(f\'{dict_name}[{k.value!r}] = {v.value}\')\n    assert looked or True  # image mode may legitimately hold none\n    assert not found, (\n        \'registered values still spelled as translucent literals:\\n  \'\n        + \'\\n  \'.join(found))\n\n\n# ------------------------------------------------------------------- the plate\n\ndef test_the_plate_is_a_step_on_the_ink_grid():\n    assert colors.APP_HOVER_LIGHT == grey(14) == \'#eeeeee\'\n\n\ndef test_the_plate_carries_gold_with_room_to_spare():\n    """The reason the register moved the value. Both plates clear the floor;\n    only one clears it by enough to survive the gold moving."""\n    gold = colors.BRAND_DARK_GOLD_DEEP\n    here = _contrast(gold, colors.APP_HOVER_LIGHT)\n    edge = _contrast(gold, colors.IMAGE_CANVAS_LIGHT)\n    assert here >= TEXT_FLOOR, f\'gold reads {here:.4f} on the plate\'\n    assert here - TEXT_FLOOR >= 0.2, (\n        f\'the plate clears the floor by only {here - TEXT_FLOOR:.4f}. The \'\n        f\'register moved APP["hover-light"] here for margin, not for a pass.\')\n    assert edge - TEXT_FLOOR < 0.05, (\n        f\'#e8e8e8 now clears by {edge - TEXT_FLOOR:.4f}, so it is no longer \'\n        f\'the knife-edge this ruling was about. Either the gold moved or the \'\n        f\'floor did; re-derive before trusting the value above.\')\n\n\ndef test_the_floor_is_not_used_as_a_hover_anywhere():\n    """A negative check needs a companion proving it is still looking."""\n    looked, found = 0, []\n    for dict_name, live in PALETTES.items():\n        for key, value in live.items():\n            if \'hover\' not in key or not isinstance(value, str):\n                continue\n            looked += 1\n            if value.lower() == \'#e8e8e8\':\n                found.append(f\'{dict_name}[{key!r}]\')\n    assert looked >= 8, f\'only {looked} hover keys seen -- the sweep is blind\'\n    assert not found, (\n        f\'#e8e8e8 is being used as a hover plate: {found}. It is \'\n        f\'GOLD_TEXT_GROUND_FLOOR, not an interaction state.\')\n\n\n# -------------------------------------------------------------- the coincidence\n\ndef test_every_coincidence_still_coincides():\n    """A named coincidence that no longer shares a value is a dead exemption,\n    and a dead exemption is a licence waiting for a defect: it would let a\n    genuinely misclassified value hide behind it."""\n    brand = pytest.importorskip(\'engine.brand\', reason=\'rnv-brand not importable\')\n    stale = []\n    for name, (entry, _why) in COINCIDENT.items():\n        mine = getattr(colors, name).lower()\n        theirs = getattr(brand, entry, None)\n        if theirs is None:\n            stale.append(f\'{name}: the register no longer defines {entry}\')\n        elif mine != theirs.lower():\n            stale.append(f\'{name} = {mine} no longer matches {entry} {theirs}\')\n    assert not stale, (\n        \'COINCIDENT entries that no longer describe reality:\\n  \'\n        + \'\\n  \'.join(stale)\n        + \'\\n\\nDelete the entry or correct it -- do not leave it standing.\')\n\n\ndef test_the_coincidence_is_not_wired_as_a_mirror():\n    """The other direction. IMAGE_CANVAS_LIGHT must not be reachable through\n    anything that follows the register, or the separation is decorative."""\n    assert \'IMAGE_CANVAS_LIGHT\' not in NEW\n    assert \'IMAGE_CANVAS_LIGHT\' not in OVERLAYS\n    node = _dict_node(\'LIGHT_THEME_COLORS\')\n    value = _entry(node, \'image_viewer_bg\')\n    assert isinstance(value, ast.Name) and value.id == \'IMAGE_CANVAS_LIGHT\', (\n        \'the light image canvas must name the app-owned constant, not the \'\n        \'register one it happens to equal\')\n\n\n# ------------------------------------------------- the spelling, not the value\n\ndef test_every_wired_entry_names_a_constant_not_a_literal():\n    """A literal cannot follow its base. If the register moves any of these,\n    they move with it or this fails."""\n    allowed = set(NEW) | set(OVERLAYS) | set(COINCIDENT)\n    literals = []\n    for dict_name, keys in WIRED.items():\n        node = _dict_node(dict_name)\n        for key in keys:\n            value = _entry(node, key)\n            if not isinstance(value, ast.Name) or value.id not in allowed:\n                literals.append(\n                    f\'{dict_name}[{key!r}] = \'\n                    f\'{ast.unparse(value) if value else "missing"}\')\n    assert not literals, (\n        \'entries still written as literals:\\n  \' + \'\\n  \'.join(literals))\n\n\ndef test_the_resolved_values_are_the_constants():\n    """The AST check proves the spelling; this proves the value. Both, because\n    a name can be spelled correctly and resolve to something else."""\n    for dict_name, keys in WIRED.items():\n        node = _dict_node(dict_name)\n        for key in keys:\n            name = _entry(node, key).id\n            assert PALETTES[dict_name][key] == getattr(colors, name), (\n                f\'{dict_name}[{key!r}] resolves to \'\n                f\'{PALETTES[dict_name][key]}, not {name}\')\n'


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
        touched = []
        for rel, text in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                p.write_text(text, encoding="utf-8")
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
        raise SystemExit(f"run this from the root of a {REPO} checkout "
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
