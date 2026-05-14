"""
Session Manager for RNV Color Picker
Handles saving and loading workspace sessions.
Includes auto-save, recent sessions, and state management.
"""

import json
import os
from datetime import datetime
from typing import Any
from pathlib import Path

from utils.logger import Logger
from utils.error_handler import ErrorHandler

logger = Logger("SessionManager")
ERROR_HANDLER_AVAILABLE = True


class SessionManager:
    """Manages Color Picker sessions (save/load workspace state)."""
    
    SESSION_VERSION = "1.0"
    SESSION_EXTENSION = ".cpksession"  # Color Picker Session
    MAX_RECENT_SESSIONS = 10
    AUTOSAVE_PREFIX = "autosave_"  # Prefix for auto-save files
    AUTOSAVE_INTERVAL = 360  # Auto-save every 6 minutes
    
    def __init__(self, sessions_dir: str | None = None):
        """
        Initialize Session Manager.
        
        Args:
            sessions_dir: Directory to store session files. 
                         If None, uses default location.
        """
        if sessions_dir:
            self.sessions_dir = Path(sessions_dir)
        else:
            # Default: sessions folder in user's home directory
            home = Path.home()
            self.sessions_dir = home / ".rnv_color_picker" / "sessions"
        
        # Create sessions directory if it doesn't exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Recent sessions cache file
        self.recent_file = self.sessions_dir / ".recent_sessions.json"
        
        # === AUTO-SAVE SETUP ===
        self.autosave_enabled = True
        self.autosave_interval = self.AUTOSAVE_INTERVAL  # 6 minutes
        self.autosave_timer = None
        self.main_app = None  # Set by main app via start_autosave()
        
        # Generate unique session ID for this app session
        # This ensures auto-saves within same session overwrite each other
        # but a new session creates a new auto-save file
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._autosave_filename = f"{self.AUTOSAVE_PREFIX}{self._session_id}{self.SESSION_EXTENSION}"
        self.autosave_path = self.sessions_dir / self._autosave_filename
        # === END AUTO-SAVE SETUP ===
        
        if logger:
            logger.success(f"Session Manager initialized: {self.sessions_dir}")
            logger.debug(f"Session ID: {self._session_id}")
    
    def save_session(self, 
                    filepath_or_name: str,
                    colors_data: list[dict[str, Any]] | dict[str, Any],
                    image_path: str | None = None,
                    settings: dict[str, Any] | None = None,
                    name: str | None = None,
                    description: str | None = None) -> bool:
        """
        Save a session to a file.
        
        Args:
            filepath_or_name: Path to save session file, or session name
            colors_data: List of color data dictionaries, or dict with "colors" key
            image_path: Path to current image
            settings: Additional settings to save
            name: Session name (optional override)
            description: Session description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle colors_data as dict with "colors" key
            if isinstance(colors_data, dict) and "colors" in colors_data:
                actual_colors = colors_data["colors"]
            else:
                actual_colors = colors_data
            
            # Determine if we were given a filepath or just a name
            filepath = filepath_or_name
            if not os.path.sep in filepath_or_name and not filepath_or_name.endswith(self.SESSION_EXTENSION):
                # It's just a name, generate filepath
                safe_name = "".join(c for c in filepath_or_name if c.isalnum() or c in (' ', '-', '_')).strip()
                filepath = str(self.sessions_dir / f"{safe_name}{self.SESSION_EXTENSION}")
            
            # Ensure proper extension
            if not filepath.endswith(self.SESSION_EXTENSION):
                filepath += self.SESSION_EXTENSION
            
            # Get session name from filename if not provided
            if not name:
                name = Path(filepath).stem
            
            # Build session data
            session_data = {
                "version": self.SESSION_VERSION,
                "name": name,
                "description": description or "",
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat(),
                
                "colors": actual_colors,
                "image_path": image_path,
                
                "settings": settings or {},
                
                "metadata": {
                    "color_count": len(actual_colors),
                    "has_image": image_path is not None
                }
            }
            
            # Write to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            # Add to recent sessions
            self._add_to_recent(filepath)
            
            if logger:
                logger.success(f"Session saved: {filepath}")
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"Error saving session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_session(self, filepath_or_name: str) -> dict[str, Any] | None:
        """
        Load a session from a file.
        
        Args:
            filepath_or_name: Path to session file, or session name
            
        Returns:
            Session data dictionary or None if failed
        """
        try:
            # Determine if we were given a filepath or just a name
            filepath = filepath_or_name
            
            if not os.path.exists(filepath):
                # Try to find by name in sessions directory
                if not os.path.sep in filepath_or_name:
                    # It's just a name, look for it
                    possible_path = self.sessions_dir / f"{filepath_or_name}{self.SESSION_EXTENSION}"
                    if possible_path.exists():
                        filepath = str(possible_path)
                    else:
                        # Search recent sessions for matching name
                        for session in self.get_recent_sessions():
                            if session.get('name') == filepath_or_name:
                                filepath = session.get('filepath', '')
                                break
            
            if not os.path.exists(filepath):
                if logger:
                    logger.warning(f"Session file not found: {filepath_or_name}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Validate version
            if session_data.get('version') != self.SESSION_VERSION:
                if logger:
                    logger.warning(f"Session version mismatch. Expected {self.SESSION_VERSION}, got {session_data.get('version')}")
            
            # Update modified time
            session_data['modified'] = datetime.now().isoformat()
            
            # Add to recent sessions
            self._add_to_recent(filepath)
            
            if logger:
                logger.success(f"Session loaded: {filepath}")
            return session_data
            
        except json.JSONDecodeError as e:
            if logger:
                logger.error(f"Invalid session file format: {e}")
            return None
        except Exception as e:
            if logger:
                logger.error(f"Error loading session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_recent_sessions(self) -> list[dict[str, str]]:
        """
        Get list of recent sessions with metadata.
        
        Returns:
            List of session info dictionaries
        """
        try:
            if not self.recent_file.exists():
                return []
            
            with open(self.recent_file, 'r', encoding='utf-8') as f:
                recent_paths = json.load(f)
            
            # Build session info list
            sessions = []
            for filepath in recent_paths:
                if not os.path.exists(filepath):
                    continue  # Skip deleted files
                
                try:
                    # Quick read just for metadata
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sessions.append({
                        'filepath': filepath,
                        'name': data.get('name', Path(filepath).stem),
                        'modified': data.get('modified', data.get('created', 'Unknown')),
                        'color_count': data.get('metadata', {}).get('color_count', 0),
                        'description': data.get('description', '')
                    })
                except Exception:
                    continue  # Skip corrupted files
            
            return sessions
            
        except Exception as e:
            if logger:
                logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def list_sessions(self) -> list[dict[str, str]]:
        """
        List all available sessions.
        
        Alias for get_recent_sessions() for compatibility.
        
        Returns:
            List of session info dictionaries with keys:
            - filepath: Full path to session file
            - name: Session name
            - modified: Last modified timestamp
            - color_count: Number of colors in session
            - description: Session description
        """
        return self.get_recent_sessions()
    
    def _add_to_recent(self, filepath: str) -> None:
        """Add a session to the recent sessions list."""
        try:
            # Load existing recent list
            recent_paths = []
            if self.recent_file.exists():
                with open(self.recent_file, 'r', encoding='utf-8') as f:
                    recent_paths = json.load(f)
            
            # Remove if already exists (will re-add at start)
            if filepath in recent_paths:
                recent_paths.remove(filepath)
            
            # Add at start
            recent_paths.insert(0, filepath)
            
            # Trim to max size
            recent_paths = recent_paths[:self.MAX_RECENT_SESSIONS]
            
            # Save
            with open(self.recent_file, 'w', encoding='utf-8') as f:
                json.dump(recent_paths, f, indent=2)
                
        except Exception as e:
            if logger:
                logger.error(f"Error adding to recent sessions: {e}")
    
    def _remove_from_recent(self, filepath: str) -> None:
        """Remove a session from the recent sessions list."""
        try:
            if not self.recent_file.exists():
                return
            
            with open(self.recent_file, 'r', encoding='utf-8') as f:
                recent_paths = json.load(f)
            
            if filepath in recent_paths:
                recent_paths.remove(filepath)
                
                with open(self.recent_file, 'w', encoding='utf-8') as f:
                    json.dump(recent_paths, f, indent=2)
                    
        except Exception as e:
            if logger:
                logger.error(f"Error removing from recent sessions: {e}")
    
    def delete_session(self, filepath_or_name: str) -> bool:
        """Delete a session file."""
        try:
            filepath = filepath_or_name
            
            # If not a valid path, try to find by name
            if not os.path.exists(filepath):
                if not os.path.sep in filepath_or_name:
                    # Try direct path in sessions dir
                    possible_path = self.sessions_dir / f"{filepath_or_name}{self.SESSION_EXTENSION}"
                    if possible_path.exists():
                        filepath = str(possible_path)
                    else:
                        # Search recent sessions for matching name
                        for session in self.get_recent_sessions():
                            if session.get('name') == filepath_or_name:
                                filepath = session.get('filepath', '')
                                break
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            self._remove_from_recent(filepath)
            
            if logger:
                logger.success(f"Session deleted: {filepath}")
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"Error deleting session: {e}")
            return False
    
    def generate_session_filename(self, base_name: str | None = None) -> str:
        """
        Generate a unique session filename.
        
        Args:
            base_name: Base name for the session. If None, uses timestamp.
            
        Returns:
            Full path to session file
        """
        if not base_name:
            # Use timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"session_{timestamp}"
        
        # Make filename safe
        base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_'))
        base_name = base_name.strip().replace(' ', '_')
        
        # Generate unique filename
        filepath = self.sessions_dir / f"{base_name}{self.SESSION_EXTENSION}"
        
        # If exists, add number suffix
        counter = 1
        while filepath.exists():
            filepath = self.sessions_dir / f"{base_name}_{counter}{self.SESSION_EXTENSION}"
            counter += 1
        
        return str(filepath)
    
    # ===== AUTO-SAVE METHODS =====
    
    def start_autosave(self, main_app) -> None:
        """
        Start auto-save timer (called by main app on startup).
        
        Args:
            main_app: Reference to main application for getting state
        """
        from PyQt6.QtCore import QTimer
        
        self.main_app = main_app
        if self.autosave_enabled:
            self.autosave_timer = QTimer()
            self.autosave_timer.timeout.connect(self._autosave)
            self.autosave_timer.start(self.autosave_interval * 1000)
            if logger:
                minutes = self.autosave_interval / 60
                logger.success(f"Auto-save enabled (every {minutes:.0f} min) → {self._autosave_filename}")
    
    def stop_autosave(self) -> None:
        """Stop auto-save timer (call on clean exit)."""
        if self.autosave_timer and self.autosave_timer.isActive():
            self.autosave_timer.stop()
            if logger:
                logger.success("Auto-save stopped")
    
    def shutdown(self) -> None:
        """
        Clean shutdown of session manager.
        
        Stops autosave timer and performs final save if needed.
        Call this in the main app's closeEvent.
        """
        try:
            # Stop autosave timer
            self.stop_autosave()
            
            # Perform final autosave if enabled and has data
            if self.autosave_enabled and self.main_app:
                if hasattr(self.main_app, 'get_current_state'):
                    state = self.main_app.get_current_state()
                    if state and state.get('colors'):
                        self.save_session(
                            str(self.autosave_path),
                            colors_data=state.get('colors', []),
                            image_path=state.get('image_path'),
                            settings=state.get('settings'),
                            name=f"Auto-save ({self._session_id})",
                            description=f"Auto-saved on exit - Session {self._session_id}"
                        )
                        if logger:
                            color_count = len(state.get('colors', []))
                            logger.info(f"Final autosave completed ({color_count} colors)")
            
            if logger:
                logger.success("Session manager shutdown complete")
                
        except Exception as e:
            if logger:
                logger.error(f"Error during session manager shutdown: {e}")
    
    def _autosave(self) -> None:
        """Auto-save current session to session-specific file (called by timer)."""
        try:
            if not self.main_app:
                return
            
            # Get current state from main app
            if hasattr(self.main_app, 'get_current_state'):
                state = self.main_app.get_current_state()
                
                if state and state.get('colors'):
                    self.save_session(
                        str(self.autosave_path),
                        colors_data=state.get('colors', []),
                        image_path=state.get('image_path'),
                        settings=state.get('settings'),
                        name=f"Auto-save ({self._session_id})",
                        description=f"Automatic backup - Session {self._session_id}"
                    )
                    if logger:
                        color_count = len(state.get('colors', []))
                        logger.success(f"Auto-saved session ({color_count} colors) to {self._autosave_filename}")
                    
        except Exception as e:
            if logger:
                logger.error(f"Auto-save failed: {e}")
    
    def check_for_autosave(self) -> str | None:
        """
        Check if autosave exists (call on startup for crash recovery).
        
        Returns:
            Path to autosave file if exists, None otherwise
        """
        if self.autosave_path.exists():
            return str(self.autosave_path)
        return None
    
    def delete_autosave(self) -> None:
        """Delete autosave file (call after successful manual save or clean exit)."""
        try:
            if self.autosave_path.exists():
                self.autosave_path.unlink()
                if logger:
                    logger.success("Auto-save file deleted")
        except Exception as e:
            if logger:
                logger.error(f"Error deleting autosave: {e}")
    
    def set_autosave_interval(self, seconds: int) -> None:
        """
        Change auto-save interval.
        
        Args:
            seconds: New interval in seconds (minimum 30)
        """
        if seconds < 30:
            seconds = 30
        self.autosave_interval = seconds
        
        # Restart timer if active
        if self.autosave_timer and self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self.autosave_timer.start(self.autosave_interval * 1000)
            if logger:
                logger.success(f"Auto-save interval changed to {seconds}s")
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self._session_id
    
    def get_autosave_path(self) -> Path:
        """Get the current autosave file path."""
        return self.autosave_path
    
    def list_autosaves(self) -> list[dict]:
        """
        List all auto-save sessions.
        
        Returns:
            List of auto-save session info dictionaries sorted by date (newest first)
        """
        autosaves = []
        try:
            for filepath in self.sessions_dir.glob(f"{self.AUTOSAVE_PREFIX}*{self.SESSION_EXTENSION}"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    autosaves.append({
                        'filepath': str(filepath),
                        'filename': filepath.name,
                        'name': data.get('name', filepath.stem),
                        'description': data.get('description', ''),
                        'color_count': data.get('metadata', {}).get('color_count', 0),
                        'created': data.get('created', ''),
                        'modified': data.get('modified', ''),
                        'is_current_session': filepath.name == self._autosave_filename
                    })
                except Exception:
                    # Skip corrupted files
                    continue
            
            # Sort by modified date, newest first
            autosaves.sort(key=lambda x: x.get('modified', ''), reverse=True)
            
        except Exception as e:
            if logger:
                logger.error(f"Error listing autosaves: {e}")
        
        return autosaves
    
    def cleanup_old_autosaves(self, keep_count: int = 5) -> int:
        """
        Remove old auto-save files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of auto-saves to keep (default 5)
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        try:
            autosaves = self.list_autosaves()
            
            # Skip the current session's autosave
            autosaves = [a for a in autosaves if not a.get('is_current_session')]
            
            # Delete old ones beyond keep_count
            for autosave in autosaves[keep_count:]:
                try:
                    os.remove(autosave['filepath'])
                    deleted += 1
                except Exception:
                    continue
            
            if deleted > 0 and logger:
                logger.info(f"Cleaned up {deleted} old auto-save files")
                
        except Exception as e:
            if logger:
                logger.error(f"Error cleaning up autosaves: {e}")
        
        return deleted


# =========================================================================
# SINGLETON ACCESSOR
# =========================================================================

# Global session manager instance
_session_instance: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.
    
    Returns:
        SessionManager: Singleton session manager instance
    """
    global _session_instance
    if _session_instance is None:
        _session_instance = SessionManager()
    return _session_instance


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def save_session(filepath: str, colors_data: list[dict], **kwargs) -> bool:
    """Quick save session."""
    return get_session_manager().save_session(filepath, colors_data, **kwargs)


def load_session(filepath: str) -> dict | None:
    """Quick load session."""
    return get_session_manager().load_session(filepath)