# -*- coding: utf-8 -*-
"""
Tests for ui/image_button.py and ui/image_viewer.py.

Phase 3d covers two sibling UI files together because they have similar shape:
small classes, mouse-event handlers, theme_manager integration, and modest
optional pixmap state. Both currently sit at 11-12% coverage.

Coverage targets:
  - ImageButton.__init__               (state init, image preload, font, cursor)
  - ImageButton._get_button_images     (file-name fallback chain)
  - ImageButton.update_height_for_window (piecewise-linear height interpolation)
  - ImageButton.setIcon                (icon storage + repaint)
  - ImageButton.paintEvent             (image-mode paint vs super delegation)
  - ImageButton.enter/leave/press/release/moveEvent (theme-conditional update)
  - ImageButton.set_theme_manager + apply_style (stylesheet branches)

  - ImageViewer.__init__               (render hints, signal_manager, state)
  - ImageViewer.show_context_menu      (theme stylesheet, conditional items)
  - ImageViewer.toggle_zoom_lock       (state flip + viewport.update)
  - ImageViewer.paintEvent             (zoom-lock border drawing)
  - ImageViewer.mousePressEvent        (left-button selection start)
  - ImageViewer.mouseMoveEvent         (selection rect creation/update)
  - ImageViewer.mouseReleaseEvent      (selection completion + parent callback)
  - ImageViewer.mouseDoubleClickEvent  (single-pixel color pick)

Out of scope:
  - The image-file-found loading paths (lines 68-76 of image_button.py) —
    these depend on resources/button_images/*.png existing. The default
    fixture monkeypatches os.path.exists to False so loading is deterministic.
    Image-mode paint tests inject _base_pixmap manually instead.
"""

import os
import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QMenu, QWidget,
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QEvent, QRectF
from PyQt6.QtGui import (
    QIcon, QPixmap, QMouseEvent, QPaintEvent, QEnterEvent,
)

from ui.image_button import ImageButton
from ui.image_viewer import ImageViewer
from utils import config


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_theme_manager(theme_name: str = "dark", is_image_mode: bool = False):
    """Build a MagicMock theme_manager with controllable theme + mode."""
    tm = MagicMock()
    tm.current_theme = theme_name
    tm.is_image_mode = MagicMock(return_value=is_image_mode)
    tm.get_current_theme = MagicMock(
        return_value=config.DARK_THEME_COLORS if theme_name == "dark"
        else config.LIGHT_THEME_COLORS
    )
    return tm


def _make_left_mouse_event(event_type, x: float, y: float,
                           button: Qt.MouseButton = Qt.MouseButton.LeftButton):
    """Construct a QMouseEvent for unit-testing event handlers directly."""
    pos = QPointF(x, y)
    return QMouseEvent(
        event_type,
        pos,                # localPos (also used as windowPos in this overload)
        button,             # button
        button,             # buttons
        Qt.KeyboardModifier.NoModifier,
    )


# =============================================================================
# ImageButton TESTS
# =============================================================================

@pytest.fixture
def button(qtbot, monkeypatch):
    """Default fixture: ImageButton with no images on disk, no theme_manager.

    `os.path.exists` is forced to False so all three pixmaps stay None. Tests
    that need image-mode rendering inject `_base_pixmap` manually after
    construction.
    """
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    btn = ImageButton(text="Test", button_name="upload", parent=None)
    qtbot.addWidget(btn)
    return btn


