"""
Tests for ui.settings_panel — the largest UI module in the project.

This file is built incrementally across the Phase 3b sub-sessions. Each
sub-session adds one TestClass below — fixtures stay scoped to the class
that needs them so a fixture problem in one sub-session can't bleed into
others.

Sub-session map:
  3b-1  TestColorHistoryItem, TestSettingsPanelConstruction,
        TestSettingsPanelFoundation, TestSettingsPanelLifecycle,
        TestBuildDialogStylesheet  (this file)
  3b-2  TestHistoryTab
  3b-3  TestSessionsTab
  3b-4  TestHarmonyTab
  3b-5  TestAccessibilityTab
  3b-6  TestShortcutsTab, TestSettingsTab, TestPersistence
"""

from unittest.mock import MagicMock, patch
import os

import pytest
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QListWidgetItem,
    QLabel, QFrame, QVBoxLayout, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCloseEvent, QShowEvent

from ui.settings_panel import SettingsPanel, ColorHistoryItem
from utils import config


# ═════════════════════════════════════════════════════════════════════════════
# SHARED FIXTURES (used by every Phase 3b sub-session)
# ═════════════════════════════════════════════════════════════════════════════

def _make_mock_parent_app(theme_name: str = "dark"):
    """Build a MagicMock that satisfies SettingsPanel's parent_app contract.

    The panel needs:
      - parent_app.theme_manager.current_theme        (str)
      - parent_app.theme_manager.get_current_theme()  (dict)
      - parent_app.theme_manager.is_image_mode()      (bool)
      - parent_app.tooltips_enabled                   (bool, optional)
      - parent_app.debug_label                        (widget, optional)

    Note: this returns a *MagicMock*, not a real QWidget. SettingsPanel passes
    `parent` to QDialog's constructor, so we need a real QWidget elsewhere —
    see the `panel` fixture which creates a real parent and attaches these
    attributes onto it.
    """
    parent = MagicMock()
    parent.theme_manager.current_theme = theme_name
    if theme_name == "light":
        parent.theme_manager.get_current_theme.return_value = config.LIGHT_THEME_COLORS
    elif theme_name == "image":
        parent.theme_manager.get_current_theme.return_value = config.IMAGE_MODE_COLORS
    else:
        parent.theme_manager.get_current_theme.return_value = config.DARK_THEME_COLORS
    parent.theme_manager.is_image_mode.return_value = (theme_name == "image")
    parent.tooltips_enabled = True
    parent.debug_label = None
    return parent


@pytest.fixture
def panel(qtbot):
    """A fully-constructed SettingsPanel with a dark-theme mock parent.

    The real QDialog parent is a fresh QWidget (so QDialog's parent
    contract is satisfied), and we attach the theme_manager mock onto it
    after construction. This matches how Phase 3a handled ColorSwatchWidget.

    IMPORTANT: only the panel is registered with qtbot. Registering both
    panel AND real_parent creates a teardown ordering conflict — qtbot
    closes real_parent first, which destroys its child panel, then tries
    to close the now-deleted panel and raises RuntimeError. Letting Python
    GC real_parent after the test is safe and avoids the issue.
    """
    real_parent = QWidget()
    mock_attrs = _make_mock_parent_app("dark")
    # Attach mock attributes onto the real QWidget
    real_parent.theme_manager = mock_attrs.theme_manager
    real_parent.tooltips_enabled = mock_attrs.tooltips_enabled
    real_parent.debug_label = mock_attrs.debug_label

    p = SettingsPanel(parent=real_parent)
    qtbot.addWidget(p)
    # Keep a reference to real_parent on the panel so it doesn't get GC'd
    # while the panel still references it.
    p._test_real_parent = real_parent
    return p


@pytest.fixture
def panel_light(qtbot):
    """SettingsPanel with a light-theme parent — for theme-switch tests."""
    real_parent = QWidget()
    mock_attrs = _make_mock_parent_app("light")
    real_parent.theme_manager = mock_attrs.theme_manager
    p = SettingsPanel(parent=real_parent)
    qtbot.addWidget(p)
    p._test_real_parent = real_parent
    return p


# ═════════════════════════════════════════════════════════════════════════════
# 1.  ColorHistoryItem — small QListWidgetItem subclass
# ═════════════════════════════════════════════════════════════════════════════
class TestColorHistoryItem:
    """ColorHistoryItem stores hex/time/color_data and paints its background
    to match the actual color. Uses cached QColors when available."""

    def test_construction_with_red(self, qtbot):
        item = ColorHistoryItem("#ff0000", "2 mins ago", {"rgb": [255, 0, 0]})
        assert item.hex_code == "#ff0000"
        assert item.time_str == "2 mins ago"
        assert item.color_data == {"rgb": [255, 0, 0]}

    def test_display_text_combines_hex_and_time(self, qtbot):
        item = ColorHistoryItem("#abcdef", "yesterday", {"rgb": [0xab, 0xcd, 0xef]})
        # Display text format: "{hex}  -  {time}"
        assert "#abcdef" in item.text()
        assert "yesterday" in item.text()

    def test_background_color_set_from_rgb(self, qtbot):
        item = ColorHistoryItem("#00ff00", "now", {"rgb": [0, 255, 0]})
        bg = item.background().color()
        assert (bg.red(), bg.green(), bg.blue()) == (0, 255, 0)

    def test_background_dark_color_uses_light_text(self, qtbot):
        # Black background → text should be near-white for contrast
        item = ColorHistoryItem("#000000", "now", {"rgb": [0, 0, 0]})
        fg = item.foreground().color()
        # Light text means R+G+B is high
        assert (fg.red() + fg.green() + fg.blue()) > 600

    def test_background_light_color_uses_dark_text(self, qtbot):
        # White background → text should be near-black
        item = ColorHistoryItem("#ffffff", "now", {"rgb": [255, 255, 255]})
        fg = item.foreground().color()
        # Dark text means R+G+B is low
        assert (fg.red() + fg.green() + fg.blue()) < 200

    def test_missing_rgb_uses_default_black(self, qtbot):
        # color_data without "rgb" key — falls back to [0, 0, 0]
        item = ColorHistoryItem("#000", "?", {})
        bg = item.background().color()
        assert (bg.red(), bg.green(), bg.blue()) == (0, 0, 0)

    def test_malformed_rgb_handled_gracefully(self, qtbot):
        # Non-list rgb value triggers the `except Exception: pass` path
        item = ColorHistoryItem("#zzz", "?", {"rgb": "not a list"})
        # No crash — item still constructed
        assert item.hex_code == "#zzz"


# ═════════════════════════════════════════════════════════════════════════════
# 2.  SettingsPanel construction — managers wired, dialog properties set
# ═════════════════════════════════════════════════════════════════════════════
class TestSettingsPanelConstruction:
    """The constructor wires up settings_manager, session_manager, color_history
    via module-level getters, sets fixed dialog size, and builds the UI."""

    def test_panel_instantiates(self, panel):
        assert panel is not None

    def test_panel_is_qdialog(self, panel):
        from PyQt6.QtWidgets import QDialog
        assert isinstance(panel, QDialog)

    def test_window_title_set(self, panel):
        assert "Color Picker" in panel.windowTitle()
        assert "Settings" in panel.windowTitle() or "Features" in panel.windowTitle()

    def test_panel_is_non_modal(self, panel):
        # setModal(False) — main window must remain interactive
        assert panel.isModal() is False

    def test_panel_has_fixed_size(self, panel):
        # setFixedSize(660, 700) per project memory
        assert panel.minimumSize() == panel.maximumSize()
        assert panel.width() == 660
        assert panel.height() == 700

    def test_settings_manager_attached(self, panel):
        assert panel.settings_manager is not None

    def test_session_manager_attached(self, panel):
        assert panel.session_manager is not None

    def test_color_history_attached(self, panel):
        assert panel.color_history is not None

    def test_signal_manager_attached(self, panel):
        assert panel.signal_manager is not None

    def test_parent_app_stored(self, panel):
        # parent_app should be the QWidget we constructed in the fixture
        assert panel.parent_app is not None

    def test_signals_defined(self, panel):
        from PyQt6.QtCore import pyqtBoundSignal
        for signal_name in ("settings_changed", "theme_change_requested",
                            "session_loaded", "color_loaded_from_history"):
            sig = getattr(panel, signal_name)
            assert isinstance(sig, pyqtBoundSignal), f"{signal_name} not a bound signal"


# ═════════════════════════════════════════════════════════════════════════════
# 3.  _build_ui — six tabs in expected order, close button
# ═════════════════════════════════════════════════════════════════════════════
class TestSettingsPanelBuildUI:
    """All six tabs must be added to the QTabWidget in the documented order,
    and the close button must wire to QDialog.close()."""

    def test_tab_widget_exists(self, panel):
        assert hasattr(panel, "tab_widget")
        assert isinstance(panel.tab_widget, QTabWidget)

    def test_tab_count_is_six(self, panel):
        assert panel.tab_widget.count() == 6

    def test_tabs_in_expected_order(self, panel):
        expected = ["History", "Sessions", "Harmony", "Accessibility", "Shortcuts", "Settings"]
        actual = [panel.tab_widget.tabText(i) for i in range(panel.tab_widget.count())]
        assert actual == expected

    def test_tab_bar_expanding(self, panel):
        # tabBar().setExpanding(True) — tabs fill the dialog width
        assert panel.tab_widget.tabBar().expanding() is True

    def test_close_button_present(self, panel):
        # Find a QPushButton with text "Close" anywhere in the panel
        buttons = panel.findChildren(QPushButton)
        close_buttons = [b for b in buttons if b.text() == "Close"]
        assert len(close_buttons) >= 1, "No Close button found in panel"


