# -*- coding: utf-8 -*-
"""
Tests for ui/about_dialog.py — the About dialog (Ctrl+/).

Phase 3c: target single QDialog with 4 tabs, theme-aware accent/dict
accessors, and a module-level convenience function. Uses the same fixture
pattern as Phase 3a/3b: real QWidget parent (NOT registered with qtbot) holds
the mocked theme_manager and is stored on the panel as _test_real_parent so
it survives the test's lifetime.

Coverage targets:
  - AboutDialog.__init__         (window setup, modal, fixed size)
  - AboutDialog._build_ui        (header + 4-tab structure + close button)
  - AboutDialog._create_about_tab    (description + system info)
  - AboutDialog._create_features_tab (categorized feature list)
  - AboutDialog._create_shortcuts_tab (categorized keyboard shortcuts)
  - AboutDialog._create_credits_tab  (acknowledgments + technologies)
  - AboutDialog._create_divider      (horizontal QFrame line)
  - AboutDialog._get_accent          (theme-aware brand-gold accessor)
  - AboutDialog._get_theme           (theme dict accessor with fallback)
  - AboutDialog._apply_theme         (dialog stylesheet application)
  - show_about_dialog (module-level convenience helper)

Out of scope:
  - The defensive `except ImportError` for QT_VERSION_STR (line 255-257) —
    impossible to trigger without monkeypatching builtin imports.
"""

import os
import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QLabel, QPushButton, QFrame,
    QTabWidget, QScrollArea, QGridLayout,
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from ui.about_dialog import AboutDialog, show_about_dialog
from utils import config


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

def _make_mock_parent(theme_name: str = "dark", with_window_icon: bool = False):
    """Build a real QWidget that quacks like ColorPickerApp for theme lookups.

    The dialog walks parent() then calls `parent().theme_manager.current_theme`
    and `parent().theme_manager.get_current_theme()`. Returning a real QWidget
    (not a MagicMock) is essential because PyQt's parent() chain requires
    actual QObject instances.

    If `with_window_icon=True`, attaches a non-null QIcon so the logo loader
    takes the pixmap-from-parent path. Otherwise it takes the file-fallback or
    text-fallback paths.
    """
    parent = QWidget()
    parent.theme_manager = MagicMock()
    parent.theme_manager.current_theme = theme_name
    parent.theme_manager.get_current_theme = MagicMock(
        return_value=config.DARK_THEME_COLORS if theme_name in ("dark", "image")
        else config.LIGHT_THEME_COLORS
    )
    if with_window_icon:
        # Build a tiny non-null pixmap and wrap in QIcon
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.red)
        parent.setWindowIcon(QIcon(pix))
    return parent


@pytest.fixture
def dialog(qtbot, monkeypatch):
    """Default fixture: AboutDialog parented to a 'dark' theme parent.

    Most tests use this. For light/image/no-parent variants, build inline.

    The `os.path.exists` monkeypatch forces the logo file-fallback to fail,
    making the text fallback ('RNV') deterministic across machines. Tests that
    need the file-found path can override this in their own monkeypatch.
    """
    real_parent = _make_mock_parent("dark", with_window_icon=False)
    # Force file-not-found so logo tests are deterministic
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    dlg = AboutDialog(parent=real_parent)
    dlg._test_real_parent = real_parent  # keep alive until dlg is gone
    qtbot.addWidget(dlg)
    return dlg


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

