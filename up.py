"""derive every alpha-carrying colour from its base

    python up.py             # apply, then run the guard and CI's two commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guard and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head.

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-24. Every colour this application writes at an alpha becomes
translucent(BASE, ALPHA), so a change to a base ripples to every alpha form of it --
in the palette and in the four stylesheets that spelled their own grounds.

TWO THINGS MOVE ON SCREEN, BOTH RULED. The main window's image scrollbar was a
fixed string that never read the palette: its handle leaves #505050 for GREY_44
(RNV-COLLAPSE-505050, alpha unchanged at 150), and its hover turns gold, which
completes the 2026-09-12 ruling. Nothing else moves, and the script proves it
before writing a byte.
"""
from __future__ import annotations

import argparse
import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

REPO = 'rnv-color-picker'
SENTINEL = 'RNV-DERIVE-ALPHA'
SENTINEL_FILE = "tests/conftest.py"
GUARD = "tests/test_derived_values.py"
DESCRIPTION = 'derive every alpha-carrying colour from its base'

#: EXACTLY WHAT CI RUNS: both steps, with the per-test timeout and coverage.
#: The first is the locked root suite, which `pytest tests/` never reaches --
#: the icon-builder round went red in CI on exactly that.
SUITES = [
    ("CI step 1: unittest -v test_rnv_color_picker",
     [sys.executable, "-m", "coverage", "run", "--data-file=.coverage.unittest",
      "--source=core,utils,ui", "--branch", "-m", "unittest", "-v",
      "test_rnv_color_picker"]),
    ("CI step 2: pytest tests/ --timeout=60",
     [sys.executable, "-m", "pytest", "tests/", "-v", "--timeout=60",
      "--timeout-method=thread", "--cov=core", "--cov=ui", "--cov=utils",
      "--cov-branch", "--cov-report=term"]),
]

#: The environment the workflow sets for every step. verify() calls
#: post_write() before the suites, and they inherit os.environ.
CI_ENV = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1",
          "QT_QPA_PLATFORM": "offscreen", "COVERAGE_FILE": ".coverage.pytest"}


def post_write() -> None:
    """CI's environment. PYTHONPATH is the checkout, as the workflow's
    `PYTHONPATH: ${{ github.workspace }}`; COVERAGE_FILE is the pytest
    step's own, and the unittest step names its data file explicitly."""
    os.environ.update(CI_ENV)
    here = str(Path.cwd())
    existing = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = here + (os.pathsep + existing if existing else "")
    print("CI environment: " + ", ".join(f"{k}={v}" for k, v in CI_ENV.items())
          + f", PYTHONPATH={here}")


#: The workflow SUITES was written from, by content hash.
CI_MIRRORS = {'.github/workflows/tests.yml': '8d472651b899dcf403c7e77919fdfb90f1a31e06d663973f54e6b903c853fbba'}

SHADOWS = {"config.py", "conftest.py", "cache.py", "test_rnv_color_picker.py"}

LEFT_ALONE = [
    "DEBUG_BG, rgba(0, 0, 0, 200). The debug dimension label must read on any "
    "window whatever the theme; it is diagnostic, and the exclusion rule keeps "
    "it off the brand. A test now says so.",
    "OVERLAY_BLACK_LIGHT, _MEDIUM and _HEAVY -- black at 50, 75 and 180, "
    "spelled as integer tuples -- and the structural QColor(0, 0, 0) and "
    "QColor(255, 255, 255) in utils/cache.py. Tuples get a fleet round of "
    "their own, and the locked suite pins these three by value.",
    "tests/test_color_history.py::TestAddColorMaxSizeInvariant. It can fail "
    "at baseline, under load, with hypothesis FailedHealthCheck (too_slow): "
    "334 to 400 unique colours take about a second to generate, right at the "
    "limit. If that is the only failure, re-run `python up.py --verify`. Not "
    "this round's to fix.",
    "the mixer, which gets its own round, and the chart's element resolver, "
    "which must learn the three derivation helpers the fleet now has.",
]

SHEET_TEXT_OLD = '\n    QScrollBar:vertical {\n        background-color: rgba(51, 51, 51, 100);\n        width: 15px;\n        border: none;\n    }\n    QScrollBar::handle:vertical {\n        background-color: rgba(80, 80, 80, 150);\n        min-height: 20px;\n        border-radius: 5px;\n    }\n    QScrollBar::handle:vertical:hover {\n        background-color: rgba(100, 100, 100, 200);\n    }\n    QScrollBar::sub-page:vertical {\n        background-color: transparent;\n    }\n    QScrollBar::add-page:vertical {\n        background-color: transparent;\n    }\n    QScrollBar:horizontal {\n        background-color: rgba(51, 51, 51, 100);\n        height: 15px;\n        border: none;\n    }\n    QScrollBar::handle:horizontal {\n        background-color: rgba(80, 80, 80, 150);\n        min-width: 20px;\n        border-radius: 5px;\n    }\n    QScrollBar::handle:horizontal:hover {\n        background-color: rgba(100, 100, 100, 200);\n    }\n    QScrollBar::sub-page:horizontal {\n        background-color: transparent;\n    }\n    QScrollBar::add-page:horizontal {\n        background-color: transparent;\n    }\n    QScrollBar::add-line, QScrollBar::sub-line {\n        border: none;\n        background: none;\n    }\n'

