#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Annotate rnv-color-picker's unconsumed `text_secondary`.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

NO VALUE CHANGES. NOT ONE PIXEL.

`text_secondary` is already #888888 dark / #666666 light, which is what the
apps that actually paint a muted text use. What was missing is that nothing in
this repository paints it: it is a redundant twin of `text_muted`, which
carries the identical value in both palettes and does the job in six places.

Swept for it three ways -- by line, by identifier, and by checking every file
that mentions it -- and the only references outside utils/config.py are a key
name in a test's REQUIRED list. Nothing reads it. Nothing renders it.

WHAT LANDS

  utils/config.py                  a NOT CONSUMED note beside each of the two
                                   values, saying the colour is already set and
                                   wiring it up is one line
  tests/test_unconsumed_keys.py    new: holds the note and the fact together,
                                   in BOTH directions -- if someone paints the
                                   key, the note is a lie and the run says so

WHY NOT JUST DELETE IT

Because the next person to need a muted-text key in this app should find one
already at the right value rather than pick a new one. A dead key with a note
is cheap; a fifth spelling of a colour is not.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-color-picker"
DESCRIPTION = "annotate the unconsumed text_secondary key"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "NOT CONSUMED"
GUARD = "tests/test_unconsumed_keys.py"
SHADOWS = {"config.py", "colors.py", "conftest.py"}

# Run them the way .github/workflows/tests.yml runs them.
SUITES = [
    ("pytest tests/", [sys.executable, "-m", "pytest", "tests/", "-q",
                       "-p", "no:cacheprovider",
                       "--timeout=60", "--timeout-method=thread"]),
    ("unittest suite", [sys.executable, "-m", "unittest",
                        "test_rnv_color_picker"]),
]

NOTE_DARK = (
    "    # NOT CONSUMED. Nothing reads this key -- 'text_muted' below carries the\n"
    "    # same value and does the job in six places. Kept, and kept correct, so\n"
    "    # wiring it up is a one-line change rather than a colour decision.\n")
NOTE_LIGHT = "    # NOT CONSUMED -- see the note in the dark palette.\n"

DARK_LINE = "    'text_secondary':     '#888888',"
LIGHT_LINE = "    'text_secondary':     '#666666',"


def edits(tree) -> None:
    tree.sub(SENTINEL_FILE, DARK_LINE, NOTE_DARK + DARK_LINE)
    tree.sub(SENTINEL_FILE, LIGHT_LINE, NOTE_LIGHT + LIGHT_LINE)


def checks(tree) -> None:
    src = tree.read(SENTINEL_FILE)
    if src.count("# NOT CONSUMED") != 2:
        raise SystemExit("expected exactly two NOT CONSUMED notes")
    # the values must not have moved -- this pass is annotation only
    for line in (DARK_LINE, LIGHT_LINE):
        if src.count(line) != 1:
            raise SystemExit(f"the value moved: {line.strip()!r}")


GUARD_SOURCE = '"""\n`text_secondary` is defined and painted nowhere, and the palette says so.\n\nIt is a redundant twin of `text_muted`, which carries the same value in both\npalettes and does the job in six places. Rather than delete it, the values are\nkept correct and a NOT CONSUMED note sits beside each, so wiring it up is one\nline and not a colour decision.\n\nThat arrangement only helps while the note is true. These tests hold both\nhalves together: the key stays unpainted, and the note stays present. If\nsomeone wires it up, the note becomes a lie and the run says so.\n"""\nfrom __future__ import annotations\n\nimport pathlib\nimport re\n\nROOT = pathlib.Path(__file__).resolve().parent.parent\nCONFIG_PY = ROOT / "utils" / "config.py"\nKEY = "text_secondary"\n\n\ndef _source(path: pathlib.Path) -> str:\n    # Five files in this repo begin with a UTF-8 BOM. Reading them as plain\n    # utf-8 makes ast.parse refuse them and makes a sweep silently skip them,\n    # so the encoding here is deliberate.\n    return path.read_text(encoding="utf-8-sig", errors="replace")\n\n\ndef _references(key: str) -> list[str]:\n    sites = []\n    for path in ROOT.rglob("*.py"):\n        parts = path.parts\n        if any(p in parts for p in (".git", "__pycache__", "tests")):\n            continue\n        if path.name.startswith("test_") or path == CONFIG_PY:\n            continue\n        # A delivery script sitting at the root mentions the key it moves.\n        # Sweeping it makes the guard fail on the very run that installs it --\n        # the same trap the repos\' placement guards already exempt `up*.py` for.\n        if path.parent == ROOT and path.name.startswith("up"):\n            continue\n        if key in _source(path):\n            sites.append(path.relative_to(ROOT).as_posix())\n    return sorted(sites)\n\n\ndef test_the_sweep_is_actually_reading_something():\n    """Guard the guard. A walk that finds nothing passes forever."""\n    walked = [p for p in ROOT.rglob("*.py")\n              if not any(x in p.parts for x in (".git", "__pycache__"))]\n    assert len(walked) > 20, f"the sweep only found {len(walked)} files"\n    # and it must be able to see a key that IS painted\n    assert _references("text_muted"), (\n        "the sweep cannot find text_muted, which is painted in six places -- "\n        "it would not find text_secondary either")\n\n\ndef test_the_key_is_still_unpainted():\n    sites = _references(KEY)\n    assert sites == [], (\n        f"{KEY} is now referenced in {sites}. If it is being painted, delete "\n        f"the NOT CONSUMED notes in utils/config.py -- they are no longer true.")\n\n\ndef test_the_note_is_still_there():\n    source = _source(CONFIG_PY)\n    notes = len(re.findall(r"#\\s*NOT CONSUMED", source))\n    assert notes == 2, (\n        f"expected a NOT CONSUMED note beside each of the two {KEY} values, "\n        f"found {notes}")\n\n\ndef test_the_twin_still_carries_the_same_values():\n    """The note says text_muted does this job. If they drift apart, wiring\n    text_secondary up would no longer be the one-line change it promises."""\n    from utils.config import DARK_THEME_COLORS, LIGHT_THEME_COLORS\n    for name, theme in (("DARK", DARK_THEME_COLORS),\n                        ("LIGHT", LIGHT_THEME_COLORS)):\n        assert theme[KEY] == theme["text_muted"], (\n            f"{name}: {KEY} is {theme[KEY]} but text_muted is "\n            f"{theme[\'text_muted\']} -- the note beside {KEY} is out of date")\n'


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