class TestImageButtonConstruction:
    """`__init__` sets up button text, name, image cache slots, font, cursor,
    and dynamic height range. All optional pixmaps default to None when the
    image files don't exist on disk."""

    def test_button_instantiates_as_qpushbutton(self, button):
        assert isinstance(button, QPushButton)

    def test_text_stored(self, button):
        assert button.button_text == "Test"
        assert button.text() == "Test"

    def test_button_name_stored(self, button):
        assert button.button_name == "upload"

    def test_default_no_theme_manager(self, button):
        assert button.theme_manager is None

    def test_always_use_image_default_false(self, button):
        assert button.always_use_image is False

    def test_pixmap_slots_none_when_no_files(self, button):
        # Default fixture forces os.path.exists=False → no pixmaps load
        assert button._base_pixmap is None
        assert button._hover_pixmap is None
        assert button._pressed_pixmap is None

    def test_font_is_bold(self, button):
        assert button.font().bold() is True

    def test_cursor_is_pointing_hand(self, button):
        assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_dynamic_height_range_from_config(self, button):
        assert button.base_height == config.BUTTON_HEIGHT_MIN
        assert button.max_height == config.BUTTON_HEIGHT_MAX
        assert button.min_window_width == config.WINDOW_WIDTH_MIN
        assert button.max_window_width == config.WINDOW_WIDTH_MAX

    def test_minimum_height_set_to_base(self, button):
        assert button.minimumHeight() == config.BUTTON_HEIGHT_MIN

    def test_mouse_tracking_enabled(self, button):
        assert button.hasMouseTracking() is True

    def test_always_use_image_true(self, qtbot, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        btn = ImageButton(text="X", button_name="x", parent=None,
                          always_use_image=True)
        qtbot.addWidget(btn)
        assert btn.always_use_image is True


class TestGetButtonImages:
    """`_get_button_images` searches BUTTON_IMAGES_DIR with multiple naming
    conventions. Returns (base, hover, pressed) — None for missing files,
    with hover/pressed falling back to base when not found."""

    def test_all_none_when_no_files_exist(self, button):
        # Default fixture — os.path.exists is False
        result = button._get_button_images("nonexistent_button")
        assert result == (None, None, None)

    def test_finds_underscore_naming(self, qtbot, monkeypatch):
        # Simulate: only "upload_base.png" exists. find_image tries
        # f"{prefix}_{suffix}.png" first.
        def fake_exists(p):
            return p.endswith("upload_base.png")
        monkeypatch.setattr(os.path, "exists", fake_exists)
        btn = ImageButton(text="", button_name="upload", parent=None)
        qtbot.addWidget(btn)
        # base found; hover/pressed not found → both fall back to base
        assert btn.base_img is not None
        assert btn.base_img.endswith("upload_base.png")
        assert btn.hover_img == btn.base_img
        assert btn.pressed_img == btn.base_img

    def test_finds_dash_naming_fallback(self, qtbot, monkeypatch):
        # Source replaces underscores with dashes as second attempt
        def fake_exists(p):
            return "screen-pick" in p and p.endswith("_base.png")
        monkeypatch.setattr(os.path, "exists", fake_exists)
        btn = ImageButton(text="", button_name="screen_pick", parent=None)
        qtbot.addWidget(btn)
        assert btn.base_img is not None
        assert "screen-pick" in btn.base_img

    def test_falls_back_to_bare_name_for_base_only(self, qtbot, monkeypatch):
        # If "{name}_base.png" not found, source tries plain "{name}.png"
        # (only for the "base" suffix)
        def fake_exists(p):
            # ONLY plain name without _base/_hover/_pressed exists
            return p.endswith("upload.png") and "upload_" not in p
        monkeypatch.setattr(os.path, "exists", fake_exists)
        btn = ImageButton(text="", button_name="upload", parent=None)
        qtbot.addWidget(btn)
        assert btn.base_img is not None
        assert btn.base_img.endswith("upload.png")

    def test_hover_and_pressed_fallback_to_base(self, qtbot, monkeypatch):
        # When only base exists, hover and pressed fall back to base
        def fake_exists(p):
            return p.endswith("upload_base.png")
        monkeypatch.setattr(os.path, "exists", fake_exists)
        btn = ImageButton(text="", button_name="upload", parent=None)
        qtbot.addWidget(btn)
        assert btn.hover_img == btn.base_img
        assert btn.pressed_img == btn.base_img

    def test_hover_pressed_distinct_when_present(self, qtbot, monkeypatch):
        # All three files exist with their own names
        def fake_exists(p):
            return any(p.endswith(suffix) for suffix in
                       ("_base.png", "_hover.png", "_pressed.png"))
        monkeypatch.setattr(os.path, "exists", fake_exists)
        btn = ImageButton(text="", button_name="upload", parent=None)
        qtbot.addWidget(btn)
        assert btn.base_img.endswith("upload_base.png")
        assert btn.hover_img.endswith("upload_hover.png")
        assert btn.pressed_img.endswith("upload_pressed.png")


class TestUpdateHeightForWindow:
    """`update_height_for_window` does piecewise-linear interpolation:
    below min_window_width → base_height, above max_window_width → max_height,
    in between → linear interpolation."""

    def test_below_min_uses_base_height(self, button):
        button.update_height_for_window(500)  # below WINDOW_WIDTH_MIN (1059)
        assert button.minimumHeight() == config.BUTTON_HEIGHT_MIN
        assert button.maximumHeight() == config.BUTTON_HEIGHT_MIN

    def test_at_min_uses_base_height(self, button):
        button.update_height_for_window(config.WINDOW_WIDTH_MIN)
        assert button.minimumHeight() == config.BUTTON_HEIGHT_MIN

    def test_above_max_uses_max_height(self, button):
        button.update_height_for_window(3000)  # above WINDOW_WIDTH_MAX (1920)
        assert button.minimumHeight() == config.BUTTON_HEIGHT_MAX
        assert button.maximumHeight() == config.BUTTON_HEIGHT_MAX

    def test_at_max_uses_max_height(self, button):
        button.update_height_for_window(config.WINDOW_WIDTH_MAX)
        assert button.minimumHeight() == config.BUTTON_HEIGHT_MAX

    def test_midpoint_interpolates(self, button):
        midpoint = (config.WINDOW_WIDTH_MIN + config.WINDOW_WIDTH_MAX) // 2
        expected_height = int(config.BUTTON_HEIGHT_MIN +
                              (config.BUTTON_HEIGHT_MAX - config.BUTTON_HEIGHT_MIN) * 0.5)
        button.update_height_for_window(midpoint)
        # Allow ±1 because of integer arithmetic in the source
        assert abs(button.minimumHeight() - expected_height) <= 1

    def test_height_min_equals_max_after_update(self, button):
        # Source sets both min and max equal — height is fixed after update
        button.update_height_for_window(1500)
        assert button.minimumHeight() == button.maximumHeight()


class TestSetIcon:
    """`setIcon` overrides QPushButton's to also store the icon on `_icon` for
    use by paintEvent."""

    def test_stores_icon_attribute(self, button):
        icon = QIcon(QPixmap(16, 16))
        button.setIcon(icon)
        assert button._icon is icon

    def test_calls_super_setIcon(self, button):
        # The super's icon should also be set so QPushButton renders it
        icon = QIcon(QPixmap(16, 16))
        button.setIcon(icon)
        assert button.icon() is not None
        assert not button.icon().isNull()


class TestPaintEvent:
    """`paintEvent` has a complex branch: only does custom image-mode painting
    when `use_image` is True AND `_base_pixmap` exists. Otherwise delegates to
    QPushButton's super().paintEvent."""

    def test_no_image_mode_falls_through_to_super(self, button):
        # No theme_manager + always_use_image=False → super paint, no crash
        button.show()
        button.repaint()  # forces a paintEvent
        # No assertion needed beyond "doesn't crash"

    def test_image_mode_with_base_pixmap_paints(self, qtbot, button):
        # Manually inject a real pixmap and force image mode
        button._base_pixmap = QPixmap(20, 20)
        button._base_pixmap.fill(Qt.GlobalColor.red)
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        button.show()
        # Should not crash when painting with image mode
        button.repaint()

    def test_image_mode_with_pressed_state(self, qtbot, button):
        # Set down state → uses pressed_pixmap if available
        button._base_pixmap = QPixmap(20, 20)
        button._base_pixmap.fill(Qt.GlobalColor.red)
        button._pressed_pixmap = QPixmap(20, 20)
        button._pressed_pixmap.fill(Qt.GlobalColor.blue)
        button._hover_pixmap = QPixmap(20, 20)
        button._hover_pixmap.fill(Qt.GlobalColor.green)
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        button.setDown(True)
        button.show()
        button.repaint()  # exercises pressed branch (cursor likely outside)

    def test_always_use_image_paints_even_without_theme_manager(self, qtbot, monkeypatch):
        # always_use_image=True bypasses the theme_manager check
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        btn = ImageButton(text="", button_name="x", parent=None,
                          always_use_image=True)
        qtbot.addWidget(btn)
        btn._base_pixmap = QPixmap(20, 20)
        btn._base_pixmap.fill(Qt.GlobalColor.cyan)
        btn.show()
        btn.repaint()  # should hit image-paint branch via always_use_image

    def test_paint_with_null_pixmap_falls_through(self, qtbot, button):
        # A null pixmap should NOT trigger custom paint (returns early via
        # `if current_pixmap and not current_pixmap.isNull()`)
        button._base_pixmap = QPixmap()  # null pixmap
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        button.show()
        button.repaint()  # falls through to super, no crash


class TestMouseEventHandlers:
    """All five mouse handlers (enter/leave/press/release/move) call
    `self.update()` only when image mode is active. They always call super."""

    def test_enter_event_updates_in_image_mode(self, button):
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        evt = QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5))
        # Doesn't crash — the slot calls self.update() which is async-safe
        button.enterEvent(evt)

    def test_enter_event_no_image_mode_no_crash(self, button):
        # No theme_manager → branch short-circuits, super still called
        evt = QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5))
        button.enterEvent(evt)

    def test_leave_event_updates_in_image_mode(self, button):
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        evt = QEvent(QEvent.Type.Leave)
        button.leaveEvent(evt)

    def test_leave_event_no_image_mode_no_crash(self, button):
        evt = QEvent(QEvent.Type.Leave)
        button.leaveEvent(evt)

    def test_mouse_press_in_image_mode(self, button):
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonPress, 5, 5)
        button.mousePressEvent(evt)

    def test_mouse_release_in_image_mode(self, button):
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 5, 5)
        button.mouseReleaseEvent(evt)

    def test_mouse_move_in_image_mode(self, button):
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        evt = _make_left_mouse_event(QEvent.Type.MouseMove, 5, 5,
                                     button=Qt.MouseButton.NoButton)
        button.mouseMoveEvent(evt)

    def test_mouse_move_no_theme_no_crash(self, button):
        # No theme_manager → branch skipped, super still called
        evt = _make_left_mouse_event(QEvent.Type.MouseMove, 5, 5,
                                     button=Qt.MouseButton.NoButton)
        button.mouseMoveEvent(evt)


