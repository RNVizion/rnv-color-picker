"""
Application configuration and theme management for RNV Color Picker.

This module is the SINGLE SOURCE OF TRUTH for all colors in the application.

Structure:
- Brand colors (BRAND_GOLD, BRAND_DARK_GOLD) — referenced everywhere, never duplicated
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

# Registered values are mirrored from RNVizion/rnv-brand (engine/brand.py).
# Everything else is COMPUTED from them, never written down, so a derivative
# cannot drift away from the colour it was derived from.
#
# This file previously held six hand-written variants. One of them, the light
# hover #c4a458, was a tint of a value that had since been retired -- orphaned,
# with nothing to flag it. That is the failure derivation prevents.


def _to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Split a six-digit hex colour into an (r, g, b) tuple."""
    h = hex_color.lstrip('#')
    if len(h) != 6:
        raise ValueError(f"expected a six-digit hex colour, got {hex_color!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lighten(hex_color: str, step: int) -> str:
    """Shift every channel by the same number of 8-bit steps.

    A uniform per-channel shift holds hue exactly, which is what keeps a
    derived gold recognisably the same gold. It is also the method the light
    palettes already used before the alignment. Negative darkens.
    """
    return '#' + ''.join(
        f'{max(0, min(255, c + step)):02x}' for c in _to_rgb(hex_color)
    )


BRAND_GOLD: Final[str] = "#d2bc93"
"""Primary brand gold -- dark-mode accents, highlights, tooltips.

Registered brand value. Unchanged by the alignment.
"""

BRAND_DARK_GOLD: Final[str] = "#8c7337"
"""Brand dark gold -- light-mode FILLS, borders and pressed states.

Registered brand value. It replaced the app-local #b19145, which did one
job of six: as text on white it measured 2.9976 against a 4.5 floor, and
as a border 2.9976 against 3.0 -- short by 0.0024, which is why a contrast
tool displaying "3.00" never surfaced it.

Carries white text at 4.5429 and black at 4.6226. Black stays the ruled
pairing and the better number.
"""

BRAND_DARK_GOLD_DEEP: Final[str] = lighten(BRAND_DARK_GOLD, -14)  # -> #7e6529
"""Derived. The one light-mode derivative, serving two roles.

BRAND_DARK_GOLD clears 4.5:1 as TEXT against pure white and nothing else
(#f5f5f5 4.1670, #eeeeee 3.9156). And a hover background carrying white
text needs a gold dark enough for white. Both roles want the same thing,
so they share one value rather than each getting its own.

    white on it ............ 5.5547
    as text on #f5f5f5 ..... 5.0949
    as text on #eeeeee ..... 4.7875
    as text on #e8e8e8 ..... 4.5334   <- binding

-14 is the smallest uniform step that clears all four; -13 gives 4.4675
on #e8e8e8 and fails. Hue is unchanged.

NEVER use as a fill under black text -- black on it is 3.7806. Below
#e8e8e8 gold does not carry text at all; that is a ruling, not a gap.
"""

BRAND_DARK_GOLD_HOVER: Final[str] = BRAND_DARK_GOLD_DEEP
"""Light-mode hover. Hover moves AWAY from its ground.

A dark ground takes a lighter hover; a light ground takes a deeper one.
The retired #c4a458 went lighter on a light ground -- toward it -- which
is why white measured 2.3868 on it. Stated as "a lighter tint for hover
feedback", the old rule was wrong half the time.
"""

BRAND_DARK_GOLD_PRESSED: Final[str] = BRAND_DARK_GOLD
"""Light-mode pressed. It IS the accent.

Two reasons, and either alone would be enough. The brand runs two golds
per mode and light spends its second on BRAND_DARK_GOLD_DEEP. And
darkening past BRAND_DARK_GOLD drops black-on-gold under the floor, which
would force white text and break the register's text-on-gold rule.
"""

BRAND_GOLD_HOVER: Final[str] = lighten(BRAND_GOLD, 13)      # -> #dfc9a0
"""Dark-mode hover. Derived, replacing the hand-written #dcc9a3.

The old hand-written value's deltas were +10/+13/+16 -- non-uniform, so it had
drifted off BRAND_GOLD's hue. A uniform step snaps it back.
"""

BRAND_GOLD_PRESSED: Final[str] = BRAND_GOLD
"""Dark-mode pressed. It IS the accent, mirroring light mode exactly.

The brand runs TWO golds per mode -- the registered one and one derived
from it -- and no more. Dark spends its second on hover, so pressed
returns to the accent rather than claiming a third.

The interaction still reads: rest sits at the accent, hover lifts away
from the dark ground, pressed drops back to rest. That is the same shape
light uses, where hover deepens away from the light ground and pressed
returns. The hand-written #b7a480 it replaces was a third gold serving
one key.
"""

BRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)
"""Derived. A hardcoded tuple is invisible to every hex-based search, so
it survives sweeps that catch every other reference to the colour."""

BRAND_DARK_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_DARK_GOLD)
"""Derived, same reason. This one held (177, 145, 69) -- the retired gold,
in the one form no sweep would have found."""