# ═════════════════════════════════════════════════════════════════════════════
# 4.  Foundation helpers: _get_accent / _get_theme / section header & divider
# ═════════════════════════════════════════════════════════════════════════════
class TestSettingsPanelFoundation:
    """The accent/theme accessors and section-builder helpers underpin every
    tab. Theme switching changes the accent color; section dividers use the
    `border_hover` theme key (NOT 'border_light' — that was a real bug fixed
    earlier in the project)."""

    def test_get_accent_dark_theme_uses_brand_gold(self, panel):
        # Dark + Image themes use the bright BRAND_GOLD
        assert panel._get_accent() == config.BRAND_GOLD

    def test_get_accent_light_theme_uses_brand_gold_dark(self, panel_light):
        # Light theme uses the muted BRAND_GOLD_DARK
        assert panel_light._get_accent() == config.BRAND_GOLD_DARK

    def test_get_theme_returns_dict(self, panel):
        theme = panel._get_theme()
        assert isinstance(theme, dict)
        # Sanity check: every theme dict must have these keys
        for key in ("text_primary", "card_bg", "border_hover"):
            assert key in theme

    def test_get_theme_dark_returns_dark_colors(self, panel):
        assert panel._get_theme() == config.DARK_THEME_COLORS

    def test_get_theme_light_returns_light_colors(self, panel_light):
        assert panel_light._get_theme() == config.LIGHT_THEME_COLORS

    def test_create_section_header_returns_qlabel(self, panel):
        header = panel._create_section_header("My Section")
        assert isinstance(header, QLabel)
        assert header.text() == "My Section"

    def test_section_header_uses_accent_color(self, panel):
        header = panel._create_section_header("Test")
        ss = header.styleSheet()
        # The dark-theme accent (BRAND_GOLD) must appear in the stylesheet
        assert config.BRAND_GOLD.lower() in ss.lower()

    def test_create_section_divider_returns_hline_qframe(self, panel):
        divider = panel._create_section_divider()
        assert isinstance(divider, QFrame)
        assert divider.frameShape() == QFrame.Shape.HLine

    def test_section_divider_uses_border_hover_theme_key(self, panel):
        """REGRESSION GUARD: 'border_light' was the original key — but it
        never existed in any theme dict, so the fallback color silently
        rendered everywhere. Fixed to 'border_hover' earlier in the project.
        This test pins the fix in place."""
        divider = panel._create_section_divider()
        ss = divider.styleSheet()
        expected_color = config.DARK_THEME_COLORS["border_hover"]
        assert expected_color.lower() in ss.lower()


# ═════════════════════════════════════════════════════════════════════════════
# 5.  Theme application — _apply_theme + update_theme
# ═════════════════════════════════════════════════════════════════════════════
class TestSettingsPanelTheme:
    """update_theme rebuilds the entire dialog stylesheet from theme keys
    and overrides Qt's highlight palette to match the brand selection color."""

    def test_apply_theme_sets_stylesheet(self, panel):
        # The panel calls _apply_theme during __init__, so a stylesheet must already be set
        assert panel.styleSheet() != ""

    def test_update_theme_sets_palette_highlight(self, panel):
        from PyQt6.QtGui import QPalette
        panel.update_theme()
        palette = panel.palette()
        hl = palette.color(QPalette.ColorRole.Highlight)
        # Must match DARK_THEME_COLORS['selected_bg']
        expected = QColor(config.DARK_THEME_COLORS["selected_bg"])
        assert hl.rgb() == expected.rgb()

    def test_update_theme_sets_highlight_text(self, panel):
        from PyQt6.QtGui import QPalette
        panel.update_theme()
        palette = panel.palette()
        fg = palette.color(QPalette.ColorRole.HighlightedText)
        expected = QColor(config.DARK_THEME_COLORS["text_on_accent"])
        assert fg.rgb() == expected.rgb()

    def test_update_theme_with_no_parent_falls_back_to_dark(self, qtbot):
        # When parent has no theme_manager, the panel falls back to DARK_THEME_COLORS
        bare_parent = QWidget()
        # No theme_manager attribute set — fallback path
        p = SettingsPanel(parent=bare_parent)
        qtbot.addWidget(p)
        p._test_real_parent = bare_parent  # keep ref alive
        # Should not crash, stylesheet still set
        assert p.styleSheet() != ""

    def test_update_theme_callable_externally(self, panel):
        # The docstring promises external callability for live theme switching
        panel.update_theme()  # no exception
        panel.update_theme()  # idempotent
        assert panel.styleSheet() != ""


# ═════════════════════════════════════════════════════════════════════════════
# 6.  Lifecycle: closeEvent + showEvent + sync helpers
# ═════════════════════════════════════════════════════════════════════════════
class TestSettingsPanelLifecycle:
    """closeEvent disconnects tracked signals; showEvent syncs UI prefs from
    main app state; the two update_*_checkbox methods are external entry
    points used when the main window's keyboard shortcut toggles a setting."""

    def test_close_event_calls_signal_manager_disconnect(self, panel):
        # Test the handler directly with a constructed event — calling
        # panel.close() would conflict with qtbot's teardown which also
        # closes registered widgets.
        panel.signal_manager.disconnect_all = MagicMock()
        panel.closeEvent(QCloseEvent())
        panel.signal_manager.disconnect_all.assert_called_once()

    def test_close_event_does_not_crash_with_no_signal_manager(self, panel):
        # Force the no-signal-manager branch (defensive code)
        panel.signal_manager = None
        panel.closeEvent(QCloseEvent())  # must not raise

    def test_show_event_calls_sync_ui_preferences(self, panel):
        panel.sync_ui_preferences = MagicMock()
        panel.showEvent(QShowEvent())
        panel.sync_ui_preferences.assert_called_once()

    def test_sync_ui_preferences_updates_tooltips_checkbox(self, panel):
        panel.parent_app.tooltips_enabled = False
        panel.sync_ui_preferences()
        assert panel.show_tooltips_check.isChecked() is False

    def test_sync_ui_preferences_no_crash_without_parent(self, panel):
        panel.parent_app = None
        panel.sync_ui_preferences()  # early-return path

    def test_update_tooltips_checkbox(self, panel):
        panel.update_tooltips_checkbox(True)
        assert panel.show_tooltips_check.isChecked() is True
        panel.update_tooltips_checkbox(False)
        assert panel.show_tooltips_check.isChecked() is False

    def test_update_debug_overlay_checkbox(self, panel):
        panel.update_debug_overlay_checkbox(True)
        assert panel.debug_overlay_check.isChecked() is True
        panel.update_debug_overlay_checkbox(False)
        assert panel.debug_overlay_check.isChecked() is False


# ═════════════════════════════════════════════════════════════════════════════
# 7.  _build_dialog_stylesheet — smoke test only (per Phase 3b decision)
# ═════════════════════════════════════════════════════════════════════════════
class TestBuildDialogStylesheet:
    """The stylesheet builder is 248 lines of CSS-as-Python — line-by-line
    validation is mechanical and low-value. We just verify it produces a
    non-empty string for each of the three real themes and that theme keys
    feed through to the output."""

    def test_dark_theme_produces_nonempty_stylesheet(self):
        ss = SettingsPanel._build_dialog_stylesheet(config.DARK_THEME_COLORS)
        assert isinstance(ss, str)
        assert len(ss) > 100

    def test_light_theme_produces_nonempty_stylesheet(self):
        ss = SettingsPanel._build_dialog_stylesheet(config.LIGHT_THEME_COLORS)
        assert isinstance(ss, str)
        assert len(ss) > 100

    def test_image_theme_produces_nonempty_stylesheet(self):
        ss = SettingsPanel._build_dialog_stylesheet(config.IMAGE_MODE_COLORS)
        assert isinstance(ss, str)
        assert len(ss) > 100

    def test_theme_dict_values_appear_in_output(self):
        # If we change a theme key, the stylesheet must reflect the change
        ss = SettingsPanel._build_dialog_stylesheet(config.DARK_THEME_COLORS)
        # text_primary is used pervasively — it must show up somewhere
        assert config.DARK_THEME_COLORS["text_primary"].lower() in ss.lower()

# ═════════════════════════════════════════════════════════════════════════════
# 8.  HISTORY TAB  (Phase 3b-2)
# ═════════════════════════════════════════════════════════════════════════════
# Targets _create_history_tab (widget wiring), _refresh_history_list (populate
# from color_history), _load_color_from_history (emit signal), _clear_color_history
# (confirm-then-clear), _export_color_history (file dialog → JSON or TXT).
#
# panel.color_history is the real ColorHistoryManager — already neutralized by
# conftest so add_color / clear_history operate in-memory only, never touching
# the user's real AppData history file.
# ═════════════════════════════════════════════════════════════════════════════

from PyQt6.QtWidgets import QListWidget, QFileDialog
from utils.dialog_helper import DialogHelper as _DH


class TestHistoryTabWiring:
    """The History tab UI must wire up the QListWidget with double-click loading
    and three buttons (Clear / Export / Refresh)."""

    def test_history_list_exists(self, panel):
        assert hasattr(panel, "history_list")
        assert isinstance(panel.history_list, QListWidget)

    def test_history_list_has_min_height(self, panel):
        # setMinimumHeight(300) — keeps the list visible even when tab is short
        assert panel.history_list.minimumHeight() >= 300

    def test_history_tab_has_three_buttons(self, panel):
        # Find the History tab's widget and look for the three buttons by text
        history_widget = panel.tab_widget.widget(0)  # index 0 = History
        from PyQt6.QtWidgets import QPushButton
        button_texts = {b.text() for b in history_widget.findChildren(QPushButton)}
        for expected in ("Clear History", "Export History", "Refresh"):
            assert expected in button_texts, f"Missing button: {expected}"


class TestHistoryListRefresh:
    """`_refresh_history_list` clears the QListWidget and repopulates it from
    color_history.get_history(). With no color_history manager, it shows a
    disabled placeholder."""

    def test_refresh_with_empty_history_clears_list(self, panel):
        panel.color_history.clear_history()
        panel._refresh_history_list()
        assert panel.history_list.count() == 0

    def test_refresh_populates_list_with_history_entries(self, panel):
        panel.color_history.clear_history()
        # Add three colors
        panel.color_history.add_color((255, 0, 0))
        panel.color_history.add_color((0, 255, 0))
        panel.color_history.add_color((0, 0, 255))
        panel._refresh_history_list()
        assert panel.history_list.count() == 3

    def test_refresh_creates_color_history_items(self, panel):
        panel.color_history.clear_history()
        panel.color_history.add_color((128, 64, 200))
        panel._refresh_history_list()
        item = panel.history_list.item(0)
        # Must be a ColorHistoryItem (has hex_code/time_str/color_data attrs)
        assert isinstance(item, ColorHistoryItem)
        assert hasattr(item, "color_data")

    def test_refresh_with_no_color_history_shows_placeholder(self, panel):
        panel.color_history = None
        panel._refresh_history_list()
        # One placeholder item, disabled
        assert panel.history_list.count() == 1
        item = panel.history_list.item(0)
        assert "not available" in item.text().lower()
        # Placeholder has the ItemIsEnabled flag cleared
        assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)

    def test_refresh_replaces_old_entries(self, panel):
        panel.color_history.clear_history()
        panel.color_history.add_color((1, 1, 1))
        panel._refresh_history_list()
        assert panel.history_list.count() == 1
        # Add more, refresh again — old item should be cleared first
        panel.color_history.add_color((2, 2, 2))
        panel.color_history.add_color((3, 3, 3))
        panel._refresh_history_list()
        # 3 colors expected (1,1,1) + (2,2,2) + (3,3,3) — not 4
        assert panel.history_list.count() == 3