class TestSetThemeManagerAndApplyStyle:
    """`set_theme_manager` stores the manager and calls `apply_style`. The
    style branches based on use_image_style and theme_manager presence."""

    def test_set_theme_manager_stores(self, button):
        tm = _make_theme_manager()
        button.set_theme_manager(tm)
        assert button.theme_manager is tm

    def test_set_theme_manager_calls_apply_style(self, button):
        tm = _make_theme_manager()
        button.set_theme_manager(tm)
        # apply_style was called → setStyleSheet should have been invoked
        # (we get a non-empty stylesheet for non-image mode)
        assert button.styleSheet() != ""

    def test_apply_style_no_theme_manager_returns_silently(self, button):
        # No theme_manager set → after clearing icon, returns
        button.theme_manager = None
        button._base_pixmap = None
        button.apply_style()  # must not raise

    def test_apply_style_dark_theme_sets_stylesheet(self, button):
        button.theme_manager = _make_theme_manager(theme_name="dark",
                                                   is_image_mode=False)
        button.apply_style()
        assert button.styleSheet() != ""

    def test_apply_style_image_mode_with_base_pixmap(self, button):
        # Image mode with base pixmap → minimal transparent stylesheet
        button._base_pixmap = QPixmap(10, 10)
        button.theme_manager = _make_theme_manager(is_image_mode=True)
        button.apply_style()
        # Source uses StylesheetCache.get_transparent_button_stylesheet()
        # We just verify it set SOMETHING
        assert button.styleSheet() != ""

    def test_apply_style_clears_icon_in_non_image_mode(self, button):
        # Set an icon first
        button.setIcon(QIcon(QPixmap(8, 8)))
        button.theme_manager = _make_theme_manager(is_image_mode=False)
        button.apply_style()
        # In non-image mode, setIcon(QIcon()) is called and _icon = None
        assert button._icon is None

    def test_apply_style_get_current_theme_returns_none(self, button):
        # If get_current_theme returns falsy, source returns early
        tm = _make_theme_manager(is_image_mode=False)
        tm.get_current_theme = MagicMock(return_value=None)
        button.theme_manager = tm
        button.apply_style()  # must not raise


