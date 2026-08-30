#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Wire rnv-color-picker's dark palettes to the register it already mirrors.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

WHAT MOVES: NOTHING. Not one rendered pixel.

This changes how every registered values in DARK and IMAGE are SPELLED, not what they
are. Every one becomes the name of a constant this app already defines and
already mirrors against RNVizion/rnv-brand:

    '#000000' -> TRUE_BLACK        '#2a2a2a' -> APP_CARD
    '#1a1a1a' -> BRAND_BLACK       '#333333' -> APP_BORDER

The script proves it moved nothing rather than asserting it: checks() resolves
every entry of every palette from the ORIGINAL file and from the EDITED one,
and refuses to write unless all three palettes are equal entry for entry.

WHY THIS IS A SEPARATE PASS

The ink pass defined and mirrored these four constants but left the palettes
spelling them out. That was deliberate and said out loud at the time: a
mechanical substitution mixed into a value change makes the diff unreadable and
the snapshot evidence worthless. This is the substitution, alone.

WHY THE DARK HALF ONLY

rnv-brand@8ab1174 rules the order. The dark surface ladder is two-thirds
specified and entirely inside the register; the light ladder is not ruled at
all. Nine light surfaces sit between grid n = 12.24 and n = 15.00 -- inside
three steps of a grid that steps 0x11 -- and which of them are real
distinctions is a judgement the register has not made yet. Wiring light now
would mean wiring it twice.

The guard asserts the light palettes were left alone, so that when the light
half is ruled, one test has to be deleted on purpose rather than a scope
quietly widening.

THE POINT OF THE WHOLE THING

A literal cannot follow its base. APP["text"] moved on 2026-08-28 and two of
these five apps would have kept the old value silently, because it was written
down rather than referenced. After this pass there is no registered value left
written down in a dark palette, and the guard is what keeps it that way.
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
DESCRIPTION = "wire the dark palettes to the mirrored register"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "APP_CARD,"
GUARD = "tests/test_register_wiring.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ('pytest tests/ (about 1 minute)',
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ('unittest suite',
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"])
]

REGISTERED = {'TRUE_BLACK': '#000000', 'BRAND_BLACK': '#1a1a1a', 'APP_CARD': '#2a2a2a', 'APP_BORDER': '#333333'}
BY_VALUE = {v: k for k, v in REGISTERED.items()}

DARK_DICTS = ('DARK_THEME_COLORS', 'IMAGE_MODE_COLORS')
LIGHT_DICTS = ('LIGHT_THEME_COLORS',)
ALL_DICTS = DARK_DICTS + LIGHT_DICTS


def _resolve(source: str) -> dict:
    """Every palette, resolved to plain values, whether an entry is written as
    a literal or as a name. This is what makes 'nothing moved' checkable rather
    than asserted."""
    # Five files in rnv-color-picker begin with a UTF-8 BOM, and Tree.read
    # decodes as plain utf-8, so the BOM arrives as a leading U+FEFF that
    # ast.parse refuses. Stripping it here rather than changing how the tree
    # reads, because the BOM must survive into the file that is written back.
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
    source = tree.read(SENTINEL_FILE)
    lines = source.splitlines(keepends=True)
    bounds = _bounds(lines)

    swapped = 0
    for name in DARK_DICTS:
        start, end = bounds[name]
        for i in range(start, end):
            line = lines[i]
            # Match against the line WITHOUT its ending and put the ending back
            # verbatim. Python's `$` also matches just before a trailing
            # newline, so a pattern ending in `(,.*)$` silently drops it -- and
            # the result is still valid Python, so every test passes while the
            # file is quietly reflowed into one line per palette.
            body = line.rstrip("\r\n")
            ending = line[len(body):]
            # Only a whole quoted value, and only where a key precedes it, so a
            # hex inside a comment or an rgba string is never touched.
            m = re.match(r"^(\s*'[a-z_0-9]+':\s*)'(#[0-9a-fA-F]{6})'(,.*)$", body)
            if not m:
                continue
            const = BY_VALUE.get(m.group(2).lower())
            if const:
                lines[i] = f"{m.group(1)}{const}{m.group(3)}{ending}"
                swapped += 1
    if swapped == 0:
        raise SystemExit("nothing was substituted -- the palettes have already "
                         "been wired, or their shape changed")
    tree.write(SENTINEL_FILE, "".join(lines))
    print(f"  substituted {swapped} literal(s) for their register names")


