# -*- coding: utf-8 -*-
"""
Tests for utils/error_handler.py.

Phase 3-aux-3 covers ErrorHandler — the centralized exception-wrapping
utility used throughout the codebase via `safe_execute` and `safe_method`.
We focus on the previously-uncovered surfaces: `_log_to_file`,
`safe_method` decorator, `ErrorContext` context manager, `safe_file_operation`
and `safe_widget_operation` convenience helpers, the singleton-style getters,
and various branches in `handle_exception` itself.

Coverage targets:
  - _log_error / _log_warning            (module-level helpers)
  - ErrorHandler.handle_exception        (callback success + callback failure +
                                          show_traceback + LOG_TO_FILE branch +
                                          custom user_message)
  - ErrorHandler._log_to_file            (writes file + recovers on file error)
  - ErrorHandler.safe_execute            (happy path + exception + reraise +
                                          fallback_value)
  - ErrorHandler.safe_method             (decorator wires status_updated +
                                          status_message + neither + fallback)
  - ErrorContext.__init__/__enter__/__exit__ (success path + exception path +
                                          reraise=True passes through)
  - safe_file_operation                  (success + FileNotFoundError +
                                          PermissionError + generic exception)
  - safe_widget_operation                (success + None widget + exception)
  - get_error_handler                    (returns class)
  - get_error_context                    (returns ErrorContext)
"""

import pytest
import os
from unittest.mock import MagicMock

from utils.error_handler import (
    _log_error,
    _log_warning,
    ErrorHandler,
    ErrorContext,
    safe_file_operation,
    safe_widget_operation,
    get_error_handler,
    get_error_context,
)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def restore_error_handler_flags():
    """Snapshot/restore ErrorHandler class-level flags so tests don't bleed."""
    original_show = ErrorHandler.SHOW_TRACEBACK
    original_log = ErrorHandler.LOG_TO_FILE
    original_path = ErrorHandler.LOG_FILE_PATH
    yield
    ErrorHandler.SHOW_TRACEBACK = original_show
    ErrorHandler.LOG_TO_FILE = original_log
    ErrorHandler.LOG_FILE_PATH = original_path


# =============================================================================
# 1.  Module-level _log_error and _log_warning
# =============================================================================

class TestLogHelpers:
    """`_log_error` and `_log_warning` are thin wrappers around the module
    Logger. They must not crash on any reasonable input."""

    def test_log_error_with_traceback_flag(self):
        try:
            raise ValueError("oops")
        except ValueError as e:
            _log_error("test context", e, show_traceback=True)
            # Must not raise

    def test_log_error_without_traceback(self):
        try:
            raise RuntimeError("oops")
        except RuntimeError as e:
            _log_error("test context", e, show_traceback=False)

    def test_log_warning_with_string(self):
        _log_warning("a warning message")  # must not raise


# =============================================================================
# 2.  ErrorHandler.handle_exception
# =============================================================================

class TestHandleException:
    """`handle_exception` logs, optionally prints traceback, optionally
    appends to a file, and optionally invokes a status_callback."""

    def test_runs_without_callback(self):
        ErrorHandler.handle_exception(
            ValueError("test"),
            "test context",
            show_traceback=False,
        )

    def test_invokes_status_callback_with_default_message(self):
        captured = []
        ErrorHandler.handle_exception(
            ValueError("test"),
            "loading file",
            status_callback=lambda msg: captured.append(msg),
            show_traceback=False,
        )
        assert len(captured) == 1
        # Default user message: "{context.capitalize()} failed"
        assert "loading file" in captured[0].lower()
        assert "failed" in captured[0].lower()

    def test_custom_user_message_overrides_default(self):
        captured = []
        ErrorHandler.handle_exception(
            ValueError("test"),
            "ctx",
            status_callback=lambda msg: captured.append(msg),
            show_traceback=False,
            user_message="Custom error happened",
        )
        assert captured == ["Custom error happened"]

    def test_callback_failure_does_not_propagate(self):
        # A status callback that itself raises must not crash
        def bad_callback(msg):
            raise RuntimeError("callback exploded")
        # Must not raise:
        ErrorHandler.handle_exception(
            ValueError("test"),
            "ctx",
            status_callback=bad_callback,
            show_traceback=False,
        )

    def test_show_traceback_flag_with_class_flag_true(
            self, restore_error_handler_flags):
        # Both arg and class flag must be True for traceback
        ErrorHandler.SHOW_TRACEBACK = True
        ErrorHandler.handle_exception(
            ValueError("test"), "ctx", show_traceback=True,
        )

    def test_show_traceback_class_flag_false_skips(
            self, restore_error_handler_flags):
        ErrorHandler.SHOW_TRACEBACK = False
        ErrorHandler.handle_exception(
            ValueError("test"), "ctx", show_traceback=True,
        )

    def test_log_to_file_flag_triggers_file_write(
            self, restore_error_handler_flags, tmp_path):
        log_path = str(tmp_path / "errors.log")
        ErrorHandler.LOG_TO_FILE = True
        ErrorHandler.LOG_FILE_PATH = log_path
        ErrorHandler.handle_exception(
            ValueError("disk error"), "saving",
            show_traceback=False,
        )
        # File should now exist with our error
        assert os.path.exists(log_path)
        content = open(log_path).read()
        assert "saving" in content
        assert "disk error" in content


