"""
Shared pytest fixtures and bootstrap for RNV Color Picker tests.

This file is auto-loaded by pytest before any test runs. It mirrors the
bootstrap logic in test_rnv_color_picker.py so the same project imports
(`from core.X import Y`) work in pytest-style tests too.
"""

import os
import sys
import types
from pathlib import Path

# Qt offscreen platform MUST be set before any QApplication is constructed.
# pytest-qt creates the QApplication automatically on first qtbot use, so
# setting it here at module-import time guarantees it's in place.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Project root — this file lives at <repo>/tests/conftest.py, so the project
# root is two parents up (not one). The earlier bug was `.parent` instead of
# `.parent.parent`, which resolved to <repo>/tests/ and caused all imports
# of `from core.X import Y` to fail in pytest-collected tests.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT_STR = str(_PROJECT_ROOT)

if _PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT_STR)

# Detect production subdir layout (core/, utils/, ui/) vs. flat layout
# (everything in one folder). Production is the subdir layout — flat is
# used only by the sandbox snapshot. Both must work so tests behave
# identically in either environment.
_SUBDIR_LAYOUT = (_PROJECT_ROOT / "core").is_dir()

if not _SUBDIR_LAYOUT:
    # Flat layout — register virtual core/utils/ui packages whose __path__
    # points at the project root. Python's import machinery then resolves
    # `from core.color_math` by looking for color_math.py in the root.
    for _pkg in ("core", "utils", "ui"):
        if _pkg not in sys.modules:
            _m = types.ModuleType(_pkg)
            _m.__path__ = [_PROJECT_ROOT_STR]
            _m.__package__ = _pkg
            sys.modules[_pkg] = _m


# ─────────────────────────────────────────────────────────────────────
# Global ColorHistoryManager safety patch — same as in test_rnv_color_picker.py
# Prevents tests from writing to the real AppData/Library/.config history file.
# Applied at module-import time so it's in effect before any test runs.
# ─────────────────────────────────────────────────────────────────────
import tempfile  # noqa: E402  (intentional: must come after sys.path mutation)

_HIST_TMP = tempfile.mkdtemp()
_HIST_SAFE = Path(_HIST_TMP) / "test_history.json"

try:
    from core.color_history import ColorHistoryManager

    ColorHistoryManager.load_history = lambda self: None

    def _safe_setup(self):
        self.history_file = _HIST_SAFE

    ColorHistoryManager._setup_history_path = _safe_setup

    def _safe_init(self):
        self.history = []
        self.history_file = _HIST_SAFE

    ColorHistoryManager.__init__ = _safe_init
except Exception:
    # If the import fails, leave the class alone — individual test files
    # can still import and patch as needed.
    pass
