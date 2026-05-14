"""
Root-level conftest.py for the RNV Color Picker test suite.

PURPOSE
-------
pytest collects tests from `tests/`, but when it does so it does NOT
automatically add the project root to `sys.path`. That means a test like

    from utils.signal_manager import SignalConnectionManager

fails with `ModuleNotFoundError: No module named 'utils.signal_manager'`
because `utils/` lives at the project root, not inside `tests/`.

This file fixes that by prepending the project root (the directory this
conftest.py lives in) to sys.path BEFORE any test module is parsed.

Why a root-level conftest.py and not just `pythonpath = .` in pytest.ini?
- pytest.ini's `pythonpath` works in most setups but silently no-ops in a
  few edge cases (older pytest, certain CI runners, coverage subprocesses)
- A conftest.py at the import root is the canonical, bulletproof solution
  documented by pytest itself
- Belt-and-suspenders: we keep BOTH so neither has to be perfect

This file should NOT define fixtures, hooks, or imports that touch Qt.
Keep it minimal and sys.path-only.
"""

import os
import sys

# Absolute path to the directory containing this conftest.py — i.e., the project root.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Prepend (not append) so our modules win over any same-named installed packages.
# Only insert if not already present, to avoid duplicate entries on repeated invocations.
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
