"""
Phase 3-aux-5: utils/session_manager.py — pytest-style coverage.

Targets the ~62% of session_manager.py left uncovered by the legacy
unittest suite (TestSessionManager in test_rnv_color_picker.py). The
unittest cases pin down save/load/delete happy paths; this file fills in:

  - save_session edge cases (dict-with-"colors", name sanitization, exception)
  - load_session search-by-name-via-recent, version mismatch, JSONDecodeError
  - get_recent_sessions empty/populated/corrupted/exception branches
  - _add_to_recent / _remove_from_recent dedup + max-trim + exception paths
  - delete_session search-by-name + exception handling
  - generate_session_filename timestamp default + collision suffix
  - All autosave plumbing: start/stop, shutdown, _autosave, check, delete,
    set_interval, list_autosaves, cleanup_old_autosaves (~140 lines)
  - Singleton getter + module-level convenience functions

Conventions:
  - tmp_path used everywhere for FS isolation (no ~/.rnv_color_picker writes)
  - autouse `_reset_singleton` so cross-test pollution can't leak via
    get_session_manager()'s module global
  - QTimer paths exercised with a stub class to avoid real timers firing
    during tests; the tests assert the wiring, not actual scheduling
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from utils.session_manager import (
    SessionManager,
    get_session_manager,
    save_session as module_save_session,
    load_session as module_load_session,
)
import utils.session_manager as session_manager_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset module-level _session_instance between tests so the singleton
    helper tests get a clean slate every time."""
    session_manager_module._session_instance = None
    yield
    session_manager_module._session_instance = None


@pytest.fixture
def sm(tmp_path):
    """A SessionManager with sessions_dir pinned to a temp directory.

    All filesystem effects of save/load/delete/etc. land in tmp_path,
    which pytest cleans up automatically.
    """
    return SessionManager(sessions_dir=str(tmp_path))


def _slots():
    """Two-color payload used as colors_data in most save tests."""
    return [
        {"rgb": [255, 0, 0], "hsl": [0, 100, 50],   "hilbert_idx": 1, "is_locked": False},
        {"rgb": [0, 255, 0], "hsl": [120, 100, 50], "hilbert_idx": 2, "is_locked": True},
    ]


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestInit:
    """Constructor sets up sessions_dir, autosave bookkeeping, and session ID."""

    def test_explicit_sessions_dir_used(self, tmp_path):
        sm = SessionManager(sessions_dir=str(tmp_path))
        assert sm.sessions_dir == tmp_path

    def test_creates_sessions_dir_if_missing(self, tmp_path):
        new_dir = tmp_path / "nonexistent" / "nested"
        assert not new_dir.exists()
        SessionManager(sessions_dir=str(new_dir))
        assert new_dir.exists()

    def test_default_sessions_dir_uses_home(self, monkeypatch, tmp_path):
        # Force Path.home() to return tmp_path so we don't pollute real ~
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        sm = SessionManager()  # no sessions_dir
        assert sm.sessions_dir == tmp_path / ".rnv_color_picker" / "sessions"
        assert sm.sessions_dir.exists()

    def test_recent_file_path_set(self, sm, tmp_path):
        assert sm.recent_file == tmp_path / ".recent_sessions.json"

    def test_autosave_enabled_default_true(self, sm):
        assert sm.autosave_enabled is True

    def test_autosave_interval_matches_class_default(self, sm):
        assert sm.autosave_interval == SessionManager.AUTOSAVE_INTERVAL

    def test_autosave_timer_starts_none(self, sm):
        assert sm.autosave_timer is None

    def test_main_app_starts_none(self, sm):
        assert sm.main_app is None

    def test_session_id_is_timestamp_string(self, sm):
        # YYYYMMDD_HHMMSS = 15 chars including underscore
        assert len(sm._session_id) == 15
        assert sm._session_id[8] == "_"

    def test_autosave_filename_uses_session_id(self, sm):
        expected_prefix = SessionManager.AUTOSAVE_PREFIX + sm._session_id
        assert sm._autosave_filename.startswith(expected_prefix)
        assert sm._autosave_filename.endswith(SessionManager.SESSION_EXTENSION)

    def test_autosave_path_under_sessions_dir(self, sm, tmp_path):
        assert sm.autosave_path == tmp_path / sm._autosave_filename