# =============================================================================
# 3.  ErrorHandler._log_to_file
# =============================================================================

class TestLogToFile:
    """`_log_to_file` writes timestamp + context + error + traceback to a
    file. If the file write itself fails, it must not propagate."""

    def test_writes_to_file(self, restore_error_handler_flags, tmp_path):
        log_path = str(tmp_path / "errors.log")
        ErrorHandler.LOG_FILE_PATH = log_path
        try:
            raise RuntimeError("simulated")
        except RuntimeError as e:
            ErrorHandler._log_to_file(e, "test context")
        assert os.path.exists(log_path)
        content = open(log_path).read()
        assert "test context" in content
        assert "simulated" in content
        assert "Timestamp:" in content

    def test_appends_to_existing_file(
            self, restore_error_handler_flags, tmp_path):
        log_path = str(tmp_path / "errors.log")
        ErrorHandler.LOG_FILE_PATH = log_path
        # Write twice
        try:
            raise ValueError("first")
        except ValueError as e:
            ErrorHandler._log_to_file(e, "first ctx")
        try:
            raise ValueError("second")
        except ValueError as e:
            ErrorHandler._log_to_file(e, "second ctx")
        content = open(log_path).read()
        assert "first" in content
        assert "second" in content

    def test_handles_unwritable_path_silently(
            self, restore_error_handler_flags):
        # Use an invalid path (NUL char is invalid on every OS for filenames)
        ErrorHandler.LOG_FILE_PATH = "/bogus/\x00/no_such.log"
        try:
            raise RuntimeError("test")
        except RuntimeError as e:
            # Must not raise
            ErrorHandler._log_to_file(e, "context")


# =============================================================================
# 4.  ErrorHandler.safe_execute
# =============================================================================

class TestSafeExecute:
    """`safe_execute` runs the func, returns its result, or returns
    fallback_value on exception. Optionally re-raises."""

    def test_returns_result_on_success(self):
        result = ErrorHandler.safe_execute(
            lambda: 42, "test context",
        )
        assert result == 42

    def test_returns_fallback_on_exception(self):
        result = ErrorHandler.safe_execute(
            lambda: 1 / 0, "division test",
            fallback_value="default",
        )
        assert result == "default"

    def test_default_fallback_is_none(self):
        result = ErrorHandler.safe_execute(
            lambda: (_ for _ in ()).throw(ValueError("oops")),
            "throwing test",
        )
        assert result is None

    def test_reraise_propagates_exception(self):
        with pytest.raises(KeyError):
            ErrorHandler.safe_execute(
                lambda: (_ for _ in ()).throw(KeyError("propagate")),
                "test", reraise=True,
            )

    def test_status_callback_invoked_on_exception(self):
        captured = []
        ErrorHandler.safe_execute(
            lambda: 1 / 0, "div by zero",
            status_callback=lambda msg: captured.append(msg),
        )
        assert len(captured) == 1
        assert "div by zero" in captured[0].lower()

    def test_user_message_passed_through(self):
        captured = []
        ErrorHandler.safe_execute(
            lambda: 1 / 0, "ctx",
            status_callback=lambda msg: captured.append(msg),
            user_message="Special message",
        )
        assert captured == ["Special message"]


# =============================================================================
# 5.  ErrorHandler.safe_method (decorator)
# =============================================================================

class TestSafeMethod:
    """`safe_method` is a decorator factory. It detects `status_updated` or
    `status_message` signal-like attributes on `self` and forwards to
    `safe_execute`."""

    def test_decorator_returns_method_result_on_success(self):
        class Obj:
            @ErrorHandler.safe_method("doing thing")
            def do_thing(self, x):
                return x * 2
        assert Obj().do_thing(7) == 14

    def test_decorator_returns_fallback_on_exception(self):
        class Obj:
            @ErrorHandler.safe_method("failing thing", fallback_value="fb")
            def fail(self):
                raise ValueError("nope")
        assert Obj().fail() == "fb"

    def test_decorator_uses_status_updated_signal(self):
        class Obj:
            def __init__(self):
                self.captured = []
                self.status_updated = MagicMock()
                self.status_updated.emit = lambda msg: self.captured.append(msg)
            @ErrorHandler.safe_method("op")
            def op(self):
                raise ValueError("bad")
        o = Obj()
        o.op()
        assert len(o.captured) == 1

    def test_decorator_falls_back_to_status_message_signal(self):
        class Obj:
            def __init__(self):
                self.captured = []
                # No status_updated; only status_message
                self.status_message = MagicMock()
                self.status_message.emit = lambda msg: self.captured.append(msg)
            @ErrorHandler.safe_method("op")
            def op(self):
                raise ValueError("bad")
        o = Obj()
        o.op()
        assert len(o.captured) == 1

    def test_decorator_handles_object_without_status_signals(self):
        class Obj:
            @ErrorHandler.safe_method("op", fallback_value=99)
            def op(self):
                raise RuntimeError("no signal")
        # Must not crash, just return fallback
        assert Obj().op() == 99

    def test_decorator_passes_args_and_kwargs(self):
        class Obj:
            @ErrorHandler.safe_method("op")
            def op(self, a, b, c=0):
                return a + b + c
        assert Obj().op(1, 2, c=10) == 13

    def test_decorator_preserves_method_name_via_wraps(self):
        class Obj:
            @ErrorHandler.safe_method("op")
            def my_method(self):
                pass
        assert Obj.my_method.__name__ == "my_method"