# =============================================================================
# ImageViewer TESTS
# =============================================================================

@pytest.fixture
def viewer(qtbot):
    """Default fixture: ImageViewer with no parent_app, no scene."""
    v = ImageViewer(parent=None)
    qtbot.addWidget(v)
    return v


def _make_parent_app(theme_name: str = "dark", is_image_mode: bool = False,
                     image_loaded: bool = False, has_pixmap: bool = False):
    """Build a MagicMock parent_app for the viewer that quacks like
    ColorPickerApp — has theme_manager, image, pixmap_item, and the two
    callbacks `extract_colors_from_selection` and `pick_color_from_pixel`."""
    app = MagicMock()
    app.theme_manager = _make_theme_manager(theme_name, is_image_mode)
    app.image = MagicMock() if image_loaded else None
    app.pixmap_item = MagicMock() if has_pixmap else None
    app.extract_colors_from_selection = MagicMock()
    app.pick_color_from_pixel = MagicMock()
    app.clear_image = MagicMock()
    return app


class TestImageViewerConstruction:
    """`__init__` sets up render hints, signal manager, transformation/resize
    anchors, mouse tracking, and the no-drag mode. State starts empty."""

    def test_viewer_instantiates_as_qgraphicsview(self, viewer):
        assert isinstance(viewer, QGraphicsView)

    def test_signal_manager_attached(self, viewer):
        assert viewer.signal_manager is not None

    def test_initial_state_empty(self, viewer):
        assert viewer.selection_start is None
        assert viewer.selection_end is None
        assert viewer.selection_rect_item is None
        assert viewer.scene_ref is None
        assert viewer.dragging is False
        assert viewer.parent_app is None
        assert viewer.zoom_locked is False

    def test_drag_mode_is_no_drag(self, viewer):
        assert viewer.dragMode() == QGraphicsView.DragMode.NoDrag

    def test_mouse_tracking_enabled(self, viewer):
        assert viewer.hasMouseTracking() is True

    def test_context_menu_policy_is_custom(self, viewer):
        assert viewer.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


