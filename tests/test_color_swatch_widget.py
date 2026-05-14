"""
Phase 2 proof-of-infrastructure tests for ColorSwatchWidget.

These are the FIRST pytest-qt tests in the project. They serve a dual purpose:

1. Verify the dual-runner setup actually works (pytest + qtbot + offscreen
   Qt + project bootstrap from conftest.py).

2. Lift coverage on color_swatch_widget.py from 15% (Phase 0 baseline) by
   exercising the full public API: construction, configure() pool-reuse,
   lock toggle, remove, copy-to-clipboard, paint event.

Phase 3 will use this same pattern for every other UI module, so the
patterns established here matter — keep tests focused on one behavior
each, use the `swatch` fixture for setup, and prefer real interactions
over mock-everything.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QMenu
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QAction

from ui.color_swatch_widget import ColorSwatchWidget
from utils import config


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def mock_parent():
    """A mock ColorPickerApp providing the attributes the swatch needs.

    The widget calls `parent_app.theme_manager.get_current_theme()` and
    `parent_app.theme_manager.is_image_mode()` from its context-menu
    handler, plus `remove_color_by_data` and `update_color_lock_state` from
    its action handlers. We give it a MagicMock that returns sensible
    defaults so all four call paths work without instantiating the real
    24K-line ColorPickerApp.
    """
    parent = MagicMock()
    parent.theme_manager.get_current_theme.return_value = config.DARK_THEME_COLORS
    parent.theme_manager.is_image_mode.return_value = False
    return parent


@pytest.fixture
def swatch(qtbot, mock_parent):
    """A fresh ColorSwatchWidget for each test.

    qtbot.addWidget() registers it for cleanup so Qt doesn't leak QObjects
    between tests. We pass parent_app=None to super() (handled by passing
    parent_app=None to the constructor) and then attach the mock manually,
    because passing a MagicMock as a Qt parent causes type errors at the
    C++ layer.
    """
    widget = ColorSwatchWidget(
        number=5,
        rgb=(210, 188, 147),  # brand gold — known good RGB
        hsl=(38, 43, 70),
        hilbert_idx=12345,
        parent_app=None,  # Qt parent stays None to avoid MagicMock type issue
    )
    widget.parent_app = mock_parent  # business-logic parent attached manually
    qtbot.addWidget(widget)
    return widget


# ═════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION & DEFAULTS
# ═════════════════════════════════════════════════════════════════════════════
class TestConstruction:
    """Constructor wiring: stored attributes, computed hex, fixed size, signal hook."""

    def test_widget_instantiates_without_crash(self, swatch):
        assert swatch is not None

    def test_number_attribute_stored(self, swatch):
        assert swatch.number == 5

    def test_rgb_attribute_stored(self, swatch):
        assert swatch.rgb == (210, 188, 147)

    def test_hsl_attribute_stored(self, swatch):
        assert swatch.hsl == (38, 43, 70)

    def test_hilbert_idx_attribute_stored(self, swatch):
        assert swatch.hilbert_idx == 12345

    def test_hex_code_computed_from_rgb(self, swatch):
        # Brand gold (210, 188, 147) → #d2bc93 — must be auto-derived
        assert swatch.hex_code == "#d2bc93"

    def test_default_not_locked(self, swatch):
        assert swatch.is_locked is False

    def test_widget_has_fixed_size(self, swatch):
        # setFixedSize(150, 150) is called in __init__
        size = swatch.size()
        assert size.width() == 150
        assert size.height() == 150

    def test_signal_manager_attached(self, swatch):
        # SignalConnectionManager is created in __init__ for tracked cleanup
        assert swatch.signal_manager is not None

    def test_context_menu_connection_tracked(self, swatch):
        # The customContextMenuRequested signal is connected via signal_manager
        # under the name "swatch_context_menu". Verify the connection exists.
        connection_count = swatch.signal_manager.get_connection_count()
        assert connection_count >= 1


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURE() — widget-pool reuse path
# ═════════════════════════════════════════════════════════════════════════════
class TestConfigure:
    """`configure()` is called by WidgetPool to reuse an existing widget
    with new color data instead of constructing a fresh one. All five
    fields plus the derived hex_code must update."""

    def test_configure_updates_number(self, swatch):
        swatch.configure(number=99, rgb=(0, 0, 0), hsl=(0, 0, 0), hilbert_idx=0)
        assert swatch.number == 99

    def test_configure_updates_rgb(self, swatch):
        swatch.configure(number=1, rgb=(64, 128, 192), hsl=(210, 50, 50), hilbert_idx=1)
        assert swatch.rgb == (64, 128, 192)

    def test_configure_updates_hsl(self, swatch):
        swatch.configure(number=1, rgb=(0, 0, 0), hsl=(180, 75, 25), hilbert_idx=1)
        assert swatch.hsl == (180, 75, 25)

    def test_configure_updates_hilbert_idx(self, swatch):
        swatch.configure(number=1, rgb=(0, 0, 0), hsl=(0, 0, 0), hilbert_idx=98765)
        assert swatch.hilbert_idx == 98765

    def test_configure_recomputes_hex_code(self, swatch):
        # Reconfigure to red — hex must follow the new RGB, not the old gold
        swatch.configure(number=1, rgb=(255, 0, 0), hsl=(0, 100, 50), hilbert_idx=1)
        assert swatch.hex_code == "#ff0000"

    def test_configure_can_set_locked(self, swatch):
        swatch.configure(number=1, rgb=(0, 0, 0), hsl=(0, 0, 0), hilbert_idx=1, is_locked=True)
        assert swatch.is_locked is True

    def test_configure_can_unlock(self, swatch):
        swatch.is_locked = True
        swatch.configure(number=1, rgb=(0, 0, 0), hsl=(0, 0, 0), hilbert_idx=1, is_locked=False)
        assert swatch.is_locked is False


# ═════════════════════════════════════════════════════════════════════════════
# LOCK / REMOVE — actions that delegate to parent_app
# ═════════════════════════════════════════════════════════════════════════════
class TestActions:
    """Actions invoked from the right-click context menu. We test them
    directly rather than driving the menu (QMenu.exec is modal and would
    block the test runner). Phase 3 will exercise the full menu flow."""

    def test_toggle_lock_flips_state_to_true(self, swatch):
        assert swatch.is_locked is False
        swatch.toggle_lock()
        assert swatch.is_locked is True

    def test_toggle_lock_flips_state_back_to_false(self, swatch):
        swatch.toggle_lock()  # → True
        swatch.toggle_lock()  # → False
        assert swatch.is_locked is False

    def test_toggle_lock_calls_parent_update(self, swatch, mock_parent):
        swatch.toggle_lock()
        mock_parent.update_color_lock_state.assert_called_once_with(
            (210, 188, 147), (38, 43, 70), 12345, True
        )

    def test_remove_color_calls_parent(self, swatch, mock_parent):
        swatch.remove_color()
        mock_parent.remove_color_by_data.assert_called_once_with(
            (210, 188, 147), (38, 43, 70), 12345
        )


# ═════════════════════════════════════════════════════════════════════════════
# CLIPBOARD — copy_hex / copy_rgb / copy_hsl
# ═════════════════════════════════════════════════════════════════════════════
class TestClipboard:
    """Each copy_* method puts a formatted string on the system clipboard.
    In offscreen mode the clipboard is process-local but real — we read it
    back to verify the exact string format."""

    def test_copy_hex_writes_hex_code(self, swatch):
        swatch.copy_hex()
        assert QApplication.clipboard().text() == "#d2bc93"

    def test_copy_rgb_writes_rgb_string(self, swatch):
        swatch.copy_rgb()
        assert QApplication.clipboard().text() == "rgb(210, 188, 147)"

    def test_copy_hsl_writes_hsl_string(self, swatch):
        swatch.copy_hsl()
        assert QApplication.clipboard().text() == "hsl(38, 43%, 70%)"


# ═════════════════════════════════════════════════════════════════════════════
# PAINT — render-without-crash for normal and locked states
# ═════════════════════════════════════════════════════════════════════════════
class TestPaint:
    """paintEvent is too render-specific to assert pixel values, but it's
    the bulk of the file. Forcing a repaint and confirming no exception
    propagates covers every branch in the painter logic."""

    def test_paint_event_does_not_crash_default(self, swatch, qtbot):
        swatch.show()
        qtbot.waitExposed(swatch)
        swatch.repaint()  # force synchronous paint

    def test_paint_event_does_not_crash_locked(self, swatch, qtbot):
        swatch.is_locked = True
        swatch.show()
        qtbot.waitExposed(swatch)
        swatch.repaint()

    def test_paint_event_handles_white_background(self, qtbot, mock_parent):
        # White triggers the "use dark text" branch in the contrast logic
        widget = ColorSwatchWidget(1, (255, 255, 255), (0, 0, 100), 0, parent_app=None)
        widget.parent_app = mock_parent
        qtbot.addWidget(widget)
        widget.show()
        qtbot.waitExposed(widget)
        widget.repaint()

    def test_paint_event_handles_black_background(self, qtbot, mock_parent):
        # Black triggers the "use light text" branch
        widget = ColorSwatchWidget(1, (0, 0, 0), (0, 0, 0), 0, parent_app=None)
        widget.parent_app = mock_parent
        qtbot.addWidget(widget)
        widget.show()
        qtbot.waitExposed(widget)
        widget.repaint()


# ═════════════════════════════════════════════════════════════════════════════
# CONTEXT MENU — exercise the full show_context_menu method
# ═════════════════════════════════════════════════════════════════════════════
# In Phase 2 we skipped this because QMenu.exec() is modal and blocks the test
# runner. Solution: monkeypatch QMenu.exec to a no-op that captures `self`, so
# the menu is fully constructed but never displayed. We can then introspect
# the captured menu's actions to verify it was built correctly.

class TestContextMenu:
    """The right-click menu must offer Copy submenu, Remove, and Lock/Unlock
    actions. Each path through `show_context_menu` (image-mode vs normal mode,
    theme present vs absent) exercises a different branch."""

    def _capture_menu(self, monkeypatch):
        """Patch QMenu.exec so the menu is built but never displayed.
        Returns the list that exec calls will populate with the menu instance."""
        captured = []

        def fake_exec(self_menu, *args, **kwargs):
            captured.append(self_menu)
            return None

        monkeypatch.setattr(QMenu, "exec", fake_exec)
        return captured

    def test_show_context_menu_invokes_exec(self, swatch, monkeypatch):
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        assert len(captured) == 1, "exec should have been called exactly once"

    def test_context_menu_has_copy_submenu(self, swatch, monkeypatch):
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        menu = captured[0]
        # The first action on the top-level menu is the Copy submenu's anchor
        action_texts = [a.text() for a in menu.actions()]
        assert any("Copy" in t for t in action_texts), \
            f"Copy submenu missing from menu actions: {action_texts}"

    def test_context_menu_has_remove_action(self, swatch, monkeypatch):
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        menu = captured[0]
        action_texts = [a.text() for a in menu.actions()]
        assert "Remove Color" in action_texts

    def test_context_menu_has_lock_action_when_unlocked(self, swatch, monkeypatch):
        # Default state: is_locked=False → menu shows "Lock Color"
        assert swatch.is_locked is False
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        menu = captured[0]
        action_texts = [a.text() for a in menu.actions()]
        assert "Lock Color" in action_texts

    def test_context_menu_has_unlock_action_when_locked(self, swatch, monkeypatch):
        # Locked state: menu should show "Unlock Color" instead
        swatch.is_locked = True
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        menu = captured[0]
        action_texts = [a.text() for a in menu.actions()]
        assert "Unlock Color" in action_texts

    def test_context_menu_image_mode_path(self, swatch, mock_parent, monkeypatch):
        """Image mode triggers the WA_TranslucentBackground branch."""
        mock_parent.theme_manager.is_image_mode.return_value = True
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        menu = captured[0]
        # In image mode the menu has WA_TranslucentBackground set
        assert menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def test_context_menu_no_theme_skips_stylesheet(self, swatch, mock_parent, monkeypatch):
        """If theme_manager returns None/falsy, the stylesheet branch is skipped
        but the menu is still built and exec'd — just unstyled."""
        mock_parent.theme_manager.get_current_theme.return_value = None
        captured = self._capture_menu(monkeypatch)
        swatch.show_context_menu(QPoint(75, 75))
        # Menu still built and exec called
        assert len(captured) == 1
        # Menu still has all actions (Copy submenu + Remove + Lock)
        action_texts = [a.text() for a in captured[0].actions()]
        assert "Remove Color" in action_texts


