"""
Application configuration and theme management for RNV Color Picker.

This module is the SINGLE SOURCE OF TRUTH for all colors in the application.

Structure:
- Brand colors (BRAND_GOLD, BRAND_GOLD_DARK) — referenced everywhere, never duplicated
- Theme color dicts (DARK_THEME_COLORS, LIGHT_THEME_COLORS, IMAGE_MODE_COLORS)
- Standalone constants (CONTRAST_ON_LIGHT, PREVIEW_BORDER, DEBUG_TEXT, etc.)
- get_theme_colors() entry function
- ThemeManager class for runtime theme state

Any hardcoded color in another file is a bug. All colors must come from here.

Python 3.13 optimized - using modern type hints.
"""

from __future__ import annotations

import os
import io
from typing import Final
from PIL import Image
from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QPixmap

from utils.logger import Logger

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
# BRAND COLORS
# ============================================================================

BRAND_GOLD: Final[str] = "#d2bc93"
"""Primary brand gold - use for hover states, highlights, tooltips, accents in Dark/Image mode"""

BRAND_GOLD_DARK: Final[str] = "#b19145"
"""Darker brand gold - use for borders, pressed states, and contrast in Light mode"""

BRAND_GOLD_RGB: Final[tuple[int, int, int]] = (210, 188, 147)
"""Brand gold as RGB tuple"""

BRAND_GOLD_DARK_RGB: Final[tuple[int, int, int]] = (177, 145, 69)
"""Dark brand gold as RGB tuple"""

BRAND_GOLD_HOVER: Final[str] = "#dcc9a3"
"""Lighter gold tint for hover on gold-filled elements (dark theme)"""

BRAND_GOLD_PRESSED: Final[str] = "#b7a480"
"""Slightly darker gold for pressed state (dark theme)"""

BRAND_GOLD_DARK_HOVER: Final[str] = "#c4a458"
"""Lighter tint of dark gold for hover (light theme)"""

BRAND_GOLD_DARK_PRESSED: Final[str] = "#8a7236"
"""Darker tint of dark gold for pressed state (light theme)"""


# ============================================================================
# DARK THEME COLORS
# ============================================================================

