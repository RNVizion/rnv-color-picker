"""
tests/test_named_and_used.py
============================
RNV-NAMED-AND-USED, 2026-10-04. Every colour in the application is named,
and every name is used.

Ruled 2026-10-04: "As long as a color exist in the app it should be named
and used no hardcoded or pointless literals should exist, only literals with
a purpose, like data or comparison are allowed. Colors are name for swap
ability and alignment."

In this application that removed 17 palette keys no mode read, image mode's
scroll_area_bg override, and six constants only tests held; and it named the
selection box's yellow, the cache's black and white, the paper and ink of
the exported palette sheet, and the channels an entry with no rgb is read as.

Three sweeps hold it, each over the application's own source:

1. NAMED. No colour is written out in the code. Every spelling is read: hex,
   rgb() and rgba(), a CSS colour name, QColor built from numbers, a Qt
   global colour, a tuple or a list of channels, an alpha set as a number.
   A colour is written once, in the colour module, under a name; everything
   else reads the name. What stays written is DATA, each entry with its
   reason, and the sweep fails for an entry that no longer matches anything.
2. USED, the palettes. Every colour a palette holds is looked up by key
   somewhere in the application.
3. USED, the constants. Every colour the colour module names is read
   somewhere in the application: by the palettes, by another constant, or by
   the code.

Clear is not a colour: 'transparent', alpha 0 and Qt's transparent are how a
widget is told to paint nothing, and are left as written.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Where this application writes its colours: the one place a literal belongs.
COLOUR_MODULES = ("utils/config.py",)
#: Where its palettes are written: their own keys are not lookups.
PALETTE_MODULES = COLOUR_MODULES
SKIP_DIRS = {"tests", "build", "dist", "docs", "resources", "scripts", "snapshots", "__pycache__"}

from utils.config import DARK_THEME_COLORS, IMAGE_MODE_COLORS, LIGHT_THEME_COLORS  # noqa: E402

PALETTES = {"DARK_THEME_COLORS": DARK_THEME_COLORS, "LIGHT_THEME_COLORS": LIGHT_THEME_COLORS,
            "IMAGE_MODE_COLORS": IMAGE_MODE_COLORS}

#: Below these a sweep has gone blind.
MIN_FILES = 30
MIN_ENTRIES = 150
MIN_CONSTANTS = 40

#: What stays written, and why: (file, literal) -> the reason. Data a person
#: starts from or a conversion falls back to is not the application's look,
#: and a brand move should not change it.
DATA = {
    ("core/color_math.py", "(0, 0, 0)"):
        "what safe_rgb() hands back for channels it cannot use: a fallback, as data",
    ("core/screen_color_picker.py", "(0, 0, 0)"):
        "the colour under the cursor before the first reading: where the picker starts",
    ("ui/color_swatch_widget.py", "(0, 0, 0)"):
        "a swatch built with no colour given, and its hue, saturation and lightness: defaults, as data",
    ("utils/settings_manager.py", "[200, 200, 200]"):
        "the stored default of a preference, default_slot_color: data in the settings file, not the look",
}

CSS_NAMES = frozenset("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue
darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink
deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold
goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush
lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey
lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime
limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise
palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow
springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
yellowgreen""".split())
QT_GLOBAL = frozenset({"white", "black", "red", "darkRed", "green", "darkGreen", "blue", "darkBlue", "cyan",
                       "darkCyan", "magenta", "darkMagenta", "yellow", "darkYellow", "gray", "darkGray",
                       "lightGray"})
HEX = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_])")
FUNC = re.compile(r"\b(?:rgba?|hsla?|hsva?)\(\s*[0-9.]+%?\s*,[^)]*\)", re.I)
PROP = re.compile(r"(?:^|[;{\s\"'])((?:[a-z-]*color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-[a-z]+)*|"
                  r"fill|stroke))\s*[:=]\s*([^;{}<>]*)", re.I)
WORD = re.compile(r"(?<![\w#.-])([a-z]+)(?![\w(-])", re.I)
NOT_A_COLOUR = re.compile(r"margin|padding|spacing|size|offset|geometry|rect|pos|range|version|ratio|weight", re.I)
A_COLOUR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})|rgba?\([^)]*\)")


