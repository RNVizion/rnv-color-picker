#!/usr/bin/env python3
"""rnv-color-picker -- the ruled light-mode error red, and the test deps move.

WHAT THIS CHANGES

1. A LIGHT-MODE ERROR RED, DERIVED

       STATUS_ERROR        = "#dc3545"                    registered base
       STATUS_ERROR_LIGHT  = lighten(STATUS_ERROR, -20)   -> #c82131

   Light error text moves #dc3545 -> #c82131, which takes it from 4.1528 on
   #f5f5f5 to 5.1811. It clears 4.5:1 down to #e8e8e8 -- the SAME coverage
   boundary the gold publishes, so the two rules do not have to be remembered
   separately.

   Uniform per-channel holds hue exactly at 354.25 degrees, for red as for
   gold. That is worth knowing: the derivation rule is not a property of the
   gold hues.

   Dark is NOT touched. #e56b77 reads 5.5537 on #1a1a1a and was never short.
   Replacing a colour that is not broken to buy uniformity is a bigger change
   than the problem justifies.

   The error FILL is not touched either. STATUS_ERROR_BG with black on it
   reads 4.6383 and always passed; only the bare TEXT was short. It now reads
   `= STATUS_ERROR` so the base has one home.

2. THE EXEMPTION IS RETIRED, AS IT ASKED TO BE

   test_light_error_text_is_the_ruled_value_and_no_worse asserted the
   shortfall in BOTH directions -- fail if it regresses, and fail if it ever
   CLEARS, with a message saying to delete the test rather than leave a
   standing note about a problem that no longer exists.

   That is exactly what happens here. The two-way assertion is why this could
   not be quietly left behind: raising the value turns the old test red, so
   the retirement is forced rather than remembered.

3. A DEAD ENTRY IN IMAGE_MODE_COLORS, MADE LIVE

   IMAGE_MODE_COLORS lists 'status_error_text' BEFORE `**DARK_THEME_COLORS`,
   so the splat overwrites it. The explicit entry has never had any effect.
   It holds the same value the splat supplies, so nothing renders wrong today
   -- but anyone editing that line to change image mode would watch it do
   nothing. Moved after the splat, where it means what it looks like.

4. TEST DEPENDENCIES MOVE

       requirements-test.txt  ->  tests/requirements-dev.txt

   All six repositories converge on that path.

USE VS MENTION -- WHAT IS NOT REWRITTEN

  CHANGELOG.md:109 records that a past release introduced
  `requirements-test.txt`. That is a true statement about the past. Rewriting
  it would make the record false, so it is exempted on purpose, and the
  exemption is asserted in both directions so it cannot rot into a licence.

USAGE

    python up.py --check     # dry run; every pass runs, nothing is written
    python up.py             # apply
    python up.py --finish    # delete this script

Runs from the repository root, as up.py or scripts/up.py. Safe to run twice.
"""

from __future__ import annotations

import os
import subprocess
import sys

CONFIG = "utils/config.py"
CONTRAST = "tests/test_brand_contrast.py"
OLD_DEPS = "requirements-test.txt"
NEW_DEPS = "tests/requirements-dev.txt"


# --------------------------------------------------------------------------
# 1. The colour
# --------------------------------------------------------------------------

ANCHOR_CONSTANTS = '''BRAND_DARK_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_DARK_GOLD)
"""Derived, same reason. This one held (177, 145, 69) -- the retired gold,
in the one form no sweep would have found."""
'''