DARK_THEME_COLORS: Final[dict[str, str | int]] = {
    'name': 'Dark',
    
    # ── Base surfaces ──
    'window_bg':          '#000000',
    'panel_bg':           '#1A1A1A',
    'card_bg':            '#2A2A2A',
    'bg_secondary':       '#2A2A2A',   # alias for card_bg
    'input_bg':           '#1A1A1A',
    'hover_bg':           '#3A3A3A',
    'pressed_bg':         '#333333',
    'selected_bg':        BRAND_GOLD,
    
    # ── Text ──
    'text_primary':       '#E0E0E0',
    'text_secondary':     '#888888',
    'text_muted':         '#888888',
    'text_disabled':      '#555555',
    'text_accent':        BRAND_GOLD,
    'text_on_accent':     '#000000',
    
    # ── Borders ──
    'border_default':     '#333333',
    'border_focus':       BRAND_GOLD,
    'border_hover':       '#444444',
    'border_accent':      BRAND_GOLD,
    'input_border':       '#333333',
    
    # ── Dialog buttons (gold accent system) ──
    'button_bg':          '#2A2A2A',
    'button_text':        '#E0E0E0',
    'button_hover_bg':    '#3A3A3A',
    'button_hover_text':  BRAND_GOLD,
    'button_hover_border': BRAND_GOLD,
    'button_pressed_bg':  BRAND_GOLD,
    'button_pressed_text': '#000000',
    'button_border':      '#333333',
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          '#1A1A1A',
    'main_btn_text':        '#E0E0E0',
    'main_btn_border':      '#333333',
    'main_btn_hover_bg':    '#333333',
    'main_btn_hover_text':  '#E0E0E0',
    'main_btn_pressed_bg':  '#444444',
    'main_btn_pressed_text': '#000000',
    
    # ── Checkbox ──
    'checkbox_bg':            '#1A1A1A',
    'checkbox_border':        '#555555',
    'checkbox_checked_bg':    BRAND_GOLD,
    'checkbox_checked_border': BRAND_GOLD,
    'checkbox_hover_border':  BRAND_GOLD,
    
    # ── Tabs ──
    'tab_bg':             '#2A2A2A',
    'tab_selected_bg':    '#1A1A1A',
    'tab_hover_bg':       '#333333',
    'tab_border':         '#333333',
    'tab_indicator':      BRAND_GOLD,
    'tab_selected_text':  BRAND_GOLD,
    'tab_hover_text':     BRAND_GOLD,
    
    # ── Scrollbars ──
    'scrollbar_bg':            '#252525',
    'scrollbar_handle':        '#444444',
    'scrollbar_handle_hover':  '#666666',
    'scrollbar_border':        '#333333',
    
    # ── List / Table ──
    'list_bg':            '#252525',
    'list_alt_bg':        '#1A1A1A',
    'list_selected_bg':   BRAND_GOLD,
    'list_selected_text': '#000000',
    'list_hover_bg':      '#3A3A3A',
    'list_hover_text':    BRAND_GOLD,
    'list_header_bg':     '#2A2A2A',
    'list_grid':          '#333333',
    
    # ── Dialog / status ──
    'dialog_bg':          '#1A1A1A',
    'dialog_border':      '#333333',
    
    # ── Tooltip ──
    'tooltip_bg':         '#2A2A2A',
    'tooltip_border':     BRAND_GOLD,
    'tooltip_text':       '#E0E0E0',
    
    # ── Semantic status ──
    'success':            '#28a745',
    'warning':            '#ffc107',
    'error':              '#dc3545',
    'info':               BRAND_GOLD,
    
    # ── Picker-specific (unique to this app) ──
    'image_viewer_bg':       '#0A0A0A',
    'scroll_area_bg':        '#000000',
    'zoom_label_bg':         '#1A1A1A',
    'zoom_label_border':     '#333333',
    'swatch_border_width':   2,
    'swatch_border_color':   '#E0E0E0',
    'output_text_color':     BRAND_GOLD,
    'text_accent_secondary': BRAND_GOLD,
    
    # ── Gold accent hover/pressed tints (no better semantic name exists) ──
    'accent_hover':       BRAND_GOLD_HOVER,
    'accent_pressed':     BRAND_GOLD_PRESSED,
}


# ============================================================================
# LIGHT THEME COLORS
# ============================================================================

