# -*- coding: utf-8 -*-
"""
Tests for utils/signal_manager.py.

Phase 3-aux-1 covers the signal connection manager — the foundational utility
that every UI test in this suite already depends on. The class tracks Qt
signal connections by widget ID, allows targeted or bulk cleanup, and surfaces
diagnostic stats. We also exercise the SignalMixin and the module-level
singleton helpers.

Coverage targets:
  - SignalConnectionManager.__init__              (empty state)
  - SignalConnectionManager.connect               (happy + error + tracking)
  - SignalConnectionManager.disconnect_widget     (happy + missing widget +
                                                   TypeError + quiet flag)
  - SignalConnectionManager.disconnect_all        (multi-widget + empty)
  - SignalConnectionManager.disconnect_widget_by_id
  - SignalConnectionManager.get_connection_count
  - SignalConnectionManager.get_widget_connection_count
  - SignalConnectionManager.get_stats
  - SignalConnectionManager.print_stats           (smoke)
  - SignalConnectionManager.list_connections      (label, lambda, anon)
  - SignalConnectionManager.verify_cleanup        (clean + dirty)
  - SignalMixin.init_signal_tracking
  - SignalMixin.track_connection
  - SignalMixin.cleanup_signals
  - get_signal_manager                            (lazy singleton)
  - reset_signal_manager                          (clears singleton)

Out of scope:
  - The "Failed to connect signal" branch in `connect` — Qt's signal.connect
    accepts almost anything callable, so reliably forcing an exception there
    requires a custom mock signal object. Logged as a small uncovered branch
    rather than chased.
"""

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from utils.signal_manager import (
    SignalConnectionManager,
    SignalMixin,
    get_signal_manager,
    reset_signal_manager,
)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

class _Emitter(QObject):
    """Minimal QObject with a parameterless and an int-parameter signal —
    used as a stand-in for any widget that emits real Qt signals."""
    triggered = pyqtSignal()
    value_changed = pyqtSignal(int)


@pytest.fixture
def manager():
    """Fresh SignalConnectionManager for each test."""
    return SignalConnectionManager()


@pytest.fixture
def emitter(qtbot):
    """A real QObject with two pyqtSignals."""
    e = _Emitter()
    return e


@pytest.fixture(autouse=True)
def _reset_singleton_between_tests():
    """Module-level singleton must not leak between tests."""
    yield
    reset_signal_manager()


# =============================================================================
# 1.  SignalConnectionManager.__init__
# =============================================================================

class TestInit:
    """Manager starts empty: no connections, zero counters."""

    def test_connections_dict_empty(self, manager):
        assert manager._connections == {}

    def test_connection_counter_zero(self, manager):
        assert manager._connection_count == 0

    def test_disconnection_counter_zero(self, manager):
        assert manager._disconnection_count == 0

    def test_get_connection_count_zero_initially(self, manager):
        assert manager.get_connection_count() == 0


# =============================================================================
# 2.  connect()
# =============================================================================

