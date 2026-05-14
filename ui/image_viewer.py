"""
Image viewer widget for RNV Color Picker.

Provides a QGraphicsView for displaying images with:
- Zoom/pan functionality
- Drag-to-select region for color extraction
- Double-click to pick single pixel color
- Zoom lock feature
- Context menu for clearing image and toggling zoom lock

Python 3.13 optimized - using modern type hints.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QGraphicsView, QMenu
from PyQt6.QtCore import Qt, QPoint, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QAction, QBrush,
    QPaintEvent, QMouseEvent
)

from utils.logger import Logger
from utils.cache import QColorCache, StylesheetCache
from utils.signal_manager import SignalConnectionManager
from utils.config import BRAND_GOLD

logger = Logger("ImageViewer")
CACHE_AVAILABLE = True
SIGNAL_MANAGER_AVAILABLE = True

if TYPE_CHECKING:
    from RNV_Color_Picker import ColorPickerApp


class ImageViewer(QGraphicsView):
    """Graphics view for image display with selection and zoom capabilities."""
    
    def __init__(self, parent: ColorPickerApp | None = None):
        """
        Initialize image viewer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize signal manager for proper cleanup
        if SIGNAL_MANAGER_AVAILABLE:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Connect context menu using signal manager for proper cleanup
        if self.signal_manager:
            self.signal_manager.connect(
                self,
                self.customContextMenuRequested,
                self.show_context_menu,
                track_as="context_menu"
            )
        else:
            self.customContextMenuRequested.connect(self.show_context_menu)

        self.selection_start: QPointF | None = None
        self.selection_end: QPointF | None = None
        self.selection_rect_item = None
        self.scene_ref = None
        self.dragging = False
        self.parent_app: ColorPickerApp | None = None
        self.zoom_locked = False

    def show_context_menu(self, pos: QPoint) -> None:
        """
        Show context menu for image viewer.
        
        Args:
            pos: Position where menu was requested
        """
        # Always create menu, but with different options based on whether image exists
        menu = QMenu(self)
        
        # Apply theme-specific styling
        if self.parent_app:
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
        
        # Add menu items based on whether image exists
        if self.parent_app and self.parent_app.image:
            clear_action = QAction("Clear Image", self)
            clear_action.triggered.connect(self.parent_app.clear_image)
            menu.addAction(clear_action)
        
        lock_text = "Unlock Zoom" if self.zoom_locked else "Lock Zoom"
        lock_action = QAction(lock_text, self)
        lock_action.triggered.connect(self.toggle_zoom_lock)
        menu.addAction(lock_action)
        
        menu.exec(self.mapToGlobal(pos))

    def toggle_zoom_lock(self) -> None:
        """Toggle zoom lock and update visual border."""
        self.zoom_locked = not self.zoom_locked
        self.viewport().update()  # Trigger repaint to show/hide border

    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint to draw lock border when zoom is locked."""
        super().paintEvent(event)
        
        # Draw lock border if zoom is locked
        if self.zoom_locked:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Use accent color from current theme (matches locked swatch border)
            accent_hex = BRAND_GOLD
            if self.parent_app and hasattr(self.parent_app, 'theme_manager'):
                theme = self.parent_app.theme_manager.get_current_theme()
                if theme:
                    accent_hex = theme.get('text_accent', BRAND_GOLD)
            if CACHE_AVAILABLE and QColorCache:
                lock_color = QColorCache.get(accent_hex)
            else:
                lock_color = QColor(accent_hex)
            pen = QPen(lock_color, 4)  # 4px border width
            painter.setPen(pen)
            
            # Draw border around viewport
            rect = self.viewport().rect()
            painter.drawRect(rect.adjusted(2, 2, -2, -2))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_start = self.mapToScene(event.pos())
            self.selection_end = None
            self.dragging = True

            if self.selection_rect_item and self.scene_ref:
                self.scene_ref.removeItem(self.selection_rect_item)
                self.selection_rect_item = None

            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move to update selection rectangle."""
        if self.dragging and self.scene_ref and self.selection_start is not None:
            current_pos = self.mapToScene(event.pos())
            rect = QRectF(self.selection_start, current_pos).normalized()

            if not self.selection_rect_item:
                # Use cached yellow color for selection
                if CACHE_AVAILABLE and QColorCache:
                    yellow = QColorCache.get("yellow")
                else:
                    yellow = QColor("yellow")
                pen = QPen(yellow, 2, Qt.PenStyle.DotLine)
                pen.setCosmetic(True)
                self.selection_rect_item = self.scene_ref.addRect(rect, pen)
            else:
                self.selection_rect_item.setRect(rect)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to complete selection."""
        if self.dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.selection_end = self.mapToScene(event.pos())
            
            if self.selection_start is not None and self.selection_end is not None and self.parent_app:
                rect = QRectF(self.selection_start, self.selection_end).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    self.parent_app.extract_colors_from_selection(rect)
            
            if self.selection_rect_item and self.scene_ref:
                self.scene_ref.removeItem(self.selection_rect_item)
                self.selection_rect_item = None
            
            self.selection_start = None
            self.selection_end = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        Handle double-click to pick color from pixel.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton and self.parent_app and self.parent_app.pixmap_item:
            scene_pos = self.mapToScene(event.pos())
            self.parent_app.pick_color_from_pixel(scene_pos)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)