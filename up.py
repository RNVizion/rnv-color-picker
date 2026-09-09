#!/usr/bin/env python3
"""
RNV-WIRING-TOOL-DO-NOT-SWEEP

rnv-color-picker: the image budget guards a file this repository does not have.

    python up.py             # rewrite the guard, run it, run the suites
    python up.py --check     # rehearse, write nothing
    python up.py --verify    # re-run the suites against what is on disk
    python up.py --finish    # delete this script

WHAT WENT WRONG, AND WHOSE FAULT IT IS. The image-budget round wrote one
guard and installed the same one in all five applications. Its budget carried

    ('resources/icons/special_slot.png', 512, 'a slot badge'),

and only two applications have that file -- the palette manager, where it is
the 99-or-more overflow tile drawn by PreviewGrid, and the mixer, where it is
an unused byte-for-byte duplicate of the app icon. Here it named nothing.

**Nothing is wrong with your images.** The resize ran and landed: the
background is 3840 on its long edge, the three gears and the icon are 512,
and the action buttons and screenshots were never touched. What failed is the
guard's own scope, on this test:

    test_the_budget_still_matches_real_files

which exists because a glob that matches nothing passes every other assertion
and looks exactly like a repository in good order. It was written against the
possibility of a budget going stale. The first thing it found was a budget
that had never been true here.

WHAT THIS DOES. Rewrites tests/test_image_budget.py with a budget that
describes THIS repository: background, three gears, icon. The entry is
removed rather than exempted -- a budget belongs to the repository it
governs, and an exemption would have left the rule in place with a note
explaining why it never applies, which is how a guard stops being read.

It also adds one test, stating the same failure from the other side: a budget
pattern with no wildcard is a claim that a specific path exists, so it is
checked as one. An assertion that names the missing FILE is easier to act on
than one that names a glob.

NO ASSET IS OPENED, RESIZED, MOVED OR WRITTEN. One test file changes.
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-color-picker"
SENTINEL_FILE = "tests/test_image_budget.py"
SENTINEL = "RNV-IMAGE-BUDGET-SCOPE"
GUARD = "tests/test_image_budget.py"
DESCRIPTION = "correct the image budget's scope for this repository"
SUITES = [("pytest tests/", [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"])]

SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

MISSING_HELP = """\
tests/test_image_budget.py is not here, so there is no guard to correct.

That file is installed by the image-budget script. Run that one first:

    python up-for-rnv-color-picker-image-budget.py

and then this one. If you have already run it and the file is missing, stop
and say so -- that is a different problem from the one this script fixes.
"""

GUARD_SOURCE = r'''"""RNV-IMAGE-BUDGET-GUARD -- the resources stay the size they were reduced to.

Installed 2026-09-08, scope corrected 2026-09-09. This repository shipped a
window background of 16000x9038 (or 8000x4500) and a settings gear of
3334x3334 for a button that renders at 50x50. Across the five applications
that was 537 MB of pixels reproducing, for the most part, flat geometric
shapes.

The backgrounds are now 3840 on the long edge -- a full 4K width, so a
maximised window on a 4K display still scales DOWN rather than up -- and the
oversized square assets are 512.

WHAT THIS GUARD IS FOR. Nothing about a resize sticks. The next export from a
design tool lands at whatever that tool defaults to, the file is committed
because it looks right, and the repository quietly grows back. A dimension is
checkable, so it is checked.

WHAT IT DELIBERATELY DOES NOT COVER. The action buttons and the screenshots.
The action buttons are already 0.2-0.4 MB and sized for the widgets they
fill -- a rule that squeezed their long edge would crush their short one,
which is how a 1250x146 button becomes 512x60 and looks wrong on a HiDPI
screen. The screenshots are 1920x1080 documentation. Neither is a problem, so
neither is governed here.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: RNV-IMAGE-BUDGET-SCOPE, 2026-09-09. The first version of this file was
#: written once and installed in all five applications, and it carried an
#: entry for resources/icons/special_slot.png. Only two applications have
#: that file: the palette manager, where it is the 99-or-more overflow tile
#: in PreviewGrid, and the mixer, where it is an unused duplicate of the app
#: icon. In the other three the entry was a rule with no subject, and
#: test_the_budget_still_matches_real_files -- which exists for exactly that
#: failure -- caught it on the first run. The entry is gone rather than
#: exempted. A budget belongs to the repository it governs.
#:
#: glob -> the largest edge this asset may have, and why that number.
BUDGET = (
    ('resources/background_images/*.png', 3840,
     'a window background; 3840 is a full 4K width, so even a maximised '
     'window on a 4K display scales it down rather than up'),
    ('resources/button_images/settings_gear_*.png', 512,
     'renders inside a 50x50 button; 512 leaves headroom for 3x HiDPI '
     'several times over'),
    ('resources/icons/icon.png', 512,
     'the window and dock icon; 512 is the largest size any desktop asks for'),
)

