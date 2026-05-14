"""
Transparent scrollable widget for RNV Color Picker.

Provides a custom QWidget that can paint a semi-transparent background,
useful for overlay effects in Image Mode.

Python 3.13 optimized - using modern type hints.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPaintEvent

from utils.logger import Logger
from utils.cache import QColorCache
from utils.config import OVERLAY_BLACK_MEDIUM

logger = Logger("TransparentScroll")
CACHE_AVAILABLE = True


class TransparentScrollWidget(QWidget):
    """Custom widget that paints a semi-transparent background."""
    
    def __init__(self, parent: QWidget | None = None):
        """
        Initialize transparent scroll widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        # Use cached color if available
        if CACHE_AVAILABLE and QColorCache:
            self.bg_color = QColorCache.get(OVERLAY_BLACK_MEDIUM)  # Semi-transparent black
        else:
            self.bg_color = QColor(*OVERLAY_BLACK_MEDIUM)
        self.is_transparent_mode = False
        
    def set_transparent_mode(
        self, 
        enabled: bool, 
        color: QColor | None = None
    ) -> None:
        """
        Enable or disable transparent background mode.
        
        Args:
            enabled: Whether to enable transparent mode
            color: Optional custom background color
        """
        self.is_transparent_mode = enabled
        if color:
            self.bg_color = color
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint semi-transparent background in transparent mode.
        
        Args:
            event: Paint event
        """
        if self.is_transparent_mode:
            painter = QPainter(self)
            painter.fillRect(self.rect(), self.bg_color)
        super().paintEvent(event)