LIGHT_THEME_COLORS: Final[dict[str, str | int]] = {
    'name': 'Light',
    
    # ── Base surfaces ──
    'window_bg':          '#F5F5F5',
    'panel_bg':           '#F5F5F5',
    'card_bg':            '#FFFFFF',
    'bg_secondary':       '#FFFFFF',
    'input_bg':           '#FFFFFF',
    'hover_bg':           '#EEEEEE',
    'pressed_bg':         '#E0E0E0',
    'selected_bg':        BRAND_GOLD_DARK,
    
    # ── Text ──
    'text_primary':       '#000000',
    'text_secondary':     '#666666',
    'text_muted':         '#666666',
    'text_disabled':      '#AAAAAA',
    'text_accent':        BRAND_GOLD_DARK,
    'text_on_accent':     '#FFFFFF',
    
    # ── Borders ──
    'border_default':     '#CCCCCC',
    'border_focus':       BRAND_GOLD_DARK,
    'border_hover':       '#AAAAAA',
    'border_accent':      BRAND_GOLD_DARK,
    'input_border':       '#CCCCCC',
    
    # ── Dialog buttons (gold accent system) ──
    'button_bg':          '#FFFFFF',
    'button_text':        '#000000',
    'button_hover_bg':    '#EEEEEE',
    'button_hover_text':  BRAND_GOLD_DARK,
    'button_hover_border': BRAND_GOLD_DARK,
    'button_pressed_bg':  BRAND_GOLD_DARK,
    'button_pressed_text': '#FFFFFF',
    'button_border':      '#CCCCCC',
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          '#FFFFFF',
    'main_btn_text':        '#000000',
    'main_btn_border':      '#CCCCCC',
    'main_btn_hover_bg':    '#333333',
    'main_btn_hover_text':  '#000000',
    'main_btn_pressed_bg':  '#444444',
    'main_btn_pressed_text': '#FFFFFF',
    
    # ── Checkbox ──
    'checkbox_bg':            '#FFFFFF',
    'checkbox_border':        '#AAAAAA',
    'checkbox_checked_bg':    BRAND_GOLD_DARK,
    'checkbox_checked_border': BRAND_GOLD_DARK,
    'checkbox_hover_border':  BRAND_GOLD_DARK,
    
    # ── Tabs ──
    'tab_bg':             '#E0E0E0',
    'tab_selected_bg':    '#FFFFFF',
    'tab_hover_bg':       '#D0D0D0',
    'tab_border':         '#CCCCCC',
    'tab_indicator':      BRAND_GOLD_DARK,
    'tab_selected_text':  BRAND_GOLD_DARK,
    'tab_hover_text':     BRAND_GOLD_DARK,
    
    # ── Scrollbars ──
    'scrollbar_bg':            '#E0E0E0',
    'scrollbar_handle':        '#AAAAAA',
    'scrollbar_handle_hover':  '#888888',
    'scrollbar_border':        '#CCCCCC',
    
    # ── List / Table ──
    'list_bg':            '#FFFFFF',
    'list_alt_bg':        '#F8F8F8',
    'list_selected_bg':   BRAND_GOLD_DARK,
    'list_selected_text': '#FFFFFF',
    'list_hover_bg':      '#EEEEEE',
    'list_hover_text':    BRAND_GOLD_DARK,
    'list_header_bg':     '#F0F0F0',
    'list_grid':          '#DDDDDD',
    
    # ── Dialog / status ──
    'dialog_bg':          '#F5F5F5',
    'dialog_border':      '#CCCCCC',
    
    # ── Tooltip ──
    'tooltip_bg':         '#FFFFFF',
    'tooltip_border':     BRAND_GOLD_DARK,
    'tooltip_text':       '#000000',
    
    # ── Semantic status ──
    'success':            '#28a745',
    'warning':            '#ffc107',
    'error':              '#dc3545',
    'info':               BRAND_GOLD_DARK,
    
    # ── Picker-specific ──
    'image_viewer_bg':       '#E8E8E8',
    'scroll_area_bg':        '#FFFFFF',
    'zoom_label_bg':         '#FFFFFF',
    'zoom_label_border':     '#000000',
    'swatch_border_width':   2,
    'swatch_border_color':   '#000000',
    'output_text_color':     BRAND_GOLD_DARK,
    'text_accent_secondary': BRAND_GOLD_DARK,
    
    # ── Gold accent hover/pressed tints (no better semantic name exists) ──
    'accent_hover':       BRAND_GOLD_DARK_HOVER,
    'accent_pressed':     BRAND_GOLD_DARK_PRESSED,
}


# ============================================================================
# IMAGE MODE COLORS (Dark theme with overlay transparency)
# ============================================================================

# Image mode shares dark palette for most keys, with a few picker-specific
# overrides for the transparent overlay look.
IMAGE_MODE_COLORS: Final[dict[str, str | int]] = {
    **DARK_THEME_COLORS,
    'name': 'Image',
    # ── Picker-specific overrides for image mode ──
    'window_bg':          '#ED000000',
    'image_viewer_bg':    '#ED0A0A0A',
    'scroll_area_bg':     '#ED000000',
    'zoom_label_bg':      '#ED1A1A1A',
    'checkbox_bg':        'rgba(0, 0, 0, 100)',
    # ── Scrollbar overrides — translucent grays (no brand gold) ──
    'scrollbar_bg':            'rgba(51, 51, 51, 100)',
    'scrollbar_handle':        'rgba(80, 80, 80, 150)',
    'scrollbar_handle_hover':  'rgba(100, 100, 100, 200)',
    'scrollbar_border':        'transparent',
}