#: A file over this, in a directory the budget governs, is the thing that
#: went wrong. Stated separately from the dimensions because a file can be
#: the right dimensions and still be enormous if it was saved badly.
MAX_BYTES = 16 * 1024 * 1024


def _governed():
    for pattern, limit, why in BUDGET:
        for path in sorted(ROOT.glob(pattern)):
            yield path, limit, why


def test_every_governed_asset_is_within_its_budget():
    """The one that matters.

    A dimension is the cheapest possible check and the whole reason the
    reduction holds: the next re-export from a design tool will be whatever
    that tool defaults to, and nobody looks at a file size in a diff.
    """
    pytest.importorskip('PIL', reason='Pillow is a declared dependency')
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    over = []
    for path, limit, why in _governed():
        with Image.open(path) as image:
            longest = max(image.width, image.height)
        if longest > limit:
            over.append(
                f'{path.relative_to(ROOT).as_posix()}  {image.width}x{image.height}'
                f'  (limit {limit} on the long edge — {why})')
    assert not over, (
        'these assets are larger than the size anything renders them at:\n  '
        + '\n  '.join(over)
        + '\n\nResize in place; the path must not move.')


def test_no_governed_asset_is_absurdly_heavy():
    """Dimensions and bytes are different failures.

    A 3840px PNG saved without optimisation, or as 16-bit, is the right shape
    and still ten times the weight. This catches that without pretending to
    know what a good size is.
    """
    heavy = [f'{p.relative_to(ROOT).as_posix()}  {p.stat().st_size / 1e6:.1f} MB'
             for p, _limit, _why in _governed() if p.stat().st_size > MAX_BYTES]
    assert not heavy, (
        'these are within their dimensions but very heavy:\n  '
        + '\n  '.join(heavy)
        + f'\n\nThe ceiling is {MAX_BYTES / 1e6:.0f} MB. Check the save '
          f'settings rather than the dimensions.')


def test_the_budget_still_matches_real_files():
    """Guard the guard, both ways.

    A glob that matches nothing passes every assertion above, which looks
    exactly like a repository in good order. And an entry that has stopped
    matching is a rule with no subject -- worth deleting deliberately rather
    than leaving to pass over silence.

    This is the test that caught the scope error described at BUDGET. It was
    written on the argument that a budget can go stale silently; the first
    thing it found was a budget that had never been true here at all.
    """
    empty = [pattern for pattern, _l, _w in BUDGET
             if not list(ROOT.glob(pattern))]
    assert not empty, (
        'these budget entries match no file in this repository:\n  '
        + '\n  '.join(empty)
        + '\n\nIf the asset was retired, remove its entry in the same commit.')


def test_the_budget_does_not_govern_a_file_this_repository_lacks():
    """The same failure stated from the other side, and pinned to a name.

    The scope error was one glob that named a file only two of the five
    applications ship. A pattern with no wildcard is a claim that a specific
    path exists, so it is worth checking as one -- an assertion that reads
    the filename is easier to act on than one that reads a glob.
    """
    missing = [pattern for pattern, _l, _w in BUDGET
               if '*' not in pattern and not (ROOT / pattern).exists()]
    assert not missing, (
        'the budget names files that are not in this repository:\n  '
        + '\n  '.join(missing)
        + '\n\nA budget belongs to the repository it governs. If an asset '
          'exists in a sibling application but not this one, it does not '
          'belong in this file.')


