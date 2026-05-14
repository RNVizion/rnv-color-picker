"""
Root-level conftest.py for RNV Color Picker.

Ensures pytest can resolve `core`, `ui`, and `utils` package imports from
test modules under tests/. When pytest collects tests from a subdirectory,
it doesn't automatically add the project root to sys.path — so test files
that do `from core.color_math import ColorMath` would fail with
ModuleNotFoundError.

This conftest.py runs before any test module is imported (pytest discovers
conftest.py files top-down, root first), so by the time the test files are
parsed, sys.path is already correctly configured.

This is a belt-and-suspenders fix: pytest.ini also sets `pythonpath = .`
for the same purpose. Either mechanism alone is sufficient; having both
guarantees correct import resolution regardless of how pytest is invoked
or which working directory it's launched from.
"""

import sys
from pathlib import Path

# Add the project root (the directory containing this file) to sys.path
# at the front, so `import core`, `import ui`, `import utils` resolve to
# the local package directories.
_PROJECT_ROOT = Path(__file__).parent.resolve()

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
