"""A widget's parent kept alive for a test is released by the test.

FOUND 2026-11-03, when PyQt6 6.12.0 was released and the picker's CI went red
on Linux and on Windows, the day after the rev 49 round landed. The suite
crashed (a segmentation fault, or an abort) in
test_settings_panel.py::TestPanelFollowsASwitch, at a call that runs every
pending deferred delete. Halving the files and then the tests that ran before
it found the one that set it up:
test_progress_and_scroll.py::TestQuickProgressDialog::test_construction_with_dark_theme_parent.

The pattern, in 20 places in three files: a dialog or panel is built with a
real QWidget parent, the test keeps the parent alive by storing it on the
child as `_test_real_parent`, and registers only the child with qtbot. qtbot
closes the child and schedules its deletion at the test's end; the parent is
left to Python. Child and parent now reference each other, so only the
garbage collector frees them, whenever it next runs, in some later test.
Deleting the parent then deletes the child, which already had its deletion
scheduled. PyQt6 6.11 survived that; 6.12 does not. The same commit passes
every test on 6.11, and crashed on 6.12 before this change.

THE FIX IS THE OWNERSHIP, NOT THE VERSION. Each parent is registered with
qtbot after its child, so Qt closes and deletes both at the test's end, the
child first. This test holds that every kept-alive parent is registered.
"""
from __future__ import annotations

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
KEEP = re.compile(r"^\s*(\w+)\._test_real_parent = (\w+)")


def _sites():
    """(file, line number, child, parent, the lines after it) for each kept-alive parent."""
    out = []
    for path in sorted(TESTS.glob("test_*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = KEEP.match(line)
            if m:
                out.append((path.name, i + 1, m.group(1), m.group(2), lines[max(0, i - 4):i + 4]))
    return out


def test_there_are_kept_alive_parents_to_check():
    assert len(_sites()) >= 10, "the pattern this guards was not found: the reader is blind"


def test_every_kept_alive_parent_is_registered_with_qtbot_after_its_child():
    unreleased = []
    for name, number, child, parent, near in _sites():
        text = "\n".join(near)
        child_at = text.find(f"qtbot.addWidget({child})")
        parent_at = text.find(f"qtbot.addWidget({parent})")
        if parent_at < 0 or child_at < 0 or parent_at < child_at:
            unreleased.append(f"{name}:{number}: {child}._test_real_parent = {parent}")
    assert not unreleased, (
        "a parent kept alive for a test, and not registered with qtbot after its "
        "child, is freed by Python's garbage collector in some later test:\n  "
        + "\n  ".join(unreleased))