# ---------------------------------------------------------------------------
# save_session — edge cases beyond the unittest happy paths
# ---------------------------------------------------------------------------


class TestSaveSession:
    """Cover the save_session branches the legacy unittest suite skips."""

    def test_colors_data_as_dict_with_colors_key(self, sm, tmp_path):
        # When colors_data is a {"colors": [...]} dict, the inner list is used
        payload = {"colors": _slots(), "extra": "ignored"}
        fp = str(tmp_path / "from_dict")
        assert sm.save_session(fp, payload) is True
        loaded = sm.load_session(fp + SessionManager.SESSION_EXTENSION)
        assert loaded is not None
        assert len(loaded["colors"]) == 2

    def test_name_only_generates_filepath_in_sessions_dir(self, sm, tmp_path):
        # No path separators and no extension → treated as a session name
        assert sm.save_session("MySession", _slots()) is True
        expected = tmp_path / ("MySession" + SessionManager.SESSION_EXTENSION)
        assert expected.exists()

    def test_name_with_special_chars_sanitized(self, sm, tmp_path):
        # Only alnum, space, dash, underscore are kept; "/" and "$" stripped
        assert sm.save_session("Bad@Name$2024", _slots()) is True
        expected = tmp_path / ("BadName2024" + SessionManager.SESSION_EXTENSION)
        assert expected.exists()

    def test_appends_extension_when_missing(self, sm, tmp_path):
        # filepath with separator but no extension → extension appended
        fp = str(tmp_path / "no_extension_here")
        assert sm.save_session(fp, _slots()) is True
        assert (tmp_path / "no_extension_here.cpksession").exists()

    def test_preserves_extension_when_present(self, sm, tmp_path):
        fp = str(tmp_path / "already_has.cpksession")
        assert sm.save_session(fp, _slots()) is True
        # Should not double the extension
        assert (tmp_path / "already_has.cpksession").exists()
        assert not (tmp_path / "already_has.cpksession.cpksession").exists()

    def test_name_derived_from_filename_when_not_provided(self, sm, tmp_path):
        fp = str(tmp_path / "auto_named")
        sm.save_session(fp, _slots())
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["name"] == "auto_named"

    def test_metadata_color_count_set(self, sm, tmp_path):
        fp = str(tmp_path / "with_count")
        sm.save_session(fp, _slots())
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["metadata"]["color_count"] == 2

    def test_metadata_has_image_true_when_image_path_given(self, sm, tmp_path):
        fp = str(tmp_path / "with_img")
        sm.save_session(fp, _slots(), image_path="/foo/bar.png")
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["metadata"]["has_image"] is True

    def test_metadata_has_image_false_when_image_path_none(self, sm, tmp_path):
        fp = str(tmp_path / "no_img")
        sm.save_session(fp, _slots())
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["metadata"]["has_image"] is False

    def test_settings_default_to_empty_dict(self, sm, tmp_path):
        fp = str(tmp_path / "no_settings")
        sm.save_session(fp, _slots())
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["settings"] == {}

    def test_settings_passed_through(self, sm, tmp_path):
        fp = str(tmp_path / "with_settings")
        sm.save_session(fp, _slots(), settings={"theme": "Dark", "max": 50})
        loaded = sm.load_session(fp + ".cpksession")
        assert loaded["settings"] == {"theme": "Dark", "max": 50}

    def test_returns_false_on_write_failure(self, sm, tmp_path, monkeypatch):
        # Force open() to raise to exercise the except path
        def fail_open(*args, **kwargs):
            raise OSError("disk full")
        monkeypatch.setattr("builtins.open", fail_open)
        assert sm.save_session(str(tmp_path / "boom"), _slots()) is False

    def test_save_adds_to_recent(self, sm, tmp_path):
        fp = str(tmp_path / "recent_test")
        sm.save_session(fp, _slots())
        recent = sm.get_recent_sessions()
        assert any(r["filepath"].endswith("recent_test.cpksession") for r in recent)


# ---------------------------------------------------------------------------
# load_session — name search, version mismatch, error branches
# ---------------------------------------------------------------------------


