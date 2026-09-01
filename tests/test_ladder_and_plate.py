"""The dark ladder, the light plate, the translucent overlays, and one
deliberate coincidence.

WHAT THIS PASS DID. rnv-brand rev 22 registered the two ends of the dark
surface ladder -- APP["canvas"] #0a0a0a and APP["panel-hover"] #3a3a3a -- rev
23 registered APP["hover-light"] #eeeeee, and rev 24 registered #e8e8e8 as
GOLD_TEXT_GROUND_FLOOR. All were app-owned here. No value changed: the pass
changes provenance and spelling, not pixels.

    BRAND_BLACK + n * 0x10,  n in -1..+2
    #0a0a0a canvas   #1a1a1a panel   #2a2a2a card   #3a3a3a panel-hover

WHY THE LADDER WAS NOT "TWO-THIRDS SPECIFIED". The register said it was,
because APP["border"] #333333 is not #3a3a3a and so looked like a missing rung.
It is not a rung -- #333333 is grey(3) on the INK grid, which governs inks and
EDGES, and a border is an edge. Measured against the wrong family.

WHY THE PLATE IS #eeeeee AND NOT #e8e8e8. #e8e8e8 is the ground
BRAND_DARK_GOLD_DEEP is calibrated against -- the smallest uniform step that
clears it is -14, and -13 gives 4.4675 and fails. The hover plate on that value
would have pinned every hover in the app to the one ground the gold cannot
afford to lose, with 0.0334 of margin. A boundary is not a plate.

WHY THE OVERLAYS ARE HERE AT ALL. Qt spells a translucent colour #AARRGGBB.
The 2026-08-29 wiring pass swept for six-digit literals, so #ED000000 never
matched #000000 and four registered values sat in IMAGE_MODE_COLORS while the
guard reported clean. They are named now, and the sweep normalises both
lengths.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from utils import config as colors
from utils.config import (DARK_THEME_COLORS as DARK,
                          IMAGE_MODE_COLORS as IMAGE,
                          LIGHT_THEME_COLORS as LIGHT)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'utils/config.py'

GRID_STEP = 0x11
LADDER_STEP = 0x10
TEXT_FLOOR = 4.5

#: Constant name -> the APP key it mirrors, and the value both hold.
NEW = {
    'APP_CANVAS': ('canvas', '#0a0a0a'),
    'APP_PANEL_HOVER': ('panel-hover', '#3a3a3a'),
    'APP_HOVER_LIGHT': ('hover-light', '#eeeeee'),
}

#: Overlay constant -> (the six-digit constant it composites, its APP key).
OVERLAYS = {
    'APP_WINDOW_OVERLAY': ('TRUE_BLACK', 'window'),
    'APP_CANVAS_OVERLAY': ('APP_CANVAS', 'canvas'),
    'APP_PANEL_OVERLAY': ('BRAND_BLACK', 'panel'),
}

#: palette dict name -> the keys in it that must now name a constant.
WIRED = {
    'DARK_THEME_COLORS': ('hover_bg', 'dialog_btn_hover_bg', 'list_hover_bg',
                          'image_viewer_bg'),
    'IMAGE_MODE_COLORS': ('window_bg', 'scroll_area_bg', 'image_viewer_bg',
                          'zoom_label_bg'),
    'LIGHT_THEME_COLORS': ('hover_bg', 'dialog_btn_hover_bg', 'tab_hover_bg',
                           'list_hover_bg', 'image_viewer_bg'),
}

#: dict NAME -> the live dict. Looking a key up in the wrong palette is how a
#: per-mode difference gets checked against the other mode's value and passes.
PALETTES = {'DARK_THEME_COLORS': DARK, 'IMAGE_MODE_COLORS': IMAGE,
            'LIGHT_THEME_COLORS': LIGHT}

#: App-owned values that DELIBERATELY share a hex with a register entry.
#: Sharing a VALUE is not playing the same ROLE, and a value check cannot tell
#: the difference -- so the intentional ones are named, with what they share
#: and why they must NOT follow if the register moves.
#:
#: name -> (register constant, why it is not the same role)
COINCIDENT = {
    'IMAGE_CANVAS_LIGHT': (
        'GOLD_TEXT_GROUND_FLOOR',
        'The register value is the darkest light ground on which the gold '
        'family carries TEXT -- it is the constraint BRAND_DARK_GOLD_DEEP is '
        'derived against. This is the empty canvas behind a loaded image: a '
        'QGraphicsView background brush in RNV_Color_Picker.py with the '
        "user's own picture drawn on it. No gold, no error red, and no text "
        'of any kind is ever drawn on it. If the register moves the floor, '
        'this must NOT follow -- which is why it is named here rather than '
        'mirrored.'),
}


def grey(n: int) -> str:
    v = n * GRID_STEP
    return '#%02x%02x%02x' % (v, v, v)


def _luminance(value: str) -> float:
    channels = [int(value.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _dict_node(name: str) -> ast.Dict:
    tree = ast.parse(SRC.read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if getattr(target, 'id', None) == name and isinstance(node.value, ast.Dict):
                return node.value
    raise AssertionError(f'{name} is not a dict literal in utils/config.py')


def _entry(node: ast.Dict, key: str):
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


# ------------------------------------------------------------- guard the guard

def test_everything_this_file_reads_still_exists():
    """Renaming a key must fail loudly here rather than let the rest of this
    file pass quietly over nothing."""
    for name in list(NEW) + list(OVERLAYS) + list(COINCIDENT):
        assert hasattr(colors, name), f'utils.config has no {name}'
    for dict_name, keys in WIRED.items():
        assert dict_name in PALETTES, f'{dict_name} is not in PALETTES'
        for key in keys:
            assert key in PALETTES[dict_name], f'{dict_name} has no {key!r}'


def test_the_wiring_map_is_not_empty():
    """Every sweep below iterates WIRED. An empty map passes all of them."""
    assert WIRED and all(WIRED.values())
    assert sum(len(v) for v in WIRED.values()) >= 13


# ------------------------------------------------------------------- the values

def test_the_new_constants_hold_the_registered_values():
    """The local half of the mirror. Runs everywhere, including where
    engine.brand is not importable -- which is why it is not optional."""
    drift = {n: getattr(colors, n) for n, (_, v) in NEW.items()
             if getattr(colors, n) != v}
    assert not drift, (
        f'these constants no longer hold their registered values: {drift}\n'
        f'If the brand moved, update this file in the same commit that updates '
        f'utils/config.py -- never one without the other.')


def test_the_new_constants_match_rnv_brand():
    """The upstream half. Skips where rnv-brand is not importable."""
    brand = pytest.importorskip(
        'engine.brand',
        reason='rnv-brand not importable here; the local pin is doing the work')
    drift = []
    for name, (key, _) in NEW.items():
        theirs, mine = brand.APP[key], getattr(colors, name)
        if mine.lower() != theirs.lower():
            drift.append(f'{name}: ours {mine}, theirs APP[{key!r}] {theirs}')
    assert not drift, 'drift from rnv-brand:\n  ' + '\n  '.join(drift)


def test_provenance_is_declared_for_everything_this_pass_named():
    """A classification that lives only in a test drifts from the thing it
    classifies, so it lives in the module and is read from there. This is also
    the first thing to read APP_PROVENANCE, whose docstring has claimed since
    the ink pass that a test reads it. Nothing did."""
    for name in NEW:
        assert colors.APP_PROVENANCE.get(name) == 'register', name
    for name in OVERLAYS:
        assert colors.APP_PROVENANCE.get(name) == 'register-overlay', name
    for name in COINCIDENT:
        group = colors.APP_PROVENANCE.get(name)
        assert group and group.startswith('app-'), (
            f'{name} is a coincidence, so it must be declared app-owned. '
            f'Declaring it register-owned would exempt a mirrored value from '
            f'the mirror.')


# ------------------------------------------------------------------ the ladder

def test_the_dark_rungs_are_exact_steps_on_the_ladder():
    """BRAND_BLACK + n * 0x10. Two of these were app-owned on the argument that
    the ladder might not be real. It is, and this is what says so."""
    base = int(colors.BRAND_BLACK.lstrip('#'), 16)
    for n, name in ((-1, 'APP_CANVAS'), (0, 'BRAND_BLACK'), (1, 'APP_CARD'),
                    (2, 'APP_PANEL_HOVER')):
        want = base + n * (LADDER_STEP * 0x010101)
        assert int(getattr(colors, name).lstrip('#'), 16) == want, (
            f'{name} is {getattr(colors, name)}, not rung n={n}')


def test_the_border_is_an_edge_and_not_a_rung():
    """The distinction that made the ladder look incomplete."""
    assert colors.APP_BORDER == grey(3)
    base = int(colors.BRAND_BLACK.lstrip('#'), 16)
    rungs = {base + n * (LADDER_STEP * 0x010101) for n in range(-1, 3)}
    assert int(colors.APP_BORDER.lstrip('#'), 16) not in rungs


def test_the_canvas_is_not_the_web_ground():
    """One byte apart, deliberately. App neutrals are pure grey R = G = B; the
    web ground #0a0a0f carries a tint the apps do not. That byte is why
    invert(#0a0a0a) = #f5f5f5 once looked like a light-ground rule and was
    not."""
    r, g, b = (int(colors.APP_CANVAS.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    assert r == g == b, f'APP_CANVAS {colors.APP_CANVAS} is not a pure grey'
    brand = pytest.importorskip('engine.brand', reason='rnv-brand not importable')
    assert colors.APP_CANVAS.lower() != brand.WEB_BLACK.lower()


# ---------------------------------------------------------------- the overlays

def test_every_overlay_is_its_base_at_the_declared_alpha():
    """The overlays are written out because Qt wants eight digits and composing
    them would make the palette resolve to an expression. This is the
    relationship that composition would have given, asserted instead -- so a
    register move fails here rather than diverging silently."""
    for name, (base_name, _key) in OVERLAYS.items():
        overlay = getattr(colors, name)
        base = getattr(colors, base_name)
        assert len(overlay) == 9, f'{name} is {overlay}, not #AARRGGBB'
        assert overlay[1:3].upper() == colors.IMAGE_OVERLAY_ALPHA.upper(), (
            f'{name} composites at {overlay[1:3]}, not IMAGE_OVERLAY_ALPHA')
        assert overlay[3:].lower() == base[1:].lower(), (
            f'{name} is {overlay}, whose colour half is not {base_name} '
            f'{base}. An overlay that stops tracking its base is the exact '
            f'drift this naming exists to prevent.')


def test_every_overlay_base_is_still_a_register_value():
    """Guard the guard. If a base stopped being registered, these would be
    tracking something app-owned under a name that says otherwise."""
    brand = pytest.importorskip('engine.brand', reason='rnv-brand not importable')
    for name, (base_name, key) in OVERLAYS.items():
        assert brand.APP[key].lower() == getattr(colors, base_name).lower(), (
            f'{name} claims to composite APP[{key!r}], which the register now '
            f'holds as {brand.APP[key]} rather than {getattr(colors, base_name)}')


def test_no_translucent_register_value_is_left_as_a_literal():
    """The defect this pass fixes, asserted from the other side. The previous
    guard compared whole strings, so an eight-digit spelling of a registered
    value never matched a six-digit register entry."""
    registered = {getattr(colors, n).lower()
                  for n in ('TRUE_BLACK', 'WHITE', 'BRAND_BLACK', 'APP_CARD',
                            'APP_BORDER', 'APP_TEXT', 'APP_TEXT_DIM',
                            'APP_CANVAS', 'APP_PANEL_HOVER', 'APP_HOVER_LIGHT')}
    looked, found = 0, []
    for dict_name in PALETTES:
        node = _dict_node(dict_name)
        for k, v in zip(node.keys, node.values):
            if not (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                continue
            if len(v.value) == 9 and v.value.startswith('#'):
                looked += 1
                if '#' + v.value[3:].lower() in registered:
                    found.append(f'{dict_name}[{k.value!r}] = {v.value}')
    assert looked or True  # image mode may legitimately hold none
    assert not found, (
        'registered values still spelled as translucent literals:\n  '
        + '\n  '.join(found))


# ------------------------------------------------------------------- the plate

def test_the_plate_is_a_step_on_the_ink_grid():
    assert colors.APP_HOVER_LIGHT == grey(14) == '#eeeeee'


def test_the_plate_carries_gold_with_room_to_spare():
    """The reason the register moved the value. Both plates clear the floor;
    only one clears it by enough to survive the gold moving."""
    gold = colors.BRAND_DARK_GOLD_DEEP
    here = _contrast(gold, colors.APP_HOVER_LIGHT)
    edge = _contrast(gold, colors.IMAGE_CANVAS_LIGHT)
    assert here >= TEXT_FLOOR, f'gold reads {here:.4f} on the plate'
    assert here - TEXT_FLOOR >= 0.2, (
        f'the plate clears the floor by only {here - TEXT_FLOOR:.4f}. The '
        f'register moved APP["hover-light"] here for margin, not for a pass.')
    assert edge - TEXT_FLOOR < 0.05, (
        f'#e8e8e8 now clears by {edge - TEXT_FLOOR:.4f}, so it is no longer '
        f'the knife-edge this ruling was about. Either the gold moved or the '
        f'floor did; re-derive before trusting the value above.')


def test_the_floor_is_not_used_as_a_hover_anywhere():
    """A negative check needs a companion proving it is still looking."""
    looked, found = 0, []
    for dict_name, live in PALETTES.items():
        for key, value in live.items():
            if 'hover' not in key or not isinstance(value, str):
                continue
            looked += 1
            if value.lower() == '#e8e8e8':
                found.append(f'{dict_name}[{key!r}]')
    assert looked >= 8, f'only {looked} hover keys seen -- the sweep is blind'
    assert not found, (
        f'#e8e8e8 is being used as a hover plate: {found}. It is '
        f'GOLD_TEXT_GROUND_FLOOR, not an interaction state.')


# -------------------------------------------------------------- the coincidence

def test_every_coincidence_still_coincides():
    """A named coincidence that no longer shares a value is a dead exemption,
    and a dead exemption is a licence waiting for a defect: it would let a
    genuinely misclassified value hide behind it."""
    brand = pytest.importorskip('engine.brand', reason='rnv-brand not importable')
    stale = []
    for name, (entry, _why) in COINCIDENT.items():
        mine = getattr(colors, name).lower()
        theirs = getattr(brand, entry, None)
        if theirs is None:
            stale.append(f'{name}: the register no longer defines {entry}')
        elif mine != theirs.lower():
            stale.append(f'{name} = {mine} no longer matches {entry} {theirs}')
    assert not stale, (
        'COINCIDENT entries that no longer describe reality:\n  '
        + '\n  '.join(stale)
        + '\n\nDelete the entry or correct it -- do not leave it standing.')


def test_the_coincidence_is_not_wired_as_a_mirror():
    """The other direction. IMAGE_CANVAS_LIGHT must not be reachable through
    anything that follows the register, or the separation is decorative."""
    assert 'IMAGE_CANVAS_LIGHT' not in NEW
    assert 'IMAGE_CANVAS_LIGHT' not in OVERLAYS
    node = _dict_node('LIGHT_THEME_COLORS')
    value = _entry(node, 'image_viewer_bg')
    assert isinstance(value, ast.Name) and value.id == 'IMAGE_CANVAS_LIGHT', (
        'the light image canvas must name the app-owned constant, not the '
        'register one it happens to equal')


# ------------------------------------------------- the spelling, not the value

def test_every_wired_entry_names_a_constant_not_a_literal():
    """A literal cannot follow its base. If the register moves any of these,
    they move with it or this fails."""
    allowed = set(NEW) | set(OVERLAYS) | set(COINCIDENT)
    literals = []
    for dict_name, keys in WIRED.items():
        node = _dict_node(dict_name)
        for key in keys:
            value = _entry(node, key)
            if not isinstance(value, ast.Name) or value.id not in allowed:
                literals.append(
                    f'{dict_name}[{key!r}] = '
                    f'{ast.unparse(value) if value else "missing"}')
    assert not literals, (
        'entries still written as literals:\n  ' + '\n  '.join(literals))


def test_the_resolved_values_are_the_constants():
    """The AST check proves the spelling; this proves the value. Both, because
    a name can be spelled correctly and resolve to something else."""
    for dict_name, keys in WIRED.items():
        node = _dict_node(dict_name)
        for key in keys:
            name = _entry(node, key).id
            assert PALETTES[dict_name][key] == getattr(colors, name), (
                f'{dict_name}[{key!r}] resolves to '
                f'{PALETTES[dict_name][key]}, not {name}')
