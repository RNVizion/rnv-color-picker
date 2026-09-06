#!/usr/bin/env python3
"""
RNV-WIRING-TOOL-DO-NOT-SWEEP

Give every hex in rnv-color-picker's palettes a constant, and collapse the strays.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file


WHY

55 palette entries in this repository were written as bare hex literals
-- 47 of them in the light palette. A literal cannot follow a register
change: when rnv-brand moves a value, every constant that mirrors it moves and
every literal stays behind. That is how #c4a458 was orphaned, and it is why
this programme's standing rule is that every hex a palette carries has a
constant between the value and its use.

The dark palette was already wired, almost entirely. Light was not, because
light was built later and by hand. So this is mostly a light pass -- but the
rule is per palette, and the handful of dark literals go with it.


WHAT IS WIRED, AND HOW THE NAMES WERE CHOSEN

Registered values take the register's name, as APP_CARD / APP_BORDER /
APP_HOVER_LIGHT already do here. Ramp greys take the ramp name, by byte, as
rnv-text-transformer does: GREY_CC, GREY_66. Nothing here is a new colour;
every constant this script adds is a hex the palettes already carried.

THE SPLIT. rnv-text-transformer ruled, in tests/test_ladder_and_plate.py, that
a hex whose register role is an INTERACTION STATE takes the register's name
only on keys that play that role -- "GREY_EE IS SPLIT, NOT RENAMED ... a
resting ground is not an interaction state, and wiring all four would claim a
role for three of them on the strength of a shared hex." The same shape is
applied here:

    #e0e0e0  pressed_bg          -> APP_PRESSED_LIGHT   plays the role
    #e0e0e0  tab_bg, scrollbar_bg -> GREY_E0            static, shares the hex
    #eeeeee  a hover             -> APP_HOVER_LIGHT
    #eeeeee  a list header       -> GREY_EE
    #dddddd  text                -> APP_TEXT
    #dddddd  a grid line         -> GREY_DD

Surfaces (#f5f5f5, #fbfbfb) and the border (#333333) are not split, because
every key that carries them plays the role.


THREE STRAYS COLLAPSE, AND THIS MOVES PIXELS

Three light greys sat on no ladder -- named nowhere, in any of the five
applications -- and each was a fraction of a step from a registered rung:

    #fafafa  ->  #fbfbfb  APP surface-light-2   CIEDE2000 0.20
    #f8f8f8  ->  #fbfbfb  APP surface-light-2   CIEDE2000 0.60
    #f0f0f0  ->  #eeeeee  APP hover-light       CIEDE2000 0.42

Ruled by Chris on 2026-09-06 onto the nearest rung, on the same reasoning as
#252525 onto the card and #505050 onto grey 44: a value under one CIEDE2000
from a registered one is that one, misspelled. Below any threshold this
register has ever called a visible step. Everything else in this script is a
rename with no pixel moved.

In this repository: list_alt_bg (#f8f8f8) and list_header_bg (#f0f0f0).
Both keys are looked up nowhere -- they are on the dead-key list -- so
no pixel actually moves here today. They are collapsed anyway, because
a dead key holding a stray is a stray waiting for a reader.

WHAT THE GUARD PINS

It reads the three palette dicts back through `ast` and fails on any value
that is a string hex, so a literal cannot come back. It asserts the split --
that `pressed_bg` resolves to the register's pressed plate and the static keys
do not -- and it asserts the collapsed keys resolve to their rung. And it
checks that no two constants in this module hold the same hex UNLESS they are
a declared split pair, so a second name for one colour cannot appear without
saying which role it plays.
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
DESCRIPTION = "wire every palette literal through a constant; collapse three strays"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "RNV-LIGHT-WIRING"
GUARD = "tests/test_light_wiring.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ("pytest tests/",
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ("unittest suite",
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

PALETTES = ['DARK_THEME_COLORS', 'LIGHT_THEME_COLORS', 'IMAGE_MODE_COLORS']
QUOTE = '"'

# hex -> the constant a key holding it takes, unless SPLIT says otherwise
WIRE = {'#ffffff': 'WHITE', '#000000': 'TRUE_BLACK', '#f5f5f5': 'APP_SURFACE_LIGHT_3', '#aaaaaa': 'APP_TEXT_DIM', '#333333': 'APP_BORDER', '#dddddd': 'GREY_DD', '#eeeeee': 'GREY_EE', '#e0e0e0': 'GREY_E0', '#cccccc': 'GREY_CC', '#666666': 'GREY_66', '#888888': 'GREY_88', '#444444': 'GREY_44', '#555555': 'GREY_55', '#606060': 'GREY_60', '#fafafa': 'APP_SURFACE_LIGHT_2', '#f8f8f8': 'APP_SURFACE_LIGHT_2', '#f0f0f0': 'GREY_EE'}
# (hex, key) -> constant, where the key plays the register's role
SPLIT = {('#e0e0e0', 'pressed_bg'): 'APP_PRESSED_LIGHT'}
# old hex -> new hex, for the three strays
COLLAPSE = {'#fafafa': '#fbfbfb', '#f8f8f8': '#fbfbfb', '#f0f0f0': '#eeeeee'}
EXPECTED = 55
EXTRA_EDITS = [('tests/test_register_wiring.py', "LIGHT_RULED = ('APP_HOVER_LIGHT',)\n", "# RNV-LIGHT-WIRING (2026-09-06). Widened on purpose, with the pass that\n# wires them: light ink is TRUE_BLACK and light edges are APP_BORDER,\n# both already ruled in the register and until now written as literals.\nLIGHT_RULED = ('APP_HOVER_LIGHT', 'TRUE_BLACK', 'APP_BORDER')\n", 1)]
EXTRA_SWEEP = []
# Blocks that already define a constant the palettes need, but define it
# BELOW the palettes -- legal where nothing referenced them, fatal the moment
# a palette does. Moved verbatim into the ladder block, comments and all.
RELOCATE = ['# ── Neutral edges ──\n# RNV-INK-RULE (2026-09-02). Named for the colour, not the job.\n#\n# GREY_44 was the swatch-preview outline, held under two role names at once:\n# the same value written twice, once in full and once in three digits, which\n# is how it stayed invisible to a census that reads six. Only the short form\n# was ever used.\n#\n# GREY_CC is the light edge swatch_edge() reaches for on a dark ground. It\n# was three digits too, and equally invisible.\nGREY_44: Final[str] = "#444444"\nGREY_CC: Final[str] = "#cccccc"\n\n\n']

NEW = ['APP_SURFACE_LIGHT_3', 'APP_SURFACE_LIGHT_2', 'APP_PRESSED_LIGHT', 'GREY_E0', 'GREY_EE', 'GREY_DD', 'GREY_66', 'GREY_88', 'GREY_55']
DOCS = {'APP_SURFACE_LIGHT_3': ('#f5f5f5', 'engine/brand.py APP["surface-light-3"]. The light window and panel\nground -- what a dialog sits on in light mode.\n\nRNV-LIGHT-WIRING (2026-09-06): this value was written out as a literal\nin every palette that used it, so nothing could move it. Registered by\nrev 27 as the third rung of the light surface ladder; named here under\nthe register\'s key, the way APP_PANEL_HOVER and APP_HOVER_LIGHT are.\nEvery key that carries it is a surface, so it is not split.'), 'APP_SURFACE_LIGHT_2': ('#fbfbfb', 'engine/brand.py APP["surface-light-2"]. One rung above the panel ground.\n\nRNV-LIGHT-WIRING (2026-09-06): new to this application. It arrives\nbecause two strays collapse onto it -- #f8f8f8 and #fafafa, which sat\n0.60 and 0.20 CIEDE2000 from this rung and on no ladder at all. Same\nruling as #252525 onto the card: a value a fraction of a step from a\nregistered one is that one, misspelled.'), 'APP_PRESSED_LIGHT': ('#e0e0e0', 'engine/brand.py APP["pressed-light"]. The light PRESSED plate -- an\ninteraction state, which is why this name goes only on `pressed_bg`.\n\nRNV-LIGHT-WIRING (2026-09-06): SPLIT, NOT RENAMED. Other keys hold\n#e0e0e0 as a static surface (a tab, a scrollbar track) and keep the\nramp-step name GREY_E0 below. Wiring a resting ground to a pressed\nstate would claim a role for it on the strength of a shared hex --\nthe same ruling rnv-text-transformer made for GREY_EE / APP_HOVER_LIGHT.'), 'GREY_E0': ('#e0e0e0', 'grey(14) on the ramp, #e0e0e0. Static surfaces that share a hex with\nAPP_PRESSED_LIGHT without being a pressed state. See the split note\nthere. Named by its byte, like every other ramp step.'), 'GREY_EE': ('#eeeeee', 'grey(14) on the ramp, #eeeeee. Static surfaces that share a hex with\nAPP_HOVER_LIGHT without being a hover: a list header, a scroll ground.\nSame split rnv-text-transformer ruled for its diff headers.'), 'GREY_DD': ('#dddddd', 'grey(13) on the ramp, #dddddd. Edges and grid lines that share a hex\nwith APP_TEXT without being text. The register\'s APP["text"] is ink;\na gridline is not, and moving the ink should not move the grid.'), 'GREY_66': ('#666666', 'grey(6) on the ramp, #666666. Secondary and muted text on light.'), 'GREY_88': ('#888888', 'grey(8) on the ramp, #888888. Muted text on dark, a scrollbar handle\nhover on light.'), 'GREY_55': ('#555555', 'grey(5) on the ramp, #555555. Disabled text and a checkbox edge on dark.')}
ANCHOR = 'plate. This value is a grid step inside it and gold reads 4.7875 on it.\n"""\n'
PROVENANCE_ANCHOR = '    "IMAGE_CANVAS_LIGHT": "app-canvas",\n}\n'
PINNED_ANCHOR = "    'APP_HOVER_LIGHT': '#eeeeee',\n}\n"

