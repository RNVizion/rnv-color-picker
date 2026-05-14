"""
DialogHelper - Consistent dialog interface for RNV Color Picker
Standardizes QMessageBox and QInputDialog calls across the application

Usage Examples:
    # Show error
    DialogHelper.show_error(self, "Failed to load file!")
    
    # Show warning
    DialogHelper.show_warning(self, "Color values out of range")
    
    # Show info
    DialogHelper.show_info(self, "Settings saved successfully")
    
    # Confirm action
    if DialogHelper.confirm(self, "Delete this color?"):
        delete_color()
    
    # Ask yes/no/cancel
    result = DialogHelper.ask_yes_no_cancel(self, "Save changes?")
    if result == DialogResult.YES:
        save()
    
    # Themed integer input (replaces QInputDialog.getInt)
    num, ok = DialogHelper.get_int(
        self, "Number of Colors", "How many dominant colors?",
        value=5, min_value=2, max_value=33
    )
    
    # Themed text input (replaces QInputDialog.getText)
    name, ok = DialogHelper.get_text(
        self, "Save Session", "Enter session name:", text="palette_5"
    )
"""

from PyQt6.QtWidgets import QMessageBox, QWidget, QInputDialog, QLineEdit
from enum import Enum

from utils.logger import Logger
from utils.config import (
    DARK_THEME_COLORS, LIGHT_THEME_COLORS, IMAGE_MODE_COLORS,
    get_theme_colors,
)

logger = Logger("DialogHelper")


class DialogResult(Enum):
    """Dialog result options."""
    YES = 1
    NO = 2
    CANCEL = 3
    OK = 4


# ============================================================================
# DIALOG STYLESHEET BUILDER
# ============================================================================

def _build_dialog_stylesheet(theme: dict) -> str:
    """
    Build a dialog stylesheet from a theme dict.
    
    Covers both QMessageBox and QInputDialog so every dialog routed through
    DialogHelper looks identical regardless of dialog type. All colors are
    pulled from the theme — no hardcoded values. This is the single source
    of styling for every DialogHelper dialog.
    """
    return f"""
    /* ---------- Dialog frame & label ---------- */
    QMessageBox, QInputDialog {{
        background-color: {theme['dialog_bg']};
        color: {theme['text_primary']};
    }}
    QMessageBox QLabel, QInputDialog QLabel {{
        color: {theme['text_primary']};
        font-size: 12px;
    }}
    
    /* ---------- Input fields (QInputDialog only) ---------- */
    QInputDialog QLineEdit,
    QInputDialog QSpinBox,
    QInputDialog QDoubleSpinBox {{
        background-color: {theme['button_bg']};
        color: {theme['text_primary']};
        border: 1px solid {theme['border_hover']};
        border-radius: 3px;
        padding: 4px 6px;
        min-height: 20px;
        selection-background-color: {theme['button_hover_bg']};
        selection-color: {theme['button_hover_text']};
    }}
    QInputDialog QLineEdit:focus,
    QInputDialog QSpinBox:focus,
    QInputDialog QDoubleSpinBox:focus {{
        border: 1px solid {theme['button_hover_border']};
    }}
    QInputDialog QSpinBox::up-button,
    QInputDialog QDoubleSpinBox::up-button,
    QInputDialog QSpinBox::down-button,
    QInputDialog QDoubleSpinBox::down-button {{
        background-color: {theme['button_bg']};
        border: 1px solid {theme['border_hover']};
        width: 16px;
    }}
    QInputDialog QSpinBox::up-button:hover,
    QInputDialog QDoubleSpinBox::up-button:hover,
    QInputDialog QSpinBox::down-button:hover,
    QInputDialog QDoubleSpinBox::down-button:hover {{
        background-color: {theme['button_hover_bg']};
        border: 1px solid {theme['button_hover_border']};
    }}
    QInputDialog QSpinBox::up-button:pressed,
    QInputDialog QDoubleSpinBox::up-button:pressed,
    QInputDialog QSpinBox::down-button:pressed,
    QInputDialog QDoubleSpinBox::down-button:pressed {{
        background-color: {theme['button_pressed_bg']};
    }}
    
    /* ---------- Buttons (shared across QMessageBox + QInputDialog) ---------- */
    QMessageBox QPushButton, QInputDialog QPushButton {{
        background-color: {theme['button_bg']};
        color: {theme['button_text']};
        border: 2px solid {theme['border_hover']};
        padding: 6px 16px;
        border-radius: 4px;
        min-width: 70px;
        font-weight: bold;
    }}
    QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{
        background-color: {theme['button_hover_bg']};
        border: 2px solid {theme['button_hover_border']};
        color: {theme['button_hover_text']};
    }}
    QMessageBox QPushButton:pressed, QInputDialog QPushButton:pressed {{
        background-color: {theme['button_pressed_bg']};
        border: 2px solid {theme['button_pressed_bg']};
        color: {theme['button_pressed_text']};
    }}
    QMessageBox QPushButton:default, QInputDialog QPushButton:default {{
        background-color: {theme['pressed_bg']};
        color: {theme['text_primary']};
        border: 2px solid {theme['checkbox_border']};
    }}
    QMessageBox QPushButton:default:hover, QInputDialog QPushButton:default:hover {{
        background-color: {theme['hover_bg']};
        border: 2px solid {theme['button_hover_border']};
        color: {theme['button_hover_text']};
    }}
    QMessageBox QPushButton:default:pressed, QInputDialog QPushButton:default:pressed {{
        background-color: {theme['button_pressed_bg']};
        border: 2px solid {theme['button_pressed_bg']};
        color: {theme['button_pressed_text']};
    }}
    """


