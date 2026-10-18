"""
Application configuration and theme management for RNV Color Picker.

Structure:
- Application metadata, limits, UI dimensions and paths
- ThemeManager class for runtime theme state

Every color lives in utils/colors.py (#63 A, 2026-10-18), which this module
reads its theme dicts from.

Python 3.13 optimized - using modern type hints.
"""

from __future__ import annotations

import os
import io
from PIL import Image
from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QPixmap

from utils.logger import Logger
# The colors this module draws with. They live in utils/colors.py; import them from there.
from utils.colors import (
    get_theme_colors, APP_BORDER, DARK_THEME_COLORS, IMAGE_MODE_COLORS, LIGHT_THEME_COLORS,
)

_logger = Logger("Config")


# ============================================================================
# APPLICATION CONSTANTS
# ============================================================================

# Application metadata
APP_NAME = "RNV Color Picker"
APP_VERSION = "3.0.3"
APP_AUTHOR = "RNV"
APP_TAGLINE = "Professional Color Extraction & Palette Management"

# Color limits
MAX_COLORS = 333
DEFAULT_WEIGHT = 50

# UI dimensions
BUTTON_HEIGHT_MIN = 40
BUTTON_HEIGHT_MAX = 55
WINDOW_WIDTH_MIN = 1059
WINDOW_WIDTH_MAX = 1920
SWATCH_SIZE = 150

# Image handling
MAX_IMAGE_DIMENSION = 3840

# Paths - using __file__ to get correct path relative to this module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
BUTTON_IMAGES_DIR = os.path.join(RESOURCES_DIR, "button_images")
BACKGROUND_IMAGES_DIR = os.path.join(RESOURCES_DIR, "background_images")
FONTS_DIR = os.path.join(RESOURCES_DIR, "fonts")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")


# ============================================================================
# THEME MANAGER
# ============================================================================