# ═════════════════════════════════════════════════════════════════════════════
# PAINT FALLBACK — branches that fire when caches are unavailable
# ═════════════════════════════════════════════════════════════════════════════
# Lines 287, 296-299, 307, 326-327 in color_swatch_widget.py are the
# `if not CACHE_AVAILABLE` fallback branches. In production CACHE_AVAILABLE
# is always True, but we still want to verify the fallback paths don't
# crash — defensive code that's never tested might rot silently.

class TestPaintFallbacks:
    """Cache-disabled paint paths. These tests temporarily turn off the
    module-level CACHE_AVAILABLE flag to exercise the inline-QColor fallback."""

    def test_paint_with_cache_disabled(self, swatch, qtbot, monkeypatch):
        from ui import color_swatch_widget as csw
        monkeypatch.setattr(csw, "CACHE_AVAILABLE", False)
        swatch.show()
        qtbot.waitExposed(swatch)
        swatch.repaint()  # must not crash even without cache

    def test_paint_with_cache_disabled_locked(self, swatch, qtbot, monkeypatch):
        from ui import color_swatch_widget as csw
        monkeypatch.setattr(csw, "CACHE_AVAILABLE", False)
        swatch.is_locked = True
        swatch.show()
        qtbot.waitExposed(swatch)
        swatch.repaint()

    def test_paint_with_no_theme(self, qtbot, mock_parent):
        """When theme_manager returns falsy, paint hits the default border path."""
        mock_parent.theme_manager.get_current_theme.return_value = None
        widget = ColorSwatchWidget(1, (100, 100, 100), (0, 0, 50), 0, parent_app=None)
        widget.parent_app = mock_parent
        qtbot.addWidget(widget)
        widget.show()
        qtbot.waitExposed(widget)
        widget.repaint()