GUARD_SOURCE = '"""Derived values: a colour that is a named colour AT AN ALPHA.\n\nA colour here used to be one of two things -- a name, or a literal -- and this\nfile adds the third the application always had and never declared.\nrgba(51, 51, 51, 100) is not a colour beside APP_BORDER; it IS APP_BORDER at\nalpha 100, and until 2026-09-25 nothing related the two. Now it is written\ntranslucent(APP_BORDER, SCROLLBAR_BG_ALPHA), and a change to APP_BORDER\nreaches it -- in the palette, and in every stylesheet that paints it.\n\nTHE IMAGE SCROLLBAR NEVER READ THE PALETTE. ThemeManager.SCROLLBAR_IMAGE was a\nfixed string, the one sheet in the file "not built from theme dict", so the\nmain window\'s image scrollbar painted its own literals whatever the palette\nsaid. Two rulings stopped at that string: RNV-COLLAPSE-505050 (2026-09-02) left\nthe handle #505050, and the gold hover (2026-09-12) left it grey --\nrgba(100, 100, 100, 200) while scrollbar_handle_hover said BRAND_GOLD. The\nsheet is built from IMAGE_MODE_COLORS now, same geometry, and both rulings\nreach it.\n\nWHAT MOVES A PIXEL: TWO THINGS, BOTH RULED. The image scrollbar handle leaves\n#505050 for GREY_44 at the same alpha, 150; and the main window\'s image\nscrollbar hover turns gold, completing the 2026-09-12 ruling. Everything else\nkeeps its colour and its alpha byte. test_nothing_moved_that_was_not_ruled\nholds each value to the constant and the byte it is made of.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\nimport re\n\nfrom utils import config as colors\nfrom utils.config import (DARK_THEME_COLORS as DARK,\n                          LIGHT_THEME_COLORS as LIGHT,\n                          IMAGE_MODE_COLORS as IMAGE,\n                          ThemeManager,\n                          translucent)\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nSRC = ROOT / "utils" / "config.py"\nPALETTES = {"DARK_THEME_COLORS": DARK, "LIGHT_THEME_COLORS": LIGHT,\n            "IMAGE_MODE_COLORS": IMAGE}\n\n#: constant -> the byte. Each is the alpha the literal it replaced already\n#: carried; all were integers or the "ED" byte, so nothing rounds.\nALPHAS = {\n    "IMAGE_OVERLAY_ALPHA": 0xED,\n    "IMAGE_CHECKBOX_ALPHA": 0x64,\n    "SCROLLBAR_BG_ALPHA": 0x64,\n    "SCROLLBAR_HANDLE_ALPHA": 0x96,\n    "IMAGE_MENU_ALPHA": 0xC8,\n    "IMAGE_BUTTON_FRAME_ALPHA": 0x64,\n}\n\n#: What each derived value is MADE OF: the constant its colour comes from, and\n#: its alpha byte. By NAME, not by hex -- see test_nothing_moved_that_was_not_ruled.\nMADE_OF = {\n    "APP_WINDOW_OVERLAY": ("TRUE_BLACK", 0xED),\n    "APP_CANVAS_OVERLAY": ("APP_CANVAS", 0xED),\n    "APP_PANEL_OVERLAY": ("BRAND_BLACK", 0xED),\n    "IMAGE_MENU_BG": ("TRUE_BLACK", 0xC8),\n    "IMAGE_BUTTON_FRAME_BG": ("TRUE_BLACK", 0x64),\n    "IMAGE_MODE_COLORS[\'checkbox_bg\']": ("TRUE_BLACK", 0x64),\n    "IMAGE_MODE_COLORS[\'scrollbar_bg\']": ("APP_BORDER", 0x64),\n    "IMAGE_MODE_COLORS[\'scrollbar_handle\']": ("GREY_44", 0x96),  # ruled\n}\n\n#: Diagnostic, and so excluded by rule: the debug overlay must read on any\n#: window whatever the theme, so it follows no brand row.\nEXCLUDED = {"DEBUG_BG"}\n\n_HEX8 = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{6})$")\n_COMPOSED = re.compile(r"#[0-9a-fA-F]{8}\\b|\\brgba\\(\\s*\\d{1,3}\\s*,\\s*\\d{1,3}"\n                       r"\\s*,\\s*\\d{1,3}\\s*,\\s*[0-9]*\\.?[0-9]+\\s*\\)")\n_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\\b")\n_FUNC = re.compile(r"\\brgba?\\(\\s*(\\d{1,3})\\s*,\\s*(\\d{1,3})\\s*,\\s*(\\d{1,3})"\n                   r"\\s*(?:,\\s*[0-9]*\\.?[0-9]+\\s*)?\\)")\nSKIP_DIRS = {".git", "tests", "build", "dist", ".venv", "venv", "__pycache__"}\n\n\ndef decompose(value: str) -> tuple[str, int] | None:\n    """(base \'#rrggbb\', alpha byte) -- taken apart, never rebuilt, so a fault\n    in translucent() cannot also be a fault here."""\n    m = _HEX8.match(value)\n    if m:\n        return "#" + m.group(2).lower(), int(m.group(1), 16)\n    return None\n\n\ndef _parts_of(spelled: str) -> tuple[str, int]:\n    """(base, alpha byte) for any composed spelling, with Qt\'s own reading of\n    a fractional alpha: it TRUNCATES, so 0.3 is 76."""\n    if spelled.startswith("#"):\n        return "#" + spelled[3:].lower(), int(spelled[1:3], 16)\n    numbers = re.findall(r"[0-9]*\\.?[0-9]+", spelled)\n    r, g, b = (int(x) for x in numbers[:3])\n    a = numbers[3]\n    return "#%02x%02x%02x" % (r, g, b), (int(float(a) * 255) if "." in a\n                                         else int(a))\n\n\ndef colours_in(text: str) -> set[str]:\n    """Every colour in a string, as #rrggbb. #AARRGGBB is alpha FIRST."""\n    found = set()\n    for m in _HEX.finditer(text):\n        h = m.group(0)[1:].lower()\n        h = h[2:] if len(h) == 8 else ("".join(c * 2 for c in h) if len(h) == 3 else h)\n        found.add("#" + h)\n    for m in _FUNC.finditer(text):\n        channels = [int(g) for g in m.groups()]\n        if all(c <= 255 for c in channels):\n            found.add("#%02x%02x%02x" % tuple(channels))\n    return found\n\n\ndef _bare_strings(tree: ast.AST) -> set[int]:\n    """Docstrings and every other string nobody evaluates -- mentions."""\n    bare = set()\n    for node in ast.walk(tree):\n        body = getattr(node, "body", None)\n        if isinstance(body, list):\n            for st in body:\n                if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):\n                    bare.add(id(st.value))\n    return bare\n\n\ndef _sources():\n    """Application source: not tests, not a root test suite, not a delivery\n    script. Yields (relative path, parsed tree). BOM-aware: several files in\n    this repository carry one, and ast.parse refuses a U+FEFF it is handed."""\n    for path in sorted(ROOT.rglob("*.py")):\n        rel = path.relative_to(ROOT)\n        if any(p in SKIP_DIRS for p in rel.parts):\n            continue\n        if len(rel.parts) == 1 and rel.name.startswith(("test_", "up")):\n            continue\n        text = path.read_bytes().decode("utf-8-sig", errors="replace")\n        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:\n            continue\n        yield rel, ast.parse(text)\n\n\ndef _derived():\n    """(where, call node, resolved value) for every translucent() call at\n    module level in utils/config.py -- a constant, or a value in a dict."""\n    tree = ast.parse(SRC.read_text(encoding="utf-8-sig"))\n    out = []\n    for node in tree.body:\n        if not isinstance(node, (ast.Assign, ast.AnnAssign)):\n            continue\n        target = node.targets[0] if isinstance(node, ast.Assign) else node.target\n        name = getattr(target, "id", None)\n        if name is None or node.value is None:\n            continue\n        if isinstance(node.value, ast.Call):\n            if getattr(node.value.func, "id", None) == "translucent":\n                out.append((name, node.value, getattr(colors, name)))\n        elif isinstance(node.value, ast.Dict):\n            live = getattr(colors, name)\n            for key, value in zip(node.value.keys, node.value.values):\n                if key is None:          # a **splat, not an entry\n                    continue\n                if (isinstance(value, ast.Call)\n                        and getattr(value.func, "id", None) == "translucent"):\n                    out.append((f"{name}[{key.value!r}]", value, live[key.value]))\n    return out\n\n\n# ------------------------------------------------------------ guard the guard\n\ndef test_translucent_composes_alpha_first():\n    """#AARRGGBB, not #RRGGBBAA. Taking the wrong end gives a real colour and\n    the wrong one, which is the failure that does not look like a failure.\n    Upper case, as the overlays it replaced were written."""\n    assert translucent("#1a1a1a", 0xED) == "#ED1A1A1A"\n    assert translucent("0A0A0A", 0xED) == "#ED0A0A0A"\n    assert decompose(translucent("#d2bc93", 0x33)) == ("#d2bc93", 0x33)\n\n\ndef test_translucent_refuses_what_it_cannot_compose():\n    for bad in (-1, 256, 999, 0.5, True):\n        try:\n            translucent("#1a1a1a", bad)\n        except (ValueError, TypeError):\n            pass\n        else:\n            raise AssertionError(f"translucent took alpha {bad!r}")\n    for bad in ("#1a1a1", "#1a1a1a1a", "nonsense", "#gggggg"):\n        try:\n            translucent(bad, 0xED)\n        except ValueError:\n            pass\n        else:\n            raise AssertionError(f"translucent took base {bad!r}")\n\n\ndef test_the_alphas_are_the_declared_bytes():\n    for name, byte in ALPHAS.items():\n        assert hasattr(colors, name), f"utils.config has no {name}"\n        value = getattr(colors, name)\n        assert type(value) is int, f"{name} is {value!r}, not an int byte"\n        assert value == byte, f"{name} is {value:#x}, declared {byte:#x}"\n\n\ndef test_the_derivation_sweep_is_looking():\n    """Every check below iterates _derived(). If it came back empty they\n    would all pass over nothing."""\n    where = {w for w, _c, _v in _derived()}\n    assert set(MADE_OF) <= where, sorted(set(MADE_OF) - where)\n\n\n# ----------------------------------------------------------- the derivations\n\ndef test_every_derived_value_names_constants_that_exist():\n    """translucent(BASE, ALPHA) where both are names: a literal in either\n    position is the thing this round removed."""\n    bad = []\n    for where, call, _value in _derived():\n        if len(call.args) != 2 or call.keywords:\n            bad.append(f"{where}: {ast.unparse(call)} is not (BASE, ALPHA)")\n            continue\n        base, alpha = call.args\n        for pos, arg in (("base", base), ("alpha", alpha)):\n            if not isinstance(arg, ast.Name):\n                bad.append(f"{where}: the {pos} is {ast.unparse(arg)}, not a name")\n            elif not hasattr(colors, arg.id):\n                bad.append(f"{where}: the {pos} names {arg.id}, which "\n                           f"utils.config does not define")\n        if isinstance(base, ast.Name) and hasattr(colors, base.id):\n            if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(getattr(colors, base.id))):\n                bad.append(f"{where}: the base {base.id} is not a six-digit colour")\n        if isinstance(alpha, ast.Name) and alpha.id not in ALPHAS:\n            bad.append(f"{where}: the alpha {alpha.id} is not a declared "\n                       f"composite alpha")\n    assert not bad, "derived values that do not derive:\\n  " + "\\n  ".join(bad)\n\n\ndef test_every_derived_value_decomposes_to_its_base_and_its_alpha():\n    """TAKEN APART, not rebuilt -- the entry IS translucent()\'s output, so\n    recomputing it would compare the call with itself."""\n    wrong = []\n    for where, call, value in _derived():\n        base, alpha = call.args\n        parts = decompose(value)\n        want = (getattr(colors, base.id).lower(), getattr(colors, alpha.id))\n        if parts != want:\n            wrong.append(f"{where} is {value!r}, which takes apart to {parts}, "\n                         f"not {base.id}/{alpha.id} {want}")\n    assert not wrong, "derived values that do not match:\\n  " + "\\n  ".join(wrong)\n\n\ndef test_no_composed_literal_is_left_in_the_application():\n    """The completeness half. Every EVALUATED string in the application\'s own\n    source that spells a named colour at an alpha. Docstrings are mentions;\n    alpha 0 is not a colour; a base no constant names has no row to follow;\n    and the diagnostic overlay is excluded by rule."""\n    named = {v.lower() for n, v in vars(colors).items()\n             if n.isupper() and isinstance(v, str)\n             and re.fullmatch(r"#[0-9a-fA-F]{6}", v)}\n    strays, files = [], 0\n    for rel, tree in _sources():\n        files += 1\n        bare = _bare_strings(tree)\n        excluded = set()\n        for node in tree.body:\n            if isinstance(node, (ast.Assign, ast.AnnAssign)):\n                t = node.targets[0] if isinstance(node, ast.Assign) else node.target\n                if getattr(t, "id", None) in EXCLUDED:\n                    excluded |= {id(n) for n in ast.walk(node)}\n        for node in ast.walk(tree):\n            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):\n                continue\n            if id(node) in bare or id(node) in excluded:\n                continue\n            for spelled in _COMPOSED.findall(node.value):\n                base, alpha = _parts_of(spelled)\n                if alpha and base in named:\n                    strays.append(f"{rel}:{node.lineno}  {spelled}")\n    # 36 application files on 2026-09-25; below 25 the walk has lost a\n    # package, not a file.\n    assert files >= 25, f"only {files} files swept -- the walk has gone blind"\n    assert not strays, ("composed values still written out rather than "\n                        "derived:\\n  " + "\\n  ".join(strays))\n\n\ndef test_the_diagnostic_overlay_stays_outside_the_brand():\n    """The exclusion rule, asserted rather than assumed: DEBUG_BG must read on\n    any window whatever the theme, so it follows no register row."""\n    tree = ast.parse(SRC.read_text(encoding="utf-8-sig"))\n    for node in tree.body:\n        if (isinstance(node, (ast.Assign, ast.AnnAssign))\n                and getattr(node.targets[0] if isinstance(node, ast.Assign)\n                            else node.target, "id", None) == "DEBUG_BG"):\n            assert isinstance(node.value, ast.Constant), (\n                "DEBUG_BG is computed from the application\'s own values; a "\n                "diagnostic overlay must not follow the brand")\n            return\n    raise AssertionError("utils.config has no DEBUG_BG")\n\n\n# ------------------------------------------------ the sheet that ignored it\n\ndef test_the_image_scrollbar_sheet_is_built_from_the_palette():\n    """SCROLLBAR_IMAGE paints the main window\'s image scrollbar. It is read\n    from IMAGE_MODE_COLORS now, so the rulings that land in the palette reach\n    the screen: the handle is GREY_44, and the hover is the gold."""\n    sheet = ThemeManager.SCROLLBAR_IMAGE\n    handle = re.findall(r"QScrollBar::handle:vertical\\s*\\{\\s*background-color:\\s*([^;]+);", sheet)\n    hover = re.findall(r"QScrollBar::handle:vertical:hover\\s*\\{\\s*background-color:\\s*([^;]+);", sheet)\n    groove = re.findall(r"QScrollBar:vertical\\s*\\{\\s*background-color:\\s*([^;]+);", sheet)\n    assert handle == [IMAGE["scrollbar_handle"]], handle\n    assert hover == [IMAGE["scrollbar_handle_hover"]] == [colors.BRAND_GOLD], hover\n    assert groove == [IMAGE["scrollbar_bg"]], groove\n    # and it carries no colour of its own any more\n    literals = [c for c in colours_in(sheet)\n                if c not in {decompose(IMAGE["scrollbar_bg"])[0],\n                             decompose(IMAGE["scrollbar_handle"])[0],\n                             colors.BRAND_GOLD}]\n    assert not literals, f"SCROLLBAR_IMAGE still spells its own colours: {literals}"\n\n\n# --------------------------------------------------- what moved, and what not\n\ndef test_the_scrollbar_handle_is_grey_44_at_150():\n    """RNV-COLLAPSE-505050, closed here 2026-09-25."""\n    assert decompose(IMAGE["scrollbar_handle"]) == (\n        colors.GREY_44, colors.SCROLLBAR_HANDLE_ALPHA)\n    assert colors.SCROLLBAR_HANDLE_ALPHA == 150\n\n\ndef test_nothing_moved_that_was_not_ruled():\n    """Each derived value, held to what it is MADE OF: the constant its colour\n    comes from and its alpha byte.\n\n    BY NAME, NOT BY HEX, and that is the point of the round. A register move\n    is meant to pass straight through these values; a test that pinned\n    \'#333333\' would fail the first time one did and ask a person to edit it\n    by hand -- the job derivation exists to remove. What this DOES catch is a\n    value quietly re-made from something else, which the decomposition check\n    accepts as long as source and value agree with each other.\n\n    The byte-for-byte before-and-after was checked once, by the delivery\n    script, against the edited module before it was written."""\n    live = {where: value for where, _call, value in _derived()}\n    for where, (base, alpha) in MADE_OF.items():\n        assert where in live, f"{where} is no longer derived"\n        assert decompose(live[where]) == (getattr(colors, base).lower(), alpha), (\n            f"{where} is {live[where]}, which is not {base} at {alpha:#04x}")\n    assert IMAGE["window_bg"] == IMAGE["scroll_area_bg"] == colors.APP_WINDOW_OVERLAY\n    assert IMAGE["image_viewer_bg"] == colors.APP_CANVAS_OVERLAY\n    assert IMAGE["zoom_label_bg"] == colors.APP_PANEL_OVERLAY\n\n\ndef test_the_collapsed_value_is_gone_in_every_spelling():\n    """#505050 in any string spelling -- #rgb, #rrggbb, #aarrggbb, rgb(),\n    rgba() -- or as integers in a tuple or a QColor call. It survived here for\n    three weeks after its ruling because every sweep compared six-digit hex."""\n    found = []\n    for rel, tree in _sources():\n        bare = _bare_strings(tree)\n        for node in ast.walk(tree):\n            if (isinstance(node, ast.Constant) and isinstance(node.value, str)\n                    and id(node) not in bare and "#505050" in colours_in(node.value)):\n                found.append(f"{rel}:{node.lineno}  {node.value[:40]!r}")\n            values = None\n            if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) in (3, 4):\n                values = node.elts\n            elif isinstance(node, ast.Call) and len(node.args) >= 3 and (\n                    getattr(node.func, "id", None) or getattr(node.func, "attr", None)\n                    ) in ("QColor", "fromRgb", "QPen", "QBrush"):\n                values = node.args\n            if values:\n                ints = tuple(v.value for v in values[:3]\n                             if isinstance(v, ast.Constant) and type(v.value) is int)\n                if ints == (80, 80, 80):\n                    found.append(f"{rel}:{node.lineno}  (80, 80, 80)")\n    assert not found, "#505050 is still here:\\n  " + "\\n  ".join(found)\n    assert colours_in("rgba(80, 80, 80, 150)") == {"#505050"}, "the decoder is blind"\n\n# RNV-DERIVE-ALPHA\n'


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for exactly one occurrence before anything is written.
    utils/config.py and utils/cache.py carry a byte-order mark; the Tree
    reads through it and puts it back."""
    tree.sub('utils/config.py',
             "    return '#' + ''.join(\n        f'{max(0, min(255, c + step)):02x}' for c in _to_rgb(hex_color)\n    )\n",
             '    return \'#\' + \'\'.join(\n        f\'{max(0, min(255, c + step)):02x}\' for c in _to_rgb(hex_color)\n    )\n\n\ndef _hex6(hex_color: str) -> str:\n    """The six hex digits of a colour, or ValueError."""\n    h = hex_color.lstrip(\'#\')\n    if len(h) != 6 or any(c not in \'0123456789abcdefABCDEF\' for c in h):\n        raise ValueError(f"{hex_color!r} is not a six-digit hex colour")\n    return h\n\n\ndef _alpha_byte(alpha: int) -> int:\n    """An alpha as the 0-255 byte, or an error. A fraction is refused, not\n    scaled: Qt TRUNCATES a fractional alpha (0.3 is 76, not 77), and a helper\n    that rounded would move a pixel inside a respelling."""\n    if isinstance(alpha, bool) or not isinstance(alpha, int):\n        raise TypeError(f"alpha {alpha!r} is not an int byte")\n    if not 0 <= alpha <= 255:\n        raise ValueError(f"alpha {alpha} is outside 0-255")\n    return alpha\n\n\ndef translucent(hex_color: str, alpha: int) -> str:\n    """A colour at an alpha, as Qt\'s eight-digit #AARRGGBB -- ALPHA FIRST.\n\n    WHY A FUNCTION RATHER THAN A WRITTEN-OUT VALUE. A value computed from\n    another value must be computed in code; a written-down derivative is\n    orphaned the moment its source moves, and nothing says so. Here the\n    image-mode scrollbar kept #505050 for three weeks after RNV-COLLAPSE-505050\n    ruled it onto GREY_44, because the alpha form was written out as rgba()\n    and every sweep in the fleet compared six-digit hex.\n\n    WHY #AARRGGBB. It is the one spelling valid both in a stylesheet and in\n    QColor(). QColor() cannot parse rgba(): it returns an INVALID colour, and\n    Qt paints that as opaque black.\n\n    WHY UPPER CASE. The three overlays this replaced were written that way\n    (#ED000000, #ED0A0A0A, #ED1A1A1A), and upper case keeps them\n    byte-identical. rnv-icon-builder\'s helper of the same name writes lower;\n    Qt reads either, and whether eight-digit hex falls under the register\'s\n    lower-case rule is a question rnv-brand has not ruled on.\n    """\n    return \'#%02X%s\' % (_alpha_byte(alpha), _hex6(hex_color).upper())\n')
    tree.sub('utils/config.py',
             'IMAGE_OVERLAY_ALPHA: Final[str] = "ED"\n"""The alpha byte image mode composites its chrome at -- 0xED, about 93%.\n\nWHY THE OVERLAYS BELOW ARE WRITTEN OUT RATHER THAN COMPOSED. Qt wants the\neight-digit #AARRGGBB form, and building it from the six-digit constant would\nmake the palette entries resolve to an expression rather than a value, which\nthis app\'s own before/after comparison cannot check. The relationship is\nenforced by tests/test_ladder_and_plate.py instead: it asserts that each\noverlay\'s last six digits ARE the register value it claims, and that its alpha\nbyte is this one. If the register moves a base, those tests fail and these move\nwith it.\n\nTHEY WERE INVISIBLE BEFORE. The 2026-08-29 wiring pass claimed no registered\nvalue was left spelled as a literal in a dark palette. That was true of\nsix-digit spellings only: its sweep compared whole strings, so #ED000000 never\nmatched #000000 and four of these sat in IMAGE_MODE_COLORS while the test\nreported clean. The sweep now normalises both lengths.\n"""\n\nAPP_WINDOW_OVERLAY: Final[str] = "#ED000000"\n"""TRUE_BLACK, and APP["window"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_CANVAS_OVERLAY: Final[str] = "#ED0A0A0A"\n"""APP_CANVAS, and APP["canvas"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_PANEL_OVERLAY: Final[str] = "#ED1A1A1A"\n"""BRAND_BLACK, and APP["panel"], at IMAGE_OVERLAY_ALPHA."""\n',
             '# ==================== Composite alphas ====================\n# A composite is a named colour AT AN ALPHA: translucent(BASE, ALPHA). The\n# colour half is a name, so a register move reaches it; the alpha half is one\n# of these, so the same move carries every alpha form of the colour with it.\n# Each byte is the one the literal it replaced already held.\n#\n# THREE ARE 100, UNDER THREE NAMES, ON PURPOSE: the checkbox ground, the\n# scrollbar groove and the button frame. Identical numbers doing unrelated\n# jobs stay separate, or retuning one silently retunes the others.\n\nIMAGE_OVERLAY_ALPHA: Final[int] = 0xED\n"""237, about 93%. The alpha image mode composites its chrome at.\n\nWAS THE STRING "ED", AND THE OVERLAYS BELOW WERE WRITTEN OUT. The reason\ngiven was that composing them would make the palette entries resolve to an\nexpression rather than a value, which this app\'s own before/after comparison\ncould not check -- so tests/test_ladder_and_plate.py asserted the\nrelationship instead, and a register move would have failed that test and\nwaited for someone to edit three strings by hand.\n\nRULED 2026-09-24 by Chris: derived values are DERIVED, not asserted. The\npalettes still resolve to plain strings at import, so every comparison of\nvalues still compares values. What changed is that a register move now\nreaches the overlays on its own. The ladder test keeps its check, taking each\noverlay apart rather than trusting the call that built it.\n\nTHEY WERE INVISIBLE BEFORE. The 2026-08-29 wiring pass claimed no registered\nvalue was left spelled as a literal in a dark palette. That was true of\nsix-digit spellings only: its sweep compared whole strings, so #ED000000 never\nmatched #000000 and four of these sat in IMAGE_MODE_COLORS while the test\nreported clean. The sweep now normalises both lengths.\n"""\n\nIMAGE_CHECKBOX_ALPHA: Final[int] = 0x64\n"""100. The checkbox indicator\'s ground in image mode (TRUE_BLACK)."""\n\nSCROLLBAR_BG_ALPHA: Final[int] = 0x64\n"""100. The image-mode scrollbar groove (APP_BORDER)."""\n\nSCROLLBAR_HANDLE_ALPHA: Final[int] = 0x96\n"""150. The image-mode scrollbar handle (GREY_44) -- the byte all five\napplications use; its colour was #505050 until 2026-09-25."""\n\nIMAGE_MENU_ALPHA: Final[int] = 0xC8\n"""200. The context menu\'s ground in image mode (TRUE_BLACK)."""\n\nIMAGE_BUTTON_FRAME_ALPHA: Final[int] = 0x64\n"""100. The frame behind the main buttons in image mode (TRUE_BLACK)."""\n\nAPP_WINDOW_OVERLAY: Final[str] = translucent(TRUE_BLACK, IMAGE_OVERLAY_ALPHA)\n"""TRUE_BLACK, and APP["window"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_CANVAS_OVERLAY: Final[str] = translucent(APP_CANVAS, IMAGE_OVERLAY_ALPHA)\n"""APP_CANVAS, and APP["canvas"], at IMAGE_OVERLAY_ALPHA."""\n\nAPP_PANEL_OVERLAY: Final[str] = translucent(BRAND_BLACK, IMAGE_OVERLAY_ALPHA)\n"""BRAND_BLACK, and APP["panel"], at IMAGE_OVERLAY_ALPHA."""\n')
    tree.sub('utils/config.py',
             "    'checkbox_bg':        'rgba(0, 0, 0, 100)',\n",
             "    'checkbox_bg':        translucent(TRUE_BLACK, IMAGE_CHECKBOX_ALPHA),\n")
    tree.sub('utils/config.py',
             "    # ── Scrollbar overrides — translucent grays (no brand gold) ──\n    'scrollbar_bg':            'rgba(51, 51, 51, 100)',\n    'scrollbar_handle':        'rgba(80, 80, 80, 150)',\n",
             "    # ── Scrollbar overrides — translucent greys, gold on hover ──\n    # Derived, and read by ThemeManager.SCROLLBAR_IMAGE below, which is\n    # what paints the main window's image scrollbar.\n    'scrollbar_bg':            translucent(APP_BORDER, SCROLLBAR_BG_ALPHA),\n    # RNV-COLLAPSE-505050, closed here 2026-09-25: this was\n    # rgba(80, 80, 80, 150), the value ruled onto GREY_44 on\n    # 2026-09-02 and left behind because nothing decoded rgba().\n    'scrollbar_handle':        translucent(GREY_44, SCROLLBAR_HANDLE_ALPHA),\n")
    tree.sub('utils/config.py',
             "    'scrollbar_border':        'transparent',\n}\n",
             "    'scrollbar_border':        'transparent',\n}\n\n# Image-mode grounds painted by stylesheets that are not built from\n# IMAGE_MODE_COLORS -- the context menu, three copies of it, and the\n# frame behind the main buttons. Named here so they derive with the rest.\nIMAGE_MENU_BG: Final[str] = translucent(TRUE_BLACK, IMAGE_MENU_ALPHA)\nIMAGE_BUTTON_FRAME_BG: Final[str] = translucent(TRUE_BLACK, IMAGE_BUTTON_FRAME_ALPHA)\n")
    tree.sub('utils/config.py',
             '# Image mode scrollbar is special — uses custom transparent overlay look\n# (not built from theme dict because these rgba values are image-mode specific)\nThemeManager.SCROLLBAR_IMAGE = """\n    QScrollBar:vertical {\n        background-color: rgba(51, 51, 51, 100);\n        width: 15px;\n        border: none;\n    }\n    QScrollBar::handle:vertical {\n        background-color: rgba(80, 80, 80, 150);\n        min-height: 20px;\n        border-radius: 5px;\n    }\n    QScrollBar::handle:vertical:hover {\n        background-color: rgba(100, 100, 100, 200);\n    }\n    QScrollBar::sub-page:vertical {\n        background-color: transparent;\n    }\n    QScrollBar::add-page:vertical {\n        background-color: transparent;\n    }\n    QScrollBar:horizontal {\n        background-color: rgba(51, 51, 51, 100);\n        height: 15px;\n        border: none;\n    }\n    QScrollBar::handle:horizontal {\n        background-color: rgba(80, 80, 80, 150);\n        min-width: 20px;\n        border-radius: 5px;\n    }\n    QScrollBar::handle:horizontal:hover {\n        background-color: rgba(100, 100, 100, 200);\n    }\n    QScrollBar::sub-page:horizontal {\n        background-color: transparent;\n    }\n    QScrollBar::add-page:horizontal {\n        background-color: transparent;\n    }\n    QScrollBar::add-line, QScrollBar::sub-line {\n        border: none;\n        background: none;\n    }\n"""\n',
             '# Image mode scrollbar keeps its own GEOMETRY -- 15px, borderless, the\n# transparent overlay look -- and takes its COLOURS from IMAGE_MODE_COLORS.\n# RNV-DERIVE-ALPHA (2026-09-25): it used to spell its own rgba() values\n# here, "not built from theme dict", so two rulings that landed in the\n# palette never reached the main window: the handle stayed #505050\n# (RNV-COLLAPSE-505050) and the hover stayed grey (the 2026-09-12 gold\n# hover). Reading the palette is what carries both.\nThemeManager.SCROLLBAR_IMAGE = f"""\n    QScrollBar:vertical {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_bg\']};\n        width: 15px;\n        border: none;\n    }}\n    QScrollBar::handle:vertical {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_handle\']};\n        min-height: 20px;\n        border-radius: 5px;\n    }}\n    QScrollBar::handle:vertical:hover {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_handle_hover\']};\n    }}\n    QScrollBar::sub-page:vertical {{\n        background-color: transparent;\n    }}\n    QScrollBar::add-page:vertical {{\n        background-color: transparent;\n    }}\n    QScrollBar:horizontal {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_bg\']};\n        height: 15px;\n        border: none;\n    }}\n    QScrollBar::handle:horizontal {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_handle\']};\n        min-width: 20px;\n        border-radius: 5px;\n    }}\n    QScrollBar::handle:horizontal:hover {{\n        background-color: {IMAGE_MODE_COLORS[\'scrollbar_handle_hover\']};\n    }}\n    QScrollBar::sub-page:horizontal {{\n        background-color: transparent;\n    }}\n    QScrollBar::add-page:horizontal {{\n        background-color: transparent;\n    }}\n    QScrollBar::add-line, QScrollBar::sub-line {{\n        border: none;\n        background: none;\n    }}\n"""\n')
    tree.sub('utils/config.py',
             "    'swatch_edge',\n",
             "    'swatch_edge',\n    'translucent',\n")
    tree.sub('utils/config.py',
             "    'DEBUG_BG',\n",
             "    'DEBUG_BG',\n    'IMAGE_MENU_BG',\n    'IMAGE_BUTTON_FRAME_BG',\n")
    tree.sub('utils/cache.py',
             '    STATUS_ERROR_BG,\n)\n',
             '    STATUS_ERROR_BG,\n    IMAGE_MENU_BG, IMAGE_BUTTON_FRAME_BG,\n)\n')
    tree.sub('utils/cache.py',
             '                        background-color: rgba(0, 0, 0, 200);\n',
             '                        background-color: {IMAGE_MENU_BG};\n')
    tree.sub('utils/cache.py',
             '            if is_image_mode:\n                cls._cache[key] = """\n                    QFrame {\n                        background-color: rgba(0, 0, 0, 100);\n                        border-radius: 8px;\n                    }\n                """\n',
             '            if is_image_mode:\n                cls._cache[key] = f"""\n                    QFrame {{\n                        background-color: {IMAGE_BUTTON_FRAME_BG};\n                        border-radius: 8px;\n                    }}\n                """\n')
    tree.sub('ui/color_swatch_widget.py',
             'from utils.config import BRAND_GOLD, prefers_dark_ink\n',
             'from utils.config import BRAND_GOLD, IMAGE_MENU_BG, prefers_dark_ink\n')
    tree.sub('ui/color_swatch_widget.py',
             '                            background-color: rgba(0, 0, 0, 200);\n',
             '                            background-color: {IMAGE_MENU_BG};\n')
    tree.sub('ui/image_viewer.py',
             'from utils.config import BRAND_GOLD\n',
             'from utils.config import BRAND_GOLD, IMAGE_MENU_BG\n')
    tree.sub('ui/image_viewer.py',
             '                                background-color: rgba(0, 0, 0, 200);\n',
             '                                background-color: {IMAGE_MENU_BG};\n')
    tree.sub('tests/test_ladder_and_plate.py',
             '    """The overlays are written out because Qt wants eight digits and composing\n    them would make the palette resolve to an expression. This is the\n    relationship that composition would have given, asserted instead -- so a\n    register move fails here rather than diverging silently."""\n    for name, (base_name, _key) in OVERLAYS.items():\n        overlay = getattr(colors, name)\n        base = getattr(colors, base_name)\n        assert len(overlay) == 9, f\'{name} is {overlay}, not #AARRGGBB\'\n        assert overlay[1:3].upper() == colors.IMAGE_OVERLAY_ALPHA.upper(), (\n',
             '    """The overlays are COMPOSED now -- translucent(BASE, IMAGE_OVERLAY_ALPHA),\n    ruled 2026-09-24 -- and this still takes each one apart rather than\n    building it again, so a bug in the composing function fails here. Until\n    that date they were written out, and this was the only thing relating\n    them to their bases."""\n    for name, (base_name, _key) in OVERLAYS.items():\n        overlay = getattr(colors, name)\n        base = getattr(colors, base_name)\n        assert len(overlay) == 9, f\'{name} is {overlay}, not #AARRGGBB\'\n        assert int(overlay[1:3], 16) == colors.IMAGE_OVERLAY_ALPHA, (\n')
    tree.sub('tests/conftest.py',
             '# RNV-DEADLINE-AND-PIN, 2026-09-12 -- the MAX_HISTORY_SIZE property test\n',
             "# RNV-DERIVE-ALPHA, 2026-09-25 -- every colour this application writes\n# at an alpha is DERIVED, translucent(BASE, ALPHA), so a change to a base\n# reaches every alpha form of it. The main window's image scrollbar now\n# reads IMAGE_MODE_COLORS, so its handle is GREY_44 (RNV-COLLAPSE-505050)\n# and its hover the gold (2026-09-12), both by ruling.\n# tests/test_derived_values.py holds it.\n# RNV-DEADLINE-AND-PIN, 2026-09-12 -- the MAX_HISTORY_SIZE property test\n")