GUARD_SOURCE = r'''"""RNV-LIGHT-WIRING-GUARD -- every palette value has a name, and the split holds.

Installed 2026-09-06. Three things it pins:

  * no value in any palette is a bare hex -- a literal cannot follow the
    register, so one appearing here is a value that will be orphaned;
  * the SPLIT: the register's interaction-state names sit only on keys that
    play the role, and static keys sharing the hex keep the ramp name;
  * the three collapsed strays resolve to their rung, and the old values are
    gone from the module.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from utils import config as C

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'utils/config.py'
PALETTES = ['DARK_THEME_COLORS', 'LIGHT_THEME_COLORS', 'IMAGE_MODE_COLORS']
HEX = re.compile(r"#[0-9a-fA-F]{6}$")

# (hex, key) -> the constant that key must resolve THROUGH, in source.
# Narrowed to the splits this repository actually holds; the fleet's other
# split keys are listed below and asserted absent.
SPLIT = {('#e0e0e0', 'pressed_bg'): 'APP_PRESSED_LIGHT'}
SPLIT_ABSENT = ['platform_btn_hover_bg']
# old hex -> new hex
COLLAPSE = {'#fafafa': '#fbfbfb', '#f8f8f8': '#fbfbfb', '#f0f0f0': '#eeeeee'}
# Hexes that legitimately carry two constant names here, with the role each
# one plays. A pair listed here is a decision on the record; anything else
# sharing a hex is a duplicate until someone says otherwise.
EXTRA_ALLOWED_PAIRS = ()
# Source lines that legitimately hold a stray value and must NOT be collapsed.
# Each one is a value this application does not own -- platform chrome, a file
# format's fixed background -- and the sweep below subtracts them by exact text
# so that removing one is a visible edit, not a silent widening.
STRAY_EXEMPT = ()


def _palette_dicts():
    mod = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    out = {}
    for node in mod.body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target in PALETTES and isinstance(value, ast.Dict):
            out[target] = value
    assert set(out) == set(PALETTES), f"palettes not found: {set(PALETTES) - set(out)}"
    return out


def _entries(d):
    """(key, value) for the literal entries of a dict node.

    A palette may open with `**OTHER_PALETTE`, and ast records that as a key
    of None. It is not an entry -- it has no name of its own -- and calling
    literal_eval on it raises rather than skipping it.
    """
    for k, v in zip(d.keys, d.values):
        if k is None:
            continue
        yield ast.literal_eval(k), v


@pytest.mark.parametrize("palette", PALETTES)
def test_no_palette_value_is_a_bare_hex(palette):
    """Read from SOURCE rather than from the resolved dict, because the
    resolved dict cannot tell a literal from a constant -- both are strings by
    the time they are values."""
    d = _palette_dicts()[palette]
    bad = []
    for key, v in _entries(d):
        if isinstance(v, ast.Constant) and isinstance(v.value, str) \
                and HEX.match(v.value):
            bad.append((key, v.value))
    assert not bad, (
        f"{palette} writes these as literals; a literal cannot follow the "
        f"register and will be orphaned the first time it moves: {bad}")


def test_the_split_puts_register_names_only_on_role_keys():
    """rnv-text-transformer's ruling, applied here: a pressed plate is an
    interaction state, a tab is not, and they do not share a name on the
    strength of a shared hex."""
    src = SOURCE.read_text(encoding="utf-8-sig")
    for (hexv, key), const in SPLIT.items():
        assert re.search(r"'%s':\s+%s," % (key, const), src), (
            f"{key} does not resolve through {const}")
    # The fleet declares two splits; this repository holds the ones in SPLIT
    # above and genuinely has no key by the other names. Asserted rather than
    # assumed, so that a key arriving later under one of those names is not
    # quietly wired to the ramp step.
    all_keys = {key for d in _palette_dicts().values() for key, _ in _entries(d)}
    for key in SPLIT_ABSENT:
        assert key not in all_keys, (
            f"{key!r} now exists in a palette here. It is a declared split in "
            f"the fleet; wire it to its register name rather than to the ramp "
            f"step, and move it into SPLIT.")
    # and the static keys that share those hexes do NOT carry the role name
    for pal_name, d in _palette_dicts().items():
        for key, v in _entries(d):
            if isinstance(v, ast.Name) and v.id == "APP_PRESSED_LIGHT":
                assert key == "pressed_bg", (
                    f"{pal_name}[{key!r}] carries APP_PRESSED_LIGHT but is not a "
                    f"pressed state; a static surface keeps GREY_E0")


@pytest.mark.parametrize("old,new", sorted(COLLAPSE.items()))
def test_the_strays_are_gone_and_resolve_to_their_rung(old, new):
    """Swept across the whole module, minus the sites that are not brand.

    A stray can come back anywhere, not only in a palette, so the sweep is
    module-wide. But module-wide is too wide on its own: some values in this
    file are not the brand's to move -- an OS chrome simulation, an export
    background fixed by a file format. Those are listed in STRAY_EXEMPT with
    the reason, so an exemption is a decision on the record rather than a
    hole in the sweep.
    """
    src = SOURCE.read_text(encoding="utf-8-sig")
    lines = [l for l in src.splitlines()
             if not l.lstrip().startswith("#") and l not in STRAY_EXEMPT]
    code = "\n".join(lines)
    assert f"'{old}'" not in code and f'"{old}"' not in code, (
        f"{old} is back as a value; it collapsed onto {new} on 2026-09-06")
    for pal in (C.LIGHT_THEME_COLORS,):
        for k, v in pal.items():
            assert v != old, f"light[{k!r}] is still {old}"


def test_every_exemption_is_still_there_and_still_needed():
    """An exemption that no longer matches a line is dead, and a dead
    exemption silently widens the sweep's blind spot the next time someone
    edits near it. Fail loudly instead."""
    src = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    for line in STRAY_EXEMPT:
        assert src.count(line) == 1, (
            f"exempted line is not present exactly once: {line!r}. If it was "
            f"deliberately removed, remove the exemption with it.")


def test_one_hex_one_name_unless_it_is_a_declared_split():
    """A second constant for one colour is either a split with a stated role,
    or a defect. This is what stops GREY_XX and APP_YY drifting into two
    names for one thing with nobody having decided that."""
    src = SOURCE.read_text(encoding="utf-8-sig")
    pat = re.compile(r"^([A-Z][A-Z0-9_]+):\s*Final\[str\]\s*=\s*['\"](#[0-9a-fA-F]{6})['\"]", re.M)
    by_hex = {}
    for name, hexv in pat.findall(src):
        by_hex.setdefault(hexv.lower(), []).append(name)
    allowed_pairs = {
        frozenset({"APP_PRESSED_LIGHT", "GREY_E0"}),
        frozenset({"APP_HOVER_LIGHT", "GREY_EE"}),
        frozenset({"APP_TEXT", "GREY_DD"}),
        # pre-existing, documented elsewhere in this module
        frozenset({"WHITE", "CONTRAST_DEMO_WHITE_BG"}),
        frozenset({"TRUE_BLACK", "CONTRAST_DEMO_BLACK_BG"}),
        frozenset({"WHITE", "SVG_EXPORT_BG"}),
        frozenset({"TRUE_BLACK", "SVG_EXPORT_STROKE"}),
        frozenset({"BRAND_BLACK", "APP_PANEL"}),
        frozenset({"APP_HOVER_LIGHT", "IMAGE_CANVAS_LIGHT"}),
    }
    allowed_pairs |= {frozenset(p) for p in EXTRA_ALLOWED_PAIRS}
    for hexv, names in by_hex.items():
        if len(names) < 2:
            continue
        pair = frozenset(names)
        ok = any(pair <= p or p <= pair for p in allowed_pairs) or \
             any(frozenset(c) in allowed_pairs
                 for c in __import__("itertools").combinations(names, 2))
        assert ok, (
            f"{hexv} has {len(names)} names -- {names} -- and is not a "
            f"declared split. Either one is a duplicate, or a split needs "
            f"declaring with the role each name plays.")


def test_every_name_a_palette_uses_is_defined_above_it():
    """Wiring gives constants callers they did not have.

    This module already held a constant defined two hundred lines BELOW the
    palettes -- legal for as long as nothing in a palette named it. The first
    palette entry to reach for it turns the file into a NameError at import,
    which surfaces as a collection error rather than as a failing assertion,
    and a collection error names one symbol and explains nothing.

    So: read the source, not the imported module. By the time the module
    imports, this has either worked or taken the whole suite down with it.
    """
    mod = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    assigned, dicts = {}, {}
    for node in mod.body:
        target = value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target is None:
            continue
        assigned.setdefault(target, node.lineno)
        if target in PALETTES and isinstance(value, ast.Dict):
            dicts[target] = node
    late = set()
    for pal, node in dicts.items():
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                at = assigned.get(sub.id)
                if at is not None and at > node.lineno:
                    late.add((pal, sub.id, at))
    assert not late, (
        f"assigned below the palette that reads them, which is a NameError "
        f"at import, not a style point: {sorted(late)}")


def test_this_guard_can_see_the_source():
    src = SOURCE.read_text(encoding="utf-8-sig")
    assert "RNV-LIGHT-WIRING" in src
    assert len(_palette_dicts()) == len(PALETTES)
'''


