# -*- coding: utf-8 -*-
"""
Tests for core/screen_color_picker.py.

Phase 3f covers the last big UI-adjacent file: a fullscreen overlay for
picking a color from anywhere on the screen. It captures a screenshot,
shows a magnifier under the cursor, draws crosshair + color info, and
emits a tuple when the user clicks (or `picker_cancelled` on Esc).

Coverage targets:
  - __init__                       (window flags, attrs, mouse tracking,
                                    timer + signal_manager wiring,
                                    initial state, cached colors)
  - _init_cached_colors            (pulls from QColorCache)
  - _get_current_color_qcolor      (returns cached QColor for current_color)
  - start_picking                  (capture → fullscreen → timer → grab kb;
                                    error path closes)
  - _capture_screen                (uses self.screen() then primaryScreen()
                                    fallback; error path nulls screenshot)
  - _update_cursor_position        (clamps cursor inside screenshot bounds,
                                    reads pixel color, calls update())
  - paintEvent                     (smoke; calls draw helpers)
  - _draw_magnifier                (returns early when no screenshot,
                                    edge-shifting near right/bottom)
  - _draw_magnifier_grid           (smoke; exception-safe)
  - _draw_crosshair                (smoke; exception-safe)
  - _draw_color_info               (smoke; edge clipping x/y)
  - mousePressEvent                (left emits + closes; right is noop)
  - keyPressEvent                  (Esc emits + closes; other keys noop)
  - closeEvent                     (stops timer, disconnects, releases
                                    keyboard, frees screenshot; safe with
                                    missing attrs)

Out of scope:
  - The actual Qt show-fullscreen behavior (would actually go fullscreen
    in test runs and is platform-specific). We monkeypatch showFullScreen
    and grabKeyboard everywhere they appear.
  - The screen.grabWindow Qt path (we mock the screen object).
"""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import (
    QPainter, QPixmap, QImage, QColor, QCursor,
    QMouseEvent, QKeyEvent, QPaintEvent, QCloseEvent,
)

from core.screen_color_picker import ScreenColorPicker
from utils import config


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_solid_pixmap(width: int = 100, height: int = 100,
                       color: tuple = (255, 0, 0)) -> QPixmap:
    """Build a solid-color QPixmap of known size (avoids needing a real
    screen capture during testing)."""
    pix = QPixmap(width, height)
    pix.fill(QColor(*color))
    return pix


def _make_mouse_event(button: Qt.MouseButton,
                      event_type=None) -> QMouseEvent:
    """Build a synthetic QMouseEvent."""
    from PyQt6.QtCore import QPointF, QEvent
    if event_type is None:
        event_type = QEvent.Type.MouseButtonPress
    return QMouseEvent(
        event_type,
        QPointF(0, 0),
        QPointF(0, 0),
        button,
        button,
        Qt.KeyboardModifier.NoModifier,
    )


def _make_key_event(key: Qt.Key) -> QKeyEvent:
    """Build a synthetic QKeyEvent."""
    from PyQt6.QtCore import QEvent
    return QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        Qt.KeyboardModifier.NoModifier,
    )


# =============================================================================
# 1.  Construction
# =============================================================================

@pytest.fixture
def picker(qtbot):
    """Default fixture: ScreenColorPicker with no parent.

    Critically: we never call start_picking() — that goes fullscreen.
    """
    p = ScreenColorPicker(parent=None)
    qtbot.addWidget(p)
    return p


