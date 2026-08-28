#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Name the APP register in rnv-color-picker, and move the dark ink onto the grid.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

WHAT MOVES

  DARK  text_primary, button_text, main_btn_text, main_btn_hover_text,
        tooltip_text, swatch_border_color   #e0e0e0 -> APP_TEXT (#dddddd)

        swatch_border_color is an EDGE, not an ink. The published grid governs
        inks AND edges, which is why it moves rather than being left behind.

  IMAGE inherits, because IMAGE_MODE_COLORS spreads DARK_THEME_COLORS.

  LIGHT pressed_bg, tab_bg, scrollbar_bg      UNCHANGED at #e0e0e0.

WHY THE VALUE MOVED, AND WHY ONLY HALF OF IT

#e0e0e0 was one hex doing two unrelated jobs: ink in dark mode, and a light
surface in the light palette. It sat off the published ink grid at n = 13.18
and refused to be pulled onto it -- because the grid governs inks and half its
uses were not ink. Split the roles and both halves land: the ink moves to
grey(13) #dddddd, the surface stays where it is. rnv-brand@68d195e publishes
both the move and the rule, including the sentence that the grid does not
govern surfaces and never can.

WHY THE NAMING HAD TO COME FIRST

This app held #e0e0e0 -- and #1a1a1a, #2a2a2a, #333333 -- as bare literals
with no constant and no provenance. The brand could have moved and nothing
here would have noticed. Naming them without moving anything would have been
half a job; moving them without naming them would have left nothing holding
the new value. So the same pass does both, and the guard asserts the ink is
spelled as a NAME rather than a value.

TWO GUARDS, NOT ONE

rnv-text-transformer's mirror test guards with importorskip('engine.brand'),
so where rnv-brand is not importable it reports clean and drift hides. Every
register value is therefore pinned locally as well as mirrored upstream. The
pin catches drift when the brand is absent; the mirror catches the brand
moving. Neither alone is enough, and this one nearly proved it.