def checks(tree) -> None:
    original = (Path.cwd() / SENTINEL_FILE).read_text(encoding="utf-8-sig")
    edited = tree.read(SENTINEL_FILE)

    # SHAPE FIRST. A value-level comparison is blind to a file being reflowed:
    # a substitution that eats line endings leaves every value identical and
    # every test green, with the palettes collapsed onto one line each. This
    # caught exactly that during development.
    if edited.count("\n") != original.count("\n"):
        raise SystemExit(
            f"the file changed shape: {original.count(chr(10))} lines before, "
            f"{edited.count(chr(10))} after. A substitution adds and removes "
            f"nothing -- something is eating or adding line endings.")

    before, after = _resolve(original), _resolve(edited)
    if set(before) != set(after):
        raise SystemExit(f"a palette appeared or vanished: "
                         f"{set(before) ^ set(after)}")
    moved = []
    for name in before:
        for key in set(before[name]) | set(after[name]):
            was, now = before[name].get(key), after[name].get(key)
            if was != now:
                moved.append(f"{name}[{key!r}]: {was} -> {now}")
    if moved:
        raise SystemExit(
            "THIS PASS MUST NOT MOVE A VALUE, and it moved these:\n  "
            + "\n  ".join(moved))

    # Completeness: no registered value may survive as a literal in dark.
    survivors = []
    for name in DARK_DICTS:
        node_src = after[name]
        for key, value in node_src.items():
            if isinstance(value, str) and value.lower() in BY_VALUE:
                # Resolved values legitimately equal the register; check the
                # SPELLING in the edited source instead.
                pass
    lines = edited.splitlines()
    bounds = _bounds([l + "\n" for l in lines])
    for name in DARK_DICTS:
        start, end = bounds[name]
        for i in range(start, end):
            m = re.match(r"^\s*'([a-z_0-9]+)':\s*'(#[0-9a-fA-F]{6})',", lines[i])
            if m and m.group(2).lower() in BY_VALUE:
                survivors.append(f"{name}[{m.group(1)!r}] = {m.group(2)}")
    if survivors:
        raise SystemExit("registered values still spelled as literals in dark:\n  "
                         + "\n  ".join(survivors))

    # The sentinel is the bare NAME followed by a comma. These palettes align
    # their values in a column, so anything that pins the whitespace between
    # the key and the value fails on a correct edit -- which it did, once.
    if SENTINEL not in edited:
        raise SystemExit(f"expected {SENTINEL!r} in the edited palette")


