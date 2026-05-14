"""
Tests for utils.dialog_helper — DialogHelper class and module-level aliases.

DialogHelper wraps QMessageBox with consistent theming and a small set of
high-level methods (show_error/warning/info/about/custom + confirm +
ask_yes_no_cancel). Each public method ends in `msg_box.exec()` which is
modal and would block the test runner.

Strategy: monkeypatch QMessageBox.exec to return a chosen value AND capture
the QMessageBox instance so we can introspect what was built (icon, title,
text, default button, stylesheet). For show_about we patch QMessageBox.about
since that's a class-level static method, not an instance exec.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QMessageBox, QWidget

from utils.dialog_helper import (
    DialogHelper, DialogResult,
    error, warning, info, confirm,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def captured_exec(monkeypatch):
    """Patch QMessageBox.exec to capture the box instance and return Ok by default.

    Returns a tuple of (capture_list, set_return_value_func). Tests can call
    set_return_value_func(QMessageBox.StandardButton.Yes) to control what
    exec returns for confirm/ask_yes_no_cancel branches.
    """
    captured = []
    return_value = [QMessageBox.StandardButton.Ok]  # mutable default

    def fake_exec(self_box, *args, **kwargs):
        captured.append(self_box)
        return return_value[0].value if hasattr(return_value[0], "value") else return_value[0]

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)

    def set_return(value):
        return_value[0] = value

    return captured, set_return


@pytest.fixture
def parent_widget(qtbot):
    """A real QWidget to use as parent — gives _apply_theme a real Qt object
    to walk up. Mock-only parents don't have the parent() chain."""
    w = QWidget()
    qtbot.addWidget(w)
    return w