class TestLoadSession:
    """load_session has two name-based search paths and three exception paths."""

    def test_load_by_name_via_sessions_dir(self, sm, tmp_path):
        # Save with a path, then load by bare name (resolved against sessions_dir)
        sm.save_session("ByName", _slots())
        loaded = sm.load_session("ByName")
        assert loaded is not None
        assert loaded["name"] == "ByName"

    def test_load_by_name_via_recent_sessions_search(self, sm, tmp_path):
        # Save a file under one path, but request load by the session's stored "name"
        # field — which falls through to the recent-sessions search loop.
        actual_path = tmp_path / "weird_filename.cpksession"
        sm.save_session(str(actual_path).replace(".cpksession", ""),
                        _slots(), name="MyDisplayName")
        # The bare name "MyDisplayName" will not exist as MyDisplayName.cpksession
        # in sessions_dir, so the loop walks recent and matches by name
        loaded = sm.load_session("MyDisplayName")
        assert loaded is not None
        assert loaded["name"] == "MyDisplayName"

    def test_load_returns_none_when_truly_missing(self, sm):
        # Name has no separator AND no matching file in dir AND not in recent
        assert sm.load_session("NopeNotHere") is None

    def test_load_logs_version_mismatch(self, sm, tmp_path):
        # Hand-craft a session file with a wrong version; load should still
        # return data (just log a warning)
        bad = tmp_path / "old.cpksession"
        with open(bad, "w") as f:
            json.dump({
                "version": "0.5",
                "name": "old",
                "colors": [],
                "metadata": {"color_count": 0, "has_image": False},
            }, f)
        loaded = sm.load_session(str(bad))
        assert loaded is not None
        assert loaded["version"] == "0.5"

    def test_load_returns_none_on_invalid_json(self, sm, tmp_path):
        bad = tmp_path / "broken.cpksession"
        bad.write_text("{not json")
        assert sm.load_session(str(bad)) is None

    def test_load_returns_none_on_generic_exception(self, sm, tmp_path, monkeypatch):
        # Make json.load raise a non-decode exception
        def fail_load(*args, **kwargs):
            raise RuntimeError("simulated")
        good = tmp_path / "good.cpksession"
        good.write_text("{}")
        monkeypatch.setattr(json, "load", fail_load)
        assert sm.load_session(str(good)) is None

    def test_load_updates_modified_timestamp(self, sm, tmp_path):
        fp = str(tmp_path / "mod_test")
        sm.save_session(fp, _slots())
        loaded = sm.load_session(fp + ".cpksession")
        # 'modified' should be an ISO-format string from datetime.now()
        assert "T" in loaded["modified"]


# ---------------------------------------------------------------------------
# get_recent_sessions
# ---------------------------------------------------------------------------


class TestGetRecentSessions:
    def test_empty_when_recent_file_missing(self, sm):
        # Fresh SessionManager has no .recent_sessions.json yet
        assert sm.get_recent_sessions() == []

    def test_populated_after_save(self, sm, tmp_path):
        sm.save_session(str(tmp_path / "a"), _slots())
        sm.save_session(str(tmp_path / "b"), _slots())
        recent = sm.get_recent_sessions()
        assert len(recent) == 2

    def test_skips_deleted_files(self, sm, tmp_path):
        # Save → manually delete the file → list should skip it
        sm.save_session(str(tmp_path / "ghost"), _slots())
        ghost = tmp_path / "ghost.cpksession"
        ghost.unlink()
        recent = sm.get_recent_sessions()
        assert all(not r["filepath"].endswith("ghost.cpksession") for r in recent)

    def test_skips_corrupted_session_files(self, sm, tmp_path):
        # Plant a path in recent that points to a corrupted .cpksession
        good = tmp_path / "good.cpksession"
        bad = tmp_path / "bad.cpksession"
        good.write_text(json.dumps({"version": "1.0", "name": "g", "colors": [],
                                    "metadata": {}, "modified": ""}))
        bad.write_text("{not json")
        # Manually populate the recent file
        sm.recent_file.write_text(json.dumps([str(good), str(bad)]))
        recent = sm.get_recent_sessions()
        names = [r["name"] for r in recent]
        assert "g" in names
        assert len(recent) == 1  # bad one skipped

    def test_returns_empty_list_on_outer_exception(self, sm, monkeypatch):
        # Force the recent_file.exists() check to raise
        class Boom:
            def exists(self_inner):
                raise RuntimeError("cannot stat")
        sm.recent_file = Boom()
        assert sm.get_recent_sessions() == []

    def test_session_info_includes_expected_keys(self, sm, tmp_path):
        sm.save_session(str(tmp_path / "info_test"), _slots(),
                        description="test desc")
        recent = sm.get_recent_sessions()
        assert recent
        for key in ("filepath", "name", "modified", "color_count", "description"):
            assert key in recent[0]

    def test_color_count_reflects_session_data(self, sm, tmp_path):
        sm.save_session(str(tmp_path / "count"), _slots())
        recent = sm.get_recent_sessions()
        assert recent[0]["color_count"] == 2