# =============================================================================
# 6.  ErrorContext (context manager)
# =============================================================================

class TestErrorContext:
    """`ErrorContext` is a context manager that catches and logs exceptions
    inside its `with` block. By default, exceptions are swallowed."""

    def test_no_exception_passes_through(self):
        with ErrorContext("safe op"):
            x = 1 + 1
        assert x == 2

    def test_exception_inside_is_swallowed(self):
        # No exception should propagate out
        with ErrorContext("dangerous op"):
            raise ValueError("boom")
        # Got here means swallowed

    def test_status_callback_invoked_on_exception(self):
        captured = []
        with ErrorContext(
            "ctx", status_callback=lambda m: captured.append(m),
        ):
            raise ValueError("error")
        assert len(captured) == 1

    def test_reraise_true_propagates(self):
        with pytest.raises(ValueError, match="propagate"):
            with ErrorContext("ctx", reraise=True):
                raise ValueError("propagate")

    def test_returns_self_on_enter(self):
        ctx = ErrorContext("ctx")
        with ctx as entered:
            assert entered is ctx

    def test_user_message_passed_through(self):
        captured = []
        with ErrorContext(
            "ctx",
            status_callback=lambda m: captured.append(m),
            user_message="custom",
        ):
            raise ValueError("boom")
        assert captured == ["custom"]


# =============================================================================
# 7.  safe_file_operation
# =============================================================================

class TestSafeFileOperation:
    """`safe_file_operation` runs a callable, catching three kinds of error
    distinctly: FileNotFoundError, PermissionError, and generic Exception."""

    def test_returns_result_on_success(self, tmp_path):
        path = tmp_path / "x.txt"
        path.write_text("data")
        result = safe_file_operation(
            lambda: path.read_text(), str(path), "reading",
        )
        assert result == "data"

    def test_file_not_found_returns_none(self):
        def missing(): raise FileNotFoundError("/no/such")
        result = safe_file_operation(missing, "/no/such", "reading")
        assert result is None

    def test_permission_error_returns_none(self):
        def denied(): raise PermissionError("/protected")
        result = safe_file_operation(denied, "/protected", "writing")
        assert result is None

    def test_generic_exception_returns_none(self):
        def oops(): raise RuntimeError("disk full")
        result = safe_file_operation(oops, "/disk", "writing")
        assert result is None


# =============================================================================
# 8.  safe_widget_operation
# =============================================================================

class TestSafeWidgetOperation:
    """`safe_widget_operation` runs a Qt-widget operation, returning False
    on None widget or exception; True on success."""

    def test_returns_true_on_success(self):
        widget = MagicMock()
        ran = []
        result = safe_widget_operation(
            widget, lambda: ran.append(1), "set text",
        )
        assert result is True
        assert ran == [1]

    def test_returns_false_when_widget_is_none(self):
        ran = []
        result = safe_widget_operation(
            None, lambda: ran.append(1), "set text",
        )
        assert result is False
        # Operation should NOT have run
        assert ran == []

    def test_returns_false_when_operation_raises(self):
        widget = MagicMock()
        def bad_op(): raise RuntimeError("Qt error")
        result = safe_widget_operation(widget, bad_op, "broken op")
        assert result is False


# =============================================================================
# 9.  Singleton helpers
# =============================================================================

class TestSingletonHelpers:
    """`get_error_handler` and `get_error_context` provide a uniform API
    parallel to other Manager classes in the codebase."""

    def test_get_error_handler_returns_class(self):
        h = get_error_handler()
        assert h is ErrorHandler

    def test_get_error_handler_methods_callable(self):
        h = get_error_handler()
        # Should still be callable as the static method
        result = h.safe_execute(lambda: 7, "test")
        assert result == 7

    def test_get_error_context_returns_instance(self):
        ctx = get_error_context("ctx")
        assert isinstance(ctx, ErrorContext)
        assert ctx.context == "ctx"

    def test_get_error_context_with_callback(self):
        cb = lambda m: None
        ctx = get_error_context("ctx", status_callback=cb)
        assert ctx.status_callback is cb

    def test_get_error_context_default_reraise_false(self):
        ctx = get_error_context("ctx")
        assert ctx.reraise is False