LINE = re.compile(r"^(\s+)'([a-z_0-9]+)':(\s+)'(#[0-9a-fA-F]{6})'(,.*)$")


def _palette_span(src: str, name: str):
    """(start, end) of the dict literal assigned to `name`, top-level only."""
    m = re.search(r"^%s\b[^\n]*=\s*\{\n" % re.escape(name), src, re.M)
    if not m:
        raise SystemExit(f"{SENTINEL_FILE}: no palette named {name}")
    start = m.end()
    end = src.index("\n}\n", start)
    return start, end


def _defined_after_use(mod):
    """Names read inside a palette dict but assigned below it.

    Python reads a module top to bottom, so a dict literal can only name
    constants already assigned. A constant sitting below the palettes is
    harmless until a palette reaches for it, which is exactly what wiring
    does -- so this has to be checked here, not assumed.
    """
    assigned, dicts = {}, {}
    for node in mod.body:
        target = value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target is None:
            continue
        assigned.setdefault(target, node.lineno)
        if target in PALETTES and isinstance(value, ast.Dict):
            dicts[target] = node
    late = set()
    for pal, node in dicts.items():
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                at = assigned.get(sub.id)
                if at is not None and at > node.lineno:
                    late.add((pal, sub.id, at))
    return sorted(late)