NEW_CONSTANTS = '''

# ============================================================================
# STATUS RED
# ============================================================================
#
# The same shape as the gold: one registered value, one derivative, and the
# derivative is COMPUTED so it cannot drift from its base.
#
# No red carries text at 4.5:1 on a real light panel. #dc3545 clears only on
# pure white, at 4.5275, and the Material red this family retired fails even
# there at 3.6824 -- its value is deliberately not written here, because
# test_one_status_family_only forbids it appearing in this file at all.
# So light spends a derivative on TEXT for exactly the reason the gold does:
# the fill and text jobs occupy non-overlapping luminance bands.

STATUS_ERROR: Final[str] = "#dc3545"
"""Registered. Fills, borders, and the ground that black is drawn on.

Black on it reads 4.6383, which passes and is not affected by the text
derivative below."""

STATUS_ERROR_LIGHT: Final[str] = lighten(STATUS_ERROR, -20)   # -> #c82131
"""Derived. Error TEXT on a light panel.

5.1811 on #f5f5f5, 4.8685 on #eeeeee, 4.6100 on #e8e8e8 -- the same coverage
boundary BRAND_DARK_GOLD_DEEP publishes. Below #e8e8e8 the red does not carry
text, which is a ruling rather than a gap.

Uniform per-channel holds hue at 354.25 degrees, identical to the base. The
hand-written reds in this family drift: #e56b77 is (+9, +54, +50) off the
base and #ff6b6b is (+35, +54, +38).

Dark keeps #e56b77 by decision, not oversight -- it reads 5.5537 on #1a1a1a
and was never short."""
'''

# Each palette's comment explained a rationale that this change replaces.
OLD_COMMENT = """    # Error message text. Theme-aware because no single red clears both
    # grounds: the register's #e56b77 is a dark-theme value and measures
    # 2.8745 on the light panel."""

DARK_COMMENT = """    # Error message text. Theme-aware because no single red clears both
    # grounds. Dark keeps #e56b77 (5.5537 on #1a1a1a); light uses the derived
    # STATUS_ERROR_LIGHT. See the STATUS RED block above."""

LIGHT_COMMENT = """    # Error message text. STATUS_ERROR_LIGHT, derived from the registered
    # red so it cannot drift from it. 5.1811 on this panel's #f5f5f5, where
    # the undarkened #dc3545 read 4.1528 and was carried as an exemption."""

IMAGE_COMMENT = """    # Error message text. Image mode inherits dark's value; the entry sits
    # AFTER the splat because a key listed before it is silently discarded."""

COLOUR_EDITS = (
    # (path, old, new, why)
    (CONFIG, ANCHOR_CONSTANTS, ANCHOR_CONSTANTS + NEW_CONSTANTS,
     "introduce the registered red and its derivative, before the palettes"),
    (CONFIG,
     OLD_COMMENT + "\n    'status_error_text': '#e56b77',\n    'name': 'Dark',",
     DARK_COMMENT + "\n    'status_error_text': '#e56b77',\n    'name': 'Dark',",
     "DARK keeps its value; only the rationale changes"),
    (CONFIG,
     OLD_COMMENT + "\n    'status_error_text': '#dc3545',\n    'name': 'Light',",
     LIGHT_COMMENT + "\n    'status_error_text': STATUS_ERROR_LIGHT,\n    'name': 'Light',",
     "LIGHT -- the only rendered value that moves"),
    (CONFIG,
     OLD_COMMENT + "\n    'status_error_text': '#e56b77',\n    **DARK_THEME_COLORS,",
     "    **DARK_THEME_COLORS,\n" + IMAGE_COMMENT + "\n    'status_error_text': '#e56b77',",
     "IMAGE -- the entry moves AFTER the splat that was discarding it"),
    (CONFIG,
     'STATUS_ERROR_BG:   Final[str] = "#dc3545"',
     'STATUS_ERROR_BG:   Final[str] = STATUS_ERROR',
     "the fill now names the base instead of restating its value"),
    (CONFIG,
     "    'STATUS_ERROR_BG',\n    'STATUS_ERROR_FG',",
     "    'STATUS_ERROR',\n    'STATUS_ERROR_LIGHT',\n"
     "    'STATUS_ERROR_BG',\n    'STATUS_ERROR_FG',",
     "export the two new names"),
)


# --------------------------------------------------------------------------
# 2. The dependency move
# --------------------------------------------------------------------------

