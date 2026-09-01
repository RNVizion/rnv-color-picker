#!/usr/bin/env python3
"""
RNV-BUTTON-NAMING-TOOL-DO-NOT-SWEEP

Rename the eight dialog button keys from button_* to dialog_btn_*.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

NOT ONE PIXEL MOVES. This is a rename and nothing else.

This application already ships two button schemes and keeps them properly
apart: main_btn_* is the black-and-white main window with its inverting
transition, and button_* is the gold scheme its dialogs use. The values are
right. The name is not.

`button_*` means the GOLD DIALOG scheme here and in rnv-icon-builder, and the
BLACK-AND-WHITE MAIN scheme in rnv-color-palette-manager, rnv-color-mixer and
rnv-text-transformer. One name, two schemes, decided by which repository you
happen to have open -- and a name that cannot be carried into a new project is
not a standard. After this pass the name says where the button lives:

    main_btn_*     the main window at launch
    dialog_btn_*   anything that opens later

WHAT MOVES

Sixty-five quoted occurrences in eleven files: both palettes in utils/config.py,
the four dialog modules that read them, and five test modules. main_btn_* is
not touched.

DOCUMENTATION IS NOT TOUCHED, ON PURPOSE

The docs pass runs once, after alignment settles, so it is written against the
finished state rather than chased through it. The guard sweeps code and
snapshots, not prose, for the same reason.

WHAT THE GUARD ASSERTS

tests/test_button_key_names.py fails if an old name comes back, if either
palette loses a new one, if any of the sixteen dialog values moved, if the
main family moved, or if the two families ever converge on one scheme -- two
families holding the same scheme is one family with extra steps.

It reads the palettes by importing them rather than by parsing them. Light's
dialog_btn_hover_text is BRAND_DARK_GOLD_DEEP, derived through lighten()
rather than written as a literal, and a static resolver returns None for it,
then compares None with None and passes. That failure mode has appeared twice
in this programme already.
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
DESCRIPTION = "rename the dialog button keys to dialog_btn_*"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "'dialog_btn_bg'"
GUARD = "tests/test_button_key_names.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ('pytest tests/',
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ('unittest suite',
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

OLD_KEYS = ("button_bg", "button_text", "button_hover_bg", "button_hover_text",
            "button_hover_border", "button_pressed_bg", "button_pressed_text",
            "button_border")
RENAME = {k: "dialog_btn_" + k[len("button_"):] for k in OLD_KEYS}

#: path -> how many QUOTED occurrences that file holds. Written down so the
#: script refuses to run against a tree that has moved under it.
QUOTED = {
    "utils/config.py": 16,
    "utils/dialog_helper.py": 21,
    "ui/about_dialog.py": 10,
    "ui/settings_panel.py": 9,
    "ui/progress_dialog.py": 3,
    "test_rnv_color_picker.py": 1,
    "tests/test_app_mirror.py": 1,
    "tests/test_brand_contrast.py": 2,
    "tests/test_ladder_and_plate.py": 2,
}

_QUOTED_RE = re.compile(r"(['\"])(" + "|".join(sorted(RENAME, key=len, reverse=True))
                        + r")\1")


def _rename_quoted(text: str) -> tuple[str, int]:
    hits = 0

    def swap(m: re.Match) -> str:
        nonlocal hits
        hits += 1
        return f"{m.group(1)}{RENAME[m.group(2)]}{m.group(1)}"

    return _QUOTED_RE.sub(swap, text), hits


def _palette_values(source: str) -> list[dict[str, str]]:
    """{key: the value EXPRESSION as written} for every palette dict.

    Deliberately not resolved to a colour. This runs before the files are
    written, so it cannot import anything, and half these values are names or
    derived calls that a static resolver turns into None. Comparing the
    expression text answers the only question --  did anything but the key
    change? -- without pretending to know what the expression evaluates to.
    """
    # This repository's sources carry UTF-8 BOMs. Tree.read decodes as plain
    # utf-8 so the round-trip preserves them byte for byte, which means the
    # marker arrives here as a character and ast.parse refuses it.
    out = []
    for node in ast.walk(ast.parse(source.lstrip("\ufeff"))):
        if not isinstance(node, ast.Dict):
            continue
        pairs = {k.value: ast.unparse(v) for k, v in zip(node.keys, node.values)
                 if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        if any(name in pairs for name in list(RENAME) + list(RENAME.values())):
            out.append(pairs)
    return out


def edits(tree) -> None:
    total = 0
    for rel, expected in QUOTED.items():
        new, hits = _rename_quoted(tree.read(rel))
        if hits != expected:
            raise SystemExit(f"{rel}: expected {expected} quoted key(s), found "
                             f"{hits}. The file moved; re-derive this edit "
                             f"before trusting the script.")
        tree.write(rel, new)
        total += hits
    print(f"  renamed {total} quoted keys in {len(QUOTED)} files")


def checks(tree) -> None:
    for rel in QUOTED:
        text = tree.read(rel)
        for old in RENAME:
            if re.search(r"(['\"])" + old + r"\1", text):
                raise SystemExit(f"{rel}: {old!r} survived the rename")

    original = (Path.cwd() / SENTINEL_FILE).read_text(encoding="utf-8")
    edited = tree.read(SENTINEL_FILE)

    if edited.count("\n") != original.count("\n"):
        raise SystemExit(
            f"utils/config.py changed shape: {original.count(chr(10))} lines "
            f"before, {edited.count(chr(10))} after. A substitution adds and "
            f"removes nothing.")

    before, after = _palette_values(original), _palette_values(edited)
    if not before or len(before) != len(after):
        raise SystemExit(f"expected the same number of palettes before and "
                         f"after; found {len(before)} and {len(after)}")

    for old_palette, new_palette in zip(before, after):
        for old_name, new_name in RENAME.items():
            if old_name not in old_palette:
                continue
            if new_name not in new_palette:
                raise SystemExit(f"{new_name} missing after the rename")
            if old_palette[old_name] != new_palette[new_name]:
                raise SystemExit(
                    f"{old_name} -> {new_name} changed its value expression:\n"
                    f"  before {old_palette[old_name]}\n"
                    f"  after  {new_palette[new_name]}\n"
                    f"A rename that changes a value is not a rename.")
        # and nothing ELSE in the palette moved either
        untouched_before = {k: v for k, v in old_palette.items()
                            if k not in RENAME}
        untouched_after = {k: v for k, v in new_palette.items()
                           if k not in RENAME.values()}
        if untouched_before != untouched_after:
            differing = {k for k in set(untouched_before) | set(untouched_after)
                         if untouched_before.get(k) != untouched_after.get(k)}
            raise SystemExit(f"keys outside the rename changed: {sorted(differing)}")

    main_family = sum(1 for p in after for k in p if k.startswith("main_btn_"))
    if main_family == 0:
        raise SystemExit("the main button family vanished from utils/config.py")
    print(f"  guards: no old name survives, every value expression identical, "
          f"{main_family} main_btn_* entries untouched")


GUARD_SOURCE = r'''"""The button keys say where the button lives.

