#!/usr/bin/env python3
"""
Fix the garbage-strategy filter in RNVizion/rnv-color-picker.
=============================================================
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Run from the repository root:

    python apply_picker_isdigit_fix.py             # apply and verify
    python apply_picker_isdigit_fix.py --finish    # verify, then remove me

THE BUG

tests/test_color_math.py builds a "garbage" strategy -- strings that
int() cannot parse -- and filters with:

    st.text(min_size=1, max_size=5).filter(lambda s: not s.lstrip("-").isdigit())

The intent, stated in its own comment, is right: "Text that genuinely
can't be int()-parsed. A bare numeric string like '0' or '-5' is valid
int input -- exclude those." The implementation is not, because
str.isdigit() and int() disagree in BOTH directions:

    input      isdigit   kept as "garbage"   int() accepts   result
    '0 '       False     yes                 yes             false failure
    ' 5'       False     yes                 yes             false failure
    '+5'       False     yes                 yes             false failure
    '5_0'      False     yes                 yes             false failure
    '1\\xa0'    False     yes                 yes             false failure
    '\\xb2'     True      no                  NO              coverage lost

int() strips surrounding whitespace, accepts a leading sign, and honours
PEP 515 underscore separators. isdigit() accepts superscripts and other
Unicode digit forms that int() rejects.

So the strategy can hand a test that expects rejection a string the code
correctly accepts. That is what happened: hypothesis found '0 ',
is_valid_rgb('0 ', 0, 0) returned True as designed, and the suite failed.
It is intermittent because hypothesis explores a different input space
each run.

THE APP IS NOT WRONG. is_valid_rgb documents itself as "Check if RGB
values are valid (in 0-255 range)" and implements that with int() inside
a try/except -- deliberate coercion. rnv-color-mixer and
rnv-color-palette-manager carry the identical implementation and test it
with plain assertions, so they never hit this. Changing three apps'
behaviour to satisfy one wrong filter would be the tail wagging the dog.

THE FIX

Filter on the operation the code under test actually performs. A
predicate that asks int() directly cannot disagree with int():

    def _int_rejects(s):
        try:
            int(s)
        except (TypeError, ValueError):
            return True
        return False

Both filters -- TestSafeRgb and TestIsValidRgb -- switch to it, plus:

* a parametrised contract test pinning the five inputs that used to slip
  through, so the behaviour is asserted rather than assumed;
* a source guard that fails if .isdigit() returns to this file.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()
TARGET = REPO / "tests" / "test_color_math.py"

TOOL_MARKER = "RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP"
OLD_FILTER = '''        st.text(min_size=1, max_size=5).filter(
            lambda s: not s.lstrip("-").isdigit()
        ),'''
NEW_FILTER = '''        st.text(min_size=1, max_size=5).filter(_int_rejects),'''

# Inputs int() accepts and str.isdigit() does not. Every one of these was
# reachable as "garbage" under the old filter.
SLIPPED_THROUGH = ["0 ", " 5", "+5", "5_0", "1\xa0"]

FAIL, OK, WARN, OFF = "\033[31m", "\033[32m", "\033[33m", "\033[0m"


def say(msg: str, colour: str = "") -> None:
    print(f"{colour}{msg}{OFF}" if colour else msg)


def die(msg: str) -> None:
    say(f"ABORT: {msg}", FAIL)
    sys.exit(1)


HELPER = '''

def _int_rejects(s: str) -> bool:
    """True when int(s) raises -- exactly what the code under test relies on.

    Asking int() directly is the point. The predicate this replaced,
    ``not s.lstrip("-").isdigit()``, was an approximation of "int() cannot
    parse this", and it was wrong in both directions:

        int() strips surrounding whitespace     '0 ', ' 5', '1\\xa0'
        int() accepts a leading sign            '+5'
        int() honours PEP 515 underscores       '5_0'
        isdigit() accepts superscripts          '\\xb2', which int() rejects

    The first four were handed to tests asserting rejection, so the suite
    failed whenever hypothesis happened to generate one -- intermittently,
    because it explores a different input space each run. The last cost
    real coverage: genuine garbage excluded from the strategy.

    A predicate defined in terms of the operation cannot drift from it.
    """
    try:
        int(s)
    except (TypeError, ValueError):
        return True
    return False

'''

CONTRACT_TESTS = '''

# ═══════════════════════════════════════════════════════════════════════════
# THE CONTRACT THE OLD FILTER GOT WRONG
# ═══════════════════════════════════════════════════════════════════════════

#: Strings int() accepts and str.isdigit() does not. Under the previous
#: filter every one of these was reachable as "garbage" and fed to a test
#: asserting rejection.
INT_PARSEABLE_BUT_NOT_ISDIGIT = ["0 ", " 5", "+5", "5_0", "1\\xa0"]


@pytest.mark.parametrize("text", INT_PARSEABLE_BUT_NOT_ISDIGIT)
def test_int_parseable_strings_are_accepted(text):
    """These are valid input, not garbage, and the app is right to take them.

    is_valid_rgb coerces with int() inside a try/except -- that is its
    documented behaviour, and rnv-color-mixer and
    rnv-color-palette-manager share the implementation. Pinning it here
    means a future 'tidy-up' of the filter has to argue with a test rather
    than quietly reintroduce the bug.
    """
    assert ColorMath.is_valid_rgb(text, 0, 0) is True
    assert ColorMath.safe_rgb(text, 128, 128) == (int(text), 128, 128)


def test_isdigit_is_not_used_to_decide_what_int_can_parse():
    """A source guard, because the old predicate looked entirely reasonable.

    It read as 'not a digit string', which is close enough to 'int() can't
    parse it' to survive review, and the two differ on whitespace, signs,
    underscores and Unicode digit forms.
    """
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    lines = source.splitlines()
    offenders = [
        f"  line {node.lineno}: {lines[node.lineno - 1].strip()[:70]}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "isdigit"
    ]
    assert not offenders, (
        "isdigit() is back in this file. It is not a test for what int() "
        "accepts:\\n" + "\\n".join(offenders))


def test_the_garbage_strategy_still_produces_garbage():
    """Guard the filter. A predicate that rejected everything would leave
    the strategy empty and every garbage test would pass vacuously."""
    rejected = [s for s in ["abc", "", "5.", "_5", "\\xb2", "??"]
                if _int_rejects(s)]
    assert len(rejected) >= 5, (
        f"_int_rejects only classified {len(rejected)} of 6 known-unparseable "
        f"strings as garbage")
    assert not _int_rejects("0 "), (
        "_int_rejects calls '0 ' garbage, but int('0 ') == 0 -- the "
        "predicate has drifted from the operation again")
'''


def read_any(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        return raw.decode("utf-8-sig" if bom else "utf-8"), ("bom" if bom else "plain")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="surrogateescape"), "surrogate"


def write_any(path: Path, text: str, mode: str) -> None:
    if mode == "bom":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    elif mode == "surrogate":
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def check_dependencies() -> None:
    probe = ("import pytest, hypothesis\n"
             "import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen')\n")
    r = subprocess.run([sys.executable, "-c", probe], cwd=REPO,
                       capture_output=True, text=True)
    if r.returncode != 0:
        m = re.search(r"No module named '([^']+)'", r.stderr)
        die((f"the Python package {m.group(1)!r} is not installed.\n\n"
             f"       pip install -r requirements.txt -r requirements-test.txt"
             if m else r.stderr[-400:]) + "\n\n       Nothing has been changed.")
    say("preflight: dependencies present", OK)


def preflight() -> None:
    check_dependencies()
    if not TARGET.exists():
        die(f"{TARGET.relative_to(REPO)} not found -- run this from the "
            f"repository root.")
    src, _ = read_any(TARGET)
    if "_int_rejects" in src:
        die("this fix has already been applied. Nothing changed.")
    n = src.count(OLD_FILTER)
    if n != 2:
        die(f"expected the isdigit filter twice in "
            f"{TARGET.relative_to(REPO)} and found {n}. This repository is "
            f"not at the state the script was proven against. Nothing "
            f"changed.")
    say(f"preflight: base state confirmed -- {n} occurrences of the filter",
        OK)


def apply_fix() -> None:
    src, mode = read_any(TARGET)

    src = src.replace(OLD_FILTER, NEW_FILTER)
    if "not s.lstrip" in src:
        die("a filter survived the replacement. Nothing further changed.")

    # The helper goes after the imports, before the first class or test.
    tree = ast.parse(src)
    anchor = None
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) or (
                isinstance(node, ast.Assign) and node.lineno > 20):
            anchor = node.lineno
            break
    if anchor is None:
        die("could not find a place to insert the helper.")
    lines = src.splitlines(keepends=True)
    src = "".join(lines[:anchor - 1]) + HELPER.lstrip("\n") + "\n" \
        + "".join(lines[anchor - 1:])

    if "import pathlib" not in src:
        src = src.replace("import pytest", "import ast\nimport pathlib\n\nimport pytest", 1)
        if "import pathlib" not in src:
            die("could not add the pathlib import the source guard needs.")

    src = src.rstrip("\n") + "\n" + CONTRACT_TESTS
    ast.parse(src)          # never write a file that will not parse
    write_any(TARGET, src, mode)
    say("applied: both filters now ask int() directly; contract tests and "
        "a source guard added", OK)


def verify() -> bool:
    ok = True
    src, _ = read_any(TARGET)

    # Look for isdigit CALLS in the AST, not the substring. The helper's
    # own docstring explains the predicate it replaced, and a text search
    # cannot tell that sentence from live code -- the first draft of this
    # check flagged exactly that and reported FAIL on a correct fix.
    tree = ast.parse(src)
    calls = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "isdigit"]
    if calls:
        ok = False
        say("verify: isdigit is being CALLED to decide what int() can parse:",
            FAIL)
        lines = src.splitlines()
        for ln in calls:
            say(f"        line {ln}: {lines[ln - 1].strip()[:64]}", FAIL)

    # The behaviour the old filter contradicted, checked against the app.
    sys.path.insert(0, str(REPO))
    for m in [k for k in list(sys.modules) if k.split(".")[0] == "core"]:
        del sys.modules[m]
    from core.color_math import ColorMath  # noqa: E402
    for text in SLIPPED_THROUGH:
        got = ColorMath.is_valid_rgb(text, 0, 0)
        if got is not True:
            ok = False
            say(f"verify: is_valid_rgb({text!r}, 0, 0) returned {got}; the "
                f"app coerces with int() and int({text!r}) == {int(text)}",
                FAIL)
    say(f"verify: {len(SLIPPED_THROUGH)} int-parseable strings accepted as "
        f"the app documents")

    say("verify: PASS" if ok else "verify: FAIL", OK if ok else FAIL)
    return ok


def run(args: list[str], label: str) -> str:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    say(f"running {label} ...")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *args],
                       cwd=REPO, env=env, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    keep = [l for l in out if l.startswith(("FAILED", "ERROR"))
            or " passed" in l or " failed" in l]
    for line in (keep or out)[-10:]:
        say(f"    {line}")
    if r.returncode < 0:
        say(f"    KILLED by signal {-r.returncode} -- not a test result", WARN)
        return "killed"
    return "pass" if r.returncode == 0 else "fail"


def targeted_tests() -> str:
    """The file this pass changes, run against many seeds.

    One run proves nothing here: the bug was intermittent precisely
    because hypothesis explores differently each time. Fifteen seeds is
    still seconds, and it is the difference between "passed" and "does not
    fail".
    """
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    say("running tests/test_color_math.py across 15 hypothesis seeds ...")
    bad = []
    for seed in range(1, 16):
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/test_color_math.py",
             f"--hypothesis-seed={seed}"],
            cwd=REPO, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            bad.append((seed, (r.stdout + r.stderr).strip().splitlines()[-1]))
    if bad:
        say(f"    FAILED on {len(bad)} of 15 seeds:", FAIL)
        for seed, line in bad[:5]:
            say(f"      seed {seed}: {line}", FAIL)
        return "fail"
    say("    15/15 seeds clean", OK)
    return "pass"


def remove_helpers(extra: list[str]) -> None:
    doomed = [SELF]
    for name in extra:
        p = (REPO / name).resolve()
        if p.exists() and p not in doomed:
            doomed.append(p)
    for p in doomed:
        try:
            p.unlink()
            say(f"    removed {p.relative_to(REPO)}", OK)
        except OSError as exc:
            say(f"    could NOT remove {p.relative_to(REPO)}: {exc}", FAIL)
    say("\n    Working tree is ready. One commit takes everything:", OK)
    say("      git add -A")
    say("      git commit -m 'Filter the garbage strategy on int(), not "
        "isdigit()'")
    say("      git push")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fix the isdigit-based garbage filter in "
                    "tests/test_color_math.py.")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--finish", nargs="*", metavar="FILE",
                    help="verify, run the seeds, then delete this tool")
    ap.add_argument("--skip-tests", action="store_true",
                    help="skip the full suite; the seed sweep always runs")
    args = ap.parse_args()

    applied = "_int_rejects" in read_any(TARGET)[0]
    if args.verify_only:
        pass
    elif applied:
        say("already applied -- skipping to verification", WARN)
    else:
        preflight()
        apply_fix()

    ok = verify()
    if targeted_tests() != "pass":
        ok = False
    if not args.skip_tests:
        if run([], "the full test suite") == "fail":
            ok = False

    if args.finish is not None:
        if ok:
            say("\nremoving transfer helpers ...")
            remove_helpers(args.finish)
        else:
            say("\nNOT removing anything -- the checks did not pass.", FAIL)

    say("\nDONE -- all checks passed" if ok
        else "\nDONE -- with failures above", OK if ok else FAIL)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