def _sources():
    """(repo-relative path, text) of every file of the application: not the
    tests, not a delivery script, not what a build leaves behind."""
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        parts = rel.split("/")
        if any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        if len(parts) == 1 and (parts[0].startswith(("test_", "up", "conftest", "run_tests"))):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:
            continue
        yield rel, text


def _prose(tree) -> set:
    """ids of the strings that are prose: docstrings and bare string statements."""
    return {id(n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}


def _clear(literal: str) -> bool:
    """rgba(..., 0) and QColor(..., 0): clear, not a colour."""
    nums = re.findall(r"[0-9.]+", literal)
    return len(nums) == 4 and float(nums[3]) == 0


def _written(rel: str, text: str) -> list:
    """(line, kind, literal) for every colour this file writes out."""
    tree = ast.parse(text)
    prose, out = _prose(tree), []
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[id(child)] = node

    def named_like(node) -> str:
        """The name a value is given: its assignment target, keyword or parameter."""
        up = parent.get(id(node))
        while isinstance(up, (ast.IfExp, ast.BoolOp, ast.Tuple, ast.List)):
            node, up = up, parent.get(id(up))
        if isinstance(up, ast.keyword):
            return up.arg or ""
        if isinstance(up, (ast.Assign, ast.AnnAssign)):
            target = up.targets[0] if isinstance(up, ast.Assign) else up.target
            return ast.unparse(target)
        if isinstance(up, ast.arguments):
            both = up.posonlyargs + up.args
            if node in up.defaults:
                return both[len(both) - len(up.defaults) + up.defaults.index(node)].arg
            if node in up.kw_defaults:
                return up.kwonlyargs[up.kw_defaults.index(node)].arg
        return ""

    def a_name_on_its_own(node, up) -> bool:
        """A CSS colour name that is the whole string, where a colour is given:
        handed to a call, chosen by an if, assigned, returned, a default or a
        value in a table. A key, an index and a comparison are not a colour
        given to anything."""
        s = node.value
        if isinstance(up, (ast.Call, ast.keyword, ast.IfExp)):
            return s.lower() in CSS_NAMES              # Qt and PIL read a name in any case
        if s not in CSS_NAMES:
            return False
        if isinstance(up, ast.Dict):
            return any(v is node for v in up.values)
        if isinstance(up, ast.arguments):
            return node in up.defaults or node in up.kw_defaults
        return isinstance(up, (ast.Assign, ast.AnnAssign, ast.Return)) and up.value is node

    for node in ast.walk(tree):
        up = parent.get(id(node))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            s = node.value
            for m in HEX.finditer(s):
                out.append((node.lineno, "hex", m.group(0)))
            for m in FUNC.finditer(s):
                if not _clear(m.group(0)):
                    out.append((node.lineno, "func", " ".join(m.group(0).split())))
            for m in PROP.finditer(s):
                for w in WORD.finditer(m.group(2)):
                    if w.group(1).lower() in CSS_NAMES:
                        out.append((node.lineno, "name", f"{m.group(1).lower()}: {w.group(1)}"))
            # a colour name on its own: QColor("yellow"), fill="white", ink = "black"
            if a_name_on_its_own(node, up):
                out.append((node.lineno, "name", s))
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", None))
            if name in ("QColor", "fromRgb", "fromRgbF", "qRgb", "qRgba") and node.args \
                    and all(isinstance(a, ast.Constant) and not isinstance(a.value, str) for a in node.args):
                literal = ast.unparse(node)
                if not _clear(literal):
                    out.append((node.lineno, "qcolor", literal))
            # an alpha set as a number: colour.setAlpha(171). Clear and solid are not a choice of alpha.
            elif name in ("setAlpha", "setAlphaF") and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) \
                    and type(node.args[0].value) in (int, float) \
                    and node.args[0].value not in ((0, 255) if name == "setAlpha" else (0, 1)):
                out.append((node.lineno, "alpha", f"{name}({node.args[0].value!r})"))
        elif isinstance(node, ast.Attribute) and node.attr in QT_GLOBAL \
                and ast.unparse(node.value) in ("Qt.GlobalColor", "Qt", "QtCore.Qt.GlobalColor", "QtCore.Qt"):
            out.append((node.lineno, "global", ast.unparse(node)))
        elif isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) in (3, 4) and all(
                isinstance(e, ast.Constant) and type(e.value) is int and 0 <= e.value <= 255 for e in node.elts):
            if (isinstance(up, (ast.comprehension, ast.For)) and up.iter is node) \
                    or isinstance(up, (ast.Compare, ast.Subscript)):
                continue                                   # an index, a membership or a comparison
            if isinstance(up, ast.Call) and getattr(up.func, "id", getattr(up.func, "attr", "")) in QCOLOR_CALLS:
                continue                                   # counted with its QColor(...)
            if len(node.elts) == 4 and node.elts[3].value == 0:
                continue                                   # clear
            if NOT_A_COLOUR.search(named_like(node)):
                continue
            out.append((node.lineno, "list" if isinstance(node, ast.List) else "tuple", ast.unparse(node)))
    return out