RNV-BUTTON-NAMING-GUARD

main_btn_* is the main window at launch. dialog_btn_* is anything that opens
later. This application ships both schemes -- black-and-white in the main
window, gold in the dialogs -- and until this pass the dialog family was called
button_*, a name that means the MAIN scheme in three of the other four
applications. The rename is what makes the name portable; these tests are what
stop it drifting back.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OLD = ("button_bg", "button_text", "button_hover_bg", "button_hover_text",
       "button_hover_border", "button_pressed_bg", "button_pressed_text",
       "button_border")
NEW = tuple("dialog_btn_" + n[len("button_"):] for n in OLD)

MAIN = ("main_btn_bg", "main_btn_text", "main_btn_border", "main_btn_hover_bg",
        "main_btn_hover_text", "main_btn_pressed_bg", "main_btn_pressed_text")

#: The sixteen dialog values, pinned. A rename that moves one is not a rename.
PINNED_DIALOG = {
    "dark": {"dialog_btn_bg": "#2a2a2a", "dialog_btn_text": "#dddddd",
             "dialog_btn_hover_bg": "#3a3a3a", "dialog_btn_hover_text": "#d2bc93",
             "dialog_btn_hover_border": "#d2bc93", "dialog_btn_pressed_bg": "#d2bc93",
             "dialog_btn_pressed_text": "#000000", "dialog_btn_border": "#333333"},
    "light": {"dialog_btn_bg": "#ffffff", "dialog_btn_text": "#000000",
              "dialog_btn_hover_bg": "#eeeeee", "dialog_btn_hover_text": "#7e6529",
              "dialog_btn_hover_border": "#8c7337", "dialog_btn_pressed_bg": "#8c7337",
              "dialog_btn_pressed_text": "#ffffff", "dialog_btn_border": "#cccccc"},
}

#: The main family is not touched by this pass, and saying so is the point:
#: these two schemes are what the naming exists to keep apart.
PINNED_MAIN = {
    "dark": {"main_btn_bg": "#1a1a1a", "main_btn_text": "#dddddd",
             "main_btn_border": "#333333", "main_btn_hover_bg": "#333333",
             "main_btn_hover_text": "#dddddd", "main_btn_pressed_bg": "#444444",
             "main_btn_pressed_text": "#000000"},
    "light": {"main_btn_bg": "#ffffff", "main_btn_text": "#000000",
              "main_btn_border": "#cccccc", "main_btn_hover_bg": "#333333",
              "main_btn_hover_text": "#000000", "main_btn_pressed_bg": "#444444",
              "main_btn_pressed_text": "#ffffff"},
}

