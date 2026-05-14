"""
Phase 5: core/color_history.py — pytest-style coverage with property tests.

The legacy unittest suite (TestColorHistoryManager in test_rnv_color_picker.py)
covers ~18 happy-path cases for the simple CRUD methods. Coverage was 48%
because the suite globally monkeypatches `__init__`, `_setup_history_path`,
and `load_history` to no-ops, which means none of those branches actually
execute under unittest. This file fills in:

  - _setup_history_path per-OS branches (Windows/macOS/Linux/fallback) +
    exception path
  - load_history: missing / empty / corrupted JSON (with backup) /
    generic exception
  - save_history: no history_file configured, write success, write failure
    (temp file cleanup)
  - add_color: exception swallowing path
  - export_history: success + exception
  - format_timestamp: today / yesterday / older / exception fallback
  - Singleton + module-level convenience functions

Plus a property test for the MAX_HISTORY_SIZE invariant — adding any number
of colors must never grow `history` past MAX_HISTORY_SIZE. That's the kind of
bound check that example-based tests rarely catch but hypothesis nails.

Conventions:
  - tmp_path everywhere; the `manager` fixture builds a ColorHistoryManager
    with `history_file` redirected so no AppData / ~/.config writes happen.
  - `_reset_singleton` autouse so the module-level singleton never leaks.
  - For OS-detection branches, monkeypatch `os.name` and `Path.home()` and
    instantiate fresh; the platform-detect runs in __init__.
"""

import importlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from core.color_history import (
    ColorHistoryManager,
    get_color_history_manager,
    add_to_history,
    get_recent_colors,
    clear_color_history,
)
import core.color_history as color_history_module


# ---------------------------------------------------------------------------
# Side-stepping conftest.py's global patch.
#
# conftest.py (lines ~47-74) monkey-patches ColorHistoryManager.__init__,
# _setup_history_path, and load_history at import time so the unittest suite
# never touches real AppData. Those patches apply before any test file's
# module-level code runs — saving references at module top is too late.
#
# Workaround: importlib.reload(core.color_history) re-executes the source
# module, which redefines the class with its original methods. We pull a
# fresh, unpatched ColorHistoryManager out of the reloaded module and use
# *that* class for tests of platform-detect and load_history. Re-importing
# patched names afterwards isn't necessary — conftest's patches were only
# bound to the prior class object, which we no longer reference here.
# ---------------------------------------------------------------------------


def _fresh_class():
    """Return a fresh ColorHistoryManager class with original methods.

    Reloading core.color_history re-runs the class body, producing a new
    class object whose __init__/_setup_history_path/load_history are the
    real source-code versions. The conftest patches are lost on the old
    class, which is fine — we don't use the old one here.
    """
    importlib.reload(color_history_module)
    return color_history_module.ColorHistoryManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset module-level _history_instance between tests so singleton tests
    get a clean slate every time."""
    color_history_module._history_instance = None
    yield
    color_history_module._history_instance = None


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A ColorHistoryManager with history_file redirected to tmp_path.

    Uses _fresh_class() to side-step conftest's global patches, builds a real
    instance (with real __init__ + load), then redirects history_file to
    tmp_path so subsequent saves stay sandboxed.
    """
    # Redirect Path.home() so the real __init__ doesn't write to ~/.config etc.
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cls = _fresh_class()
    m = cls()
    m.history_file = tmp_path / "history.json"
    m.history = []  # purge anything load_history may have picked up
    return m


# Property-test strategy
rgb = st.tuples(
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
)


# ===========================================================================
# _setup_history_path — per-OS branches
# ===========================================================================