def _picked(module: ast.Module, names: set) -> ast.Module:
    """The top-level definitions named, and nothing else -- so the edited
    colours can be evaluated here without importing utils.config, which pulls
    in PIL, PyQt6 and the application's logger."""
    body = []
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            body.append(node)
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in names:
            body.append(node)
    return ast.Module(body=body, type_ignores=[])


def checks(tree) -> None:
    """Against the IN-MEMORY tree, before anything reaches disk."""
    src = tree.read('utils/config.py')
    module = ast.parse(src)
    names = {'_hex6', '_alpha_byte', 'translucent', 'TRUE_BLACK', 'APP_CANVAS',
             'BRAND_BLACK', 'APP_BORDER', 'GREY_44', 'BRAND_GOLD',
             'IMAGE_OVERLAY_ALPHA', 'IMAGE_CHECKBOX_ALPHA', 'SCROLLBAR_BG_ALPHA',
             'SCROLLBAR_HANDLE_ALPHA', 'IMAGE_MENU_ALPHA', 'IMAGE_BUTTON_FRAME_ALPHA',
             'APP_WINDOW_OVERLAY', 'APP_CANVAS_OVERLAY', 'APP_PANEL_OVERLAY',
             'IMAGE_MENU_BG', 'IMAGE_BUTTON_FRAME_BG'}
    ns = {'Final': typing.Final}
    exec(compile(_picked(module, names), 'utils/config.py (edited, selected)', 'exec'), ns)

    # the values, byte for byte where the spelling did not change
    assert ns['APP_WINDOW_OVERLAY'] == '#ED000000', ns['APP_WINDOW_OVERLAY']
    assert ns['APP_CANVAS_OVERLAY'] == '#ED0A0A0A', ns['APP_CANVAS_OVERLAY']
    assert ns['APP_PANEL_OVERLAY'] == '#ED1A1A1A', ns['APP_PANEL_OVERLAY']
    assert ns['IMAGE_MENU_BG'] == '#C8000000', ns['IMAGE_MENU_BG']
    assert ns['IMAGE_BUTTON_FRAME_BG'] == '#64000000', ns['IMAGE_BUTTON_FRAME_BG']

    image = next(n.value for n in module.body if isinstance(n, ast.AnnAssign)
                 and getattr(n.target, 'id', None) == 'IMAGE_MODE_COLORS')
    entries = {k.value: v for k, v in zip(image.keys, image.values) if k is not None}
    live = {k: eval(compile(ast.Expression(entries[k]), k, 'eval'), ns)
            for k in ('checkbox_bg', 'scrollbar_bg', 'scrollbar_handle',
                      'scrollbar_handle_hover')}
    assert live['checkbox_bg'] == '#64000000', live['checkbox_bg']
    assert live['scrollbar_bg'] == '#64333333', live['scrollbar_bg']
    assert live['scrollbar_handle'] == '#96444444', live['scrollbar_handle']  # ruled
    assert live['scrollbar_handle_hover'] == ns['BRAND_GOLD']
    for name in ('DARK_THEME_COLORS', 'LIGHT_THEME_COLORS', 'IMAGE_MODE_COLORS'):
        node = next(n.value for n in module.body if isinstance(n, ast.AnnAssign)
                    and getattr(n.target, 'id', None) == name)
        for k, v in zip(node.keys, node.values):
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                assert 'rgba(' not in v.value, f'{name}[{k.value!r}] = {v.value}'

    # THE SHEET: the new one must be the old one with exactly three colours
    # swapped, and nothing else -- not a brace, not a space.
    sheet = next(n for n in module.body if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Attribute)
                 and n.targets[0].attr == 'SCROLLBAR_IMAGE')
    new_sheet = eval(compile(ast.Expression(sheet.value), 'SCROLLBAR_IMAGE', 'eval'),
                     dict(ns, IMAGE_MODE_COLORS=live))
    want = (SHEET_TEXT_OLD.replace('rgba(51, 51, 51, 100)', live['scrollbar_bg'])
            .replace('rgba(80, 80, 80, 150)', live['scrollbar_handle'])
            .replace('rgba(100, 100, 100, 200)', live['scrollbar_handle_hover']))
    assert new_sheet == want, 'SCROLLBAR_IMAGE changed more than its three colours'
    assert new_sheet.count(ns['BRAND_GOLD']) == 2, 'the hover is not gold, twice'

    # the three other stylesheets read the named grounds
    cache = tree.read('utils/cache.py')
    assert 'rgba(' not in cache, 'utils/cache.py still spells an rgba() ground'
    assert 'background-color: {IMAGE_BUTTON_FRAME_BG};' in cache
    for rel in ('ui/color_swatch_widget.py', 'ui/image_viewer.py'):
        text = tree.read(rel)
        assert 'rgba(' not in text, f'{rel} still spells an rgba() ground'
        assert 'background-color: {IMAGE_MENU_BG};' in text, rel

    ladder = tree.read('tests/test_ladder_and_plate.py')
    assert 'IMAGE_OVERLAY_ALPHA.upper()' not in ladder

    # the unconsumed-keys guard counts exactly two NOT CONSUMED notes in
    # utils/config.py; nothing here may add a third
    assert len(re.findall(r'#\s*NOT CONSUMED', src)) == 2
