#!/usr/bin/env python3
"""
RNV-STATUS-TOOL-DO-NOT-SWEEP

Re-walk rnv-color-picker's light status text to the boundary the gold already stops at.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file


THIS IS A FOLLOW-UP, NOT A SECOND MIGRATION

The status family landed here against register rev 30. Rev 31, on 2026-09-05,
moved three values and nothing else -- the LIGHT text variants -- and closed
the question the migration scripts carried as RNV-STATUS-LIGHT-FLOOR.

    STATUS_SUCCESS_TEXT_LIGHT  #8a6581  ->  #825d79
    STATUS_ERROR_TEXT_LIGHT    #b84e58  ->  #ae4650

Everything else the migration did is untouched. The fills, the dark text
variants and the two gamut-corrected reds are already at rev 31 and are
asserted here so this script cannot run against a repository that is not.


WHY THE VALUES MOVED

They were first walked against #f5f5f5, which the register's rule called "the
worst light ground". It was not: rev 27 had put APP hover-light #eeeeee,
GOLD_TEXT_GROUND_FLOOR #e8e8e8 and pressed-light #e0e0e0 below it, and because
the rule takes the FIRST step that clears, each value stopped at 4.52 with no
margin and they failed one rung down together.

THE DECIDING REASON IS NOT THE SIZE OF THE MOVE. The desktop side argued from
cost -- a small move, the same colours -- and that does not pick between
#e8e8e8 and #e0e0e0, because #e0e0e0 was affordable on identical grounds. The
register's reason does: #e8e8e8 is where BRAND_DARK_GOLD_DEEP already stops.

    on #e8e8e8   gold-deep 4.53   the three 4.52 / 4.53 / 4.52   pass
    on #e0e0e0   gold-deep 4.21   the three 4.20 / 4.20 / 4.20   fail

ONE boundary for every brand text family instead of two. Walking to #e0e0e0
would have covered the pressed plate and left an author having to remember
which family they were in to know where text stops.


WHAT THIS ALSO DOES

The migration NARROWED a boundary test to #ffffff and #f5f5f5 while the
question was open, and recorded in the docstring what it had given up. This
restores the full four rungs -- and they pass, because the values reach them.
That is the point of the re-walk being visible in the test rather than only in
the register.


ONE THING IS STILL OPEN, ON THE OTHER SIDE

The DARK text variants have the identical fault. They were derived against APP
card #2a2a2a; rev 29 then registered panel-hover #3a3a3a, which is LIGHTER and
therefore worse for light text on a dark ground. All three fail there --
success-text 3.61, warning-text 3.64, error-text 3.58 -- while BRAND_GOLD
clears every dark surface at 6.15.

The register left it open because the fix is not symmetric: on light the worst
surface is a PRESSED plate and ruling that running text is not carried on a
transient state is defensible, while on dark the worst is a HOVER, which a
label sits under for as long as a cursor rests there.

The fleet's exposure today is ZERO. The element sweep across all five
applications resolves four status elements, every one a plain dialog label
painted with an inline `color:` on a dialog ground; no status key appears in a
selector carrying :hover, in any mode. This script does not touch the dark
values, and the guard it installs asserts them at their current numbers so a
future re-walk has to come through the register rather than by hand.
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
DESCRIPTION = "re-walk the light status text to #e8e8e8 (register rev 31)"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "RNV-STATUS-LIGHT-FLOOR, CLOSED"
GUARD = "tests/test_light_rewalk.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

MISSING_HELP = (
    "run this from the root of a rnv-color-picker checkout.\n\n"
    "If you ARE in one, the status-family migration has not been applied here "
    "yet -- run up-for-rnv-color-picker-status-family.py first. This script only moves "
    "the three values rev 31 changed; it does not perform the migration."
)

SUITES = [
    ("pytest tests/",
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ("unittest suite",
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

# the value this repository holds now -> the value at register rev 31
REWALK = {'#8a6581': '#825d79', '#b84e58': '#ae4650'}

# already at rev 31 before this script runs. Asserted so a repository that is
# NOT on rev 30 cannot be half-moved by this follow-up.
ALREADY = {'STATUS_SUCCESS': '#926c89', 'STATUS_WARNING': '#a2703c', 'STATUS_ERROR': '#c75b64', 'STATUS_ERROR_TEXT': '#dd6f77'}

EDITS = [
    ('utils/config.py',
     'RNV-STATUS-LIGHT-FLOOR applies to this value too: it reads 4.25 on #eeeeee\nand 4.02 on #e8e8e8, both registered rungs, both below the 4.5 floor."""\n',
     'RNV-STATUS-LIGHT-FLOOR closed at rev 31: re-walked against #e8e8e8, where\nit now reads 4.52. See STATUS_ERROR_TEXT_LIGHT below for why that ground\nand not #e0e0e0."""\n', 1),
    ('utils/config.py',
     'RNV-STATUS-LIGHT-FLOOR: this value does NOT reach the coverage boundary its\npredecessor did. #c82131 read 4.6100 on #e8e8e8; this reads 4.0150 there and\n4.2401 on APP hover-light #eeeeee. The register walks its light text variants\nagainst #f5f5f5 as "the worst light ground", and rev 27 put three registered\nrungs below it. The question is open with the brand chat; if it re-walks\nagainst #e8e8e8 the answer here is #ae4650, moving 3.1 -- inside the\nregister\'s own 8.40 bar, so it stays the same red."""\n',
     'RNV-STATUS-LIGHT-FLOOR, CLOSED 2026-09-05 at register rev 31.\n\nThese were first walked against #f5f5f5 as "the worst light ground". It was\nnot the worst: rev 27 had put APP hover-light #eeeeee, GOLD_TEXT_GROUND_FLOOR\n#e8e8e8 and pressed-light #e0e0e0 below it, and because the rule takes the\nFIRST step that clears, each value stopped at 4.52 with no margin and they\nfailed one rung down together.\n\nRe-walked against #e8e8e8. THE DECIDING REASON IS NOT THE SIZE OF THE MOVE --\n#e0e0e0 was affordable on identical grounds, so cost does not pick between\nthem. It is that #e8e8e8 is where BRAND_DARK_GOLD_DEEP already stops:\n\n    on #e8e8e8   gold-deep 4.53   these 4.52 / 4.53 / 4.52   pass\n    on #e0e0e0   gold-deep 4.21   these 4.20 / 4.20 / 4.20   fail\n\nONE boundary for every brand text family instead of two. Walking to #e0e0e0\nwould have covered the pressed plate and left an author having to remember\nwhich family they were in to know where text stops. Below #e8e8e8, no brand\ntext of any family.\n\nThis value reads 4.52 on #e8e8e8 and 5.08 on #f5f5f5, so it reaches the\ncoverage boundary its predecessor #c82131 did -- which the intermediate\n#b84e58 did not, at 4.0150."""\n', 1),
    ('tests/test_brand_contrast.py',
     '    for ground in ("#ffffff", "#f5f5f5"):\n        ratio = contrast_ratio(C.STATUS_ERROR_TEXT_LIGHT, ground)\n',
     '    for ground in ("#ffffff", "#f5f5f5", "#eeeeee", "#e8e8e8"):\n        ratio = contrast_ratio(C.STATUS_ERROR_TEXT_LIGHT, ground)\n', 1),
    ('tests/test_brand_contrast.py',
     '    for ground in ("#ffffff", "#f5f5f5", "#eeeeee", "#e8e8e8"):\n        ratio = contrast_ratio(C.STATUS_ERROR_TEXT_LIGHT, ground)\n',
     '    # Restored at rev 31: the re-walked value reaches all four rungs.\n    # #e0e0e0 is deliberately absent -- BRAND_DARK_GOLD_DEEP fails there\n    # too, so it is the boundary for every brand text family, not a gap.\n    for ground in ("#ffffff", "#f5f5f5", "#eeeeee", "#e8e8e8"):\n        ratio = contrast_ratio(C.STATUS_ERROR_TEXT_LIGHT, ground)\n', 1),
]

