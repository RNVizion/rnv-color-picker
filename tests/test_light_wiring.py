"""RNV-LIGHT-WIRING-GUARD -- every palette value has a name, and the split holds.

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