class ThemeManager:
    """
    Manages application theme state (Dark / Light / Image) at runtime.
    
    Theme color dicts are module-level constants in utils/colors.py. This class
    handles theme switching, image-mode detection, and provides the active
    theme dict via get_current_theme().
    """
    
    def __init__(self):
        self.current_theme = 'dark'
        self.image_mode_available = False
        self.image_mode_active = False
        self.background_pixmap: QPixmap | None = None
    
    def detect_image_resources(self) -> bool:
        """Check if custom images are available for Image Mode."""
        bg_path = os.path.join(BACKGROUND_IMAGES_DIR, "background.png")
        has_background = False

        if os.path.exists(bg_path):
            try:
                img = Image.open(bg_path)

                max_dimension = MAX_IMAGE_DIMENSION
                if img.width > max_dimension or img.height > max_dimension:
                    ratio = min(max_dimension / img.width, max_dimension / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    if _logger:
                        _logger.info(f"Resized background image to {new_size[0]}x{new_size[1]}")

                buffer = QByteArray()
                bio = io.BytesIO()
                img.save(bio, format="PNG")
                buffer.append(bio.getvalue())

                pixmap = QPixmap()
                pixmap.loadFromData(buffer)

                self.background_pixmap = pixmap
                has_background = True
                if _logger:
                    _logger.success(f"Loaded background image: {img.width}x{img.height}")

            except Exception as e:
                if _logger:
                    _logger.error(f"Failed to load background image: {e}")
        
        button_names = ['upload', 'grab', 'dominant', 'screen', 'save', 'export', 'clear', 'reset']
        button_count = sum(
            1 for name in button_names 
            if os.path.exists(os.path.join(BUTTON_IMAGES_DIR, f"{name}.png")) or
               os.path.exists(os.path.join(BUTTON_IMAGES_DIR, f"{name}_base.png"))
        )
        
        self.image_mode_available = has_background or button_count >= 3
        
        if self.image_mode_available:
            self.image_mode_active = True
            self.current_theme = 'image'
        
        return self.image_mode_available
    
    def cycle_theme(self) -> str:
        """Cycle through available themes."""
        if self.image_mode_available:
            if self.current_theme == 'image':
                self.current_theme = 'dark'
                self.image_mode_active = False
            elif self.current_theme == 'dark':
                self.current_theme = 'light'
            else:
                self.current_theme = 'image'
                self.image_mode_active = True
        else:
            self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        
        return self.current_theme
    
    def get_current_theme(self) -> dict[str, str | int]:
        """Get the active theme's color dict."""
        return get_theme_colors(self.current_theme)
    
    def get_theme_display_name(self) -> str:
        """Get display name for current theme."""
        match self.current_theme:
            case 'dark':
                return "Dark Mode"
            case 'light':
                return "Light Mode"
            case 'image':
                return "Image Mode"
            case _:
                return "Unknown"
    
    def is_image_mode(self) -> bool:
        """Check if currently in image mode."""
        return self.image_mode_active and self.current_theme == 'image'
    
    # ------------------------------------------------------------------------
    # Scrollbar stylesheet builders — generate stylesheets from theme dicts.
    # These are classmethods that accept an optional theme dict; if omitted,
    # they use the class-level defaults for backward compatibility with code
    # that references ThemeManager.SCROLLBAR_DARK as a static string.
    # ------------------------------------------------------------------------
    
    @classmethod
    def _build_scrollbar(cls, theme: dict[str, str | int]) -> str:
        """Build a scrollbar stylesheet from a theme dict."""
        bg          = theme['scrollbar_bg']
        handle      = theme['scrollbar_handle']
        hover       = theme['scrollbar_handle_hover']
        border      = theme.get('scrollbar_border', theme.get('border_default', APP_BORDER))
        return f"""
            QScrollBar:vertical {{
                background: {bg};
                width: 12px;
                margin: 0px;
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background: {bg};
                height: 12px;
                margin: 0px;
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """


# ============================================================================
# SCROLLBAR STYLESHEETS — Module-level (pre-built for backward compatibility)
# ============================================================================
# These exist as module-level class attributes so existing code references
# like `ThemeManager.SCROLLBAR_DARK` continue to work. They're pre-built
# from the theme dicts so there's still a single source of truth.

ThemeManager.SCROLLBAR_DARK  = ThemeManager._build_scrollbar(DARK_THEME_COLORS)
ThemeManager.SCROLLBAR_LIGHT = ThemeManager._build_scrollbar(LIGHT_THEME_COLORS)

# Image mode scrollbar keeps its own GEOMETRY -- 15px, borderless, the
# transparent overlay look -- and takes its COLORS from IMAGE_MODE_COLORS.
# RNV-DERIVE-ALPHA (2026-09-25): it used to spell its own rgba() values
# here, "not built from theme dict", so two rulings that landed in the
# palette never reached the main window: the handle stayed #505050
# (RNV-COLLAPSE-505050) and the hover stayed gray (the 2026-09-12 gold
# hover). Reading the palette is what carries both.
ThemeManager.SCROLLBAR_IMAGE = f"""
    QScrollBar:vertical {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_bg']};
        width: 15px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_handle']};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_handle_hover']};
    }}
    QScrollBar::sub-page:vertical {{
        background-color: transparent;
    }}
    QScrollBar::add-page:vertical {{
        background-color: transparent;
    }}
    QScrollBar:horizontal {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_bg']};
        height: 15px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_handle']};
        min-width: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {IMAGE_MODE_COLORS['scrollbar_handle_hover']};
    }}
    QScrollBar::sub-page:horizontal {{
        background-color: transparent;
    }}
    QScrollBar::add-page:horizontal {{
        background-color: transparent;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        border: none;
        background: none;
    }}
"""


# ============================================================================
# PUBLIC API
# ============================================================================

__all__: list[str] = [
    # Classes
    'ThemeManager',
    # App constants
    'APP_NAME', 'APP_VERSION', 'APP_AUTHOR', 'APP_TAGLINE',
    'MAX_COLORS', 'DEFAULT_WEIGHT',
    'BUTTON_HEIGHT_MIN', 'BUTTON_HEIGHT_MAX',
    'WINDOW_WIDTH_MIN', 'WINDOW_WIDTH_MAX', 'SWATCH_SIZE',
    'MAX_IMAGE_DIMENSION',
    # Paths
    'BASE_DIR', 'RESOURCES_DIR', 'BUTTON_IMAGES_DIR',
    'BACKGROUND_IMAGES_DIR', 'FONTS_DIR', 'ICONS_DIR',
]