class TestToggleZoomLock:
    """`toggle_zoom_lock` is a simple state-flip with a viewport repaint."""

    def test_starts_unlocked(self, viewer):
        assert viewer.zoom_locked is False

    def test_toggle_locks(self, viewer):
        viewer.toggle_zoom_lock()
        assert viewer.zoom_locked is True

    def test_toggle_twice_returns_to_unlocked(self, viewer):
        viewer.toggle_zoom_lock()
        viewer.toggle_zoom_lock()
        assert viewer.zoom_locked is False


class TestPaintEvent:
    """`paintEvent` always calls super, then optionally draws a 4px lock
    border when `zoom_locked` is True."""

    def test_paint_unlocked_does_not_crash(self, viewer):
        viewer.show()
        viewer.repaint()

    def test_paint_locked_does_not_crash(self, viewer):
        viewer.zoom_locked = True
        viewer.show()
        viewer.repaint()

    def test_paint_locked_with_parent_app_uses_theme_accent(self, viewer):
        viewer.parent_app = _make_parent_app(theme_name="dark")
        viewer.zoom_locked = True
        viewer.show()
        viewer.repaint()
        # The paint code branches based on parent_app + theme_manager. We just
        # need to verify it doesn't crash and exercises the theme branch.

    def test_paint_locked_theme_returns_none(self, viewer):
        # If parent_app exists but get_current_theme returns falsy, code
        # falls through to BRAND_GOLD default.
        viewer.parent_app = _make_parent_app()
        viewer.parent_app.theme_manager.get_current_theme = MagicMock(return_value=None)
        viewer.zoom_locked = True
        viewer.show()
        viewer.repaint()


