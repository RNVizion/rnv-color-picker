"""Test dependencies live at tests/requirements-dev.txt.

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