# ---------------------------------------------------------------------------
# list_sessions — alias for get_recent_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_alias_returns_same_as_get_recent_sessions(self, sm, tmp_path):
        sm.save_session(str(tmp_path / "x"), _slots())
        assert sm.list_sessions() == sm.get_recent_sessions()


# ---------------------------------------------------------------------------
# _add_to_recent / _remove_from_recent — internals
# ---------------------------------------------------------------------------


class TestAddToRecent:
    def test_first_add_creates_recent_file(self, sm, tmp_path):
        assert not sm.recent_file.exists()
        sm._add_to_recent(str(tmp_path / "a.cpksession"))
        assert sm.recent_file.exists()

    def test_dedups_and_promotes_to_front(self, sm, tmp_path):
        a, b = str(tmp_path / "a.cpksession"), str(tmp_path / "b.cpksession")
        sm._add_to_recent(a)
        sm._add_to_recent(b)
        sm._add_to_recent(a)  # re-add a → should move to front, not duplicate
        with open(sm.recent_file) as f:
            entries = json.load(f)
        assert entries[0] == a
        assert entries.count(a) == 1

    def test_trims_to_max_recent(self, sm, tmp_path):
        # Add 12 entries; only MAX_RECENT_SESSIONS (10) should survive
        for i in range(12):
            sm._add_to_recent(str(tmp_path / f"s{i}.cpksession"))
        with open(sm.recent_file) as f:
            entries = json.load(f)
        assert len(entries) == SessionManager.MAX_RECENT_SESSIONS

    def test_swallows_exception_silently(self, sm, monkeypatch):
        # Force open() to raise — _add_to_recent must not propagate
        def fail_open(*args, **kwargs):
            raise OSError("nope")
        monkeypatch.setattr("builtins.open", fail_open)
        # Should not raise; we rely on the try/except in source
        sm._add_to_recent("/anything")


class TestRemoveFromRecent:
    def test_no_file_no_op(self, sm):
        # No recent file → returns silently
        assert not sm.recent_file.exists()
        sm._remove_from_recent("/anything.cpksession")  # must not raise

    def test_removes_known_entry(self, sm, tmp_path):
        a = str(tmp_path / "a.cpksession")
        sm._add_to_recent(a)
        sm._remove_from_recent(a)
        with open(sm.recent_file) as f:
            entries = json.load(f)
        assert a not in entries

    def test_unknown_entry_is_noop(self, sm, tmp_path):
        # File exists but the path isn't in the list — the conditional branch
        # should not write the file again, but mustn't crash
        a = str(tmp_path / "a.cpksession")
        sm._add_to_recent(a)
        sm._remove_from_recent(str(tmp_path / "different.cpksession"))
        with open(sm.recent_file) as f:
            entries = json.load(f)
        assert a in entries  # original still present

    def test_swallows_exception(self, sm, tmp_path, monkeypatch):
        # Plant a recent file, then break open()
        sm.recent_file.write_text(json.dumps(["/foo"]))
        original_open = open

        def fail_open(*args, **kwargs):
            raise OSError("denied")
        monkeypatch.setattr("builtins.open", fail_open)
        sm._remove_from_recent("/foo")  # must not raise


# ---------------------------------------------------------------------------
# delete_session — search-by-name + exception paths
# ---------------------------------------------------------------------------