THE OTHER FIVE CONSTANTS ARE DEFINED BUT NOT YET WIRED. That is deliberate and
said out loud in ui/colors.py: rewiring them is a mechanical substitution and
this pass is a value change. Mixing the two would make the diff unreadable and
the snapshot evidence worthless.
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
DESCRIPTION = "name the APP register and move the dark ink to grey(13)"
SENTINEL_FILE = "utils/config.py"
SENTINEL = 'APP_TEXT: Final[str] = "#dddddd"'
GUARD = "tests/test_app_mirror.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ("pytest tests/ (about 8 minutes)",
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ("unittest suite",
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

ANCHOR = ("\n\n# ============================================================"
          "================\n# STATUS RED\n")

INK_KEYS = ("text_primary", "button_text", "main_btn_text",
            "main_btn_hover_text", "tooltip_text", "swatch_border_color")
OLD_INK = "'#e0e0e0'"
NEW_INK = "APP_TEXT"

APP_BLOCK = '\n\n# ==================== APP Neutrals ====================\n#\n# MIRRORED FROM RNVizion/rnv-brand engine/brand.py APP. Until 2026-08-28 these\n# were bare hex literals in the palettes below -- no constant, no provenance --\n# and every one of them is a REGISTERED brand value. A registered value could\n# move upstream and this app would keep the old one silently, which is the\n# failure #c4a458 had, one level down. It nearly happened: APP["text"] moved\n# from #e0e0e0 to #dddddd in rnv-brand@68d195e.\n#\n# THE INK GRID, published in the brand beside that move:\n#\n#     grey(n) = n * 0x11, n in 0..15.   TRUE_BLACK -> WHITE in fifteen steps.\n#\n# IT GOVERNS INKS AND EDGES AND DELIBERATELY DOES NOT GOVERN SURFACES.\n# BRAND_BLACK sits at n = 1.53 and APP_CARD at n = 2.47; BRAND_BLACK is a\n# permanent and will not move to fit a ladder. The scope is part of the rule.\n#\n# THIS PASS WIRES THE INK ONLY. The other five constants are defined and\n# mirrored here so drift is caught, but the palettes below still spell them as\n# literals; rewiring those is the grey-ramp derivation pass, and doing it here\n# would have mixed a mechanical substitution into a value change.\n\nTRUE_BLACK: Final[str] = "#000000"\n"""engine/brand.py TRUE_BLACK, and APP["window"]. Primary text in light mode,\nand the label on a pressed control in dark. grey(0)."""\n\nWHITE: Final[str] = "#ffffff"\n"""engine/brand.py WHITE. Control surface in light mode. grey(15)."""\n\nBRAND_BLACK: Final[str] = "#1a1a1a"\n"""engine/brand.py BRAND_BLACK, and APP["panel"]. Charcoal; a permanent.\nNot on the ink grid (n = 1.53) and not required to be -- it is a surface."""\n\nAPP_CARD: Final[str] = "#2a2a2a"\n"""engine/brand.py APP["card"]. A surface, not on the grid (n = 2.47)."""\n\nAPP_BORDER: Final[str] = "#333333"\n"""engine/brand.py APP["border"]. grey(3). An edge, so the grid governs it."""\n\nAPP_TEXT: Final[str] = "#dddddd"\n"""engine/brand.py APP["text"]. grey(13). Primary ink in dark and image mode.\n\nMOVED FROM #e0e0e0 ON 2026-08-28, with the brand rather than after it.\n#e0e0e0 was one hex doing two unrelated jobs -- ink in dark mode, and a light\nSURFACE in the light palette below. It refused to sit on the grid because the\ngrid governs inks and half its uses were not ink. Only the ink half moved.\nContrast falls 0.21 to 0.45 and the floor afterwards is 7.17:1 on the pressed\nplate #444444, the darkest ground it is ever drawn on.\n"""\n\nAPP_TEXT_DIM: Final[str] = "#aaaaaa"\n"""engine/brand.py APP["text-dim"]. grey(10)."""\n\nAPP_PROVENANCE: Final[dict[str, str]] = {\n    "TRUE_BLACK": "register",\n    "WHITE": "register",\n    "BRAND_BLACK": "register",\n    "APP_CARD": "register",\n    "APP_BORDER": "register",\n    "APP_TEXT": "register",\n    "APP_TEXT_DIM": "register",\n}\n"""Declarative, and read by tests/test_app_mirror.py. A classification that\nlives only in a test drifts from the thing it classifies."""\n\n'


def _bounds(lines):
    """DARK and LIGHT carry identically-spelled key lines, so a plain string
    replace cannot tell them apart. Every edit is scoped to its own dict."""
    starts = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(DARK_THEME_COLORS|LIGHT_THEME_COLORS|IMAGE_MODE_COLORS)\s*:", line)
        if m:
            starts[m.group(1)] = i
    if len(starts) != 3:
        raise SystemExit(f"expected three theme dicts, found {sorted(starts)}")
    order = sorted(starts.items(), key=lambda kv: kv[1])
    return {n: (st, order[i + 1][1] if i + 1 < len(order) else len(lines))
            for i, (n, st) in enumerate(order)}


def _set(lines, span, key, expect, value):
    st, en = span
    hits = [i for i in range(st, en) if lines[i].strip().startswith(f"'{key}':")]
    if len(hits) != 1:
        raise SystemExit(f"expected one '{key}' in that palette, found {len(hits)}")
    if expect not in lines[hits[0]]:
        raise SystemExit(f"'{key}' is not {expect}: {lines[hits[0]].strip()!r}")
    lines[hits[0]] = lines[hits[0]].replace(expect, value)


def edits(tree) -> None:
    src = tree.read(SENTINEL_FILE)
    if src.count(ANCHOR) != 1:
        raise SystemExit("could not find the single STATUS RED heading; "
                         "the file moved, re-derive this edit")
    src = src.replace(ANCHOR, APP_BLOCK + ANCHOR.lstrip("\n"), 1)

    lines = src.splitlines(keepends=True)
    b = _bounds(lines)
    for key in INK_KEYS:
        _set(lines, b["DARK_THEME_COLORS"], key, OLD_INK, NEW_INK)
    tree.write(SENTINEL_FILE, "".join(lines))


def checks(tree) -> None:
    src = tree.read(SENTINEL_FILE)
    if src.count(SENTINEL) != 1:
        raise SystemExit("APP_TEXT was not defined exactly once")
    for key in INK_KEYS:
        # These palettes align their values in a column, so the gap after the
        # colon is not one space. Matching on a fixed string here is how a
        # correct edit gets reported as a failure.
        if not re.search(rf"'{key}':\s+APP_TEXT,", src):
            raise SystemExit(f"dark {key} does not read APP_TEXT")
    # The light surfaces must survive untouched -- three of them.
    if src.count(OLD_INK) != 3:
        raise SystemExit(
            f"expected exactly three surviving #e0e0e0 (the light surfaces), "
            f"found {src.count(OLD_INK)}")
    if "APP_TEXT: Final[str] = \"#e0e0e0\"" in src:
        raise SystemExit("APP_TEXT still holds the old ink")


GUARD_SOURCE = '"""\nThe APP register, mirrored -- and the ink move that made mirroring necessary.\n\nWHY THIS FILE EXISTS. Until 2026-08-28 this app carried #e0e0e0, #1a1a1a,\n#2a2a2a and #333333 as bare hex literals with no constant and no provenance.\nEvery one of them is a REGISTERED value in RNVizion/rnv-brand. A registered\nvalue could have moved upstream and this app would have kept the old one\nsilently -- the same failure #c4a458 had, one level down.\n\nIt nearly happened. `APP["text"]` moved from #e0e0e0 to #dddddd in\nrnv-brand@68d195e, and nothing here would have noticed.\n\nTHE INK GRID, published in the brand beside that move:\n\n    grey(n) = n * 0x11, n in 0..15.   TRUE_BLACK -> WHITE in fifteen steps.\n\nIt governs INKS AND EDGES and deliberately does not govern surfaces --\nBRAND_BLACK sits at n = 1.53 and APP_CARD at n = 2.47, and BRAND_BLACK is a\npermanent that will not move to fit a ladder.\n\nTWO GUARDS, NOT ONE. rnv-text-transformer\'s mirror test guards with\n`pytest.importorskip(\'engine.brand\')`, so where rnv-brand is not importable it\nreports clean and drift hides. Every register value here is therefore pinned\nLOCALLY as well as mirrored UPSTREAM: the pin catches drift when the brand is\nabsent, the mirror catches the brand moving. Neither alone is enough.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\n\nimport pytest\n\nfrom utils import config as colors\nfrom utils.config import (DARK_THEME_COLORS as DARK, IMAGE_MODE_COLORS as IMAGE,\n                       LIGHT_THEME_COLORS as LIGHT)\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nSRC = ROOT / \'utils\' / \'config.py\'\n\nGRID_STEP = 0x11\n\n#: What the brand register held on 2026-08-28, written down so this file still\n#: has an opinion when engine.brand cannot be imported.\nPINNED = {\n    \'TRUE_BLACK\': \'#000000\',\n    \'WHITE\': \'#ffffff\',\n    \'BRAND_BLACK\': \'#1a1a1a\',\n    \'APP_CARD\': \'#2a2a2a\',\n    \'APP_BORDER\': \'#333333\',\n    \'APP_TEXT\': \'#dddddd\',\n    \'APP_TEXT_DIM\': \'#aaaaaa\',\n}\n\n#: Dark-mode ink and edge. These carry APP_TEXT and must reference it by name.\n#: swatch_border_color is an EDGE rather than an ink -- the grid governs both,\n#: which is why it moves with the text instead of being left behind.\nINK_KEYS = (\'text_primary\', \'button_text\', \'main_btn_text\',\n            \'main_btn_hover_text\', \'tooltip_text\', \'swatch_border_color\')\n\n#: The other half of #e0e0e0\'s old double life: a LIGHT surface, which the\n#: grid does not govern and which did not move.\nLIGHT_SURFACE_KEYS = (\'pressed_bg\', \'tab_bg\', \'scrollbar_bg\')\n\n\ndef grey(n: int) -> str:\n    v = n * GRID_STEP\n    return \'#%02x%02x%02x\' % (v, v, v)\n\n\ndef _dict_node(name: str) -> ast.Dict:\n    tree = ast.parse(SRC.read_text(encoding=\'utf-8-sig\'))\n    for node in ast.walk(tree):\n        if isinstance(node, (ast.Assign, ast.AnnAssign)):\n            target = node.targets[0] if isinstance(node, ast.Assign) else node.target\n            if getattr(target, \'id\', None) == name and isinstance(node.value, ast.Dict):\n                return node.value\n    raise AssertionError(f\'{name} is not a dict literal in utils/config.py\')\n\n\ndef _entry(node: ast.Dict, key: str) -> ast.AST | None:\n    for k, v in zip(node.keys, node.values):\n        if isinstance(k, ast.Constant) and k.value == key:\n            return v\n    return None\n\n\n# ------------------------------------------------------------- guard the guard\n\ndef test_the_keys_this_file_reads_still_exist():\n    """Every assertion below reads these. If a key is renamed, this fails\n    loudly instead of the rest quietly passing over nothing."""\n    for key in INK_KEYS:\n        assert key in DARK, f\'DARK has no {key}\'\n    for key in LIGHT_SURFACE_KEYS:\n        assert key in LIGHT, f\'LIGHT has no {key}\'\n    for name in PINNED:\n        assert hasattr(colors, name), f\'utils.config has no {name}\'\n\n\n# ------------------------------------------------------------------- the value\n\ndef test_the_ink_is_a_step_on_the_grid():\n    assert colors.APP_TEXT == grey(13) == \'#dddddd\', (\n        f\'APP_TEXT is {colors.APP_TEXT}, not grey(13). The ink grid admits no \'\n        f\'exceptions -- see rnv-brand engine/brand.py APP.\')\n\n\ndef test_every_pinned_neutral_is_what_the_register_held():\n    """The local half of the mirror. Runs everywhere, including where\n    engine.brand is not importable."""\n    drift = {n: getattr(colors, n) for n, v in PINNED.items()\n             if getattr(colors, n) != v}\n    assert not drift, (\n        f\'these constants no longer hold their registered values: {drift}\\n\'\n        f\'If the brand moved, update PINNED here in the same commit that \'\n        f\'updates utils/config.py -- never one without the other.\')\n\n\ndef test_register_values_match_rnv_brand():\n    """The upstream half. Skips where rnv-brand is not importable, which is\n    exactly why the pin above is not optional."""\n    brand = pytest.importorskip(\n        \'engine.brand\',\n        reason=\'rnv-brand not importable here; the local pin is doing the work\')\n    drift = []\n    for name in PINNED:\n        if name.startswith(\'APP_\'):\n            theirs = brand.APP[name[4:].lower().replace(\'_\', \'-\')]\n        else:\n            theirs = getattr(brand, name)\n        mine = getattr(colors, name)\n        if mine.lower() != theirs.lower():\n            drift.append(f\'{name}: ours {mine}, theirs {theirs}\')\n    assert not drift, \'drift from rnv-brand:\\n  \' + \'\\n  \'.join(drift)\n\n\n# --------------------------------------------------- the ink references the name\n\ndef test_every_dark_ink_reads_the_constant_not_a_literal():\n    """A literal cannot follow its base. This is the whole point of the pass:\n    if APP_TEXT moves again, these move with it or this test fails."""\n    node = _dict_node(\'DARK_THEME_COLORS\')\n    literals = []\n    for key in INK_KEYS:\n        value = _entry(node, key)\n        if not (isinstance(value, ast.Name) and value.id == \'APP_TEXT\'):\n            literals.append(f\'{key} = {ast.unparse(value) if value else "missing"}\')\n    assert not literals, (\n        \'dark ink entries still written as literals:\\n  \' + \'\\n  \'.join(literals))\n\n\ndef test_the_resolved_ink_is_the_constant():\n    """The AST check above proves the spelling; this proves the value."""\n    for key in INK_KEYS:\n        assert DARK[key] == colors.APP_TEXT, f\'DARK[{key!r}] is {DARK[key]}\'\n\n\ndef test_image_mode_inherits_the_dark_ink():\n    """IMAGE_MODE_COLORS spreads DARK_THEME_COLORS, so the move carries. Stated\n    rather than assumed: if that spread is ever replaced by a literal block,\n    this is what says so."""\n    for key in INK_KEYS:\n        assert IMAGE[key] == colors.APP_TEXT, (\n            f\'IMAGE[{key!r}] is {IMAGE[key]}, not the dark ink -- image mode \'\n            f\'has stopped inheriting from DARK_THEME_COLORS\')\n\n\n# ------------------------------------------------------------- what did NOT move\n\ndef test_the_light_surfaces_did_not_follow_the_ink():\n    """#e0e0e0 was one hex doing two jobs. Only the ink half moved; the light\n    half is a SURFACE, and the grid does not govern surfaces."""\n    for key in LIGHT_SURFACE_KEYS:\n        assert LIGHT[key] == \'#e0e0e0\', (\n            f\'LIGHT[{key!r}] is {LIGHT[key]}. That is a light surface, not ink \'\n            f\'-- it was deliberately left behind when the ink moved to grey(13).\')\n\n\ndef test_the_light_ink_is_true_black():\n    """Primary text is one role with two mode values: dark is a grey on the\n    grid, light is TRUE_BLACK."""\n    assert LIGHT[\'text_primary\'] == colors.TRUE_BLACK == \'#000000\'\n\n\n# ---------------------------------------------------------------- what it costs\n\ndef _luminance(value: str) -> float:\n    channels = [int(value.lstrip(\'#\')[i:i + 2], 16) / 255 for i in (0, 2, 4)]\n    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4\n                for c in channels]\n    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]\n\n\ndef _contrast(a: str, b: str) -> float:\n    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)\n    return (high + 0.05) / (low + 0.05)\n\n\ndef test_the_ink_clears_the_text_floor_on_every_dark_ground_it_touches():\n    """Measured, not assumed. The darkest ground the ink is drawn on is the\n    pressed plate; everything else has more room."""\n    grounds = (\'#000000\', \'#1a1a1a\', \'#2a2a2a\', \'#333333\', \'#3a3a3a\', \'#444444\')\n    worst = min((_contrast(colors.APP_TEXT, g), g) for g in grounds)\n    assert worst[0] >= 4.5, (\n        f\'the ink falls to {worst[0]:.2f}:1 on {worst[1]}, under the 4.5 floor\')\n'


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
