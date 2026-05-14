"""
Color swatch widget for RNV Color Picker.

Displays individual color swatches with:
- Color preview with number and HEX/RGB labels
- Lock/unlock functionality
- Right-click context menu for removing colors
- Theme-aware styling

Python 3.13 optimized - using modern type hints.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QAction, QPaintEvent

from utils.logger import Logger
from utils.cache import QColorCache, ColorCache, StylesheetCache
from utils.signal_manager import SignalConnectionManager
from utils.config import BRAND_GOLD

logger = Logger("ColorSwatch")
CACHE_AVAILABLE = True
SIGNAL_MANAGER_AVAILABLE = True

if TYPE_CHECKING:
    from RNV_Color_Picker import ColorPickerApp


class ColorSwatchWidget(QWidget):
    """Individual color swatch display with lock and remove functionality."""
    
    def __init__(
        self, 
        number: int = 0, 
        rgb: tuple[int, int, int] = (0, 0, 0), 
        hsl: tuple[int, int, int] = (0, 0, 0), 
        hilbert_idx: int = 0, 
        parent_app: ColorPickerApp = None
    ):
        """
        Initialize color swatch widget.
        
        Args:
            number: Display number for this color
            rgb: RGB color tuple (0-255, 0-255, 0-255)
            hsl: HSL color tuple
            hilbert_idx: Hilbert curve index for sorting
            parent_app: Reference to main application
        """
        super().__init__(parent_app)
        self.parent_app = parent_app
        
        # Initialize signal manager for tracked connections
        if SIGNAL_MANAGER_AVAILABLE:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        # Initialize with provided values or defaults
        self.number = number
        self.rgb = rgb
        self.hsl = hsl
        self.hilbert_idx = hilbert_idx
        
        # Use cached hex conversion if available
        if CACHE_AVAILABLE and ColorCache:
            self.hex_code = ColorCache.rgb_to_hex(rgb)
        else:
            self.hex_code = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        self.is_locked = False
        
        self.setFixedSize(150, 150)
        self.setMinimumSize(150, 150)
        
        # Enable context menu with tracked connection
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        if self.signal_manager:
            self.signal_manager.connect(
                self,
                self.customContextMenuRequested,
                self.show_context_menu,
                track_as="swatch_context_menu"
            )
        else:
            self.customContextMenuRequested.connect(self.show_context_menu)
    
    def configure(
        self,
        number: int,
        rgb: tuple[int, int, int],
        hsl: tuple[int, int, int],
        hilbert_idx: int,
        is_locked: bool = False
    ) -> None:
        """
        Configure/reconfigure widget with new color data.
        
        Used by WidgetPool for efficient widget reuse without reconstruction.
        
        Args:
            number: Display number for this color
            rgb: RGB color tuple (0-255, 0-255, 0-255)
            hsl: HSL color tuple
            hilbert_idx: Hilbert curve index for sorting
            is_locked: Whether the color is locked
        """
        self.number = number
        self.rgb = rgb
        self.hsl = hsl
        self.hilbert_idx = hilbert_idx
        self.is_locked = is_locked
        
        # Update hex code using cache if available
        if CACHE_AVAILABLE and ColorCache:
            self.hex_code = ColorCache.rgb_to_hex(rgb)
        else:
            self.hex_code = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        
        # Trigger repaint with new data
        self.update()
    
    def show_context_menu(self, pos: QPoint) -> None:
        """
        Show context menu for color swatch.
        
        Args:
            pos: Position where menu was requested
        """
        menu = QMenu(self)
    
        # Apply theme-specific styling
        theme = self.parent_app.theme_manager.get_current_theme()
        is_image_mode = self.parent_app.theme_manager.is_image_mode()
    
        # Enable transparency for the menu in Image Mode
        if is_image_mode:
            menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            menu.setWindowFlags(
                menu.windowFlags() | 
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.NoDropShadowWindowHint
            )
    
        if theme:
            # Use cached menu stylesheet
            theme_name = self.parent_app.theme_manager.current_theme
            if CACHE_AVAILABLE and StylesheetCache:
                menu_style = StylesheetCache.get_menu_stylesheet(
                    theme_name, is_image_mode, theme
                )
            else:
                # Fallback: inline stylesheet
                if is_image_mode:
                    menu_style = f"""
                        QMenu {{
                            background-color: rgba(0, 0, 0, 200);
                            color: {theme['text_primary']};
                            border: none;
                            padding: 2px;
                        }}
                        QMenu::item {{
                            background-color: transparent;
                            color: {theme['text_primary']};
                            padding: 6px 24px 6px 12px;
                            border-radius: 3px;
                            margin: 1px;
                        }}
                        QMenu::item:selected {{
                            background-color: {theme['hover_bg']};
                            color: {theme['text_accent']};
                        }}
                        QMenu::item:pressed {{
                            background-color: {theme['selected_bg']};
                            color: {theme['text_on_accent']};
                        }}
                    """
                else:
                    menu_style = f"""
                        QMenu {{
                            background-color: {theme['card_bg']};
                            color: {theme['text_primary']};
                            border: none;
                            padding: 2px;
                        }}
                        QMenu::item {{
                            background-color: transparent;
                            color: {theme['text_primary']};
                            padding: 6px 24px 6px 12px;
                            border-radius: 3px;
                            margin: 1px;
                        }}
                        QMenu::item:selected {{
                            background-color: {theme['hover_bg']};
                            color: {theme['text_accent']};
                        }}
                        QMenu::item:pressed {{
                            background-color: {theme['selected_bg']};
                            color: {theme['text_on_accent']};
                        }}
                    """
            menu.setStyleSheet(menu_style)
    
        # Add Copy submenu
        copy_menu = menu.addMenu("Copy Color")
        
        # Copy HEX
        copy_hex_action = QAction(f"HEX ({self.hex_code})", self)
        copy_hex_action.triggered.connect(self.copy_hex)
        copy_menu.addAction(copy_hex_action)
        
        # Copy RGB
        rgb_str = f"rgb({self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]})"
        copy_rgb_action = QAction(f"RGB ({rgb_str})", self)
        copy_rgb_action.triggered.connect(self.copy_rgb)
        copy_menu.addAction(copy_rgb_action)
        
        # Copy HSL
        hsl_str = f"hsl({self.hsl[0]}, {self.hsl[1]}%, {self.hsl[2]}%)"
        copy_hsl_action = QAction(f"HSL ({hsl_str})", self)
        copy_hsl_action.triggered.connect(self.copy_hsl)
        copy_menu.addAction(copy_hsl_action)
        
        menu.addSeparator()
    
        # Add Remove action
        remove_action = QAction("Remove Color", self)
        remove_action.triggered.connect(self.remove_color)
        menu.addAction(remove_action)
    
        # Add Lock/Unlock action
        lock_text = "Unlock Color" if self.is_locked else "Lock Color"
        lock_action = QAction(lock_text, self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)
    
        menu.exec(self.mapToGlobal(pos))
    
    def copy_hex(self) -> None:
        """Copy HEX color code to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.hex_code)
    
    def copy_rgb(self) -> None:
        """Copy RGB color value to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(f"rgb({self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]})")
    
    def copy_hsl(self) -> None:
        """Copy HSL color value to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(f"hsl({self.hsl[0]}, {self.hsl[1]}%, {self.hsl[2]}%)")
    
    def remove_color(self) -> None:
        """Remove this color from the palette."""
        self.parent_app.remove_color_by_data(self.rgb, self.hsl, self.hilbert_idx)
    
    def toggle_lock(self) -> None:
        """Toggle lock state for this color."""
        self.is_locked = not self.is_locked
        # Update the lock state in parent app's color list
        self.parent_app.update_color_lock_state(
            self.rgb, self.hsl, self.hilbert_idx, self.is_locked
        )
        self.update()  # Repaint to show lock indicator
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the color swatch with text labels.
        
        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use cached QColor if available
        if CACHE_AVAILABLE and QColorCache:
            fill_color = QColorCache.get(self.rgb)
        else:
            fill_color = QColor(*self.rgb)
        painter.fillRect(self.rect(), fill_color)
    
        theme = self.parent_app.theme_manager.get_current_theme()
        if theme:
            border_width = theme['swatch_border_width']
            if CACHE_AVAILABLE and QColorCache:
                border_color = QColorCache.get(theme['swatch_border_color'])
            else:
                border_color = QColor(theme['swatch_border_color'])
        else:
            border_width = 1
            border_color = QColorCache.BLACK
    
        # Draw lock indicator border if locked
        if self.is_locked:
            accent_hex = theme.get('text_accent', BRAND_GOLD) if theme else BRAND_GOLD
            if CACHE_AVAILABLE and QColorCache:
                lock_color = QColorCache.get(accent_hex)
            else:
                lock_color = QColor(accent_hex)
            painter.setPen(QPen(lock_color, border_width + 2))  # Custom beige border for locked
        else:
            painter.setPen(QPen(border_color, border_width))
    
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
    
        # Calculate font sizes based on widget size
        base_size = min(self.width(), self.height())
        num_font_size = max(8, int(base_size * 0.12))
        # Use smaller font for HEX/RGB to ensure they fit
        text_font_size = max(6, int(base_size * 0.08))
        
        # Determine text color based on background brightness (use cache if available)
        r, g, b = int(self.rgb[0]), int(self.rgb[1]), int(self.rgb[2])
        if CACHE_AVAILABLE and ColorCache:
            text_rgb = ColorCache.get_text_color_for_background((r, g, b))
            text_color = QColorCache.get(text_rgb)
        else:
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            text_color = QColorCache.BLACK if brightness > 128 else QColorCache.WHITE
    
        # Draw color number at top
        global_font = QApplication.font()
        num_font = QFont(global_font.family(), num_font_size, QFont.Weight.Bold)
        painter.setFont(num_font)
        painter.setPen(text_color)
        painter.drawText(5, num_font_size + 2, f"#{self.number}")
    
        # Draw HEX and RGB codes at bottom
        text_font = QFont(global_font.family(), text_font_size)
        painter.setFont(text_font)
        
        # Position text from bottom with proper spacing
        line_height = text_font_size + 4
        bottom_margin = 8
        
        # RGB on bottom line
        rgb_text = f"RGB({r},{g},{b})"
        rgb_y = self.height() - bottom_margin
        painter.drawText(5, rgb_y, rgb_text)
        
        # HEX above RGB
        hex_y = rgb_y - line_height
        painter.drawText(5, hex_y, self.hex_code)