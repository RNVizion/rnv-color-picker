"""
RNV Color Picker - Professional Color Extraction Application

A PyQt6-based application for extracting, organizing, and exporting colors
from images.

Features:
- Upload and sample colors from images
- Screen color picker with magnifier
- Dominant color extraction using K-means clustering
- Multiple palette export formats (ASE, ACO, GPL, JSON, etc.)
- Dark/Light/Image themes
- Hilbert curve color sorting
- Session save/load
- Keyboard shortcuts

Packages:
- core: Core color manipulation and extraction modules
- ui: User interface widgets and components  
- utils: Utility functions and configuration

Author: RNV
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "RNV"
__app_name__ = "RNV Color Picker"

# Logger setup (deferred to avoid circular imports)
_logger = None

def _get_package_logger():
    """Get or create package logger (lazy initialization)."""
    global _logger
    if _logger is None:
        try:
            from .logger import Logger
            _logger = Logger("RNVColorPicker")
        except ImportError:
            pass
    return _logger

# Main exports
from .RNV_Color_Picker import ColorPickerApp

__all__ = ['ColorPickerApp', '__version__', '__author__', '__app_name__']