# ------------------------------------------------------------------ plumbing
#
# EXIT CODES ARE A TAXONOMY, NOT A BOOLEAN. Rev 6 §3.0.1. A harness that
# returns non-zero for everything tells the operator something is wrong and
# nothing about what, and the three non-zero cases want three different
# actions: read the diff, install something, re-run.
EXIT_CLEAN = 0       # everything agreed
EXIT_DISAGREES = 1   # something ran and disagreed -- read it
EXIT_CANNOT_RUN = 2  # the environment is not ready -- nothing was asked
EXIT_INCOMPLETE = 3  # it ran and did not finish -- re-run before believing it


class Stop(SystemExit):
    """A refusal this script chose, as opposed to a crash.

    Carries an exit code from the taxonomy. Bare SystemExit('message') exits 1,
    which says A TEST DISAGREED -- so every refusal used to arrive wearing the
    one verdict it was not.
    """

    def __init__(self, message: str, code: int = EXIT_CANNOT_RUN) -> None:
        super().__init__(message)
        self.code = code


#: Two files per repository that exist there and in none of the others.
#: Verified against the live fleet by _fingerprint_check.py at build time,
#: because a fingerprint that has been renamed away identifies nothing and
#: would refuse every correct checkout.
FINGERPRINTS = {
    "rnv-color-mixer": ("core/image_handler.py", "ui/canvas_view.py"),
    "rnv-color-palette-manager": ("core/color_extractor.py",
                                  "ui/batch_export_dialog.py"),
    "rnv-color-picker": ("core/hilbert_curve.py", "ui/color_swatch_widget.py"),
    "rnv-icon-builder": ("core/icon_builder_core.py", "core/project_manager.py"),
    "rnv-text-transformer": ("core/diff_engine.py", "core/text_cleaner.py"),
}