class TestDeleteSession:
    def test_delete_by_name_via_sessions_dir(self, sm, tmp_path):
        sm.save_session("ToDelete", _slots())
        target = tmp_path / "ToDelete.cpksession"
        assert target.exists()
        assert sm.delete_session("ToDelete") is True
        assert not target.exists()

    def test_delete_by_name_via_recent_search(self, sm, tmp_path):
        # Save under a different filename but with a name field, then delete by name
        actual = tmp_path / "weird.cpksession"
        sm.save_session(str(actual).replace(".cpksession", ""),
                        _slots(), name="DisplayName")
        assert sm.delete_session("DisplayName") is True
        assert not actual.exists()

    def test_delete_unknown_name_returns_true_and_no_crash(self, sm):
        # Source returns True even when nothing was actually deleted (no file
        # found, but no exception either) — _remove_from_recent is still called
        assert sm.delete_session("Nonexistent") is True

    def test_delete_returns_false_on_exception(self, sm, monkeypatch):
        # Force os.remove to raise after we've located a real file
        def fail_remove(path):
            raise OSError("permission denied")
        # First save a real file
        sm.save_session("WillFail", _slots())
        monkeypatch.setattr(os, "remove", fail_remove)
        assert sm.delete_session("WillFail") is False


# ---------------------------------------------------------------------------
# generate_session_filename
# ---------------------------------------------------------------------------


class TestGenerateSessionFilename:
    def test_no_base_name_uses_timestamp(self, sm):
        fp = sm.generate_session_filename(None)
        # Default is "session_YYYYMMDD_HHMMSS.cpksession"
        name = Path(fp).stem
        assert name.startswith("session_")
        assert fp.endswith(SessionManager.SESSION_EXTENSION)

    def test_collision_appends_counter(self, sm, tmp_path):
        # Pre-create the file the function would normally pick
        first = tmp_path / "dup.cpksession"
        first.write_text("{}")
        fp = sm.generate_session_filename("dup")
        assert "dup_1" in fp

    def test_multiple_collisions_increment_counter(self, sm, tmp_path):
        # Pre-create dup, dup_1, dup_2 → next should be dup_3
        for name in ("dup.cpksession", "dup_1.cpksession", "dup_2.cpksession"):
            (tmp_path / name).write_text("{}")
        fp = sm.generate_session_filename("dup")
        assert "dup_3" in fp

    def test_special_chars_stripped(self, sm):
        fp = sm.generate_session_filename("my$file@name!")
        # Special chars removed; result should contain only alnum + _
        stem = Path(fp).stem
        assert "$" not in stem
        assert "@" not in stem
        assert "!" not in stem

    def test_spaces_replaced_with_underscores(self, sm):
        fp = sm.generate_session_filename("my session name")
        assert "my_session_name" in Path(fp).stem


# ---------------------------------------------------------------------------
# Auto-save: start / stop / shutdown / _autosave / check / delete / interval
# ---------------------------------------------------------------------------


class _StubTimer:
    """Stand-in for QTimer that records calls without actually scheduling."""

    instances = []

    def __init__(self):
        self._active = False
        self._interval = None
        self._connected_callback = None
        self.start_calls = 0
        self.stop_calls = 0
        type(self).instances.append(self)

        # Mimic QTimer.timeout.connect(...) interface
        class _Sig:
            def __init__(self_inner, parent):
                self_inner.parent = parent

            def connect(self_inner, cb):
                self_inner.parent._connected_callback = cb
        self.timeout = _Sig(self)

    def start(self, interval_ms):
        self._active = True
        self._interval = interval_ms
        self.start_calls += 1

    def stop(self):
        self._active = False
        self.stop_calls += 1

    def isActive(self):
        return self._active


@pytest.fixture
def stub_timer(monkeypatch):
    """Patch QTimer at the import site inside session_manager.start_autosave."""
    _StubTimer.instances = []
    monkeypatch.setattr("PyQt6.QtCore.QTimer", _StubTimer)
    return _StubTimer


