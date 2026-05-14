"""
Progress dialog for long-running operations.

Provides visual feedback during:
- Color extraction
- K-means clustering
- Palette export
- Image loading

Python 3.13 optimized.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from utils.logger import Logger
from utils.signal_manager import SignalConnectionManager
from utils.config import (
    DARK_THEME_COLORS, LIGHT_THEME_COLORS, IMAGE_MODE_COLORS,
)

logger = Logger("ProgressDialog")
SIGNAL_MANAGER_AVAILABLE = True


# ============================================================================
# PROGRESS DIALOG STYLESHEET BUILDER
# ============================================================================

def _build_progress_stylesheet(theme: dict) -> str:
    """
    Build a ProgressDialog stylesheet from a theme dict.
    
    All colors are pulled from the theme — no hardcoded values.
    """
    return f"""
    QDialog {{
        background-color: {theme['dialog_bg']};
        color: {theme['text_primary']};
    }}
    QLabel {{
        color: {theme['text_primary']};
        font-size: 12px;
    }}
    QLabel#title_label {{
        font-size: 14px;
        font-weight: bold;
        color: {theme['text_accent']};
    }}
    QProgressBar {{
        border: 2px solid {theme['border_hover']};
        border-radius: 6px;
        background-color: {theme['card_bg']};
        text-align: center;
        color: {theme['text_primary']};
        font-weight: bold;
        min-height: 24px;
    }}
    QProgressBar::chunk {{
        background-color: {theme['text_accent']};
        border-radius: 4px;
    }}
    QPushButton {{
        background-color: {theme['pressed_bg']};
        color: {theme['text_primary']};
        border: 2px solid {theme['border_hover']};
        padding: 8px 20px;
        border-radius: 4px;
        font-weight: bold;
        min-width: 80px;
    }}
    QPushButton:hover {{
        background-color: {theme['hover_bg']};
        border: 2px solid {theme['button_hover_border']};
    }}
    QPushButton:pressed {{
        background-color: {theme['button_pressed_bg']};
        color: {theme['button_pressed_text']};
    }}
    QPushButton:disabled {{
        background-color: {theme['card_bg']};
        color: {theme['text_disabled']};
        border: 2px solid {theme['border_default']};
    }}
    """


# Pre-built stylesheets for each theme — preserved as module-level
# constants for backward compatibility with any external references.
DARK_PROGRESS_STYLE  = _build_progress_stylesheet(DARK_THEME_COLORS)
LIGHT_PROGRESS_STYLE = _build_progress_stylesheet(LIGHT_THEME_COLORS)
IMAGE_PROGRESS_STYLE = _build_progress_stylesheet(IMAGE_MODE_COLORS)


class ProgressDialog(QDialog):
    """
    Modal progress dialog with cancel support.
    
    Shows progress bar and optional status text.
    Emits cancelled signal when user cancels.
    
    Example:
        dialog = ProgressDialog("Extracting colors...", parent=self)
        dialog.cancelled.connect(worker.cancel)
        worker.progress.connect(dialog.set_progress)
        worker.finished.connect(dialog.accept)
        dialog.exec()
    """
    
    cancelled = pyqtSignal()
    
    def __init__(
        self,
        title: str = "Processing...",
        message: str = "",
        can_cancel: bool = True,
        parent=None,
        is_dark: bool = True
    ):
        """
        Initialize progress dialog.
        
        Args:
            title: Dialog window title
            message: Status message to display
            can_cancel: Whether to show cancel button
            parent: Parent widget
            is_dark: Use dark theme styling
        """
        super().__init__(parent)
        
        # Initialize signal manager for tracked connections
        if SIGNAL_MANAGER_AVAILABLE:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        
        # Detect theme from parent
        self._theme_name = 'dark' if is_dark else 'light'
        if parent:
            if hasattr(parent, 'theme_manager'):
                self._theme_name = getattr(parent.theme_manager, 'current_theme', 'dark')
        # Keep legacy attribute for backward-compat with any external code
        self._is_dark = self._theme_name in ('dark', 'image')
        
        self._setup_ui(message, can_cancel)
        self._apply_theme()
        self._cancelled = False
    
    def _apply_theme(self) -> None:
        """Apply theme-appropriate styling."""
        if self._theme_name == 'light':
            self.setStyleSheet(LIGHT_PROGRESS_STYLE)
        elif self._theme_name == 'image':
            self.setStyleSheet(IMAGE_PROGRESS_STYLE)
        else:
            self.setStyleSheet(DARK_PROGRESS_STYLE)
    
    def _setup_ui(self, message: str, can_cancel: bool) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title label
        self.title_label = QLabel(self.windowTitle())
        self.title_label.setObjectName("title_label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Status label
        self.status_label = QLabel(message or "Please wait...")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m")
        layout.addWidget(self.progress_bar)
        
        # Percentage/count label
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent_label)
        
        # Cancel button
        if can_cancel:
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.setMinimumWidth(100)
            
            # Connect using signal manager for proper cleanup
            if self.signal_manager:
                self.signal_manager.connect(
                    self.cancel_button,
                    self.cancel_button.clicked,
                    self._on_cancel,
                    track_as="cancel_button"
                )
            else:
                self.cancel_button.clicked.connect(self._on_cancel)
            
            button_layout.addWidget(self.cancel_button)
            
            button_layout.addStretch()
            layout.addLayout(button_layout)
        else:
            self.cancel_button = None
    
    def set_progress(self, current: int, total: int) -> None:
        """
        Update progress bar.
        
        Args:
            current: Current progress value
            total: Total progress value
        """
        if total > 0:
            percent = int(100 * current / total)
        else:
            percent = 0
        
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current} / {total}")
        self.percent_label.setText(f"{percent}% complete")
        
        # Process events to keep UI responsive
        QApplication.processEvents()
    
    def set_status(self, message: str) -> None:
        """Update status message."""
        self.status_label.setText(message)
        QApplication.processEvents()
    
    def set_indeterminate(self, indeterminate: bool = True) -> None:
        """
        Set progress bar to indeterminate mode.
        
        Args:
            indeterminate: True for spinning animation
        """
        if indeterminate:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setFormat("")
            self.percent_label.setText("Working...")
        else:
            self.progress_bar.setMaximum(100)
            self.progress_bar.setFormat("%v / %m")
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self._cancelled = True
        if self.cancel_button:
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")
        self.status_label.setText("Cancelling operation...")
        self.cancelled.emit()
    
    @property
    def was_cancelled(self) -> bool:
        """Check if dialog was cancelled."""
        return self._cancelled
    
    def closeEvent(self, event) -> None:
        """Handle dialog close as cancellation."""
        if not self._cancelled:
            self._on_cancel()
        super().closeEvent(event)


class LoadingDialog(ProgressDialog):
    """
    Progress dialog specifically for loading colors.
    
    Auto-detects theme and provides color-specific messaging.
    """
    
    def __init__(
        self,
        title: str = "Loading Colors",
        total_colors: int = 0,
        parent=None
    ):
        # Detect theme from parent
        is_dark = True
        if parent and hasattr(parent, 'theme_manager'):
            theme = getattr(parent.theme_manager, 'current_theme', 'dark')
            is_dark = theme in ('dark', 'image')
        
        super().__init__(
            title=title,
            message=f"Processing {total_colors} colors...",
            can_cancel=True,
            parent=parent,
            is_dark=is_dark
        )
        
        self.total_colors = total_colors
        self.progress_bar.setMaximum(total_colors if total_colors > 0 else 100)
    
    def update_color_progress(self, current: int, status: str = "") -> bool:
        """
        Update progress for color loading.
        
        Args:
            current: Current color index
            status: Optional status message
            
        Returns:
            False if cancelled, True otherwise
        """
        if self._cancelled:
            return False
        
        self.set_progress(current, self.total_colors)
        
        if status:
            self.set_status(status)
        else:
            self.set_status(f"Processing color {current} of {self.total_colors}...")
        
        return True


class QuickProgressDialog(ProgressDialog):
    """
    Simplified progress dialog for quick operations.
    
    Auto-closes after a short delay when complete.
    """
    
    def __init__(
        self,
        title: str = "Processing...",
        parent=None
    ):
        # Detect theme from parent
        is_dark = True
        if parent and hasattr(parent, 'theme_manager'):
            theme = getattr(parent.theme_manager, 'current_theme', 'dark')
            is_dark = theme in ('dark', 'image')
        
        super().__init__(
            title=title,
            message="",
            can_cancel=False,
            parent=parent,
            is_dark=is_dark
        )
        self.setMinimumWidth(300)
    
    def complete(self, message: str = "Complete!") -> None:
        """
        Mark operation as complete.
        
        Args:
            message: Completion message
        """
        self.set_progress(100, 100)
        self.set_status(message)
        self.percent_label.setText("Done!")
        
        # Auto-close after brief delay
        QTimer.singleShot(800, self.accept)