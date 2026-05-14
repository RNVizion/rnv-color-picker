# -*- coding: utf-8 -*-
"""
Tests for ui/progress_dialog.py and ui/transparent_scroll_widget.py.

Phase 3e covers two more sibling UI files: a progress dialog hierarchy
(ProgressDialog → LoadingDialog, QuickProgressDialog) used during long
extractions, and a small transparent scroll widget used as an overlay in
Image Mode.

Coverage targets:
  - _build_progress_stylesheet   (theme-driven CSS builder)
  - ProgressDialog.__init__      (modal, signal_manager, theme detect)
  - ProgressDialog._apply_theme  (3-way theme branch)
  - ProgressDialog._setup_ui     (title/status/progress_bar/percent/cancel)
  - ProgressDialog.set_progress  (percent calc, label updates)
  - ProgressDialog.set_status    (status label update)
  - ProgressDialog.set_indeterminate (spinning mode toggle)
  - ProgressDialog._on_cancel    (state + signal emission)
  - ProgressDialog.was_cancelled (property)
  - ProgressDialog.closeEvent    (close-as-cancel)
  - LoadingDialog.__init__       (theme detection, progress max)
  - LoadingDialog.update_color_progress (cancellation short-circuit)
  - QuickProgressDialog.__init__ (no-cancel variant)
  - QuickProgressDialog.complete (auto-fill)
  - TransparentScrollWidget.__init__         (cache color, mode default)
  - TransparentScrollWidget.set_transparent_mode (state flip, color arg)
  - TransparentScrollWidget.paintEvent       (fill rect when transparent)

Out of scope:
  - The QTimer.singleShot auto-close in QuickProgressDialog.complete (the
    timer fires asynchronously; testing it requires qtbot.wait, which
    introduces flakiness without much added value).
"""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QDialog, QPushButton, QProgressBar, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.progress_dialog import (
    _build_progress_stylesheet,
    ProgressDialog,
    LoadingDialog,
    QuickProgressDialog,
    DARK_PROGRESS_STYLE,
    LIGHT_PROGRESS_STYLE,
    IMAGE_PROGRESS_STYLE,
)
from ui.transparent_scroll_widget import TransparentScrollWidget
from utils import config


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_parent_with_theme(theme_name: str = "dark"):
    """Build a real QWidget parent with a `theme_manager.current_theme`
    attribute. Must be a QWidget because QDialog's __init__ requires it.
    Returns the widget — caller is responsible for keeping it alive (we
    attach it to the dialog as `_test_real_parent` in the calling tests
    where the dialog is registered with qtbot)."""
    from PyQt6.QtWidgets import QWidget
    parent = QWidget()
    parent.theme_manager = MagicMock()
    parent.theme_manager.current_theme = theme_name
    return parent


# =============================================================================
# 1.  _build_progress_stylesheet
# =============================================================================

class TestBuildProgressStylesheet:
    """Module-level helper: takes a theme dict, returns a CSS string with all
    the colors interpolated. Pure function — easy to verify."""

    def test_dark_theme_produces_nonempty_stylesheet(self):
        ss = _build_progress_stylesheet(config.DARK_THEME_COLORS)
        assert ss != ""
        assert "QDialog" in ss
        assert "QProgressBar" in ss
        assert "QPushButton" in ss

    def test_dark_theme_uses_dark_dialog_bg(self):
        ss = _build_progress_stylesheet(config.DARK_THEME_COLORS)
        assert config.DARK_THEME_COLORS["dialog_bg"].lower() in ss.lower()

    def test_light_theme_uses_light_dialog_bg(self):
        ss = _build_progress_stylesheet(config.LIGHT_THEME_COLORS)
        assert config.LIGHT_THEME_COLORS["dialog_bg"].lower() in ss.lower()

    def test_module_level_constants_prebuilt(self):
        # The module exposes prebuilt stylesheets for backward compat
        assert DARK_PROGRESS_STYLE != ""
        assert LIGHT_PROGRESS_STYLE != ""
        assert IMAGE_PROGRESS_STYLE != ""
        # And they should differ from each other (different theme dicts)
        assert DARK_PROGRESS_STYLE != LIGHT_PROGRESS_STYLE


# =============================================================================
# 2.  ProgressDialog
# =============================================================================

@pytest.fixture
def dialog(qtbot):
    """Default fixture: ProgressDialog with cancel button, no parent."""
    dlg = ProgressDialog(title="Test", message="Working...",
                         can_cancel=True, parent=None, is_dark=True)
    qtbot.addWidget(dlg)
    return dlg