class TestStartAutosave:
    def test_creates_timer_and_starts_it(self, sm, stub_timer):
        main_app = MagicMock()
        sm.start_autosave(main_app)
        assert sm.autosave_timer is not None
        assert sm.autosave_timer._active is True
        assert sm.autosave_timer.start_calls == 1

    def test_main_app_stored(self, sm, stub_timer):
        main_app = MagicMock()
        sm.start_autosave(main_app)
        assert sm.main_app is main_app

    def test_uses_configured_interval_in_ms(self, sm, stub_timer):
        sm.autosave_interval = 90  # seconds
        sm.start_autosave(MagicMock())
        # interval is multiplied by 1000 for QTimer
        assert sm.autosave_timer._interval == 90_000

    def test_callback_connected_to_autosave_method(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        assert sm.autosave_timer._connected_callback == sm._autosave

    def test_disabled_skips_timer_creation(self, sm, stub_timer):
        sm.autosave_enabled = False
        sm.start_autosave(MagicMock())
        # main_app is set unconditionally, but no timer is built
        assert sm.autosave_timer is None


class TestStopAutosave:
    def test_active_timer_is_stopped(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        assert sm.autosave_timer._active is True
        sm.stop_autosave()
        assert sm.autosave_timer._active is False

    def test_no_timer_no_op(self, sm):
        # Never started → no autosave_timer; stop must be safe
        assert sm.autosave_timer is None
        sm.stop_autosave()  # must not raise

    def test_inactive_timer_no_op(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        sm.autosave_timer.stop()
        # Calling stop again on already-inactive timer goes through the
        # `if active` short-circuit
        sm.stop_autosave()
        # No additional stop() call is made because isActive() is False
        assert sm.autosave_timer.stop_calls == 1


class TestShutdown:
    def test_shutdown_stops_autosave(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        sm.shutdown()
        assert sm.autosave_timer._active is False

    def test_shutdown_safe_without_main_app(self, sm):
        # No main_app set → just the stop path; no save attempted
        sm.shutdown()  # must not raise

    def test_shutdown_main_app_without_get_current_state(self, sm, stub_timer):
        # main_app exists but has no get_current_state attr → save skipped
        sm.start_autosave(object())  # plain object has no get_current_state
        sm.shutdown()
        # No autosave file written
        assert not sm.autosave_path.exists()

    def test_shutdown_with_state_saves_autosave(self, sm, stub_timer, tmp_path):
        main_app = MagicMock()
        main_app.get_current_state.return_value = {
            "colors": _slots(),
            "image_path": "/foo.png",
            "settings": {"theme": "Dark"},
        }
        sm.start_autosave(main_app)
        sm.shutdown()
        assert sm.autosave_path.exists()

    def test_shutdown_with_empty_colors_skips_save(self, sm, stub_timer):
        main_app = MagicMock()
        main_app.get_current_state.return_value = {"colors": []}
        sm.start_autosave(main_app)
        sm.shutdown()
        assert not sm.autosave_path.exists()

    def test_shutdown_with_none_state_skips_save(self, sm, stub_timer):
        main_app = MagicMock()
        main_app.get_current_state.return_value = None
        sm.start_autosave(main_app)
        sm.shutdown()
        assert not sm.autosave_path.exists()

    def test_shutdown_swallows_exception(self, sm, stub_timer):
        main_app = MagicMock()
        main_app.get_current_state.side_effect = RuntimeError("boom")
        sm.start_autosave(main_app)
        # Must not raise
        sm.shutdown()


class TestAutosaveCallback:
    """The _autosave method is what the QTimer calls on tick."""

    def test_no_main_app_returns_early(self, sm):
        # No main_app means immediate return; no exception
        sm._autosave()
        assert not sm.autosave_path.exists()

    def test_no_get_current_state_returns_early(self, sm):
        sm.main_app = object()  # no get_current_state attr
        sm._autosave()
        assert not sm.autosave_path.exists()

    def test_empty_state_skips_save(self, sm):
        sm.main_app = MagicMock()
        sm.main_app.get_current_state.return_value = {"colors": []}
        sm._autosave()
        assert not sm.autosave_path.exists()

    def test_with_state_writes_autosave_file(self, sm):
        sm.main_app = MagicMock()
        sm.main_app.get_current_state.return_value = {
            "colors": _slots(),
            "image_path": None,
            "settings": {},
        }
        sm._autosave()
        assert sm.autosave_path.exists()

    def test_swallows_exception(self, sm):
        sm.main_app = MagicMock()
        sm.main_app.get_current_state.side_effect = RuntimeError("tick fail")
        sm._autosave()  # must not raise


class TestCheckForAutosave:
    def test_returns_path_string_when_exists(self, sm):
        sm.autosave_path.write_text("{}")
        result = sm.check_for_autosave()
        assert result == str(sm.autosave_path)

    def test_returns_none_when_missing(self, sm):
        assert sm.check_for_autosave() is None


class TestDeleteAutosave:
    def test_removes_existing_file(self, sm):
        sm.autosave_path.write_text("{}")
        assert sm.autosave_path.exists()
        sm.delete_autosave()
        assert not sm.autosave_path.exists()

    def test_no_file_is_noop(self, sm):
        assert not sm.autosave_path.exists()
        sm.delete_autosave()  # must not raise

    def test_swallows_exception(self, sm, monkeypatch):
        sm.autosave_path.write_text("{}")

        # Make Path.unlink raise — the except in source should swallow it
        def fail_unlink(self_inner, *args, **kwargs):
            raise OSError("locked")
        monkeypatch.setattr(Path, "unlink", fail_unlink)
        sm.delete_autosave()  # must not raise


class TestSetAutosaveInterval:
    def test_clamps_below_minimum(self, sm):
        sm.set_autosave_interval(5)
        assert sm.autosave_interval == 30

    def test_accepts_value_above_minimum(self, sm):
        sm.set_autosave_interval(120)
        assert sm.autosave_interval == 120

    def test_at_minimum_boundary(self, sm):
        sm.set_autosave_interval(30)
        assert sm.autosave_interval == 30

    def test_restarts_active_timer_with_new_interval(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        sm.set_autosave_interval(45)
        # After restart, interval should be 45 * 1000 ms
        assert sm.autosave_timer._interval == 45_000
        # Timer was stopped and started again
        assert sm.autosave_timer.start_calls == 2
        assert sm.autosave_timer.stop_calls == 1

    def test_does_not_touch_inactive_timer(self, sm, stub_timer):
        sm.start_autosave(MagicMock())
        sm.autosave_timer.stop()  # inactive
        prior_starts = sm.autosave_timer.start_calls
        sm.set_autosave_interval(60)
        # No restart since timer wasn't active
        assert sm.autosave_timer.start_calls == prior_starts


# ---------------------------------------------------------------------------
# Simple getters
# ---------------------------------------------------------------------------


class TestSimpleGetters:
    def test_get_session_id(self, sm):
        assert sm.get_session_id() == sm._session_id

    def test_get_autosave_path(self, sm):
        assert sm.get_autosave_path() == sm.autosave_path
        assert isinstance(sm.get_autosave_path(), Path)


# ---------------------------------------------------------------------------
# list_autosaves
# ---------------------------------------------------------------------------


class TestListAutosaves:
    def test_empty_dir_returns_empty_list(self, sm):
        assert sm.list_autosaves() == []

    def test_only_autosave_prefixed_files_returned(self, sm, tmp_path):
        # Plant a regular session AND an autosave; only the autosave shows up
        sm.save_session("regular", _slots())
        # Manually craft an autosave file
        autosave = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}20990101_000000.cpksession"
        autosave.write_text(json.dumps({
            "version": "1.0", "name": "old auto",
            "metadata": {"color_count": 3}, "modified": "2099-01-01T00:00:00",
            "created": "2099-01-01T00:00:00", "description": "",
        }))
        result = sm.list_autosaves()
        assert len(result) == 1
        assert result[0]["name"] == "old auto"

    def test_corrupted_autosave_skipped(self, sm, tmp_path):
        # Two autosaves; one is corrupted
        good = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}good.cpksession"
        bad = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}bad.cpksession"
        good.write_text(json.dumps({
            "version": "1.0", "name": "g", "metadata": {}, "modified": "z",
            "created": "", "description": "",
        }))
        bad.write_text("{not json")
        result = sm.list_autosaves()
        assert len(result) == 1
        assert result[0]["name"] == "g"

    def test_current_session_marker_set(self, sm):
        # Write a file at the current session's autosave path
        sm.autosave_path.write_text(json.dumps({
            "version": "1.0", "name": "current", "metadata": {}, "modified": "z",
            "created": "", "description": "",
        }))
        result = sm.list_autosaves()
        assert any(a["is_current_session"] for a in result)

    def test_sorted_newest_first(self, sm, tmp_path):
        old_path = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}old.cpksession"
        new_path = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}new.cpksession"
        old_path.write_text(json.dumps({
            "version": "1.0", "name": "old", "metadata": {},
            "modified": "2020-01-01T00:00:00", "created": "", "description": "",
        }))
        new_path.write_text(json.dumps({
            "version": "1.0", "name": "new", "metadata": {},
            "modified": "2099-01-01T00:00:00", "created": "", "description": "",
        }))
        result = sm.list_autosaves()
        assert result[0]["name"] == "new"
        assert result[-1]["name"] == "old"

    def test_returns_empty_on_outer_exception(self, sm, monkeypatch):
        # Force the glob() to raise
        def fail_glob(self_inner, pattern):
            raise RuntimeError("glob broke")
        monkeypatch.setattr(Path, "glob", fail_glob)
        assert sm.list_autosaves() == []


