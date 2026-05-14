"""
Utility modules for RNV Color Picker.

Contains configuration, caching, logging, and helper functions.
"""

from utils.config import (
    ThemeManager, 
    MAX_COLORS,
    DEFAULT_WEIGHT,
    BUTTON_HEIGHT_MIN,
    BUTTON_HEIGHT_MAX,
    WINDOW_WIDTH_MIN,
    WINDOW_WIDTH_MAX,
    SWATCH_SIZE,
    MAX_IMAGE_DIMENSION,
    BASE_DIR,
    RESOURCES_DIR,
    BUTTON_IMAGES_DIR,
    BACKGROUND_IMAGES_DIR,
    FONTS_DIR,
    ICONS_DIR,
)
from utils.font_loader import load_embedded_font
from utils.logger import Logger, get_logger, LogLevel
from utils.dialog_helper import DialogHelper, DialogResult
from utils.error_handler import ErrorHandler, ErrorContext
from utils.signal_manager import SignalConnectionManager
from utils.settings_manager import SettingsManager, get_settings_manager
from utils.session_manager import SessionManager
from utils.clipboard import ClipboardUtils
from utils.pixmap_cache import ImagePixmapCache
from utils.cache import (
    ColorCache,
    QColorCache,
    StylesheetCache,
    FontCache,
    ResourceCache,
    clear_all_caches,
)
from utils.file_utils import (
    ensure_directory,
    get_user_data_dir,
    get_temp_dir,
    normalize_path,
    safe_read_json,
    safe_write_json,
    safe_read_text,
    safe_write_text,
    safe_copy,
    safe_delete,
    get_file_size,
    get_file_modified_time,
    format_file_size,
    create_backup,
    cleanup_old_backups,
    validate_image_file,
    get_image_dimensions,
)
from utils.async_file_ops import AsyncFileManager

__all__ = [
    # Config
    'ThemeManager',
    'MAX_COLORS',
    'DEFAULT_WEIGHT',
    'BUTTON_HEIGHT_MIN',
    'BUTTON_HEIGHT_MAX',
    'WINDOW_WIDTH_MIN',
    'WINDOW_WIDTH_MAX',
    'SWATCH_SIZE',
    'MAX_IMAGE_DIMENSION',
    'BASE_DIR',
    'RESOURCES_DIR',
    'BUTTON_IMAGES_DIR',
    'BACKGROUND_IMAGES_DIR',
    'FONTS_DIR',
    'ICONS_DIR',
    # Font
    'load_embedded_font',
    # Logging
    'Logger',
    'get_logger',
    'LogLevel',
    # Dialog
    'DialogHelper',
    'DialogResult',
    # Error handling
    'ErrorHandler',
    'ErrorContext',
    # Signal management
    'SignalConnectionManager',
    # Settings
    'SettingsManager',
    'get_settings_manager',
    # Session
    'SessionManager',
    # Clipboard
    'ClipboardUtils',
    # Pixmap cache
    'ImagePixmapCache',
    # Caching
    'ColorCache',
    'QColorCache',
    'StylesheetCache',
    'FontCache',
    'ResourceCache',
    'clear_all_caches',
    # File utils
    'ensure_directory',
    'get_user_data_dir',
    'get_temp_dir',
    'normalize_path',
    'safe_read_json',
    'safe_write_json',
    'safe_read_text',
    'safe_write_text',
    'safe_copy',
    'safe_delete',
    'get_file_size',
    'get_file_modified_time',
    'format_file_size',
    'create_backup',
    'cleanup_old_backups',
    'validate_image_file',
    'get_image_dimensions',
    # Async
    'AsyncFileManager',
]