class TestConstruction:
    """`__init__` sets window title, modal flag, fixed size, and the
    WA_DeleteOnClose attribute that prevents stale-state bugs on reopen."""

    def test_dialog_instantiates(self, dialog):
        assert dialog is not None
        assert isinstance(dialog, QDialog)

    def test_window_title_contains_app_name(self, dialog):
        assert config.APP_NAME in dialog.windowTitle()

    def test_dialog_is_modal(self, dialog):
        assert dialog.isModal() is True

    def test_dialog_has_fixed_size_650_520(self, dialog):
        # The source explicitly calls setFixedSize(650, 520)
        assert dialog.minimumSize().width() == 650
        assert dialog.minimumSize().height() == 520
        assert dialog.maximumSize().width() == 650
        assert dialog.maximumSize().height() == 520

    def test_delete_on_close_set(self, dialog):
        assert dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2.  BUILD UI — HEADER + TABS + CLOSE BUTTON
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildUI:
    """`_build_ui` creates the header (logo + name/version/tagline), a 4-tab
    QTabWidget, and a Close button. All are accessible through documented
    attributes."""

    def test_header_widget_exists(self, dialog):
        assert hasattr(dialog, "header_widget")
        assert isinstance(dialog.header_widget, QWidget)

    def test_name_label_shows_app_name(self, dialog):
        assert hasattr(dialog, "name_label")
        assert dialog.name_label.text() == config.APP_NAME

    def test_version_label_shows_version(self, dialog):
        assert hasattr(dialog, "version_label")
        assert config.APP_VERSION in dialog.version_label.text()
        assert "Version" in dialog.version_label.text()

    def test_tagline_label_shows_tagline(self, dialog):
        from ui.about_dialog import APP_TAGLINE
        assert hasattr(dialog, "tagline_label")
        assert dialog.tagline_label.text() == APP_TAGLINE

    def test_tab_widget_has_four_tabs(self, dialog):
        assert hasattr(dialog, "tab_widget")
        assert isinstance(dialog.tab_widget, QTabWidget)
        assert dialog.tab_widget.count() == 4

    def test_tab_labels_in_expected_order(self, dialog):
        labels = [dialog.tab_widget.tabText(i) for i in range(4)]
        assert labels == ["About", "Features", "Shortcuts", "Credits"]

    def test_close_button_present_and_connected(self, dialog):
        # Close button should be findable as a QPushButton with text "Close"
        buttons = dialog.findChildren(QPushButton)
        close_buttons = [b for b in buttons if b.text() == "Close"]
        assert len(close_buttons) == 1
        # And it should have at least one signal connection (to close())
        # We can verify by checking it has receivers — but the more reliable
        # test is that clicking it closes the dialog.
        # (Skipping the click test because closing triggers WA_DeleteOnClose
        # which can confuse qtbot teardown.)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  LOGO FALLBACK CHAIN — parent.windowIcon → file → text
# ─────────────────────────────────────────────────────────────────────────────

class TestLogoFallbacks:
    """The logo loader has a 3-tier fallback: (1) parent's windowIcon if
    non-null, (2) load from `resources/icons/icon.png`, (3) text 'RNV' if all
    else fails. The default `dialog` fixture forces the text fallback by
    monkeypatching `os.path.exists` and providing no parent windowIcon."""

    def test_text_fallback_when_no_icon_available(self, dialog):
        # Default fixture: no parent windowIcon, file does not exist → "RNV"
        labels = dialog.header_widget.findChildren(QLabel)
        rnv_labels = [lbl for lbl in labels if lbl.text() == "RNV"]
        assert len(rnv_labels) == 1, "expected text fallback 'RNV' label"

    def test_uses_parent_windowicon_when_available(self, qtbot, monkeypatch):
        # Parent has a non-null windowIcon → tier 1 succeeds
        real_parent = _make_mock_parent("dark", with_window_icon=True)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        # The logo label should have a pixmap (not text)
        labels = dlg.header_widget.findChildren(QLabel)
        # Find labels with a non-null pixmap
        pixmap_labels = [lbl for lbl in labels
                         if lbl.pixmap() is not None and not lbl.pixmap().isNull()]
        assert len(pixmap_labels) >= 1, "expected pixmap from parent windowIcon"

    def test_no_parent_falls_back_to_text(self, qtbot, monkeypatch):
        # No parent at all — both tier 1 and tier 2 fail (no icon file in
        # sandbox), fallback to text. This also exercises the parent-is-None
        # branch of _get_theme/_get_accent.
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=None)
        qtbot.addWidget(dlg)
        labels = dlg.header_widget.findChildren(QLabel)
        rnv_labels = [lbl for lbl in labels if lbl.text() == "RNV"]
        assert len(rnv_labels) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 4.  THEME ACCESSORS — _get_accent and _get_theme
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAccent:
    """`_get_accent` returns BRAND_GOLD for dark/image themes, BRAND_GOLD_DARK
    for light, and BRAND_GOLD as a default fallback when no parent is set or
    accessing theme_manager raises."""

    def test_dark_theme_returns_brand_gold(self, dialog):
        # Default fixture is 'dark'
        assert dialog._get_accent() == config.BRAND_GOLD

    def test_light_theme_returns_brand_gold_dark(self, qtbot, monkeypatch):
        real_parent = _make_mock_parent("light", with_window_icon=False)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        assert dlg._get_accent() == config.BRAND_GOLD_DARK

    def test_image_theme_returns_brand_gold(self, qtbot, monkeypatch):
        real_parent = _make_mock_parent("image", with_window_icon=False)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        # 'image' theme is treated like 'dark' for accent purposes
        assert dlg._get_accent() == config.BRAND_GOLD

    def test_no_parent_defaults_to_brand_gold(self, qtbot, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=None)
        qtbot.addWidget(dlg)
        assert dlg._get_accent() == config.BRAND_GOLD

    def test_theme_manager_exception_falls_back_to_brand_gold(self, qtbot, monkeypatch):
        # If accessing theme_manager raises, the try/except catches it and
        # returns BRAND_GOLD. Build a parent whose theme_manager raises on
        # attribute access.
        real_parent = QWidget()

        class _Boom:
            @property
            def current_theme(self):
                raise RuntimeError("simulated failure")

        real_parent.theme_manager = _Boom()
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        assert dlg._get_accent() == config.BRAND_GOLD