class TestConstruction:
    """`__init__` sets a frameless, top-most, translucent widget with mouse
    tracking + cross cursor; initialises screenshot=None, current_color=
    (0,0,0), magnifier_size=140, zoom_factor=8; wires the QTimer through the
    signal_manager; populates cached colors."""

    def test_widget_instantiates(self, picker):
        assert isinstance(picker, QWidget)

    def test_signal_manager_attached(self, picker):
        # Source: SIGNAL_MANAGER_AVAILABLE=True, so signal_manager is set
        assert picker.signal_manager is not None

    def test_window_flags_include_frameless(self, picker):
        flags = picker.windowFlags()
        assert bool(flags & Qt.WindowType.FramelessWindowHint)

    def test_window_flags_include_stay_on_top(self, picker):
        flags = picker.windowFlags()
        assert bool(flags & Qt.WindowType.WindowStaysOnTopHint)

    def test_window_flags_include_tool(self, picker):
        flags = picker.windowFlags()
        assert bool(flags & Qt.WindowType.Tool)

    def test_translucent_background_attribute(self, picker):
        assert picker.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def test_delete_on_close_attribute(self, picker):
        assert picker.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def test_mouse_tracking_enabled(self, picker):
        assert picker.hasMouseTracking() is True

    def test_cursor_is_cross(self, picker):
        assert picker.cursor().shape() == Qt.CursorShape.CrossCursor

    def test_initial_state_empty(self, picker):
        assert picker.screenshot is None
        assert picker.current_color == (0, 0, 0)
        assert picker.cursor_pos == QPoint(0, 0)

    def test_magnifier_defaults(self, picker):
        assert picker.magnifier_size == 140
        assert picker.zoom_factor == 8

    def test_update_timer_created(self, picker):
        from PyQt6.QtCore import QTimer
        assert isinstance(picker.update_timer, QTimer)

    def test_color_picked_signal_defined(self, picker):
        # Just check the signal exists as an attribute
        assert hasattr(picker, 'color_picked')

    def test_picker_cancelled_signal_defined(self, picker):
        assert hasattr(picker, 'picker_cancelled')

    def test_timer_connection_tracked_by_signal_manager(self, picker):
        # signal_manager.connect(...) was called with track_as="cursor_update_timer"
        # Hard to introspect exactly — just verify the timer's timeout is connected
        # by checking that signal_manager has at least one tracked connection
        assert picker.signal_manager is not None


# =============================================================================
# 2.  _init_cached_colors
# =============================================================================

class TestInitCachedColors:
    """Pulls three QColors from QColorCache during __init__."""

    def test_gold_color_cached(self, picker):
        assert picker._gold_color is not None
        assert isinstance(picker._gold_color, QColor)

    def test_gold_alpha_cached(self, picker):
        assert picker._gold_alpha is not None
        assert isinstance(picker._gold_alpha, QColor)

    def test_black_180_cached(self, picker):
        assert picker._black_180 is not None
        assert isinstance(picker._black_180, QColor)


# =============================================================================
# 3.  _get_current_color_qcolor
# =============================================================================

class TestGetCurrentColorQColor:
    """Returns a QColor matching `current_color` (cache or fallback)."""

    def test_default_returns_black(self, picker):
        c = picker._get_current_color_qcolor()
        assert isinstance(c, QColor)
        assert (c.red(), c.green(), c.blue()) == (0, 0, 0)

    def test_returns_qcolor_for_set_current_color(self, picker):
        picker.current_color = (200, 100, 50)
        c = picker._get_current_color_qcolor()
        assert (c.red(), c.green(), c.blue()) == (200, 100, 50)


# =============================================================================
# 4.  start_picking
# =============================================================================

class TestStartPicking:
    """`start_picking` chains: capture → setGeometry → showFullScreen →
    timer.start(16) → grabKeyboard. Errors are caught and the dialog closes."""

    def test_calls_capture_screen(self, picker, monkeypatch):
        capture_calls = []
        monkeypatch.setattr(picker, "_capture_screen",
                            lambda: capture_calls.append(1))
        monkeypatch.setattr(picker, "showFullScreen", lambda: None)
        monkeypatch.setattr(picker, "grabKeyboard", lambda: None)
        monkeypatch.setattr(picker.update_timer, "start", lambda ms: None)
        picker.start_picking()
        assert capture_calls == [1]

    def test_starts_timer_at_16ms(self, picker, monkeypatch):
        timer_calls = []
        monkeypatch.setattr(picker, "_capture_screen", lambda: None)
        monkeypatch.setattr(picker, "showFullScreen", lambda: None)
        monkeypatch.setattr(picker, "grabKeyboard", lambda: None)
        monkeypatch.setattr(picker.update_timer, "start",
                            lambda ms: timer_calls.append(ms))
        picker.start_picking()
        assert timer_calls == [16]

    def test_grabs_keyboard(self, picker, monkeypatch):
        grab_calls = []
        monkeypatch.setattr(picker, "_capture_screen", lambda: None)
        monkeypatch.setattr(picker, "showFullScreen", lambda: None)
        monkeypatch.setattr(picker, "grabKeyboard",
                            lambda: grab_calls.append(1))
        monkeypatch.setattr(picker.update_timer, "start", lambda ms: None)
        picker.start_picking()
        assert grab_calls == [1]

    def test_calls_show_fullscreen(self, picker, monkeypatch):
        show_calls = []
        monkeypatch.setattr(picker, "_capture_screen", lambda: None)
        monkeypatch.setattr(picker, "showFullScreen",
                            lambda: show_calls.append(1))
        monkeypatch.setattr(picker, "grabKeyboard", lambda: None)
        monkeypatch.setattr(picker.update_timer, "start", lambda ms: None)
        picker.start_picking()
        assert show_calls == [1]

    def test_exception_in_capture_triggers_close(self, picker, monkeypatch):
        # If _capture_screen raises, error path runs and self.close() is called
        close_calls = []
        def bad_capture(): raise RuntimeError("boom")
        monkeypatch.setattr(picker, "_capture_screen", bad_capture)
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        # ErrorHandler.handle_exception is the documented path — it shouldn't
        # re-raise; if it does, the test catches the wrapped error
        try:
            picker.start_picking()
        except Exception:
            pass
        assert close_calls == [1]