def refuse_wrong_repository(root) -> None:
    """Refuse a checkout that is not the repository this script was built for.

    CALLED FIRST IN apply(), BEFORE THE SENTINEL AND BEFORE ANY ANCHOR, and the
    order is the whole point. The five applications share file names -- four of
    them have a utils/config.py or a ui/colors.py, and several share a
    tests/conftest.py. Run in the wrong sibling, a sentinel check says "already
    applied" or "not a checkout" and an anchor check says "the file moved",
    and BOTH of those are the script guessing at the wrong question.

    A fingerprint is a file only the right repository has. Two, because one
    that gets renamed takes the check with it.
    """
    want = FINGERPRINTS.get(REPO)
    if not want:
        return
    missing = [f for f in want if not (root / f).exists()]
    if missing:
        raise Stop(
            f"this is not a {REPO} checkout.\n"
            f"  expected to find: {', '.join(want)}\n"
            f"  missing here:     {', '.join(missing)}\n"
            f"Run it from the root of {REPO}. Nothing was read or written.",
            EXIT_CANNOT_RUN)


def _left_alone() -> None:
    """Print what this round deliberately did not touch.

    LEFT_ALONE is optional and is prose, not a guard. It exists because a
    reader of a diff can see what changed and cannot see what was considered
    and declined, and the second is where a round's scope actually lives.
    """
    items = globals().get("LEFT_ALONE")
    if not items:
        return
    print("\nleft alone, deliberately:")
    for line in items:
        print(f"  - {line}")