SKIP = {".git", "build", "dist", ".venv", "__pycache__"}

#: A sweep for a name cannot tell a USE of that name from a MENTION of it, and
#: the two files certain to mention it are this guard -- which lists the old
#: names in order to forbid them -- and the delivery script that performs the
#: rename. Both are skipped by marker rather than by filename, because the
#: delivery script arrives under whatever name it is saved as.
MARKERS = ("RNV-BUTTON-NAMING-GUARD", "RNV-BUTTON-NAMING-TOOL-DO-NOT-SWEEP")


def _palettes():
    """Read the palettes the way the application reads them.

    Static resolution is not enough here: light's dialog_btn_hover_text is
    BRAND_DARK_GOLD_DEEP, which is derived by lighten() rather than written as
    a literal, and an AST resolver returns None for it -- then compares None
    with None and passes.
    """
    from utils.config import DARK_THEME_COLORS, LIGHT_THEME_COLORS
    return {"dark": DARK_THEME_COLORS, "light": LIGHT_THEME_COLORS}


def _sources():
    for path in sorted(ROOT.rglob("*")):
        # Prose is not swept. docs/ is updated in one pass after alignment
        # settles, so it names the old keys until then, and a guard that failed
        # on that would be failing on a decision rather than a defect.
        if path.is_dir() or path.suffix not in (".py", ".ambr"):
            continue
        if any(part in SKIP for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(marker in text for marker in MARKERS):
            continue
        yield path, text


def test_no_old_button_key_name_survives():
    offenders = []
    for path, text in _sources():
        for old in OLD:
            if re.search(r"(['\"])" + old + r"\1", text):
                offenders.append(f"{path.relative_to(ROOT)}: {old}")
    assert not offenders, (
        "these are dialog button keys and must be named dialog_btn_*:\n  "
        + "\n  ".join(offenders))


def test_the_marker_exemption_covers_only_the_two_tools():
    """An exemption that grows silently is how a guard stops guarding."""
    marked = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(marker in text for marker in MARKERS):
            marked.append(path.relative_to(ROOT))
    assert len(marked) <= 2, f"unexpected marked file(s): {marked}"
    assert Path(__file__).relative_to(ROOT) in marked


def test_both_palettes_carry_the_new_dialog_names():
    for mode, palette in _palettes().items():
        missing = [n for n in NEW if n not in palette]
        assert not missing, f"{mode} palette missing {missing}"


def test_the_rename_moved_no_dialog_value():
    for mode, pins in PINNED_DIALOG.items():
        palette = _palettes()[mode]
        actual = {k: palette.get(k) for k in pins}
        assert actual == pins, (
            f"the {mode} dialog button values changed.\n"
            f"  wanted {pins}\n  found  {actual}\n"
            "A rename that changes a value is not a rename.")


def test_the_main_family_is_untouched():
    for mode, pins in PINNED_MAIN.items():
        palette = _palettes()[mode]
        actual = {k: palette.get(k) for k in pins}
        assert actual == pins, (
            f"the {mode} main button values changed. This pass renames the "
            f"DIALOG family and must not reach the main window.\n"
            f"  wanted {pins}\n  found  {actual}")


def test_the_two_schemes_are_still_different():
    """If the families ever converge, the naming stops carrying information.

    Not a style rule: the main button is black-and-white with an inverting
    transition, the dialog button is gold. They differ at rest, at hover and
    at press, in both modes, and that is the whole reason for two families.
    """
    for mode, palette in _palettes().items():
        for main, dialog in (("main_btn_hover_text", "dialog_btn_hover_text"),
                             ("main_btn_pressed_bg", "dialog_btn_pressed_bg")):
            assert palette[main] != palette[dialog], (
                f"{mode}: {main} and {dialog} now hold the same value "
                f"({palette[main]}). Two families holding one scheme is one "
                f"family with extra steps.")


def test_the_main_window_still_reads_the_main_family():
    for rel in ("RNV_Color_Picker.py", "utils/cache.py"):
        src = (ROOT / rel).read_text(encoding="utf-8-sig")
        assert "'main_btn_bg'" in src, f"{rel} no longer reads main_btn_bg"


def test_the_dialogs_read_the_dialog_family():
    for rel in ("utils/dialog_helper.py", "ui/about_dialog.py",
                "ui/progress_dialog.py", "ui/settings_panel.py"):
        src = (ROOT / rel).read_text(encoding="utf-8-sig")
        assert "dialog_btn_" in src, f"{rel} no longer reads the dialog family"
        assert "'main_btn_" not in src, (
            f"{rel} reads the main family. Dialogs open later and take the "
            f"gold scheme; wiring one to main_btn_* fuses the two.")
'''


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