def _constant_block() -> str:
    out = []
    for name in NEW:
        hexv, doc = DOCS[name]
        out.append(f'{name}: Final[str] = {QUOTE}{hexv}{QUOTE}\n"""{doc}"""\n\n')
    return "".join(out)


def edits(tree) -> None:
    src = tree.read(SENTINEL_FILE)

    # --- 1. the constants, in one block after the light hover plate. Every
    # one is a hex the palettes already carry; the block adds names, not
    # colours. Anchored on the last line of APP_HOVER_LIGHT's docstring.
    if src.count(ANCHOR) != 1:
        raise SystemExit(f"{SENTINEL_FILE}: the APP_HOVER_LIGHT anchor is not "
                         f"where this script expects it")
    for name in NEW:
        if re.search(r"^%s\b" % name, src, re.M):
            raise SystemExit(f"{name} already exists in {SENTINEL_FILE}")
    marker = (f"\n# RNV-LIGHT-WIRING (2026-09-06): the constants below name values the\n"
              f"# palettes already carried as literals. Nothing here is a new colour.\n"
              f"# Registered values take the register's key; ramp greys take their byte.\n\n")
    # constants that exist but sit BELOW the palettes: lift them, verbatim,
    # into the same block. A name is not available to a dict literal that runs
    # before the assignment -- Python reads the module top to bottom.
    moved = ""
    for block in RELOCATE:
        if src.count(block) != 1:
            raise SystemExit(f"{SENTINEL_FILE}: the block to relocate is not "
                             f"present exactly once; re-derive this script")
        src = src.replace(block, "", 1)
        moved += ("# RNV-LIGHT-WIRING (2026-09-06): moved up from below the\n"
                  "# palettes, unchanged. It now has palette callers, and a\n"
                  "# name defined after its use is a NameError at import.\n"
                  + block)
    src = src.replace(ANCHOR, ANCHOR + marker + _constant_block() + moved, 1)

    # --- 2. the palettes. Every 6-digit literal inside the three dicts is
    # rewritten to its constant, chosen by (hex, key) so the split is explicit.
    # Counted exactly: fewer means the file changed shape, more means a
    # literal appeared that this script has no name for.
    rewired = []
    for pal in PALETTES:
        start, end = _palette_span(src, pal)
        body = src[start:end]
        new_lines = []
        for line in body.split("\n"):
            m = LINE.match(line)
            if not m:
                new_lines.append(line)
                continue
            indent, key, gap, hexv, rest = m.groups()
            hexv = hexv.lower()
            const = SPLIT.get((hexv, key)) or WIRE.get(hexv)
            if const is None:
                raise SystemExit(f"{pal}: {key!r} holds {hexv}, which this "
                                 f"script has no constant for")
            note = ""
            if hexv in COLLAPSE:
                new_hex = COLLAPSE[hexv]
                note = f"   # was {hexv}, collapsed onto {new_hex}"
            # keep the column alignment the file already has
            pad = gap if len(gap) > 1 else " "
            new_lines.append(f"{indent}'{key}':{pad}{const}{rest.rstrip()}{note}"
                             if not rest.strip().startswith("#") or note
                             else f"{indent}'{key}':{pad}{const}{rest}")
            rewired.append((pal, key, hexv, const))
        src = src[:start] + "\n".join(new_lines) + src[end:]

    if len(rewired) != EXPECTED:
        raise SystemExit(f"rewired {len(rewired)} entries, expected {EXPECTED}. "
                         f"The palettes have changed shape since this script "
                         f"was derived; re-derive it rather than trusting it.")
    tree.write(SENTINEL_FILE, src)

    # --- 3. APP_PROVENANCE: the register mirrors declared register-owned, the
    # ramp steps app-owned, the way tests/test_ladder_and_plate.py reads it.
    prov = "".join(
        f'    "{n}": "{"register" if n.startswith("APP_") else "app-ramp"}",\n'
        for n in NEW)
    tree.sub(SENTINEL_FILE, PROVENANCE_ANCHOR,
             PROVENANCE_ANCHOR.replace("}\n", prov + "}\n"), 1)

    # --- 4. the local pin in tests/test_app_mirror.py, so the register
    # mirrors are checked where rnv-brand is not importable.
    pins = "".join(f"    '{n}': '{DOCS[n][0]}',\n" for n in NEW if n.startswith("APP_"))
    tree.sub("tests/test_app_mirror.py", PINNED_ANCHOR,
             PINNED_ANCHOR.replace("}\n", pins + "}\n"), 1)

    # --- 5. repository-specific edits outside the palettes.
    for rel, old, new, times in EXTRA_EDITS:
        tree.sub(rel, old, new, times)

    print(f"  {len(NEW)} constant(s) added, {len(rewired)} palette entries wired, "
          f"{sum(1 for _,_,h,_ in rewired if h in COLLAPSE)} collapsed")
    for pal, key, hexv, const in rewired:
        flag = "  <- MOVES" if hexv in COLLAPSE else ""
        print(f"     {pal[:5]:5} {key:28} {hexv} -> {const}{flag}")