def refuse_to_shadow() -> None:
    name = Path(__file__).name
    if name in SHADOWS:
        raise Stop(f"refusing to run as {name} -- it would shadow a module on "
                   f"sys.path. Rename to up.py and run again.", EXIT_CANNOT_RUN)


class Tree:
    """Every edit lands here first. Disk is written only after all guards pass,
    so --check is a real rehearsal and a half-applied state is impossible."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, str] = {}
        self.deleted: set[str] = set()
        #: rel -> (had a BOM, line endings were CRLF throughout). What a file
        #: was on disk, so flush() can put back exactly that around the edit.
        self.form: dict[str, tuple[bool, bool]] = {}

    def read(self, rel: str) -> str:
        """The file as text with LF line endings, whatever it is on disk.

        A FILE IS ITS BYTES, AND AN EDIT MUST NOT CHANGE THE ONES IT DID NOT
        MEAN TO. This used to read with read_text('utf-8-sig') and flush with
        encode('utf-8'). The first strips a byte-order mark and folds CRLF to
        LF; the second puts neither back. So a one-line edit to a CRLF file
        rewrote every line ending in it, and any edit to a file with a BOM
        deleted its first three bytes. rnv-color-picker's utils/config.py --
        the picker's palette -- carries a BOM, so its next round would have.

        Anchors are written with \\n, so a CRLF file is held as LF in memory
        and its endings are restored on write. A file that MIXES endings is
        held exactly as it is: anchors then match only its LF lines, and
        everything else round-trips untouched.
        """
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise Stop(f"missing file: {rel}", EXIT_CANNOT_RUN)
            raw = p.read_bytes()
            bom = raw.startswith(b"\xef\xbb\xbf")
            text = (raw[3:] if bom else raw).decode("utf-8")
            crlf = text.count("\r\n")
            all_crlf = crlf > 0 and crlf == text.count("\n")
            if all_crlf:
                text = text.replace("\r\n", "\n")
            self.files[rel] = text
            self.form[rel] = (bom, all_crlf)
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        """Mark a file for removal. Nothing leaves disk until flush()."""
        if not (self.root / rel).exists() and rel not in self.files:
            raise Stop(f"cannot delete {rel}: it is not in this checkout",
                       EXIT_CANNOT_RUN)
        self.files.pop(rel, None)
        self.deleted.add(rel)

    def sub(self, rel: str, old: str, new: str, times: int = 1) -> None:
        src = self.read(rel)
        found = src.count(old)
        if found != times:
            raise Stop(
                f"{rel}: expected {times} occurrence(s) of the anchor, found "
                f"{found}. The file moved; re-derive this edit before trusting "
                f"the script.", EXIT_CANNOT_RUN)
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
            data = self.encode(rel, text)
            if not p.exists() or p.read_bytes() != data:
                p.write_bytes(data)
                touched.append(rel)
        return touched

    def encode(self, rel: str, text: str) -> bytes:
        """Text back to bytes in the form the file had when it was read.

        A file never read -- one this script creates -- has no form to keep
        and is written as plain UTF-8 with LF, which is what every file in
        this fleet is unless it says otherwise.
        """
        bom, all_crlf = self.form.get(rel, (False, False))
        if all_crlf:
            text = text.replace("\n", "\r\n")
        return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


def _tail(out: str, lines: int = 40) -> str:
    text = out.strip()
    marker = "short test summary info"
    if marker in text:
        return text[max(0, text.rindex(marker) - 30):]
    return "\n".join(text.splitlines()[-lines:])


def _outcome(code: int, out: str) -> str:
    """"pass", "fail", "abort", "killed" or "env" -- only exit code 1 means a
    test failed.

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
        # EXIT 1 IS NOT ALWAYS A TEST DISAGREEING, and this used to assume it
        # was. A missing pytest PLUGIN or a missing pinned package does not
        # stop collection -- the tests are found, then fail at setup -- so
        # pytest exits 1, the same code a real regression gives.
        #
        # It shipped that way. A fresh Codespace with the app requirements and
        # none of tests/requirements-dev.txt ran a round that had landed
        # cleanly and got 85 errors ("fixture 'qtbot' not found": pytest-qt)
        # and 3 failures ("No module named 'engine'": the rnv-brand pin), and
        # the verdict was "FAILED -- the suite is not green". Not one of the 88
        # was the change disagreeing with anything.
        #
        # The discriminator is the assertion. A regression raises
        # AssertionError; a missing dependency raises nothing of the kind. If
        # the run carries environment signatures and NO assertion failure, it
        # is the environment. If it carries both, it is a failure -- the
        # conservative direction, because under-reporting a real regression is
        # the one way this verdict must never be wrong.
        if _missing_dependency(out) and not _ASSERTION.search(out):
            return "env"
        return "fail"
    return "env"