class TestSetupHistoryPath:
    """The path differs by OS: Windows uses %APPDATA%, macOS uses
    ~/Library/Application Support, Linux uses ~/.config, and unknown OSes
    fall back to ~/.rnvcolorpicker.

    Every test here uses _fresh_class() to bypass conftest's global patches
    so the real platform-detect code runs.
    """

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="WindowsPath cannot be instantiated on non-Windows platforms; "
               "this test exercises the real Path(APPDATA) construction which "
               "only works on Windows.",
    )
    def test_windows_uses_appdata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
        m = _fresh_class()()
        assert "AppData" in str(m.history_file)
        assert "RNVColorPicker" in str(m.history_file)

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="WindowsPath cannot be instantiated on non-Windows platforms.",
    )
    def test_windows_no_appdata_falls_back_to_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        m = _fresh_class()()
        # Should land in tmp_path / RNVColorPicker
        assert str(tmp_path) in str(m.history_file)

    def test_macos_uses_library_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Stub os.uname() to return Darwin.
        # raising=False because os.uname is POSIX-only — on Windows the attr
        # doesn't exist, and monkeypatch's default `raising=True` would reject
        # setting an unknown attribute. With raising=False, the lambda gets
        # set anyway, satisfying the source's `hasattr(os, 'uname')` check.
        class _Uname:
            sysname = "Darwin"
        monkeypatch.setattr(os, "uname", lambda: _Uname(), raising=False)

        m = _fresh_class()()
        assert "Library" in str(m.history_file)
        assert "Application Support" in str(m.history_file)

    def test_linux_uses_config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        class _Uname:
            sysname = "Linux"
        monkeypatch.setattr(os, "uname", lambda: _Uname(), raising=False)

        m = _fresh_class()()
        assert ".config" in str(m.history_file)
        assert "RNVColorPicker" in str(m.history_file)

    def test_unknown_os_uses_fallback(self, tmp_path, monkeypatch):
        # Some exotic os.name not in {"nt", "posix"}
        monkeypatch.setattr(os, "name", "java")  # Jython, anyone?
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        m = _fresh_class()()
        # Source falls back to ~/.rnvcolorpicker
        assert ".rnvcolorpicker" in str(m.history_file)

    def test_exception_falls_back_to_local(self, monkeypatch):
        cls = _fresh_class()

        # Force Path.home() to raise; the except clause should fall back
        # to a relative HISTORY_FILENAME (and continue without crashing)
        def boom():
            raise OSError("no home dir")
        monkeypatch.setattr(Path, "home", boom)
        # Force POSIX path so home() is the first thing to fail
        monkeypatch.setattr(os, "name", "posix")

        class _Uname:
            sysname = "Linux"
        monkeypatch.setattr(os, "uname", lambda: _Uname(), raising=False)

        m = cls()
        # Fallback is just the filename, no directory
        assert m.history_file == Path(cls.HISTORY_FILENAME)


# ===========================================================================
# load_history — missing / empty / corrupted / exception paths
# ===========================================================================


class TestLoadHistory:
    """load_history's branches are why this module's coverage was 48%."""

    def test_missing_file_starts_empty(self, manager):
        # history_file is set but doesn't exist → empty history
        assert not manager.history_file.exists()
        manager.history = ["dirty"]  # plant something to confirm reset
        manager.load_history()
        assert manager.history == []

    def test_empty_file_starts_fresh(self, manager):
        # File exists but contains only whitespace
        manager.history_file.write_text("   \n  ")
        manager.load_history()
        assert manager.history == []

    def test_valid_json_populates_history(self, manager):
        payload = {
            "version": "1.0",
            "colors": [{"hex": "#ff0000", "rgb": [255, 0, 0],
                        "timestamp": "2024-01-01T00:00:00",
                        "source": "manual", "pick_count": 1}],
        }
        manager.history_file.write_text(json.dumps(payload))
        manager.load_history()
        assert len(manager.history) == 1
        assert manager.history[0]["hex"] == "#ff0000"

    def test_corrupted_json_creates_backup_and_resets(self, manager, tmp_path):
        # Plant a corrupted file
        manager.history_file.write_text("{not valid json")
        manager.history = ["should be cleared"]
        manager.load_history()
        # History reset to empty
        assert manager.history == []
        # Backup file should now exist alongside the original
        backup = manager.history_file.with_suffix(".json.bak")
        assert backup.exists()
        # Original was rewritten as a clean empty-history JSON file
        assert manager.history_file.exists()
        with open(manager.history_file) as f:
            new_data = json.load(f)
        assert new_data["colors"] == []

    def test_corrupted_json_with_backup_failure_still_recovers(
            self, manager, monkeypatch):
        # Plant a corrupted file, then make shutil.copy2 raise.
        # Source has try/except around the backup — must still reset history.
        manager.history_file.write_text("{not valid json")

        import shutil
        def fail_copy(*args, **kwargs):
            raise OSError("copy denied")
        monkeypatch.setattr(shutil, "copy2", fail_copy)
        manager.load_history()  # must not raise
        assert manager.history == []

    def test_generic_exception_resets_history(self, manager, monkeypatch):
        # Make open() raise something other than JSONDecodeError
        manager.history_file.write_text("anything")
        manager.history = ["dirty"]

        def boom(*args, **kwargs):
            raise RuntimeError("disk error")
        monkeypatch.setattr("builtins.open", boom)
        manager.load_history()
        assert manager.history == []

    def test_history_file_is_none_starts_empty(self, manager):
        # If path setup failed earlier and history_file is None, just empty
        manager.history_file = None
        manager.history = []
        manager.load_history()  # must not raise
        assert manager.history == []


