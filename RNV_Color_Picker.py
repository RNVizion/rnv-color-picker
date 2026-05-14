"""
RNV Color Picker - Professional Color Extraction Application

A PyQt6-based application for extracting, organizing, and exporting colors
from images. Features include:
- Upload and sample colors from images
- Screen color picker
- Dominant color extraction using K-means clustering
- Multiple palette export formats
- Dark/Light/Image themes
- Hilbert curve color sorting

Python 3.13 optimized.
"""

import sys
import os
import colorsys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QFrame, QFileDialog,
    QInputDialog, QGraphicsScene, QGraphicsPixmapItem,
    QCheckBox, QGridLayout
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QEvent, QPoint, QTimer
from PyQt6.QtGui import (
    QPixmap, QImage, QColor, QIcon, QPalette, QBrush,
    QCursor, QPainter, QPen, QPainterPath
)
from PIL import Image, ImageDraw, ImageFont
from sklearn.cluster import KMeans

# Core modules
from core.screen_color_picker import ScreenColorPicker
from core.palette_formats import PaletteFormats
from core.hilbert_curve import HilbertCurve
from core.color_history import get_color_history_manager

# UI components
from ui.image_button import ImageButton
from ui.image_viewer import ImageViewer
from ui.color_swatch_widget import ColorSwatchWidget
from ui.transparent_scroll_widget import TransparentScrollWidget
from ui.settings_panel import SettingsPanel
from ui.about_dialog import AboutDialog
from ui.progress_dialog import LoadingDialog, QuickProgressDialog

# Utilities
from utils.config import (
    ThemeManager, MAX_COLORS, APP_VERSION,
    BUTTON_HEIGHT_MIN, BUTTON_HEIGHT_MAX,
    WINDOW_WIDTH_MIN, WINDOW_WIDTH_MAX, SWATCH_SIZE,
    DEBUG_BG, DEBUG_TEXT,
    BRAND_GOLD, DARK_THEME_COLORS,
    OVERLAY_BLACK_MEDIUM,
)
from utils.font_loader import load_embedded_font
from utils.logger import Logger, get_logger
from utils.dialog_helper import DialogHelper, DialogResult
from utils.error_handler import ErrorHandler, ErrorContext
from utils.signal_manager import SignalConnectionManager
from utils.settings_manager import SettingsManager, get_settings_manager
from utils.session_manager import SessionManager
from utils.clipboard import ClipboardUtils
from utils.pixmap_cache import ImagePixmapCache
from utils.cache import ColorCache, StylesheetCache
from ui.widget_pool import WidgetPool

CACHE_AVAILABLE = True

# Create module logger
logger = Logger("ColorPicker")


class _ThemedToolTip(QLabel):
    """
    Custom tooltip that bypasses native Windows tooltip rendering.

    Native QToolTip on Windows creates an OS-level popup window with its own
    frame that cannot be styled via CSS. This class creates a frameless Qt
    widget with WA_TranslucentBackground and paints its own rounded-rect
    background, giving pixel-perfect themed tooltips in Dark, Light, and
    Image modes.
    """

    _instance: '_ThemedToolTip | None' = None
    _OFFSET_X: int = 16
    _OFFSET_Y: int = 20
    _HIDE_DELAY_MS: int = 5000
    _MAX_WIDTH: int = 400
    _BORDER_RADIUS: int = 4

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWordWrap(True)
        self.setMaximumWidth(self._MAX_WIDTH)
        self.hide()

        # Colors for paintEvent (updated on each show)
        self._bg_color = QColor(DARK_THEME_COLORS['card_bg'])
        self._border_color = QColor(BRAND_GOLD)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    @classmethod
    def instance(cls) -> '_ThemedToolTip':
        """Get or create the singleton tooltip instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def paintEvent(self, event) -> None:
        """Paint rounded-rect background and border manually."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect = self.rect().adjusted(1, 1, -1, -1)
        path.addRoundedRect(
            float(rect.x()), float(rect.y()),
            float(rect.width()), float(rect.height()),
            self._BORDER_RADIUS, self._BORDER_RADIUS
        )
        painter.fillPath(path, self._bg_color)

        painter.setPen(QPen(self._border_color, 1.0))
        painter.drawPath(path)
        painter.end()

        # Let QLabel paint the text on top
        super().paintEvent(event)

    def show_tip(self, global_pos: QPoint, text: str,
                 colors: dict, font_family: str) -> None:
        """Show themed tooltip at the given global position."""
        self._bg_color = QColor(colors['card_bg'])
        self._border_color = QColor(colors['tooltip_border'])

        self.setText(text.title())

        self.setStyleSheet(
            f"color: {colors['text_primary']};"
            f"padding: 4px 8px;"
            f"font-family: '{font_family}';"
            f"background: transparent;"
        )
        self.adjustSize()

        x = global_pos.x() + self._OFFSET_X
        y = global_pos.y() + self._OFFSET_Y

        # Keep tooltip on screen
        screen = QApplication.screenAt(global_pos)
        if screen:
            rect = screen.availableGeometry()
            if x + self.width() > rect.right():
                x = global_pos.x() - self.width() - 4
            if y + self.height() > rect.bottom():
                y = global_pos.y() - self.height() - 4

        self.move(x, y)
        self.show()
        self._hide_timer.start(self._HIDE_DELAY_MS)

    def hide_tip(self) -> None:
        """Hide the tooltip and cancel auto-hide timer."""
        self._hide_timer.stop()
        self.hide()