#: A dependency that is not installed, as pytest reports it. Each of these
#: arrived in a real run of this fleet's suites.
_ENV_SIGNS = (
    re.compile(r"fixture '\w+' not found"),                 # a pytest plugin
    re.compile(r"ModuleNotFoundError: No module named"),    # a package
    re.compile(r"\bis not importable\b"),                   # the register pin
    re.compile(r"ImportError: lib[\w.+-]+\.so"),            # a system library
)
#: A real regression. pytest prints the failing line under `E   ` and the
#: exception class in the summary.
_ASSERTION = re.compile(r"^E\s+assert\b|\bAssertionError\b", re.M)


def _missing_dependency(out: str) -> bool:
    return any(sign.search(out) for sign in _ENV_SIGNS)


#: verdict -> taxonomy. "abort" and "killed" are EXIT_INCOMPLETE rather than
#: EXIT_CANNOT_RUN: the environment WAS ready and the run started, which is a
#: different instruction to the operator -- re-run, do not go installing things.
_VERDICT_CODE = {
    "pass": EXIT_CLEAN,
    "fail": EXIT_DISAGREES,
    "env": EXIT_CANNOT_RUN,
    "abort": EXIT_INCOMPLETE,
    "killed": EXIT_INCOMPLETE,
}


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
    return _VERDICT_CODE[verdict]


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
    if code != EXIT_CLEAN:
        return code
    for label, args in SUITES:
        code = _step(label, args)
        if code != EXIT_CLEAN:
            return code
    print("\nGreen.")
    return EXIT_CLEAN