DEP_REWRITES = (
    (".github/workflows/tests.yml",
     "pip install -r requirements-test.txt",
     "pip install -r tests/requirements-dev.txt",
     "LIVE -- CI fails outright without this"),
    ("pyproject.toml",
     "# Test and development dependencies — kept in sync with requirements-test.txt",
     "# Test and development dependencies — kept in sync with tests/requirements-dev.txt",
     "DOCS -- a comment naming the file it mirrors"),
)

# Rewrites applied INSIDE the moved file. The second one is the trap.
SELF_REWRITES = (
    ("# Install with: pip install -r requirements-test.txt",
     "# Install with: pip install -r tests/requirements-dev.txt",
     "its own install line would otherwise name a path that no longer exists"),
    ("-r requirements.txt",
     "-r ../requirements.txt",
     "pip resolves a -r include RELATIVE TO THE FILE THAT CONTAINS IT, not "
     "to the working directory. Moved into tests/ and left alone, this line "
     "asks for tests/requirements.txt and pip fails with a message naming a "
     "file nobody ever wrote. No path assertion catches it -- only running "
     "pip does"),
)

# Files that may keep saying the old path, and why. Asserted BOTH ways.
DEP_EXEMPT = {
    "CHANGELOG.md":
        "HISTORY -- records what a past release shipped; rewriting it would "
        "make a true statement false",
    "tests/test_dependency_file_placement.py":
        "the guard; its job is to name the retired path",
}


# --------------------------------------------------------------------------
# 3. Guards
# --------------------------------------------------------------------------

GUARD_PATH = "tests/test_dependency_file_placement.py"