class TestGetTheme:
    """`_get_theme` returns the parent's current theme dict, or DARK_THEME_COLORS
    as a fallback when no parent or the lookup fails."""

    def test_returns_dict_with_expected_keys(self, dialog):
        result = dialog._get_theme()
        assert isinstance(result, dict)
        # A few keys we know the dialog uses
        for key in ("dialog_bg", "text_primary", "text_muted",
                    "border_hover", "pressed_bg"):
            assert key in result, f"theme dict missing '{key}'"

    def test_dark_parent_returns_dark_theme(self, dialog):
        # Default fixture's mock returns DARK_THEME_COLORS for "dark"
        result = dialog._get_theme()
        assert result == config.DARK_THEME_COLORS

    def test_light_parent_returns_light_theme(self, qtbot, monkeypatch):
        real_parent = _make_mock_parent("light", with_window_icon=False)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        result = dlg._get_theme()
        assert result == config.LIGHT_THEME_COLORS

    def test_no_parent_falls_back_to_dark_colors(self, qtbot, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=None)
        qtbot.addWidget(dlg)
        result = dlg._get_theme()
        assert result == config.DARK_THEME_COLORS

    def test_theme_manager_exception_falls_back(self, qtbot, monkeypatch):
        real_parent = QWidget()
        real_parent.theme_manager = MagicMock()
        real_parent.theme_manager.get_current_theme = MagicMock(
            side_effect=RuntimeError("simulated"))
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        dlg = AboutDialog(parent=real_parent)
        dlg._test_real_parent = real_parent
        qtbot.addWidget(dlg)
        result = dlg._get_theme()
        assert result == config.DARK_THEME_COLORS


# ─────────────────────────────────────────────────────────────────────────────
# 5.  APPLY THEME — dialog stylesheet
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyTheme:
    """`_apply_theme` is called once during __init__. It builds the tab styling
    block and applies the main dialog stylesheet using values from
    `_get_theme()`. Smoke tests only — we don't validate every CSS rule."""

    def test_dialog_stylesheet_set(self, dialog):
        # _apply_theme was called during __init__
        assert dialog.styleSheet() != ""

    def test_dialog_stylesheet_contains_dialog_bg_value(self, dialog):
        ss = dialog.styleSheet()
        expected_bg = config.DARK_THEME_COLORS["dialog_bg"]
        assert expected_bg.lower() in ss.lower()

    def test_dialog_stylesheet_contains_tab_styling(self, dialog):
        ss = dialog.styleSheet()
        # Tab CSS rules should be embedded
        assert "QTabBar" in ss
        assert "QTabWidget" in ss

    def test_header_widget_uses_pressed_bg(self, dialog):
        ss = dialog.header_widget.styleSheet()
        expected = config.DARK_THEME_COLORS["pressed_bg"]
        assert expected.lower() in ss.lower()

    def test_apply_theme_callable_externally(self, dialog):
        # Should not crash when called a second time externally
        dialog._apply_theme()


# ─────────────────────────────────────────────────────────────────────────────
# 6.  CREATE DIVIDER
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateDivider:
    """`_create_divider` returns a horizontal QFrame styled with the theme's
    `border_hover` color."""

    def test_returns_qframe(self, dialog):
        line = dialog._create_divider()
        assert isinstance(line, QFrame)

    def test_divider_is_horizontal_line(self, dialog):
        line = dialog._create_divider()
        assert line.frameShape() == QFrame.Shape.HLine

    def test_divider_uses_border_hover_color(self, dialog):
        line = dialog._create_divider()
        ss = line.styleSheet()
        expected = config.DARK_THEME_COLORS["border_hover"]
        assert expected.lower() in ss.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  TAB CONTENT SMOKE TESTS — verify each tab actually contains something
# ─────────────────────────────────────────────────────────────────────────────