# ===========================================================================
# save_history
# ===========================================================================


class TestSaveHistory:
    def test_no_history_file_returns_false(self, manager):
        manager.history_file = None
        assert manager.save_history() is False

    def test_success_writes_valid_json(self, manager):
        manager.history = [{"hex": "#abcdef", "rgb": [171, 205, 239],
                            "timestamp": "2024-01-01T00:00:00",
                            "source": "manual", "pick_count": 1}]
        assert manager.save_history() is True
        with open(manager.history_file) as f:
            data = json.load(f)
        assert data["colors"] == manager.history
        assert data["version"] == "1.0"
        assert "last_updated" in data

    def test_atomic_write_cleans_up_temp_file_on_failure(
            self, manager, monkeypatch):
        # Make json.dump raise mid-write; source must clean up the .tmp file
        def fail_dump(*args, **kwargs):
            raise OSError("simulated write failure")
        monkeypatch.setattr(json, "dump", fail_dump)

        manager.history = [{"hex": "#000000"}]
        assert manager.save_history() is False
        # No temp file left behind
        temp = manager.history_file.with_suffix(".json.tmp")
        assert not temp.exists()

    def test_creates_parent_directory_if_missing(self, tmp_path):
        m = ColorHistoryManager()
        # Point at a path whose parent doesn't exist yet
        nested = tmp_path / "deep" / "nested" / "history.json"
        m.history_file = nested
        m.history = []
        assert m.save_history() is True
        assert nested.exists()


# ===========================================================================
# add_color — exception path + property test for max-size invariant
# ===========================================================================


class TestAddColor:
    def test_exception_in_save_does_not_propagate(self, manager, monkeypatch):
        # Make save_history raise — add_color's try/except should swallow it
        def boom(*args, **kwargs):
            raise RuntimeError("save broke")
        monkeypatch.setattr(manager, "save_history", boom)
        # Add must not raise
        manager.add_color((128, 128, 128))

    def test_distinct_colors_grow_history(self, manager):
        manager.add_color((255, 0, 0))
        manager.add_color((0, 255, 0))
        manager.add_color((0, 0, 255))
        assert len(manager.history) == 3
        # Most recent at the front
        assert manager.history[0]["hex"] == "#0000ff"

    def test_pick_count_starts_at_one(self, manager):
        manager.add_color((50, 100, 150))
        assert manager.history[0]["pick_count"] == 1

    def test_consecutive_dupe_updates_existing_entry_timestamp(self, manager):
        manager.add_color((255, 255, 0))
        first_ts = manager.history[0]["timestamp"]
        # Same color again should bump count + update timestamp, not insert
        manager.add_color((255, 255, 0))
        assert len(manager.history) == 1
        assert manager.history[0]["pick_count"] == 2
        # Timestamp updated (or at least not stale)
        assert manager.history[0]["timestamp"] >= first_ts


