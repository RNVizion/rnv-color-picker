"""Derived values: a colour that is a named colour AT AN ALPHA.

A colour here used to be one of two things -- a name, or a literal -- and this
file adds the third the application always had and never declared.
rgba(51, 51, 51, 100) is not a colour beside APP_BORDER; it IS APP_BORDER at
alpha 100, and until 2026-09-25 nothing related the two. Now it is written
translucent(APP_BORDER, SCROLLBAR_BG_ALPHA), and a change to APP_BORDER
reaches it -- in the palette, and in every stylesheet that paints it.

THE IMAGE SCROLLBAR NEVER READ THE PALETTE. ThemeManager.SCROLLBAR_IMAGE was a
fixed string, the one sheet in the file "not built from theme dict", so the
main window's image scrollbar painted its own literals whatever the palette
said. Two rulings stopped at that string: RNV-COLLAPSE-505050 (2026-09-02) left
the handle #505050, and the gold hover (2026-09-12) left it grey --
rgba(100, 100, 100, 200) while scrollbar_handle_hover said BRAND_GOLD. The
sheet is built from IMAGE_MODE_COLORS now, same geometry, and both rulings
reach it.

WHAT MOVES A PIXEL: TWO THINGS, BOTH RULED. The image scrollbar handle leaves
#505050 for GREY_44 at the same alpha, 150; and the main window's image
scrollbar hover turns gold, completing the 2026-09-12 ruling. Everything else
keeps its colour and its alpha byte. test_nothing_moved_that_was_not_ruled
holds each value to the constant and the byte it is made of.
"""
from __future__ import annotations

import ast
import pathlib
import re

from utils import config as colors
from utils.config import (DARK_THEME_COLORS as DARK,
                          LIGHT_THEME_COLORS as LIGHT,
                          IMAGE_MODE_COLORS as IMAGE,
                          ThemeManager,
                          translucent)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "utils" / "config.py"
PALETTES = {"DARK_THEME_COLORS": DARK, "LIGHT_THEME_COLORS": LIGHT,
            "IMAGE_MODE_COLORS": IMAGE}

#: constant -> the byte. Each is the alpha the literal it replaced already
#: carried; all were integers or the "ED" byte, so nothing rounds.
ALPHAS = {
    "IMAGE_OVERLAY_ALPHA": 0xED,
    "IMAGE_CHECKBOX_ALPHA": 0x64,
    "SCROLLBAR_BG_ALPHA": 0x64,
    "SCROLLBAR_HANDLE_ALPHA": 0x96,
    "IMAGE_MENU_ALPHA": 0xC8,
}

#: What each derived value is MADE OF: the constant its colour comes from, and
#: its alpha byte. By NAME, not by hex -- see test_nothing_moved_that_was_not_ruled.
MADE_OF = {
    "APP_WINDOW_OVERLAY": ("TRUE_BLACK", 0xED),
    "APP_PANEL_OVERLAY": ("BRAND_BLACK", 0xED),
    "IMAGE_MENU_BG": ("TRUE_BLACK", 0xC8),
    "IMAGE_MODE_COLORS['checkbox_bg']": ("TRUE_BLACK", 0x64),
    "IMAGE_MODE_COLORS['scrollbar_bg']": ("APP_BORDER", 0x64),
    "IMAGE_MODE_COLORS['scrollbar_handle']": ("GREY_44", 0x96),  # ruled
}

#: Diagnostic, and so excluded by rule: the debug overlay must read on any
#: window whatever the theme, so it follows no brand row.
EXCLUDED = {"DEBUG_BG"}

_HEX8 = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{6})$")
_COMPOSED = re.compile(r"#[0-9a-fA-F]{8}\b|\brgba\(\s*\d{1,3}\s*,\s*\d{1,3}"
                       r"\s*,\s*\d{1,3}\s*,\s*[0-9]*\.?[0-9]+\s*\)")
_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_FUNC = re.compile(r"\brgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})"
                   r"\s*(?:,\s*[0-9]*\.?[0-9]+\s*)?\)")
SKIP_DIRS = {".git", "tests", "build", "dist", ".venv", "venv", "__pycache__"}


def decompose(value: str) -> tuple[str, int] | None:
    """(base '#rrggbb', alpha byte) -- taken apart, never rebuilt, so a fault
    in translucent() cannot also be a fault here."""
    m = _HEX8.match(value)
    if m:
        return "#" + m.group(2).lower(), int(m.group(1), 16)
    return None