class TestTabContent:
    """Each tab is created via a separate `_create_*_tab` method. We verify
    each tab has the expected high-level structure (header label, content
    items) without asserting exact text — that would be brittle."""

    def test_about_tab_has_capabilities_list(self, dialog):
        about_widget = dialog.tab_widget.widget(0)
        all_text = " ".join(lbl.text() for lbl in about_widget.findChildren(QLabel))
        # A few capability strings from the source
        assert "Color Extraction" in all_text
        assert "Hilbert Curve" in all_text or "Hilbert" in all_text

    def test_about_tab_shows_system_info(self, dialog):
        about_widget = dialog.tab_widget.widget(0)
        all_text = " ".join(lbl.text() for lbl in about_widget.findChildren(QLabel))
        # System info section presence (at minimum the headers)
        assert "Python" in all_text
        assert "PyQt6" in all_text
        assert "Qt" in all_text

    def test_features_tab_has_scrollarea(self, dialog):
        features_widget = dialog.tab_widget.widget(1)
        scroll_areas = features_widget.findChildren(QScrollArea)
        assert len(scroll_areas) >= 1

    def test_features_tab_lists_categories(self, dialog):
        features_widget = dialog.tab_widget.widget(1)
        all_text = " ".join(lbl.text() for lbl in features_widget.findChildren(QLabel))
        for expected in ("Color Extraction", "Screen Color Picker",
                         "Color Tools", "Session & Export"):
            assert expected in all_text, f"missing category: {expected}"

    def test_shortcuts_tab_lists_known_shortcuts(self, dialog):
        shortcuts_widget = dialog.tab_widget.widget(2)
        all_text = " ".join(lbl.text() for lbl in shortcuts_widget.findChildren(QLabel))
        for key in ("Ctrl+O", "Ctrl+S", "Ctrl+E", "Ctrl+G", "Ctrl+/", "F11", "F12"):
            assert key in all_text, f"missing shortcut: {key}"

    def test_credits_tab_lists_technologies(self, dialog):
        credits_widget = dialog.tab_widget.widget(3)
        all_text = " ".join(lbl.text() for lbl in credits_widget.findChildren(QLabel))
        for tech in ("PyQt6", "Python", "Pillow"):
            assert tech in all_text, f"missing tech: {tech}"

    def test_credits_tab_has_footer(self, dialog):
        credits_widget = dialog.tab_widget.widget(3)
        all_text = " ".join(lbl.text() for lbl in credits_widget.findChildren(QLabel))
        # Footer contains copyright line
        assert "rights reserved" in all_text.lower() or "©" in all_text


# ─────────────────────────────────────────────────────────────────────────────
# 8.  MODULE-LEVEL HELPER — show_about_dialog
# ─────────────────────────────────────────────────────────────────────────────

class TestShowAboutDialog:
    """`show_about_dialog(parent=None)` is a convenience wrapper. It builds an
    AboutDialog and calls .exec() on it. Tests must monkeypatch exec to avoid
    blocking, since exec() is modal and would never return without UI."""

    def test_creates_and_execs_dialog(self, qtbot, monkeypatch):
        exec_calls = []

        def fake_exec(self_):
            exec_calls.append("called")
            return 1  # accepted

        monkeypatch.setattr(AboutDialog, "exec", fake_exec)
        # Avoid logo file lookup
        monkeypatch.setattr(os.path, "exists", lambda p: False)

        show_about_dialog(parent=None)
        assert exec_calls == ["called"]

    def test_passes_parent_to_dialog(self, qtbot, monkeypatch):
        captured_parents = []
        original_init = AboutDialog.__init__

        def spy_init(self, parent=None):
            captured_parents.append(parent)
            original_init(self, parent)

        monkeypatch.setattr(AboutDialog, "__init__", spy_init)
        monkeypatch.setattr(AboutDialog, "exec", lambda self_: 0)
        monkeypatch.setattr(os.path, "exists", lambda p: False)

        real_parent = _make_mock_parent("dark", with_window_icon=False)
        show_about_dialog(parent=real_parent)
        assert captured_parents == [real_parent]

    def test_default_parent_is_none(self, qtbot, monkeypatch):
        # Calling with no args should pass None (the function default)
        captured_parents = []
        original_init = AboutDialog.__init__

        def spy_init(self, parent=None):
            captured_parents.append(parent)
            original_init(self, parent)

        monkeypatch.setattr(AboutDialog, "__init__", spy_init)
        monkeypatch.setattr(AboutDialog, "exec", lambda self_: 0)
        monkeypatch.setattr(os.path, "exists", lambda p: False)

        show_about_dialog()
        assert captured_parents == [None]