class TestShowContextMenu:
    """`show_context_menu` builds a QMenu, applies theme styling, and adds
    items conditionally based on `parent_app.image` (Clear Image only when an
    image is loaded). The menu's exec() must be monkeypatched to avoid
    blocking."""

    def test_no_parent_app_creates_menu_with_lock_only(self, viewer, monkeypatch):
        captured_actions = []

        # NOTE: monkeypatching QMenu.exec turns fake_exec into a bound method,
        # so it receives (self, pos) — accept *args to handle the position arg.
        def fake_exec(self_, *args):
            captured_actions.extend([a.text() for a in self_.actions()])
            return None

        monkeypatch.setattr(QMenu, "exec", fake_exec)
        viewer.show_context_menu(QPoint(10, 10))
        # No parent_app → no Clear Image; only Lock Zoom
        assert "Lock Zoom" in captured_actions
        assert "Clear Image" not in captured_actions

    def test_parent_app_with_image_adds_clear_action(self, viewer, monkeypatch):
        captured_actions = []
        monkeypatch.setattr(QMenu, "exec",
                            lambda self_, *args: captured_actions.extend(
                                [a.text() for a in self_.actions()]))
        viewer.parent_app = _make_parent_app(image_loaded=True)
        viewer.show_context_menu(QPoint(10, 10))
        assert "Clear Image" in captured_actions
        assert "Lock Zoom" in captured_actions

    def test_parent_app_no_image_omits_clear_action(self, viewer, monkeypatch):
        captured_actions = []
        monkeypatch.setattr(QMenu, "exec",
                            lambda self_, *args: captured_actions.extend(
                                [a.text() for a in self_.actions()]))
        viewer.parent_app = _make_parent_app(image_loaded=False)
        viewer.show_context_menu(QPoint(10, 10))
        assert "Clear Image" not in captured_actions

    def test_zoom_locked_shows_unlock_label(self, viewer, monkeypatch):
        captured_actions = []
        monkeypatch.setattr(QMenu, "exec",
                            lambda self_, *args: captured_actions.extend(
                                [a.text() for a in self_.actions()]))
        viewer.zoom_locked = True
        viewer.show_context_menu(QPoint(10, 10))
        assert "Unlock Zoom" in captured_actions
        assert "Lock Zoom" not in captured_actions

    def test_image_mode_uses_translucent_styling(self, viewer, monkeypatch):
        # When in image mode, the menu sets WA_TranslucentBackground attribute
        captured_attrs = []

        def fake_exec(self_, *args):
            captured_attrs.append(
                self_.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

        monkeypatch.setattr(QMenu, "exec", fake_exec)
        viewer.parent_app = _make_parent_app(is_image_mode=True)
        viewer.show_context_menu(QPoint(10, 10))
        assert captured_attrs == [True]

    def test_dark_mode_does_not_use_translucent(self, viewer, monkeypatch):
        captured_attrs = []
        monkeypatch.setattr(QMenu, "exec",
                            lambda self_, *args: captured_attrs.append(
                                self_.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)))
        viewer.parent_app = _make_parent_app(is_image_mode=False)
        viewer.show_context_menu(QPoint(10, 10))
        assert captured_attrs == [False]


class TestMousePressEvent:
    """LeftButton starts a selection drag; other buttons fall through to
    super (parent QGraphicsView default behavior)."""

    def test_left_button_starts_drag(self, viewer):
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonPress, 10, 10)
        viewer.mousePressEvent(evt)
        assert viewer.dragging is True
        assert viewer.selection_start is not None
        assert viewer.selection_end is None

    def test_right_button_does_not_start_drag(self, viewer):
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonPress, 10, 10,
                                     button=Qt.MouseButton.RightButton)
        viewer.mousePressEvent(evt)
        assert viewer.dragging is False
        assert viewer.selection_start is None

    def test_left_button_clears_existing_selection(self, viewer):
        # Set up a fake existing rect item + scene to test the cleanup branch
        scene = QGraphicsScene()
        viewer.setScene(scene)
        viewer.scene_ref = scene
        from PyQt6.QtGui import QPen
        rect_item = scene.addRect(QRectF(0, 0, 10, 10), QPen(Qt.GlobalColor.yellow))
        viewer.selection_rect_item = rect_item

        evt = _make_left_mouse_event(QEvent.Type.MouseButtonPress, 10, 10)
        viewer.mousePressEvent(evt)
        # Source removes the old rect item and clears the reference
        assert viewer.selection_rect_item is None