def test_the_assets_are_where_they_were():
    """No path moved.

    The reduction was done in place on purpose: this project's standing
    instruction is that the image directories are correct and are not to be
    rearranged. A resize that also relocated a file would be a much larger
    change wearing a smaller one's clothes.
    """
    for directory in ('resources/background_images', 'resources/button_images',
                      'resources/icons'):
        assert (ROOT / directory).is_dir(), (
            f'{directory} is missing. The image resize was done in place and '
            f'must not have moved anything.')
'''


def _budget_of(text: str, where: str):
    """Read the BUDGET tuple out of a guard's SOURCE, without importing it.

    The guard imports pytest and resolves paths from __file__, so executing
    it to inspect it would be answering a question about a file by running
    it somewhere it does not live. ast.literal_eval reads the literal and
    refuses anything that is not one.
    """
    tree = ast.parse(text, where)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "BUDGET" for t in node.targets):
            return list(ast.literal_eval(node.value))
    raise SystemExit(f"{where}: no BUDGET assignment found")


def edits(tree) -> None:
    """Validate what is on disk before replacing it.

    The harness writes GUARD_SOURCE over GUARD immediately after this
    returns, so the only job here is to refuse when the file on disk is not
    the thing this script was written to correct.
    """
    installed = tree.read(SENTINEL_FILE)
    if "RNV-IMAGE-BUDGET-GUARD" not in installed:
        raise SystemExit(
            f"{SENTINEL_FILE} exists but is not the image-budget guard. "
            f"Refusing to overwrite a file this script did not install.")

    before = _budget_of(installed, SENTINEL_FILE)
    dead = [pattern for pattern, *_ in before
            if not list(Path.cwd().glob(pattern))]
    if not dead:
        raise SystemExit(
            "every entry in the installed budget matches a real file here, "
            "so there is nothing to correct. If a suite is red, it is red "
            "for some other reason.")

    print(f"  installed budget: {len(before)} entries, "
          f"{len(dead)} matching nothing")
    for pattern in dead:
        print(f"    - {pattern}")


def checks(tree) -> None:
    root = Path.cwd()
    new = tree.files[GUARD]

    # 1. it parses. A guard that does not import is a guard that does not run,
    #    and pytest reports that as a collection error rather than a failure.
    try:
        ast.parse(new, GUARD)
    except SyntaxError as exc:
        raise SystemExit(f"the replacement guard does not parse: {exc}")

    after = _budget_of(new, GUARD)

    # 2. every entry names something real. This is the assertion that failed;
    #    check it here, against the in-memory file, so --check is a true
    #    rehearsal rather than a promise.
    dead = [pattern for pattern, *_ in after if not list(root.glob(pattern))]
    if dead:
        raise SystemExit("the replacement budget still names nothing: "
                         + ", ".join(dead))

    # 3. and nothing real was dropped along with it. Removing the whole
    #    budget would satisfy check 2 perfectly.
    for pattern in ("resources/background_images/*.png",
                    "resources/button_images/settings_gear_*.png",
                    "resources/icons/icon.png"):
        if not any(p == pattern for p, *_ in after):
            raise SystemExit(f"the replacement budget lost {pattern}; that is "
                             f"a real asset and must stay governed")

    # 4. the previous round's resize is on disk. This script does not touch
    #    an asset, so if one is over budget the guard will be red for a
    #    reason this script cannot fix, and saying so now beats a test
    #    failure five minutes into a Qt suite.
    try:
        from PIL import Image
    except ImportError:
        print("  guards: Pillow not importable; skipped the on-disk size check")
    else:
        Image.MAX_IMAGE_PIXELS = None
        over = []
        for pattern, limit, _why in after:
            for path in sorted(root.glob(pattern)):
                with Image.open(path) as image:
                    if max(image.width, image.height) > limit:
                        over.append(f"{path.relative_to(root).as_posix()} "
                                    f"{image.width}x{image.height} > {limit}")
        if over:
            raise SystemExit(
                "these assets are still over budget, which this script does "
                "not fix -- run the image-budget script first:\n  "
                + "\n  ".join(over))

    # 5. the marker landed, or --verify has nothing to recognise later.
    if SENTINEL not in new:
        raise SystemExit("the scope note did not land")

    print(f"  guards: {len(after)} budget entries, all matching real files; "
          f"every governed asset within budget on disk")


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
