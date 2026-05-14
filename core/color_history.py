"""
Color History Manager for RNV Color Picker Application
Tracks recently picked colors with timestamps for quick reuse.

Python 3.13 optimized - using modern type hints.
"""

import json
import os
from datetime import datetime
from typing import Any
from pathlib import Path

from utils.logger import Logger
from utils.error_handler import ErrorHandler
from utils.cache import ColorCache

logger = Logger("ColorHistory")
ERROR_HANDLER_AVAILABLE = True
CACHE_AVAILABLE = True


class ColorHistoryManager:
    """Manages color picking history with timestamps."""
    
    MAX_HISTORY_SIZE = 333  # Maximum colors to keep in history
    HISTORY_FILENAME = "color_history.json"
    
    def __init__(self):
        """Initialize the color history manager."""
        self.history: list[dict[str, Any]] = []
        self.history_file: Path | None = None
        self._setup_history_path()
        self.load_history()
    
    def _setup_history_path(self) -> None:
        """Determine the history file path based on OS."""
        try:
            if os.name == 'nt':  # Windows
                app_data = os.getenv('APPDATA')
                if app_data:
                    history_dir = Path(app_data) / "RNVColorPicker"
                else:
                    history_dir = Path.home() / "RNVColorPicker"
            elif os.name == 'posix':
                if hasattr(os, 'uname') and os.uname().sysname == 'Darwin':  # macOS
                    history_dir = Path.home() / "Library" / "Application Support" / "RNVColorPicker"
                else:  # Linux
                    history_dir = Path.home() / ".config" / "RNVColorPicker"
            else:
                # Fallback
                history_dir = Path.home() / ".rnvcolorpicker"
            
            # Create directory if it doesn't exist
            history_dir.mkdir(parents=True, exist_ok=True)
            
            self.history_file = history_dir / self.HISTORY_FILENAME
            if logger:
                logger.info(f"Color history file: {self.history_file}")
            
        except Exception as e:
            if logger:
                logger.error(f"Error setting up history path: {e}")
            # Fallback to local directory
            self.history_file = Path(self.HISTORY_FILENAME)
    
    def load_history(self) -> None:
        """Load history from file."""
        try:
            if self.history_file and self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for empty or whitespace-only content
                if not content.strip():
                    self.history = []
                    if logger:
                        logger.info("Color history file is empty, starting fresh")
                    return
                
                try:
                    data = json.loads(content)
                    self.history = data.get("colors", [])
                    if logger:
                        logger.success(f"Loaded {len(self.history)} colors from history")
                        
                except json.JSONDecodeError as e:
                    # File is corrupted - backup and start fresh
                    if logger:
                        logger.warning(f"Color history file corrupted (JSON error at line {e.lineno})")
                    
                    # Create backup of corrupted file
                    backup_path = self.history_file.with_suffix('.json.bak')
                    try:
                        import shutil
                        shutil.copy2(self.history_file, backup_path)
                        if logger:
                            logger.info(f"Backed up corrupted file to: {backup_path}")
                    except Exception:
                        pass  # Backup failed, continue anyway
                    
                    # Start fresh
                    self.history = []
                    self.save_history()  # Write clean file
                    if logger:
                        logger.info("Created new empty color history file")
            else:
                self.history = []
                if logger:
                    logger.info("No color history found, starting fresh")
        
        except Exception as e:
            if logger:
                logger.error(f"Error loading color history: {e}")
            self.history = []
    
    def save_history(self) -> bool:
        """Save current history to file using atomic write to prevent corruption."""
        try:
            if not self.history_file:
                if logger:
                    logger.warning("No history file path configured")
                return False
            
            # Ensure directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data
            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "colors": self.history
            }
            
            # Atomic write: write to temp file then rename
            # This prevents corruption if the app crashes during write
            temp_file = self.history_file.with_suffix('.json.tmp')
            
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # Rename temp file to actual file (atomic on most systems)
                temp_file.replace(self.history_file)
                
            except Exception as e:
                # Clean up temp file if it exists
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                raise e
            
            if logger:
                logger.debug(f"Color history saved ({len(self.history)} colors)")
            return True
        
        except Exception as e:
            if logger:
                logger.error(f"Error saving color history: {e}")
            return False
    
    def add_color(self, rgb: tuple[int, int, int], source: str = "unknown") -> None:
        """
        Add a color to history.
        
        Args:
            rgb: RGB color tuple (0-255, 0-255, 0-255)
            source: Where the color was picked from ("image", "screen", "manual", etc.)
        """
        try:
            # Convert numpy uint8 to Python int to ensure JSON serialization works
            rgb = tuple(int(v) for v in rgb)
            
            # Create hex code (use cache if available)
            if CACHE_AVAILABLE and ColorCache:
                hex_code = ColorCache.rgb_to_hex(rgb)
            else:
                hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            
            # Check for existing entry (avoid duplicates in quick succession)
            # If the same color was added within the last second, don't add again
            if self.history:
                last_entry = self.history[0]
                if last_entry.get("hex") == hex_code:
                    # Update timestamp of existing entry instead
                    last_entry["timestamp"] = datetime.now().isoformat()
                    last_entry["pick_count"] = last_entry.get("pick_count", 1) + 1
                    self.save_history()
                    return
            
            # Create entry - ensure all values are Python native types
            entry = {
                "hex": hex_code,
                "rgb": list(rgb),  # Already converted to int above
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "pick_count": 1
            }
            
            # Add to front of list
            self.history.insert(0, entry)
            
            # Trim to max size
            if len(self.history) > self.MAX_HISTORY_SIZE:
                self.history = self.history[:self.MAX_HISTORY_SIZE]
            
            # Save automatically
            self.save_history()
            
            if logger:
                logger.debug(f"Added color to history: {hex_code}")
            
        except Exception as e:
            if logger:
                logger.error(f"Error adding color to history: {e}")
    
    def get_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Get color history.
        
        Args:
            limit: Maximum number of entries to return (None = all)
            
        Returns:
            List of color history entries
        """
        if limit is None:
            return self.history.copy()
        return self.history[:limit]
    
    def get_recent_colors(self, count: int = 10) -> list[tuple[int, int, int]]:
        """
        Get just the RGB values of recent colors.
        
        Args:
            count: Number of colors to return
            
        Returns:
            List of RGB tuples
        """
        colors = []
        for entry in self.history[:count]:
            rgb = entry.get("rgb", [0, 0, 0])
            colors.append(tuple(rgb))
        return colors
    
    def clear_history(self) -> None:
        """Clear all color history."""
        self.history = []
        self.save_history()
        if logger:
            logger.info("Color history cleared")
    
    def remove_color(self, hex_code: str) -> bool:
        """
        Remove a specific color from history.
        
        Args:
            hex_code: HEX code of color to remove (e.g., "#ff0000")
            
        Returns:
            True if removed, False if not found
        """
        hex_code = hex_code.lower()
        initial_length = len(self.history)
        
        self.history = [
            entry for entry in self.history 
            if entry.get("hex", "").lower() != hex_code
        ]
        
        if len(self.history) < initial_length:
            self.save_history()
            if logger:
                logger.debug(f"Removed color from history: {hex_code}")
            return True
        return False
    
    def get_color_info(self, hex_code: str) -> dict[str, Any] | None:
        """
        Get info about a specific color in history.
        
        Args:
            hex_code: HEX code to look up
            
        Returns:
            Color entry dict or None if not found
        """
        hex_code = hex_code.lower()
        for entry in self.history:
            if entry.get("hex", "").lower() == hex_code:
                return entry.copy()
        return None
    
    def export_history(self, filepath: str) -> bool:
        """
        Export history to a file.
        
        Args:
            filepath: Path to export file
            
        Returns:
            True if successful
        """
        try:
            data = {
                "version": "1.0",
                "exported": datetime.now().isoformat(),
                "color_count": len(self.history),
                "colors": self.history
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if logger:
                logger.success(f"Color history exported to {filepath}")
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"Error exporting color history: {e}")
            return False
    
    def format_timestamp(self, timestamp: str) -> str:
        """
        Format a timestamp for display.
        
        Args:
            timestamp: ISO format timestamp string
            
        Returns:
            Human-readable time string
        """
        try:
            dt = datetime.fromisoformat(timestamp)
            now = datetime.now()
            
            # If today, show just time
            if dt.date() == now.date():
                return dt.strftime("%I:%M %p")
            
            # If yesterday, show "Yesterday"
            yesterday = now.date().replace(day=now.day - 1) if now.day > 1 else now.date()
            if dt.date() == yesterday:
                return f"Yesterday {dt.strftime('%I:%M %p')}"
            
            # Otherwise show date
            return dt.strftime("%m/%d/%Y %I:%M %p")
            
        except Exception:
            return timestamp


# Singleton instance
_history_instance: ColorHistoryManager | None = None


def get_color_history_manager() -> ColorHistoryManager:
    """Get the global color history manager instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = ColorHistoryManager()
    return _history_instance


# Convenience functions
def add_to_history(rgb: tuple[int, int, int], source: str = "unknown") -> None:
    """Add a color to history."""
    get_color_history_manager().add_color(rgb, source)


def get_recent_colors(count: int = 10) -> list[tuple[int, int, int]]:
    """Get recent colors from history."""
    return get_color_history_manager().get_recent_colors(count)


def clear_color_history() -> None:
    """Clear all color history."""
    get_color_history_manager().clear_history()