GUARD_SOURCE = '"""\nThe dark half of the derivation: every registered value spelled as a NAME.\n\nWHAT THIS PASS DID. The ink pass of 2026-08-28 defined and mirrored the APP\nregister here but deliberately left the palettes spelling those values as\nliterals -- rewiring is a mechanical substitution and that pass was a value\nchange, and mixing the two makes the diff unreadable and the snapshot evidence\nworthless. This is the substitution, on its own, in DARK and IMAGE only.\n\nWHY DARK ONLY. rnv-brand@8ab1174 rules the order: the dark surface ladder is\ntwo-thirds specified and entirely inside the register, while the light ladder\nis not ruled at all -- nine light surfaces sit inside three grid steps and the\nregister has not yet decided which of them are real distinctions. Deriving\nagainst that gap would mean deriving twice.\n\nNOTHING MOVED. This pass changes how values are spelled, not what they are.\nThe delivery script proved it by resolving both palettes before and after and\ncomparing them entry by entry; these tests hold the result in place.\n\nTHE POINT OF IT. A literal cannot follow its base. APP["text"] moved on\n2026-08-28 and this app would have kept the old value silently, because the\nvalue was written down rather than referenced. Every registered value in the\ndark palettes is now a name, so the next register move carries.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\n\nimport pytest\n\nfrom utils import config as colors\nfrom utils.config import (DARK_THEME_COLORS as DARK,\n                          IMAGE_MODE_COLORS as IMAGE)\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nSRC = ROOT / \'utils/config.py\'\n\n#: The register, as this app mirrors it. Value-keyed, because the substitution\n#: was value-keyed: any dark entry holding one of these must now name it.\nREGISTERED = {\'TRUE_BLACK\': \'#000000\', \'BRAND_BLACK\': \'#1a1a1a\', \'APP_CARD\': \'#2a2a2a\', \'APP_BORDER\': \'#333333\'}\n\nDARK_DICTS = (\'DARK_THEME_COLORS\', \'IMAGE_MODE_COLORS\')\nLIGHT_DICTS = (\'LIGHT_THEME_COLORS\',)\n\n#: dict NAME -> the live dict. Looking a key up in the wrong palette is how a\n#: per-mode difference gets checked against the other mode\'s value and passes.\n#: DARK and IMAGE agree on most keys in most of these apps, so a lookup that\n#: falls back from one to the other is right almost everywhere and wrong\n#: exactly where it matters.\nPALETTES = {\'DARK_THEME_COLORS\': DARK, \'IMAGE_MODE_COLORS\': IMAGE}\n\n\ndef _dicts(names):\n    tree = ast.parse(SRC.read_text(encoding=\'utf-8-sig\'))\n    out = {}\n    for node in ast.walk(tree):\n        if isinstance(node, (ast.Assign, ast.AnnAssign)):\n            target = node.targets[0] if isinstance(node, ast.Assign) else node.target\n            name = getattr(target, \'id\', None)\n            if name in names and isinstance(node.value, ast.Dict):\n                out[name] = node.value\n    missing = set(names) - set(out)\n    assert not missing, f\'these palettes are no longer dict literals: {missing}\'\n    return out\n\n\n# ------------------------------------------------------------- guard the guard\n\ndef test_the_palettes_this_file_reads_still_exist():\n    """Every assertion below walks these. If one is renamed or stops being a\n    dict literal, this fails loudly instead of the rest passing over nothing."""\n    assert _dicts(DARK_DICTS)\n    assert _dicts(LIGHT_DICTS)\n\n\ndef test_the_register_map_is_not_empty():\n    """A sweep with nothing to look for passes forever."""\n    assert len(REGISTERED) >= 4\n    for name, value in REGISTERED.items():\n        assert getattr(colors, name) == value, (\n            f\'{name} is {getattr(colors, name)}, not {value} -- the map this \'\n            f\'file sweeps for has gone stale against the constants\')\n\n\n# ------------------------------------------------------------ the substitution\n\ndef test_no_registered_value_is_spelled_as_a_literal_in_dark():\n    """The completeness half. This is the assertion that makes the pass stick:\n    a literal cannot follow its base, so there must not be one left."""\n    by_value = {v: k for k, v in REGISTERED.items()}\n    literals = []\n    for dict_name, node in _dicts(DARK_DICTS).items():\n        for key, value in zip(node.keys, node.values):\n            if not isinstance(key, ast.Constant):\n                continue\n            if isinstance(value, ast.Constant) and isinstance(value.value, str):\n                if value.value.lower() in by_value:\n                    literals.append(\n                        f\'{dict_name}[{key.value!r}] = {value.value} \'\n                        f\'(should read {by_value[value.value.lower()]})\')\n    assert not literals, (\n        \'registered values still written as literals in the dark palettes:\\n  \'\n        + \'\\n  \'.join(literals))\n\n\ndef test_every_dark_entry_that_names_a_constant_resolves_to_the_register():\n    """The other half. A name is only worth having if it holds the right\n    value."""\n    wrong = []\n    for dict_name, node in _dicts(DARK_DICTS).items():\n        for key, value in zip(node.keys, node.values):\n            if isinstance(value, ast.Name) and value.id in REGISTERED:\n                actual = PALETTES[dict_name].get(key.value)\n                if actual != REGISTERED[value.id]:\n                    wrong.append(f\'{dict_name}[{key.value!r}] -> {value.id} \'\n                                 f\'resolves to {actual}\')\n    assert not wrong, \'names resolving wrongly:\\n  \' + \'\\n  \'.join(wrong)\n\n\ndef test_the_dark_palettes_actually_use_some_of_them():\n    """Guard the guard, again. If the palettes stopped referencing the register\n    entirely, the sweep above would find no literals and pass -- for the wrong\n    reason."""\n    used = set()\n    for node in _dicts(DARK_DICTS).values():\n        for value in node.values:\n            if isinstance(value, ast.Name) and value.id in REGISTERED:\n                used.add(value.id)\n    assert len(used) >= 3, (\n        f\'the dark palettes reference only {sorted(used)} of the register. \'\n        f\'The literal sweep passes trivially when nothing is referenced.\')\n\n\n# --------------------------------------------------------------- what did NOT\n\ndef test_the_light_palettes_were_left_alone():\n    """This pass is the DARK half, on the register\'s stated order. The light\n    ladder is unruled -- nine surfaces inside three grid steps, and which of\n    them are real distinctions is a judgement the register has not made. If a\n    later pass wires light, this test is the thing that has to be deleted on\n    purpose."""\n    named = []\n    for dict_name, node in _dicts(LIGHT_DICTS).items():\n        for key, value in zip(node.keys, node.values):\n            if isinstance(value, ast.Name) and value.id in REGISTERED:\n                named.append(f\'{dict_name}[{key.value!r}] -> {value.id}\')\n    assert not named, (\n        \'the light palettes now reference the register:\\n  \' + \'\\n  \'.join(named)\n        + \'\\n\\nThat is the light half, and it is not ruled yet.\')\n'


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