# Pre-build the default stylesheets from the theme dicts so callers don't
# have to rebuild every time. If a theme dict is updated in config.py, these
# reflect the change on next program start (single source of truth preserved).
DARK_DIALOG_STYLE  = _build_dialog_stylesheet(DARK_THEME_COLORS)
LIGHT_DIALOG_STYLE = _build_dialog_stylesheet(LIGHT_THEME_COLORS)
IMAGE_DIALOG_STYLE = _build_dialog_stylesheet(IMAGE_MODE_COLORS)


class DialogHelper:
    """
    Centralized dialog management for consistent UX.
    
    Benefits:
    - Consistent styling across all dialogs (QMessageBox + QInputDialog)
    - Theme-aware dialogs
    - Less code duplication
    - Single point to customize all dialogs
    """
    
    # Default window titles
    DEFAULT_ERROR_TITLE = "Error"
    DEFAULT_WARNING_TITLE = "Warning"
    DEFAULT_INFO_TITLE = "Information"
    DEFAULT_CONFIRM_TITLE = "Confirm"
    
    # Theme support (can be customized)
    USE_THEMED_DIALOGS = True
    
    @staticmethod
    def _apply_theme(dialog: QWidget, parent: QWidget | None) -> None:
        """
        Apply theme-appropriate styling to a dialog widget.
        
        Works for any QWidget that supports setStyleSheet — currently
        QMessageBox and QInputDialog.
        
        Args:
            dialog: The dialog widget to style
            parent: Parent widget (used to discover the active theme)
        """
        if not DialogHelper.USE_THEMED_DIALOGS:
            return
        
        # Walk up the parent chain to find the active theme name
        theme_name = 'dark'  # Default
        
        if parent:
            if hasattr(parent, 'theme_manager'):
                theme_name = getattr(parent.theme_manager, 'current_theme', 'dark')
            elif hasattr(parent, 'parent_app') and parent.parent_app:
                if hasattr(parent.parent_app, 'theme_manager'):
                    theme_name = getattr(parent.parent_app.theme_manager, 'current_theme', 'dark')
            else:
                current = parent.parent() if hasattr(parent, 'parent') else None
                while current:
                    if hasattr(current, 'theme_manager'):
                        theme_name = getattr(current.theme_manager, 'current_theme', 'dark')
                        break
                    current = current.parent() if hasattr(current, 'parent') else None
        
        # Pick pre-built stylesheet matching the active theme
        if theme_name == 'light':
            dialog.setStyleSheet(LIGHT_DIALOG_STYLE)
        elif theme_name == 'image':
            dialog.setStyleSheet(IMAGE_DIALOG_STYLE)
        else:
            dialog.setStyleSheet(DARK_DIALOG_STYLE)
    
    @staticmethod
    def show_error(
        parent: QWidget | None,
        message: str,
        title: str | None = None,
        detailed_text: str | None = None
    ) -> None:
        """
        Show error dialog.
        
        Args:
            parent: Parent widget
            message: Error message to display
            title: Optional custom title (default: "Error")
            detailed_text: Optional detailed error info
        
        Example:
            DialogHelper.show_error(self, "Failed to load image!")
            DialogHelper.show_error(self, "File not found", detailed_text=str(exception))
        """
        title = title or DialogHelper.DEFAULT_ERROR_TITLE
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if detailed_text:
            msg_box.setDetailedText(detailed_text)
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        msg_box.exec()
    
    @staticmethod
    def show_warning(
        parent: QWidget | None,
        message: str,
        title: str | None = None,
        detailed_text: str | None = None
    ) -> None:
        """
        Show warning dialog.
        
        Args:
            parent: Parent widget
            message: Warning message to display
            title: Optional custom title (default: "Warning")
            detailed_text: Optional detailed warning info
        
        Example:
            DialogHelper.show_warning(self, "Color values will be clamped to 0-255")
        """
        title = title or DialogHelper.DEFAULT_WARNING_TITLE
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if detailed_text:
            msg_box.setDetailedText(detailed_text)
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        msg_box.exec()
    
    @staticmethod
    def show_info(
        parent: QWidget | None,
        message: str,
        title: str | None = None,
        detailed_text: str | None = None
    ) -> None:
        """
        Show information dialog.
        
        Args:
            parent: Parent widget
            message: Information message to display
            title: Optional custom title (default: "Information")
            detailed_text: Optional detailed info
        
        Example:
            DialogHelper.show_info(self, "Settings saved successfully!")
        """
        title = title or DialogHelper.DEFAULT_INFO_TITLE
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if detailed_text:
            msg_box.setDetailedText(detailed_text)
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        msg_box.exec()
    
    @staticmethod
    def confirm(
        parent: QWidget | None,
        message: str,
        title: str | None = None,
        default_yes: bool = False
    ) -> bool:
        """
        Show yes/no confirmation dialog.
        
        Args:
            parent: Parent widget
            message: Question to ask
            title: Optional custom title (default: "Confirm")
            default_yes: If True, Yes is default button
        
        Returns:
            True if user clicked Yes, False if No
        
        Example:
            if DialogHelper.confirm(self, "Delete this color?"):
                delete_color()
        """
        title = title or DialogHelper.DEFAULT_CONFIRM_TITLE
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if default_yes:
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        else:
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        result = msg_box.exec()
        return result == QMessageBox.StandardButton.Yes
    
    @staticmethod
    def ask_yes_no_cancel(
        parent: QWidget | None,
        message: str,
        title: str | None = None
    ) -> DialogResult:
        """
        Show yes/no/cancel dialog.
        
        Args:
            parent: Parent widget
            message: Question to ask
            title: Optional custom title (default: "Confirm")
        
        Returns:
            DialogResult.YES, DialogResult.NO, or DialogResult.CANCEL
        
        Example:
            result = DialogHelper.ask_yes_no_cancel(self, "Save changes before closing?")
            if result == DialogResult.YES:
                save_and_close()
            elif result == DialogResult.NO:
                close_without_saving()
            # CANCEL = do nothing
        """
        title = title or DialogHelper.DEFAULT_CONFIRM_TITLE
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        result = msg_box.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            return DialogResult.YES
        elif result == QMessageBox.StandardButton.No:
            return DialogResult.NO
        else:
            return DialogResult.CANCEL
    
    @staticmethod
    def show_about(
        parent: QWidget | None,
        app_name: str,
        version: str,
        description: str,
        copyright_info: str | None = None
    ) -> None:
        """
        Show about dialog.
        
        Args:
            parent: Parent widget
            app_name: Application name
            version: Version string
            description: Application description
            copyright_info: Optional copyright information
        
        Example:
            DialogHelper.show_about(
                self,
                "Color Picker",
                "1.0",
                "Professional color extraction application",
                "© 2026 RNV"
            )
        """
        # OPTIMIZED: Use list join instead of string concatenation
        parts = [
            f"<h2>{app_name}</h2>",
            f"<p><b>Version:</b> {version}</p>",
            f"<p>{description}</p>"
        ]
        
        if copyright_info:
            parts.append(f"<p><i>{copyright_info}</i></p>")
        
        message = "".join(parts)
        QMessageBox.about(parent, f"About {app_name}", message)
    
    @staticmethod
    def show_custom(
        parent: QWidget | None,
        title: str,
        message: str,
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default_button: QMessageBox.StandardButton | None = None,
        detailed_text: str | None = None
    ) -> QMessageBox.StandardButton:
        """
        Show custom dialog with full control.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Message to display
            icon: Icon type
            buttons: Button combination
            default_button: Default button
            detailed_text: Optional detailed info
        
        Returns:
            The button that was clicked
        
        Example:
            result = DialogHelper.show_custom(
                self,
                "Custom Dialog",
                "Choose an option",
                icon=QMessageBox.Icon.Question,
                buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)
        
        if default_button:
            msg_box.setDefaultButton(default_button)
        
        if detailed_text:
            msg_box.setDetailedText(detailed_text)
        
        # Apply theme styling
        DialogHelper._apply_theme(msg_box, parent)
        
        return msg_box.exec()
    
    # ========================================================================
    # INPUT DIALOGS (themed equivalents of QInputDialog static helpers)
    # ========================================================================
    
    @staticmethod
    def get_int(
        parent: QWidget | None,
        title: str,
        label: str,
        value: int = 0,
        min_value: int = -2147483647,
        max_value: int = 2147483647,
        step: int = 1,
    ) -> tuple[int, bool]:
        """
        Themed equivalent of QInputDialog.getInt().
        
        Builds a QInputDialog instance (not the static call) so the active
        theme stylesheet can be applied. Return shape matches QInputDialog
        for drop-in replacement.
        
        Args:
            parent: Parent widget
            title: Window title
            label: Prompt label shown above the spin box
            value: Initial spin-box value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Step size for the spin-box arrows
        
        Returns:
            (value, ok) — same shape as QInputDialog.getInt()
        
        Example:
            num, ok = DialogHelper.get_int(
                self, "Number of Colors", "How many dominant colors?",
                value=5, min_value=2, max_value=33
            )
            if ok:
                use(num)
        """
        dialog = QInputDialog(parent)
        dialog.setInputMode(QInputDialog.InputMode.IntInput)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setIntRange(min_value, max_value)
        dialog.setIntValue(value)
        dialog.setIntStep(step)
        
        # Apply theme styling
        DialogHelper._apply_theme(dialog, parent)
        
        ok = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.intValue(), ok
    
    @staticmethod
    def get_text(
        parent: QWidget | None,
        title: str,
        label: str,
        text: str = "",
        echo_mode: QLineEdit.EchoMode = QLineEdit.EchoMode.Normal,
    ) -> tuple[str, bool]:
        """
        Themed equivalent of QInputDialog.getText().
        
        Builds a QInputDialog instance (not the static call) so the active
        theme stylesheet can be applied. Return shape matches QInputDialog
        for drop-in replacement.
        
        Args:
            parent: Parent widget
            title: Window title
            label: Prompt label shown above the line edit
            text: Initial text in the line edit
            echo_mode: Echo mode (Normal, Password, NoEcho, PasswordEchoOnEdit)
        
        Returns:
            (text, ok) — same shape as QInputDialog.getText()
        
        Example:
            name, ok = DialogHelper.get_text(
                self, "Save Session", "Enter session name:",
                text="palette_5_colors"
            )
            if ok and name:
                save_session(name)
        """
        dialog = QInputDialog(parent)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        dialog.setTextEchoMode(echo_mode)
        
        # Apply theme styling
        DialogHelper._apply_theme(dialog, parent)
        
        ok = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.textValue(), ok


# Convenience aliases for shorter code
def error(parent, message, title=None):
    """Shorthand for DialogHelper.show_error()"""
    DialogHelper.show_error(parent, message, title)

def warning(parent, message, title=None):
    """Shorthand for DialogHelper.show_warning()"""
    DialogHelper.show_warning(parent, message, title)

def info(parent, message, title=None):
    """Shorthand for DialogHelper.show_info()"""
    DialogHelper.show_info(parent, message, title)

def confirm(parent, message, title=None):
    """Shorthand for DialogHelper.confirm()"""
    return DialogHelper.confirm(parent, message, title)