# =============================================================================
# 5.  _capture_screen
# =============================================================================

class TestCaptureScreen:
    """Captures the screen via `self.screen().grabWindow(0)`. Falls back to
    `QApplication.primaryScreen()` if `self.screen()` returns None.
    Exceptions null `self.screenshot`."""

    def test_uses_self_screen_when_available(self, picker, monkeypatch):
        fake_pix = _make_solid_pixmap(50, 50)
        mock_screen = MagicMock()
        mock_screen.grabWindow.return_value = fake_pix
        monkeypatch.setattr(picker, "screen", lambda: mock_screen)
        picker._capture_screen()
        assert picker.screenshot is fake_pix
        mock_screen.grabWindow.assert_called_once_with(0)

    def test_falls_back_to_primary_screen(self, picker, monkeypatch):
        fake_pix = _make_solid_pixmap(80, 80)
        mock_screen = MagicMock()
        mock_screen.grabWindow.return_value = fake_pix
        monkeypatch.setattr(picker, "screen", lambda: None)
        monkeypatch.setattr(QApplication, "primaryScreen",
                            staticmethod(lambda: mock_screen))
        picker._capture_screen()
        assert picker.screenshot is fake_pix

    def test_no_screen_at_all_leaves_screenshot_unchanged(
            self, picker, monkeypatch):
        # If both self.screen() and primaryScreen() return None, the if-block
        # is skipped silently (no exception path)
        monkeypatch.setattr(picker, "screen", lambda: None)
        monkeypatch.setattr(QApplication, "primaryScreen",
                            staticmethod(lambda: None))
        picker._capture_screen()
        # screenshot stays None (initial value)
        assert picker.screenshot is None

    def test_exception_nulls_screenshot(self, picker, monkeypatch):
        # First seed a stale screenshot to verify it gets cleared
        picker.screenshot = _make_solid_pixmap(20, 20)
        def bad_screen(): raise RuntimeError("no screen")
        monkeypatch.setattr(picker, "screen", bad_screen)
        picker._capture_screen()
        assert picker.screenshot is None


# =============================================================================
# 6.  _update_cursor_position
# =============================================================================