class TestLoadColorFromHistory:
    """Double-clicking a history item emits `color_loaded_from_history(rgb_tuple)`
    so the main app can add the color to the palette."""

    def test_emits_signal_with_rgb_tuple(self, panel, qtbot):
        panel.color_history.clear_history()
        panel.color_history.add_color((210, 188, 147))  # brand gold
        panel._refresh_history_list()
        item = panel.history_list.item(0)

        with qtbot.waitSignal(panel.color_loaded_from_history, timeout=500) as blocker:
            panel._load_color_from_history(item)
        assert blocker.args == [(210, 188, 147)]

    def test_no_item_no_current_selection_is_noop(self, panel):
        panel.color_history.clear_history()
        panel._refresh_history_list()
        # No selection, no item passed — early-return path, no signal emitted
        panel._load_color_from_history(None)  # must not raise

    def test_falls_back_to_current_item_when_arg_none(self, panel, qtbot):
        panel.color_history.clear_history()
        panel.color_history.add_color((100, 200, 50))
        panel._refresh_history_list()
        panel.history_list.setCurrentRow(0)

        with qtbot.waitSignal(panel.color_loaded_from_history, timeout=500) as blocker:
            panel._load_color_from_history(None)  # falls back to currentItem()
        assert blocker.args == [(100, 200, 50)]

    def test_item_without_color_data_is_noop(self, panel):
        # Plain QListWidgetItem (no color_data attribute) is the no-op path
        plain_item = QListWidgetItem("plain text")
        panel._load_color_from_history(plain_item)  # must not raise

    def test_malformed_color_data_triggers_error_dialog(self, panel, monkeypatch):
        # Build an item where color_data exists (passes hasattr check) but
        # operating on it raises — so the inner try/except path fires.
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))

        class BrokenColorData:
            def get(self, *args, **kwargs):
                raise RuntimeError("boom")

        class BadItem:
            color_data = BrokenColorData()

        panel._load_color_from_history(BadItem())
        # The except path calls DialogHelper.show_warning
        assert len(captured) == 1
        assert "Failed" in captured[0]


class TestClearColorHistory:
    """`_clear_color_history` shows a confirm dialog. On Yes it calls
    color_history.clear_history() and refreshes the list. On No it does nothing."""

    def test_yes_clears_and_refreshes(self, panel, monkeypatch):
        # Pre-populate
        panel.color_history.clear_history()
        panel.color_history.add_color((1, 1, 1))
        panel.color_history.add_color((2, 2, 2))
        panel._refresh_history_list()
        assert panel.history_list.count() == 2

        # User clicks Yes
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)

        panel._clear_color_history()
        assert len(panel.color_history.get_history()) == 0
        assert panel.history_list.count() == 0

    def test_no_does_not_clear(self, panel, monkeypatch):
        panel.color_history.clear_history()
        panel.color_history.add_color((1, 1, 1))

        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: False)

        panel._clear_color_history()
        # History intact
        assert len(panel.color_history.get_history()) == 1

    def test_no_color_history_does_not_crash(self, panel, monkeypatch):
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)
        panel.color_history = None
        panel._clear_color_history()  # must not raise


class TestExportColorHistory:
    """`_export_color_history` opens a file dialog and writes JSON or TXT
    depending on the chosen extension. Empty history shows a warning."""

    def test_no_color_history_shows_warning(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.color_history = None
        panel._export_color_history()
        assert len(captured) == 1
        assert "not available" in captured[0].lower()

    def test_empty_history_shows_warning(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.color_history.clear_history()
        panel._export_color_history()
        assert len(captured) == 1
        assert "no colors" in captured[0].lower() or "history to export" in captured[0].lower()

    def test_user_cancels_file_dialog_is_noop(self, panel, monkeypatch, tmp_path):
        panel.color_history.clear_history()
        panel.color_history.add_color((1, 2, 3))
        # User cancels — getSaveFileName returns ("", "")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            lambda *a, **k: ("", ""))
        # No dialog calls expected
        panel._export_color_history()  # must not raise

    def test_json_export_calls_export_history(self, panel, monkeypatch, tmp_path):
        panel.color_history.clear_history()
        panel.color_history.add_color((255, 128, 64))
        target = str(tmp_path / "exported.json")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            lambda *a, **k: (target, "JSON Files (*.json)"))
        # Suppress success info dialog
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        # Spy on color_history.export_history
        spy_calls = []
        original = panel.color_history.export_history
        def spy(path):
            spy_calls.append(path)
            return original(path)
        panel.color_history.export_history = spy

        panel._export_color_history()
        assert spy_calls == [target]

    def test_txt_export_writes_formatted_lines(self, panel, monkeypatch, tmp_path):
        panel.color_history.clear_history()
        panel.color_history.add_color((255, 0, 0))
        panel.color_history.add_color((0, 255, 0))
        target = str(tmp_path / "history.txt")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            lambda *a, **k: (target, "Text Files (*.txt)"))
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        panel._export_color_history()

        # Verify the file was created and has the expected structure
        assert (tmp_path / "history.txt").exists()
        content = (tmp_path / "history.txt").read_text(encoding="utf-8")
        assert "RNV Color Picker" in content
        assert "Total colors: 2" in content
        assert "RGB(" in content  # at least one data line

    def test_txt_export_failure_shows_warning(self, panel, monkeypatch):
        panel.color_history.clear_history()
        panel.color_history.add_color((1, 2, 3))
        # Path that can't be opened (root-level Windows path won't be writable)
        bad_path = "/no/such/dir/x.txt" if os.name != "nt" else "Z:\\nonexistent\\x.txt"
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            lambda *a, **k: (bad_path, "Text Files (*.txt)"))
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))

        panel._export_color_history()
        assert len(captured) == 1
        assert "failed" in captured[0].lower() or "error" in captured[0].lower()

# ═════════════════════════════════════════════════════════════════════════════
# 9.  SESSIONS TAB  (Phase 3b-3)
# ═════════════════════════════════════════════════════════════════════════════
# Targets _create_sessions_tab (widget wiring), _refresh_session_list (populate
# QListWidget from session_manager.list_sessions()), _save_current_session
# (QInputDialog → save_session), _load_selected_session (load + emit
# session_loaded), _delete_selected_session (confirm → delete_session), and
# the 4 autosave/autoload sync helpers.
#
# panel.session_manager is the real SessionManager with a tmp directory (per
# conftest bootstrap). save/load/delete actually hit disk in a temp area, so
# we get full integration without touching the user's real session files.
# ═════════════════════════════════════════════════════════════════════════════

from PyQt6.QtWidgets import QInputDialog, QCheckBox


# ----- Helper to stand in for ColorPickerApp's `colors` list -----------------
def _seed_parent_app_with_colors(panel, count: int = 3):
    """Attach a `colors` list and refresh_color_display stub to panel.parent_app
    so save/load can operate. Returns the colors list for assertion."""
    colors = []
    for i in range(count):
        rgb = (10 * (i + 1), 20 * (i + 1), 30 * (i + 1))
        hsl = (i * 30, 50, 50)
        colors.append((rgb, hsl, i, False))
    panel.parent_app.colors = colors
    panel.parent_app.refresh_color_display = MagicMock()
    return colors


class TestSessionsTabWiring:
    """The Sessions tab UI must wire up the QListWidget with double-click
    loading, four buttons (Save / Load / Delete / Refresh), and the
    autosave/autoload checkboxes."""

    def test_session_list_exists(self, panel):
        assert hasattr(panel, "session_list")
        assert isinstance(panel.session_list, QListWidget)

    def test_session_list_min_height(self, panel):
        # setMinimumHeight(200) per source
        assert panel.session_list.minimumHeight() >= 200

    def test_sessions_tab_has_four_buttons(self, panel):
        sessions_widget = panel.tab_widget.widget(1)  # index 1 = Sessions
        from PyQt6.QtWidgets import QPushButton
        button_texts = {b.text() for b in sessions_widget.findChildren(QPushButton)}
        for expected in ("Save Current", "Load Selected", "Delete Selected", "Refresh"):
            assert expected in button_texts, f"Missing button: {expected}"

    def test_autosave_checkbox_exists(self, panel):
        assert hasattr(panel, "session_autosave_check")
        assert isinstance(panel.session_autosave_check, QCheckBox)

    def test_autoload_checkbox_exists(self, panel):
        assert hasattr(panel, "session_autoload_check")
        assert isinstance(panel.session_autoload_check, QCheckBox)


class TestSessionListRefresh:
    """`_refresh_session_list` clears the QListWidget and repopulates from
    session_manager.list_sessions(). With no manager, shows a disabled placeholder."""

    def test_refresh_with_no_session_manager_shows_placeholder(self, panel):
        panel.session_manager = None
        panel._refresh_session_list()
        assert panel.session_list.count() == 1
        item = panel.session_list.item(0)
        assert "not available" in item.text().lower()
        assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)

    def test_refresh_with_empty_session_manager(self, panel, monkeypatch):
        monkeypatch.setattr(panel.session_manager, "list_sessions", lambda: [])
        panel._refresh_session_list()
        assert panel.session_list.count() == 0

    def test_refresh_populates_from_dict_sessions(self, panel, monkeypatch):
        sessions = [
            {"name": "morning_palette", "filepath": "/x/morning.cpksession",
             "modified": "2026-04-30", "color_count": 5, "description": ""},
            {"name": "evening_palette", "filepath": "/x/evening.cpksession",
             "modified": "2026-04-29", "color_count": 7, "description": ""},
        ]
        monkeypatch.setattr(panel.session_manager, "list_sessions", lambda: sessions)
        panel._refresh_session_list()
        assert panel.session_list.count() == 2
        assert panel.session_list.item(0).text() == "morning_palette"
        assert panel.session_list.item(1).text() == "evening_palette"

    def test_refresh_stores_session_data_on_user_role(self, panel, monkeypatch):
        session = {"name": "alpha", "filepath": "/x.cpksession", "color_count": 3}
        monkeypatch.setattr(panel.session_manager, "list_sessions", lambda: [session])
        panel._refresh_session_list()
        item = panel.session_list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == session

    def test_refresh_handles_string_session_entries(self, panel, monkeypatch):
        # Defensive path: list_sessions might return strings instead of dicts
        monkeypatch.setattr(panel.session_manager, "list_sessions", lambda: ["legacy_name"])
        panel._refresh_session_list()
        assert panel.session_list.count() == 1
        assert panel.session_list.item(0).text() == "legacy_name"