# ============================================================================
# STANDALONE COLOR CONSTANTS (Fixed — NOT theme-aware)
# ============================================================================
# These colors are intentionally fixed across all themes. Separated from
# the theme dicts so a developer immediately knows:
# "this color is deliberately hardcoded — do not try to theme it."

# ── WCAG Contrast demo swatches ──
# These represent the actual black/white reference pair the user is testing
# contrast against. They must stay black and white regardless of the active
# theme or the demo loses its meaning.
CONTRAST_DEMO_BLACK_BG: Final[str] = "#000000"
CONTRAST_DEMO_WHITE_BG: Final[str] = "#FFFFFF"
CONTRAST_DEMO_BLACK_FG: Final[str] = "#000000"
CONTRAST_DEMO_WHITE_FG: Final[str] = "#FFFFFF"

CONTRAST_ON_LIGHT: Final[str] = "#000000"
"""Black text for use on light/bright backgrounds (e.g. color swatches)"""

CONTRAST_ON_DARK: Final[str] = "#FFFFFF"
"""White text for use on dark/dim backgrounds (e.g. color swatches)"""

SWATCH_BORDER_ON_LIGHT: Final[str] = "#333"
"""Dark border for color swatches on light-colored surfaces"""

SWATCH_BORDER_ON_DARK: Final[str] = "#CCC"
"""Light border for color swatches on dark-colored surfaces"""

# ── Swatch preview border ──
# Neutral gray that reads well on both dark and light backgrounds.
# Color-preview widgets need a consistent subtle outline so the swatch
# is visible even when the color itself is near-white or near-black.
PREVIEW_BORDER: Final[str] = "#444444"
PREVIEW_BORDER_THIN: Final[str] = "#444"

# ── Debug overlay ──
# High-visibility terminal green on semi-transparent black. Used by the
# floating debug dimension label during development. Must be readable on
# any window contents regardless of theme.
DEBUG_TEXT: Final[str] = "#00FF00"
DEBUG_BG: Final[str] = "rgba(0, 0, 0, 200)"

# ── Status / feedback colors (universal semantic meaning) ──
STATUS_SUCCESS_BG: Final[str] = "#4caf50"
STATUS_SUCCESS_FG: Final[str] = "#FFFFFF"
STATUS_ERROR_BG:   Final[str] = "#f44336"
STATUS_ERROR_FG:   Final[str] = "#FFFFFF"
STATUS_ACTIVE_COLOR: Final[str] = "#4CAF50"


# ── Semi-transparent black overlays (fixed visual effects) ──
# Alpha-channel overlays used to dim UI surfaces in specific contexts.
# The alpha values are intentional and theme-independent — they create
# consistent dim levels regardless of what's beneath them.
# Stored as RGBA tuples so callers can do `QColor(*OVERLAY_BLACK_MEDIUM)`
# or `QColorCache.get(OVERLAY_BLACK_MEDIUM)` without any string parsing.
OVERLAY_BLACK_LIGHT:  Final[tuple[int, int, int, int]] = (0, 0, 0, 50)
"""Light dim overlay (alpha 50/255) — magnifier outer-area shading."""

OVERLAY_BLACK_MEDIUM: Final[tuple[int, int, int, int]] = (0, 0, 0, 75)
"""Medium dim overlay (alpha 75/255) — transparent scroll widget background."""

OVERLAY_BLACK_HEAVY:  Final[tuple[int, int, int, int]] = (0, 0, 0, 180)
"""Heavy dim overlay (alpha 180/255) — magnifier crosshair shadow."""

# ── SVG palette export (printable artifact) ──
# Fixed paper-white background and ink-black stroke for the SVG export
# format. Theme-independent because exported SVGs need to look the same
# regardless of which theme was active at export time.
SVG_EXPORT_BG:     Final[str] = "#FFFFFF"
"""Background fill for SVG palette export (paper white)."""

SVG_EXPORT_STROKE: Final[str] = "#000000"
"""Stroke color for SVG palette export swatch borders (ink black)."""