def _parts_of(spelled: str) -> tuple[str, int]:
    """(base, alpha byte) for any composed spelling, with Qt's own reading of
    a fractional alpha: it TRUNCATES, so 0.3 is 76."""
    if spelled.startswith("#"):
        return "#" + spelled[3:].lower(), int(spelled[1:3], 16)
    numbers = re.findall(r"[0-9]*\.?[0-9]+", spelled)
    r, g, b = (int(x) for x in numbers[:3])
    a = numbers[3]
    return "#%02x%02x%02x" % (r, g, b), (int(float(a) * 255) if "." in a
                                         else int(a))


def colours_in(text: str) -> set[str]:
    """Every colour in a string, as #rrggbb. #AARRGGBB is alpha FIRST."""
    found = set()
    for m in _HEX.finditer(text):
        h = m.group(0)[1:].lower()
        h = h[2:] if len(h) == 8 else ("".join(c * 2 for c in h) if len(h) == 3 else h)
        found.add("#" + h)
    for m in _FUNC.finditer(text):
        channels = [int(g) for g in m.groups()]
        if all(c <= 255 for c in channels):
            found.add("#%02x%02x%02x" % tuple(channels))
    return found


def _bare_strings(tree: ast.AST) -> set[int]:
    """Docstrings and every other string nobody evaluates -- mentions."""
    bare = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            for st in body:
                if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):
                    bare.add(id(st.value))
    return bare


def _sources():
    """Application source: not tests, not a root test suite, not a delivery
    script. Yields (relative path, parsed tree). BOM-aware: several files in
    this repository carry one, and ast.parse refuses a U+FEFF it is handed."""
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        if len(rel.parts) == 1 and rel.name.startswith(("test_", "up")):
            continue
        text = path.read_bytes().decode("utf-8-sig", errors="replace")
        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:
            continue
        yield rel, ast.parse(text)


def _derived():
    """(where, call node, resolved value) for every translucent() call at
    module level in utils/config.py -- a constant, or a value in a dict."""
    tree = ast.parse(SRC.read_text(encoding="utf-8-sig"))
    out = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        name = getattr(target, "id", None)
        if name is None or node.value is None:
            continue
        if isinstance(node.value, ast.Call):
            if getattr(node.value.func, "id", None) == "translucent":
                out.append((name, node.value, getattr(colors, name)))
        elif isinstance(node.value, ast.Dict):
            live = getattr(colors, name)
            for key, value in zip(node.value.keys, node.value.values):
                if key is None:          # a **splat, not an entry
                    continue
                if (isinstance(value, ast.Call)
                        and getattr(value.func, "id", None) == "translucent"):
                    out.append((f"{name}[{key.value!r}]", value, live[key.value]))
    return out


# ------------------------------------------------------------ guard the guard

def test_translucent_composes_alpha_first():
    """#AARRGGBB, not #RRGGBBAA. Taking the wrong end gives a real colour and
    the wrong one, which is the failure that does not look like a failure.
    Lower case, whatever case it is given: RNV-LOWER-EIGHT."""
    assert translucent("#1a1a1a", 0xED) == "#ed1a1a1a"
    assert translucent("0A0A0A", 0xED) == "#ed0a0a0a"
    assert decompose(translucent("#d2bc93", 0x33)) == ("#d2bc93", 0x33)


def test_translucent_refuses_what_it_cannot_compose():
    for bad in (-1, 256, 999, 0.5, True):
        try:
            translucent("#1a1a1a", bad)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"translucent took alpha {bad!r}")
    for bad in ("#1a1a1", "#1a1a1a1a", "nonsense", "#gggggg"):
        try:
            translucent(bad, 0xED)
        except ValueError:
            pass
        else:
            raise AssertionError(f"translucent took base {bad!r}")


def test_the_alphas_are_the_declared_bytes():
    for name, byte in ALPHAS.items():
        assert hasattr(colors, name), f"utils.config has no {name}"
        value = getattr(colors, name)
        assert type(value) is int, f"{name} is {value!r}, not an int byte"
        assert value == byte, f"{name} is {value:#x}, declared {byte:#x}"


def test_the_derivation_sweep_is_looking():
    """Every check below iterates _derived(). If it came back empty they
    would all pass over nothing."""
    where = {w for w, _c, _v in _derived()}
    assert set(MADE_OF) <= where, sorted(set(MADE_OF) - where)