class TestMouseMoveEvent:
    """When dragging is active and a scene exists, move events build/update
    the selection rectangle."""

    def test_no_drag_falls_through(self, viewer):
        # No drag started → super is called, no rect created
        evt = _make_left_mouse_event(QEvent.Type.MouseMove, 50, 50,
                                     button=Qt.MouseButton.NoButton)
        viewer.mouseMoveEvent(evt)
        assert viewer.selection_rect_item is None

    def test_drag_with_scene_creates_rect(self, qtbot, viewer):
        # Set up: scene WITH a rect so mapToScene returns sensible coords,
        # show the viewer so the viewport has a real size.
        scene = QGraphicsScene(0, 0, 200, 200)
        viewer.setScene(scene)
        viewer.scene_ref = scene
        viewer.resize(200, 200)
        viewer.show()
        qtbot.waitExposed(viewer)
        viewer.dragging = True
        viewer.selection_start = QPointF(10, 10)

        evt = _make_left_mouse_event(QEvent.Type.MouseMove, 50, 50,
                                     button=Qt.MouseButton.LeftButton)
        viewer.mouseMoveEvent(evt)
        assert viewer.selection_rect_item is not None

    def test_drag_with_existing_rect_updates_it(self, qtbot, viewer):
        scene = QGraphicsScene(0, 0, 200, 200)
        viewer.setScene(scene)
        viewer.scene_ref = scene
        viewer.resize(200, 200)
        viewer.show()
        qtbot.waitExposed(viewer)
        viewer.dragging = True
        viewer.selection_start = QPointF(10, 10)

        # First move creates the rect
        evt1 = _make_left_mouse_event(QEvent.Type.MouseMove, 50, 50)
        viewer.mouseMoveEvent(evt1)
        original_rect_item = viewer.selection_rect_item
        # Second move updates the same rect (doesn't create a new one)
        evt2 = _make_left_mouse_event(QEvent.Type.MouseMove, 100, 100)
        viewer.mouseMoveEvent(evt2)
        assert viewer.selection_rect_item is original_rect_item

    def test_drag_with_qpointf_zero_zero_start_now_creates_rect(self, qtbot, viewer):
        # Regression test: source previously used `if self.dragging and
        # self.scene_ref and self.selection_start:` — but bool(QPointF(0,0))
        # is False, so a drag starting at scene origin never created a rect.
        # The fix uses explicit `is not None` check.
        scene = QGraphicsScene(0, 0, 200, 200)
        viewer.setScene(scene)
        viewer.scene_ref = scene
        viewer.resize(200, 200)
        viewer.show()
        qtbot.waitExposed(viewer)
        viewer.dragging = True
        viewer.selection_start = QPointF(0, 0)  # the previously-broken value

        evt = _make_left_mouse_event(QEvent.Type.MouseMove, 50, 50,
                                     button=Qt.MouseButton.LeftButton)
        viewer.mouseMoveEvent(evt)
        # With the fix in place, the rect IS created
        assert viewer.selection_rect_item is not None