class TestSaveSession:
    """`_save_current_session` prompts for a name via QInputDialog, then calls
    session_manager.save_session() with the colors converted to dict form."""

    def test_no_session_manager_shows_warning(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.session_manager = None
        panel._save_current_session()
        assert len(captured) == 1
        assert "not available" in captured[0].lower()

    def test_no_colors_shows_warning(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.parent_app.colors = []
        panel._save_current_session()
        assert len(captured) == 1
        assert "no colors" in captured[0].lower()

    def test_user_cancels_input_dialog_is_noop(self, panel, monkeypatch):
        _seed_parent_app_with_colors(panel, count=2)
        # User clicks Cancel: ok == False
        monkeypatch.setattr(_DH, "get_text", lambda *a, **k: ("ignored", False))
        spy = MagicMock()
        panel.session_manager.save_session = spy
        panel._save_current_session()
        spy.assert_not_called()

    def test_empty_name_is_noop(self, panel, monkeypatch):
        _seed_parent_app_with_colors(panel)
        # `if ok and name:` — empty name skipped even with ok=True
        monkeypatch.setattr(_DH, "get_text", lambda *a, **k: ("", True))
        spy = MagicMock()
        panel.session_manager.save_session = spy
        panel._save_current_session()
        spy.assert_not_called()

    def test_save_calls_session_manager_with_correct_payload(self, panel, monkeypatch):
        _seed_parent_app_with_colors(panel, count=2)
        monkeypatch.setattr(_DH, "get_text", lambda *a, **k: ("my_palette", True))
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        captured = []

        def fake_save(name, data):
            captured.append((name, data))
            return True

        panel.session_manager.save_session = fake_save
        panel._save_current_session()

        assert len(captured) == 1
        name, data = captured[0]
        assert name == "my_palette"
        assert "colors" in data
        assert len(data["colors"]) == 2
        # Color entries must be plain Python ints/bools — not numpy types
        first = data["colors"][0]
        assert isinstance(first["rgb"], list)
        assert all(isinstance(v, int) for v in first["rgb"])
        assert isinstance(first["locked"], bool)

    def test_save_failure_shows_error_dialog(self, panel, monkeypatch):
        _seed_parent_app_with_colors(panel)
        monkeypatch.setattr(_DH, "get_text", lambda *a, **k: ("name", True))
        panel.session_manager.save_session = lambda n, d: False  # simulate failure
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._save_current_session()
        assert len(captured) == 1
        assert "failed" in captured[0].lower()


class TestLoadSession:
    """`_load_selected_session` loads via session_manager.load_session(), emits
    `session_loaded`, applies colors to parent_app, and refreshes the display."""

    def test_no_selection_shows_warning(self, panel, monkeypatch):
        # Empty session list — no current item
        panel.session_list.clear()
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._load_selected_session()
        assert len(captured) == 1
        assert "select" in captured[0].lower()

    def test_no_session_manager_shows_warning(self, panel, monkeypatch):
        # Add an item, then nuke the manager
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("test_session"))
        panel.session_list.setCurrentRow(0)
        panel.session_manager = None
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._load_selected_session()
        assert len(captured) == 1
        assert "not available" in captured[0].lower()

    def test_load_success_emits_session_loaded_signal(self, panel, qtbot, monkeypatch):
        # Set up a session in the list
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("my_session"))
        panel.session_list.setCurrentRow(0)
        # Stub load_session to return valid data
        session_data = {
            "colors": [
                {"rgb": [255, 0, 0], "hsl": [0, 100, 50], "hilbert": 0, "locked": False},
                {"rgb": [0, 255, 0], "hsl": [120, 100, 50], "hilbert": 1, "locked": True},
            ]
        }
        monkeypatch.setattr(panel.session_manager, "load_session",
                            lambda name: session_data if name == "my_session" else None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        # Need parent_app.colors and refresh_color_display
        panel.parent_app.colors = []
        panel.parent_app.refresh_color_display = MagicMock()

        with qtbot.waitSignal(panel.session_loaded, timeout=500) as blocker:
            panel._load_selected_session()
        assert blocker.args == ["my_session"]

    def test_load_populates_parent_app_colors(self, panel, monkeypatch):
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("s1"))
        panel.session_list.setCurrentRow(0)
        session_data = {
            "colors": [
                {"rgb": [10, 20, 30], "hsl": [180, 50, 25], "hilbert": 5, "locked": True},
            ]
        }
        monkeypatch.setattr(panel.session_manager, "load_session",
                            lambda name: session_data)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel.parent_app.colors = [("old", "data", 0, False)]  # sentinel old value
        panel.parent_app.refresh_color_display = MagicMock()

        panel._load_selected_session()

        # Old colors cleared, new ones applied as 4-tuples
        assert len(panel.parent_app.colors) == 1
        rgb, hsl, hilbert, locked = panel.parent_app.colors[0]
        assert rgb == (10, 20, 30)
        assert hsl == (180, 50, 25)
        assert hilbert == 5
        assert locked is True
        panel.parent_app.refresh_color_display.assert_called_once()

    def test_load_missing_locked_field_defaults_false(self, panel, monkeypatch):
        # Older session files might lack "locked" key — defaults to False
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("legacy"))
        panel.session_list.setCurrentRow(0)
        session_data = {
            "colors": [{"rgb": [1, 2, 3], "hsl": [0, 0, 0], "hilbert": 0}],
        }
        monkeypatch.setattr(panel.session_manager, "load_session",
                            lambda name: session_data)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel.parent_app.colors = []
        panel.parent_app.refresh_color_display = MagicMock()

        panel._load_selected_session()
        assert panel.parent_app.colors[0][3] is False  # locked field

    def test_load_failure_shows_error(self, panel, monkeypatch):
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("broken"))
        panel.session_list.setCurrentRow(0)
        # load_session returns None → failure path
        monkeypatch.setattr(panel.session_manager, "load_session", lambda name: None)
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._load_selected_session()
        assert len(captured) == 1
        assert "failed" in captured[0].lower()