# ----------------------------------------------------------- the derivations

def test_every_derived_value_names_constants_that_exist():
    """translucent(BASE, ALPHA) where both are names: a literal in either
    position is the thing this round removed."""
    bad = []
    for where, call, _value in _derived():
        if len(call.args) != 2 or call.keywords:
            bad.append(f"{where}: {ast.unparse(call)} is not (BASE, ALPHA)")
            continue
        base, alpha = call.args
        for pos, arg in (("base", base), ("alpha", alpha)):
            if not isinstance(arg, ast.Name):
                bad.append(f"{where}: the {pos} is {ast.unparse(arg)}, not a name")
            elif not hasattr(colors, arg.id):
                bad.append(f"{where}: the {pos} names {arg.id}, which "
                           f"utils.config does not define")
        if isinstance(base, ast.Name) and hasattr(colors, base.id):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(getattr(colors, base.id))):
                bad.append(f"{where}: the base {base.id} is not a six-digit colour")
        if isinstance(alpha, ast.Name) and alpha.id not in ALPHAS:
            bad.append(f"{where}: the alpha {alpha.id} is not a declared "
                       f"composite alpha")
    assert not bad, "derived values that do not derive:\n  " + "\n  ".join(bad)


def test_every_derived_value_decomposes_to_its_base_and_its_alpha():
    """TAKEN APART, not rebuilt -- the entry IS translucent()'s output, so
    recomputing it would compare the call with itself."""
    wrong = []
    for where, call, value in _derived():
        base, alpha = call.args
        parts = decompose(value)
        want = (getattr(colors, base.id).lower(), getattr(colors, alpha.id))
        if parts != want:
            wrong.append(f"{where} is {value!r}, which takes apart to {parts}, "
                         f"not {base.id}/{alpha.id} {want}")
    assert not wrong, "derived values that do not match:\n  " + "\n  ".join(wrong)


def test_no_composed_literal_is_left_in_the_application():
    """The completeness half. Every EVALUATED string in the application's own
    source that spells a named colour at an alpha. Docstrings are mentions;
    alpha 0 is not a colour; a base no constant names has no row to follow;
    and the diagnostic overlay is excluded by rule."""
    named = {v.lower() for n, v in vars(colors).items()
             if n.isupper() and isinstance(v, str)
             and re.fullmatch(r"#[0-9a-fA-F]{6}", v)}
    strays, files = [], 0
    for rel, tree in _sources():
        files += 1
        bare = _bare_strings(tree)
        excluded = set()
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                t = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if getattr(t, "id", None) in EXCLUDED:
                    excluded |= {id(n) for n in ast.walk(node)}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if id(node) in bare or id(node) in excluded:
                continue
            for spelled in _COMPOSED.findall(node.value):
                base, alpha = _parts_of(spelled)
                if alpha and base in named:
                    strays.append(f"{rel}:{node.lineno}  {spelled}")
    # 36 application files on 2026-09-25; below 25 the walk has lost a
    # package, not a file.
    assert files >= 25, f"only {files} files swept -- the walk has gone blind"
    assert not strays, ("composed values still written out rather than "
                        "derived:\n  " + "\n  ".join(strays))