class ColorPickerApp(QMainWindow):
    """Main application window for RNV Color Picker."""
    
    MAX_COLORS = 333
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RNV Color Picker")
        
        # Set minimum size and default size to 1059 x 850
        self.setMinimumSize(1059, 850)
        self.setGeometry(100, 100, 1059, 850)
        
        logger.success("Core modules loaded")
        
        # Initialize managers
        self.theme_manager = ThemeManager()
        self.theme_manager.detect_image_resources()
        
        self.settings_manager = get_settings_manager()
        self.session_manager = SessionManager()
        self.signal_manager = SignalConnectionManager()
        self.pixmap_cache = ImagePixmapCache(max_size=15)
        self.color_history = get_color_history_manager()
        
        logger.success("Settings Manager initialized and loaded")
        
        # Initialize clipboard utils (after QApplication exists)
        try:
            self.clipboard = ClipboardUtils()
        except RuntimeError:
            self.clipboard = None
            logger.warning("ClipboardUtils not available")
        
        # Set application icon
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "resources", "icons", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.success("Loaded application icon from:", details=icon_path)
        else:
            logger.warning("Icon not found", details=icon_path)
        
        # Initialize state
        self.colors: list[tuple[tuple[int, int, int], tuple[int, int, int], int, bool]] = []
        self.color_widgets: list[ColorSwatchWidget] = []
        self.image: Image.Image | None = None
        self.current_pixmap: QPixmap | None = None
        self.sort_method = "hilbert"
        self.preserve_colors = False
        self.all_buttons: list[ImageButton] = []
        self.background_label: QLabel | None = None
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.scale_factor = 1.0
        self.settings_panel: SettingsPanel | None = None
        self.about_dialog: AboutDialog | None = None
        self.tooltips_enabled = True  # Tooltips shown by default
        
        # Initialize widget pool for efficient swatch recycling
        self.swatch_pool: WidgetPool[ColorSwatchWidget] = WidgetPool(
            factory=lambda: ColorSwatchWidget(parent_app=self),
            initial_size=0,  # Lazy creation
            max_size=MAX_COLORS + 50  # Allow some headroom
        )
        logger.debug(f"Widget pool initialized (max_size={MAX_COLORS + 50})")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create background label for image mode
        self.background_label = QLabel(self)
        self.background_label.setScaledContents(True)
        self.background_label.lower()
        self.background_label.hide()
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(1)

        self.setup_image_viewer()
        main_layout.addWidget(self.graphics_view, 7)

        button_frame = self.create_button_frame()
        main_layout.addWidget(button_frame)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(350)
        self.scroll_area = scroll_area
        
        # Use custom transparent widget for scrollable content
        self.scrollable_frame = TransparentScrollWidget()
        self.grid_layout = QGridLayout(self.scrollable_frame)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        
        scroll_area.setWidget(self.scrollable_frame)
        main_layout.addWidget(scroll_area, 3)

        self.create_checkboxes()
        self.create_debug_label()
        self.resizeEvent = self.on_resize
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        # Apply initial theme
        logger.info("Applying theme to all components...")
        self.apply_theme()
        logger.success("Initial theme application complete")
        
        # Apply saved settings from settings manager
        self._apply_saved_settings()
        
        # Apply initial tooltips (based on saved settings)
        self._apply_tooltips()
        logger.info(f"Tooltips {'enabled' if self.tooltips_enabled else 'disabled'} (Press F11 to toggle)")
        
        # Capture font family for custom tooltip rendering
        self.font_family = QApplication.instance().font().family()
        
        # Install application-level event filter for custom themed tooltips
        # (bypasses native Windows tooltip rendering that ignores CSS border-radius)
        QApplication.instance().installEventFilter(self)
        
        logger.success("ColorPickerApp initialization completed successfully")

    def create_checkboxes(self) -> None:
        """Create theme, sort, preserve checkboxes and settings button."""
        self.theme_button = QPushButton(self.theme_manager.get_theme_display_name(), self)
        self.signal_manager.connect(
            self.theme_button, self.theme_button.clicked, self.cycle_theme, "theme_button_clicked"
        )
        
        self.sort_checkbox = QCheckBox("Sort: Hilbert Curve", self)
        self.sort_checkbox.setChecked(True)
        self.signal_manager.connect(
            self.sort_checkbox, self.sort_checkbox.stateChanged, self.on_sort_checkbox_changed, "sort_checkbox_changed"
        )
        
        self.preserve_checkbox = QCheckBox("Preserve Colors", self)
        self.preserve_checkbox.setChecked(False)
        self.signal_manager.connect(
            self.preserve_checkbox, self.preserve_checkbox.stateChanged, self.on_preserve_checkbox_changed, "preserve_checkbox_changed"
        )
        
        # Settings button - ImageButton with always_use_image for consistent appearance
        self.settings_button = ImageButton("", "settings_gear", self, always_use_image=True)
        self.settings_button.set_theme_manager(self.theme_manager)
        self.signal_manager.connect(
            self.settings_button, self.settings_button.clicked, self.open_settings, "settings_button_clicked"
        )
        
        self.update_checkbox_styles()
        self.update_checkbox_positions()

    def create_debug_label(self) -> None:
        """Create debug label to show window dimensions."""
        self.debug_label = QLabel(self)
        self.debug_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.debug_label.setStyleSheet(f"""
            background-color: {DEBUG_BG};
            color: {DEBUG_TEXT};
            padding: 5px 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        """)
        self.update_debug_label()
        self.debug_label.raise_()

    def showEvent(self, event) -> None:
        """Handle window show event - ensure proper initial positioning."""
        super().showEvent(event)
        # Update positions after the window is shown and layout is complete
        # Use QTimer.singleShot(0) to defer until after the event loop processes
        QTimer.singleShot(0, self._deferred_position_update)
    
    def _deferred_position_update(self) -> None:
        """Deferred position update called after window is fully shown."""
        self.update_checkbox_positions()
        self.update_debug_label()

    def update_debug_label(self) -> None:
        """Update debug label with current window dimensions."""
        width = self.width()
        height = self.height()
        self.debug_label.setText(f"Window: {width} x {height} px")
        self.debug_label.adjustSize()
        # Position in top-left corner
        self.debug_label.move(10, 10)

    def toggle_tooltips(self) -> None:
        """Toggle tooltips visibility for all widgets."""
        self.tooltips_enabled = not self.tooltips_enabled
        self._apply_tooltips()
        
        status = "enabled" if self.tooltips_enabled else "disabled"
        if logger:
            logger.info(f"Tooltips {status}")
        
        # Save to settings manager
        if self.settings_manager:
            self.settings_manager.set("show_tooltips", self.tooltips_enabled)
            self.settings_manager.save_settings()
        
        # Update settings panel checkbox if open
        if hasattr(self, 'settings_panel') and self.settings_panel:
            self.settings_panel.update_tooltips_checkbox(self.tooltips_enabled)
        
        # Show brief notification
        DialogHelper.show_info(
            self, 
            f"Tooltips {status}\n\nPress F11 to toggle", 
            title="Tooltips"
        )
    
    def toggle_debug_overlay(self) -> None:
        """Toggle debug overlay visibility."""
        if hasattr(self, 'debug_label') and self.debug_label:
            is_visible = self.debug_label.isVisible()
            new_visible = not is_visible
            
            if new_visible:
                # Showing again: restore dimension text and visibility
                self.debug_label.setText("")  # ensure clean state
                self.update_debug_label()
                self.debug_label.show()
                self.debug_label.raise_()
            else:
                # Hiding: clear, resize to 0, hide, and force full repaint
                # The resize-to-zero ensures no rectangle remains in the layout
                self.debug_label.clear()
                self.debug_label.setText("")
                self.debug_label.resize(0, 0)
                self.debug_label.hide()
                # Repaint the window to erase any leftover paint
                self.repaint()
            
            status = "hidden" if is_visible else "shown"
            if logger:
                logger.info(f"Debug overlay {status}")
            
            # Save to settings manager
            if self.settings_manager:
                self.settings_manager.set("show_debug_overlay", new_visible)
                self.settings_manager.save_settings()
            
            # Update settings panel checkbox if open
            if hasattr(self, 'settings_panel') and self.settings_panel:
                self.settings_panel.update_debug_overlay_checkbox(new_visible)
            
            # Show brief notification
            DialogHelper.show_info(
                self, 
                f"Debug overlay {status}\n\nPress F12 to toggle", 
                title="Debug Overlay"
            )
        else:
            if logger:
                logger.warning("Debug label not found")
    
    def _apply_tooltips(self) -> None:
        """Apply or remove tooltips from all widgets based on tooltips_enabled flag."""
        # Define tooltips for buttons
        button_tooltips = {
            "upload": "Upload an image to extract colors from (Ctrl+O)",
            "grab": "Extract all unique colors from the image (Ctrl+G)",
            "dominant": "Extract dominant colors using K-means clustering (Ctrl+K)",
            "screen": "Pick a color from anywhere on screen (Ctrl+Shift+C)",
            "save": "Save color swatches as an image file (Ctrl+S)",
            "export": "Export palette in various formats (Ctrl+E)",
            "clear": "Clear all unlocked colors (Ctrl+D)",
            "reset": "Reset zoom and pan to default (Ctrl+0)",
        }
        
        # Apply/remove tooltips from buttons
        for btn in self.all_buttons:
            if self.tooltips_enabled:
                # Get tooltip based on button's image name
                img_name = getattr(btn, 'img_name', '')
                tooltip = button_tooltips.get(img_name, "")
                btn.setToolTip(tooltip)
            else:
                btn.setToolTip("")
        
        # Theme button tooltip
        if hasattr(self, 'theme_button') and self.theme_button:
            if self.tooltips_enabled:
                self.theme_button.setToolTip("Click to cycle through themes (Dark/Light/Image)")
            else:
                self.theme_button.setToolTip("")
        
        # Settings button tooltip
        if hasattr(self, 'settings_button') and self.settings_button:
            if self.tooltips_enabled:
                self.settings_button.setToolTip("Open settings and features panel (Ctrl+, or Ctrl+P)")
            else:
                self.settings_button.setToolTip("")
        
        # Checkbox tooltips
        if hasattr(self, 'sort_checkbox') and self.sort_checkbox:
            if self.tooltips_enabled:
                self.sort_checkbox.setToolTip("Toggle between Hilbert Curve and HSL sorting")
            else:
                self.sort_checkbox.setToolTip("")
        
        if hasattr(self, 'preserve_checkbox') and self.preserve_checkbox:
            if self.tooltips_enabled:
                self.preserve_checkbox.setToolTip("Keep existing colors when adding new ones")
            else:
                self.preserve_checkbox.setToolTip("")
        
        # Graphics view tooltip
        if hasattr(self, 'graphics_view') and self.graphics_view:
            if self.tooltips_enabled:
                self.graphics_view.setToolTip("Double-click to pick color, drag to select region, scroll to zoom")
            else:
                self.graphics_view.setToolTip("")
    
    def _apply_saved_settings(self) -> None:
        """Apply saved settings from settings manager on startup."""
        if not self.settings_manager:
            return
        
        try:
            settings = self.settings_manager.settings
            
            # Apply tooltips setting
            self.tooltips_enabled = settings.get("show_tooltips", True)
            
            # Apply debug overlay setting
            show_debug = settings.get("show_debug_overlay", True)
            if hasattr(self, 'debug_label') and self.debug_label:
                self.debug_label.setVisible(show_debug)
            
            # Apply sort method (block signals to prevent save loop)
            sort_method = settings.get("default_sort_method", "hilbert")
            self.sort_method = sort_method
            if hasattr(self, 'sort_checkbox'):
                self.sort_checkbox.blockSignals(True)
                is_hilbert = sort_method == "hilbert"
                self.sort_checkbox.setChecked(is_hilbert)
                self.sort_checkbox.setText("Sort: Hilbert Curve" if is_hilbert else "Sort: HSL")
                self.sort_checkbox.blockSignals(False)
            
            # Apply preserve colors setting (block signals to prevent save loop)
            self.preserve_colors = settings.get("preserve_colors", False)
            if hasattr(self, 'preserve_checkbox'):
                self.preserve_checkbox.blockSignals(True)
                self.preserve_checkbox.setChecked(self.preserve_colors)
                self.preserve_checkbox.blockSignals(False)
            
            # Apply theme (if different from current)
            saved_theme = settings.get("theme", "image")
            if saved_theme != self.theme_manager.current_theme:
                if saved_theme == "dark":
                    self.theme_manager.current_theme = 'dark'
                    self.theme_manager.image_mode_active = False
                elif saved_theme == "light":
                    self.theme_manager.current_theme = 'light'
                    self.theme_manager.image_mode_active = False
                elif saved_theme == "image" and self.theme_manager.image_mode_available:
                    self.theme_manager.current_theme = 'image'
                    self.theme_manager.image_mode_active = True
                
                if hasattr(self, 'theme_button'):
                    self.theme_button.setText(self.theme_manager.get_theme_display_name())
                    self.theme_button.adjustSize()
                    self.theme_button.updateGeometry()
                self.apply_theme()
            
            logger.success("Saved settings applied")
            
            # Start auto-save timer if enabled in settings
            auto_save_enabled = settings.get("auto_save_session", True)
            if auto_save_enabled and hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.start_autosave(self)
                # Clean up old auto-saves on startup (keep last 5)
                self.session_manager.cleanup_old_autosaves(keep_count=5)
            
        except Exception as e:
            logger.error(f"Error applying saved settings: {e}")

    def update_checkbox_styles(self) -> None:
        """Update checkbox, theme button, and settings button styles based on current theme."""
        theme = self.theme_manager.get_current_theme()
        
        if theme:
            # Use cached checkbox stylesheet if available
            theme_name = self.theme_manager.current_theme
            if CACHE_AVAILABLE and StylesheetCache:
                checkbox_style = StylesheetCache.get_checkbox_stylesheet(theme_name, theme)
            else:
                checkbox_style = f"""
                    QCheckBox {{
                        background-color: {theme['checkbox_bg']};
                        padding: 5px;
                        border: 1px solid {theme['checkbox_border']};
                        border-radius: 3px;
                        color: {theme['text_primary']};
                    }}
                """
            self.sort_checkbox.setStyleSheet(checkbox_style)
            self.preserve_checkbox.setStyleSheet(checkbox_style)
            
            # Use cached theme button stylesheet if available
            if CACHE_AVAILABLE and StylesheetCache:
                theme_button_style = StylesheetCache.get_theme_button_stylesheet(theme_name, theme)
            else:
                theme_button_style = f"""
                    QPushButton {{
                        background-color: {theme['main_btn_bg']};
                        color: {theme['main_btn_text']};
                        border: 1px solid {theme['main_btn_border']};
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['main_btn_hover_bg']};
                        color: {theme['main_btn_hover_text']};
                    }}
                    QPushButton:pressed {{
                        background-color: {theme['main_btn_pressed_bg']};
                        color: {theme['main_btn_pressed_text']};
                    }}
                """
            self.theme_button.setStyleSheet(theme_button_style)
            
            # Settings button - use ImageButton's apply_style for proper image mode support
            if hasattr(self, 'settings_button'):
                self.settings_button.apply_style()

    def update_checkbox_positions(self) -> None:
        """Position checkboxes in bottom-right and settings in top-right of scroll area."""
        # Start from bottom and work up for bottom-right controls
        if hasattr(self, 'preserve_checkbox'):
            self.preserve_checkbox.adjustSize()
            x = self.width() - self.preserve_checkbox.width() - 20
            y = self.height() - self.preserve_checkbox.height() - 20
            self.preserve_checkbox.move(x, y)
            self.preserve_checkbox.raise_()
        
        if hasattr(self, 'sort_checkbox'):
            self.sort_checkbox.adjustSize()
            x = self.width() - self.sort_checkbox.width() - 20
            y = y - self.sort_checkbox.height() - 10
            self.sort_checkbox.move(x, y)
            self.sort_checkbox.raise_()
        
        if hasattr(self, 'theme_button'):
            self.theme_button.adjustSize()
            x = self.width() - self.theme_button.width() - 20
            y = y - self.theme_button.height() - 10
            self.theme_button.move(x, y)
            self.theme_button.raise_()
        
        # Settings button - TOP-RIGHT of scroll area (icon button)
        if hasattr(self, 'settings_button') and hasattr(self, 'scroll_area'):
            # Set size for icon button (square-ish for gear icon)
            btn_size = 40
            self.settings_button.setFixedSize(btn_size, btn_size)
            
            # Get scroll_area's global position and map to main window
            scroll_rect = self.scroll_area.geometry()
            # Position at top-right of scroll area with padding
            x = scroll_rect.right() - btn_size - 15
            y = scroll_rect.top() + 10
            
            self.settings_button.move(x, y)
            self.settings_button.raise_()

    def cycle_theme(self) -> None:
        """Cycle through available themes."""
        self.theme_manager.cycle_theme()
        self.theme_button.setText(self.theme_manager.get_theme_display_name())
        self.apply_theme()
        
        # Force theme button to recalculate size and position
        self.theme_button.adjustSize()
        self.theme_button.updateGeometry()
        self.update_checkbox_positions()
        
        self.update()
        QApplication.processEvents()
        
        # Save theme to settings manager
        if self.settings_manager:
            self.settings_manager.set("theme", self.theme_manager.current_theme)
            self.settings_manager.save_settings()

    def apply_theme(self) -> None:
        """Apply current theme to all UI components."""
        theme = self.theme_manager.get_current_theme()
        is_image = self.theme_manager.is_image_mode()

        # Get pre-defined scrollbar styling (optimized for performance)
        if is_image:
            scrollbar_style = ThemeManager.SCROLLBAR_IMAGE
        elif theme['name'] == 'Dark':
            scrollbar_style = ThemeManager.SCROLLBAR_DARK
        else:  # Light mode
            scrollbar_style = ThemeManager.SCROLLBAR_LIGHT

        # Application-wide palette
        palette = QPalette()
        window_color = QColor(theme['window_bg'])
        text_color = QColor(theme['text_primary'])

        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Window, window_color)
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText, text_color)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Window, window_color)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText, text_color)

        app = QApplication.instance()
        if app:
            app.setPalette(palette)

        # Background handling
        self.background_label.hide()

        if is_image and self.theme_manager.background_pixmap:
            self.background_label.setPixmap(self.theme_manager.background_pixmap)
            self.background_label.setGeometry(0, 0, self.width(), self.height())
            self.background_label.show()
            self.setStyleSheet(scrollbar_style)
        else:
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {theme['window_bg']};
                }}
                {scrollbar_style}
            """)

        # Button frame
        if is_image:
            self.button_frame.setStyleSheet(f"""
                QFrame {{ background: transparent; border: none; }}
                {scrollbar_style}
            """)
        else:
            self.button_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme['window_bg']};
                    border: none;
                }}
                {scrollbar_style}
            """)

        # Image viewer
        if is_image:
            self.graphics_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.graphics_view.setStyleSheet("background: transparent; border: none;")

            # Use semi-transparent black brush
            semi_transparent_black = QColor(*OVERLAY_BLACK_MEDIUM)
            self.graphics_view.setBackgroundBrush(QBrush(semi_transparent_black))

            if hasattr(self.graphics_view, 'scene_ref') and self.graphics_view.scene_ref:
                self.graphics_view.scene_ref.setBackgroundBrush(QBrush(Qt.GlobalColor.transparent))
        else:
            self.graphics_view.setStyleSheet(f"background-color: {theme['image_viewer_bg']};")
            self.graphics_view.setBackgroundBrush(QBrush(QColor(theme['image_viewer_bg'])))
            if hasattr(self.graphics_view, 'scene_ref') and self.graphics_view.scene_ref:
                self.graphics_view.scene_ref.setBackgroundBrush(QBrush(QColor(theme['image_viewer_bg'])))

        # Scroll area handling
        if is_image:
            self.scrollable_frame.set_transparent_mode(True, QColor(*OVERLAY_BLACK_MEDIUM))
            self.scroll_area.viewport().setAutoFillBackground(False)
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: 1px solid {theme['border_default']};
                }}
                QScrollArea > QWidget > QWidget {{
                    background: transparent;
                }}
                {scrollbar_style}
            """)
        else:
            self.scrollable_frame.set_transparent_mode(False)
            self.scroll_area.viewport().setAutoFillBackground(True)
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {theme['scroll_area_bg']};
                    border: 1px solid {theme['border_default']};
                }}
                QWidget {{
                    background-color: {theme['scroll_area_bg']};
                }}
                {scrollbar_style}
            """)

        # Zoom label
        self.zoom_label.setStyleSheet(f"""
            background-color: {theme['zoom_label_bg']};
            color: {theme['text_primary']};
            padding: 5px;
            border: 1px solid {theme['zoom_label_border']};
        """)

        # Update all buttons
        for btn in self.all_buttons:
            btn.apply_style()

        # Update checkboxes
        self.update_checkbox_styles()

        # Update color swatches (just repaint, don't recreate)
        for widget in self.color_widgets:
            widget.update()
        
        # Update settings panel theme if open
        if self.settings_panel and self.settings_panel.isVisible():
            self.settings_panel.update_theme()
        
        # Update about dialog theme if open
        if self.about_dialog and self.about_dialog.isVisible():
            self.about_dialog._apply_theme()
    
        self.repaint()

    def on_resize(self, event) -> None:
        """Handle window resize event."""
        self.update_checkbox_positions()
        self.update_debug_label()
        
        # Update button heights based on window width
        current_width = self.width()
        for btn in self.all_buttons:
            btn.update_height_for_window(current_width)
        
        if self.theme_manager.is_image_mode():
            if self.background_label and self.background_label.pixmap():
                self.background_label.setGeometry(0, 0, self.width(), self.height())
        
        return super().resizeEvent(event)

    def on_sort_checkbox_changed(self, state: int) -> None:
        """Handle sort checkbox state change."""
        if state == Qt.CheckState.Checked.value:
            self.sort_method = "hilbert"
            self.sort_checkbox.setText("Sort: Hilbert Curve")
        else:
            self.sort_method = "hsl"
            self.sort_checkbox.setText("Sort: HSL")
        
        # Save to settings manager
        if self.settings_manager:
            self.settings_manager.set("default_sort_method", self.sort_method)
            self.settings_manager.save_settings()
        
        if self.colors:
            self.sort_colors()
            self.refresh_color_display(show_progress=False)  # No progress for sorting

    def on_preserve_checkbox_changed(self, state: int) -> None:
        """Handle preserve checkbox state change."""
        self.preserve_colors = (state == Qt.CheckState.Checked.value)
        
        # Save to settings manager
        if self.settings_manager:
            self.settings_manager.set("preserve_colors", self.preserve_colors)
            self.settings_manager.save_settings()

    def rgb_to_hsl(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """Convert RGB to HSL. Uses cache if available."""
        if CACHE_AVAILABLE and ColorCache:
            return ColorCache.rgb_to_hsl(rgb)
        r, g, b = (x / 255.0 for x in rgb)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return (int(h * 360), int(s * 100), int(l * 100))

    def sort_colors_by_hsl(self) -> None:
        """Sort colors by HSL values."""
        self.colors.sort(key=lambda x: (x[1][0], x[1][2], x[1][1]))

    def sort_colors_by_hilbert(self) -> None:
        """Sort colors by Hilbert curve index."""
        self.colors.sort(key=lambda x: x[2])

    def sort_colors(self) -> None:
        """Sort colors using current sort method."""
        if self.sort_method == "hilbert":
            self.sort_colors_by_hilbert()
        else:
            self.sort_colors_by_hsl()

    def get_remaining_slots(self) -> int:
        """Get number of remaining color slots."""
        return self.MAX_COLORS - len(self.colors)

    def color_exists(self, rgb: tuple[int, int, int]) -> bool:
        """Check if color already exists in palette."""
        return any(color[0] == rgb for color in self.colors)

    def add_color(self, rgb: tuple[int, int, int]) -> bool:
        """Add a color to the palette."""
        if len(self.colors) >= self.MAX_COLORS:
            return False
    
        if self.color_exists(rgb):
            return False
    
        hsl = self.rgb_to_hsl(rgb)
        hilbert_idx = HilbertCurve.rgb_to_hilbert(rgb)
        self.colors.append((rgb, hsl, hilbert_idx, False))  # False = not locked
        return True

    def add_colors_batch(
        self, 
        rgb_list: list[tuple[int, int, int]], 
        source: str | None = None
    ) -> tuple[int, int]:
        """
        Add multiple colors at once.
        
        Args:
            rgb_list: List of RGB tuples to add
            source: Optional source for color history tracking 
                   (e.g., "grab", "dominant", "import", "selection")
        
        Returns:
            Tuple of (added_count, skipped_duplicates)
        """
        added_count = 0
        skipped_duplicates = 0
        
        for rgb in rgb_list:
            if len(self.colors) >= self.MAX_COLORS:
                break
            
            if self.color_exists(rgb):
                skipped_duplicates += 1
                continue
            
            # Track to color history if source is provided
            if source and self.color_history:
                self.color_history.add_color(rgb, source=source)
            
            if self.add_color(rgb):
                added_count += 1
        
        return added_count, skipped_duplicates

    def _add_colors_with_progress(
        self, 
        rgb_list: list[tuple[int, int, int]], 
        source: str | None = None
    ) -> tuple[int, int]:
        """
        Add multiple colors with a progress dialog.
        
        Shows a loading bar for large color operations to prevent UI freezing.
        
        Args:
            rgb_list: List of RGB tuples to add
            source: Optional source for color history tracking
        
        Returns:
            Tuple of (added_count, skipped_duplicates)
        """
        import time
        
        total = min(len(rgb_list), self.MAX_COLORS - len(self.colors))
        
        # Create and show progress dialog
        progress = LoadingDialog(
            title="Loading Colors",
            total_colors=total,
            parent=self
        )
        progress.set_status("Preparing to load colors...")
        progress.show()
        
        # CRITICAL: Force dialog to fully render before heavy work
        progress.raise_()
        progress.activateWindow()
        progress.repaint()
        QApplication.processEvents()
        time.sleep(0.1)  # Allow paint to complete
        QApplication.processEvents()
        
        added_count = 0
        skipped_duplicates = 0
        
        for i, rgb in enumerate(rgb_list):
            # Check for cancellation
            if progress.was_cancelled:
                if logger:
                    logger.info("Color loading cancelled by user")
                break
            
            if len(self.colors) >= self.MAX_COLORS:
                break
            
            # Update progress every color
            progress.set_progress(i + 1, total)
            progress.set_status(f"Adding color {i + 1} of {total}...")
            
            if self.color_exists(rgb):
                skipped_duplicates += 1
                continue
            
            # Track to color history if source is provided
            if source and self.color_history:
                self.color_history.add_color(rgb, source=source)
            
            if self.add_color(rgb):
                added_count += 1
        
        # Close progress dialog
        progress.accept()
        
        if logger:
            logger.info(f"Added {added_count} colors (skipped {skipped_duplicates} duplicates)")
        
        return added_count, skipped_duplicates

    def update_color_lock_state(
        self, 
        rgb: tuple[int, int, int], 
        hsl: tuple[int, int, int], 
        hilbert_idx: int, 
        is_locked: bool
    ) -> None:
        """Update the lock state for a specific color."""
        for i, color in enumerate(self.colors):
            if color[0] == rgb and color[1] == hsl and color[2] == hilbert_idx:
                self.colors[i] = (rgb, hsl, hilbert_idx, is_locked)
                break

    def _colors_to_palette_format(self) -> list[tuple[tuple[int, int, int], int]]:
        """Convert app colors to palette format (rgb, weight)."""
        return [(color[0], 50) for color in self.colors]
    
    def _palette_to_app_format(
        self, 
        palette_colors: list[tuple[tuple[int, int, int], int]]
    ) -> list[tuple[int, int, int]]:
        """Convert palette colors to app format."""
        return [color[0] for color in palette_colors]

    def pick_color_from_pixel(self, scene_pos: QPointF) -> None:
        """Pick color from a pixel in the image."""
        if not self.pixmap_item or not self.image:
            return
        
        item_pos = self.pixmap_item.mapFromScene(scene_pos)
        x, y = int(item_pos.x()), int(item_pos.y())
        
        width, height = self.image.size
        if 0 <= x < width and 0 <= y < height:
            rgb = self.image.getpixel((x, y))
            
            # Add to color history
            if hasattr(self, 'color_history') and self.color_history:
                self.color_history.add_color(rgb, source="image")
            
            if self.add_color(rgb):
                self.sort_colors()
                self.refresh_color_display(show_progress=False)
            else:
                if len(self.colors) >= self.MAX_COLORS:
                    DialogHelper.show_warning(
                        self, 
                        f"Maximum capacity reached ({self.MAX_COLORS} colors)",
                        title="Max Colors"
                    )
                else:
                    DialogHelper.show_info(
                        self, 
                        "This color already exists in the palette",
                        title="Duplicate"
                    )

    def clear_image(self) -> None:
        """Clear the current image."""
        if DialogHelper.confirm(self, "Are you sure you want to clear the image?", title="Clear Image"):
            self.image = None
            self.current_pixmap = None
            self.scene.clear()
            self.pixmap_item = None
            self.graphics_view.zoom_locked = False
            # No image: hide the zoom indicator
            self.zoom_label.hide()

    def save_colors_as_image(self) -> None:
        """Save colors as an image file."""
        if not self.colors:
            DialogHelper.show_warning(self, "No colors to save!", title="No Colors")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Colors As Image",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)"
        )
        if not file_path:
            return

        is_png = file_path.lower().endswith('.png')
        fmt = 'PNG' if is_png else 'JPEG'

        cols = 3
        rows = (len(self.colors) + cols - 1) // cols
        
        page_width = 2550
        page_height = 3300
        
        margin = 150
        usable_width = page_width - (2 * margin)
        usable_height = page_height - (2 * margin)
        
        spacing = 10
        
        swatch_width = (usable_width - (cols - 1) * spacing) // cols
        swatch_height = (usable_height - (rows - 1) * spacing) // rows
        
        content_width = cols * swatch_width + (cols - 1) * spacing
        content_height = rows * swatch_height + (rows - 1) * spacing
        
        offset_x = (page_width - content_width) // 2
        offset_y = (page_height - content_height) // 2

        if is_png:
            palette_img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))
        else:
            palette_img = Image.new("RGB", (page_width, page_height), (255, 255, 255))

        draw = ImageDraw.Draw(palette_img)

        for idx, (rgb, hsl, hilbert_idx, is_locked) in enumerate(self.colors):
            col = idx % cols
            row = idx // cols
            
            x = offset_x + col * (swatch_width + spacing)
            y = offset_y + row * (swatch_height + spacing)
            
            draw.rectangle(
                [x, y, x + swatch_width, y + swatch_height], 
                fill=rgb, outline=(0, 0, 0), width=2
            )
            
            try:
                font_size = max(14, min(swatch_width, swatch_height) // 12)
                mont_path = os.path.join(os.getcwd(), "resources", "fonts", "Montserrat-Black.ttf")
                if os.path.exists(mont_path):
                    font = ImageFont.truetype(mont_path, font_size)
                    small_font = ImageFont.truetype(mont_path, max(10, font_size - 4))
                else:
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                        small_font = ImageFont.truetype("arial.ttf", max(10, font_size - 4))
                    except OSError:
                        font = ImageFont.load_default()
                        small_font = font
                
                r, g, b = rgb
                # Use cached text color calculation if available
                if CACHE_AVAILABLE and ColorCache:
                    text_color = ColorCache.get_text_color_for_background((r, g, b))
                    hex_code = ColorCache.rgb_to_hex((r, g, b))
                else:
                    brightness = (r * 299 + g * 587 + b * 114) / 1000
                    text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                    hex_code = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                
                draw.text((x + 10, y + 10), f"#{idx + 1}", fill=text_color, font=font)
                
                draw.text((x + 10, y + swatch_height - 50), hex_code, fill=text_color, font=small_font)
                
                rgb_text = f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"
                draw.text((x + 10, y + swatch_height - 25), rgb_text, fill=text_color, font=small_font)
            except Exception:
                pass

        try:
            palette_img.save(file_path, fmt, quality=95, dpi=(300, 300))
            DialogHelper.show_info(
                self, 
                f"Saved {len(self.colors)} colors in 3-column grid\n"
                f"Swatches fill entire page at 8.5x11 inches\n"
                f"Saved to: {file_path}",
                title="Saved"
            )
            logger.success(f"Saved palette image: {file_path}")
        except Exception as e:
            DialogHelper.show_error(self, f"Failed to save image: {e}")
            logger.error("Failed to save palette image", error=e)

    def export_palette(self) -> None:
        """Export color palette in various professional formats."""
        if not self.colors:
            DialogHelper.show_warning(self, "No colors to export!", title="No Colors")
            return
        
        formats = PaletteFormats.get_export_formats()
        filter_string = ";;".join([f"{name} ({pattern})" for name, pattern in formats])
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Palette",
            "",
            filter_string
        )
        
        if not file_path:
            return
        
        try:
            palette_colors = self._colors_to_palette_format()
            PaletteFormats.export_palette(file_path, palette_colors)
            
            DialogHelper.show_info(
                self, 
                f"Palette exported successfully!\n\n"
                f"File: {file_path}\n"
                f"Colors: {len(palette_colors)}",
                title="Success"
            )
            logger.success(f"Palette exported: {file_path}")
        except Exception as e:
            DialogHelper.show_error(
                self, 
                f"Failed to export palette:\n{e}",
                title="Export Error"
            )
            logger.error("Failed to export palette", error=e)

    def import_palette(self) -> None:
        """Import color palette from various professional formats."""
        formats = PaletteFormats.get_import_formats()
        filter_string = ";;".join([f"{name} ({pattern})" for name, pattern in formats])
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Palette",
            "",
            filter_string
        )
        
        if not file_path:
            return
        
        try:
            palette_colors = PaletteFormats.import_palette(file_path)
            
            if not palette_colors:
                DialogHelper.show_warning(
                    self,
                    "No colors found in the selected file.",
                    title="Import Error"
                )
                return
            
            rgb_list = self._palette_to_app_format(palette_colors)
            
            if self.colors:
                result = DialogHelper.ask_yes_no_cancel(
                    self,
                    f"Found {len(rgb_list)} colors in palette.\n\n"
                    f"Replace existing {len(self.colors)} colors or add to them?\n\n"
                    f"Yes = Replace, No = Add, Cancel = Abort",
                    title="Import Mode"
                )
                
                if result == DialogResult.CANCEL:
                    return
                elif result == DialogResult.YES:
                    if not self.preserve_colors:
                        self.clear_colors()
            
            added_count, skipped = self.add_colors_batch(rgb_list, source="import")
            self.sort_colors()
            self.refresh_color_display(show_progress=False)
            
            remaining = self.get_remaining_slots()
            msg = f"Import successful!\n\nAdded: {added_count} colors"
            if skipped > 0:
                msg += f"\nSkipped: {skipped} duplicates"
            if remaining == 0:
                msg += f"\n\nMax capacity reached ({self.MAX_COLORS} colors)"
            else:
                msg += f"\nSlots remaining: {remaining}"
            
            DialogHelper.show_info(self, msg, title="Import Complete")
            logger.success(f"Imported {added_count} colors from: {file_path}")
            
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to import palette:\n{e}",
                title="Import Error"
            )
            logger.error("Failed to import palette", error=e)

    def refresh_color_display(self, show_progress: bool = True) -> None:
        """
        Refresh the color swatch display using widget pool for efficiency.
        
        Args:
            show_progress: Show progress dialog for large displays (100+ colors)
        """
        import time
        
        total_colors = len(self.colors)
        
        # Use progress dialog for large displays
        use_progress = show_progress and total_colors > 100
        progress = None
        
        if use_progress:
            progress = LoadingDialog(
                title="Refreshing Display",
                total_colors=total_colors,
                parent=self
            )
            progress.set_status("Preparing display...")
            progress.show()
            
            # CRITICAL: Force dialog to fully render before heavy work
            progress.raise_()
            progress.activateWindow()
            progress.repaint()
            QApplication.processEvents()
            time.sleep(0.1)  # Allow paint to complete
            QApplication.processEvents()
        
        # Release existing widgets back to pool (instead of deleting)
        for widget in self.color_widgets:
            try:
                # Check if widget is still valid (not deleted at C++ level)
                if widget is not None:
                    self.grid_layout.removeWidget(widget)
                    widget.hide()
            except RuntimeError:
                # Widget was already deleted by the pool - skip it
                pass
        
        # Return all widgets to pool for reuse
        self.swatch_pool.release_all()
        self.color_widgets.clear()
        
        # Process events after clearing
        QApplication.processEvents()

        for idx, color_data in enumerate(self.colors, start=1):
            rgb, hsl, hilbert_idx, is_locked = color_data
            row = (idx - 1) // 3
            col = (idx - 1) % 3
            
            # Acquire widget from pool (reuses existing or creates new)
            swatch = self.swatch_pool.acquire()
            
            # Configure with new data (fast - just updates properties)
            swatch.configure(idx, rgb, hsl, hilbert_idx, is_locked)
            swatch.show()
            
            self.grid_layout.addWidget(swatch, row, col)
            self.color_widgets.append(swatch)
            
            # Update progress every swatch for large displays
            if use_progress and progress:
                if progress.was_cancelled:
                    break
                progress.set_progress(idx, total_colors)
                progress.set_status(f"Creating swatch {idx} of {total_colors}...")
        
        # Close progress dialog
        if progress:
            progress.accept()
        
        # Log pool statistics
        if logger:
            logger.debug(
                f"Widget pool: {self.swatch_pool.in_use_count} in use, "
                f"{self.swatch_pool.available_count} available, "
                f"{self.swatch_pool.total_count} total"
            )
        
        # Final process events
        QApplication.processEvents()

    def setup_image_viewer(self) -> None:
        """Set up the image viewer component."""
        self.graphics_view = ImageViewer(self)
        self.graphics_view.parent_app = self
        self.graphics_view.setMinimumSize(800, 400)

        self.scene = QGraphicsScene()
        self.graphics_view.scene_ref = self.scene
        self.graphics_view.setScene(self.scene)

        self.graphics_view.viewport().installEventFilter(self)
        self.graphics_view.viewport().setMouseTracking(True)

        self.zoom_label = QLabel("100%", self.graphics_view)
        self.zoom_label.move(5, 5)
        self.zoom_label.hide()  # Only shown when an image is loaded

        self.pixmap_item = None
        self.scale_factor = 1.0

    def eventFilter(self, obj, event) -> bool:
        """
        Application-level event filter handling both zoom and custom themed tooltips.

        - Viewport wheel events: handled first for zoom (existing behavior).
        - QEvent.ToolTip: intercepted to show _ThemedToolTip instead of the
          native OS tooltip, which ignores CSS border-radius on Windows in
          Light and Image modes.
        - Leave / MouseButtonPress / WindowDeactivate / Wheel: hides tooltip.
        """
        event_type = event.type()

        # --- Zoom handling for image viewer viewport (existing behavior) ---
        if obj == self.graphics_view.viewport():
            if event_type == QEvent.Type.Wheel:
                if not self.graphics_view.zoom_locked:
                    zoom_in_factor = 1.1
                    zoom_out_factor = 1 / zoom_in_factor

                    zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
                    self.scale_factor *= zoom_factor
                    self.scale_factor = max(0.1, min(self.scale_factor, 10.0))

                    self.graphics_view.scale(zoom_factor, zoom_factor)
                    self.zoom_label.setText(f"{int(self.scale_factor * 100)}%")
                return True

        # --- Custom themed tooltip handling ---
        if event_type == QEvent.Type.ToolTip:
            if isinstance(obj, QWidget) and obj.toolTip():
                theme = self.theme_manager.get_current_theme()
                tooltip_colors = {
                    'card_bg': theme['card_bg'],
                    'text_primary': theme['text_primary'],
                    'tooltip_border': theme['tooltip_border'],
                }
                _ThemedToolTip.instance().show_tip(
                    QCursor.pos(),
                    obj.toolTip(),
                    tooltip_colors,
                    self.font_family
                )
                return True  # Consume event — prevent native tooltip
        elif event_type in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress,
                            QEvent.Type.WindowDeactivate, QEvent.Type.Wheel):
            _ThemedToolTip.instance().hide_tip()

        return super().eventFilter(obj, event)

    def extract_colors_from_selection(self, rect: QRectF) -> None:
        """Extract colors from a selected region."""
        if not self.pixmap_item or not self.image:
            return
        
        x1 = int(rect.left())
        y1 = int(rect.top())
        x2 = int(rect.right())
        y2 = int(rect.bottom())
        
        width, height = self.image.size
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        if x1 >= x2 or y1 >= y2:
            return
        
        cropped = self.image.crop((x1, y1, x2, y2))
        
        img_array = np.array(cropped)
        pixels = img_array.reshape(-1, 3)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        
        sorted_idx = np.argsort(counts)[::-1]
        unique_colors = unique_colors[sorted_idx]
        
        if not self.preserve_colors:
            self.clear_colors()
        
        rgb_list = [tuple(rgb) for rgb in unique_colors]
        added_count, skipped = self.add_colors_batch(rgb_list, source="selection")
        
        remaining = self.get_remaining_slots()
        msg = f"Added {added_count} colors"
        if skipped > 0:
            msg += f"\nSkipped {skipped} duplicates"
        if remaining == 0:
            msg += f"\nMax capacity reached ({self.MAX_COLORS} colors)"
        else:
            msg += f"\n{remaining} slots remaining"
        
        DialogHelper.show_info(self, msg, title="Selection Colors")
        logger.success(f"Extracted {added_count} colors from selection")
        
        self.sort_colors()
        self.refresh_color_display(show_progress=False)

    def create_button_frame(self) -> QFrame:
        """Create the button toolbar."""
        logger.info("Building UI...")
        
        button_frame = QFrame()
        self.button_frame = button_frame
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)

        buttons = [
            ("Upload Image", self.upload_image, "upload"),
            ("Grab ALL Colors", self.pick_all_colors, "grab"),
            ("Dominant Colors", self.extract_dominant_colors, "dominant"),
            ("Screen Picker", self.screen_picker, "screen"),
            ("Save As Image", self.save_colors_as_image, "save"),
            ("Export Palette", self.export_palette, "export"),
            ("Clear All Colors", self.clear_colors, "clear"),
            ("Reset Zoom/Pan", self.reset_zoom_pan, "reset")
        ]

        for text, callback, img_name in buttons:
            btn = ImageButton(text, img_name)
            btn.img_name = img_name  # Store for tooltip lookup
            btn.set_theme_manager(self.theme_manager)
            self.signal_manager.connect(
                btn, btn.clicked, callback, f"btn_{img_name}_clicked"
            )
            button_layout.addWidget(btn)
            self.all_buttons.append(btn)
            logger.debug(f"Loaded button images: {text}")

        return button_frame

    def upload_image(self) -> None:
        """Upload an image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Image files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.image = Image.open(file_path).convert("RGB")
            self.display_image()

    def display_image(self) -> None:
        """Display the loaded image."""
        if not self.image:
            return
        
        img_array = np.array(self.image)
        height, width, channel = img_array.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            img_array.data, width, height, bytes_per_line, 
            QImage.Format.Format_RGB888
        )
        self.current_pixmap = QPixmap.fromImage(q_image)
        
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(self.current_pixmap)
        self.scene.addItem(self.pixmap_item)
        
        # Image is loaded - show the zoom indicator
        self.zoom_label.show()
        
        self.reset_zoom_pan()

    def reset_zoom_pan(self) -> None:
        """Reset zoom and pan to default."""
        if self.pixmap_item:
            self.graphics_view.resetTransform()
            self.graphics_view.fitInView(
                self.pixmap_item, 
                Qt.AspectRatioMode.KeepAspectRatio
            )
            self.scale_factor = 1.0
            self.zoom_label.setText("100%")

    def open_settings(self) -> None:
        """Open the settings panel dialog."""
        try:
            # Create panel if it doesn't exist or was closed
            if self.settings_panel is None or not self.settings_panel.isVisible():
                logger.info("Opening Settings Panel...")
                self.settings_panel = SettingsPanel(self)
                
                # Connect signals
                self.signal_manager.connect(
                    self.settings_panel, 
                    self.settings_panel.settings_changed, 
                    self._on_setting_changed, 
                    "settings_panel_changed"
                )
                self.signal_manager.connect(
                    self.settings_panel,
                    self.settings_panel.theme_change_requested,
                    self._on_theme_change_requested,
                    "settings_panel_theme_change"
                )
                self.signal_manager.connect(
                    self.settings_panel,
                    self.settings_panel.color_loaded_from_history,
                    self._on_color_loaded_from_history,
                    "settings_panel_color_loaded"
                )
                logger.success("Settings Panel loaded")
            
            self.settings_panel.show()
            self.settings_panel.raise_()
            self.settings_panel.activateWindow()
            
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to open settings panel:\n{e}",
                title="Settings Error"
            )
            logger.error(f"Failed to open settings panel: {e}")
    
    def open_about(self) -> None:
        """Open the About dialog."""
        try:
            # Always create a fresh dialog (previous one is deleted on close)
            logger.info("Opening About dialog...")
            self.about_dialog = AboutDialog(self)
            self.about_dialog.destroyed.connect(self._on_about_dialog_destroyed)
            logger.success("About dialog created")
            
            self.about_dialog.show()
            self.about_dialog.raise_()
            self.about_dialog.activateWindow()
            
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to open about dialog:\n{e}",
                title="About Error"
            )
            logger.error(f"Failed to open about dialog: {e}")
    
    def _on_about_dialog_destroyed(self) -> None:
        """Handle about dialog being destroyed."""
        self.about_dialog = None
    
    def _on_setting_changed(self, key: str, value: object) -> None:
        """Handle settings changes from the settings panel."""
        try:
            logger.debug(f"Setting changed: {key} = {value}")
            
            if key == "max_colors":
                self.MAX_COLORS = int(value)
            elif key == "default_sort_method":
                self.sort_method = str(value)
                if hasattr(self, 'sort_checkbox'):
                    self.sort_checkbox.setChecked(value == "hilbert")
                    self.sort_checkbox.setText(
                        "Sort: Hilbert Curve" if value == "hilbert" else "Sort: HSL"
                    )
            elif key == "preserve_colors_on_extract":
                self.preserve_colors = bool(value)
                if hasattr(self, 'preserve_checkbox'):
                    self.preserve_checkbox.setChecked(bool(value))
            elif key == "show_tooltips":
                self.tooltips_enabled = bool(value)
                self._apply_tooltips()
            elif key == "show_debug_overlay":
                if hasattr(self, 'debug_label'):
                    self.debug_label.setVisible(bool(value))
            
        except Exception as e:
            logger.error(f"Error applying setting {key}: {e}")
    
    def _on_theme_change_requested(self, theme: str) -> None:
        """Handle theme change from settings panel."""
        try:
            # Map theme name to manager state
            if theme == "dark":
                self.theme_manager.current_theme = 'dark'
                self.theme_manager.image_mode_active = False
            elif theme == "light":
                self.theme_manager.current_theme = 'light'
                self.theme_manager.image_mode_active = False
            elif theme == "image" and self.theme_manager.image_mode_available:
                self.theme_manager.current_theme = 'image'
                self.theme_manager.image_mode_active = True
            
            # Update UI
            self.theme_button.setText(self.theme_manager.get_theme_display_name())
            self.apply_theme()
            
            # Force theme button to recalculate size and position
            self.theme_button.adjustSize()
            self.theme_button.updateGeometry()
            self.update_checkbox_positions()
            self.update()
            
            logger.info(f"Theme changed to: {theme}")
            
        except Exception as e:
            logger.error(f"Error changing theme: {e}")
    
    def _on_color_loaded_from_history(self, rgb: tuple[int, int, int]) -> None:
        """Handle color loaded from history in settings panel."""
        try:
            # Add to color history again (updates timestamp)
            if hasattr(self, 'color_history') and self.color_history:
                self.color_history.add_color(rgb, source="history")
            
            if self.add_color(rgb):
                self.sort_colors()
                self.refresh_color_display(show_progress=False)
                logger.success(f"Added color from history: {rgb}")
            else:
                if len(self.colors) >= self.MAX_COLORS:
                    DialogHelper.show_warning(
                        self, 
                        f"Maximum capacity reached ({self.MAX_COLORS} colors)",
                        title="Max Colors"
                    )
                else:
                    DialogHelper.show_info(
                        self, 
                        "This color already exists in the palette",
                        title="Duplicate"
                    )
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to add color from history: {e}",
                title="Error"
            )
            logger.error(f"Error adding color from history: {e}")

    def screen_picker(self) -> None:
        """Launch the screen color picker overlay."""
        try:
            picker = ScreenColorPicker(self)
            self.signal_manager.connect(
                picker, picker.color_picked, self._on_color_picked_from_screen, "screen_picker_color_picked"
            )
            self.signal_manager.connect(
                picker, picker.picker_cancelled, self._on_screen_picker_cancelled, "screen_picker_cancelled"
            )
            picker.start_picking()
            
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to start screen color picker:\n{e}",
                title="Screen Picker Error"
            )
            logger.error(f"Failed to start screen picker: {e}")
    
    def _on_color_picked_from_screen(self, rgb: tuple[int, int, int]) -> None:
        """Handle color picked from screen picker."""
        try:
            # Add to color history
            if hasattr(self, 'color_history') and self.color_history:
                self.color_history.add_color(rgb, source="screen")
            
            if self.add_color(rgb):
                self.sort_colors()
                self.refresh_color_display(show_progress=False)
                logger.success(f"Added color from screen: {rgb}")
            else:
                if len(self.colors) >= self.MAX_COLORS:
                    DialogHelper.show_warning(
                        self, 
                        f"Maximum capacity reached ({self.MAX_COLORS} colors)",
                        title="Max Colors"
                    )
                else:
                    DialogHelper.show_info(
                        self, 
                        "This color already exists in the palette",
                        title="Duplicate"
                    )
        except Exception as e:
            DialogHelper.show_error(
                self,
                f"Failed to add color: {e}",
                title="Error"
            )
            logger.error(f"Error adding color from screen: {e}")
    
    def _on_screen_picker_cancelled(self) -> None:
        """Handle screen picker cancellation."""
        logger.info("Screen color picker cancelled by user")

    def pick_all_colors(self) -> None:
        """Extract all unique colors from the image."""
        import time
        
        if not self.image:
            DialogHelper.show_warning(self, "Please upload an image first!", title="No Image")
            return

        # Show indeterminate progress while processing image
        progress = LoadingDialog(
            title="Extracting Colors",
            total_colors=0,
            parent=self
        )
        progress.set_indeterminate(True)
        progress.set_status("Analyzing image for unique colors...")
        progress.show()
        
        # CRITICAL: Force dialog to fully render before heavy work
        progress.raise_()
        progress.activateWindow()
        progress.repaint()
        QApplication.processEvents()
        time.sleep(0.1)  # Allow paint to complete
        QApplication.processEvents()

        # Heavy numpy operation
        img_array = np.array(self.image)
        pixels = img_array.reshape(-1, 3)
        
        progress.set_status("Finding unique colors...")
        QApplication.processEvents()

        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        total_colors = len(unique_colors)
        
        progress.set_status(f"Found {total_colors} unique colors, sorting...")
        QApplication.processEvents()

        sorted_idx = np.argsort(counts)[::-1]
        unique_colors = unique_colors[sorted_idx]
        
        # Close initial progress
        progress.accept()

        if not self.preserve_colors:
            self.clear_colors()
        
        rgb_list = [tuple(rgb) for rgb in unique_colors]
        
        # Use progress dialog for large operations (50+ colors)
        if len(rgb_list) > 50:
            added_count, skipped = self._add_colors_with_progress(rgb_list, source="grab")
        else:
            added_count, skipped = self.add_colors_batch(rgb_list, source="grab")
        
        remaining = self.get_remaining_slots()
        msg = f"Image contains {total_colors} unique colors\n"
        msg += f"Added {added_count} colors"
        if skipped > 0:
            msg += f"\nSkipped {skipped} duplicates"
        if remaining == 0:
            msg += f"\nMax capacity reached ({self.MAX_COLORS} colors)"
        else:
            msg += f"\n{remaining} slots remaining"
        
        DialogHelper.show_info(self, msg, title="Unique Colors")
        if logger:
            logger.success(f"Extracted {added_count} unique colors from image")
        
        self.sort_colors()
        self.refresh_color_display(show_progress=False)

    def extract_dominant_colors(self) -> None:
        """Extract dominant colors using K-means clustering."""
        import time
        
        if not self.image:
            DialogHelper.show_warning(self, "Upload an image first!", title="No Image")
            return
        
        num_colors, ok = DialogHelper.get_int(
            self,
            "Number of Colors",
            "How many dominant colors?",
            value=5,
            min_value=2,
            max_value=33
        )
        
        if not ok:
            return
        
        # Show progress during KMeans (can be slow)
        progress = LoadingDialog(
            title="Extracting Dominant Colors",
            total_colors=num_colors,
            parent=self
        )
        progress.set_indeterminate(True)
        progress.set_status("Analyzing image with K-means clustering...")
        progress.show()
        
        # CRITICAL: Force dialog to fully render before heavy work
        progress.raise_()
        progress.activateWindow()
        progress.repaint()
        QApplication.processEvents()
        time.sleep(0.1)  # Allow paint to complete
        QApplication.processEvents()
        
        img_small = self.image.resize((150, 150))
        pixels = np.array(img_small).reshape(-1, 3)
        
        progress.set_status(f"Finding {num_colors} dominant colors...")
        QApplication.processEvents()
        
        kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
        labels = kmeans.fit_predict(pixels)
        centers = kmeans.cluster_centers_.astype(int)
        counts = np.bincount(labels)
        sorted_idx = np.argsort(counts)[::-1]
        
        # Close progress
        progress.accept()
        
        if not self.preserve_colors:
            self.clear_colors()
        
        rgb_list = [tuple(centers[idx]) for idx in sorted_idx]
        added_count, skipped = self.add_colors_batch(rgb_list, source="dominant")
        
        remaining = self.get_remaining_slots()
        msg = f"Added {added_count} dominant colors"
        if skipped > 0:
            msg += f"\nSkipped {skipped} duplicates"
        if remaining == 0:
            msg += f"\nMax capacity reached ({self.MAX_COLORS} colors)"
        else:
            msg += f"\n{remaining} slots remaining"
        
        DialogHelper.show_info(self, msg, title="Dominant Colors")
        logger.success(f"Extracted {added_count} dominant colors using K-means")
        
        self.sort_colors()
        self.refresh_color_display(show_progress=False)

    def remove_color_by_data(
        self, 
        rgb: tuple[int, int, int], 
        hsl: tuple[int, int, int], 
        hilbert_idx: int
    ) -> None:
        """Remove a color regardless of lock state (for right-click remove)."""
        self.colors = [
            color for color in self.colors 
            if not (color[0] == rgb and color[1] == hsl and color[2] == hilbert_idx)
        ]
        self.refresh_color_display(show_progress=False)

    def clear_colors(self) -> None:
        """Clear all colors except locked ones."""
        locked_colors = [color for color in self.colors if color[3]]
    
        if locked_colors:
            self.colors = locked_colors
            self.refresh_color_display(show_progress=False)
            DialogHelper.show_info(
                self, 
                f"{len(locked_colors)} locked color(s) were preserved",
                title="Locked Colors Preserved"
            )
            logger.info(f"Preserved {len(locked_colors)} locked colors during clear")
        else:
            # Safely release widgets - some may have been deleted by pool overflow
            for widget in self.color_widgets:
                try:
                    # Check if widget is still valid (not deleted at C++ level)
                    if widget is not None:
                        self.grid_layout.removeWidget(widget)
                        widget.hide()
                except RuntimeError:
                    # Widget was already deleted by the pool - skip it
                    pass
            
            # Return all to pool for reuse
            self.swatch_pool.release_all()
            
            self.colors.clear()
            self.color_widgets.clear()

    def save_color_swatch(self, rgb: tuple[int, int, int], size: int = 100) -> None:
        """Save a single color swatch as an image."""
        swatch = Image.new("RGB", (size, size), rgb)
        filename = f"color_{rgb[0]}_{rgb[1]}_{rgb[2]}.png"
        swatch.save(filename)
        DialogHelper.show_info(self, f"Saved {filename}", title="Saved")
        logger.success(f"Saved color swatch: {filename}")

    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts for the application."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        if logger:
            logger.info("Setting up keyboard shortcuts...")
        
        # Store shortcuts as instance variables to prevent garbage collection
        self._shortcuts = []
        
        # Upload Image - Ctrl+O
        self.shortcut_upload = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_upload.activated.connect(self.upload_image)
        self._shortcuts.append(self.shortcut_upload)
        
        # Save Color Swatch - Ctrl+S
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_colors_as_image)
        self._shortcuts.append(self.shortcut_save)
        
        # Export Palette - Ctrl+E
        self.shortcut_export = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_export.activated.connect(self.export_palette)
        self._shortcuts.append(self.shortcut_export)
        
        # Screen Color Picker - Ctrl+Shift+C
        self.shortcut_screen_picker = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.shortcut_screen_picker.activated.connect(self.screen_picker)
        self._shortcuts.append(self.shortcut_screen_picker)
        
        # Settings - Ctrl+, (comma)
        self.shortcut_settings_comma = QShortcut(QKeySequence("Ctrl+,"), self)
        self.shortcut_settings_comma.activated.connect(self.open_settings)
        self._shortcuts.append(self.shortcut_settings_comma)
        
        # Settings - Ctrl+P
        self.shortcut_settings_p = QShortcut(QKeySequence("Ctrl+P"), self)
        self.shortcut_settings_p.activated.connect(self.open_settings)
        self._shortcuts.append(self.shortcut_settings_p)
        
        # Clear Colors - Ctrl+D
        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut_clear.activated.connect(self.clear_colors)
        self._shortcuts.append(self.shortcut_clear)
        
        # Reset Zoom - Ctrl+0
        self.shortcut_reset_zoom = QShortcut(QKeySequence("Ctrl+0"), self)
        self.shortcut_reset_zoom.activated.connect(self.reset_zoom_pan)
        self._shortcuts.append(self.shortcut_reset_zoom)
        
        # About Dialog - Ctrl+/
        self.shortcut_about = QShortcut(QKeySequence("Ctrl+/"), self)
        self.shortcut_about.activated.connect(self.open_about)
        self._shortcuts.append(self.shortcut_about)
        
        # Grab All Colors - Ctrl+G
        self.shortcut_grab_all = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_grab_all.activated.connect(self.pick_all_colors)
        self._shortcuts.append(self.shortcut_grab_all)
        
        # Dominant Colors - Ctrl+K
        self.shortcut_dominant = QShortcut(QKeySequence("Ctrl+K"), self)
        self.shortcut_dominant.activated.connect(self.extract_dominant_colors)
        self._shortcuts.append(self.shortcut_dominant)
        
        # Toggle Tooltips - F11
        self.shortcut_tooltips = QShortcut(QKeySequence("F11"), self)
        self.shortcut_tooltips.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_tooltips.activated.connect(self.toggle_tooltips)
        self._shortcuts.append(self.shortcut_tooltips)
        
        # Toggle Debug Overlay - F12
        self.shortcut_debug = QShortcut(QKeySequence("F12"), self)
        self.shortcut_debug.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_debug.activated.connect(self.toggle_debug_overlay)
        self._shortcuts.append(self.shortcut_debug)
        
        if logger:
            logger.success("Keyboard shortcuts initialized")
        
        # Print shortcut summary
        shortcuts_info = [
            "  Ctrl+O - Upload Image",
            "  Ctrl+S - Save Color Swatch",
            "  Ctrl+E - Export Palette",
            "  Ctrl+Shift+C - Screen Color Picker",
            "  Ctrl+, or Ctrl+P - Settings & Features",
            "  Ctrl+D - Clear Colors",
            "  Ctrl+0 - Reset Zoom",
            "  Ctrl+/ - About Dialog",
            "  Ctrl+G - Grab All Colors",
            "  Ctrl+K - Dominant Colors",
            "  F11 - Toggle Tooltips",
            "  F12 - Toggle Debug Overlay",
        ]
        for shortcut in shortcuts_info:
            print(f"         |                      | {shortcut}")

    def get_current_state(self) -> dict | None:
        """
        Get current application state for session saving.
        
        Returns:
            Dictionary with colors, image_path, and settings, or None if no data
        """
        if not self.colors:
            return None
        
        try:
            # Convert all values to Python int to avoid numpy uint8 JSON serialization issues
            colors_data = [
                {
                    'rgb': [int(v) for v in c[0]], 
                    'hsl': [int(v) for v in c[1]], 
                    'hilbert': int(c[2]), 
                    'locked': bool(c[3])
                }
                for c in self.colors
            ]
            
            return {
                'colors': colors_data,
                'image_path': getattr(self, 'current_image_path', None),
                'settings': {
                    'sort_method': self.sort_method,
                    'preserve_colors': self.preserve_colors,
                    'theme': self.theme_manager.current_theme
                }
            }
        except Exception as e:
            if logger:
                logger.error(f"Error getting current state: {e}")
            return None

    def closeEvent(self, event) -> None:
        """Handle application close event with proper cleanup."""
        try:
            # 0. Remove app-level event filter and hide custom tooltip
            QApplication.instance().removeEventFilter(self)
            _ThemedToolTip.instance().hide_tip()

            # 1. Stop any active workers/threads
            if hasattr(self, 'current_worker') and self.current_worker:
                if self.current_worker.isRunning():
                    self.current_worker.cancel()
                    self.current_worker.quit()
                    self.current_worker.wait(1000)  # Wait up to 1 second
                    if logger:
                        logger.info("Stopped active worker thread")
            
            # 2. Disconnect all tracked signals
            if self.signal_manager:
                disconnected = self.signal_manager.disconnect_all()
                if logger:
                    logger.info(f"Disconnected {disconnected} signal connections")
            
            # 3. Clear widget pool if exists
            if hasattr(self, 'swatch_pool') and self.swatch_pool:
                self.swatch_pool.clear()
                if logger:
                    logger.info("Cleared widget pool")
            
            # 4. Clear pixmap cache
            if hasattr(self, 'pixmap_cache') and self.pixmap_cache:
                self.pixmap_cache.clear()
                if logger:
                    logger.info("Cleared pixmap cache")
            
            # 5. Clear color caches (log stats first)
            try:
                from utils.cache import clear_all_caches, log_cache_stats
                log_cache_stats()  # Log performance stats before clearing
                clear_all_caches()
                if logger:
                    logger.info("Cleared all color caches")
            except ImportError:
                pass
            
            # 6. Close settings panel if open
            if hasattr(self, 'settings_panel') and self.settings_panel:
                self.settings_panel.close()
            
            # 7. Close about dialog if open
            if hasattr(self, 'about_dialog') and self.about_dialog:
                self.about_dialog.close()
            
            # 8. Shutdown session manager (handles auto-save timer and final save)
            if hasattr(self, 'session_manager') and self.session_manager:
                # Check if auto-save on exit is enabled in settings
                auto_save_enabled = True  # Default to True for safety
                if hasattr(self, 'settings_manager') and self.settings_manager:
                    auto_save_enabled = self.settings_manager.get("auto_save_session", True)
                
                if auto_save_enabled:
                    # Let session manager handle the final save with proper session ID
                    self.session_manager.shutdown()
                else:
                    # Just stop the timer without saving
                    self.session_manager.stop_autosave()
                    if logger:
                        logger.debug("Auto-save on exit is disabled in settings")
            
            # 10. Save color history
            if hasattr(self, 'color_history') and self.color_history:
                try:
                    self.color_history.save_history()
                    if logger:
                        logger.info("Saved color history")
                except Exception as e:
                    if logger:
                        logger.warning(f"Failed to save color history: {e}")
            
            if logger:
                logger.success("Application closing - cleanup complete")
            
        except Exception as e:
            if logger:
                logger.error(f"Error during cleanup: {e}")
        
        event.accept()


def print_startup_banner():
    """Print the startup banner with version info."""
    separator = "=" * 60
    title = f"RNV Color Picker v{APP_VERSION}".center(58)
    
    print(separator)
    print(f"={title}=")
    print(separator)


def main():
    """Main application entry point with comprehensive logging."""
    # Print startup banner
    print_startup_banner()
    
    logger.info("Starting Color Picker application...")
    
    # High DPI setting for Qt6
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Use Fusion style for consistent cross-platform rendering
    app.setStyle("Fusion")
    
    # Load and apply font
    global_font = load_embedded_font(10)
    app.setFont(global_font)
    logger.success("Universal font stylesheet applied")
    
    # Create main window
    logger.info("Creating main window...")
    window = ColorPickerApp()
    
    # Show window
    logger.info("Showing window...")
    window.show()
    
    logger.success("Application ready!")
    print("=" * 60)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()