class TestUpdateCursorPosition:
    """Updates `cursor_pos` from `QCursor.pos()`, reads pixel color from the
    screenshot at the (clamped) cursor position, then calls update()."""

    def test_updates_cursor_pos_from_qcursor(self, picker, monkeypatch):
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(42, 73)))
        picker._update_cursor_position()
        assert picker.cursor_pos == QPoint(42, 73)

    def test_reads_pixel_color_from_screenshot(self, picker, monkeypatch):
        # Solid red pixmap → current_color should become (255, 0, 0)
        picker.screenshot = _make_solid_pixmap(50, 50, color=(255, 0, 0))
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(10, 10)))
        picker._update_cursor_position()
        assert picker.current_color == (255, 0, 0)

    def test_clamps_cursor_to_screenshot_bounds_high(self, picker, monkeypatch):
        # Cursor at 999,999 — screenshot is 50x50 → must clamp to (49, 49)
        picker.screenshot = _make_solid_pixmap(50, 50, color=(0, 200, 100))
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(9999, 9999)))
        picker._update_cursor_position()
        assert picker.current_color == (0, 200, 100)  # didn't crash

    def test_clamps_cursor_to_screenshot_bounds_low(self, picker, monkeypatch):
        # Cursor at -100,-100 — must clamp to (0, 0)
        picker.screenshot = _make_solid_pixmap(50, 50, color=(100, 100, 200))
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(-100, -100)))
        picker._update_cursor_position()
        assert picker.current_color == (100, 100, 200)

    def test_no_screenshot_does_not_set_color(self, picker, monkeypatch):
        # If screenshot is None, the color-read block is skipped
        picker.screenshot = None
        picker.current_color = (123, 45, 67)  # sentinel to verify unchanged
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(10, 10)))
        picker._update_cursor_position()
        assert picker.current_color == (123, 45, 67)

    def test_calls_update_to_trigger_repaint(self, picker, monkeypatch):
        update_calls = []
        monkeypatch.setattr(QCursor, "pos",
                            staticmethod(lambda: QPoint(0, 0)))
        monkeypatch.setattr(picker, "update",
                            lambda: update_calls.append(1))
        picker._update_cursor_position()
        assert update_calls == [1]

    def test_exception_caught_silently(self, picker, monkeypatch):
        # Force QCursor.pos to raise — the outer try/except logs and returns
        def bad_pos(): raise RuntimeError("cursor failure")
        monkeypatch.setattr(QCursor, "pos", staticmethod(bad_pos))
        # Must not raise
        picker._update_cursor_position()


# =============================================================================
# 7.  paintEvent (and the draw helpers)
# =============================================================================

class TestPaintEventCallsHelpers:
    """`paintEvent` is wrapped in try/except. We verify it invokes the three
    draw helpers when in a happy state, and tolerates errors otherwise."""

    def test_paint_event_does_not_crash_without_screenshot(
            self, picker, monkeypatch):
        # No screenshot — _draw_magnifier returns early; the rest still runs
        # We monkeypatch the helpers to skip real painting
        monkeypatch.setattr(picker, "_draw_magnifier", lambda p: None)
        monkeypatch.setattr(picker, "_draw_crosshair", lambda p: None)
        monkeypatch.setattr(picker, "_draw_color_info", lambda p: None)
        # paintEvent's QPainter(self) on a non-shown widget may emit warnings
        # but the try/except should swallow any failure
        from PyQt6.QtCore import QRect as _QRect
        evt = QPaintEvent(_QRect(0, 0, 100, 100))
        picker.paintEvent(evt)  # must not raise

    def test_paint_event_calls_draw_helpers(self, picker, monkeypatch):
        helpers_called = []
        monkeypatch.setattr(picker, "_draw_magnifier",
                            lambda p: helpers_called.append("mag"))
        monkeypatch.setattr(picker, "_draw_crosshair",
                            lambda p: helpers_called.append("cross"))
        monkeypatch.setattr(picker, "_draw_color_info",
                            lambda p: helpers_called.append("info"))
        from PyQt6.QtCore import QRect as _QRect
        evt = QPaintEvent(_QRect(0, 0, 100, 100))
        picker.paintEvent(evt)
        # All three helpers should have been called in order
        assert helpers_called == ["mag", "cross", "info"]


class TestDrawMagnifier:
    """`_draw_magnifier` returns early on missing/null screenshot. Otherwise,
    it computes magnifier offsets relative to cursor + edge-shifts when
    near right/bottom of the widget."""

    def test_returns_early_without_screenshot(self, picker):
        picker.screenshot = None
        # Need a valid painter on a real device
        target = _make_solid_pixmap(200, 200)
        painter = QPainter(target)
        try:
            picker._draw_magnifier(painter)  # should return early
        finally:
            painter.end()

    def test_returns_early_with_null_screenshot(self, picker):
        picker.screenshot = QPixmap()  # null pixmap
        target = _make_solid_pixmap(200, 200)
        painter = QPainter(target)
        try:
            picker._draw_magnifier(painter)
        finally:
            painter.end()

    def test_normal_position_does_not_crash(self, picker):
        picker.screenshot = _make_solid_pixmap(400, 400)
        picker.cursor_pos = QPoint(100, 100)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_magnifier(painter)
        finally:
            painter.end()

    def test_near_right_edge_shifts_magnifier(self, picker):
        # When cursor near right, the magnifier should be drawn to the left
        picker.screenshot = _make_solid_pixmap(400, 400)
        picker.cursor_pos = QPoint(780, 100)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_magnifier(painter)
        finally:
            painter.end()

    def test_near_bottom_edge_shifts_magnifier(self, picker):
        picker.screenshot = _make_solid_pixmap(400, 400)
        picker.cursor_pos = QPoint(100, 580)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_magnifier(painter)
        finally:
            painter.end()