class TestProgressDialogConstruction:
    """`__init__` sets window title, modal=True, minimumWidth=400, signal_manager
    attached, theme detection from parent."""

    def test_dialog_instantiates(self, dialog):
        assert isinstance(dialog, QDialog)

    def test_window_title_set(self, dialog):
        assert dialog.windowTitle() == "Test"

    def test_dialog_is_modal(self, dialog):
        assert dialog.isModal() is True

    def test_min_width_400(self, dialog):
        assert dialog.minimumWidth() == 400

    def test_signal_manager_attached(self, dialog):
        assert dialog.signal_manager is not None

    def test_default_theme_is_dark(self, dialog):
        # Default fixture: is_dark=True, no parent → theme stays dark
        assert dialog._theme_name == "dark"
        assert dialog._is_dark is True

    def test_is_dark_false_uses_light(self, qtbot):
        dlg = ProgressDialog(is_dark=False)
        qtbot.addWidget(dlg)
        assert dlg._theme_name == "light"
        assert dlg._is_dark is False

    def test_parent_with_dark_theme_overrides_is_dark_arg(self, qtbot):
        # Parent's theme_manager wins over the is_dark arg
        parent = _make_parent_with_theme("dark")
        dlg = ProgressDialog(is_dark=False, parent=parent)
        dlg._test_real_parent = parent  # keep alive
        qtbot.addWidget(dlg)
        assert dlg._theme_name == "dark"

    def test_parent_with_image_theme_detected(self, qtbot):
        parent = _make_parent_with_theme("image")
        dlg = ProgressDialog(parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._theme_name == "image"
        # 'image' is dark-like for the legacy _is_dark flag
        assert dlg._is_dark is True

    def test_parent_with_light_theme_detected(self, qtbot):
        parent = _make_parent_with_theme("light")
        dlg = ProgressDialog(parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._theme_name == "light"
        assert dlg._is_dark is False

    def test_starts_uncancelled(self, dialog):
        assert dialog._cancelled is False
        assert dialog.was_cancelled is False


class TestApplyTheme:
    """`_apply_theme` is called during __init__. Picks one of three pre-built
    stylesheets based on `_theme_name`."""

    def test_dark_theme_applies_dark_style(self, dialog):
        # Default fixture is dark
        assert dialog.styleSheet() == DARK_PROGRESS_STYLE

    def test_light_theme_applies_light_style(self, qtbot):
        dlg = ProgressDialog(is_dark=False)
        qtbot.addWidget(dlg)
        assert dlg.styleSheet() == LIGHT_PROGRESS_STYLE

    def test_image_theme_applies_image_style(self, qtbot):
        parent = _make_parent_with_theme("image")
        dlg = ProgressDialog(parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg.styleSheet() == IMAGE_PROGRESS_STYLE


class TestSetupUI:
    """`_setup_ui` builds title/status/progress_bar/percent_label widgets and
    optionally a cancel button."""

    def test_title_label_exists_with_window_title(self, dialog):
        assert hasattr(dialog, "title_label")
        assert dialog.title_label.text() == "Test"

    def test_status_label_shows_message(self, dialog):
        assert hasattr(dialog, "status_label")
        assert dialog.status_label.text() == "Working..."

    def test_status_label_default_when_message_empty(self, qtbot):
        dlg = ProgressDialog(message="")
        qtbot.addWidget(dlg)
        assert dlg.status_label.text() == "Please wait..."

    def test_progress_bar_initialized(self, dialog):
        assert hasattr(dialog, "progress_bar")
        assert isinstance(dialog.progress_bar, QProgressBar)
        assert dialog.progress_bar.minimum() == 0
        assert dialog.progress_bar.maximum() == 100
        assert dialog.progress_bar.value() == 0

    def test_percent_label_starts_at_zero(self, dialog):
        assert hasattr(dialog, "percent_label")
        assert dialog.percent_label.text() == "0%"

    def test_cancel_button_exists_when_can_cancel(self, dialog):
        assert dialog.cancel_button is not None
        assert isinstance(dialog.cancel_button, QPushButton)
        assert dialog.cancel_button.text() == "Cancel"

    def test_no_cancel_button_when_can_cancel_false(self, qtbot):
        dlg = ProgressDialog(can_cancel=False)
        qtbot.addWidget(dlg)
        assert dlg.cancel_button is None


class TestSetProgress:
    """`set_progress(current, total)` updates the progress bar and percent
    label."""

    def test_sets_progress_bar_value(self, dialog):
        dialog.set_progress(50, 100)
        assert dialog.progress_bar.value() == 50
        assert dialog.progress_bar.maximum() == 100

    def test_updates_percent_label(self, dialog):
        dialog.set_progress(25, 100)
        assert "25%" in dialog.percent_label.text()

    def test_format_string_shows_current_over_total(self, dialog):
        dialog.set_progress(7, 42)
        assert dialog.progress_bar.format() == "7 / 42"

    def test_zero_total_yields_zero_percent(self, dialog):
        # Avoids division-by-zero — source guards with `if total > 0`
        dialog.set_progress(5, 0)
        assert "0%" in dialog.percent_label.text()

    def test_full_progress_shows_100_percent(self, dialog):
        dialog.set_progress(50, 50)
        assert "100%" in dialog.percent_label.text()


class TestSetStatusAndIndeterminate:
    """`set_status` updates the status label. `set_indeterminate` switches the
    progress bar between determinate (max=100) and indeterminate (max=0)."""

    def test_set_status_updates_label(self, dialog):
        dialog.set_status("Now extracting colors...")
        assert dialog.status_label.text() == "Now extracting colors..."

    def test_set_indeterminate_true_zeros_max(self, dialog):
        dialog.set_indeterminate(True)
        assert dialog.progress_bar.maximum() == 0
        assert dialog.progress_bar.format() == ""
        assert dialog.percent_label.text() == "Working..."

    def test_set_indeterminate_default_arg_is_true(self, dialog):
        # Default arg is True per source signature
        dialog.set_indeterminate()
        assert dialog.progress_bar.maximum() == 0

    def test_set_indeterminate_false_restores_determinate(self, dialog):
        dialog.set_indeterminate(True)
        dialog.set_indeterminate(False)
        assert dialog.progress_bar.maximum() == 100
        assert dialog.progress_bar.format() == "%v / %m"


class TestCancellation:
    """`_on_cancel` flips state, disables the button, updates labels, and
    emits the `cancelled` signal. `closeEvent` invokes `_on_cancel` if not
    already cancelled."""

    def test_on_cancel_flips_state(self, dialog):
        dialog._on_cancel()
        assert dialog._cancelled is True
        assert dialog.was_cancelled is True

    def test_on_cancel_emits_signal(self, dialog, qtbot):
        with qtbot.waitSignal(dialog.cancelled, timeout=500):
            dialog._on_cancel()

    def test_on_cancel_disables_button(self, dialog):
        dialog._on_cancel()
        assert dialog.cancel_button.isEnabled() is False
        assert dialog.cancel_button.text() == "Cancelling..."

    def test_on_cancel_updates_status_label(self, dialog):
        dialog._on_cancel()
        assert "cancel" in dialog.status_label.text().lower()

    def test_on_cancel_safe_when_no_cancel_button(self, qtbot):
        dlg = ProgressDialog(can_cancel=False)
        qtbot.addWidget(dlg)
        dlg._on_cancel()  # must not crash with cancel_button=None
        assert dlg._cancelled is True

    def test_close_event_triggers_cancel_if_not_cancelled(self, dialog):
        from PyQt6.QtGui import QCloseEvent
        dialog.closeEvent(QCloseEvent())
        assert dialog._cancelled is True

    def test_close_event_skips_cancel_if_already_cancelled(self, dialog, qtbot):
        # Pre-cancel via direct method, then verify closeEvent doesn't re-emit
        dialog._on_cancel()
        emit_count = []
        dialog.cancelled.connect(lambda: emit_count.append(1))
        from PyQt6.QtGui import QCloseEvent
        dialog.closeEvent(QCloseEvent())
        # Should NOT have emitted again
        assert emit_count == []


# =============================================================================
# 3.  LoadingDialog (subclass of ProgressDialog)
# =============================================================================

class TestLoadingDialog:
    """`LoadingDialog` is for color extraction. It pre-sets the progress max
    to total_colors and exposes `update_color_progress` which returns False
    if the user has cancelled."""

    def test_construction_sets_total_colors(self, qtbot):
        dlg = LoadingDialog(title="Loading", total_colors=42)
        qtbot.addWidget(dlg)
        assert dlg.total_colors == 42
        assert dlg.progress_bar.maximum() == 42

    def test_zero_total_colors_uses_max_100(self, qtbot):
        # Edge case: defaults to 100 when total_colors is 0
        dlg = LoadingDialog(total_colors=0)
        qtbot.addWidget(dlg)
        assert dlg.progress_bar.maximum() == 100

    def test_construction_status_message_includes_count(self, qtbot):
        dlg = LoadingDialog(total_colors=333)
        qtbot.addWidget(dlg)
        assert "333" in dlg.status_label.text()

    def test_construction_with_dark_theme_parent(self, qtbot):
        parent = _make_parent_with_theme("dark")
        dlg = LoadingDialog(total_colors=10, parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._is_dark is True

    def test_construction_with_light_theme_parent(self, qtbot):
        parent = _make_parent_with_theme("light")
        dlg = LoadingDialog(total_colors=10, parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._is_dark is False

    def test_update_progress_returns_true_when_not_cancelled(self, qtbot):
        dlg = LoadingDialog(total_colors=100)
        qtbot.addWidget(dlg)
        assert dlg.update_color_progress(50) is True

    def test_update_progress_returns_false_when_cancelled(self, qtbot):
        dlg = LoadingDialog(total_colors=100)
        qtbot.addWidget(dlg)
        dlg._on_cancel()
        assert dlg.update_color_progress(50) is False

    def test_update_progress_advances_bar(self, qtbot):
        dlg = LoadingDialog(total_colors=200)
        qtbot.addWidget(dlg)
        dlg.update_color_progress(100)
        assert dlg.progress_bar.value() == 100

    def test_update_progress_with_custom_status(self, qtbot):
        dlg = LoadingDialog(total_colors=10)
        qtbot.addWidget(dlg)
        dlg.update_color_progress(3, status="Custom message")
        assert dlg.status_label.text() == "Custom message"

    def test_update_progress_default_status_includes_counts(self, qtbot):
        dlg = LoadingDialog(total_colors=10)
        qtbot.addWidget(dlg)
        dlg.update_color_progress(5)
        assert "5" in dlg.status_label.text()
        assert "10" in dlg.status_label.text()


# =============================================================================
# 4.  QuickProgressDialog
# =============================================================================

class TestQuickProgressDialog:
    """`QuickProgressDialog` is a no-cancel variant for fast operations.
    `complete()` fills the bar to 100% and shows a completion message."""

    def test_no_cancel_button(self, qtbot):
        dlg = QuickProgressDialog(title="Quick op")
        qtbot.addWidget(dlg)
        assert dlg.cancel_button is None

    def test_minimum_width_300(self, qtbot):
        dlg = QuickProgressDialog()
        qtbot.addWidget(dlg)
        assert dlg.minimumWidth() == 300

    def test_construction_with_dark_theme_parent(self, qtbot):
        parent = _make_parent_with_theme("dark")
        dlg = QuickProgressDialog(parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._is_dark is True

    def test_construction_with_light_theme_parent(self, qtbot):
        parent = _make_parent_with_theme("light")
        dlg = QuickProgressDialog(parent=parent)
        dlg._test_real_parent = parent
        qtbot.addWidget(dlg)
        assert dlg._is_dark is False

    def test_complete_sets_progress_to_full(self, qtbot):
        dlg = QuickProgressDialog()
        qtbot.addWidget(dlg)
        dlg.complete()
        assert dlg.progress_bar.value() == 100
        assert dlg.progress_bar.maximum() == 100

    def test_complete_updates_status(self, qtbot):
        dlg = QuickProgressDialog()
        qtbot.addWidget(dlg)
        dlg.complete(message="All done!")
        assert dlg.status_label.text() == "All done!"

    def test_complete_default_message(self, qtbot):
        dlg = QuickProgressDialog()
        qtbot.addWidget(dlg)
        dlg.complete()
        assert "Complete" in dlg.status_label.text()

    def test_complete_sets_done_label(self, qtbot):
        dlg = QuickProgressDialog()
        qtbot.addWidget(dlg)
        dlg.complete()
        assert dlg.percent_label.text() == "Done!"


# =============================================================================
# 5.  TransparentScrollWidget
# =============================================================================

class TestTransparentScrollWidget:
    """Small custom QWidget that paints a semi-transparent background when
    transparent mode is enabled."""

    def test_widget_instantiates(self, qtbot):
        w = TransparentScrollWidget(parent=None)
        qtbot.addWidget(w)

    def test_default_bg_color_is_overlay_black(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        # Source uses QColorCache.get(OVERLAY_BLACK_MEDIUM) — should be a QColor
        assert w.bg_color is not None

    def test_default_not_in_transparent_mode(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        assert w.is_transparent_mode is False

    def test_set_transparent_mode_enables(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        w.set_transparent_mode(True)
        assert w.is_transparent_mode is True

    def test_set_transparent_mode_disables(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        w.set_transparent_mode(True)
        w.set_transparent_mode(False)
        assert w.is_transparent_mode is False

    def test_set_transparent_mode_with_custom_color(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        custom = QColor(255, 0, 0, 128)
        w.set_transparent_mode(True, color=custom)
        assert w.bg_color is custom

    def test_set_transparent_mode_no_color_keeps_existing(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        original = w.bg_color
        w.set_transparent_mode(True)  # no color arg
        assert w.bg_color is original

    def test_paint_event_in_transparent_mode_does_not_crash(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        w.set_transparent_mode(True)
        w.show()
        w.repaint()  # exercises the paint branch with fillRect

    def test_paint_event_in_normal_mode_does_not_crash(self, qtbot):
        w = TransparentScrollWidget()
        qtbot.addWidget(w)
        # is_transparent_mode is False by default
        w.show()
        w.repaint()  # exercises the super().paintEvent path