GUARD_SOURCE = r'''"""Test dependencies live at tests/requirements-dev.txt.

All six RNV repositories converge on that path. This file MENTIONS the
retired `requirements-test.txt` and is therefore excluded from the sweep that
forbids it -- the use/mention distinction, which has produced a false "clean"
in this family more than once.
"""

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
WANTED = REPO / "tests" / "requirements-dev.txt"
RETIRED = "requirements-test.txt"

SKIP_DIRS = {".git", "build", "dist", "__pycache__", ".venv", ".pytest_cache",
             "htmlcov", "scripts", ".benchmarks", ".hypothesis"}

MENTION_ONLY = {pathlib.Path(__file__).name}

# A changelog records what a past release shipped. Rewriting it would turn a
# true statement false, so it keeps the retired name on purpose -- and the
# exemption is asserted live below, so it cannot rot into a blanket licence.
HISTORY_FILES = {"CHANGELOG.md"}

TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".ini",
                 ".cfg", ".sh", ".bat"}


def _is_delivery_script(path):
    if "scripts" in path.parts:
        return True
    return path.parent == REPO and path.name.startswith("up")


def _files():
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in MENTION_ONLY or _is_delivery_script(path):
            continue
        yield path


def test_the_dependency_file_is_where_it_belongs():
    assert WANTED.is_file(), f"{WANTED} is missing"
    assert not (REPO / RETIRED).exists(), \
        f"{RETIRED} is still at the repository root"


def test_the_moved_file_still_has_content():
    """A move that produced an empty file satisfies every path assertion here
    and fails only at pip-install time, in someone else's error message."""
    lines = [ln.strip() for ln in WANTED.read_text(encoding="utf-8").splitlines()]
    packages = [ln for ln in lines if ln and not ln.startswith("#")]
    assert len(packages) >= 3, f"only {len(packages)} requirements found"


def test_every_include_in_the_moved_file_resolves():
    """The assertion that would have caught this move breaking.

    pip resolves a `-r` include RELATIVE TO THE FILE THAT CONTAINS IT. This
    file carried `-r requirements.txt` while it sat at the repository root,
    where that was correct. Moved into tests/ unchanged, the same line asks
    for tests/requirements.txt -- a file nobody has ever written.

    Nothing above catches it. The path assertions pass, the content assertion
    passes, every test in the suite passes, and CI fails at pip-install time
    with an error naming a file that does not appear anywhere in the
    repository. Only resolving the include finds it.
    """
    includes = [ln.strip().split(None, 1)[1].strip()
                for ln in WANTED.read_text(encoding="utf-8").splitlines()
                if ln.strip().startswith("-r ")]
    assert includes, (
        "no -r include found. If one was removed deliberately, remove this "
        "test with it rather than leaving it passing vacuously.")
    for include in includes:
        target = (WANTED.parent / include).resolve()
        assert target.is_file(), (
            f"{WANTED.name} includes {include!r}, which resolves to {target} "
            f"and does not exist")


def test_nothing_live_still_points_at_the_retired_path():
    offenders = [p.relative_to(REPO).as_posix() for p in _files()
                 if p.name not in HISTORY_FILES
                 and RETIRED in p.read_text(encoding="utf-8", errors="replace")]
    assert not offenders, \
        "these still name the retired path:\n  " + "\n  ".join(offenders)


def test_that_sweep_is_actually_looking():
    """Guard the guard. A sweep that walks an empty list passes forever."""
    walked = {p.relative_to(REPO).as_posix() for p in _files()}
    assert len(walked) > 20, f"the sweep only found {len(walked)} files"
    for required in ("pyproject.toml", ".github/workflows/tests.yml"):
        assert required in walked, f"{required} is not being swept"
    assert RETIRED in f"pip install -r {RETIRED}", \
        "the retired-path pattern no longer matches a known offender"


def test_the_history_exemption_is_load_bearing():
    """Asserted in BOTH directions.

    CHANGELOG.md is skipped by the sweep above. If it ever stops naming the
    retired path, the exemption is dead weight -- and dead weight is a licence
    waiting for a future defect, so this fails rather than passing quietly.
    """
    changelog = REPO / "CHANGELOG.md"
    assert changelog.exists(), "CHANGELOG.md is gone; drop the exemption"
    assert RETIRED in changelog.read_text(encoding="utf-8", errors="replace"), (
        "CHANGELOG.md no longer names the retired path, so exempting it "
        "protects nothing. Remove it from HISTORY_FILES.")


def test_the_mention_exemption_is_load_bearing():
    here = pathlib.Path(__file__)
    assert here.name in MENTION_ONLY
    assert RETIRED in here.read_text(encoding="utf-8"), \
        "this file no longer mentions the retired path -- drop the exemption"


def test_the_workflow_installs_from_the_new_path():
    text = (REPO / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8")
    assert "pip install -r tests/requirements-dev.txt" in text
'''


# --------------------------------------------------------------------------
# 4. The exemption being retired, and what replaces it
#
# The old block is embedded VERBATIM rather than matched by pattern. A regex
# that drifts by one character silently matches nothing and the retirement
# ships half done; an exact 35-line block either matches once or stops the
# run. check_fingerprint asserts the count is exactly 1.
# --------------------------------------------------------------------------

EXEMPTION_BLOCK = r'''# ══════════════════════════════════════════════════════════════════════════
# THE PAIRING THE WALKER CANNOT SEE
# ══════════════════════════════════════════════════════════════════════════
#
# The error label sets a colour and no background of its own -- it inherits
# the panel it sits on. The stylesheet walker only records a pair when both
# halves appear in one rule, so this pairing is invisible to it and has to
# be asserted by hand.

LIGHT_ERROR_SHORTFALL = 4.1528   # measured, #dc3545 on #f5f5f5


def test_dark_error_text_clears_its_panel() -> None:
    d = C.DARK_THEME_COLORS
    assert contrast_ratio(d["status_error_text"], d["panel_bg"]) >= TEXT_FLOOR


def test_light_error_text_is_the_ruled_value_and_no_worse() -> None:
    """The register rules #dc3545 for light mode and explicitly declines to
    derive a darker variant. Its #e56b77 error-text is a dark-theme value
    and measures 2.8745 here -- worse than what we have.

    So this pairing is short at 4.1528, against 3.3777 for the retired
    Material red. The test holds the improvement and fails if it regresses.
    """
    light = C.LIGHT_THEME_COLORS
    ratio = contrast_ratio(light["status_error_text"], light["panel_bg"])
    assert ratio >= LIGHT_ERROR_SHORTFALL - 0.0001, (
        f"light error text regressed to {ratio:.4f}, below the "
        f"{LIGHT_ERROR_SHORTFALL} this pass established")
    assert ratio < TEXT_FLOOR, (
        f"light error text now measures {ratio:.4f} and CLEARS the floor. "
        f"Brand Infrastructure has presumably ruled a light-mode error "
        f"text -- delete this test and its exemption rather than leaving a "
        f"standing note about a problem that no longer exists.")'''