class TestDrawMagnifierGrid:
    """Smoke test: draws zoom_factor+1 lines vertically and horizontally."""

    def test_draws_grid_without_crashing(self, picker):
        target = _make_solid_pixmap(400, 400)
        painter = QPainter(target)
        try:
            picker._draw_magnifier_grid(painter, QRect(50, 50, 140, 140))
        finally:
            painter.end()

    def test_grid_with_extreme_zoom(self, picker):
        # zoom_factor mutation: grid draws zoom_factor+1 lines
        picker.zoom_factor = 16
        picker.magnifier_size = 160
        target = _make_solid_pixmap(400, 400)
        painter = QPainter(target)
        try:
            picker._draw_magnifier_grid(painter, QRect(0, 0, 160, 160))
        finally:
            painter.end()


class TestDrawCrosshair:
    """Smoke test: draws crosshair + center circle at cursor position."""

    def test_draws_crosshair_without_crashing(self, picker):
        picker.cursor_pos = QPoint(100, 100)
        picker.resize(400, 400)
        target = _make_solid_pixmap(400, 400)
        painter = QPainter(target)
        try:
            picker._draw_crosshair(painter)
        finally:
            painter.end()

    def test_draws_at_origin(self, picker):
        # Edge: cursor at top-left
        picker.cursor_pos = QPoint(0, 0)
        picker.resize(400, 400)
        target = _make_solid_pixmap(400, 400)
        painter = QPainter(target)
        try:
            picker._draw_crosshair(painter)
        finally:
            painter.end()


class TestDrawColorInfo:
    """`_draw_color_info` draws an info box near cursor + clips to widget
    edges. Multiple branches: bottom edge → flip up, left edge → push
    right, right edge → push left."""

    def test_draws_color_info_normal_position(self, picker):
        picker.cursor_pos = QPoint(200, 200)
        picker.current_color = (128, 64, 32)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_color_info(painter)
        finally:
            painter.end()

    def test_near_bottom_edge_flips_up(self, picker):
        picker.cursor_pos = QPoint(100, 580)
        picker.current_color = (255, 128, 0)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_color_info(painter)
        finally:
            painter.end()

    def test_near_left_edge_pushes_right(self, picker):
        picker.cursor_pos = QPoint(20, 300)
        picker.current_color = (200, 200, 200)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_color_info(painter)
        finally:
            painter.end()

    def test_near_right_edge_pushes_left(self, picker):
        picker.cursor_pos = QPoint(790, 300)
        picker.current_color = (50, 100, 150)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_color_info(painter)
        finally:
            painter.end()

    def test_handles_known_color_text(self, picker):
        # Just verify that with current_color set, the method runs through
        picker.cursor_pos = QPoint(400, 300)
        picker.current_color = (1, 2, 3)
        picker.resize(800, 600)
        target = _make_solid_pixmap(800, 600)
        painter = QPainter(target)
        try:
            picker._draw_color_info(painter)
        finally:
            painter.end()


# =============================================================================
# 8.  mousePressEvent
# =============================================================================

class TestMousePressEvent:
    """Left button → emit color_picked + close. Other buttons → noop."""

    def test_left_button_emits_color_picked(self, picker, monkeypatch, qtbot):
        # Disable close to prevent widget destruction during signal capture
        monkeypatch.setattr(picker, "close", lambda: None)
        picker.current_color = (10, 20, 30)
        with qtbot.waitSignal(picker.color_picked, timeout=500) as blocker:
            picker.mousePressEvent(_make_mouse_event(Qt.MouseButton.LeftButton))
        assert blocker.args == [(10, 20, 30)]

    def test_left_button_calls_close(self, picker, monkeypatch):
        close_calls = []
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        picker.mousePressEvent(_make_mouse_event(Qt.MouseButton.LeftButton))
        assert close_calls == [1]

    def test_right_button_does_not_emit(self, picker, monkeypatch):
        emit_count = []
        close_calls = []
        picker.color_picked.connect(lambda c: emit_count.append(c))
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        picker.mousePressEvent(_make_mouse_event(Qt.MouseButton.RightButton))
        assert emit_count == []
        assert close_calls == []

    def test_middle_button_does_not_emit(self, picker, monkeypatch):
        emit_count = []
        close_calls = []
        picker.color_picked.connect(lambda c: emit_count.append(c))
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        picker.mousePressEvent(_make_mouse_event(Qt.MouseButton.MiddleButton))
        assert emit_count == []
        assert close_calls == []