# ---------------------------------------------------------------------------
# cleanup_old_autosaves
# ---------------------------------------------------------------------------


class TestCleanupOldAutosaves:
    def _make_autosave(self, tmp_path, suffix, modified):
        path = tmp_path / f"{SessionManager.AUTOSAVE_PREFIX}{suffix}.cpksession"
        path.write_text(json.dumps({
            "version": "1.0", "name": suffix, "metadata": {},
            "modified": modified, "created": "", "description": "",
        }))
        return path

    def test_no_autosaves_deletes_nothing(self, sm):
        assert sm.cleanup_old_autosaves(keep_count=5) == 0

    def test_below_keep_count_deletes_nothing(self, sm, tmp_path):
        for i in range(3):
            self._make_autosave(tmp_path, f"a{i}", f"2020-01-0{i+1}T00:00:00")
        assert sm.cleanup_old_autosaves(keep_count=5) == 0

    def test_above_keep_count_deletes_oldest(self, sm, tmp_path):
        # 7 autosaves, keep 3 → delete 4
        for i in range(7):
            self._make_autosave(tmp_path, f"a{i}", f"2020-01-{i+1:02d}T00:00:00")
        deleted = sm.cleanup_old_autosaves(keep_count=3)
        assert deleted == 4

    def test_current_session_protected(self, sm, tmp_path):
        # Write current-session autosave plus 5 olds; cleanup with keep=0
        sm.autosave_path.write_text(json.dumps({
            "version": "1.0", "name": "current", "metadata": {},
            "modified": "2099-12-31T00:00:00", "created": "", "description": "",
        }))
        for i in range(5):
            self._make_autosave(tmp_path, f"old{i}", f"2020-01-{i+1:02d}T00:00:00")
        sm.cleanup_old_autosaves(keep_count=0)
        # Current session autosave must still exist
        assert sm.autosave_path.exists()

    def test_swallows_per_file_remove_failure(self, sm, tmp_path, monkeypatch):
        # 3 autosaves, keep 0 — but os.remove fails on every call.
        # Source uses try/except per file and continues.
        for i in range(3):
            self._make_autosave(tmp_path, f"a{i}", f"2020-01-0{i+1}T00:00:00")

        def fail_remove(path):
            raise OSError("denied")
        monkeypatch.setattr(os, "remove", fail_remove)
        # Should not raise; deleted count stays at 0
        assert sm.cleanup_old_autosaves(keep_count=0) == 0

    def test_returns_zero_on_outer_exception(self, sm, monkeypatch):
        # Make list_autosaves raise — outer except returns 0
        def fail_list(self_inner):
            raise RuntimeError("listing broke")
        monkeypatch.setattr(SessionManager, "list_autosaves", fail_list)
        assert sm.cleanup_old_autosaves() == 0


# ---------------------------------------------------------------------------
# Singleton + module-level convenience functions
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_first_call_creates_instance(self, monkeypatch, tmp_path):
        # Force home dir to tmp so no pollution
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        sm = get_session_manager()
        assert isinstance(sm, SessionManager)

    def test_subsequent_calls_return_same_instance(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        first = get_session_manager()
        second = get_session_manager()
        assert first is second


class TestModuleLevelConvenience:
    def test_module_save_session_delegates_to_singleton(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Module-level wrapper goes through get_session_manager()
        fp = str(tmp_path / "mod_save")
        assert module_save_session(fp, _slots()) is True
        assert (tmp_path / "mod_save.cpksession").exists()

    def test_module_load_session_delegates_to_singleton(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        fp = str(tmp_path / "mod_load")
        module_save_session(fp, _slots())
        loaded = module_load_session(fp + ".cpksession")
        assert loaded is not None
        assert loaded["colors"][0]["rgb"] == [255, 0, 0]