EXEMPTION_REPLACEMENT = r'''# ══════════════════════════════════════════════════════════════════════════
# THE PAIRING THE WALKER CANNOT SEE
# ══════════════════════════════════════════════════════════════════════════
#
# The error label sets a colour and no background of its own -- it inherits
# the panel it sits on. The stylesheet walker only records a pair when both
# halves appear in one rule, so this pairing is invisible to it and has to
# be asserted by hand.
#
# It used to be asserted as an EXEMPTION: light error text measured 4.1528 on
# #f5f5f5, short of the floor, and the test held that number and failed if it
# ever cleared -- with a message telling whoever cleared it to delete the test
# rather than leave a standing note about a problem that no longer exists.
#
# That has now happened. STATUS_ERROR_LIGHT = lighten(STATUS_ERROR, -20)
# reads 5.1811 on #f5f5f5, so the exemption is gone and this is an ordinary
# floor assertion. Doing as the old test instructed is the point: an exemption
# that outlives its problem is a licence waiting for a future defect.


def test_dark_error_text_clears_its_panel() -> None:
    d = C.DARK_THEME_COLORS
    assert contrast_ratio(d["status_error_text"], d["panel_bg"]) >= TEXT_FLOOR


def test_light_error_text_clears_its_panel() -> None:
    """No exemption. The light error red is derived to clear the floor."""
    light = C.LIGHT_THEME_COLORS
    ratio = contrast_ratio(light["status_error_text"], light["panel_bg"])
    assert ratio >= TEXT_FLOOR, (
        f"light error text measures {ratio:.4f}, below the {TEXT_FLOOR} floor")


def test_light_error_text_is_derived_not_written() -> None:
    """A written-down derivative orphans the moment its base moves. This one
    is computed, so it cannot drift from STATUS_ERROR."""
    assert C.LIGHT_THEME_COLORS["status_error_text"] == C.STATUS_ERROR_LIGHT
    assert C.STATUS_ERROR_LIGHT == C.lighten(C.STATUS_ERROR, -20)
    assert C.STATUS_ERROR_LIGHT != C.STATUS_ERROR, (
        "the light error red must be a DERIVATIVE, not the base value")


def test_light_error_text_carries_down_to_the_published_boundary() -> None:
    """The gold publishes #e8e8e8 as the ground below which it stops carrying
    text. The error red is derived to the same boundary, so the two rules do
    not have to be remembered separately."""
    for ground in ("#ffffff", "#f5f5f5", "#eeeeee", "#e8e8e8"):
        ratio = contrast_ratio(C.STATUS_ERROR_LIGHT, ground)
        assert ratio >= TEXT_FLOOR, \
            f"{C.STATUS_ERROR_LIGHT} on {ground} = {ratio:.4f}"


def test_the_error_fill_still_pairs_with_black() -> None:
    """STATUS_ERROR_BG/_FG is a FILL, not text, and was never short. Asserted
    so this pass cannot quietly move it while fixing the text beside it."""
    assert contrast_ratio(C.STATUS_ERROR_FG, C.STATUS_ERROR_BG) >= TEXT_FLOOR
    assert C.STATUS_ERROR_BG == C.STATUS_ERROR'''