def apply(check_only: bool) -> int:
    root = Path.cwd()

    # FIRST. Before the sentinel, before any anchor. See the docstring.
    refuse_wrong_repository(root)

    if not (root / SENTINEL_FILE).exists():
        # A script whose sentinel file is created by an EARLIER script cannot
        # tell "wrong directory" from "prerequisite not run", and the default
        # message asserts the first while the second is more likely. Such a
        # script sets MISSING_HELP and says which one to run.
        raise Stop(globals().get("MISSING_HELP") or
                   f"run this from the root of a {REPO} checkout "
                   f"(no {SENTINEL_FILE} here)", EXIT_CANNOT_RUN)

    if SENTINEL in (root / SENTINEL_FILE).read_text(encoding="utf-8-sig"):
        # ALREADY APPLIED IS NOT AN ERROR, AND USED TO EXIT 1.
        #
        # The operator runs this from a phone and the honest question behind a
        # second run is "did this land?". Exiting 1 answered "something
        # disagreed", which is the one thing that had not happened. Re-running
        # the suites answers the question that was actually asked, and a
        # repository that has the change and passes its tests is CLEAN.
        print(f"already applied -- {SENTINEL!r} is present in "
              f"{SENTINEL_FILE}.\nNothing to write. Re-running the suites so "
              f"the answer is measured rather than assumed.\n")
        return verify()

    tree = Tree(root)
    edits(tree)

    # THE SCRIPT MUST WRITE ITS OWN SENTINEL WHERE apply() LOOKS FOR IT.
    #
    # Checked here, against the in-memory tree, before anything reaches disk.
    #
    # WHY THIS IS NOT A BUILD-TIME CHECK. The build's `sentinel-written` guard
    # asserts the marker appears at least twice in the composed script -- its
    # own declaration plus somewhere it gets written. That is a PROXY. A round
    # can carry the marker in a new guard file and never put it in
    # SENTINEL_FILE, and the build passes while the already-applied branch can
    # never fire. That shipped once, on 2026-09-24: the operator ran a landed
    # script a second time and got "expected 1 occurrence of the anchor, found
    # 0. The file moved" -- about a file that had not moved, from a script
    # that could not tell it had already run.
    #
    # Here the question is exact rather than approximated: after every edit,
    # is the marker in the file apply() reads? It fires on the FIRST run, in
    # the author's verification, rather than on the operator's second.
    if SENTINEL not in tree.read(SENTINEL_FILE):
        raise Stop(
            f"this script never writes {SENTINEL!r} into {SENTINEL_FILE}, "
            f"which is the file it reads to tell whether it has already run.\n"
            f"Applied once it would work; run again it would re-attempt "
            f"anchors that are already replaced and report them as missing.\n"
            f"Add an edit that marks {SENTINEL_FILE}. Nothing was written.",
            EXIT_CANNOT_RUN)
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
        _left_alone()
        return EXIT_CLEAN

    touched = tree.flush()
    print("wrote: " + ", ".join(touched) + "\n")
    code = verify()
    if code == EXIT_CLEAN:
        _left_alone()
    return code


def finish() -> None:
    me = Path(__file__).resolve()
    print(f"removing {me.name}")
    me.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--check", action="store_true",
                    help="rehearse every edit in memory, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run the suites only, change nothing")
    ap.add_argument("--finish", action="store_true", help="delete this script")
    args = ap.parse_args()
    try:
        refuse_to_shadow()
        if args.finish:
            finish()
            return EXIT_CLEAN
        if args.verify:
            return verify()
        return apply(args.check)
    except Stop as stop:
        # Print it ourselves and return the taxonomy code. Letting SystemExit
        # propagate would print the message and exit 1 regardless of .code.
        print(stop.args[0] if stop.args else "", file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    raise SystemExit(main())