# ═════════════════════════════════════════════════════════════════════════════
# show_error / show_warning / show_info — basic icon + title + text behavior
# ═════════════════════════════════════════════════════════════════════════════
class TestShowError:
    def test_sets_critical_icon(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "Something failed")
        assert captured[0].icon() == QMessageBox.Icon.Critical

    def test_uses_default_title_when_none_given(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "msg")
        assert captured[0].windowTitle() == DialogHelper.DEFAULT_ERROR_TITLE

    def test_custom_title_overrides_default(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "msg", title="Custom Boom")
        assert captured[0].windowTitle() == "Custom Boom"

    def test_message_text_set(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "Something failed")
        assert captured[0].text() == "Something failed"

    def test_includes_detailed_text(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "msg", detailed_text="stack trace here")
        assert captured[0].detailedText() == "stack trace here"

    def test_no_detailed_text_when_omitted(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_error(parent_widget, "msg")
        assert captured[0].detailedText() == ""


class TestShowWarning:
    def test_sets_warning_icon(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_warning(parent_widget, "Be careful")
        assert captured[0].icon() == QMessageBox.Icon.Warning

    def test_uses_default_title(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_warning(parent_widget, "msg")
        assert captured[0].windowTitle() == DialogHelper.DEFAULT_WARNING_TITLE

    def test_includes_detailed_text(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_warning(parent_widget, "msg", detailed_text="why")
        assert captured[0].detailedText() == "why"


class TestShowInfo:
    def test_sets_information_icon(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "FYI")
        assert captured[0].icon() == QMessageBox.Icon.Information

    def test_uses_default_title(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "msg")
        assert captured[0].windowTitle() == DialogHelper.DEFAULT_INFO_TITLE


# ═════════════════════════════════════════════════════════════════════════════
# confirm — returns True on Yes, False on No, with default-button toggling
# ═════════════════════════════════════════════════════════════════════════════
class TestConfirm:
    def test_returns_true_on_yes(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.Yes)
        assert DialogHelper.confirm(parent_widget, "Delete?") is True

    def test_returns_false_on_no(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.No)
        assert DialogHelper.confirm(parent_widget, "Delete?") is False

    def test_default_no_when_not_specified(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.confirm(parent_widget, "Delete?")
        # defaultButton() returns the QPushButton; standardButton() maps it back to the enum
        box = captured[0]
        assert box.standardButton(box.defaultButton()) == QMessageBox.StandardButton.No

    def test_default_yes_when_requested(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.confirm(parent_widget, "Delete?", default_yes=True)
        box = captured[0]
        assert box.standardButton(box.defaultButton()) == QMessageBox.StandardButton.Yes

    def test_uses_question_icon(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.confirm(parent_widget, "Delete?")
        assert captured[0].icon() == QMessageBox.Icon.Question

    def test_custom_title(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.confirm(parent_widget, "Delete?", title="Please Confirm")
        assert captured[0].windowTitle() == "Please Confirm"


# ═════════════════════════════════════════════════════════════════════════════
# ask_yes_no_cancel — three-way result branches
# ═════════════════════════════════════════════════════════════════════════════
class TestAskYesNoCancel:
    def test_returns_yes_on_yes_button(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.Yes)
        assert DialogHelper.ask_yes_no_cancel(parent_widget, "Save?") == DialogResult.YES

    def test_returns_no_on_no_button(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.No)
        assert DialogHelper.ask_yes_no_cancel(parent_widget, "Save?") == DialogResult.NO

    def test_returns_cancel_on_cancel_button(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.Cancel)
        assert DialogHelper.ask_yes_no_cancel(parent_widget, "Save?") == DialogResult.CANCEL


# ═════════════════════════════════════════════════════════════════════════════
# show_about — uses QMessageBox.about (class static method, not instance exec)
# ═════════════════════════════════════════════════════════════════════════════
class TestShowAbout:
    def test_calls_qmessagebox_about(self, monkeypatch, parent_widget):
        about_calls = []
        monkeypatch.setattr(
            QMessageBox, "about",
            lambda parent, title, text: about_calls.append((parent, title, text))
        )
        DialogHelper.show_about(
            parent_widget, "RNV Color Picker", "3.0.3",
            "Professional color extraction"
        )
        assert len(about_calls) == 1
        _parent, title, text = about_calls[0]
        assert title == "About RNV Color Picker"
        assert "RNV Color Picker" in text
        assert "3.0.3" in text
        assert "Professional color extraction" in text

    def test_includes_copyright_when_provided(self, monkeypatch, parent_widget):
        about_calls = []
        monkeypatch.setattr(
            QMessageBox, "about",
            lambda parent, title, text: about_calls.append((parent, title, text))
        )
        DialogHelper.show_about(
            parent_widget, "App", "1.0", "desc", copyright_info="© 2026 Me"
        )
        _parent, _title, text = about_calls[0]
        assert "© 2026 Me" in text

    def test_omits_copyright_when_none(self, monkeypatch, parent_widget):
        about_calls = []
        monkeypatch.setattr(
            QMessageBox, "about",
            lambda parent, title, text: about_calls.append((parent, title, text))
        )
        DialogHelper.show_about(parent_widget, "App", "1.0", "desc")
        _parent, _title, text = about_calls[0]
        # copyright is wrapped in <i>...</i> — verify no italic tag at all
        assert "<i>" not in text


# ═════════════════════════════════════════════════════════════════════════════
# show_custom — flexible escape hatch
# ═════════════════════════════════════════════════════════════════════════════
class TestShowCustom:
    def test_returns_button_clicked(self, captured_exec, parent_widget):
        captured, set_return = captured_exec
        set_return(QMessageBox.StandardButton.Ok)
        result = DialogHelper.show_custom(
            parent_widget, "Title", "Message",
            buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        assert result == QMessageBox.StandardButton.Ok.value

    def test_sets_title_and_text(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_custom(parent_widget, "MyTitle", "MyMessage")
        assert captured[0].windowTitle() == "MyTitle"
        assert captured[0].text() == "MyMessage"

    def test_default_button_applied(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_custom(
            parent_widget, "T", "M",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.Yes,
        )
        box = captured[0]
        assert box.standardButton(box.defaultButton()) == QMessageBox.StandardButton.Yes

    def test_detailed_text_set(self, captured_exec, parent_widget):
        captured, _ = captured_exec
        DialogHelper.show_custom(parent_widget, "T", "M", detailed_text="verbose")
        assert captured[0].detailedText() == "verbose"


# ═════════════════════════════════════════════════════════════════════════════
# _apply_theme — theme detection via parent walk
# ═════════════════════════════════════════════════════════════════════════════
class TestApplyTheme:
    def test_dark_theme_applies_dark_style(self, captured_exec, parent_widget):
        # Parent has a theme_manager attribute reporting "dark"
        parent_widget.theme_manager = MagicMock()
        parent_widget.theme_manager.current_theme = "dark"
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "msg")
        # The applied stylesheet should be non-empty
        assert captured[0].styleSheet() != ""

    def test_light_theme_applies_light_style(self, captured_exec, parent_widget):
        parent_widget.theme_manager = MagicMock()
        parent_widget.theme_manager.current_theme = "light"
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "msg")
        assert captured[0].styleSheet() != ""

    def test_image_theme_applies_image_style(self, captured_exec, parent_widget):
        parent_widget.theme_manager = MagicMock()
        parent_widget.theme_manager.current_theme = "image"
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "msg")
        assert captured[0].styleSheet() != ""

    def test_no_parent_uses_default_dark(self, captured_exec):
        # Pass parent=None — _apply_theme should still set a stylesheet (the dark default)
        captured, _ = captured_exec
        DialogHelper.show_info(None, "msg")
        assert captured[0].styleSheet() != ""

    def test_themed_dialogs_disabled_skips_styling(self, captured_exec, parent_widget, monkeypatch):
        # Toggle USE_THEMED_DIALOGS off — _apply_theme should early-return
        monkeypatch.setattr(DialogHelper, "USE_THEMED_DIALOGS", False)
        captured, _ = captured_exec
        DialogHelper.show_info(parent_widget, "msg")
        # No stylesheet applied
        assert captured[0].styleSheet() == ""

    def test_parent_app_chain_walked(self, captured_exec, qtbot):
        """Some widgets store their parent app reference as `.parent_app` — the
        helper should walk that chain too."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.parent_app = MagicMock()
        parent.parent_app.theme_manager = MagicMock()
        parent.parent_app.theme_manager.current_theme = "light"
        captured, _ = captured_exec
        DialogHelper.show_info(parent, "msg")
        assert captured[0].styleSheet() != ""


# ═════════════════════════════════════════════════════════════════════════════
# Module-level convenience aliases
# ═════════════════════════════════════════════════════════════════════════════
class TestModuleAliases:
    """error/warning/info/confirm functions at module scope are thin wrappers
    around DialogHelper.* — verify they delegate correctly."""

    def test_error_alias_delegates(self, monkeypatch, parent_widget):
        calls = []
        monkeypatch.setattr(
            DialogHelper, "show_error",
            lambda *a, **k: calls.append((a, k))
        )
        error(parent_widget, "msg", title="t")
        assert len(calls) == 1
        assert calls[0][0] == (parent_widget, "msg", "t")

    def test_warning_alias_delegates(self, monkeypatch, parent_widget):
        calls = []
        monkeypatch.setattr(
            DialogHelper, "show_warning",
            lambda *a, **k: calls.append((a, k))
        )
        warning(parent_widget, "msg", title="t")
        assert len(calls) == 1

    def test_info_alias_delegates(self, monkeypatch, parent_widget):
        calls = []
        monkeypatch.setattr(
            DialogHelper, "show_info",
            lambda *a, **k: calls.append((a, k))
        )
        info(parent_widget, "msg")
        assert len(calls) == 1

    def test_confirm_alias_delegates_and_returns(self, monkeypatch, parent_widget):
        monkeypatch.setattr(
            DialogHelper, "confirm",
            lambda parent, message, title=None: True
        )
        assert confirm(parent_widget, "Delete?") is True
