"""
File Utilities for RNV Color Picker
Provides common file operations, path handling, and resource management.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Any, Union
from datetime import datetime

from utils.logger import Logger
from utils.error_handler import ErrorHandler

logger = Logger("FileUtils")
ERROR_HANDLER_AVAILABLE = True


# =========================================================================
# PATH UTILITIES
# =========================================================================

def ensure_directory(path: Union[str, Path]) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        bool: True if directory exists or was created
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to create directory: {path}", details=str(e))
        return False


def get_user_data_dir(app_name: str = "RNVColorPicker") -> Path:
    """
    Get the user's application data directory.
    
    Args:
        app_name: Application name for the directory
        
    Returns:
        Path: User data directory path
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:  # macOS/Linux
        base = Path.home() / '.config'
    
    user_dir = base / app_name
    ensure_directory(user_dir)
    return user_dir


def get_temp_dir(app_name: str = "RNVColorPicker") -> Path:
    """
    Get a temporary directory for the application.
    
    Args:
        app_name: Application name for the temp directory
        
    Returns:
        Path: Temporary directory path
    """
    import tempfile
    temp_base = Path(tempfile.gettempdir())
    temp_dir = temp_base / app_name
    ensure_directory(temp_dir)
    return temp_dir


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize and resolve a file path.
    
    Args:
        path: Path to normalize
        
    Returns:
        Path: Normalized absolute path
    """
    return Path(path).expanduser().resolve()


# =========================================================================
# FILE OPERATIONS
# =========================================================================

def safe_read_json(filepath: Union[str, Path], default: Any = None) -> Any:
    """
    Safely read a JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Parsed JSON data or default value
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return default
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except json.JSONDecodeError as e:
        if logger:
            logger.warning(f"Invalid JSON in {filepath}: {e}")
        return default
    except Exception as e:
        if logger:
            logger.error(f"Error reading {filepath}: {e}")
        return default


def safe_write_json(filepath: Union[str, Path], data: Any, indent: int = 2) -> bool:
    """
    Safely write data to a JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        data: Data to write
        indent: JSON indentation level
        
    Returns:
        bool: True if write was successful
    """
    try:
        path = Path(filepath)
        ensure_directory(path.parent)
        
        # Write to temp file first, then rename (atomic write)
        temp_path = path.with_suffix('.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        # Rename temp file to final path
        temp_path.replace(path)
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error writing {filepath}: {e}")
        return False


def safe_read_text(filepath: Union[str, Path], default: str = "") -> str:
    """
    Safely read a text file with error handling.
    
    Args:
        filepath: Path to text file
        default: Default value if file doesn't exist
        
    Returns:
        File contents or default value
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return default
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        if logger:
            logger.error(f"Error reading {filepath}: {e}")
        return default


def safe_write_text(filepath: Union[str, Path], content: str) -> bool:
    """
    Safely write text to a file with error handling.
    
    Args:
        filepath: Path to text file
        content: Content to write
        
    Returns:
        bool: True if write was successful
    """
    try:
        path = Path(filepath)
        ensure_directory(path.parent)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error writing {filepath}: {e}")
        return False


def safe_copy(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """
    Safely copy a file with error handling.
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        bool: True if copy was successful
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            if logger:
                logger.warning(f"Source file not found: {src}")
            return False
        
        ensure_directory(dst_path.parent)
        shutil.copy2(src_path, dst_path)
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error copying {src} to {dst}: {e}")
        return False


def safe_delete(filepath: Union[str, Path]) -> bool:
    """
    Safely delete a file with error handling.
    
    Args:
        filepath: Path to file to delete
        
    Returns:
        bool: True if delete was successful or file didn't exist
    """
    try:
        path = Path(filepath)
        if path.exists():
            path.unlink()
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error deleting {filepath}: {e}")
        return False


# =========================================================================
# FILE INFORMATION
# =========================================================================

def get_file_size(filepath: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to file
        
    Returns:
        int: File size in bytes, or -1 if file doesn't exist
    """
    try:
        return Path(filepath).stat().st_size
    except Exception:
        return -1


def get_file_modified_time(filepath: Union[str, Path]) -> datetime | None:
    """
    Get file modification time.
    
    Args:
        filepath: Path to file
        
    Returns:
        datetime: Modification time, or None if file doesn't exist
    """
    try:
        stat = Path(filepath).stat()
        return datetime.fromtimestamp(stat.st_mtime)
    except Exception:
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size as human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes < 0:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} PB"


# =========================================================================
# BACKUP UTILITIES
# =========================================================================

def create_backup(filepath: Union[str, Path], backup_dir: Union[str, Path] = None) -> Path | None:
    """
    Create a backup of a file.
    
    Args:
        filepath: Path to file to backup
        backup_dir: Directory for backup (defaults to same directory)
        
    Returns:
        Path: Path to backup file, or None if backup failed
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return None
        
        # Determine backup directory
        if backup_dir:
            backup_path = Path(backup_dir)
        else:
            backup_path = path.parent
        
        ensure_directory(backup_path)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_{timestamp}{path.suffix}.bak"
        backup_file = backup_path / backup_name
        
        shutil.copy2(path, backup_file)
        
        if logger:
            logger.debug(f"Created backup: {backup_file}")
        
        return backup_file
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to create backup of {filepath}: {e}")
        return None


def cleanup_old_backups(backup_dir: Union[str, Path], prefix: str, keep_count: int = 5) -> int:
    """
    Clean up old backup files, keeping only the most recent ones.
    
    Args:
        backup_dir: Directory containing backups
        prefix: Filename prefix to match
        keep_count: Number of backups to keep
        
    Returns:
        int: Number of files deleted
    """
    try:
        path = Path(backup_dir)
        if not path.exists():
            return 0
        
        # Find matching backup files
        backups = sorted(
            path.glob(f"{prefix}*.bak"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Delete old backups
        deleted = 0
        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            deleted += 1
        
        if deleted > 0 and logger:
            logger.debug(f"Cleaned up {deleted} old backups in {backup_dir}")
        
        return deleted
        
    except Exception as e:
        if logger:
            logger.error(f"Error cleaning up backups: {e}")
        return 0


# =========================================================================
# RESOURCE VALIDATION
# =========================================================================

def validate_image_file(filepath: Union[str, Path]) -> bool:
    """
    Validate that a file is a valid image.
    
    Args:
        filepath: Path to image file
        
    Returns:
        bool: True if file is a valid image
    """
    try:
        from PIL import Image
        
        path = Path(filepath)
        if not path.exists():
            return False
        
        # Check extension
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        if path.suffix.lower() not in valid_extensions:
            return False
        
        # Try to open the image
        with Image.open(path) as img:
            img.verify()
        
        return True
        
    except Exception:
        return False


def get_image_dimensions(filepath: Union[str, Path]) -> tuple[int, int] | None:
    """
    Get dimensions of an image file.
    
    Args:
        filepath: Path to image file
        
    Returns:
        tuple: (width, height) or None if not a valid image
    """
    try:
        from PIL import Image
        
        with Image.open(filepath) as img:
            return img.size
            
    except Exception:
        return None