# ============================================================================
# DARK THEME COLORS
# ============================================================================

DARK_THEME_COLORS: Final[dict[str, str | int]] = {
    # Error message text. Theme-aware because no single red clears both
    # grounds: the register's #e56b77 is a dark-theme value and measures
    # 2.8745 on the light panel.
    'status_error_text': '#e56b77',
    'name': 'Dark',
    
    # ── Base surfaces ──
    'window_bg':          '#000000',
    'panel_bg':           '#1a1a1a',
    'card_bg':            '#2a2a2a',
    'bg_secondary':       '#2a2a2a',   # alias for card_bg
    'input_bg':           '#1a1a1a',
    'hover_bg':           '#3a3a3a',
    'pressed_bg':         '#333333',
    'selected_bg':        BRAND_GOLD,
    
    # ── Text ──
    'text_primary':       '#e0e0e0',
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
    'button_bg':          '#2a2a2a',
    'button_text':        '#e0e0e0',
    'button_hover_bg':    '#3a3a3a',
    'button_hover_text':  BRAND_GOLD,
    'button_hover_border': BRAND_GOLD,
    'button_pressed_bg':  BRAND_GOLD,
    'button_pressed_text': '#000000',
    'button_border':      '#333333',
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          '#1a1a1a',
    'main_btn_text':        '#e0e0e0',
    'main_btn_border':      '#333333',
    'main_btn_hover_bg':    '#333333',
    'main_btn_hover_text':  '#e0e0e0',
    'main_btn_pressed_bg':  '#444444',
    'main_btn_pressed_text': '#000000',
    
    # ── Checkbox ──
    'checkbox_bg':            '#1a1a1a',
    'checkbox_border':        '#555555',
    'checkbox_checked_bg':    BRAND_GOLD,
    'checkbox_checked_border': BRAND_GOLD,
    'checkbox_hover_border':  BRAND_GOLD,
    
    # ── Tabs ──
    'tab_bg':             '#2a2a2a',
    'tab_selected_bg':    '#1a1a1a',
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
    'list_alt_bg':        '#1a1a1a',
    'list_selected_bg':   BRAND_GOLD,
    'list_selected_text': '#000000',
    'list_hover_bg':      '#3a3a3a',
    'list_hover_text':    BRAND_GOLD,
    'list_header_bg':     '#2a2a2a',
    'list_grid':          '#333333',
    
    # ── Dialog / status ──
    'dialog_bg':          '#1a1a1a',
    'dialog_border':      '#333333',
    
    # ── Tooltip ──
    'tooltip_bg':         '#2a2a2a',
    'tooltip_border':     BRAND_GOLD,
    'tooltip_text':       '#e0e0e0',
    
    # ── Semantic status ──
    'success':            '#28a745',
    'warning':            '#ffc107',
    'error':              '#dc3545',
    'info':               BRAND_GOLD,
    
    # ── Picker-specific (unique to this app) ──
    'image_viewer_bg':       '#0a0a0a',
    'scroll_area_bg':        '#000000',
    'zoom_label_bg':         '#1a1a1a',
    'zoom_label_border':     '#333333',
    'swatch_border_width':   2,
    'swatch_border_color':   '#e0e0e0',
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
    # Error message text. Theme-aware because no single red clears both
    # grounds: the register's #e56b77 is a dark-theme value and measures
    # 2.8745 on the light panel.
    'status_error_text': '#dc3545',
    'name': 'Light',
    
    # ── Base surfaces ──
    'window_bg':          '#f5f5f5',
    'panel_bg':           '#f5f5f5',
    'card_bg':            '#ffffff',
    'bg_secondary':       '#ffffff',
    'input_bg':           '#ffffff',
    'hover_bg':           '#eeeeee',
    'pressed_bg':         '#e0e0e0',
    'selected_bg':        BRAND_DARK_GOLD,
    
    # ── Text ──
    'text_primary':       '#000000',
    'text_secondary':     '#666666',
    'text_muted':         '#666666',
    'text_disabled':      '#aaaaaa',
    'text_accent':        BRAND_DARK_GOLD_DEEP,
    'text_on_accent':     '#ffffff',
    
    # ── Borders ──
    'border_default':     '#cccccc',
    'border_focus':       BRAND_DARK_GOLD,
    'border_hover':       '#aaaaaa',
    'border_accent':      BRAND_DARK_GOLD,
    'input_border':       '#cccccc',
    
    # ── Dialog buttons (gold accent system) ──
    'button_bg':          '#ffffff',
    'button_text':        '#000000',
    'button_hover_bg':    '#eeeeee',
    'button_hover_text':  BRAND_DARK_GOLD_DEEP,
    'button_hover_border': BRAND_DARK_GOLD,
    'button_pressed_bg':  BRAND_DARK_GOLD,
    'button_pressed_text': '#ffffff',
    'button_border':      '#cccccc',
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          '#ffffff',
    'main_btn_text':        '#000000',
    'main_btn_border':      '#cccccc',
    'main_btn_hover_bg':    '#333333',
    'main_btn_hover_text':  '#000000',
    'main_btn_pressed_bg':  '#444444',
    'main_btn_pressed_text': '#ffffff',
    
    # ── Checkbox ──
    'checkbox_bg':            '#ffffff',
    'checkbox_border':        '#aaaaaa',
    'checkbox_checked_bg':    BRAND_DARK_GOLD,
    'checkbox_checked_border': BRAND_DARK_GOLD,
    'checkbox_hover_border':  BRAND_DARK_GOLD,
    
    # ── Tabs ──
    'tab_bg':             '#e0e0e0',
    'tab_selected_bg':    '#ffffff',
    'tab_hover_bg':       '#eeeeee',
    'tab_border':         '#cccccc',
    'tab_indicator':      BRAND_DARK_GOLD,
    'tab_selected_text':  BRAND_DARK_GOLD_DEEP,
    'tab_hover_text':     BRAND_DARK_GOLD_DEEP,
    
    # ── Scrollbars ──
    'scrollbar_bg':            '#e0e0e0',
    'scrollbar_handle':        '#aaaaaa',
    'scrollbar_handle_hover':  '#888888',
    'scrollbar_border':        '#cccccc',
    
    # ── List / Table ──
    'list_bg':            '#ffffff',
    'list_alt_bg':        '#f8f8f8',
    'list_selected_bg':   BRAND_DARK_GOLD,
    'list_selected_text': '#ffffff',
    'list_hover_bg':      '#eeeeee',
    'list_hover_text':    BRAND_DARK_GOLD_DEEP,
    'list_header_bg':     '#f0f0f0',
    'list_grid':          '#dddddd',
    
    # ── Dialog / status ──
    'dialog_bg':          '#f5f5f5',
    'dialog_border':      '#cccccc',
    
    # ── Tooltip ──
    'tooltip_bg':         '#ffffff',
    'tooltip_border':     BRAND_DARK_GOLD,
    'tooltip_text':       '#000000',
    
    # ── Semantic status ──
    'success':            '#28a745',
    'warning':            '#ffc107',
    'error':              '#dc3545',
    'info':               BRAND_DARK_GOLD,
    
    # ── Picker-specific ──
    'image_viewer_bg':       '#e8e8e8',
    'scroll_area_bg':        '#ffffff',
    'zoom_label_bg':         '#ffffff',
    'zoom_label_border':     '#000000',
    'swatch_border_width':   2,
    'swatch_border_color':   '#000000',
    'output_text_color':     BRAND_DARK_GOLD,
    'text_accent_secondary': BRAND_DARK_GOLD,
    
    # ── Gold accent hover/pressed tints (no better semantic name exists) ──
    'accent_hover':       BRAND_DARK_GOLD_HOVER,
    'accent_pressed':     BRAND_DARK_GOLD_PRESSED,
}