# --------------------------------------------------------------------------
# Machinery -- in-memory tree, flushed only after verification
# --------------------------------------------------------------------------

class Halt(SystemExit):
    pass


def _this_script() -> str:
    return os.path.relpath(os.path.realpath(__file__),
                           os.path.realpath(os.getcwd())).replace(os.sep, "/")


class Tree:
    SKIP_DIRS = {".git", "__pycache__", "build", "dist", ".venv", "scripts",
                 ".pytest_cache", "htmlcov", ".benchmarks", ".hypothesis"}
    TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".ini",
                     ".cfg", ".sh", ".bat"}

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.dirty: set[str] = set()

    def get(self, path: str) -> str:
        if path not in self.files:
            with open(path, "r", encoding="utf-8") as handle:
                self.files[path] = handle.read()
        return self.files[path]

    def sweep_text(self, path: str) -> str:
        if path in self.files:
            return self.files[path]
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def set(self, path: str, text: str) -> None:
        self.files[path] = text
        self.dirty.add(path)

    def texts(self):
        me = _this_script()
        for root, dirs, names in os.walk("."):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for name in sorted(names):
                if os.path.splitext(name)[1] not in self.TEXT_SUFFIXES:
                    continue
                path = os.path.relpath(os.path.join(root, name),
                                       ".").replace(os.sep, "/")
                if path != me:
                    yield path

    def flush(self) -> int:
        for path in sorted(self.dirty):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self.files[path])
        return len(self.dirty)


def git(*args: str) -> str:
    result = subprocess.run(("git",) + args, capture_output=True, text=True)
    if result.returncode:
        raise Halt(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def lighten(hex_color: str, step: int) -> str:
    h = hex_color.lstrip("#")
    channels = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return "#" + "".join(f"{max(0, min(255, c + step)):02x}" for c in channels)


def contrast(a: str, b: str) -> float:
    def lum(value: str) -> float:
        h = value.lstrip("#")
        parts = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        parts = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
                 for x in parts]
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]
    first, second = sorted((lum(a), lum(b)), reverse=True)
    return (first + 0.05) / (second + 0.05)


# --------------------------------------------------------------------------
# Passes
# --------------------------------------------------------------------------

def already_done() -> bool:
    if os.path.exists(CONFIG) and "STATUS_ERROR_LIGHT" in open(
            CONFIG, encoding="utf-8").read():
        print("Already applied -- utils/config.py defines STATUS_ERROR_LIGHT.")
        print("Nothing to do. This is the idempotent exit, not an error.")
        return True
    return False


def check_fingerprint(tree: Tree, block: str) -> None:
    problems = []
    for path, old, _new, why in COLOUR_EDITS + DEP_REWRITES:
        if not os.path.exists(path):
            problems.append(f"  {path} does not exist")
            continue
        count = tree.sweep_text(path).count(old)
        if count != 1:
            problems.append(
                f"  {path}: expected 1 occurrence of {old.splitlines()[0][:60]!r}"
                f", found {count}\n      ({why})")
    if tree.sweep_text(CONTRAST).count(block) != 1:
        problems.append(f"  {CONTRAST}: the exemption block is not present "
                        f"exactly once")
    if not os.path.exists(OLD_DEPS):
        problems.append(f"  {OLD_DEPS} is not at the repository root")
    if os.path.exists(NEW_DEPS):
        problems.append(f"  {NEW_DEPS} already exists")
    if problems:
        raise Halt("This is not the tree this script was written against:\n"
                   + "\n".join(problems)
                   + "\n\nRun it from the root of a clean checkout of main.")


def apply_colour(tree: Tree) -> None:
    for path, old, new, why in COLOUR_EDITS:
        tree.set(path, tree.get(path).replace(old, new, 1))
        print(f"  {why}")


