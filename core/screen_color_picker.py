"""
Screen Color Picker Widget
Cross-platform screen color picker that works outside the app window.

Python 3.13 optimized - using modern type hints.
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QCursor, QPaintEvent,
    QMouseEvent, QKeyEvent, QFont, QCloseEvent
)

from utils.logger import Logger
from utils.error_handler import ErrorHandler
from utils.signal_manager import SignalConnectionManager
from utils.cache import QColorCache
from utils.config import (
    BRAND_GOLD, BRAND_GOLD_RGB,
    OVERLAY_BLACK_LIGHT, OVERLAY_BLACK_HEAVY,
)

logger = Logger("ScreenPicker")
ERROR_HANDLER_AVAILABLE = True
SIGNAL_MANAGER_AVAILABLE = True
CACHE_AVAILABLE = True


class ScreenColorPicker(QWidget):
    """
    Fullscreen overlay for picking colors from anywhere on screen.
    Shows a magnified view of the area under the cursor.
    """
    
    # Signals
    color_picked = pyqtSignal(tuple)  # Emits RGB tuple when color is picked
    picker_cancelled = pyqtSignal()   # Emits when picker is cancelled (Esc)
    
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        
        # Initialize signal manager for proper cleanup
        if SIGNAL_MANAGER_AVAILABLE:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        # Widget setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Screen capture
        self.screenshot: QPixmap | None = None
        self.current_color: tuple[int, int, int] = (0, 0, 0)
        self.cursor_pos = QPoint(0, 0)
        
        # Magnifier settings
        self.magnifier_size = 140  # Size of magnifier square
        self.zoom_factor = 8       # How much to zoom
        
        # Update timer for smooth cursor tracking
        self.update_timer = QTimer(self)
        
        # Connect timer using signal manager for proper cleanup
        if self.signal_manager:
            self.signal_manager.connect(
                self.update_timer,
                self.update_timer.timeout,
                self._update_cursor_position,
                track_as="cursor_update_timer"
            )
        else:
            self.update_timer.timeout.connect(self._update_cursor_position)
        
        # Cache frequently used colors for performance
        self._init_cached_colors()
    
    def _init_cached_colors(self) -> None:
        """Initialize cached colors for efficient painting."""
        if CACHE_AVAILABLE and QColorCache:
            self._gold_color = QColorCache.get(BRAND_GOLD)
            self._gold_alpha = QColorCache.get((*BRAND_GOLD_RGB, 50))
            self._black_180 = QColorCache.get(OVERLAY_BLACK_HEAVY)
        else:
            self._gold_color = QColor(BRAND_GOLD)
            self._gold_alpha = QColor(*BRAND_GOLD_RGB, 50)
            self._black_180 = QColor(*OVERLAY_BLACK_HEAVY)
    
    def _get_current_color_qcolor(self) -> QColor:
        """Get QColor for current picked color."""
        if CACHE_AVAILABLE and QColorCache:
            return QColorCache.get(self.current_color)
        else:
            return QColor(*self.current_color)
    
    def start_picking(self) -> None:
        """Start the color picking process."""
        try:
            # Capture screen
            self._capture_screen()
            
            # Show fullscreen
            screen = self.screen()
            if screen:
                self.setGeometry(screen.availableGeometry())
            self.showFullScreen()
            
            # Start cursor tracking
            self.update_timer.start(16)  # ~60 FPS
            
            # Grab keyboard for Esc key
            self.grabKeyboard()
            
            if logger:
                logger.success("Screen color picker started (Click to pick, Esc to cancel)")
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="starting color picker",
                    show_traceback=True
                )
            elif logger:
                logger.error(f"Error starting color picker: {e}")
            self.close()
    
    def _capture_screen(self) -> None:
        """Capture the entire screen."""
        try:
            # Get the screen this widget is on
            screen = self.screen()
            if not screen:
                # Fallback to primary screen
                screen = QApplication.primaryScreen()
            
            if screen:
                # Capture screenshot
                self.screenshot = screen.grabWindow(0)
                if logger:
                    logger.success(f"Screenshot captured: {self.screenshot.width()}x{self.screenshot.height()}")
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="capturing screen",
                    show_traceback=True
                )
            elif logger:
                logger.error(f"Error capturing screen: {e}")
            self.screenshot = None
    
    def _update_cursor_position(self) -> None:
        """Update cursor position and current color."""
        try:
            # Get global cursor position
            self.cursor_pos = QCursor.pos()
            
            # Get color at cursor position
            if self.screenshot and not self.screenshot.isNull():
                x = max(0, min(self.cursor_pos.x(), self.screenshot.width() - 1))
                y = max(0, min(self.cursor_pos.y(), self.screenshot.height() - 1))
                
                color = self.screenshot.toImage().pixelColor(x, y)
                self.current_color = (color.red(), color.green(), color.blue())
            
            # Trigger repaint
            self.update()
            
        except Exception as e:
            if logger:
                logger.error(f"Error updating cursor: {e}")
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the magnifier and crosshair."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw semi-transparent overlay (cached)
            if CACHE_AVAILABLE and QColorCache:
                overlay_color = QColorCache.get(OVERLAY_BLACK_LIGHT)
            else:
                overlay_color = QColor(*OVERLAY_BLACK_LIGHT)
            painter.fillRect(self.rect(), overlay_color)
            
            # Draw magnifier
            self._draw_magnifier(painter)
            
            # Draw crosshair
            self._draw_crosshair(painter)
            
            # Draw color info
            self._draw_color_info(painter)
            
        except Exception as e:
            if logger:
                logger.error(f"Error in paint event: {e}")
    
    def _draw_magnifier(self, painter: QPainter) -> None:
        """Draw the magnified view of area under cursor."""
        if not self.screenshot or self.screenshot.isNull():
            return
        
        try:
            # Calculate magnifier position (offset from cursor)
            mag_offset = 60  # Distance from cursor
            mag_x = self.cursor_pos.x() + mag_offset
            mag_y = self.cursor_pos.y() + mag_offset
            
            # Keep magnifier on screen
            if mag_x + self.magnifier_size > self.width():
                mag_x = self.cursor_pos.x() - mag_offset - self.magnifier_size
            if mag_y + self.magnifier_size > self.height():
                mag_y = self.cursor_pos.y() - mag_offset - self.magnifier_size
            
            # Map cursor to local coordinates
            local_pos = self.mapFromGlobal(self.cursor_pos)
            
            # Calculate source rectangle (area to magnify)
            pixel_size = self.magnifier_size // self.zoom_factor
            src_x = max(0, local_pos.x() - pixel_size // 2)
            src_y = max(0, local_pos.y() - pixel_size // 2)
            src_rect = QRect(src_x, src_y, pixel_size, pixel_size)
            
            # Destination rectangle (where to draw magnified view)
            dest_rect = QRect(mag_x, mag_y, self.magnifier_size, self.magnifier_size)
            
            # Draw magnified screenshot
            painter.drawPixmap(dest_rect, self.screenshot, src_rect)
            
            # Draw grid
            self._draw_magnifier_grid(painter, dest_rect)
            
            # Draw center pixel highlight
            center_x = dest_rect.center().x()
            center_y = dest_rect.center().y()
            pixel_w = self.magnifier_size // self.zoom_factor
            highlight_rect = QRect(
                center_x - pixel_w // 2,
                center_y - pixel_w // 2,
                pixel_w,
                pixel_w
            )
            painter.setPen(QPen(self._gold_color, 2))  # Gold brand color (cached)
            painter.drawRect(highlight_rect)
            
            # Draw border around magnifier
            painter.setPen(QPen(self._gold_color, 3))  # Gold brand color (cached)
            painter.drawRect(dest_rect)
            
        except Exception as e:
            if logger:
                logger.error(f"Error drawing magnifier: {e}")
    
    def _draw_magnifier_grid(self, painter: QPainter, rect: QRect) -> None:
        """Draw grid lines in magnifier."""
        try:
            pixel_size = self.magnifier_size // self.zoom_factor
            
            # Draw vertical lines (gold brand color with transparency - cached)
            painter.setPen(QPen(self._gold_alpha, 1))
            for i in range(self.zoom_factor + 1):
                x = rect.left() + i * pixel_size
                painter.drawLine(x, rect.top(), x, rect.bottom())
            
            # Draw horizontal lines
            for i in range(self.zoom_factor + 1):
                y = rect.top() + i * pixel_size
                painter.drawLine(rect.left(), y, rect.right(), y)
                
        except Exception as e:
            if logger:
                logger.error(f"Error drawing grid: {e}")
    
    def _draw_crosshair(self, painter: QPainter) -> None:
        """Draw crosshair at cursor position."""
        try:
            local_pos = self.mapFromGlobal(self.cursor_pos)
            
            # Draw crosshair lines (gold brand color - cached)
            painter.setPen(QPen(self._gold_color, 2))
            
            # Vertical line
            painter.drawLine(local_pos.x(), 0, local_pos.x(), self.height())
            
            # Horizontal line
            painter.drawLine(0, local_pos.y(), self.width(), local_pos.y())
            
            # Draw center circle
            painter.setPen(QPen(self._gold_color, 2))
            painter.drawEllipse(local_pos, 20, 20)
            
        except Exception as e:
            if logger:
                logger.error(f"Error drawing crosshair: {e}")
    
    def _draw_color_info(self, painter: QPainter) -> None:
        """Draw color information near cursor."""
        try:
            # Color info position (below cursor)
            local_pos = self.mapFromGlobal(self.cursor_pos)
            info_x = local_pos.x() - 60
            info_y = local_pos.y() + 30
            
            # Keep on screen
            if info_y + 60 > self.height():
                info_y = local_pos.y() - 90
            if info_x < 0:
                info_x = 10
            if info_x + 120 > self.width():
                info_x = self.width() - 130
            
            # Draw background (cached black with alpha)
            info_rect = QRect(info_x, info_y, 120, 60)
            painter.fillRect(info_rect, self._black_180)
            painter.setPen(QPen(self._gold_color, 2))  # Gold border (cached)
            painter.drawRect(info_rect)
            
            # Draw color swatch
            swatch_rect = QRect(info_x + 5, info_y + 5, 30, 30)
            painter.fillRect(swatch_rect, self._get_current_color_qcolor())
            painter.drawRect(swatch_rect)
            
            # Draw color text (gold brand color - cached)
            painter.setPen(self._gold_color)
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            
            # HEX
            hex_color = f"#{self.current_color[0]:02X}{self.current_color[1]:02X}{self.current_color[2]:02X}"
            painter.drawText(info_x + 40, info_y + 15, hex_color)
            
            # RGB
            rgb_text = f"RGB: {self.current_color[0]}, {self.current_color[1]}, {self.current_color[2]}"
            painter.setFont(QFont("Arial", 7))
            painter.drawText(info_x + 40, info_y + 30, rgb_text)
            
            # Instructions
            painter.drawText(info_x + 5, info_y + 50, "Click to pick")
            
        except Exception as e:
            if logger:
                logger.error(f"Error drawing color info: {e}")
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click - pick the color."""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                # Emit the picked color
                self.color_picked.emit(self.current_color)
                if logger:
                    logger.success(f"Color picked: {self.current_color}")
                self.close()
                
        except Exception as e:
            if logger:
                logger.error(f"Error in mouse press: {e}")
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press - Esc to cancel."""
        try:
            if event.key() == Qt.Key.Key_Escape:
                if logger:
                    logger.info("Color picker cancelled")
                self.picker_cancelled.emit()
                self.close()
                
        except Exception as e:
            if logger:
                logger.error(f"Error in key press: {e}")
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up when closing."""
        try:
            # Stop update timer
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
                if logger:
                    logger.debug("Stopped update timer")
            
            # Disconnect signal manager connections if available
            if hasattr(self, 'signal_manager') and self.signal_manager:
                self.signal_manager.disconnect_all(quiet=True)
            
            # Release keyboard
            self.releaseKeyboard()
            
            # Clear screenshot to free memory
            self.screenshot = None
            
            if logger:
                logger.debug("Screen color picker closed cleanly")
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="closing screen color picker",
                    show_traceback=True
                )
            elif logger:
                logger.error(f"Error in close event: {e}")
        
        event.accept()