class TestConnect:
    """`connect` wires the signal, increments the connection counter, and
    records the (signal, slot, track_as) tuple under id(widget)."""

    def test_returns_signal_for_chaining(self, manager, emitter):
        # PyQt quirk: each access to `emitter.triggered` returns a *new*
        # bound-signal wrapper around the same underlying signal, so we
        # must capture once and compare to the captured reference.
        sig = emitter.triggered
        slot = lambda: None
        result = manager.connect(emitter, sig, slot)
        assert result is sig

    def test_increments_connection_counter(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        assert manager._connection_count == 1

    def test_signal_actually_fires_slot(self, manager, emitter):
        # Real wiring: emit fires the slot
        calls = []
        manager.connect(emitter, emitter.triggered,
                        lambda: calls.append(1))
        emitter.triggered.emit()
        assert calls == [1]

    def test_tracks_widget_in_connections_dict(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        assert id(emitter) in manager._connections

    def test_tracks_multiple_signals_for_same_widget(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.connect(emitter, emitter.value_changed, lambda v: None)
        assert len(manager._connections[id(emitter)]) == 2

    def test_tuple_includes_track_as_label(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="my_label")
        signal, slot, label = manager._connections[id(emitter)][0]
        assert label == "my_label"

    def test_default_track_as_is_none(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        signal, slot, label = manager._connections[id(emitter)][0]
        assert label is None

    def test_tracks_two_widgets_separately(self, manager, qtbot):
        e1 = _Emitter()
        e2 = _Emitter()
        manager.connect(e1, e1.triggered, lambda: None)
        manager.connect(e2, e2.triggered, lambda: None)
        assert id(e1) in manager._connections
        assert id(e2) in manager._connections
        assert manager._connections[id(e1)] is not manager._connections[id(e2)]


# =============================================================================
# 3.  disconnect_widget()
# =============================================================================

class TestDisconnectWidget:
    """`disconnect_widget` removes all connections for one widget, returns
    the count, and increments the disconnection counter."""

    def test_returns_zero_for_unknown_widget(self, manager, emitter):
        # Widget was never connected
        assert manager.disconnect_widget(emitter) == 0

    def test_returns_zero_quiet_for_unknown_widget(self, manager, emitter):
        # quiet flag suppresses warnings — verify still returns 0
        assert manager.disconnect_widget(emitter, quiet=True) == 0

    def test_disconnects_all_signals_for_widget(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.connect(emitter, emitter.value_changed, lambda v: None)
        assert manager.disconnect_widget(emitter) == 2

    def test_removes_widget_from_tracking_dict(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.disconnect_widget(emitter)
        assert id(emitter) not in manager._connections

    def test_increments_disconnection_counter(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.disconnect_widget(emitter)
        assert manager._disconnection_count == 1

    def test_signal_no_longer_fires_slot_after_disconnect(self, manager, emitter):
        calls = []
        manager.connect(emitter, emitter.triggered,
                        lambda: calls.append(1))
        manager.disconnect_widget(emitter)
        emitter.triggered.emit()
        assert calls == []

    def test_handles_already_disconnected_signal(self, manager, emitter):
        # If signal was manually disconnected before us, signal.disconnect
        # raises TypeError. We swallow that and continue.
        slot = lambda: None
        manager.connect(emitter, emitter.triggered, slot)
        emitter.triggered.disconnect(slot)  # manual disconnect first
        # Should not raise; should still clean up tracking
        result = manager.disconnect_widget(emitter, quiet=True)
        assert id(emitter) not in manager._connections
        # disconnected count should be 0 since the signal was already detached
        assert result == 0

    def test_quiet_flag_suppresses_logging_path(self, manager, emitter):
        # We can't easily assert "no log" without injecting a fake logger,
        # but we can verify the quiet path runs to completion and returns
        # the right value
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="test")
        assert manager.disconnect_widget(emitter, quiet=True) == 1

    def test_with_track_as_label_logs_on_disconnect(self, manager, emitter):
        # Smoke: the labeled disconnect path runs without crashing
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="labeled")
        assert manager.disconnect_widget(emitter) == 1


# =============================================================================
# 4.  disconnect_all() and disconnect_widget_by_id()
# =============================================================================

class TestDisconnectAll:
    """`disconnect_all` wipes the entire dict and returns total count."""

    def test_returns_zero_when_empty(self, manager):
        assert manager.disconnect_all() == 0

    def test_returns_zero_quiet_when_empty(self, manager):
        assert manager.disconnect_all(quiet=True) == 0

    def test_disconnects_multi_widget_connections(self, manager, qtbot):
        e1 = _Emitter()
        e2 = _Emitter()
        manager.connect(e1, e1.triggered, lambda: None)
        manager.connect(e1, e1.value_changed, lambda v: None)
        manager.connect(e2, e2.triggered, lambda: None)
        total = manager.disconnect_all(quiet=True)
        assert total == 3

    def test_clears_connections_dict(self, manager, qtbot):
        e1 = _Emitter()
        e2 = _Emitter()
        manager.connect(e1, e1.triggered, lambda: None)
        manager.connect(e2, e2.triggered, lambda: None)
        manager.disconnect_all(quiet=True)
        assert manager._connections == {}

    def test_signals_no_longer_fire_after_disconnect_all(self, manager, qtbot):
        e1 = _Emitter()
        calls = []
        manager.connect(e1, e1.triggered, lambda: calls.append(1))
        manager.disconnect_all(quiet=True)
        e1.triggered.emit()
        assert calls == []


class TestDisconnectWidgetById:
    """`disconnect_widget_by_id` is the internal helper used by
    disconnect_all — also covered for completeness."""

    def test_returns_zero_for_unknown_id(self, manager):
        assert manager.disconnect_widget_by_id(99999) == 0

    def test_disconnects_by_id(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        wid = id(emitter)
        result = manager.disconnect_widget_by_id(wid)
        assert result == 1
        assert wid not in manager._connections

    def test_swallows_disconnect_errors(self, manager, emitter):
        # Pre-disconnect the signal manually — Qt's signal.disconnect raises
        # then. The bulk path swallows all exceptions silently.
        slot = lambda: None
        manager.connect(emitter, emitter.triggered, slot)
        emitter.triggered.disconnect(slot)
        wid = id(emitter)
        # Must not raise
        manager.disconnect_widget_by_id(wid)
        assert wid not in manager._connections


# =============================================================================
# 5.  Counters and stats
# =============================================================================

class TestGetConnectionCount:
    """`get_connection_count` sums all per-widget connection lists."""

    def test_empty_returns_zero(self, manager):
        assert manager.get_connection_count() == 0

    def test_single_connection(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        assert manager.get_connection_count() == 1

    def test_multiple_widgets(self, manager, qtbot):
        e1 = _Emitter()
        e2 = _Emitter()
        manager.connect(e1, e1.triggered, lambda: None)
        manager.connect(e1, e1.value_changed, lambda v: None)
        manager.connect(e2, e2.triggered, lambda: None)
        assert manager.get_connection_count() == 3


class TestGetWidgetConnectionCount:
    """`get_widget_connection_count` reports for one widget."""

    def test_unknown_widget_returns_zero(self, manager, emitter):
        assert manager.get_widget_connection_count(emitter) == 0

    def test_known_widget_returns_count(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.connect(emitter, emitter.value_changed, lambda v: None)
        assert manager.get_widget_connection_count(emitter) == 2


class TestGetStats:
    """`get_stats` returns a dict with active/widgets/connected/disconnected."""

    def test_empty_stats(self, manager):
        s = manager.get_stats()
        assert s == {
            'active': 0,
            'widgets': 0,
            'total_connected': 0,
            'total_disconnected': 0,
        }

    def test_after_connect_and_disconnect(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.connect(emitter, emitter.value_changed, lambda v: None)
        manager.disconnect_widget(emitter, quiet=True)
        s = manager.get_stats()
        assert s['active'] == 0
        assert s['widgets'] == 0
        assert s['total_connected'] == 2
        assert s['total_disconnected'] == 2

    def test_active_reflects_pending_connections(self, manager, qtbot):
        e1 = _Emitter()
        e2 = _Emitter()
        manager.connect(e1, e1.triggered, lambda: None)
        manager.connect(e2, e2.triggered, lambda: None)
        s = manager.get_stats()
        assert s['active'] == 2
        assert s['widgets'] == 2


class TestPrintStats:
    """`print_stats` is a logging convenience — smoke test."""

    def test_print_stats_does_not_crash_empty(self, manager):
        manager.print_stats()  # must not raise

    def test_print_stats_does_not_crash_populated(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="test")
        manager.print_stats()


# =============================================================================
# 6.  list_connections() and verify_cleanup()
# =============================================================================

class TestListConnections:
    """`list_connections` returns one string per tracked connection."""

    def test_empty_list(self, manager):
        assert manager.list_connections() == []

    def test_lists_with_track_as_label(self, manager, emitter):
        def my_slot(): pass
        manager.connect(emitter, emitter.triggered, my_slot,
                        track_as="my_label")
        items = manager.list_connections()
        assert len(items) == 1
        assert "my_label" in items[0]
        assert "my_slot" in items[0]

    def test_lists_without_track_as_uses_widget_id(self, manager, emitter):
        def my_slot(): pass
        manager.connect(emitter, emitter.triggered, my_slot)
        items = manager.list_connections()
        assert len(items) == 1
        # No label → uses "widget_<id>"
        assert "widget_" in items[0]

    def test_lists_lambda_slot(self, manager, emitter):
        # lambda has __name__ = '<lambda>'
        manager.connect(emitter, emitter.triggered, lambda: None)
        items = manager.list_connections()
        assert len(items) == 1

    def test_lists_multiple_connections(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="a")
        manager.connect(emitter, emitter.value_changed, lambda v: None,
                        track_as="b")
        items = manager.list_connections()
        assert len(items) == 2


class TestVerifyCleanup:
    """`verify_cleanup` returns True when no connections remain."""

    def test_returns_true_when_clean(self, manager):
        assert manager.verify_cleanup() is True

    def test_returns_false_when_dirty(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None,
                        track_as="leaked")
        assert manager.verify_cleanup() is False

    def test_returns_true_after_full_cleanup(self, manager, emitter):
        manager.connect(emitter, emitter.triggered, lambda: None)
        manager.disconnect_all(quiet=True)
        assert manager.verify_cleanup() is True


# =============================================================================
# 7.  SignalMixin
# =============================================================================

class TestSignalMixin:
    """`SignalMixin` adds tracked-signal helpers to any QObject."""

    def test_init_creates_signal_manager(self, qtbot):
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        obj.init_signal_tracking()
        assert isinstance(obj._signal_manager, SignalConnectionManager)

    def test_init_is_idempotent(self, qtbot):
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        obj.init_signal_tracking()
        first = obj._signal_manager
        obj.init_signal_tracking()  # again — should NOT replace
        assert obj._signal_manager is first

    def test_track_connection_auto_initializes(self, qtbot):
        # If init_signal_tracking wasn't called, track_connection should
        # call it lazily
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        # Don't call init_signal_tracking explicitly
        obj.track_connection(obj, obj.triggered, lambda: None,
                             label="auto")
        assert hasattr(obj, "_signal_manager")
        assert obj._signal_manager.get_connection_count() == 1

    def test_track_connection_wires_signal(self, qtbot):
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        obj.init_signal_tracking()
        calls = []
        obj.track_connection(obj, obj.triggered,
                             lambda: calls.append(1))
        obj.triggered.emit()
        assert calls == [1]

    def test_cleanup_signals_disconnects_all(self, qtbot):
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        obj.init_signal_tracking()
        calls = []
        obj.track_connection(obj, obj.triggered,
                             lambda: calls.append(1))
        obj.cleanup_signals()
        obj.triggered.emit()
        assert calls == []  # signal disconnected

    def test_cleanup_signals_safe_without_init(self, qtbot):
        # If init_signal_tracking was never called, cleanup is a no-op
        class Mixed(_Emitter, SignalMixin):
            pass
        obj = Mixed()
        obj.cleanup_signals()  # must not raise


# =============================================================================
# 8.  Module-level singleton helpers
# =============================================================================

class TestSingleton:
    """`get_signal_manager` is a lazy-init singleton; `reset_signal_manager`
    clears it."""

    def test_first_call_creates_instance(self):
        # autouse fixture clears between tests, so this is a fresh state
        m = get_signal_manager()
        assert isinstance(m, SignalConnectionManager)

    def test_subsequent_calls_return_same_instance(self):
        m1 = get_signal_manager()
        m2 = get_signal_manager()
        assert m1 is m2

    def test_reset_nulls_singleton(self):
        m1 = get_signal_manager()
        reset_signal_manager()
        m2 = get_signal_manager()
        # After reset, a new instance is created
        assert m2 is not m1

    def test_reset_disconnects_existing_connections(self, qtbot):
        m = get_signal_manager()
        e = _Emitter()
        calls = []
        m.connect(e, e.triggered, lambda: calls.append(1))
        reset_signal_manager()
        e.triggered.emit()
        assert calls == []  # reset performed disconnect_all

    def test_reset_when_singleton_is_none_is_safe(self):
        # Force singleton to None first
        reset_signal_manager()
        # Call again — must not crash
        reset_signal_manager()