def retire_the_exemption(tree: Tree, block: str, replacement: str) -> None:
    tree.set(CONTRAST, tree.get(CONTRAST).replace(block, replacement, 1))
    print(f"  {CONTRAST}: the two-way exemption is replaced by an ordinary")
    print(f"    floor assertion, plus three tests the exemption never had")


def assert_no_dep_reference_was_missed(tree: Tree) -> None:
    listed = {path for path, _o, _n, _w in DEP_REWRITES}
    exempt = set(DEP_EXEMPT) | {OLD_DEPS, GUARD_PATH}
    unaccounted = [p for p in tree.texts()
                   if OLD_DEPS in tree.sweep_text(p)
                   and p not in listed and p not in exempt]
    if unaccounted:
        raise Halt(
            "These name the old dependency path but are in neither the\n"
            "rewrite list nor the exemption list. Each is either a rewrite\n"
            "this script is missing, or a HISTORY-class reference that must\n"
            "be exempted deliberately -- decide which:\n  "
            + "\n  ".join(unaccounted))
    print(f"  every file naming the old path is accounted for "
          f"({len(listed)} to rewrite, {len(DEP_EXEMPT)} exempt)")


def assert_dep_exemptions_are_live(tree: Tree) -> None:
    for path, why in DEP_EXEMPT.items():
        if path == GUARD_PATH:
            if OLD_DEPS not in GUARD_SOURCE:
                raise Halt(f"{path} is exempted but the guard no longer names "
                           f"{OLD_DEPS}. Drop the exemption.")
            continue
        if not os.path.exists(path):
            raise Halt(f"{path} is exempted ({why}) but does not exist")
        if OLD_DEPS not in tree.sweep_text(path):
            raise Halt(
                f"{path} is exempted ({why}) but does not name {OLD_DEPS}. "
                f"The exemption protects nothing and should be removed rather "
                f"than left as a standing licence.")
        print(f"  exemption live: {path}")


def move_the_deps(tree: Tree, dry: bool) -> None:
    body = tree.get(OLD_DEPS)
    for old_line, new_line, why in SELF_REWRITES:
        if old_line not in body:
            raise Halt(f"{OLD_DEPS} does not contain {old_line!r}\n  ({why})")
        body = body.replace(old_line, new_line, 1)
        print(f"    inside the file: {old_line!r} -> {new_line!r}")
    tree.set(NEW_DEPS, body)
    if not dry:
        git("mv", OLD_DEPS, NEW_DEPS)
    print(f"  {OLD_DEPS} -> {NEW_DEPS}  (git mv, so history follows)")


def rewrite_dep_references(tree: Tree) -> None:
    for path, old, new, why in DEP_REWRITES:
        tree.set(path, tree.get(path).replace(old, new, 1))
        print(f"  {path}  [{why.split(' -- ')[0]}]")


def install_guard(tree: Tree) -> None:
    tree.set(GUARD_PATH, GUARD_SOURCE)
    print(f"  {GUARD_PATH}: {len(GUARD_SOURCE.splitlines())} lines")