QCOLOR_CALLS = ("QColor", "fromRgb", "fromRgbF", "qRgb", "qRgba")


def _all_written() -> list:
    """(rel, line, kind, literal) outside the colour module."""
    out = []
    for rel, text in _sources():
        if rel in COLOUR_MODULES:
            continue
        out += [(rel, line, kind, literal) for line, kind, literal in _written(rel, text)]
    return out


def _data(rel: str, literal: str):
    """The DATA entry that covers this literal, or None."""
    for (where, what) in DATA:
        if where == rel and what in ("*", literal):
            return (where, what)
    return None


# ------------------------------------------------------------ guard the guard

def test_the_sweep_reads_the_application():
    files = [rel for rel, _text in _sources()]
    assert len(files) >= MIN_FILES, f"only {len(files)} files swept: the sweep has gone blind"
    for rel in COLOUR_MODULES:
        assert rel in files, f"{rel} is not among the files swept"
    assert not [f for f in files if f.startswith("tests/")], "the sweep reads the tests"


def test_the_sweep_reads_every_spelling():
    """Each spelling of a colour, in a line of the kind the application
    writes, is seen; clear, an index and a margin are not."""
    seen = {(kind, literal) for _line, kind, literal in _written("probe.py", (
        "from PyQt6.QtGui import QColor\n"
        "from PyQt6.QtCore import Qt\n"
        "a = 'background-color: #ffcccc; border: 2px solid red;'\n"
        "b = f'color: rgba(255, 255, 255, 230); padding: {4}px'\n"
        "c = QColor(128, 128, 128)\n"
        "d = Qt.GlobalColor.darkGreen\n"
        "e = QColor('yellow')\n"
        "text_color = (0, 0, 0) if a else (255, 255, 255)\n"
        "f = saved.get('color', [200, 200, 200])\n"
        "ink = 'white'\n"
        "g = {'ground': 'black'}\n"
        "h = Image.new('RGB', (8, 8), 'Gray')\n"
        "c.setAlpha(171)\n"))}
    assert seen == {("hex", "#ffcccc"), ("name", "border: red"), ("func", "rgba(255, 255, 255, 230)"),
                    ("qcolor", "QColor(128, 128, 128)"), ("global", "Qt.GlobalColor.darkGreen"),
                    ("name", "yellow"), ("tuple", "(0, 0, 0)"), ("tuple", "(255, 255, 255)"),
                    ("list", "[200, 200, 200]"), ("name", "white"), ("name", "black"), ("name", "Gray"),
                    ("alpha", "setAlpha(171)")}, seen
    quiet = _written("probe.py", (
        "from PyQt6.QtGui import QColor\n"
        "from PyQt6.QtCore import Qt\n"
        "a = 'background: transparent; border: none; color: rgba(0, 0, 0, 0);'\n"
        "b = QColor(0, 0, 0, 0)\n"
        "b.setAlpha(0)\n"
        "b.setAlpha(255)\n"
        "c = Qt.GlobalColor.transparent\n"
        "d = [int(h[i:i + 2], 16) for i in (0, 2, 4)]\n"
        "margins = (10, 10, 10, 10)\n"
        "sizes = [16, 32, 48]\n"
        "'''a bare string is prose: color: red, #ffcccc'''\n"
        "if d in (5, 10, 20) or d == (0, 0, 0) or a == 'red':\n"
        "    pass\n"
        "for size in [16, 32, 48]:\n"
        "    e = {'red': 1}['red']\n"))
    assert quiet == [], quiet