# ── Missing-data placeholder ──
# Default value used when a color history dict entry is missing its 'hex'
# field. Black is a deliberately wrong-looking sentinel so missing data is
# visually obvious in the UI rather than silently rendering as a real color.
MISSING_HEX_PLACEHOLDER: Final[str] = "#000000"
"""Placeholder hex when a color entry dict lacks its 'hex' key."""


# ============================================================================
# THEME ENTRY FUNCTION
# ============================================================================

def get_theme_colors(theme_name: str = 'dark') -> dict[str, str | int]:
    """
    Get the color palette for the specified theme.
    
    Args:
        theme_name: 'dark', 'light', or 'image'
    
    Returns:
        Dictionary of color definitions for that theme
    """
    match theme_name:
        case 'light':
            return LIGHT_THEME_COLORS
        case 'image':
            return IMAGE_MODE_COLORS
        case _:
            return DARK_THEME_COLORS


# ============================================================================
# THEME MANAGER
# ============================================================================

class ThemeManager:
    """
    Manages application theme state (Dark / Light / Image) at runtime.
    
    Theme color dicts are module-level constants in this file. This class
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
        border      = theme.get('scrollbar_border', theme.get('border_default', '#333333'))
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

# Image mode scrollbar is special — uses custom transparent overlay look
# (not built from theme dict because these rgba values are image-mode specific)
ThemeManager.SCROLLBAR_IMAGE = """
    QScrollBar:vertical {
        background-color: rgba(51, 51, 51, 100);
        width: 15px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: rgba(80, 80, 80, 150);
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: rgba(100, 100, 100, 200);
    }
    QScrollBar::sub-page:vertical {
        background-color: transparent;
    }
    QScrollBar::add-page:vertical {
        background-color: transparent;
    }
    QScrollBar:horizontal {
        background-color: rgba(51, 51, 51, 100);
        height: 15px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: rgba(80, 80, 80, 150);
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: rgba(100, 100, 100, 200);
    }
    QScrollBar::sub-page:horizontal {
        background-color: transparent;
    }
    QScrollBar::add-page:horizontal {
        background-color: transparent;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        border: none;
        background: none;
    }
"""


# ============================================================================
# PUBLIC API
# ============================================================================

__all__: list[str] = [
    # Brand colors
    'BRAND_GOLD',
    'BRAND_GOLD_DARK',
    'BRAND_GOLD_RGB',
    'BRAND_GOLD_DARK_RGB',
    'BRAND_GOLD_HOVER',
    'BRAND_GOLD_PRESSED',
    'BRAND_GOLD_DARK_HOVER',
    'BRAND_GOLD_DARK_PRESSED',
    # Theme dicts + entry function
    'DARK_THEME_COLORS',
    'LIGHT_THEME_COLORS',
    'IMAGE_MODE_COLORS',
    'get_theme_colors',
    # Standalone constants
    'CONTRAST_ON_LIGHT',
    'CONTRAST_ON_DARK',
    'CONTRAST_DEMO_BLACK_BG',
    'CONTRAST_DEMO_WHITE_BG',
    'CONTRAST_DEMO_BLACK_FG',
    'CONTRAST_DEMO_WHITE_FG',
    'SWATCH_BORDER_ON_LIGHT',
    'SWATCH_BORDER_ON_DARK',
    'PREVIEW_BORDER',
    'PREVIEW_BORDER_THIN',
    'DEBUG_TEXT',
    'DEBUG_BG',
    'STATUS_SUCCESS_BG',
    'STATUS_SUCCESS_FG',
    'STATUS_ERROR_BG',
    'STATUS_ERROR_FG',
    'STATUS_ACTIVE_COLOR',
    'OVERLAY_BLACK_LIGHT',
    'OVERLAY_BLACK_MEDIUM',
    'OVERLAY_BLACK_HEAVY',
    'SVG_EXPORT_BG',
    'SVG_EXPORT_STROKE',
    'MISSING_HEX_PLACEHOLDER',
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