def verify(tree: Tree) -> None:
    problems = []
    config_src = tree.get(CONFIG)

    derived = lighten("#dc3545", -20)
    if derived != "#c82131":
        problems.append(f"the derivation gives {derived}, expected #c82131")
    for ground, floor in (("#ffffff", 4.5), ("#f5f5f5", 4.5),
                          ("#eeeeee", 4.5), ("#e8e8e8", 4.5)):
        ratio = contrast(derived, ground)
        if ratio < floor:
            problems.append(f"{derived} on {ground} = {ratio:.4f}, below {floor}")

    # The values that must NOT have moved.
    if config_src.count("'status_error_text': '#e56b77'") != 2:
        problems.append("dark/image error text is no longer #e56b77 in both")
    if "'status_error_text': STATUS_ERROR_LIGHT," not in config_src:
        problems.append("light error text does not read STATUS_ERROR_LIGHT")
    if "'status_error_text': '#dc3545'" in config_src:
        problems.append("a palette still holds the undarkened red as text")
    if "STATUS_ERROR_BG:   Final[str] = STATUS_ERROR" not in config_src:
        problems.append("the error fill no longer names the base")
    if "STATUS_ERROR_LIGHT: Final[str] = lighten(STATUS_ERROR, -20)" \
            not in config_src:
        problems.append("the derivative is not computed from the base")

    # The image-mode entry must now sit AFTER the splat.
    splat = config_src.find("**DARK_THEME_COLORS,")
    image_key = config_src.find("'status_error_text': '#e56b77',", splat)
    if splat < 0 or image_key < 0:
        problems.append("could not locate the image-mode entry after the splat")

    # The exemption must be gone, and its replacement present.
    contrast_src = tree.get(CONTRAST)
    if "LIGHT_ERROR_SHORTFALL" in contrast_src:
        problems.append("the retired exemption constant is still present")
    if "test_light_error_text_clears_its_panel" not in contrast_src:
        problems.append("the replacement floor assertion is missing")

    # Dependency sweep, with the exemptions honoured and asserted.
    swept = 0
    for path in tree.texts():
        if path in DEP_EXEMPT or path in (OLD_DEPS, NEW_DEPS):
            continue
        swept += 1
        if OLD_DEPS in tree.sweep_text(path):
            problems.append(f"{path} still names {OLD_DEPS}")
    if swept < 20:
        problems.append(f"the sweep visited only {swept} files; it is not looking")
    if OLD_DEPS not in f"pip install -r {OLD_DEPS}":
        problems.append("the sweep pattern no longer matches a known offender")

    body = tree.get(NEW_DEPS)
    packages = [ln for ln in (l.strip() for l in body.splitlines())
                if ln and not ln.startswith("#")]
    if len(packages) < 3:
        problems.append(f"the moved file holds only {len(packages)} requirements")

    if problems:
        raise Halt("VERIFY FAILED -- nothing was written:\n  "
                   + "\n  ".join(problems))
    print(f"  verify: {derived} clears 4.5 down to #e8e8e8; dark unchanged; "
          f"fill unchanged;")
    print(f"    exemption retired; {swept} files swept; "
          f"{len(packages)} requirements intact")


def finish() -> None:
    here = os.path.abspath(__file__)
    os.remove(here)
    print(f"Removed {here}")


def main() -> int:
    if "--finish" in sys.argv:
        finish()
        return 0

    dry = "--check" in sys.argv

    if not os.path.isdir(".git"):
        raise Halt("run this from the repository root (.git not found)")
    if already_done():
        return 0

    block, replacement = EXEMPTION_BLOCK, EXEMPTION_REPLACEMENT

    tree = Tree()
    check_fingerprint(tree, block)

    print("DRY RUN -- every pass runs, nothing is written\n" if dry
          else "Applying\n")

    print("1. the ruled light-mode error red")
    apply_colour(tree)

    print("\n2. retire the exemption, as its own message instructed")
    retire_the_exemption(tree, block, replacement)

    print("\n3. account for every reference to the old dependency path")
    assert_no_dep_reference_was_missed(tree)
    assert_dep_exemptions_are_live(tree)

    print("\n4. move the dependency file")
    move_the_deps(tree, dry)
    rewrite_dep_references(tree)

    print("\n5. guard")
    install_guard(tree)

    print("\n6. verify the pending tree")
    verify(tree)

    if dry:
        print(f"\nDry run complete. {len(tree.dirty)} files would change; "
              f"none were written. The git mv did not run.")
        return 0

    written = tree.flush()
    print(f"\n7. wrote {written} files")

    print("\nDone. Now run, from the repository root:")
    print("    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q")
    print("    QT_QPA_PLATFORM=offscreen python -m unittest test_rnv_color_picker")
    print(f"\nThen, once green:  python {_this_script()} --finish")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as stop:
        print(f"\n{stop}", file=sys.stderr)
        sys.exit(1)
