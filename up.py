#!/usr/bin/env python3
"""RNV-DEADLINE-AND-PIN — a flake, a vacuous property test, and a dead skip.

    python up.py             # apply, then run both suites
    python up.py --check     # rehearse every edit in memory, write nothing

For rnv-color-picker, derived against a fresh clone at the live head.

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source. That marker is what tells this fleet's scanners to skip it.

TWO FILES, THREE FINDINGS.

1. THE FLAKE WAS A DEADLINE, NOT AN ASSERTION.
   `test_history_never_exceeds_max_size` failed about one run in eight with
   hypothesis `DeadlineExceeded`. `add_color()` calls `save_history()` on
   EVERY call, and that rewrites the whole JSON file, so one example of 400
   colours is 400 whole-file writes of a list growing to 333 entries:

       50 colours    41 ms
      100 colours    95 ms
      200 colours   248 ms   <- already over
      400 colours   743 ms

   The default deadline is 200 ms per example and `@settings` never overrode
   it. Hypothesis re-runs an over-deadline example before reporting, so
   whether it reported depended on machine load -- it passed alone, passed
   under eight fixed seeds, and failed inside a combined
   `pytest tests/ test_rnv_color_picker.py`. When it did fire, shrinking
   re-ran the writes and took six minutes before giving up.

   FIX: stub the save in that test. The property is the TRIM, which is in
   memory; persistence is TestSaveHistory's job. 400 colours goes from 721 ms
   to 1.0 ms. Not `deadline=None`, which would have silenced the signal and
   kept the cost.

2. AND THE TEST HAD NEVER REACHED ITS OWN BOUND.
   Found while tampering to check the fix: with the trim DELETED from
   add_color, this test stayed GREEN. `min_size=1` with `max_size=400` is a
   ceiling hypothesis does not approach -- twenty measured draws came out

       1 1 1 1 2 2 2 2 3 3 3 4 4 5 5 7 8 8 10 14

   largest fourteen, none above 333. A trim cannot happen below 334 colours,
   so no example could exercise the invariant. The class docstring says a
   property test catches this bound "that example tests can't"; the example
   test beside it was the one catching it.

   FIX: `min_size=334`, so every draw crosses the bound -- 20/20, measured.
   With the save stubbed this costs about 1.2 s, and the test now FAILS when
   the trim is deleted, which it did not before.

3. THE REGISTER-PIN TEST HAD SKIPPED SINCE THE DAY IT WAS WRITTEN.
   "engine.brand declares no __version__", in all five applications, inside a
   file whose own docstring says "a skipped test and a passing test look
   identical in a summary line. That is the whole failure mode this guards."

   It was looking in the wrong place. pip records the exact commit: PEP 610
   writes `direct_url.json` into the installed distribution's metadata with
   the `commit_id` it resolved. That is the other half of the comparison and
   it was there all along. Adding `__version__` to engine/brand.py would have
   been wrong twice over -- a second place the revision can disagree with
   pyproject.toml, and it still would not name a commit.

   The skips that remain are distinguishable: each says what it could not
   determine rather than that something is missing.

WHAT IS DELIBERATELY NOT HERE. `add_color`'s one-write-per-colour reaches
`add_colors_batch`, so a palette import does a whole-file rewrite per colour
-- about 0.5 s of disk churn at the 333 bound, 2.35 s for a thousand. Changing
it means changing WHEN history becomes durable, on a path that today cannot
lose data. That is a ruling, not a fix.
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

REPO = "rnv-color-picker"
SENTINEL_FILE = "tests/conftest.py"
SENTINEL = "RNV-DEADLINE-AND-PIN"
GUARD = "tests/test_color_history.py"
DESCRIPTION = "fix the deadline flake, the vacuous bound, and the dead skip"

SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py",
           "accessibility.py", "color_history.py"}


def post_write() -> None:
    """Install the dev requirements so the pin test RUNS rather than skips.

    The whole point of finding 3 is that a skip and a pass look alike. If this
    round applied and then the test skipped because the register is not
    installed, nobody would learn whether the fix works.

    NON-FATAL on purpose: a machine with no network should still get its
    suites run. The test then skips with an accurate reason, which is the
    designed behaviour, and this prints why.
    """
    for extra in ([], ["--break-system-packages"]):
        code, _out = run("installing the dev requirements",
                         [sys.executable, "-m", "pip", "install", "-q",
                          "--disable-pip-version-check", *extra,
                          "-r", "tests/requirements-dev.txt"])
        if code == 0:
            print("  dev requirements installed; the pin test will compare "
                  "rather than skip")
            return
    print("  COULD NOT INSTALL the dev requirements. Not fatal -- the suites "
          "still run below, and test_the_installed_register_is_the_pinned_one "
          "will SKIP with the reason it could not determine the commit. That "
          "skip is correct; it is not this round failing.")


def _timeout_flag() -> list:
    return ["--timeout=120"] if find_spec("pytest_timeout") else []


SUITES = [("\"pytest tests/\"",
           [sys.executable, "-m", "pytest", "tests/", "-q",
            "-p", "no:cacheprovider"]),
          ("\"the LOCKED file\"",
           [sys.executable, "-m", "pytest", "test_rnv_color_picker.py", "-q",
            "-p", "no:cacheprovider"] + _timeout_flag())]

EDITS = [('tests/conftest.py', '# RNV-RATING-SCALE, 2026-09-12 -- the contrast-rating label takes the\n# STATUS text family plus BRAND_BLUE, per mode, instead of four\n', "# RNV-DEADLINE-AND-PIN, 2026-09-12 -- the MAX_HISTORY_SIZE property test\n# stops doing 400 whole-file writes per example (it was blowing\n# hypothesis's 200 ms deadline about one run in eight) and starts drawing\n# lists big enough to reach the bound at all: min_size was 1, and twenty\n# draws never exceeded fourteen. And the register-pin test stops skipping\n# -- pip's direct_url.json names the installed commit, which is the\n# comparison it wanted and could not make.\n# RNV-RATING-SCALE, 2026-09-12 -- the contrast-rating label takes the\n# STATUS text family plus BRAND_BLUE, per mode, instead of four\n", 1), ('tests/test_color_history.py', '    @given(colors=st.lists(rgb, min_size=1, max_size=400, unique=True))\n    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])\n    def test_history_never_exceeds_max_size(self, manager, colors):\n        # Add an arbitrary number of distinct colors\n        manager.history = []\n        for c in colors:\n            manager.add_color(c)\n        # Even after adding 400 distinct colors, history <= MAX_HISTORY_SIZE\n        assert len(manager.history) <= ColorHistoryManager.MAX_HISTORY_SIZE\n\n    def test_exactly_max_size_after_overfilling(self, manager):\n        # Add MAX_HISTORY_SIZE + 50 distinct colors — history should be\n        # trimmed exactly to MAX_HISTORY_SIZE\n        N = ColorHistoryManager.MAX_HISTORY_SIZE + 50\n        for i in range(N):\n            # Generate distinct colors via the int-to-RGB encoding\n            r = (i // (256 * 256)) % 256\n            g = (i // 256) % 256\n            b = i % 256\n            manager.add_color((r, g, b))\n        assert len(manager.history) == ColorHistoryManager.MAX_HISTORY_SIZE', '    @given(colors=st.lists(rgb, min_size=334, max_size=400, unique=True))\n    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])\n    def test_history_never_exceeds_max_size(self, manager, colors):\n        # RNV-DEADLINE 2026-09-12, AND min_size IS THE HALF THAT MATTERS.\n        #\n        # THIS TEST NEVER ONCE REACHED THE BOUND IT WAS WRITTEN FOR. With\n        # min_size=1, max_size=400 is a ceiling Hypothesis does not approach:\n        # it biases toward small examples, and twenty draws measured as\n        #\n        #     1 1 1 1 2 2 2 2 3 3 3 4 4 5 5 7 8 8 10 14\n        #\n        # -- largest fourteen, ZERO above 333. A trim cannot happen below 334\n        # colours, so no example could exercise the invariant. Proved by\n        # deleting the trim from add_color entirely: this test stayed GREEN\n        # while test_exactly_max_size_after_overfilling caught it. The class\n        # docstring says a property test catches this bound "that example\n        # tests can\'t"; it was the example test doing the work.\n        #\n        # min_size=334 makes every draw cross the bound -- 20/20, measured --\n        # for about 1.1 s of generation, which is what uniqueness filtering\n        # over 334-400 triples costs. Small lists are TestAddColor\'s job.\n        #\n        # AND IT FAILED INTERMITTENTLY -- roughly\n        # one run in eight -- and not on its assertion. It raised\n        # hypothesis DeadlineExceeded, because add_color() calls\n        # save_history() on EVERY call and save_history() rewrites the whole\n        # JSON file. 400 colours is 400 whole-file writes of a list growing\n        # to 333 entries:\n        #\n        #     50 colours    41 ms\n        #    100 colours    95 ms\n        #    200 colours   248 ms   <- already over the deadline\n        #    400 colours   743 ms\n        #\n        # Hypothesis\'s default deadline is 200 ms PER EXAMPLE and @settings\n        # above does not override it, so any draw above about 170 colours is\n        # over. It re-runs an over-deadline example before reporting, so\n        # whether it reports depends on machine load -- which is why it passed\n        # alone and under eight fixed seeds, and failed inside a combined\n        # `pytest tests/ test_rnv_color_picker.py` run. When it did fire,\n        # shrinking re-ran the writes and took six minutes before giving up.\n        #\n        # THE PROPERTY IS THE TRIM, AND THE TRIM IS IN MEMORY. Persistence is\n        # TestSaveHistory\'s job; this test needs add_color\'s list arithmetic\n        # and nothing else. Stubbing the save takes the same 400 colours from\n        # 721 ms to 1.0 ms and leaves the invariant exactly as strong.\n        #\n        # NOT deadline=None, which is the other obvious fix. That would stop\n        # the failure and keep the cost -- 20 examples of real disk churn, and\n        # a shrink that is still pathological the day this assertion breaks\n        # for a real reason. The deadline is a useful signal; what was wrong\n        # was the work, not the limit.\n        manager.save_history = lambda: True\n        # Add an arbitrary number of distinct colors\n        manager.history = []\n        for c in colors:\n            manager.add_color(c)\n        # Even after adding 400 distinct colors, history <= MAX_HISTORY_SIZE\n        assert len(manager.history) <= ColorHistoryManager.MAX_HISTORY_SIZE\n\n    def test_the_trim_still_happens_when_the_save_is_real(self, manager):\n        """Guard the stub above.\n\n        Replacing save_history with a no-op is only safe if the trim does not\n        depend on it. Asserted once, at full size, against the real save --\n        so if a future add_color ever moves the trim behind the write, the\n        stub stops hiding it. One example rather than twenty: this costs\n        about 700 ms and buys the licence for the fast path above.\n        """\n        for i in range(ColorHistoryManager.MAX_HISTORY_SIZE + 50):\n            manager.add_color(((i // 65536) % 256, (i // 256) % 256, i % 256))\n        assert len(manager.history) == ColorHistoryManager.MAX_HISTORY_SIZE\n        assert manager.history_file.exists(), (\n            "the real save never ran, so this guard is not guarding anything")\n\n    def test_exactly_max_size_after_overfilling(self, manager):\n        # RNV-DEADLINE 2026-09-12: same stub, same reason. 383 adds is 383\n        # whole-file writes and about 690 ms for an assertion about list\n        # length. No Hypothesis deadline applies here, so this was never\n        # flaky -- it was just slow for nothing.\n        manager.save_history = lambda: True\n        # Add MAX_HISTORY_SIZE + 50 distinct colors — history should be\n        # trimmed exactly to MAX_HISTORY_SIZE\n        N = ColorHistoryManager.MAX_HISTORY_SIZE + 50\n        for i in range(N):\n            # Generate distinct colors via the int-to-RGB encoding\n            r = (i // (256 * 256)) % 256\n            g = (i // 256) % 256\n            b = i % 256\n            manager.add_color((r, g, b))\n        assert len(manager.history) == ColorHistoryManager.MAX_HISTORY_SIZE', 1), ('tests/test_register_pin.py', 'def test_the_installed_register_is_the_pinned_one():\n    """The pin says which revision; this asks whether that is what is\n    actually installed. They come apart the moment someone bumps the pin and\n    does not reinstall -- and then the suite is checking the app against a\n    register nobody declared."""\n    import engine.brand as brand\n    version = getattr(brand, \'__version__\', None)\n    if version is None:\n        pytest.skip(\'engine.brand declares no __version__; the pin is the \'\n                    \'only statement of which revision this is\')\n    assert version, \'engine.brand.__version__ is empty\'', 'def test_the_installed_register_is_the_pinned_one():\n    """The pin says which revision; this asks whether that is what is\n    actually installed. They come apart the moment someone bumps the pin and\n    does not reinstall -- and then the suite is checking the app against a\n    register nobody declared.\n\n    RNV-DEADLINE-AND-PIN, 2026-09-12: THIS TEST SKIPPED FROM THE DAY IT WAS\n    WRITTEN, in all five applications, for five days, with the reason\n    "engine.brand declares no __version__". That is the failure this file\'s\n    own docstring names four paragraphs up -- "a skipped test and a passing\n    test look identical in a summary line" -- committed by the file that\n    names it.\n\n    It was also looking in the wrong place. `__version__` would only have\n    answered "which release", and the question here is "which COMMIT", which\n    pip already records: PEP 610 writes direct_url.json into the installed\n    distribution\'s metadata with the exact `commit_id` it resolved. That is\n    the other half of the comparison, and it was there the whole time.\n\n    Adding __version__ to engine/brand.py would have been the wrong fix\n    twice over: it puts the revision in a second place that can disagree with\n    pyproject.toml, and it still would not name the commit.\n\n    THE SKIPS THAT REMAIN ARE DISTINGUISHABLE, which is the point. Each says\n    what it could not determine rather than that something is absent.\n    """\n    import json\n    import importlib.metadata as metadata\n\n    import engine.brand  # noqa: F401 -- the register must at least import\n\n    try:\n        raw = metadata.distribution(\'rnv-brand\').read_text(\'direct_url.json\')\n    except metadata.PackageNotFoundError:\n        pytest.skip(\'engine.brand imports but no rnv-brand DISTRIBUTION is \'\n                    \'installed -- it is being resolved from sys.path, so pip \'\n                    \'has no metadata to compare the pin against\')\n    if not raw:\n        pytest.skip(\'rnv-brand is installed without direct_url.json, so it \'\n                    \'did not come from a VCS URL and records no commit\')\n\n    installed = (json.loads(raw).get(\'vcs_info\') or {}).get(\'commit_id\')\n    if not installed:\n        pytest.skip(\'rnv-brand was installed from a path or an index rather \'\n                    \'than a git ref, so its metadata names no commit\')\n\n    match = PIN_RE.search(DEV_REQS.read_text(encoding=\'utf-8\'))\n    assert match, \'no rnv-brand pin found\'\n    pinned = match.group(\'ref\')\n    assert installed == pinned, (\n        f\'tests/requirements-dev.txt pins rnv-brand@{pinned[:12]} but the \'\n        f\'INSTALLED register is {installed[:12]}. Every mirror test in this \'\n        f\'repository is comparing this app against a revision nobody \'\n        f\'declared. Run:\\n\\n\'\n        f\'    pip install -r tests/requirements-dev.txt\\n\')', 1)]