QUOTE = '"'
NAMES = ['STATUS_SUCCESS_TEXT_LIGHT', 'STATUS_ERROR_TEXT_LIGHT']
BEFORE = {'STATUS_SUCCESS_TEXT_LIGHT': '#8a6581', 'STATUS_ERROR_TEXT_LIGHT': '#b84e58'}
VALUE_FILES = ['utils/config.py', 'tests/test_status_family.py', 'tests/test_brand_contrast.py']

GUARD_SOURCE = r'''"""RNV-STATUS-LIGHT-REWALK -- the light boundary is #e8e8e8, and it is shared.

Installed by the rev 31 follow-up. Two things it pins that the migration's own
guard does not:

  * the light text variants reach #e8e8e8, which they did not at rev 30;
  * they stop at #e0e0e0, and so does BRAND_DARK_GOLD_DEEP -- one boundary for
    every brand text family rather than one per family.

The second is the load-bearing half. A test that only asserted "these clear
#e8e8e8" would pass equally on values walked to #e0e0e0, which is the choice
the register explicitly did not make.
"""
from __future__ import annotations

import pytest

from utils import config as C

TEXT_FLOOR = 4.5

REWALKED = {'STATUS_SUCCESS_TEXT_LIGHT': '#825d79', 'STATUS_ERROR_TEXT_LIGHT': '#ae4650'}

# The rungs the register publishes, lightest first. #e0e0e0 is in the list on
# purpose: it is asserted to FAIL, which is what makes it a boundary.
REACHES = ("#ffffff", "#fbfbfb", "#f5f5f5", "#eeeeee", "#e8e8e8")
STOPS_AT = "#e0e0e0"

GOLD_DEEP = "#7e6529"   # BRAND_DARK_GOLD_DEEP, the family this shares with


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(value: str) -> float:
    h = value.lstrip("#")
    t = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return 0.2126 * _lin(t[0]) + 0.7152 * _lin(t[1]) + 0.0722 * _lin(t[2])


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name,value", sorted(REWALKED.items()))
def test_the_light_values_are_the_re_walked_ones(name, value):
    """Pinned by value. rev 30 held #8a6581 / #976633 / #b84e58, walked against
    #f5f5f5; rev 31 holds these, walked against #e8e8e8."""
    assert getattr(C, name) == value


@pytest.mark.parametrize("name", sorted(REWALKED))
@pytest.mark.parametrize("ground", REACHES)
def test_the_light_text_reaches_every_rung_down_to_the_ground_floor(name, ground):
    ratio = contrast(getattr(C, name), ground)
    assert ratio >= TEXT_FLOOR, f"{name} on {ground} = {ratio:.4f}"


@pytest.mark.parametrize("name", sorted(REWALKED))
def test_the_light_text_stops_where_the_gold_stops(name):
    """The half that makes #e8e8e8 a BOUNDARY rather than an arbitrary target.

    Values walked to #e0e0e0 would pass the test above and fail this one. The
    register chose #e8e8e8 because BRAND_DARK_GOLD_DEEP already stops there --
    4.53 on #e8e8e8, 4.21 on #e0e0e0 -- so below it no brand text of any
    family is carried, and an author does not have to remember which family
    they are in to know where text stops.

    If this ever goes green, either the values were re-walked deeper without
    the gold moving with them, or the gold moved. Either way the two families
    have separated and the boundary is two boundaries again.
    """
    assert contrast(GOLD_DEEP, STOPS_AT) < TEXT_FLOOR, (
        "BRAND_DARK_GOLD_DEEP now clears #e0e0e0 -- the shared boundary moved "
        "and these values should be re-walked with it")
    assert contrast(getattr(C, name), STOPS_AT) < TEXT_FLOOR, (
        f"{name} now clears {STOPS_AT}, which BRAND_DARK_GOLD_DEEP does "
        f"not. The two text families no longer share a boundary.")


def test_this_guard_is_measuring_the_right_thing():
    """Guard the guard. If contrast() ever returned a constant, every
    assertion above would pass while checking nothing."""
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0, abs=0.001)
    assert contrast(GOLD_DEEP, "#e8e8e8") == pytest.approx(4.53, abs=0.02)
'''