def checks(tree) -> None:
    src = tree.read(SENTINEL_FILE)
    # rnv-color-picker's files carry a UTF-8 BOM; ast.parse refuses it.
    mod = ast.parse(src.lstrip("\ufeff"))

    # no string hex survives inside the three palette dicts
    for node in mod.body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target in PALETTES and isinstance(value, ast.Dict):
            for k, v in zip(value.keys, value.values):
                if isinstance(v, ast.Constant) and isinstance(v.value, str) \
                        and re.fullmatch(r"#[0-9a-fA-F]{6}", v.value):
                    raise SystemExit(f"{target}[{ast.literal_eval(k)!r}] is "
                                     f"still the literal {v.value}")

    for name in NEW:
        hexv = DOCS[name][0]
        if f"{name}: Final[str] = {QUOTE}{hexv}{QUOTE}" not in src:
            raise SystemExit(f"{name} did not land as {hexv}")
    # The strays are gone from the PALETTES. Not from the whole file: the
    # icon builder's OS_SIM_COLORS holds #f0f0f0 as the colour of a Windows
    # taskbar, which is a fixed platform value that must NOT follow the brand
    # -- the same class as SVG_EXPORT_BG. A sweep of the whole module would
    # have "fixed" it.
    for pal in PALETTES:
        start, end = _palette_span(src, pal)
        body = src[start:end]
        for old in COLLAPSE:
            if f"'{old}'" in body or f'"{old}"' in body:
                raise SystemExit(f"stray {old} survives in {pal}")
    for extra in EXTRA_SWEEP:
        text = tree.read(extra)
        for old in COLLAPSE:
            if f"'{old}'" in text or f'"{old}"' in text:
                raise SystemExit(f"stray {old} survives in {extra}")
    # Every name a palette reaches for is assigned ABOVE the palette that
    # reaches for it. This is the guard that was missing: the icon builder
    # already defined GREY_CC two hundred lines BELOW its palettes, which was
    # legal only while nothing in a palette named it. Wiring gave it a caller
    # and turned the file into a NameError at import -- caught by a test
    # collection error, which is a poor place to learn it.
    late = _defined_after_use(mod)
    if late:
        raise SystemExit(
            f"{SENTINEL_FILE}: these names are used by a palette but assigned "
            f"below it, which is a NameError at import: {late}")

    if SENTINEL not in src:
        raise SystemExit("the wiring note did not land")
    print(f"  guards: 0 literals left in {len(PALETTES)} palettes, "
          f"{len(NEW)} constants in, {len(COLLAPSE)} strays gone, "
          f"every palette name defined above its use")


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
