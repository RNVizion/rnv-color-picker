"""
Phase 6 part 2: utils/async_file_ops.py — Qt threading on file I/O.

Same hybrid strategy as test_workers.py:
  - Synchronous run() for FileWriterThread / FileReaderThread logic
    (json/text/binary branches, ValueError on unknown format, exception path)
  - Real start() with qtbot.waitUntil for AsyncFileManager lifecycle tests
    where the manager kicks off the thread internally and we need to wait
    for the user-supplied callback to fire

Coverage targets:
  - FileWriterThread — init, json/text/binary writes, ValueError for
    unknown format, exception path (unwritable destination)
  - FileReaderThread — init, json/text/binary reads, ValueError for
    unknown format, exception path (missing file, malformed JSON)
  - AsyncFileManager — write_file_async + read_file_async happy paths,
    progress_callback wiring, status_callback wiring, _cleanup_threads,
    wait_all, cancel_all, get_active_count, callback exception handling
  - Module-level convenience functions: async_save_json, async_load_json
"""

import json
import time

import pytest
from PyQt6.QtCore import QThread

from utils.async_file_ops import (
    FileWriterThread,
    FileReaderThread,
    AsyncFileManager,
    async_save_json,
    async_load_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_writer_signals(thread):
    """Hook lists onto FileWriterThread's two signals.

    Returns (finished_log, progress_log). After thread.run() finishes (or
    after qtbot has waited on a real start()), the lists are populated.
    """
    finished_log, progress_log = [], []
    thread.finished.connect(lambda ok, msg: finished_log.append((ok, msg)))
    thread.progress.connect(lambda p: progress_log.append(p))
    return finished_log, progress_log


def _collect_reader_signals(thread):
    """Hook lists onto FileReaderThread's two signals.

    Returns (finished_log, progress_log) where finished entries are
    (success, data, message) tuples.
    """
    finished_log, progress_log = [], []
    thread.finished.connect(
        lambda ok, data, msg: finished_log.append((ok, data, msg)))
    thread.progress.connect(lambda p: progress_log.append(p))
    return finished_log, progress_log


# ===========================================================================
# FileWriterThread
# ===========================================================================


class TestFileWriterThreadInit:
    def test_inherits_qthread(self, tmp_path):
        # AsyncFileManager treats threads polymorphically as QThread
        t = FileWriterThread(str(tmp_path / "x.json"), {})
        assert isinstance(t, QThread)

    def test_signals_defined(self):
        assert hasattr(FileWriterThread, "finished")
        assert hasattr(FileWriterThread, "progress")

    def test_init_stores_filepath_and_data(self, tmp_path):
        path = str(tmp_path / "x.json")
        data = {"colors": [(255, 0, 0)]}
        t = FileWriterThread(path, data)
        assert t.filepath == path
        assert t.data == data

    def test_default_format_is_json(self, tmp_path):
        t = FileWriterThread(str(tmp_path / "x.json"), {})
        assert t.format == "json"


class TestFileWriterThreadJson:
    def test_writes_json_with_indent_and_unicode(self, tmp_path):
        path = tmp_path / "out.json"
        payload = {"name": "café", "values": [1, 2, 3]}
        t = FileWriterThread(str(path), payload, format="json")
        finished, progress = _collect_writer_signals(t)
        t.run()
        # File written, content matches
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == payload
        # Finished with success=True
        assert finished == [(True, f"✔ Saved to {path}")]
        # Progress reaches 100
        assert progress[-1] == 100

    def test_progress_monotonic(self, tmp_path):
        # Source emits 10 → 30 → 90 → 100 for the json branch
        path = tmp_path / "out.json"
        t = FileWriterThread(str(path), {"k": "v"}, format="json")
        _, progress = _collect_writer_signals(t)
        t.run()
        assert progress == sorted(progress)
        assert progress[0] == 10
        assert progress[-1] == 100


class TestFileWriterThreadText:
    def test_writes_text(self, tmp_path):
        path = tmp_path / "out.txt"
        t = FileWriterThread(str(path), "hello world", format="text")
        finished, _ = _collect_writer_signals(t)
        t.run()
        assert path.read_text(encoding="utf-8") == "hello world"
        assert finished[0][0] is True

    def test_str_conversion_for_non_string_data(self, tmp_path):
        # Source does `f.write(str(self.data))` for text format
        path = tmp_path / "out.txt"
        t = FileWriterThread(str(path), 42, format="text")
        _, _ = _collect_writer_signals(t)
        t.run()
        assert path.read_text(encoding="utf-8") == "42"


class TestFileWriterThreadBinary:
    def test_writes_bytes(self, tmp_path):
        path = tmp_path / "out.bin"
        payload = b"\x00\x01\x02\xff\xfe"
        t = FileWriterThread(str(path), payload, format="binary")
        finished, _ = _collect_writer_signals(t)
        t.run()
        assert path.read_bytes() == payload
        assert finished[0][0] is True


class TestFileWriterThreadErrorBranches:
    def test_unknown_format_emits_failure(self, tmp_path):
        # Source raises ValueError for unsupported formats; the except
        # block converts it into finished(False, "Save failed: ...")
        t = FileWriterThread(
            str(tmp_path / "x.dat"), b"data", format="not_a_real_format")
        finished, _ = _collect_writer_signals(t)
        t.run()
        assert len(finished) == 1
        success, msg = finished[0]
        assert success is False
        assert "Save failed" in msg

    def test_unwritable_destination_emits_failure(self, tmp_path):
        # /no/such/dir/file.json — open() raises FileNotFoundError
        t = FileWriterThread("/no/such/dir/x.json", {"k": 1}, format="json")
        finished, _ = _collect_writer_signals(t)
        t.run()
        assert finished[0][0] is False
        assert "Save failed" in finished[0][1]


# ===========================================================================
# FileReaderThread
# ===========================================================================


class TestFileReaderThreadInit:
    def test_inherits_qthread(self, tmp_path):
        t = FileReaderThread(str(tmp_path / "x.json"))
        assert isinstance(t, QThread)

    def test_init_stores_filepath_and_default_format(self, tmp_path):
        path = str(tmp_path / "x.json")
        t = FileReaderThread(path)
        assert t.filepath == path
        assert t.format == "json"


class TestFileReaderThreadJson:
    def test_reads_back_json(self, tmp_path):
        path = tmp_path / "in.json"
        payload = {"colors": [[255, 0, 0], [0, 255, 0]]}
        path.write_text(json.dumps(payload), encoding="utf-8")
        t = FileReaderThread(str(path))
        finished, progress = _collect_reader_signals(t)
        t.run()
        assert len(finished) == 1
        success, data, msg = finished[0]
        assert success is True
        assert data == payload
        assert "Loaded from" in msg
        assert progress[-1] == 100

    def test_unicode_round_trip(self, tmp_path):
        path = tmp_path / "in.json"
        payload = {"name": "café", "emoji": "🎨"}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        t = FileReaderThread(str(path))
        finished, _ = _collect_reader_signals(t)
        t.run()
        assert finished[0][1] == payload


class TestFileReaderThreadText:
    def test_reads_text(self, tmp_path):
        path = tmp_path / "in.txt"
        path.write_text("plain text contents", encoding="utf-8")
        t = FileReaderThread(str(path), format="text")
        finished, _ = _collect_reader_signals(t)
        t.run()
        assert finished[0][1] == "plain text contents"


class TestFileReaderThreadBinary:
    def test_reads_bytes(self, tmp_path):
        path = tmp_path / "in.bin"
        payload = b"\x00\xff\x10\x20\x30"
        path.write_bytes(payload)
        t = FileReaderThread(str(path), format="binary")
        finished, _ = _collect_reader_signals(t)
        t.run()
        assert finished[0][1] == payload


class TestFileReaderThreadErrorBranches:
    def test_unknown_format_emits_failure(self, tmp_path):
        # ValueError for unsupported format → caught by outer try
        path = tmp_path / "x.dat"
        path.write_bytes(b"anything")
        t = FileReaderThread(str(path), format="invalid_fmt")
        finished, _ = _collect_reader_signals(t)
        t.run()
        success, data, msg = finished[0]
        assert success is False
        assert data is None
        assert "Load failed" in msg

    def test_missing_file_emits_failure(self, tmp_path):
        t = FileReaderThread(str(tmp_path / "missing.json"))
        finished, _ = _collect_reader_signals(t)
        t.run()
        success, data, msg = finished[0]
        assert success is False
        assert data is None
        assert "Load failed" in msg

    def test_malformed_json_emits_failure(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not valid json")
        t = FileReaderThread(str(path))
        finished, _ = _collect_reader_signals(t)
        t.run()
        assert finished[0][0] is False


# ===========================================================================
# AsyncFileManager — uses qtbot for real-thread lifecycle
# ===========================================================================


class TestAsyncFileManagerInit:
    def test_starts_with_empty_thread_list(self):
        m = AsyncFileManager()
        assert m._active_threads == []

    def test_default_callbacks_are_none(self):
        m = AsyncFileManager()
        assert m.status_callback is None
        assert m.progress_callback is None

    def test_custom_callbacks_stored(self):
        status, progress = lambda *a: None, lambda *a: None
        m = AsyncFileManager(status_callback=status, progress_callback=progress)
        assert m.status_callback is status
        assert m.progress_callback is progress

    def test_active_count_zero_initially(self):
        assert AsyncFileManager().get_active_count() == 0


class TestAsyncFileManagerWriteAsync:
    def test_write_completes_and_invokes_callback(self, qtbot, tmp_path):
        # Real threading: spin up a writer thread, wait for the user
        # callback to fire (which means _on_write_complete already fired).
        path = str(tmp_path / "out.json")
        captured = []
        m = AsyncFileManager()
        m.write_file_async(
            path, {"k": "v"},
            on_complete=lambda ok, msg: captured.append((ok, msg)))
        qtbot.waitUntil(lambda: len(captured) > 0, timeout=5000)
        assert captured[0][0] is True
        assert json.loads((tmp_path / "out.json").read_text()) == {"k": "v"}

    def test_status_callback_receives_writing_then_done(self, qtbot, tmp_path):
        path = str(tmp_path / "out.json")
        statuses = []
        m = AsyncFileManager(status_callback=statuses.append)
        done = []
        m.write_file_async(path, {"k": 1},
                            on_complete=lambda ok, msg: done.append(msg))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        # Source emits "Writing file..." pre-start, then the success message
        # in _on_write_complete via status_callback(message)
        assert any("Writing" in s for s in statuses)
        assert any("Saved" in s for s in statuses)

    def test_progress_callback_receives_updates(self, qtbot, tmp_path):
        path = str(tmp_path / "out.json")
        progress = []
        done = []
        m = AsyncFileManager(progress_callback=progress.append)
        m.write_file_async(path, {"k": 1},
                            on_complete=lambda ok, msg: done.append(msg))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        # Source emits 10, 30, 90, 100 in the json branch
        assert 100 in progress

    def test_no_on_complete_callback_is_safe(self, qtbot, tmp_path):
        # on_complete=None should not crash _on_write_complete
        path = str(tmp_path / "out.json")
        statuses = []
        m = AsyncFileManager(status_callback=statuses.append)
        m.write_file_async(path, {"k": 1}, on_complete=None)
        # Wait until status callback observes the success message
        qtbot.waitUntil(lambda: any("Saved" in s for s in statuses),
                        timeout=5000)


class TestAsyncFileManagerReadAsync:
    def test_read_completes_and_invokes_callback(self, qtbot, tmp_path):
        path = tmp_path / "in.json"
        path.write_text(json.dumps({"hello": "world"}))
        captured = []
        m = AsyncFileManager()
        m.read_file_async(
            str(path),
            on_complete=lambda ok, data, msg: captured.append((ok, data, msg)))
        qtbot.waitUntil(lambda: len(captured) > 0, timeout=5000)
        assert captured[0][0] is True
        assert captured[0][1] == {"hello": "world"}

    def test_read_failure_passes_none_data_to_callback(self, qtbot, tmp_path):
        captured = []
        m = AsyncFileManager()
        m.read_file_async(
            str(tmp_path / "missing.json"),
            on_complete=lambda ok, data, msg: captured.append((ok, data, msg)))
        qtbot.waitUntil(lambda: len(captured) > 0, timeout=5000)
        assert captured[0][0] is False
        assert captured[0][1] is None

    def test_status_callback_receives_reading_then_done(self, qtbot, tmp_path):
        path = tmp_path / "in.json"
        path.write_text(json.dumps([1, 2, 3]))
        statuses = []
        done = []
        m = AsyncFileManager(status_callback=statuses.append)
        m.read_file_async(str(path),
                           on_complete=lambda *a: done.append(a))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        assert any("Reading" in s for s in statuses)
        assert any("Loaded" in s for s in statuses)

    def test_read_with_progress_callback(self, qtbot, tmp_path):
        # Source line 248 — progress wiring for read_file_async.
        # Symmetric with the write progress test, but a different code path.
        path = tmp_path / "in.json"
        path.write_text(json.dumps({"k": 1}))
        progress = []
        done = []
        m = AsyncFileManager(progress_callback=progress.append)
        m.read_file_async(str(path),
                           on_complete=lambda *a: done.append(True))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        assert 100 in progress

    def test_read_with_no_on_complete_callback_is_safe(self, qtbot, tmp_path):
        # _on_read_complete short-circuits when callback is None.
        # Symmetric with the equivalent write test.
        path = tmp_path / "in.json"
        path.write_text(json.dumps({"k": 1}))
        statuses = []
        m = AsyncFileManager(status_callback=statuses.append)
        m.read_file_async(str(path), on_complete=None)
        qtbot.waitUntil(lambda: any("Loaded" in s for s in statuses),
                        timeout=5000)


class TestAsyncFileManagerCallbackExceptionHandling:
    def test_write_callback_exception_does_not_crash(self, qtbot, tmp_path):
        # Source wraps callback in try/except. A raising callback must not
        # propagate or break the manager's cleanup.
        m = AsyncFileManager()
        seen_callback = []

        def raising_callback(ok, msg):
            seen_callback.append(True)
            raise RuntimeError("intentional test failure")

        path = str(tmp_path / "out.json")
        # Just kicking this off and letting it complete should be safe
        m.write_file_async(path, {"k": 1}, on_complete=raising_callback)
        qtbot.waitUntil(lambda: len(seen_callback) > 0, timeout=5000)
        # File still got written despite the callback exploding
        assert (tmp_path / "out.json").exists()

    def test_read_callback_exception_does_not_crash(self, qtbot, tmp_path):
        path = tmp_path / "in.json"
        path.write_text(json.dumps({"x": 1}))
        seen_callback = []

        def raising_callback(ok, data, msg):
            seen_callback.append(True)
            raise RuntimeError("intentional test failure")

        m = AsyncFileManager()
        m.read_file_async(str(path), on_complete=raising_callback)
        qtbot.waitUntil(lambda: len(seen_callback) > 0, timeout=5000)


class TestAsyncFileManagerCleanupAndWait:
    def test_cleanup_threads_removes_finished(self, qtbot, tmp_path):
        # After a write completes, _cleanup_threads should drop it from
        # _active_threads. We observe by checking get_active_count later.
        path = str(tmp_path / "out.json")
        done = []
        m = AsyncFileManager()
        m.write_file_async(path, {"k": 1},
                            on_complete=lambda ok, msg: done.append(msg))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        # Give Qt a moment for _cleanup_threads to run
        qtbot.waitUntil(lambda: m.get_active_count() == 0, timeout=2000)

    def test_wait_all_returns_true_when_no_threads(self):
        assert AsyncFileManager().wait_all() is True

    def test_wait_all_blocks_until_completion(self, qtbot, tmp_path):
        path = str(tmp_path / "out.json")
        m = AsyncFileManager()
        m.write_file_async(path, {"k": 1}, on_complete=None)
        # wait_all blocks the test thread until the writer finishes
        result = m.wait_all(timeout=5000)
        assert result is True
        # File present after wait_all returns
        assert (tmp_path / "out.json").exists()

    def test_get_active_count_zero_after_completion(self, qtbot, tmp_path):
        path = str(tmp_path / "out.json")
        done = []
        m = AsyncFileManager()
        m.write_file_async(path, {"k": 1},
                            on_complete=lambda *a: done.append(True))
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        # _cleanup_threads runs at end of _on_write_complete
        qtbot.waitUntil(lambda: m.get_active_count() == 0, timeout=2000)

    def test_cleanup_swallows_deletelater_exception(self, qtbot, tmp_path):
        # _cleanup_threads has try/except around thread.deleteLater().
        # Patch QThread.deleteLater to raise; cleanup must not propagate.
        path = str(tmp_path / "out.json")
        done = []
        m = AsyncFileManager()

        def raise_on_delete(self):
            raise RuntimeError("deleteLater failed")
        # Patch on the QThread class so the writer thread is affected
        original = QThread.deleteLater
        QThread.deleteLater = raise_on_delete
        try:
            m.write_file_async(path, {"k": 1},
                                on_complete=lambda *a: done.append(True))
            qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
            # _cleanup_threads ran with the raising deleteLater and must not
            # have propagated. Active threads list still cleaned up.
            qtbot.waitUntil(lambda: m.get_active_count() == 0, timeout=2000)
        finally:
            QThread.deleteLater = original


class TestAsyncFileManagerCancelAll:
    def test_cancel_all_with_no_active_threads_is_safe(self):
        m = AsyncFileManager()
        m.cancel_all()  # must not raise
        assert m._active_threads == []

    def test_cancel_all_calls_status_callback(self):
        statuses = []
        m = AsyncFileManager(status_callback=statuses.append)
        m.cancel_all()
        assert any("cancelled" in s.lower() for s in statuses)


# ===========================================================================
# Module-level convenience wrappers
# ===========================================================================


class TestConvenienceFunctions:
    def test_async_save_json_returns_manager_and_writes(self, qtbot, tmp_path):
        path = str(tmp_path / "conv.json")
        done = []
        manager = async_save_json(
            path, {"k": "v"}, on_complete=lambda ok, msg: done.append(ok))
        # Returns an AsyncFileManager instance
        assert isinstance(manager, AsyncFileManager)
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        assert done[0] is True
        assert json.loads((tmp_path / "conv.json").read_text()) == {"k": "v"}

    def test_async_load_json_returns_manager_and_reads(self, qtbot, tmp_path):
        path = tmp_path / "conv.json"
        path.write_text(json.dumps({"loaded": True}))
        captured = []
        manager = async_load_json(
            str(path),
            on_complete=lambda ok, data, msg: captured.append((ok, data)))
        assert isinstance(manager, AsyncFileManager)
        qtbot.waitUntil(lambda: len(captured) > 0, timeout=5000)
        assert captured[0] == (True, {"loaded": True})

    def test_async_save_json_with_status_callback(self, qtbot, tmp_path):
        path = str(tmp_path / "conv.json")
        statuses = []
        done = []
        async_save_json(
            path, {"k": 1},
            on_complete=lambda ok, msg: done.append(True),
            status_callback=statuses.append)
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        assert len(statuses) >= 2  # "Writing..." + "Saved..."

    def test_async_load_json_with_status_callback(self, qtbot, tmp_path):
        path = tmp_path / "conv.json"
        path.write_text(json.dumps({"k": 1}))
        statuses = []
        done = []
        async_load_json(
            str(path),
            on_complete=lambda *a: done.append(True),
            status_callback=statuses.append)
        qtbot.waitUntil(lambda: len(done) > 0, timeout=5000)
        assert len(statuses) >= 2