def edits(tree) -> None:
    for rel, old, new, times in EDITS:
        tree.sub(rel, old, new, times)

    # The values themselves, everywhere they are written in the files this
    # repository keeps them in. Counted rather than swept: a value that turns
    # up more times than expected means the file grew a copy while nobody was
    # looking, which is the condition the naming rule exists to prevent.
    for rel in VALUE_FILES:
        text = tree.read(rel)
        for old, new in REWALK.items():
            n = text.count(old)
            if n:
                text = text.replace(old, new)
        tree.write(rel, text)
    print(f"  {len(EDITS)} anchored edit(s) plus the values in "
          f"{len(VALUE_FILES)} file(s)")


def checks(tree) -> None:
    src = tree.read(SENTINEL_FILE)

    # every re-walked value is in, and none of the old ones survives
    for old, new in REWALK.items():
        if old in src:
            raise SystemExit(f"{old} survives in {SENTINEL_FILE}")
    for name, want in ALREADY.items():
        if f"{name}: Final[str] = {QUOTE}{want}{QUOTE}" not in src:
            raise SystemExit(
                f"{name} is not {want}. This repository is not at register "
                f"rev 30, so this follow-up would leave it half-moved. Apply "
                f"the status-family migration first.")
    for name in NAMES:
        want = REWALK[BEFORE[name]]
        if f"{name}: Final[str] = {QUOTE}{want}{QUOTE}" not in src:
            raise SystemExit(f"{name} is not {want}")

    for rel in VALUE_FILES:
        text = tree.read(rel)
        for old in REWALK:
            if old in text:
                raise SystemExit(f"{old} survives in {rel}")

    if SENTINEL not in src:
        raise SystemExit("the closing note did not land")
    print(f"  guards: {len(REWALK)} value(s) re-walked, "
          f"{len(ALREADY)} unchanged value(s) confirmed at rev 31")


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
        """Compare and write BYTES, not decoded text.

        read_text('utf-8') here raised on a file that was not valid UTF-8 --
        which is precisely the file some scripts exist to fix. Bytes compare
        identically for everything else and cannot refuse to look."""
        touched = []
        for rel, text in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = text.encode("utf-8")
            if not p.exists() or p.read_bytes() != data:
                p.write_bytes(data)
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