def edits(tree) -> None:
    for rel, old, new, times in EDITS:
        tree.sub(rel, old, new, times)


def checks(tree) -> None:
    """Run against the in-memory tree, before anything reaches disk."""
    hist = tree.read("tests/test_color_history.py")
    pin = tree.read("tests/test_register_pin.py")

    # THE BOUND. min_size is the half that makes the test mean anything, and
    # it is checked as a NUMBER against the constant it has to exceed, not as
    # a string -- so raising MAX_HISTORY_SIZE without raising this is visible.
    src = tree.read("core/color_history.py").lstrip("﻿")
    cap = next((n.value.value for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "MAX_HISTORY_SIZE"
                and isinstance(n.value, ast.Constant)), None)
    if cap is None:
        raise SystemExit("core/color_history.py: MAX_HISTORY_SIZE not found")
    # READ THE DECORATOR, NOT THE FILE. The first version of this check was
    # `"min_size=1, max_size=400" not in hist`, and it landed red on the
    # comment this round adds to EXPLAIN that min_size used to be 1. Use and
    # mention, seventeenth time in this programme and the third inside a
    # checker written to catch the previous one. The use is a keyword argument
    # in the @given decorator; a mention is prose. Only one of them is a node.
    tree_hist = ast.parse(hist)
    fn = next((n for n in ast.walk(tree_hist)
               if isinstance(n, ast.FunctionDef)
               and n.name == "test_history_never_exceeds_max_size"), None)
    if fn is None:
        raise SystemExit("test_history_never_exceeds_max_size is gone")
    drawn = None
    for deco in fn.decorator_list:
        if not isinstance(deco, ast.Call):
            continue
        for kw in deco.keywords:
            if kw.arg != "colors" or not isinstance(kw.value, ast.Call):
                continue
            for inner in kw.value.keywords:
                if inner.arg == "min_size" and isinstance(inner.value,
                                                          ast.Constant):
                    drawn = inner.value.value
    if drawn is None:
        raise SystemExit("the @given decorator declares no min_size for colors")
    if drawn <= cap:
        raise SystemExit(
            f"@given draws lists from min_size={drawn}, but no trim happens "
            f"below {cap + 1} colours (MAX_HISTORY_SIZE={cap}) -- so an "
            f"example can pass without ever reaching the bound. That is how "
            f"this test stayed green with the trim deleted.")

    # THE STUB, in both places that add hundreds of colours.
    if hist.count("manager.save_history = lambda: True") != 2:
        raise SystemExit(
            f"expected the save stubbed in 2 tests, found "
            f"{hist.count('manager.save_history = lambda: True')}")
    if "def test_the_trim_still_happens_when_the_save_is_real" not in hist:
        raise SystemExit(
            "the stub has no guard. Replacing save_history with a no-op is "
            "only safe while the trim does not depend on it, and nothing "
            "would say so once it did.")

    # THE SKIP. Gone as a CODE PATH -- the docstring of the replacement quotes
    # the old reason, and must be allowed to. Same trap as min_size above, hit
    # twice in one round: a string check cannot tell a skip from a sentence
    # about a skip. So read the pytest.skip CALLS, which is what a skip is.
    pin_fn = next((n for n in ast.walk(ast.parse(pin))
                   if isinstance(n, ast.FunctionDef)
                   and n.name == "test_the_installed_register_is_the_pinned_one"),
                  None)
    if pin_fn is None:
        raise SystemExit("test_the_installed_register_is_the_pinned_one is gone")

    skips, compares = [], []
    for node in ast.walk(pin_fn):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in (
                "skip", "fail"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    skips.append(arg.value)
                elif isinstance(arg, ast.JoinedStr):
                    skips.append(ast.unparse(arg))
                elif isinstance(arg, ast.BinOp):
                    skips.append(ast.unparse(arg))
        if isinstance(node, ast.Compare):
            compares.append(ast.unparse(node))

    live = [s for s in skips if "__version__" in s]
    if live:
        raise SystemExit(
            "tests/test_register_pin.py still SKIPS over __version__: "
            + "; ".join(live))
    if not any("installed" in c and "pinned" in c for c in compares):
        raise SystemExit(
            "the test does not compare the installed commit against the pin, "
            "which is the assertion the __version__ skip was standing in for")
    if "direct_url.json" not in ast.unparse(pin_fn):
        raise SystemExit(
            "tests/test_register_pin.py does not read direct_url.json -- "
            "pip's record of which commit is installed")

    print(f"checks: min_size={cap + 1} crosses MAX_HISTORY_SIZE={cap}, "
          f"2 stubs + 1 guard, the __version__ skip is gone")


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
        self.deleted: set[str] = set()

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        """Mark a file for removal. Nothing leaves disk until flush().

        Added for the round that retired the last CI deselect: with no
        deselects left, tests/test_ci_deselects.py swept an empty set and
        would have passed over nothing. Its own failure message said to
        delete it in the commit that removed the last one, so the harness
        needed to be able to.
        """
        if not (self.root / rel).exists() and rel not in self.files:
            raise SystemExit(f"cannot delete {rel}: it is not in this checkout")
        self.files.pop(rel, None)
        self.deleted.add(rel)

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
        for rel in sorted(self.deleted):
            p = self.root / rel
            if p.exists():
                p.unlink()
                touched.append(f"{rel} (deleted)")
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
