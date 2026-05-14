"""
Caching utilities for RNV Color Picker.

Provides:
- LRU caches for color conversions
- Stylesheet caching
- Font caching
- QColor object pooling

Python 3.13 optimized.
"""

import functools
import colorsys
from typing import Callable
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication

from utils.logger import Logger
from utils.config import (
    BRAND_GOLD, BRAND_GOLD_DARK,
    BRAND_GOLD_HOVER, BRAND_GOLD_PRESSED,
    BRAND_GOLD_DARK_HOVER, BRAND_GOLD_DARK_PRESSED,
    SWATCH_BORDER_ON_LIGHT,
    CONTRAST_ON_LIGHT, CONTRAST_ON_DARK,
    STATUS_ERROR_BG,
)

logger = Logger("Cache")


class ColorCache:
    """
    High-performance color conversion cache.
    
    Uses LRU caching to avoid repeated conversions for the same colors.
    Typical hit rates > 90% for palette operations.
    """
    
    @staticmethod
    @functools.lru_cache(maxsize=2048)
    def rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """
        Convert RGB to HSL with caching.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            HSL tuple (H: 0-360, S: 0-100, L: 0-100)
        """
        r, g, b = (x / 255.0 for x in rgb)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return (int(h * 360), int(s * 100), int(l * 100))
    
    @staticmethod
    @functools.lru_cache(maxsize=2048)
    def rgb_to_hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
        """
        Convert RGB to HSV with caching.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            HSV tuple (H: 0-1, S: 0-1, V: 0-1)
        """
        r, g, b = (x / 255.0 for x in rgb)
        return colorsys.rgb_to_hsv(r, g, b)
    
    @staticmethod
    @functools.lru_cache(maxsize=2048)
    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        """
        Convert RGB to hex string with caching.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            Hex string like '#ff0000'
        """
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def get_text_color_for_background(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """
        Get optimal text color (black or white) for a background color.
        
        Uses perceived brightness formula for accessibility.
        
        Args:
            rgb: Background RGB tuple
            
        Returns:
            (0,0,0) for dark text or (255,255,255) for light text
        """
        r, g, b = rgb
        # Perceived brightness formula (ITU-R BT.601)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return (0, 0, 0) if brightness > 128 else (255, 255, 255)
    
    @staticmethod
    @functools.lru_cache(maxsize=512)
    def hilbert_index(rgb: tuple[int, int, int], order: int = 8) -> int:
        """
        Calculate Hilbert curve index for RGB color with caching.
        
        Args:
            rgb: RGB tuple (0-255)
            order: Hilbert curve order
            
        Returns:
            Integer index along Hilbert curve
        """
        def interleave(xi: int, yi: int, zi: int) -> int:
            result = 0
            for i in range(order):
                result |= ((xi & (1 << i)) << (2 * i)) | \
                         ((yi & (1 << i)) << (2 * i + 1)) | \
                         ((zi & (1 << i)) << (2 * i + 2))
            return result
        
        max_val = (1 << order) - 1
        r, g, b = rgb
        xi = int((r / 255.0) * max_val)
        yi = int((g / 255.0) * max_val)
        zi = int((b / 255.0) * max_val)
        
        return interleave(xi, yi, zi)
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all caches. Call when memory pressure is high."""
        cls.rgb_to_hsl.cache_clear()
        cls.rgb_to_hsv.cache_clear()
        cls.rgb_to_hex.cache_clear()
        cls.get_text_color_for_background.cache_clear()
        cls.hilbert_index.cache_clear()
    
    @classmethod
    def get_stats(cls) -> dict[str, dict]:
        """Get cache statistics for monitoring."""
        return {
            'rgb_to_hsl': cls.rgb_to_hsl.cache_info()._asdict(),
            'rgb_to_hsv': cls.rgb_to_hsv.cache_info()._asdict(),
            'rgb_to_hex': cls.rgb_to_hex.cache_info()._asdict(),
            'text_color': cls.get_text_color_for_background.cache_info()._asdict(),
            'hilbert': cls.hilbert_index.cache_info()._asdict(),
        }


class QColorCache:
    """
    Cache for QColor objects to avoid repeated construction.
    
    QColor construction from strings is expensive - this cache
    provides O(1) lookup for commonly used colors.
    """
    
    _cache: dict[str | tuple, QColor] = {}
    
    # Pre-defined common colors
    LOCK_BORDER = None  # Initialized on first use
    BLACK = None
    WHITE = None
    TRANSPARENT = None
    
    @classmethod
    def _init_constants(cls) -> None:
        """Initialize constant colors on first use."""
        if cls.LOCK_BORDER is None:
            cls.LOCK_BORDER = QColor(BRAND_GOLD)
            cls.BLACK = QColor(0, 0, 0)
            cls.WHITE = QColor(255, 255, 255)
            cls.TRANSPARENT = QColor(0, 0, 0, 0)
    
    @classmethod
    def get(cls, color: str | tuple[int, int, int] | tuple[int, int, int, int]) -> QColor:
        """
        Get a QColor from cache or create and cache it.
        
        Args:
            color: Hex string '#rrggbb' or RGB/RGBA tuple
            
        Returns:
            Cached QColor object
        """
        cls._init_constants()
        
        # Convert tuple to hashable key
        key = color if isinstance(color, str) else tuple(color)
        
        if key not in cls._cache:
            if isinstance(color, str):
                cls._cache[key] = QColor(color)
            elif len(color) == 3:
                cls._cache[key] = QColor(color[0], color[1], color[2])
            else:
                cls._cache[key] = QColor(color[0], color[1], color[2], color[3])
        
        return cls._cache[key]
    
    @classmethod
    def get_rgb(cls, r: int, g: int, b: int, a: int = 255) -> QColor:
        """Get QColor from RGB values."""
        return cls.get((r, g, b, a) if a != 255 else (r, g, b))
    
    @classmethod
    def clear(cls) -> None:
        """Clear the cache."""
        cls._cache.clear()
    
    @classmethod
    def size(cls) -> int:
        """Get current cache size."""
        return len(cls._cache)


class StylesheetCache:
    """
    Cache for generated stylesheets.
    
    Avoids repeated string formatting for theme-based stylesheets.
    """
    
    _cache: dict[tuple, str] = {}
    
    @classmethod
    def get_menu_stylesheet(
        cls,
        theme_name: str,
        is_image_mode: bool,
        theme: dict
    ) -> str:
        """
        Get cached menu stylesheet.
        
        Args:
            theme_name: Current theme name
            is_image_mode: Whether in image mode
            theme: Theme dictionary
            
        Returns:
            CSS stylesheet string
        """
        key = (theme_name, is_image_mode, 'menu')
        
        if key not in cls._cache:
            if is_image_mode:
                cls._cache[key] = f"""
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
                    QMenu::item:disabled {{
                        color: {theme['text_disabled']};
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background-color: {theme['border_default']};
                        margin: 4px 6px;
                    }}
                """
            else:
                cls._cache[key] = f"""
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
                    QMenu::item:disabled {{
                        color: {theme['text_disabled']};
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background-color: {theme['border_default']};
                        margin: 4px 6px;
                    }}
                """
        
        return cls._cache[key]
    
    @classmethod
    def get_checkbox_stylesheet(cls, theme_name: str, theme: dict) -> str:
        """Get cached checkbox stylesheet."""
        key = (theme_name, 'checkbox')
        
        if key not in cls._cache:
            cls._cache[key] = f"""
                QCheckBox {{
                    background-color: {theme['checkbox_bg']};
                    padding: 5px;
                    border: 1px solid {theme['checkbox_border']};
                    border-radius: 3px;
                    color: {theme['text_primary']};
                }}
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_scrollbar_stylesheet(cls, theme_name: str, theme: dict) -> str:
        """Get cached scrollbar stylesheet for themed scroll areas."""
        key = (theme_name, 'scrollbar')
        
        if key not in cls._cache:
            cls._cache[key] = f"""
                QScrollBar:vertical {{
                    background: {theme['scrollbar_bg']};
                    width: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {theme['scrollbar_handle']};
                    min-height: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {theme['scrollbar_handle_hover']};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar:horizontal {{
                    background: {theme['scrollbar_bg']};
                    height: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:horizontal {{
                    background: {theme['scrollbar_handle']};
                    min-width: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: {theme['scrollbar_handle_hover']};
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0px;
                }}
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_button_frame_stylesheet(
        cls, 
        theme_name: str, 
        theme: dict, 
        is_image_mode: bool
    ) -> str:
        """Get cached button frame stylesheet."""
        key = (theme_name, is_image_mode, 'button_frame')
        
        if key not in cls._cache:
            if is_image_mode:
                cls._cache[key] = """
                    QFrame {
                        background-color: rgba(0, 0, 0, 100);
                        border-radius: 8px;
                    }
                """
            else:
                cls._cache[key] = f"""
                    QFrame {{
                        background-color: {theme['window_bg']};
                        border-radius: 8px;
                    }}
                """
        
        return cls._cache[key]
    
    @classmethod
    def get_scroll_area_stylesheet(
        cls,
        theme_name: str,
        theme: dict,
        is_image_mode: bool
    ) -> str:
        """Get cached scroll area stylesheet."""
        key = (theme_name, is_image_mode, 'scroll_area')
        
        if key not in cls._cache:
            scrollbar_css = cls.get_scrollbar_stylesheet(theme_name, theme)
            
            if is_image_mode:
                cls._cache[key] = f"""
                    QScrollArea {{
                        background-color: transparent;
                        border: none;
                    }}
                    {scrollbar_css}
                """
            else:
                cls._cache[key] = f"""
                    QScrollArea {{
                        background-color: {theme['scroll_area_bg']};
                        border: 1px solid {theme['border_default']};
                        border-radius: 8px;
                    }}
                    {scrollbar_css}
                """
        
        return cls._cache[key]
    
    @classmethod
    def get_theme_button_stylesheet(cls, theme_name: str, theme: dict) -> str:
        """Get cached theme toggle button stylesheet (main window button — inverse system, no gold)."""
        key = (theme_name, 'theme_button')
        
        if key not in cls._cache:
            cls._cache[key] = f"""
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
        
        return cls._cache[key]
    
    @classmethod
    def get_zoom_label_stylesheet(cls, theme_name: str, theme: dict) -> str:
        """Get cached zoom label stylesheet."""
        key = (theme_name, 'zoom_label')
        
        if key not in cls._cache:
            cls._cache[key] = f"""
                QLabel {{
                    color: {theme['text_primary']};
                    font-size: 11px;
                    background-color: {theme['zoom_label_bg']};
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_close_button_stylesheet(cls, is_dark: bool = True) -> str:
        """Get cached close/OK button stylesheet (gold themed, theme-aware)."""
        key = ('static', 'close_button', is_dark)
        
        if key not in cls._cache:
            if is_dark:
                bg      = BRAND_GOLD
                fg      = CONTRAST_ON_LIGHT   # black text on bright gold
                hover   = BRAND_GOLD_HOVER
                pressed = BRAND_GOLD_PRESSED
            else:
                bg      = BRAND_GOLD_DARK
                fg      = CONTRAST_ON_DARK    # white text on dark gold
                hover   = BRAND_GOLD_DARK_HOVER
                pressed = BRAND_GOLD_DARK_PRESSED
            cls._cache[key] = f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: none;
                    padding: 8px 24px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QPushButton:pressed {{
                    background-color: {pressed};
                }}
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_header_stylesheet(cls, size: int = 14, bold: bool = True) -> str:
        """Get cached header label stylesheet."""
        key = ('static', 'header', size, bold)
        
        if key not in cls._cache:
            weight = "bold" if bold else "normal"
            cls._cache[key] = f"font-weight: {weight}; font-size: {size}px;"
        
        return cls._cache[key]
    
    @classmethod
    def get_description_stylesheet(cls) -> str:
        """Get cached description label stylesheet."""
        key = ('static', 'description')
        
        if key not in cls._cache:
            cls._cache[key] = "color: gray; font-size: 11px;"
        
        return cls._cache[key]
    
    @classmethod
    def get_image_button_stylesheet(cls, theme_name: str, theme: dict) -> str:
        """Get cached image button stylesheet (main window buttons — inverse system, no gold)."""
        key = (theme_name, 'image_button')
        
        if key not in cls._cache:
            cls._cache[key] = f"""
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
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_transparent_button_stylesheet(cls) -> str:
        """Get cached transparent button stylesheet for image modes."""
        key = ('static', 'transparent_button')
        
        if key not in cls._cache:
            cls._cache[key] = """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                }
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_color_preview_stylesheet(cls, hex_color: str, size: int = 60) -> str:
        """
        Get cached color preview box stylesheet.
        
        Args:
            hex_color: Hex color code (e.g., "#ff0000")
            size: Box size in pixels
            
        Returns:
            CSS stylesheet string
        """
        key = ('color_preview', hex_color, size)
        
        if key not in cls._cache:
            cls._cache[key] = f"""
                QLabel {{
                    background-color: {hex_color};
                    border: 2px solid {SWATCH_BORDER_ON_LIGHT};
                    border-radius: 8px;
                    min-width: {size}px;
                    min-height: {size}px;
                    max-width: {size}px;
                    max-height: {size}px;
                }}
            """
        
        return cls._cache[key]
    
    @classmethod
    def get_subheader_stylesheet(cls, color: str = BRAND_GOLD) -> str:
        """Get cached sub-header stylesheet."""
        key = ('static', 'subheader', color)
        
        if key not in cls._cache:
            cls._cache[key] = f"font-weight: bold; font-size: 13px; color: {color};"
        
        return cls._cache[key]
    
    @classmethod
    def get_monospace_stylesheet(cls, size: int = 9) -> str:
        """Get cached monospace label stylesheet."""
        key = ('static', 'monospace', size)
        
        if key not in cls._cache:
            cls._cache[key] = f"font-size: {size}px; font-family: monospace;"
        
        return cls._cache[key]
    
    @classmethod
    def get_error_stylesheet(cls) -> str:
        """Get cached error message stylesheet."""
        key = ('static', 'error')
        
        if key not in cls._cache:
            cls._cache[key] = f"color: {STATUS_ERROR_BG}; padding: 20px;"
        
        return cls._cache[key]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all cached stylesheets."""
        cls._cache.clear()


class FontCache:
    """
    Cache for QFont and PIL ImageFont objects.
    """
    
    _qfont_cache: dict[tuple, QFont] = {}
    _pil_font_cache: dict[tuple, any] = {}
    
    @classmethod
    def get_qfont(
        cls,
        family: str | None = None,
        size: int = 10,
        bold: bool = False
    ) -> QFont:
        """
        Get cached QFont.
        
        Args:
            family: Font family (None = application default)
            size: Point size
            bold: Whether bold
            
        Returns:
            Cached QFont object
        """
        if family is None:
            family = QApplication.font().family()
        
        key = (family, size, bold)
        
        if key not in cls._qfont_cache:
            font = QFont(family, size)
            if bold:
                font.setBold(True)
            cls._qfont_cache[key] = font
        
        return cls._qfont_cache[key]
    
    @classmethod
    def get_pil_font(cls, path: str, size: int):
        """
        Get cached PIL ImageFont.
        
        Args:
            path: Font file path
            size: Point size
            
        Returns:
            Cached ImageFont or None if unavailable
        """
        key = (path, size)
        
        if key not in cls._pil_font_cache:
            try:
                from PIL import ImageFont
                import os
                if os.path.exists(path):
                    cls._pil_font_cache[key] = ImageFont.truetype(path, size)
                else:
                    cls._pil_font_cache[key] = None
            except Exception:
                cls._pil_font_cache[key] = None
        
        return cls._pil_font_cache[key]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all font caches."""
        cls._qfont_cache.clear()
        cls._pil_font_cache.clear()


class ResourceCache:
    """
    Cache for file existence checks and resource paths.
    """
    
    _exists_cache: dict[str, bool] = {}
    
    @classmethod
    def exists(cls, path: str) -> bool:
        """
        Check if file exists with caching.
        
        Args:
            path: File path to check
            
        Returns:
            True if file exists
        """
        if path not in cls._exists_cache:
            import os
            cls._exists_cache[path] = os.path.exists(path)
        return cls._exists_cache[path]
    
    @classmethod
    def invalidate(cls, path: str | None = None) -> None:
        """
        Invalidate cache entry or entire cache.
        
        Args:
            path: Specific path to invalidate, or None for all
        """
        if path is None:
            cls._exists_cache.clear()
        elif path in cls._exists_cache:
            del cls._exists_cache[path]


def clear_all_caches() -> None:
    """Clear all caches. Call on low memory or theme change."""
    if logger:
        logger.debug("Clearing all caches")
    ColorCache.clear_all()
    QColorCache.clear()
    StylesheetCache.clear()
    FontCache.clear()
    ResourceCache.invalidate()
    if logger:
        logger.debug("All caches cleared")


def get_cache_stats() -> dict[str, dict]:
    """
    Get statistics for all caches.
    
    Returns:
        Dictionary with stats for each cache:
        - ColorCache: LRU cache info for each method
        - QColorCache: Pool size
        - StylesheetCache: Number of cached stylesheets
        - FontCache: Number of cached fonts
        - ResourceCache: Number of cached paths
    """
    stats = {}
    
    # ColorCache LRU stats
    color_cache_stats = {}
    for method_name in ['rgb_to_hsl', 'rgb_to_hsv', 'rgb_to_hex', 'get_text_color_for_background', 'hilbert_index']:
        try:
            method = getattr(ColorCache, method_name)
            if hasattr(method, 'cache_info'):
                info = method.cache_info()
                color_cache_stats[method_name] = {
                    'hits': info.hits,
                    'misses': info.misses,
                    'size': info.currsize,
                    'maxsize': info.maxsize,
                    'hit_rate': f"{info.hits / (info.hits + info.misses) * 100:.1f}%" if (info.hits + info.misses) > 0 else "N/A"
                }
        except AttributeError:
            pass
    stats['ColorCache'] = color_cache_stats
    
    # QColorCache stats
    stats['QColorCache'] = {
        'pool_size': len(QColorCache._cache)
    }
    
    # StylesheetCache stats
    stats['StylesheetCache'] = {
        'cached_stylesheets': len(StylesheetCache._cache)
    }
    
    # FontCache stats
    stats['FontCache'] = {
        'qfont_cache': len(FontCache._qfont_cache),
        'pil_font_cache': len(FontCache._pil_font_cache)
    }
    
    # ResourceCache stats
    stats['ResourceCache'] = {
        'cached_paths': len(ResourceCache._exists_cache)
    }
    
    return stats


def log_cache_stats() -> None:
    """Log current cache statistics."""
    stats = get_cache_stats()
    
    if logger:
        logger.info("=== Cache Statistics ===")
        
        # ColorCache
        if stats.get('ColorCache'):
            for method, info in stats['ColorCache'].items():
                logger.info(
                    f"ColorCache.{method}: "
                    f"hits={info['hits']}, misses={info['misses']}, "
                    f"size={info['size']}/{info['maxsize']}, "
                    f"hit_rate={info['hit_rate']}"
                )
        
        # Other caches
        logger.info(f"QColorCache: {stats.get('QColorCache', {})}")
        logger.info(f"StylesheetCache: {stats.get('StylesheetCache', {})}")
        logger.info(f"FontCache: {stats.get('FontCache', {})}")
        logger.info(f"ResourceCache: {stats.get('ResourceCache', {})}")


# =============================================================================
# SINGLETON ACCESS FUNCTIONS
# =============================================================================

def get_color_cache() -> type[ColorCache]:
    """Get the ColorCache class for color conversions."""
    return ColorCache


def get_qcolor_cache() -> type[QColorCache]:
    """Get the QColorCache class for QColor object pooling."""
    return QColorCache


def get_stylesheet_cache() -> type[StylesheetCache]:
    """Get the StylesheetCache class for stylesheet caching."""
    return StylesheetCache


def get_font_cache() -> type[FontCache]:
    """Get the FontCache class for font caching."""
    return FontCache


def get_resource_cache() -> type[ResourceCache]:
    """Get the ResourceCache class for file existence caching."""
    return ResourceCache


# =============================================================================
# CONVENIENCE FUNCTIONS (direct access without class reference)
# =============================================================================

def cached_rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert RGB to HSL using cache."""
    return ColorCache.rgb_to_hsl(rgb)


def cached_rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert RGB to hex using cache."""
    return ColorCache.rgb_to_hex(rgb)


def cached_text_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Get optimal text color for background using cache."""
    return ColorCache.get_text_color_for_background(rgb)


def cached_qcolor(color: str | tuple) -> 'QColor':
    """Get a cached QColor object."""
    return QColorCache.get(color)


# ============================================================================
# EAGER INITIALIZATION
# ============================================================================
# QColorCache exposes BLACK / WHITE / TRANSPARENT / LOCK_BORDER as class
# attributes (see _init_constants). Without this call they would remain
# None until the first QColorCache.get() invocation. Calling it once at
# import time makes those attributes safe to access directly anywhere in
# the codebase — e.g. `QColorCache.BLACK` works without first having to
# call `QColorCache.get(...)` to trigger the lazy init.
QColorCache._init_constants()