def test_the_diagnostic_overlay_stays_outside_the_brand():
    """The exclusion rule, asserted rather than assumed: DEBUG_BG must read on
    any window whatever the theme, so it follows no register row."""
    tree = ast.parse(SRC.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if (isinstance(node, (ast.Assign, ast.AnnAssign))
                and getattr(node.targets[0] if isinstance(node, ast.Assign)
                            else node.target, "id", None) == "DEBUG_BG"):
            assert isinstance(node.value, ast.Constant), (
                "DEBUG_BG is computed from the application's own values; a "
                "diagnostic overlay must not follow the brand")
            return
    raise AssertionError("utils.config has no DEBUG_BG")


# ------------------------------------------------ the sheet that ignored it

def test_the_image_scrollbar_sheet_is_built_from_the_palette():
    """SCROLLBAR_IMAGE paints the main window's image scrollbar. It is read
    from IMAGE_MODE_COLORS now, so the rulings that land in the palette reach
    the screen: the handle is GREY_44, and the hover is the gold."""
    sheet = ThemeManager.SCROLLBAR_IMAGE
    handle = re.findall(r"QScrollBar::handle:vertical\s*\{\s*background-color:\s*([^;]+);", sheet)
    hover = re.findall(r"QScrollBar::handle:vertical:hover\s*\{\s*background-color:\s*([^;]+);", sheet)
    groove = re.findall(r"QScrollBar:vertical\s*\{\s*background-color:\s*([^;]+);", sheet)
    assert handle == [IMAGE["scrollbar_handle"]], handle
    assert hover == [IMAGE["scrollbar_handle_hover"]] == [colors.BRAND_GOLD], hover
    assert groove == [IMAGE["scrollbar_bg"]], groove
    # and it carries no colour of its own any more
    literals = [c for c in colours_in(sheet)
                if c not in {decompose(IMAGE["scrollbar_bg"])[0],
                             decompose(IMAGE["scrollbar_handle"])[0],
                             colors.BRAND_GOLD}]
    assert not literals, f"SCROLLBAR_IMAGE still spells its own colours: {literals}"


# --------------------------------------------------- what moved, and what not

def test_the_scrollbar_handle_is_grey_44_at_150():
    """RNV-COLLAPSE-505050, closed here 2026-09-25."""
    assert decompose(IMAGE["scrollbar_handle"]) == (
        colors.GREY_44, colors.SCROLLBAR_HANDLE_ALPHA)
    assert colors.SCROLLBAR_HANDLE_ALPHA == 150


def test_nothing_moved_that_was_not_ruled():
    """Each derived value, held to what it is MADE OF: the constant its colour
    comes from and its alpha byte.

    BY NAME, NOT BY HEX, and that is the point of the round. A register move
    is meant to pass straight through these values; a test that pinned
    '#333333' would fail the first time one did and ask a person to edit it
    by hand -- the job derivation exists to remove. What this DOES catch is a
    value quietly re-made from something else, which the decomposition check
    accepts as long as source and value agree with each other.

    The byte-for-byte before-and-after was checked once, by the delivery
    script, against the edited module before it was written."""
    live = {where: value for where, _call, value in _derived()}
    for where, (base, alpha) in MADE_OF.items():
        assert where in live, f"{where} is no longer derived"
        assert decompose(live[where]) == (getattr(colors, base).lower(), alpha), (
            f"{where} is {live[where]}, which is not {base} at {alpha:#04x}")
    # RNV-NAMED-AND-USED (2026-10-04): scroll_area_bg held it too, and image
    # mode never read that key; it comes through the splat now, unread.
    assert IMAGE["window_bg"] == colors.APP_WINDOW_OVERLAY
    assert IMAGE["scroll_area_bg"] == DARK["scroll_area_bg"]
    assert IMAGE["zoom_label_bg"] == colors.APP_PANEL_OVERLAY


def test_the_collapsed_value_is_gone_in_every_spelling():
    """#505050 in any string spelling -- #rgb, #rrggbb, #aarrggbb, rgb(),
    rgba() -- or as integers in a tuple or a QColor call. It survived here for
    three weeks after its ruling because every sweep compared six-digit hex."""
    found = []
    for rel, tree in _sources():
        bare = _bare_strings(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in bare and "#505050" in colours_in(node.value)):
                found.append(f"{rel}:{node.lineno}  {node.value[:40]!r}")
            values = None
            if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) in (3, 4):
                values = node.elts
            elif isinstance(node, ast.Call) and len(node.args) >= 3 and (
                    getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    ) in ("QColor", "fromRgb", "QPen", "QBrush"):
                values = node.args
            if values:
                ints = tuple(v.value for v in values[:3]
                             if isinstance(v, ast.Constant) and type(v.value) is int)
                if ints == (80, 80, 80):
                    found.append(f"{rel}:{node.lineno}  (80, 80, 80)")
    assert not found, "#505050 is still here:\n  " + "\n  ".join(found)
    assert colours_in("rgba(80, 80, 80, 150)") == {"#505050"}, "the decoder is blind"

# RNV-DERIVE-ALPHA


# ------------------------------------------------ eight-digit hex, lower case

LOWER8_MODULES = ('utils.config',)
#: Found when this was written; below the floor, the sweep has gone blind.
#: 10 until RNV-NAMED-AND-USED (2026-10-04), when image mode's unread
#: scroll_area_bg override went. 9 until 2026-10-05, when the frame colour
#: only an uncalled stylesheet function read went.
LOWER8_FLOOR = 8
LOWER8_FILES = 25