# ----------------------------------------------------------------- 1. named

def test_no_colour_is_written_out_in_the_code():
    stray = [f"{rel}:{line}  {literal}" for rel, line, _kind, literal in _all_written()
             if _data(rel, literal) is None]
    assert not stray, (
        "a colour is written out where a name belongs. Name it in "
        f"{COLOUR_MODULES[0]} and read the name; or, if it is data, add it to DATA "
        "with its reason:\n  " + "\n  ".join(stray))


def test_every_data_entry_still_covers_something():
    """An exemption that outlives what it excused is a licence for the next
    literal written in that file."""
    used = {_data(rel, literal) for rel, _line, _kind, literal in _all_written()}
    stale = [f"{where}: {what}" for (where, what) in DATA if (where, what) not in used]
    assert not stale, "DATA entries that match nothing now:\n  " + "\n  ".join(stale)
    assert all(reason.strip() for reason in DATA.values()), "a DATA entry has no reason"


# ---------------------------------------------------- 2. used: the palettes

def _strings_the_application_reads() -> set:
    """Every string the code holds outside the palettes' own keys: what a
    lookup by key, or a table of keys, is written with. A module's __all__
    is a list of the names it exports, not of keys, and is left out: a
    function called warning() does not look up a palette's 'warning'."""
    out = set()
    for rel, text in _sources():
        tree = ast.parse(text)
        not_keys = _prose(tree)
        if rel in PALETTE_MODULES:
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    not_keys |= {id(k) for k in node.keys if k is not None}
        for node in tree.body:
            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else
                      node.target if isinstance(node, ast.AnnAssign) else None)
            if getattr(target, "id", None) == "__all__" and node.value is not None:
                not_keys |= {id(n) for n in ast.walk(node.value)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in not_keys:
                if (rel, node.value) in NOT_LOOKUPS:        # spelled like a key, and not a lookup of one
                    _NOT_A_READ_SEEN.add((rel, node.value))
                    continue
                out.add(node.value)
    return out


def test_every_colour_a_palette_holds_is_looked_up():
    read = _strings_the_application_reads()
    unread = sorted({f"{name}[{key!r}]" for name, palette in PALETTES.items() for key, value in palette.items()
                     if isinstance(value, str) and (A_COLOUR.fullmatch(value) or value == "transparent")
                     and key not in read})
    assert not unread, (
        "palette entries nothing in the application looks up. A colour is kept "
        "for what uses it:\n  " + "\n  ".join(unread))
    assert sum(len(p) for p in PALETTES.values()) >= MIN_ENTRIES, "the palettes have gone missing"


# --------------------------------------------------- 3. used: the constants

def _colour_constants() -> dict:
    """NAME -> where it is defined, for every module-level constant of the
    colour module whose value is a colour: a hex string, an rgb() string, or
    channels under a name that says so."""
    out = {}
    for rel in COLOUR_MODULES:
        module = importlib.import_module(rel[:-3].replace("/", "."))
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))
        for node in tree.body:
            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else
                      node.target if isinstance(node, ast.AnnAssign) else None)
            if not isinstance(target, ast.Name) or not target.id.isupper():
                continue
            value = getattr(module, target.id, None)
            if isinstance(value, str) and A_COLOUR.fullmatch(value):
                out[target.id] = rel
            elif isinstance(value, tuple) and len(value) in (3, 4) and all(type(v) is int for v in value) \
                    and re.search(r"RGB|COLOR|COLOUR|OVERLAY", target.id):
                out[target.id] = rel
    return out