# ============================================================================
# IMAGE MODE COLORS (Dark theme with overlay transparency)
# ============================================================================

# Image mode shares dark palette for most keys, with a few picker-specific
# overrides for the transparent overlay look.
IMAGE_MODE_COLORS: Final[dict[str, str | int]] = {
    # Error message text. Theme-aware because no single red clears both
    # grounds: the register's #e56b77 is a dark-theme value and measures
    # 2.8745 on the light panel.
    'status_error_text': '#e56b77',
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
CONTRAST_DEMO_WHITE_BG: Final[str] = "#ffffff"
CONTRAST_DEMO_BLACK_FG: Final[str] = "#000000"
CONTRAST_DEMO_WHITE_FG: Final[str] = "#ffffff"

CONTRAST_ON_LIGHT: Final[str] = "#000000"
"""Black text for use on light/bright backgrounds (e.g. color swatches)"""

CONTRAST_ON_DARK: Final[str] = "#ffffff"
"""White text for use on dark/dim backgrounds (e.g. color swatches)"""

SWATCH_BORDER_ON_LIGHT: Final[str] = "#333"
"""Dark border for color swatches on light-colored surfaces"""

SWATCH_BORDER_ON_DARK: Final[str] = "#ccc"
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
DEBUG_TEXT: Final[str] = "#00ff00"
DEBUG_BG: Final[str] = "rgba(0, 0, 0, 200)"

# ── Status / feedback colors (universal semantic meaning) ──
STATUS_SUCCESS_BG: Final[str] = "#28a745"
STATUS_SUCCESS_FG: Final[str] = "#000000"
STATUS_ERROR_BG:   Final[str] = "#dc3545"
STATUS_ERROR_FG:   Final[str] = "#000000"
STATUS_ACTIVE_COLOR: Final[str] = "#28a745"


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
SVG_EXPORT_BG:     Final[str] = "#ffffff"
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
    'BRAND_DARK_GOLD',
    'BRAND_GOLD_RGB',
    'BRAND_DARK_GOLD_RGB',
    'BRAND_GOLD_HOVER',
    'BRAND_GOLD_PRESSED',
    'BRAND_DARK_GOLD_HOVER',
    'BRAND_DARK_GOLD_PRESSED',
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