def _lower8_values():
    """(where, value) for every eight-digit hex string the colour modules
    build -- their constants, the dicts they hold, and their classes' dicts
    -- as they EVALUATE, which is what a derived value is."""
    import importlib

    def walk(where, value):
        if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{8}", value):
            yield where, value
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from walk(f"{where}[{key!r}]", item)

    for name in LOWER8_MODULES:
        module = importlib.import_module(name)
        for attr, value in vars(module).items():
            if attr.startswith("__"):
                continue
            if isinstance(value, type) and value.__module__ == name:
                for cattr, cvalue in vars(value).items():
                    if not cattr.startswith("__"):
                        yield from walk(f"{name}.{attr}.{cattr}", cvalue)
            else:
                yield from walk(f"{name}.{attr}", value)


def _lower8_trees():
    """Application source: not tests, not a root test suite, not a delivery
    script. BOM-aware."""
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if any(p in {".git", "tests", "snapshots", "build", "dist", ".venv",
                     "venv", "__pycache__"} for p in rel.parts):
            continue
        if len(rel.parts) == 1 and rel.name.startswith(("test_", "up")):
            continue
        text = path.read_bytes().decode("utf-8-sig", errors="replace")
        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:
            continue
        yield rel, ast.parse(text)


def test_eight_digit_hex_is_lower_case():
    """RNV-LOWER-EIGHT, 2026-09-25. The register writes hex in lower case --
    Notation, ruled 2026-08-15, Brand Book decision #19 -- and on 2026-09-25
    Chris ruled that eight digits are hex too: #ed1a1a1a, never #ED1A1A1A.
    Qt reads either case, so no pixel moved when this application's helper
    changed.

    Both halves: every eight-digit value the application BUILDS, as its
    colour modules evaluate, and every eight-digit literal it WRITES in code.
    Docstrings are prose, and a sentence that names an upper-case value as
    history keeps its case."""
    built = list(_lower8_values())
    assert len(built) >= LOWER8_FLOOR, (
        f"only {len(built)} eight-digit values found; the sweep has gone blind")
    upper = [f"{where} = {value}" for where, value in built
             if value != value.lower()]
    written, files = [], 0
    for rel, tree in _lower8_trees():
        files += 1
        bare = _bare_strings(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in bare):
                for hex8 in re.findall(r"#[0-9a-fA-F]{8}\b", node.value):
                    if hex8 != hex8.lower():
                        written.append(f"{rel}:{node.lineno}  {hex8}")
    assert files >= LOWER8_FILES, f"only {files} files swept"
    assert not upper, "built in upper case:\n  " + "\n  ".join(upper)
    assert not written, "written in upper case:\n  " + "\n  ".join(written)


# ------------------------------------------------- colours spelled in integers

import importlib as _importlib

#: Where the derived constants live, and where their bases and alphas live.
TUPLE_HOME = 'utils/config.py'
TUPLE_HOME_MODULE = 'utils.config'
TUPLE_BASES_MODULE = 'utils.config'
#: Each derived constant, by NAME: (helper, base, alpha or None). A register
#: move passes straight through; a value re-made from something else fails.
TUPLES_MADE_OF = {'OVERLAY_BLACK_LIGHT': ('translucent_tuple', 'TRUE_BLACK', 'OVERLAY_LIGHT_ALPHA'), 'OVERLAY_BLACK_MEDIUM': ('translucent_tuple', 'TRUE_BLACK', 'OVERLAY_MEDIUM_ALPHA'), 'OVERLAY_BLACK_HEAVY': ('translucent_tuple', 'TRUE_BLACK', 'OVERLAY_HEAVY_ALPHA')}
#: The alpha bytes behind them, each the one its literal already carried.
TUPLE_ALPHAS = {'OVERLAY_LIGHT_ALPHA': 50, 'OVERLAY_MEDIUM_ALPHA': 75, 'OVERLAY_HEAVY_ALPHA': 180}
#: Module- and class-level constants spelled in integers ON PURPOSE -- data a
#: person starts from, not a brand element -- with the reason.
INT_DATA = {}
TUPLE_FILES = 25
#: The call each derived constant is wrapped in, if any.
_WRAP = None