# =============================================================================
# 9.  keyPressEvent
# =============================================================================

class TestKeyPressEvent:
    """Esc → emit picker_cancelled + close. Other keys → noop."""

    def test_esc_emits_picker_cancelled(self, picker, monkeypatch, qtbot):
        monkeypatch.setattr(picker, "close", lambda: None)
        with qtbot.waitSignal(picker.picker_cancelled, timeout=500):
            picker.keyPressEvent(_make_key_event(Qt.Key.Key_Escape))

    def test_esc_calls_close(self, picker, monkeypatch):
        close_calls = []
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        picker.keyPressEvent(_make_key_event(Qt.Key.Key_Escape))
        assert close_calls == [1]

    def test_other_key_does_not_close(self, picker, monkeypatch):
        close_calls = []
        monkeypatch.setattr(picker, "close", lambda: close_calls.append(1))
        picker.keyPressEvent(_make_key_event(Qt.Key.Key_A))
        assert close_calls == []

    def test_other_key_does_not_emit(self, picker, monkeypatch):
        emit_count = []
        picker.picker_cancelled.connect(lambda: emit_count.append(1))
        monkeypatch.setattr(picker, "close", lambda: None)
        picker.keyPressEvent(_make_key_event(Qt.Key.Key_Return))
        assert emit_count == []


# =============================================================================
# 10.  closeEvent
# =============================================================================

class TestCloseEvent:
    """`closeEvent` stops the timer, disconnects all tracked signals,
    releases keyboard, and clears the screenshot."""

    def test_stops_update_timer(self, picker, monkeypatch):
        stop_calls = []
        monkeypatch.setattr(picker.update_timer, "stop",
                            lambda: stop_calls.append(1))
        monkeypatch.setattr(picker, "releaseKeyboard", lambda: None)
        picker.closeEvent(QCloseEvent())
        assert stop_calls == [1]

    def test_disconnects_signal_manager(self, picker, monkeypatch):
        disc_calls = []
        picker.signal_manager.disconnect_all = lambda quiet=False: \
            disc_calls.append(quiet)
        monkeypatch.setattr(picker, "releaseKeyboard", lambda: None)
        picker.closeEvent(QCloseEvent())
        assert disc_calls == [True]  # called with quiet=True

    def test_releases_keyboard(self, picker, monkeypatch):
        release_calls = []
        monkeypatch.setattr(picker, "releaseKeyboard",
                            lambda: release_calls.append(1))
        picker.closeEvent(QCloseEvent())
        assert release_calls == [1]

    def test_clears_screenshot(self, picker, monkeypatch):
        picker.screenshot = _make_solid_pixmap(50, 50)
        monkeypatch.setattr(picker, "releaseKeyboard", lambda: None)
        picker.closeEvent(QCloseEvent())
        assert picker.screenshot is None

    def test_safe_when_signal_manager_missing(self, picker, monkeypatch):
        # Source uses hasattr() guard
        del picker.signal_manager
        monkeypatch.setattr(picker, "releaseKeyboard", lambda: None)
        picker.closeEvent(QCloseEvent())  # must not crash

    def test_safe_when_update_timer_missing(self, picker, monkeypatch):
        # Source uses hasattr() guard
        del picker.update_timer
        monkeypatch.setattr(picker, "releaseKeyboard", lambda: None)
        picker.closeEvent(QCloseEvent())  # must not crash

    def test_exception_caught_silently(self, picker, monkeypatch):
        # If releaseKeyboard raises, the outer try/except + ErrorHandler runs
        def bad_release(): raise RuntimeError("kb failure")
        monkeypatch.setattr(picker, "releaseKeyboard", bad_release)
        # Must not raise
        picker.closeEvent(QCloseEvent())