class TestDeleteSession:
    """`_delete_selected_session` shows a confirm dialog. On Yes calls
    session_manager.delete_session() and refreshes."""

    def test_no_selection_shows_warning(self, panel, monkeypatch):
        panel.session_list.clear()
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._delete_selected_session()
        assert len(captured) == 1
        assert "select" in captured[0].lower()

    def test_yes_confirms_and_deletes(self, panel, monkeypatch):
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("delete_me"))
        panel.session_list.setCurrentRow(0)
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)
        delete_calls = []
        panel.session_manager.delete_session = lambda name: (delete_calls.append(name) or True)
        # Also stub list_sessions so refresh doesn't blow up
        monkeypatch.setattr(panel.session_manager, "list_sessions", lambda: [])

        panel._delete_selected_session()
        assert delete_calls == ["delete_me"]

    def test_no_does_not_delete(self, panel, monkeypatch):
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("keep_me"))
        panel.session_list.setCurrentRow(0)
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: False)
        spy = MagicMock()
        panel.session_manager.delete_session = spy
        panel._delete_selected_session()
        spy.assert_not_called()

    def test_delete_failure_shows_warning(self, panel, monkeypatch):
        panel.session_list.clear()
        panel.session_list.addItem(QListWidgetItem("fail_me"))
        panel.session_list.setCurrentRow(0)
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)
        panel.session_manager.delete_session = lambda name: False
        captured = []
        monkeypatch.setattr(_DH, "show_warning",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._delete_selected_session()
        assert len(captured) == 1
        assert "failed" in captured[0].lower()


class TestSessionAutosaveSync:
    """The 4 sync helpers keep two checkboxes (one on Sessions tab, one on
    Settings tab) in lock-step. Each guards against an infinite loop with
    blockSignals(True/False). Each guards against the partner not yet
    existing via hasattr().

    Qt.CheckState.Checked = 2  (the magic number used in source)
    Qt.CheckState.Unchecked = 0
    """

    def test_from_general_to_sessions_autosave_checked(self, panel):
        # When the General-tab autosave checkbox flips on, the Sessions-tab
        # checkbox should follow.
        panel.session_autosave_check.setChecked(False)
        panel._sync_autosave_checkbox_from_general(2)  # Checked
        assert panel.session_autosave_check.isChecked() is True

    def test_from_general_to_sessions_autosave_unchecked(self, panel):
        panel.session_autosave_check.setChecked(True)
        panel._sync_autosave_checkbox_from_general(0)  # Unchecked
        assert panel.session_autosave_check.isChecked() is False

    def test_from_sessions_to_general_autosave(self, panel):
        # Settings tab also exists by now (built after Sessions tab in __init__)
        panel.autosave_session_check.setChecked(False)
        panel._sync_autosave_checkbox_from_sessions(2)
        assert panel.autosave_session_check.isChecked() is True

    def test_from_general_to_sessions_autoload(self, panel):
        panel.session_autoload_check.setChecked(False)
        panel._sync_autoload_checkbox_from_general(2)
        assert panel.session_autoload_check.isChecked() is True

    def test_from_sessions_to_general_autoload(self, panel):
        panel.autoload_session_check.setChecked(False)
        panel._sync_autoload_checkbox_from_sessions(2)
        assert panel.autoload_session_check.isChecked() is True

    def test_sync_blocks_signals_to_prevent_infinite_loop(self, panel):
        # If sync didn't blockSignals, setting the partner would re-fire
        # stateChanged → the original setter would fire again → infinite loop.
        # Verify by counting stateChanged emissions on the partner.
        emissions = []
        panel.session_autosave_check.stateChanged.connect(
            lambda s: emissions.append(s)
        )
        # Trigger a sync from the General-tab side
        panel._sync_autosave_checkbox_from_general(2)
        # The partner's state changed but its stateChanged signal must NOT
        # have fired (it would have triggered _sync_autosave_checkbox_from_sessions
        # → infinite recursion). blockSignals(True) prevents this.
        assert emissions == []

    def test_sync_noop_when_partner_missing(self, panel):
        # If the partner attribute is missing, sync is a no-op (defensive)
        del panel.session_autosave_check
        panel._sync_autosave_checkbox_from_general(2)  # must not raise

# ═════════════════════════════════════════════════════════════════════════════
# 10.  HARMONY TAB  (Phase 3b-4)
# ═════════════════════════════════════════════════════════════════════════════
# Targets _create_harmony_tab (widget wiring), _update_harmony_base (preview
# refresh on RGB spin change), _pick_harmony_base_from_palette (read first
# palette color into spinboxes), _generate_harmony (call ColorHarmony +
# render swatches), _create_harmony_swatch (build a single swatch widget),
# _add_harmony_to_palette (call parent_app.add_color for each).
#
# NOTE: Unlike the History/Sessions tabs, the Harmony tab does NOT fire any
# of the 4 panel signals. _add_harmony_to_palette calls parent_app.add_color()
# directly, so tests need a parent_app with a working add_color method.
# ═════════════════════════════════════════════════════════════════════════════

from PyQt6.QtWidgets import QSpinBox, QComboBox
from core.color_harmony import ColorHarmony, HarmonyType


class TestHarmonyTabWiring:
    """The Harmony tab UI must wire up RGB spin boxes (with default brand-gold
    values), a harmony-type combo, a swatches container, and the 'Add to Palette'
    button."""

    def test_rgb_spinboxes_exist(self, panel):
        for name in ("harmony_r_spin", "harmony_g_spin", "harmony_b_spin"):
            assert hasattr(panel, name)
            assert isinstance(getattr(panel, name), QSpinBox)

    def test_rgb_spinboxes_have_0_255_range(self, panel):
        for spin in (panel.harmony_r_spin, panel.harmony_g_spin, panel.harmony_b_spin):
            assert spin.minimum() == 0
            assert spin.maximum() == 255

    def test_rgb_spinboxes_default_to_brand_gold(self, panel):
        # Source uses (191, 145, 69) as the initial values
        assert panel.harmony_r_spin.value() == 191
        assert panel.harmony_g_spin.value() == 145
        assert panel.harmony_b_spin.value() == 69

    def test_harmony_type_combo_has_all_seven_types(self, panel):
        assert hasattr(panel, "harmony_type_combo")
        assert isinstance(panel.harmony_type_combo, QComboBox)
        # Source defines 7 types; verify count and a few key entries
        assert panel.harmony_type_combo.count() == 7
        items = [panel.harmony_type_combo.itemText(i) for i in range(7)]
        for expected in ("Complementary", "Triadic", "Analogous", "Monochromatic"):
            assert expected in items

    def test_harmony_swatches_layout_exists(self, panel):
        assert hasattr(panel, "harmony_swatches_layout")
        # After construction, _generate_harmony has been called once,
        # so swatches already exist (count > 0). Plus a stretch item at the end.
        assert panel.harmony_swatches_layout.count() >= 2

    def test_harmony_base_preview_exists(self, panel):
        assert hasattr(panel, "harmony_base_preview")
        # Fixed 60×60 per source
        assert panel.harmony_base_preview.size().width() == 60
        assert panel.harmony_base_preview.size().height() == 60


class TestHarmonyBaseUpdate:
    """`_update_harmony_base` is the slot for spin-box changes. It updates the
    preview's stylesheet to match the new RGB and re-runs the harmony generator."""

    def test_setting_spin_value_triggers_update(self, panel):
        # The spinbox is connected to _update_harmony_base via valueChanged.
        # Set a distinctive RGB, then check the preview stylesheet contains it.
        panel.harmony_r_spin.setValue(50)
        panel.harmony_g_spin.setValue(100)
        panel.harmony_b_spin.setValue(150)
        ss = panel.harmony_base_preview.styleSheet()
        assert "rgb(50, 100, 150)" in ss

    def test_update_calls_generate_harmony(self, panel):
        spy = MagicMock(wraps=panel._generate_harmony)
        panel._generate_harmony = spy
        panel.harmony_r_spin.setValue(42)
        spy.assert_called()


class TestPickHarmonyBaseFromPalette:
    """`_pick_harmony_base_from_palette` reads the first color from
    parent_app.colors and pushes its RGB into the spin boxes."""

    def test_no_parent_shows_info_dialog(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_info",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.parent_app = None
        panel._pick_harmony_base_from_palette()
        assert len(captured) == 1
        assert "no colors" in captured[0].lower()

    def test_empty_palette_shows_info_dialog(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(_DH, "show_info",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel.parent_app.colors = []
        panel._pick_harmony_base_from_palette()
        assert len(captured) == 1

    def test_picks_first_color_into_spinboxes(self, panel):
        # First color in palette has rgb=(77, 88, 99)
        panel.parent_app.colors = [
            ((77, 88, 99), (200, 50, 50), 0, False),
            ((10, 20, 30), (180, 80, 30), 1, False),
        ]
        panel._pick_harmony_base_from_palette()
        assert panel.harmony_r_spin.value() == 77
        assert panel.harmony_g_spin.value() == 88
        assert panel.harmony_b_spin.value() == 99


class TestGenerateHarmony:
    """`_generate_harmony` reads the RGB spinboxes + harmony type combo, calls
    ColorHarmony.generate_harmony(), updates the description label, stores the
    result on self.harmony_colors, and rebuilds the swatch widgets."""

    def test_stores_generated_colors_on_panel(self, panel):
        # Default state runs once at construction — harmony_colors must exist
        assert hasattr(panel, "harmony_colors")
        assert len(panel.harmony_colors) >= 1

    def test_generates_2_colors_for_complementary(self, panel):
        panel.harmony_type_combo.setCurrentText("Complementary")
        panel._generate_harmony()
        assert len(panel.harmony_colors) == 2

    def test_generates_3_colors_for_triadic(self, panel):
        panel.harmony_type_combo.setCurrentText("Triadic")
        panel._generate_harmony()
        assert len(panel.harmony_colors) == 3

    def test_generates_5_colors_for_monochromatic(self, panel):
        panel.harmony_type_combo.setCurrentText("Monochromatic")
        panel._generate_harmony()
        assert len(panel.harmony_colors) == 5

    def test_first_color_is_base_rgb(self, panel):
        panel.harmony_r_spin.setValue(200)
        panel.harmony_g_spin.setValue(100)
        panel.harmony_b_spin.setValue(50)
        panel._generate_harmony()
        # ColorHarmony always returns the base as the first entry
        assert panel.harmony_colors[0] == (200, 100, 50)

    def test_square_alias_maps_to_tetradic(self, panel, monkeypatch):
        # The combo entry "Tetradic (Square)" must map to HarmonyType.TETRADIC.
        # Spy on generate_harmony to capture which enum value is passed.
        captured_types = []

        def fake_generate(base, htype):
            captured_types.append(htype)
            return [(0, 0, 0)] * 4

        monkeypatch.setattr(ColorHarmony, "generate_harmony", staticmethod(fake_generate))
        panel.harmony_type_combo.setCurrentText("Tetradic (Square)")
        panel._generate_harmony()
        assert captured_types[-1] == HarmonyType.TETRADIC

    def test_rectangle_alias_maps_to_compound(self, panel, monkeypatch):
        captured_types = []

        def fake_generate(base, htype):
            captured_types.append(htype)
            return [(0, 0, 0)] * 4

        monkeypatch.setattr(ColorHarmony, "generate_harmony", staticmethod(fake_generate))
        panel.harmony_type_combo.setCurrentText("Compound (Rectangle)")
        panel._generate_harmony()
        assert captured_types[-1] == HarmonyType.COMPOUND

    def test_description_label_updated(self, panel):
        panel.harmony_type_combo.setCurrentText("Triadic")
        panel._generate_harmony()
        # Description from ColorHarmony.get_harmony_description; non-empty
        assert panel.harmony_desc_label.text() != ""

    def test_swatches_rebuilt_on_regenerate(self, panel):
        # Generate triadic (3 colors) → 3 swatches + 1 stretch = 4 layout items
        panel.harmony_type_combo.setCurrentText("Triadic")
        panel._generate_harmony()
        triadic_count = panel.harmony_swatches_layout.count()
        # Switch to monochromatic (5 colors) → 5 swatches + 1 stretch = 6 items
        panel.harmony_type_combo.setCurrentText("Monochromatic")
        panel._generate_harmony()
        mono_count = panel.harmony_swatches_layout.count()
        assert mono_count > triadic_count

    def test_unknown_type_falls_back_to_complementary(self, panel, monkeypatch):
        """If the combo text doesn't match any known type, defaults to Complementary."""
        captured_types = []

        def fake_generate(base, htype):
            captured_types.append(htype)
            return [(0, 0, 0), (255, 255, 255)]

        monkeypatch.setattr(ColorHarmony, "generate_harmony", staticmethod(fake_generate))
        # Force an unrecognized type by adding a fake item and selecting it
        panel.harmony_type_combo.addItem("FakeType")
        panel.harmony_type_combo.setCurrentText("FakeType")
        panel._generate_harmony()
        assert captured_types[-1] == HarmonyType.COMPLEMENTARY


class TestCreateHarmonySwatch:
    """`_create_harmony_swatch` builds a 70×90 widget with a colored box and
    hex label. The base swatch gets a thicker accent border."""

    def test_returns_qwidget(self, panel):
        swatch = panel._create_harmony_swatch((255, 0, 0), is_base=False)
        assert isinstance(swatch, QWidget)

    def test_swatch_has_fixed_size(self, panel):
        swatch = panel._create_harmony_swatch((100, 100, 100), is_base=False)
        assert swatch.size().width() == 70
        assert swatch.size().height() == 90

    def test_swatch_contains_hex_label(self, panel):
        swatch = panel._create_harmony_swatch((255, 0, 128), is_base=False)
        # Find the hex label child — should contain the uppercase hex
        labels = swatch.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]
        assert any("FF0080" in t for t in label_texts)

    def test_base_swatch_labelled_base(self, panel):
        swatch = panel._create_harmony_swatch((0, 255, 0), is_base=True)
        labels = swatch.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]
        assert "Base" in label_texts

    def test_non_base_swatch_no_base_label(self, panel):
        swatch = panel._create_harmony_swatch((0, 255, 0), is_base=False)
        labels = swatch.findChildren(QLabel)
        # The "Base" label is empty when is_base=False — no label has text "Base"
        label_texts = [lbl.text() for lbl in labels]
        assert "Base" not in label_texts

    def test_base_swatch_uses_accent_border(self, panel):
        # is_base=True → 3px accent border. Color box stylesheet contains accent.
        swatch = panel._create_harmony_swatch((50, 50, 50), is_base=True)
        labels = swatch.findChildren(QLabel)
        # The first label is the color box (has background-color in stylesheet)
        color_box_ss = next(
            (lbl.styleSheet() for lbl in labels if "background-color" in lbl.styleSheet()),
            ""
        )
        assert "3px solid" in color_box_ss
        # Accent for dark theme is BRAND_GOLD
        assert config.BRAND_GOLD.lower() in color_box_ss.lower()


class TestAddHarmonyToPalette:
    """`_add_harmony_to_palette` iterates over self.harmony_colors and calls
    parent_app.add_color() for each. Successful additions trigger
    parent_app.refresh_color_display() and an info dialog."""

    def test_no_colors_is_noop(self, panel):
        panel.harmony_colors = []
        # Should not raise, should not call anything
        panel.parent_app.add_color = MagicMock()
        panel._add_harmony_to_palette()
        panel.parent_app.add_color.assert_not_called()

    def test_no_harmony_colors_attribute_is_noop(self, panel):
        # If self.harmony_colors was never set, function early-returns
        if hasattr(panel, "harmony_colors"):
            del panel.harmony_colors
        panel.parent_app.add_color = MagicMock()
        panel._add_harmony_to_palette()
        panel.parent_app.add_color.assert_not_called()

    def test_no_parent_app_is_noop(self, panel):
        panel.harmony_colors = [(255, 0, 0), (0, 255, 0)]
        panel.parent_app = None
        # Must not raise
        panel._add_harmony_to_palette()

    def test_calls_add_color_for_each_harmony_color(self, panel, monkeypatch):
        panel.harmony_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        added = []
        panel.parent_app.add_color = lambda rgb: (added.append(rgb) or True)
        panel.parent_app.refresh_color_display = MagicMock()
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        panel._add_harmony_to_palette()
        assert added == [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

    def test_calls_refresh_when_at_least_one_added(self, panel, monkeypatch):
        panel.harmony_colors = [(10, 20, 30)]
        panel.parent_app.add_color = lambda rgb: True
        panel.parent_app.refresh_color_display = MagicMock()
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        panel._add_harmony_to_palette()
        panel.parent_app.refresh_color_display.assert_called_once()

    def test_no_refresh_when_all_adds_failed(self, panel):
        panel.harmony_colors = [(10, 20, 30), (40, 50, 60)]
        panel.parent_app.add_color = lambda rgb: False  # palette full, all fail
        panel.parent_app.refresh_color_display = MagicMock()
        panel._add_harmony_to_palette()
        panel.parent_app.refresh_color_display.assert_not_called()

    def test_records_in_color_history_when_available(self, panel, monkeypatch):
        panel.harmony_colors = [(100, 100, 100)]
        panel.parent_app.add_color = lambda rgb: True
        panel.parent_app.refresh_color_display = MagicMock()
        # parent_app has its own color_history (typical for ColorPickerApp)
        history_calls = []
        panel.parent_app.color_history = MagicMock()
        panel.parent_app.color_history.add_color = lambda rgb, source=None: history_calls.append((rgb, source))
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        panel._add_harmony_to_palette()
        assert history_calls == [((100, 100, 100), "harmony")]

    def test_exception_in_one_color_does_not_stop_the_rest(self, panel, monkeypatch):
        # If add_color raises on the first color, the others should still go through
        panel.harmony_colors = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
        added = []

        def add_color(rgb):
            if rgb == (1, 2, 3):
                raise RuntimeError("first one fails")
            added.append(rgb)
            return True

        panel.parent_app.add_color = add_color
        panel.parent_app.refresh_color_display = MagicMock()
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        panel._add_harmony_to_palette()
        # Two colors succeeded
        assert added == [(4, 5, 6), (7, 8, 9)]

# ═════════════════════════════════════════════════════════════════════════════
# 11.  ACCESSIBILITY TAB  (Phase 3b-5)
# ═════════════════════════════════════════════════════════════════════════════
# Largest tab by source-line count (510 lines), but most of it is dispatch into
# core.accessibility (already 86% covered). We focus on the seam between the
# UI and ColorAccessibility plus the parser+clipboard interactions.
#
# Targets _update_contrast_check (WCAG ratio + AA/AAA pass/fail labels),
# _update_blindness_sim (5 simulated swatches via ColorAccessibility), the 6
# copy/paste methods (3 sections × {copy, paste}), and _parse_color_text.
# ═════════════════════════════════════════════════════════════════════════════

from core.accessibility import ColorAccessibility, ColorBlindnessType


class TestAccessibilityTabWiring:
    """The Accessibility tab UI must wire up: foreground/background RGB
    spinboxes, three preview QLabels (fg, bg, sample-text), contrast ratio
    label, four WCAG verdict labels, and simulator RGB spinboxes."""

    def test_fg_rgb_spinboxes_exist(self, panel):
        for name in ("access_fg_r", "access_fg_g", "access_fg_b"):
            spin = getattr(panel, name, None)
            assert isinstance(spin, QSpinBox), f"{name} missing or not QSpinBox"
            assert spin.minimum() == 0 and spin.maximum() == 255

    def test_bg_rgb_spinboxes_exist(self, panel):
        for name in ("access_bg_r", "access_bg_g", "access_bg_b"):
            spin = getattr(panel, name, None)
            assert isinstance(spin, QSpinBox), f"{name} missing or not QSpinBox"
            assert spin.minimum() == 0 and spin.maximum() == 255

    def test_simulator_rgb_spinboxes_exist(self, panel):
        for name in ("sim_r", "sim_g", "sim_b"):
            spin = getattr(panel, name, None)
            assert isinstance(spin, QSpinBox), f"{name} missing or not QSpinBox"

    def test_contrast_preview_labels_exist(self, panel):
        # fg preview, bg preview, and sample-text preview
        assert isinstance(panel.access_fg_preview, QLabel)
        assert isinstance(panel.access_bg_preview, QLabel)
        assert isinstance(panel.access_preview_box, QLabel)

    def test_wcag_verdict_labels_exist(self, panel):
        for name in ("wcag_aa_normal", "wcag_aa_large",
                     "wcag_aaa_normal", "wcag_aaa_large"):
            assert isinstance(getattr(panel, name), QLabel)

    def test_contrast_ratio_label_exists(self, panel):
        assert isinstance(panel.contrast_ratio_label, QLabel)


class TestUpdateContrastCheck:
    """`_update_contrast_check` reads the fg/bg spinboxes, calls
    ColorAccessibility.check_contrast(), updates the ratio label, and
    flips each WCAG verdict label between PASS/FAIL stylesheet variants."""

    def _set_fg_bg(self, panel, fg, bg):
        # Suppress the per-spin-change calls during setup, then trigger once at end
        for spin in (panel.access_fg_r, panel.access_fg_g, panel.access_fg_b,
                     panel.access_bg_r, panel.access_bg_g, panel.access_bg_b):
            spin.blockSignals(True)
        panel.access_fg_r.setValue(fg[0])
        panel.access_fg_g.setValue(fg[1])
        panel.access_fg_b.setValue(fg[2])
        panel.access_bg_r.setValue(bg[0])
        panel.access_bg_g.setValue(bg[1])
        panel.access_bg_b.setValue(bg[2])
        for spin in (panel.access_fg_r, panel.access_fg_g, panel.access_fg_b,
                     panel.access_bg_r, panel.access_bg_g, panel.access_bg_b):
            spin.blockSignals(False)
        panel._update_contrast_check()

    def test_black_on_white_gives_max_ratio(self, panel):
        self._set_fg_bg(panel, (0, 0, 0), (255, 255, 255))
        # Black-on-white is exactly 21.00:1 by WCAG definition
        assert "21.00:1" in panel.contrast_ratio_label.text()

    def test_black_on_white_passes_all_wcag(self, panel):
        self._set_fg_bg(panel, (0, 0, 0), (255, 255, 255))
        # All four verdicts should be PASS
        for label_name in ("wcag_aa_normal", "wcag_aa_large",
                           "wcag_aaa_normal", "wcag_aaa_large"):
            label = getattr(panel, label_name)
            assert "PASS" in label.text(), f"{label_name} should PASS for black/white"

    def test_white_on_white_fails_all_wcag(self, panel):
        # 1:1 contrast — fails everything
        self._set_fg_bg(panel, (255, 255, 255), (255, 255, 255))
        for label_name in ("wcag_aa_normal", "wcag_aa_large",
                           "wcag_aaa_normal", "wcag_aaa_large"):
            label = getattr(panel, label_name)
            assert "FAIL" in label.text(), f"{label_name} should FAIL for white/white"

    def test_pass_uses_success_styling(self, panel):
        self._set_fg_bg(panel, (0, 0, 0), (255, 255, 255))
        ss = panel.wcag_aa_normal.styleSheet()
        # Background uses STATUS_SUCCESS_BG
        assert config.STATUS_SUCCESS_BG.lower() in ss.lower()

    def test_fail_uses_error_styling(self, panel):
        self._set_fg_bg(panel, (255, 255, 255), (255, 255, 255))
        ss = panel.wcag_aa_normal.styleSheet()
        assert config.STATUS_ERROR_BG.lower() in ss.lower()

    def test_fg_preview_styled_with_fg_rgb(self, panel):
        self._set_fg_bg(panel, (123, 45, 67), (200, 200, 200))
        ss = panel.access_fg_preview.styleSheet()
        assert "rgb(123, 45, 67)" in ss

    def test_repeated_update_doesnt_corrupt_label_text(self, panel):
        """Regression guard: the source uses `label.text().split(' - ')[0]` to
        strip the previous PASS/FAIL suffix before re-appending. If that logic
        breaks, repeated updates would accrete suffixes like 'AA Normal Text -
        PASS - PASS - FAIL'."""
        # The source resets text to base BEFORE calling set_pass_fail, so it
        # works correctly. Verify by toggling pass→fail→pass.
        self._set_fg_bg(panel, (0, 0, 0), (255, 255, 255))     # all PASS
        self._set_fg_bg(panel, (255, 255, 255), (255, 255, 255))  # all FAIL
        self._set_fg_bg(panel, (0, 0, 0), (255, 255, 255))     # all PASS again
        text = panel.wcag_aa_normal.text()
        # Should be "AA Normal Text - PASS", with exactly one suffix
        assert text.count(" - ") == 1
        assert text == "AA Normal Text - PASS"


class TestUpdateBlindnessSim:
    """`_update_blindness_sim` reads sim_r/g/b, runs simulate_colorblindness for
    5 types (Normal/Protanopia/Deuteranopia/Tritanopia/Achromatopsia), and
    populates the results layout with labelled swatches."""

    def test_creates_five_simulation_swatches(self, panel):
        # Set a vivid color and trigger
        panel.sim_r.setValue(255)
        panel.sim_g.setValue(0)
        panel.sim_b.setValue(0)
        panel._update_blindness_sim()
        # 5 swatches + 1 stretch = 6 layout items
        assert panel.blindness_results_layout.count() == 6

    def test_swatches_labelled_correctly(self, panel):
        panel.sim_r.setValue(128)
        panel.sim_g.setValue(64)
        panel.sim_b.setValue(200)
        panel._update_blindness_sim()
        # Walk the layout and collect all QLabel texts
        all_texts = set()
        for i in range(panel.blindness_results_layout.count()):
            item = panel.blindness_results_layout.itemAt(i)
            if item.widget():
                for lbl in item.widget().findChildren(QLabel):
                    all_texts.add(lbl.text())
        for expected in ("Normal", "Protanopia", "Deuteranopia",
                         "Tritanopia", "Achromatopsia"):
            assert expected in all_texts, f"Missing simulation: {expected}"

    def test_swatch_color_box_uses_simulated_rgb(self, panel, monkeypatch):
        # Stub simulate_colorblindness to return a known sentinel RGB so we can
        # verify the color box stylesheet receives it.
        monkeypatch.setattr(
            ColorAccessibility, "simulate_colorblindness",
            staticmethod(lambda rgb, btype: (42, 84, 168))
        )
        panel.sim_r.setValue(100)
        panel.sim_g.setValue(100)
        panel.sim_b.setValue(100)
        panel._update_blindness_sim()
        # Find any swatch's color box and verify the stylesheet contains the sentinel
        first_swatch = panel.blindness_results_layout.itemAt(0).widget()
        color_box_ss = next(
            (lbl.styleSheet() for lbl in first_swatch.findChildren(QLabel)
             if "background-color" in lbl.styleSheet()),
            ""
        )
        assert "rgb(42, 84, 168)" in color_box_ss

    def test_repeated_updates_clear_old_swatches(self, panel):
        # Two updates in a row should not double the layout count
        panel.sim_r.setValue(50)
        panel._update_blindness_sim()
        first_count = panel.blindness_results_layout.count()
        panel.sim_r.setValue(60)
        panel._update_blindness_sim()
        second_count = panel.blindness_results_layout.count()
        assert first_count == second_count, "swatches accreted instead of being cleared"

    def test_color_preview_styled_with_input_rgb(self, panel):
        panel.sim_r.setValue(99)
        panel.sim_g.setValue(88)
        panel.sim_b.setValue(77)
        panel._update_blindness_sim()
        ss = panel.sim_color_preview.styleSheet()
        assert "rgb(99, 88, 77)" in ss


class TestCopyPasteColorMethods:
    """The 6 copy/paste methods (fg/bg/sim × copy/paste) interact with
    QApplication.clipboard(). Tests verify clipboard reads/writes."""

    def test_copy_fg_color_writes_hex_to_clipboard(self, panel):
        panel.access_fg_r.setValue(0xFF)
        panel.access_fg_g.setValue(0x88)
        panel.access_fg_b.setValue(0x00)
        panel._copy_fg_color()
        assert QApplication.clipboard().text() == "#ff8800"

    def test_copy_bg_color_writes_hex_to_clipboard(self, panel):
        panel.access_bg_r.setValue(0x12)
        panel.access_bg_g.setValue(0x34)
        panel.access_bg_b.setValue(0x56)
        panel._copy_bg_color()
        assert QApplication.clipboard().text() == "#123456"

    def test_copy_sim_color_writes_hex_to_clipboard(self, panel):
        panel.sim_r.setValue(0xAB)
        panel.sim_g.setValue(0xCD)
        panel.sim_b.setValue(0xEF)
        panel._copy_sim_color()
        assert QApplication.clipboard().text() == "#abcdef"

    def test_paste_fg_color_from_hex_clipboard(self, panel):
        QApplication.clipboard().setText("#ff8800")
        panel._paste_fg_color()
        assert panel.access_fg_r.value() == 255
        assert panel.access_fg_g.value() == 136
        assert panel.access_fg_b.value() == 0

    def test_paste_bg_color_from_rgb_clipboard(self, panel):
        QApplication.clipboard().setText("rgb(50, 100, 150)")
        panel._paste_bg_color()
        assert panel.access_bg_r.value() == 50
        assert panel.access_bg_g.value() == 100
        assert panel.access_bg_b.value() == 150

    def test_paste_sim_color_from_csv_clipboard(self, panel):
        QApplication.clipboard().setText("11, 22, 33")
        panel._paste_sim_color()
        assert panel.sim_r.value() == 11
        assert panel.sim_g.value() == 22
        assert panel.sim_b.value() == 33

    def test_paste_invalid_text_is_noop(self, panel):
        # Set a known starting value
        panel.access_fg_r.setValue(50)
        panel.access_fg_g.setValue(50)
        panel.access_fg_b.setValue(50)
        QApplication.clipboard().setText("not a color")
        panel._paste_fg_color()
        # Values unchanged
        assert panel.access_fg_r.value() == 50
        assert panel.access_fg_g.value() == 50
        assert panel.access_fg_b.value() == 50


class TestParseColorText:
    """`_parse_color_text` accepts hex (with/without `#`), RGB(r,g,b), and
    plain comma-separated formats. Returns RGB tuple or None."""

    @pytest.mark.parametrize("text,expected", [
        ("#FF8800", (255, 136, 0)),
        ("#ff8800", (255, 136, 0)),
        ("FF8800", (255, 136, 0)),
        ("ff8800", (255, 136, 0)),
        ("  #FF8800  ", (255, 136, 0)),  # whitespace stripped
        ("#000000", (0, 0, 0)),
        ("#FFFFFF", (255, 255, 255)),
    ])
    def test_hex_parsing(self, panel, text, expected):
        assert panel._parse_color_text(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("rgb(255, 136, 0)", (255, 136, 0)),
        ("RGB(255, 136, 0)", (255, 136, 0)),
        ("rgb( 50 , 100 , 150 )", (50, 100, 150)),  # whitespace tolerance
        ("rgb(0,0,0)", (0, 0, 0)),
    ])
    def test_rgb_parsing(self, panel, text, expected):
        assert panel._parse_color_text(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("255, 136, 0", (255, 136, 0)),
        ("0,0,0", (0, 0, 0)),
        ("100 , 200 , 50", (100, 200, 50)),
    ])
    def test_csv_parsing(self, panel, text, expected):
        assert panel._parse_color_text(text) == expected

    def test_rgb_format_clamps_to_255(self, panel):
        # The RGB regex allows >255 but the parser clamps
        assert panel._parse_color_text("rgb(300, 400, 500)") == (255, 255, 255)

    def test_csv_format_clamps_to_255(self, panel):
        assert panel._parse_color_text("999, 1000, 1001") == (255, 255, 255)

    @pytest.mark.parametrize("text", [
        "",
        "not a color",
        "#GGG",          # invalid hex chars
        "#FFF",          # 3-char hex not supported
        "#FF88000",      # 7 hex chars
        "rgb()",
        "rgb(1, 2)",     # only 2 values
        "1, 2",          # only 2 values
    ])
    def test_invalid_text_returns_none(self, panel, text):
        assert panel._parse_color_text(text) is None

# ═════════════════════════════════════════════════════════════════════════════
# 12.  SHORTCUTS + SETTINGS TABS + PERSISTENCE  (Phase 3b-6, final 3b sub-session)
# ═════════════════════════════════════════════════════════════════════════════
# Targets _create_shortcuts_tab/_create_shortcut_row (mostly view code), the
# Settings tab UI (theme/session/color/export/UI prefs), and the round-trip
# persistence methods: _load_settings_into_ui, _save_ui_to_settings,
# _save_settings_to_file, _reset_settings_to_defaults, _apply_settings.
#
# This sub-session covers the FINAL TWO panel signals:
#   - settings_changed(str, object)
#   - theme_change_requested(str)
# ═════════════════════════════════════════════════════════════════════════════

from PyQt6.QtWidgets import QLineEdit, QScrollArea, QHBoxLayout


class TestShortcutsTab:
    """The Shortcuts tab is mostly static reference content — a scroll area
    full of (key, action) rows organized into 4 sections (File Operations,
    Color Operations, View Controls, Application)."""

    def test_shortcuts_tab_uses_scrollarea(self, panel):
        # The Shortcuts tab is index 4 (0=History, 1=Sessions, 2=Harmony,
        # 3=Accessibility, 4=Shortcuts, 5=Settings)
        shortcuts_widget = panel.tab_widget.widget(4)
        scroll_areas = shortcuts_widget.findChildren(QScrollArea)
        assert len(scroll_areas) >= 1, "Shortcuts tab should contain a QScrollArea"

    def test_shortcuts_tab_lists_known_shortcuts(self, panel):
        shortcuts_widget = panel.tab_widget.widget(4)
        all_text = " ".join(lbl.text() for lbl in shortcuts_widget.findChildren(QLabel))
        # Verify a handful of documented shortcuts are present
        for key in ("Ctrl+O", "Ctrl+S", "Ctrl+E", "Ctrl+G", "Ctrl+K",
                    "Ctrl+,", "F11", "F12"):
            assert key in all_text, f"Shortcut {key} missing from Shortcuts tab"

    def test_shortcuts_tab_lists_section_headers(self, panel):
        shortcuts_widget = panel.tab_widget.widget(4)
        all_text = " ".join(lbl.text() for lbl in shortcuts_widget.findChildren(QLabel))
        for section in ("File Operations", "Color Operations",
                        "View Controls", "Application"):
            assert section in all_text, f"Section header missing: {section}"


class TestCreateShortcutRow:
    """`_create_shortcut_row` builds one row showing the keystroke and action.
    The keystroke label uses the theme's `pressed_bg` background plus a
    monospace font."""

    def test_returns_qhboxlayout(self, panel):
        row = panel._create_shortcut_row("Ctrl+X", "Cut")
        assert isinstance(row, QHBoxLayout)

    def test_row_contains_two_labels(self, panel):
        row = panel._create_shortcut_row("Ctrl+S", "Save")
        # Walk the layout: should have at least 2 widgets (key + action) and a stretch
        widgets = []
        for i in range(row.count()):
            item = row.itemAt(i)
            if item.widget():
                widgets.append(item.widget())
        assert len(widgets) == 2
        assert all(isinstance(w, QLabel) for w in widgets)
        assert widgets[0].text() == "Ctrl+S"
        assert widgets[1].text() == "Save"

    def test_key_label_uses_monospace_font(self, panel):
        row = panel._create_shortcut_row("Ctrl+S", "Save")
        key_label = row.itemAt(0).widget()
        # Stylesheet must mention a monospace family
        ss = key_label.styleSheet()
        assert "Consolas" in ss or "Courier" in ss or "monospace" in ss

    def test_key_label_uses_theme_pressed_bg(self, panel):
        row = panel._create_shortcut_row("Ctrl+S", "Save")
        key_label = row.itemAt(0).widget()
        ss = key_label.styleSheet()
        expected_bg = config.DARK_THEME_COLORS["pressed_bg"]
        assert expected_bg.lower() in ss.lower()


class TestSettingsTabWiring:
    """The Settings tab has theme combo, 4 checkboxes, max-colors line edit,
    sort combo, export-format combo, and 3 action buttons."""

    def test_theme_combo_has_three_options(self, panel):
        assert hasattr(panel, "theme_combo")
        assert isinstance(panel.theme_combo, QComboBox)
        assert panel.theme_combo.count() == 3
        items = [panel.theme_combo.itemText(i) for i in range(3)]
        assert items == ["Dark Mode", "Light Mode", "Image Mode"]

    def test_max_colors_input_exists(self, panel):
        assert hasattr(panel, "max_colors_input")
        assert isinstance(panel.max_colors_input, QLineEdit)

    def test_sort_combo_has_two_options(self, panel):
        assert hasattr(panel, "sort_combo")
        assert panel.sort_combo.count() == 2
        items = [panel.sort_combo.itemText(i) for i in range(2)]
        assert items == ["Hilbert Curve", "HSL"]

    def test_export_format_combo_has_six_options(self, panel):
        assert hasattr(panel, "export_format_combo")
        assert panel.export_format_combo.count() == 6

    def test_settings_tab_checkboxes_exist(self, panel):
        for name in ("autosave_session_check", "autoload_session_check",
                     "preserve_colors_check", "show_tooltips_check",
                     "debug_overlay_check", "remember_size_check",
                     "remember_position_check"):
            cb = getattr(panel, name, None)
            assert isinstance(cb, QCheckBox), f"{name} missing or not QCheckBox"

    def test_settings_tab_has_three_action_buttons(self, panel):
        settings_widget = panel.tab_widget.widget(5)  # index 5 = Settings
        from PyQt6.QtWidgets import QPushButton
        button_texts = {b.text() for b in settings_widget.findChildren(QPushButton)}
        for expected in ("Save Settings", "Reset to Defaults", "Apply"):
            assert expected in button_texts


class TestLoadSettingsIntoUI:
    """`_load_settings_into_ui` reads `settings_manager.settings` and applies
    the values to all UI controls. The constructor calls this once."""

    def test_no_settings_manager_is_noop(self, panel):
        panel.settings_manager = None
        panel._load_settings_into_ui()  # must not raise

    def test_loads_dark_theme_into_combo(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"theme": "dark"})
        panel._load_settings_into_ui()
        assert panel.theme_combo.currentIndex() == 0

    def test_loads_light_theme_into_combo(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"theme": "light"})
        panel._load_settings_into_ui()
        assert panel.theme_combo.currentIndex() == 1

    def test_loads_image_theme_into_combo(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"theme": "image"})
        panel._load_settings_into_ui()
        assert panel.theme_combo.currentIndex() == 2

    def test_loads_max_colors(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"max_colors": 256})
        panel._load_settings_into_ui()
        assert panel.max_colors_input.text() == "256"

    def test_loads_sort_method_hilbert(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"default_sort_method": "hilbert"})
        panel._load_settings_into_ui()
        assert panel.sort_combo.currentIndex() == 0

    def test_loads_sort_method_hsl(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"default_sort_method": "hsl"})
        panel._load_settings_into_ui()
        assert panel.sort_combo.currentIndex() == 1

    def test_loads_export_format(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"export_format": "json"})
        panel._load_settings_into_ui()
        # json maps to index 4 per format_map in source
        assert panel.export_format_combo.currentIndex() == 4

    def test_loads_checkbox_states(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings", {
            "auto_save_session": False,
            "auto_load_session": True,
            "preserve_colors": True,
            "show_tooltips": False,
            "show_debug_overlay": False,
            "remember_window_size": False,
            "remember_window_position": True,
        })
        panel._load_settings_into_ui()
        assert panel.autosave_session_check.isChecked() is False
        assert panel.autoload_session_check.isChecked() is True
        assert panel.preserve_colors_check.isChecked() is True
        assert panel.show_tooltips_check.isChecked() is False
        assert panel.debug_overlay_check.isChecked() is False
        assert panel.remember_size_check.isChecked() is False
        assert panel.remember_position_check.isChecked() is True

    def test_unknown_theme_falls_back_to_index_0(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "settings",
                            {"theme": "rainbow"})  # not in theme_map
        panel._load_settings_into_ui()
        assert panel.theme_combo.currentIndex() == 0


