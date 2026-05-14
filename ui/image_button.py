"""
Custom button widget with image mode support for RNV Color Picker.

Provides a QPushButton that can display:
- Text labels in normal themes (Dark/Light)
- Full-area images in Image Mode with hover/pressed states
- Dynamic height based on window width

Python 3.13 optimized - using modern type hints.
"""

import os
from PyQt6.QtWidgets import QPushButton, QWidget
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QCursor, 
    QPaintEvent, QMouseEvent, QEnterEvent
)

from utils.logger import Logger
from utils.cache import StylesheetCache
from utils.config import (
    BUTTON_IMAGES_DIR, BUTTON_HEIGHT_MIN, BUTTON_HEIGHT_MAX, 
    WINDOW_WIDTH_MIN, WINDOW_WIDTH_MAX
)

logger = Logger("ImageButton")
CACHE_AVAILABLE = True


class ImageButton(QPushButton):
    """QPushButton that fully fills the button area with icon in Image Mode."""
    
    def __init__(
        self, 
        text: str = "", 
        button_name: str = "", 
        parent: QWidget | None = None,
        always_use_image: bool = False
    ):
        """
        Initialize image button.
        
        Args:
            text: Button text label
            button_name: Name used to find button images
            parent: Parent widget
            always_use_image: If True, always display image regardless of theme
        """
        super().__init__(text, parent)
        
        self.button_text = text
        self.button_name = button_name
        self.theme_manager = None
        self.always_use_image = always_use_image
        self._icon: QIcon | None = None
        self._base_pixmap: QPixmap | None = None
        self._hover_pixmap: QPixmap | None = None
        self._pressed_pixmap: QPixmap | None = None

        # Enable mouse tracking to receive move events even when no button is pressed
        self.setMouseTracking(True)
        
        # Load button images
        self.base_img, self.hover_img, self.pressed_img = self._get_button_images(button_name)
        
        # Preload pixmaps for better quality
        if self.base_img and os.path.exists(self.base_img):
            self._base_pixmap = QPixmap(self.base_img)
            self._base_pixmap.setDevicePixelRatio(self.devicePixelRatioF())
        if self.hover_img and os.path.exists(self.hover_img):
            self._hover_pixmap = QPixmap(self.hover_img)
            self._hover_pixmap.setDevicePixelRatio(self.devicePixelRatioF())
        if self.pressed_img and os.path.exists(self.pressed_img):
            self._pressed_pixmap = QPixmap(self.pressed_img)
            self._pressed_pixmap.setDevicePixelRatio(self.devicePixelRatioF())
        
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Dynamic height configuration
        self.base_height = BUTTON_HEIGHT_MIN
        self.max_height = BUTTON_HEIGHT_MAX
        self.min_window_width = WINDOW_WIDTH_MIN
        self.max_window_width = WINDOW_WIDTH_MAX
        
        self.setMinimumHeight(self.base_height)
    
    def _get_button_images(
        self, 
        name: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Get base, hover, and pressed image paths for a button.
        
        Args:
            name: Button name
            
        Returns:
            Tuple of (base_path, hover_path, pressed_path)
        """
        name_underscore = name.lower().replace(' ', '_')
        
        def find_image(prefix: str, suffix: str) -> str | None:
            """Try to find image with both naming conventions."""
            path = os.path.join(BUTTON_IMAGES_DIR, f"{prefix}_{suffix}.png")
            if os.path.exists(path):
                return path
            
            path = os.path.join(BUTTON_IMAGES_DIR, f"{prefix.replace('_', '-')}_{suffix}.png")
            if os.path.exists(path):
                return path
            
            if suffix == "base":
                path = os.path.join(BUTTON_IMAGES_DIR, f"{prefix}.png")
                if os.path.exists(path):
                    return path
                path = os.path.join(BUTTON_IMAGES_DIR, f"{prefix.replace('_', '-')}.png")
                if os.path.exists(path):
                    return path
            
            return None
        
        base_img = find_image(name_underscore, "base")
        hover_img = find_image(name_underscore, "hover")
        pressed_img = find_image(name_underscore, "pressed")
        
        if not hover_img:
            hover_img = base_img
        if not pressed_img:
            pressed_img = base_img
            
        return base_img, hover_img, pressed_img
    
    def update_height_for_window(self, window_width: int) -> None:
        """
        Dynamically adjust button height based on window width.
        
        Args:
            window_width: Current window width in pixels
        """
        if window_width <= self.min_window_width:
            new_height = self.base_height
        elif window_width >= self.max_window_width:
            new_height = self.max_height
        else:
            # Linear interpolation between min and max
            ratio = (window_width - self.min_window_width) / (self.max_window_width - self.min_window_width)
            new_height = int(self.base_height + (self.max_height - self.base_height) * ratio)
        
        self.setMinimumHeight(new_height)
        self.setMaximumHeight(new_height)
    
    def setIcon(self, icon: QIcon) -> None:
        """Store icon and repaint."""
        self._icon = icon
        super().setIcon(icon)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint for Image Mode or always_use_image - fill button with icon."""
        # Check if we should use image painting
        use_image = self.always_use_image or (self.theme_manager and self.theme_manager.is_image_mode())
        
        if use_image and self._base_pixmap:
            # Use pixmap directly for better quality
            current_pixmap = self._base_pixmap
        
            # Manually check mouse position for accurate state detection
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            mouse_over = self.rect().contains(local_pos)
        
            # Determine which pixmap to show based on state
            if self.isDown() and mouse_over and self._pressed_pixmap:
                # Show pressed only if button is down AND mouse is over
                current_pixmap = self._pressed_pixmap
            elif not self.isDown() and mouse_over and self._hover_pixmap:
                # Show hover only if button is NOT down AND mouse is over
                current_pixmap = self._hover_pixmap
            # Otherwise show base state (already set)
        
            if current_pixmap and not current_pixmap.isNull():
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

                rect = self.rect()
                # Scale pixmap to button size with smooth transformation
                scaled_pixmap = current_pixmap.scaled(
                    rect.size() * self.devicePixelRatioF(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                scaled_pixmap.setDevicePixelRatio(self.devicePixelRatioF())
                painter.drawPixmap(rect, scaled_pixmap)
                return
    
        super().paintEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Handle mouse enter event."""
        if self.theme_manager and self.theme_manager.is_image_mode():
            self.update()  # Trigger repaint for hover state
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Handle mouse leave event."""
        if self.theme_manager and self.theme_manager.is_image_mode():
            self.update()  # Trigger repaint for normal state
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press event."""
        if self.theme_manager and self.theme_manager.is_image_mode():
            self.update()  # Trigger repaint for pressed state
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release event."""
        if self.theme_manager and self.theme_manager.is_image_mode():
            self.update()  # Trigger repaint for hover state
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Force repaint when mouse moves (especially when dragging)."""
        if self.theme_manager and self.theme_manager.is_image_mode():
            self.update()  # Trigger repaint to update button state
        super().mouseMoveEvent(event)

    def set_theme_manager(self, theme_manager) -> None:
        """Set theme manager for this button."""
        self.theme_manager = theme_manager
        self.apply_style()

    def apply_style(self) -> None:
        """Apply styling based on current theme."""
        # Check if we should use image styling
        use_image_style = self.always_use_image or (self.theme_manager and self.theme_manager.is_image_mode())
        
        if use_image_style and self._base_pixmap:
            # Using custom painting, so minimal stylesheet
            if CACHE_AVAILABLE and StylesheetCache:
                self.setStyleSheet(StylesheetCache.get_transparent_button_stylesheet())
            else:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                    }
                """)
            self.update()
            return

        # Clear icon for non-image modes
        self.setIcon(QIcon())
        self._icon = None

        if not self.theme_manager:
            return

        theme = self.theme_manager.get_current_theme()
        if not theme:
            return

        # Use cached stylesheet if available
        if CACHE_AVAILABLE and StylesheetCache:
            theme_name = self.theme_manager.current_theme
            self.setStyleSheet(StylesheetCache.get_image_button_stylesheet(theme_name, theme))
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['main_btn_bg']};
                    color: {theme['main_btn_text']};
                    border: 1px solid {theme['main_btn_border']};
                    padding: 2px 8px;
                    border-radius: 4px;
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
            """)