def _names_the_application_reads() -> dict:
    """NAME -> how many times the code reads it: as a name or as an attribute."""
    counts: dict[str, int] = {}
    for rel, text in _sources():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                counts[node.id] = counts.get(node.id, 0) + 1
            elif isinstance(node, ast.Attribute):
                if (rel, node.attr) in NOT_READS:           # spelled like a constant, and not a read of one
                    _NOT_A_READ_SEEN.add((rel, node.attr))
                    continue
                counts[node.attr] = counts.get(node.attr, 0) + 1
    return counts


def test_every_colour_constant_is_read():
    constants = _colour_constants()
    assert len(constants) >= MIN_CONSTANTS, f"only {len(constants)} colour constants found"
    reads = _names_the_application_reads()
    unread = sorted(name for name in constants if not reads.get(name))
    assert not unread, (
        "colour constants nothing in the application reads. A name is kept for "
        "what uses it:\n  " + "\n  ".join(f"{name}  ({constants[name]})" for name in unread))


def test_every_exported_name_exists():
    """__all__ names what the colour module offers. A name it lists and does
    not define makes `from module import *` fail."""
    for rel in COLOUR_MODULES:
        module = importlib.import_module(rel[:-3].replace("/", "."))
        missing = [n for n in getattr(module, "__all__", []) if not hasattr(module, n)]
        assert not missing, f"{rel} exports names it does not define: {missing}"


# ---------------------------------------------- image mode's own palette

#: Image mode is the dark palette under its own name and, after the spread,
#: the entries image mode reads and draws for itself. A new one is a
#: decision: it is added here with the entry.
IMAGE_OWN = ('status_error_text', 'window_bg', 'zoom_label_bg', 'checkbox_bg', 'scrollbar_bg', 'scrollbar_handle', 'scrollbar_handle_hover', 'scrollbar_border')


def _palette_display(name: str) -> ast.Dict:
    """The dict display NAME is assigned, at module level or in a class body."""
    for rel in PALETTE_MODULES:
        for node in ast.walk(ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))):
            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else
                      node.target if isinstance(node, ast.AnnAssign) else None)
            if getattr(target, "id", None) == name and isinstance(node.value, ast.Dict):
                return node.value
    raise AssertionError(f"{name} is not written as a dict display")


def test_image_mode_is_the_dark_palette_and_its_own_entries():
    node = _palette_display("IMAGE_MODE_COLORS")
    spreads = [ast.unparse(v) for k, v in zip(node.keys, node.values) if k is None]
    assert spreads == ["DARK_THEME_COLORS"] and node.keys[0] is None, (
        f"IMAGE_MODE_COLORS spreads {spreads}: it is the dark palette first, and no other")
    written = sorted(k.value for k in node.keys if k is not None and k.value != "name")
    assert written == sorted(IMAGE_OWN), (
        "the entries image mode writes for itself are not the ones listed. An entry "
        f"image mode never reads is a value nothing shows:\n  written {written}\n  listed  {sorted(IMAGE_OWN)}")


# ------------------------------------------- what only looks like a read

#: A string the code holds that is spelled like a palette key and is not a
#: lookup of one: (file, string) -> what it is. Left uncounted, so a key
#: this round removed cannot come back and be taken for read by a line
#: that never read it.
NOT_LOOKUPS = {
    ('utils/cache.py', 'error'):
        "a part of a cached stylesheet's own key, ('static', 'error', colour): it names the "
        'sheet, and looks up no palette',
}

#: An attribute the code reads that is spelled like a colour constant and is
#: not one: (file, name) -> what it is. Left uncounted for the same reason.
NOT_READS = dict()

_NOT_A_READ_SEEN: set = set()


def test_what_only_looks_like_a_read_is_still_in_the_code():
    """An entry that matches no line excuses nothing, and is taken out."""
    _strings_the_application_reads()
    _names_the_application_reads()
    listed = set(NOT_LOOKUPS) | set(NOT_READS)
    stale = sorted(listed - _NOT_A_READ_SEEN)
    assert not stale, f"listed as only looking like a read, and no longer in the code: {stale}"
    assert all(reason.strip() for reason in list(NOT_LOOKUPS.values()) + list(NOT_READS.values())), (
        "an entry has no reason")