def _int_spelled(tree):
    """(name, #rrggbb, alpha) for every module- or class-level constant whose
    value spells a colour in integers: a tuple or list of three or four int
    literals, or QColor/QPen/QBrush called with them. Locals inside functions
    are state, not constants, and are not read."""
    bodies = [tree.body] + [n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for body in bodies:
        for statement in body:
            if (not isinstance(statement, (ast.Assign, ast.AnnAssign))
                    or statement.value is None):
                continue
            target = (statement.targets[0] if isinstance(statement, ast.Assign)
                      else statement.target)
            name, value = getattr(target, "id", None), statement.value
            if isinstance(value, (ast.Tuple, ast.List)):
                elts = value.elts
            elif isinstance(value, ast.Call) and (
                    getattr(value.func, "id", None) or getattr(value.func, "attr", None)
                    ) in ("QColor", "fromRgb", "QPen", "QBrush"):
                elts = value.args
            else:
                continue
            if name is None or len(elts) not in (3, 4):
                continue
            ints = [e.value for e in elts
                    if isinstance(e, ast.Constant) and type(e.value) is int]
            if len(ints) != len(elts) or not all(0 <= i <= 255 for i in ints):
                continue
            yield (name, "#%02x%02x%02x" % tuple(ints[:3]),
                   ints[3] if len(ints) == 4 else 255)


def _tuple_trees():
    """Application source: not tests, not a root test suite, not a delivery
    script. BOM-aware."""
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if any(p in {".git", "tests", "snapshots", "build", "dist", ".venv",
                     "venv", "__pycache__"} for p in rel.parts):
            continue
        if len(rel.parts) == 1 and rel.name.startswith(("test_", "up")):
            continue
        text = path.read_bytes().decode("utf-8-sig", errors="replace")
        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:
            continue
        yield rel, ast.parse(text)


def _rgb_of(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _as_rgba(value):
    """A tuple as it is; a QColor as its channels."""
    if hasattr(value, "alpha") and callable(value.alpha):
        return (value.red(), value.green(), value.blue(), value.alpha())
    return tuple(value)


def test_the_integer_sweep_reads_both_notations():
    """Guard the guard: a tuple and a QColor at module or class level are
    read; a local inside a function is not."""
    probe = ast.parse("A = (0, 0, 0, 50)\n"
                      "class K:\n    B = QColor(68, 68, 68)\n"
                      "def f():\n    c = (0, 0, 0)\n")
    assert sorted(_int_spelled(probe)) == [("A", "#000000", 50), ("B", "#444444", 255)]


def test_every_tuple_constant_is_derived_by_name():
    """RNV-TUPLE-ROUND, 2026-09-26. A colour spelled in integers is a colour
    every string sweep in the fleet was blind to, and #505050 sat in two of
    them for three weeks after it was ruled away. Each constant here is now
    its helper called on a named base and a named alpha, and it evaluates to
    exactly that pair -- held BY NAME, so a register move passes through."""
    tree = ast.parse((ROOT / TUPLE_HOME).read_text(encoding="utf-8-sig"))
    values = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            t = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if getattr(t, "id", None):
                values[t.id] = node.value
    home = _importlib.import_module(TUPLE_HOME_MODULE)
    bases = _importlib.import_module(TUPLE_BASES_MODULE)
    assert TUPLES_MADE_OF, "nothing to check"
    for name, (helper, base, alpha) in TUPLES_MADE_OF.items():
        call = values.get(name)
        assert call is not None, f"{name} is gone from {TUPLE_HOME}"
        if _WRAP:
            assert (isinstance(call, ast.Call)
                    and getattr(call.func, "id", None) == _WRAP
                    and len(call.args) == 1), (
                f"{name} is not {_WRAP}(...): {ast.unparse(call)}")
            call = call.args[0]
        want_names = [base] + ([alpha] if alpha else [])
        assert (isinstance(call, ast.Call) and getattr(call.func, "id", None) == helper
                and [getattr(a, "id", None) for a in call.args] == want_names
                and not call.keywords), (
            f"{name} is {ast.unparse(call)}, not {helper}({', '.join(want_names)})")
        live = _as_rgba(getattr(home, name))
        want = _rgb_of(getattr(bases, base)) + ((TUPLE_ALPHAS[alpha],) if alpha else ())
        if len(live) == 4 and len(want) == 3:
            want += (255,)
        assert live == want, f"{name} is {live}; made of {want_names} it is {want}"


def test_the_tuple_alphas_are_the_declared_bytes():
    bases = _importlib.import_module(TUPLE_BASES_MODULE)
    for name, byte in TUPLE_ALPHAS.items():
        value = getattr(bases, name)
        assert type(value) is int and value == byte, (
            f"{name} is {value!r}, declared {byte:#x}")


def test_no_named_colour_is_spelled_in_integers():
    """The completeness half. Every module- or class-level constant in the
    application that spells a NAMED colour in integers. Alpha 0 draws no
    colour; a base no constant names has no row to follow; and INT_DATA is
    data a person starts from, each with its reason."""
    bases = _importlib.import_module(TUPLE_BASES_MODULE)
    named = {v.lower() for n, v in vars(bases).items()
             if n.isupper() and isinstance(v, str)
             and re.fullmatch(r"#[0-9a-fA-F]{6}", v)}
    strays, files = [], 0
    for rel, tree in _tuple_trees():
        files += 1
        for name, rgb, alpha in _int_spelled(tree):
            if name in INT_DATA or alpha == 0 or rgb not in named:
                continue
            strays.append(f"{rel}: {name} = {rgb} at alpha {alpha}")
    assert files >= TUPLE_FILES, f"only {files} files swept -- the walk has gone blind"
    assert not strays, ("named colours still spelled in integers, where no "
                        "register move reaches them:\n  " + "\n  ".join(strays))


# RNV-CANVAS-OVERLAY-GONE
# ------------------------------------------------- the overlay nothing read

def test_the_unread_canvas_overlay_stays_removed():
    """RNV-CANVAS-OVERLAY-GONE, ruling 5 of 2026-09-26. APP_CANVAS_OVERLAY --
    APP_CANVAS at IMAGE_OVERLAY_ALPHA, #ed0a0a0a -- was image mode's
    image_viewer_bg, and nothing read it: the viewer reads image_viewer_bg
    only outside image mode, and in image mode paints OVERLAY_BLACK_MEDIUM.
    A render set it to #ff00ff. No pixel changed in 171 captures of the main
    window, Settings and About in all three modes, and no text changed in
    1,635 stylesheet and palette entries, while a control that moved dark's
    image_viewer_bg changed 11 captures and 12 entries. So the constant went,
    with its provenance entry and the override. Image mode inherits dark's
    image_viewer_bg through the splat, and does not read it.

    Gone from the module and named nowhere in the application. An override
    brought back is a colour on no element: decide it, do not inherit it."""
    assert not hasattr(colors, "APP_CANVAS_OVERLAY"), "APP_CANVAS_OVERLAY is back"
    assert "APP_CANVAS_OVERLAY" not in colors.APP_PROVENANCE
    assert IMAGE["image_viewer_bg"] == DARK["image_viewer_bg"], (
        "image mode overrides image_viewer_bg again, and image mode never reads it")
    sources = list(_sources())
    assert any(rel.as_posix() == "utils/config.py" for rel, _ in sources), (
        "the sweep cannot see utils/config.py, so it proves nothing")
    named = [f"{rel}:{node.lineno}" for rel, tree in sources for node in ast.walk(tree)
             if (isinstance(node, ast.Name) and node.id == "APP_CANVAS_OVERLAY")
             or (isinstance(node, ast.Constant) and node.value == "APP_CANVAS_OVERLAY")]
    assert not named, f"APP_CANVAS_OVERLAY is named again: {named}"


def test_image_mode_still_does_not_read_image_viewer_bg():
    """The premise the removal stands on, held in the source: every read of
    image_viewer_bg in the application sits in the branch of an `if is_image`
    that is NOT image mode. If image mode starts reading the key it gets
    dark's opaque canvas, so an image value has to be decided first."""
    reads = []
    for rel, tree in _sources():
        parents = {child: node for node in ast.walk(tree)
                   for child in ast.iter_child_nodes(node)}
        for n in ast.walk(tree):
            if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                    and n.slice.value == "image_viewer_bg"):
                reads.append(f"{rel}:{n.lineno}")
                child, node = n, parents.get(n)
                while node is not None and not (isinstance(node, ast.If)
                                                and ast.unparse(node.test) == "is_image"):
                    child, node = node, parents.get(node)
                assert node is not None and any(child is s for s in node.orelse), (
                    f"{rel}:{n.lineno} reads image_viewer_bg where image mode can reach it")
    assert reads, "no read of image_viewer_bg was found, so this proves nothing"