class TestSaveUIToSettings:
    """`_save_ui_to_settings` reads UI controls and calls
    `settings_manager.set(key, value)` for each, then saves to file. The
    `skip_theme` flag suppresses the theme write (used by Apply button to
    avoid double-applying)."""

    def _spy_settings_set(self, panel, monkeypatch):
        """Intercept settings_manager.set and save_settings to capture calls."""
        captured = []
        monkeypatch.setattr(panel.settings_manager, "set",
                            lambda k, v: captured.append((k, v)))
        monkeypatch.setattr(panel.settings_manager, "save_settings",
                            lambda: None)
        return captured

    def test_no_settings_manager_is_noop(self, panel):
        panel.settings_manager = None
        panel._save_ui_to_settings()  # must not raise

    def test_writes_theme_when_skip_theme_false(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel.theme_combo.setCurrentIndex(1)  # light
        panel._save_ui_to_settings(skip_theme=False)
        keys = [k for k, _ in captured]
        assert "theme" in keys
        # Find the theme entry and verify value
        theme_entries = [v for k, v in captured if k == "theme"]
        assert theme_entries == ["light"]

    def test_skip_theme_omits_theme_write(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel._save_ui_to_settings(skip_theme=True)
        keys = [k for k, _ in captured]
        assert "theme" not in keys

    def test_writes_all_expected_keys(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel._save_ui_to_settings(skip_theme=False)
        keys = {k for k, _ in captured}
        for expected in ("theme", "auto_save_session", "auto_load_session",
                         "max_colors", "default_sort_method", "preserve_colors",
                         "export_format", "show_tooltips", "show_debug_overlay",
                         "remember_window_size", "remember_window_position"):
            assert expected in keys, f"missing key: {expected}"

    def test_max_colors_clamped_low(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel.max_colors_input.setText("0")
        panel._save_ui_to_settings()
        max_entries = [v for k, v in captured if k == "max_colors"]
        # max(1, min(1000, 0)) = 1
        assert max_entries == [1]
        # Input is also rewritten to the clamped value
        assert panel.max_colors_input.text() == "1"

    def test_max_colors_clamped_high(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel.max_colors_input.setText("9999")
        panel._save_ui_to_settings()
        max_entries = [v for k, v in captured if k == "max_colors"]
        assert max_entries == [1000]
        assert panel.max_colors_input.text() == "1000"

    def test_invalid_max_colors_resets_to_333(self, panel, monkeypatch):
        captured = self._spy_settings_set(panel, monkeypatch)
        panel.max_colors_input.setText("not a number")
        panel._save_ui_to_settings()
        max_entries = [v for k, v in captured if k == "max_colors"]
        assert max_entries == [333]
        assert panel.max_colors_input.text() == "333"

    def test_calls_save_settings_at_end(self, panel, monkeypatch):
        save_calls = []
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings",
                            lambda: save_calls.append("called"))
        panel._save_ui_to_settings()
        assert save_calls == ["called"]


class TestSaveSettingsToFile:
    """`_save_settings_to_file` is the 'Save Settings' button handler. Calls
    `_save_ui_to_settings(skip_theme=True)` then shows an info dialog."""

    def test_calls_save_with_skip_theme(self, panel, monkeypatch):
        captured = []
        original = panel._save_ui_to_settings
        def spy(skip_theme=False):
            captured.append(skip_theme)
            # Don't call original — settings_manager would write to disk
        monkeypatch.setattr(panel, "_save_ui_to_settings", spy)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel._save_settings_to_file()
        assert captured == [True]

    def test_shows_info_dialog(self, panel, monkeypatch):
        monkeypatch.setattr(panel, "_save_ui_to_settings", lambda **k: None)
        captured = []
        monkeypatch.setattr(_DH, "show_info",
                            lambda self_, msg, title=None, **k: captured.append(msg))
        panel._save_settings_to_file()
        assert len(captured) == 1
        assert "saved" in captured[0].lower()


class TestResetSettingsToDefaults:
    """`_reset_settings_to_defaults` shows a confirm dialog. On Yes, calls
    `settings_manager.reset_to_defaults()` and reloads UI."""

    def test_yes_calls_reset_and_reloads(self, panel, monkeypatch):
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        reset_calls = []
        load_calls = []
        monkeypatch.setattr(panel.settings_manager, "reset_to_defaults",
                            lambda: reset_calls.append("called"))
        monkeypatch.setattr(panel, "_load_settings_into_ui",
                            lambda: load_calls.append("called"))
        panel._reset_settings_to_defaults()
        assert reset_calls == ["called"]
        assert load_calls == ["called"]

    def test_no_does_not_reset(self, panel, monkeypatch):
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: False)
        spy = MagicMock()
        panel.settings_manager.reset_to_defaults = spy
        panel._reset_settings_to_defaults()
        spy.assert_not_called()

    def test_no_settings_manager_after_confirm_is_safe(self, panel, monkeypatch):
        # User confirms but settings_manager is gone — guarded by `if self.settings_manager:`
        monkeypatch.setattr(_DH, "confirm", lambda *a, **k: True)
        panel.settings_manager = None
        panel._reset_settings_to_defaults()  # must not raise


class TestApplySettings:
    """`_apply_settings` is the heart of the persistence story. It:
      1. Saves UI to settings (with skip_theme=True)
      2. Emits `settings_changed(key, value)` for 5 specific keys
      3. Emits `theme_change_requested(theme)` ONLY if selected != current
      4. Shows an info dialog
    These signals are how the main app reacts to user preference changes."""

    def test_emits_settings_changed_for_max_colors(self, panel, qtbot, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel.max_colors_input.setText("250")

        emitted = []
        panel.settings_changed.connect(lambda k, v: emitted.append((k, v)))
        panel._apply_settings()
        assert ("max_colors", 250) in emitted

    def test_emits_settings_changed_for_sort_method(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel.sort_combo.setCurrentIndex(1)  # HSL

        emitted = []
        panel.settings_changed.connect(lambda k, v: emitted.append((k, v)))
        panel._apply_settings()
        assert ("default_sort_method", "hsl") in emitted

    def test_emits_settings_changed_for_all_five_known_keys(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)

        emitted_keys = []
        panel.settings_changed.connect(lambda k, v: emitted_keys.append(k))
        panel._apply_settings()
        for expected in ("max_colors", "default_sort_method",
                         "preserve_colors", "show_tooltips", "show_debug_overlay"):
            assert expected in emitted_keys, f"settings_changed not emitted for {expected}"

    def test_invalid_max_colors_skips_signal(self, panel, monkeypatch):
        # If max_colors text is unparseable, source has try/except and skips
        # the signal silently. Note: _save_ui_to_settings runs FIRST and rewrites
        # the input to "333" — so we patch save to a no-op to keep the bad input.
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(panel, "_save_ui_to_settings", lambda **k: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel.max_colors_input.setText("abc")

        emitted = []
        panel.settings_changed.connect(lambda k, v: emitted.append(k))
        panel._apply_settings()
        # max_colors NOT emitted; the other 4 still are
        assert "max_colors" not in emitted
        # But other keys still fired
        assert "default_sort_method" in emitted

    def test_emits_theme_change_when_theme_differs(self, panel, qtbot, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        # Parent app reports current theme as "dark" (from fixture)
        # Switch combo to "Light Mode" (index 1)
        panel.theme_combo.setCurrentIndex(1)

        with qtbot.waitSignal(panel.theme_change_requested, timeout=500) as blocker:
            panel._apply_settings()
        assert blocker.args == ["light"]

    def test_no_theme_change_signal_when_theme_matches(self, panel, monkeypatch):
        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)
        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        # Parent reports "dark", combo is at "Dark Mode" (index 0) — no signal
        panel.theme_combo.setCurrentIndex(0)

        emitted = []
        panel.theme_change_requested.connect(lambda t: emitted.append(t))
        panel._apply_settings()
        assert emitted == []

    def test_calls_save_ui_to_settings_with_skip_theme(self, panel, monkeypatch):
        captured = []
        monkeypatch.setattr(panel, "_save_ui_to_settings",
                            lambda skip_theme=False: captured.append(skip_theme))
        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)
        panel._apply_settings()
        assert captured == [True]