class TestMouseReleaseEvent:
    """LeftButton release ends the drag and, if the rect is meaningful
    (>5×5), invokes parent_app.extract_colors_from_selection()."""

    def test_release_without_drag_falls_through(self, viewer):
        # No drag in progress → super is called
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 50, 50)
        viewer.mouseReleaseEvent(evt)
        # No crash, no callback invoked

    def test_release_with_meaningful_rect_calls_extract(self, viewer):
        # mapToScene depends on the viewport transform which is unstable
        # in offscreen tests, so stub it to identity for predictable rect
        # math.
        viewer.mapToScene = lambda p: QPointF(p.x(), p.y())
        viewer.scene_ref = QGraphicsScene()
        viewer.parent_app = _make_parent_app()
        viewer.dragging = True
        viewer.selection_start = QPointF(10, 10)

        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 100, 100)
        viewer.mouseReleaseEvent(evt)
        viewer.parent_app.extract_colors_from_selection.assert_called_once()
        assert viewer.dragging is False

    def test_release_with_tiny_rect_does_not_call_extract(self, viewer):
        # Rect <= 5×5 → no extract call (defensive against accidental clicks)
        viewer.parent_app = _make_parent_app()
        viewer.dragging = True
        viewer.selection_start = QPointF(0, 0)

        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 3, 3)
        viewer.mouseReleaseEvent(evt)
        viewer.parent_app.extract_colors_from_selection.assert_not_called()

    def test_release_clears_selection_state(self, viewer):
        viewer.parent_app = _make_parent_app()
        viewer.dragging = True
        viewer.selection_start = QPointF(0, 0)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 50, 50)
        viewer.mouseReleaseEvent(evt)
        assert viewer.selection_start is None
        assert viewer.selection_end is None

    def test_right_button_release_falls_through(self, viewer):
        # Right release while dragging — source checks `event.button() ==
        # LeftButton`, so right button release falls through to super
        viewer.parent_app = _make_parent_app()
        viewer.dragging = True
        viewer.selection_start = QPointF(0, 0)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 50, 50,
                                     button=Qt.MouseButton.RightButton)
        viewer.mouseReleaseEvent(evt)
        # Drag still in progress because we didn't get the LeftButton release
        assert viewer.dragging is True

    def test_release_with_qpointf_zero_zero_start_now_fires(self, viewer):
        # Regression test: the source previously used `if self.selection_start
        # and self.selection_end and self.parent_app:` — but bool(QPointF(0,0))
        # is False, so a drag starting at scene origin silently never fired
        # the extract callback. The fix uses explicit `is not None` checks.
        viewer.mapToScene = lambda p: QPointF(p.x(), p.y())
        viewer.scene_ref = QGraphicsScene()
        viewer.parent_app = _make_parent_app()
        viewer.dragging = True
        viewer.selection_start = QPointF(0, 0)  # the previously-broken value

        evt = _make_left_mouse_event(QEvent.Type.MouseButtonRelease, 50, 50)
        viewer.mouseReleaseEvent(evt)
        # With the fix in place, this NOW fires correctly
        viewer.parent_app.extract_colors_from_selection.assert_called_once()


class TestMouseDoubleClickEvent:
    """LeftButton double-click on a viewer with a pixmap_item triggers
    `parent_app.pick_color_from_pixel(scene_pos)`."""

    def test_double_click_with_pixmap_calls_pick_color(self, viewer):
        viewer.parent_app = _make_parent_app(has_pixmap=True)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonDblClick, 25, 25)
        viewer.mouseDoubleClickEvent(evt)
        viewer.parent_app.pick_color_from_pixel.assert_called_once()

    def test_double_click_without_pixmap_does_nothing(self, viewer):
        viewer.parent_app = _make_parent_app(has_pixmap=False)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonDblClick, 25, 25)
        viewer.mouseDoubleClickEvent(evt)
        viewer.parent_app.pick_color_from_pixel.assert_not_called()

    def test_double_click_no_parent_app_does_not_crash(self, viewer):
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonDblClick, 25, 25)
        viewer.mouseDoubleClickEvent(evt)  # no parent_app at all

    def test_right_button_double_click_falls_through(self, viewer):
        viewer.parent_app = _make_parent_app(has_pixmap=True)
        evt = _make_left_mouse_event(QEvent.Type.MouseButtonDblClick, 25, 25,
                                     button=Qt.MouseButton.RightButton)
        viewer.mouseDoubleClickEvent(evt)
        # Right button → falls through to super, no callback
        viewer.parent_app.pick_color_from_pixel.assert_not_called()