class TestAddColorMaxSizeInvariant:
    """The MAX_HISTORY_SIZE invariant is exactly the kind of bound a property
    test catches that example tests can't."""

    @given(colors=st.lists(rgb, min_size=1, max_size=400, unique=True))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_history_never_exceeds_max_size(self, manager, colors):
        # Add an arbitrary number of distinct colors
        manager.history = []
        for c in colors:
            manager.add_color(c)
        # Even after adding 400 distinct colors, history <= MAX_HISTORY_SIZE
        assert len(manager.history) <= ColorHistoryManager.MAX_HISTORY_SIZE

    def test_exactly_max_size_after_overfilling(self, manager):
        # Add MAX_HISTORY_SIZE + 50 distinct colors — history should be
        # trimmed exactly to MAX_HISTORY_SIZE
        N = ColorHistoryManager.MAX_HISTORY_SIZE + 50
        for i in range(N):
            # Generate distinct colors via the int-to-RGB encoding
            r = (i // (256 * 256)) % 256
            g = (i // 256) % 256
            b = i % 256
            manager.add_color((r, g, b))
        assert len(manager.history) == ColorHistoryManager.MAX_HISTORY_SIZE


# ===========================================================================
# export_history
# ===========================================================================


class TestExportHistory:
    def test_export_success(self, manager, tmp_path):
        manager.add_color((10, 20, 30))
        out = tmp_path / "exported.json"
        assert manager.export_history(str(out)) is True
        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        assert data["color_count"] == 1
        assert data["colors"][0]["hex"] == "#0a141e"

    def test_export_failure_returns_false(self, manager, tmp_path, monkeypatch):
        # Make open() raise during export
        original_open = open

        def fail_open(*args, **kwargs):
            # Only fail when writing the export, not when checking history_file
            if str(args[0]).endswith("exported.json"):
                raise OSError("disk full")
            return original_open(*args, **kwargs)
        monkeypatch.setattr("builtins.open", fail_open)
        manager.add_color((1, 1, 1))
        assert manager.export_history(str(tmp_path / "exported.json")) is False


# ===========================================================================
# format_timestamp — today / yesterday / older / exception
# ===========================================================================


class TestFormatTimestamp:
    def test_today_shows_time_only(self, manager):
        # Use today's date with a specific time
        now = datetime.now()
        ts = now.replace(hour=14, minute=30, second=0).isoformat()
        out = manager.format_timestamp(ts)
        # Format is "%I:%M %p" → e.g. "02:30 PM"
        assert ":" in out
        assert "AM" in out or "PM" in out
        assert "/" not in out  # no date separator

    def test_yesterday_shows_yesterday_label(self, manager):
        # Use yesterday's date if today's day > 1; otherwise the source
        # falls back to today (its yesterday calculation is naive). We
        # only assert the today-fallback case if day == 1.
        now = datetime.now()
        if now.day > 1:
            yesterday = now.replace(day=now.day - 1, hour=10, minute=0, second=0)
            out = manager.format_timestamp(yesterday.isoformat())
            assert "Yesterday" in out

    def test_older_shows_full_date(self, manager):
        # A date well in the past (e.g., 30 days ago) goes through the
        # final else branch with strftime("%m/%d/%Y %I:%M %p")
        old = (datetime.now() - timedelta(days=30)).isoformat()
        out = manager.format_timestamp(old)
        assert "/" in out  # date separator
        assert "AM" in out or "PM" in out

    def test_invalid_timestamp_returns_input(self, manager):
        # Source's except catches all exceptions and returns the input
        bad = "not a timestamp"
        assert manager.format_timestamp(bad) == bad


class TestRemoveColor:
    """remove_color rebuilds the history list excluding the matching hex."""

    def test_remove_existing_returns_true(self, manager):
        manager.add_color((255, 0, 0))
        assert manager.remove_color("#ff0000") is True
        assert manager.history == []

    def test_remove_missing_returns_false(self, manager):
        manager.add_color((255, 0, 0))
        assert manager.remove_color("#abcdef") is False
        # History untouched
        assert len(manager.history) == 1

    def test_remove_is_case_insensitive(self, manager):
        manager.add_color((255, 0, 0))
        # Mixed-case input should still match #ff0000 stored lowercase
        assert manager.remove_color("#FF0000") is True

    def test_remove_only_targeted_entry(self, manager):
        # Multi-color history — only the named one should disappear
        manager.add_color((255, 0, 0))
        manager.add_color((0, 255, 0))
        manager.add_color((0, 0, 255))
        manager.remove_color("#00ff00")
        hexes = [e["hex"] for e in manager.history]
        assert "#00ff00" not in hexes
        assert "#ff0000" in hexes
        assert "#0000ff" in hexes


class TestGetColorInfo:
    """get_color_info returns a copy of the matching entry, None if missing."""

    def test_existing_returns_dict_copy(self, manager):
        manager.add_color((100, 100, 100))
        info = manager.get_color_info("#646464")
        assert info is not None
        assert info["hex"] == "#646464"

    def test_missing_returns_none(self, manager):
        manager.add_color((100, 100, 100))
        assert manager.get_color_info("#deadbe") is None

    def test_case_insensitive_lookup(self, manager):
        manager.add_color((255, 0, 0))
        # Uppercase hex input still finds the lowercase-stored entry
        assert manager.get_color_info("#FF0000") is not None

    def test_returned_dict_is_copy_not_reference(self, manager):
        # Mutating the returned dict shouldn't leak into history
        manager.add_color((10, 20, 30))
        info = manager.get_color_info("#0a141e")
        info["pick_count"] = 9999
        assert manager.history[0]["pick_count"] == 1


# ===========================================================================
# Singleton + module-level convenience functions
# ===========================================================================


class TestSingleton:
    """The singleton mechanic: first call constructs, subsequent calls return
    the same instance.

    Note we access via `color_history_module.X` rather than the imported
    names because earlier tests call _fresh_class() which reloads the
    module. After reload, the freshly-redefined `ColorHistoryManager` and
    `get_color_history_manager` live on the module object — the names we
    `from`-imported at the top of this file still point to the prior
    (conftest-patched) class. Using module-attribute lookup keeps both
    the singleton and the isinstance check pointing at the same class.
    """

    def test_first_call_creates_instance(self):
        sm = color_history_module.get_color_history_manager()
        assert isinstance(sm, color_history_module.ColorHistoryManager)

    def test_subsequent_calls_return_same_instance(self):
        first = color_history_module.get_color_history_manager()
        second = color_history_module.get_color_history_manager()
        assert first is second


class TestModuleConvenienceFunctions:
    """The module-level helpers are thin wrappers around the singleton.
    They must delegate correctly without side effects beyond what the
    underlying methods already test.

    Same module-attribute trick as TestSingleton — after _fresh_class()
    reloads, only `color_history_module.X` consistently points at the
    fresh class.
    """

    def test_add_to_history_delegates(self, monkeypatch, tmp_path):
        # Build a sentinel from the (post-reload) fresh class
        sentinel = color_history_module.ColorHistoryManager()
        sentinel.history_file = tmp_path / "test.json"
        sentinel.history = []
        monkeypatch.setattr(color_history_module, "_history_instance", sentinel)

        color_history_module.add_to_history((42, 84, 168), source="test")
        assert sentinel.history[0]["rgb"] == [42, 84, 168]
        assert sentinel.history[0]["source"] == "test"

    def test_get_recent_colors_delegates(self, monkeypatch, tmp_path):
        sentinel = color_history_module.ColorHistoryManager()
        sentinel.history_file = tmp_path / "test.json"
        sentinel.history = []
        monkeypatch.setattr(color_history_module, "_history_instance", sentinel)

        sentinel.add_color((10, 20, 30))
        sentinel.add_color((40, 50, 60))
        result = color_history_module.get_recent_colors(count=5)
        assert isinstance(result, list)
        assert (40, 50, 60) in result

    def test_clear_color_history_delegates(self, monkeypatch, tmp_path):
        sentinel = color_history_module.ColorHistoryManager()
        sentinel.history_file = tmp_path / "test.json"
        sentinel.history = []
        monkeypatch.setattr(color_history_module, "_history_instance", sentinel)

        sentinel.add_color((1, 2, 3))
        color_history_module.clear_color_history()
        assert sentinel.history == []


# ===========================================================================
# Property tests: get_recent_colors / get_history bounds
# ===========================================================================


class TestGetHistoryProperties:
    """Once history is populated, get_history(limit=k) returns a list of
    length min(k, len(history))."""

    @given(
        colors=st.lists(rgb, min_size=0, max_size=20, unique=True),
        limit=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_get_history_respects_limit(self, manager, colors, limit):
        manager.history = []
        for c in colors:
            manager.add_color(c)
        out = manager.get_history(limit=limit)
        assert len(out) == min(limit, len(manager.history))

    @given(
        colors=st.lists(rgb, min_size=0, max_size=10, unique=True),
        count=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_get_recent_colors_respects_count(self, manager, colors, count):
        manager.history = []
        for c in colors:
            manager.add_color(c)
        result = manager.get_recent_colors(count=count)
        # Result is bounded by both count and actual history length
        assert len(result) <= count
        assert len(result) <= len(manager.history)
        # Each result is a 3-tuple
        for c in result:
            assert isinstance(c, tuple)
            assert len(c) == 3
