"""
The dark half of the derivation: every registered value spelled as a NAME.

WHAT THIS PASS DID. The ink pass of 2026-08-28 defined and mirrored the APP
register here but deliberately left the palettes spelling those values as
literals -- rewiring is a mechanical substitution and that pass was a value
change, and mixing the two makes the diff unreadable and the snapshot evidence
worthless. This is the substitution, on its own, in DARK and IMAGE only.

WHY DARK ONLY. rnv-brand@8ab1174 rules the order: the dark surface ladder is
two-thirds specified and entirely inside the register, while the light ladder
is not ruled at all -- nine light surfaces sit inside three grid steps and the
register has not yet decided which of them are real distinctions. Deriving
against that gap would mean deriving twice.

NOTHING MOVED. This pass changes how values are spelled, not what they are.
The delivery script proved it by resolving both palettes before and after and
comparing them entry by entry; these tests hold the result in place.

THE POINT OF IT. A literal cannot follow its base. APP["text"] moved on
2026-08-28 and this app would have kept the old value silently, because the
value was written down rather than referenced. Every registered value in the
dark palettes is now a name, so the next register move carries.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from utils import config as colors
from utils.config import (DARK_THEME_COLORS as DARK,
                          IMAGE_MODE_COLORS as IMAGE)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'utils/config.py'

#: The register, as this app mirrors it. Value-keyed, because the substitution
#: was value-keyed: any dark entry holding one of these must now name it.
REGISTERED = {'TRUE_BLACK': '#000000', 'BRAND_BLACK': '#1a1a1a', 'APP_CARD': '#2a2a2a', 'APP_BORDER': '#333333'}

DARK_DICTS = ('DARK_THEME_COLORS', 'IMAGE_MODE_COLORS')
LIGHT_DICTS = ('LIGHT_THEME_COLORS',)

#: dict NAME -> the live dict. Looking a key up in the wrong palette is how a
#: per-mode difference gets checked against the other mode's value and passes.
#: DARK and IMAGE agree on most keys in most of these apps, so a lookup that
#: falls back from one to the other is right almost everywhere and wrong
#: exactly where it matters.
PALETTES = {'DARK_THEME_COLORS': DARK, 'IMAGE_MODE_COLORS': IMAGE}


def _dicts(names):
    tree = ast.parse(SRC.read_text(encoding='utf-8-sig'))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            name = getattr(target, 'id', None)
            if name in names and isinstance(node.value, ast.Dict):
                out[name] = node.value
    missing = set(names) - set(out)
    assert not missing, f'these palettes are no longer dict literals: {missing}'
    return out


# ------------------------------------------------------------- guard the guard

def test_the_palettes_this_file_reads_still_exist():
    """Every assertion below walks these. If one is renamed or stops being a
    dict literal, this fails loudly instead of the rest passing over nothing."""
    assert _dicts(DARK_DICTS)
    assert _dicts(LIGHT_DICTS)


def test_the_register_map_is_not_empty():
    """A sweep with nothing to look for passes forever."""
    assert len(REGISTERED) >= 4
    for name, value in REGISTERED.items():
        assert getattr(colors, name) == value, (
            f'{name} is {getattr(colors, name)}, not {value} -- the map this '
            f'file sweeps for has gone stale against the constants')


# ------------------------------------------------------------ the substitution

def test_no_registered_value_is_spelled_as_a_literal_in_dark():
    """The completeness half. This is the assertion that makes the pass stick:
    a literal cannot follow its base, so there must not be one left."""
    by_value = {v: k for k, v in REGISTERED.items()}
    literals = []
    for dict_name, node in _dicts(DARK_DICTS).items():
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                if value.value.lower() in by_value:
                    literals.append(
                        f'{dict_name}[{key.value!r}] = {value.value} '
                        f'(should read {by_value[value.value.lower()]})')
    assert not literals, (
        'registered values still written as literals in the dark palettes:\n  '
        + '\n  '.join(literals))


def test_every_dark_entry_that_names_a_constant_resolves_to_the_register():
    """The other half. A name is only worth having if it holds the right
    value."""
    wrong = []
    for dict_name, node in _dicts(DARK_DICTS).items():
        for key, value in zip(node.keys, node.values):
            if isinstance(value, ast.Name) and value.id in REGISTERED:
                actual = PALETTES[dict_name].get(key.value)
                if actual != REGISTERED[value.id]:
                    wrong.append(f'{dict_name}[{key.value!r}] -> {value.id} '
                                 f'resolves to {actual}')
    assert not wrong, 'names resolving wrongly:\n  ' + '\n  '.join(wrong)


def test_the_dark_palettes_actually_use_some_of_them():
    """Guard the guard, again. If the palettes stopped referencing the register
    entirely, the sweep above would find no literals and pass -- for the wrong
    reason."""
    used = set()
    for node in _dicts(DARK_DICTS).values():
        for value in node.values:
            if isinstance(value, ast.Name) and value.id in REGISTERED:
                used.add(value.id)
    assert len(used) >= 3, (
        f'the dark palettes reference only {sorted(used)} of the register. '
        f'The literal sweep passes trivially when nothing is referenced.')


# --------------------------------------------------------------- what did NOT

def test_the_light_palettes_were_left_alone():
    """This pass is the DARK half, on the register's stated order. The light
    ladder is unruled -- nine surfaces inside three grid steps, and which of
    them are real distinctions is a judgement the register has not made. If a
    later pass wires light, this test is the thing that has to be deleted on
    purpose."""
    named = []
    for dict_name, node in _dicts(LIGHT_DICTS).items():
        for key, value in zip(node.keys, node.values):
            if isinstance(value, ast.Name) and value.id in REGISTERED:
                named.append(f'{dict_name}[{key.value!r}] -> {value.id}')
    assert not named, (
        'the light palettes now reference the register:\n  ' + '\n  '.join(named)
        + '\n\nThat is the light half, and it is not ruled yet.')
