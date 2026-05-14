"""
Settings Panel for RNV Color Picker Application
Tabbed dialog with History, Sessions, Shortcuts, Settings, Harmony, and Accessibility tabs.
"""

from typing import TYPE_CHECKING
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QComboBox, QScrollArea, 
    QCheckBox, QLineEdit, QFileDialog, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QFrame,
    QGridLayout, QGroupBox, QInputDialog, QApplication,
    QSlider, QSpinBox, QListView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime

from utils.logger import Logger
from utils.dialog_helper import DialogHelper
from utils.cache import QColorCache, ColorCache, StylesheetCache
from utils.settings_manager import get_settings_manager
from utils.session_manager import get_session_manager
from utils.error_handler import ErrorHandler
from utils.signal_manager import SignalConnectionManager
from utils.config import (
    BRAND_GOLD, BRAND_GOLD_DARK,
    PREVIEW_BORDER_THIN,
    CONTRAST_DEMO_BLACK_BG, CONTRAST_DEMO_WHITE_BG,
    CONTRAST_DEMO_BLACK_FG, CONTRAST_DEMO_WHITE_FG,
    STATUS_SUCCESS_BG, STATUS_SUCCESS_FG,
    STATUS_ERROR_BG, STATUS_ERROR_FG,
    MISSING_HEX_PLACEHOLDER,
)
from core.color_history import get_color_history_manager
from core.color_harmony import ColorHarmony, HarmonyType
from core.accessibility import ColorAccessibility, ColorBlindnessType, WCAGLevel

logger = Logger("SettingsPanel")
DIALOG_HELPER_AVAILABLE = True
CACHE_AVAILABLE = True
ERROR_HANDLER_AVAILABLE = True
SIGNAL_MANAGER_AVAILABLE = True

if TYPE_CHECKING:
    from RNV_Color_Picker import ColorPickerApp


class ColorHistoryItem(QListWidgetItem):
    """Custom list item for displaying color history with color swatch."""
    
    def __init__(self, hex_code: str, time_str: str, color_data: dict):
        """
        Initialize color history item.
        
        Args:
            hex_code: HEX color code (e.g., "#ff0000")
            time_str: Formatted timestamp string
            color_data: Full color data dictionary
        """
        # Create display text with color swatch placeholder
        display_text = f"{hex_code}  -  {time_str}"
        super().__init__(display_text)
        
        self.hex_code = hex_code
        self.time_str = time_str
        self.color_data = color_data
        
        # Set background color to show the actual color
        try:
            rgb = color_data.get("rgb", [0, 0, 0])
            
            # Use cached colors if available
            if CACHE_AVAILABLE and QColorCache and ColorCache:
                color = QColorCache.get((rgb[0], rgb[1], rgb[2]))
                text_rgb = ColorCache.get_text_color_for_background((rgb[0], rgb[1], rgb[2]))
                text_color = QColorCache.get(text_rgb)
            else:
                color = QColor(rgb[0], rgb[1], rgb[2])
                # Determine text color based on brightness
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                text_color = QColorCache.BLACK if brightness > 128 else QColorCache.WHITE
            
            self.setBackground(color)
            self.setForeground(text_color)
            
        except Exception:
            pass  # Use default colors if parsing fails


class SettingsPanel(QDialog):
    """Tabbed settings dialog for RNV Color Picker."""
    
    # Signals
    settings_changed = pyqtSignal(str, object)  # setting_key, value
    theme_change_requested = pyqtSignal(str)  # theme name
    session_loaded = pyqtSignal(str)  # session name
    color_loaded_from_history = pyqtSignal(tuple)  # RGB tuple when color loaded from history
    
    def __init__(self, parent: "ColorPickerApp" = None):
        super().__init__(parent)
        
        self.parent_app = parent
        
        # Initialize signal manager for proper cleanup
        if SIGNAL_MANAGER_AVAILABLE and SignalConnectionManager:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        # Get managers with proper logging
        if get_settings_manager:
            self.settings_manager = get_settings_manager()
            if logger:
                logger.info("[OK] Settings Manager module loaded")
        else:
            self.settings_manager = None
            if logger:
                logger.warning("Settings manager not available")
        
        if get_session_manager:
            self.session_manager = get_session_manager()
            if logger:
                logger.info("[OK] Session Manager module loaded")
        else:
            self.session_manager = None
            if logger:
                logger.warning("Session manager not available")
        
        # Color history manager
        if get_color_history_manager:
            self.color_history = get_color_history_manager()
            if logger:
                logger.info("[OK] Color History module loaded")
        else:
            self.color_history = None
            if logger:
                logger.warning("Color history manager not available")
        
        self.setWindowTitle("RNV Color Picker - Features & Settings")
        self.setModal(False)  # Allow interaction with main window
        self.setFixedSize(660, 700)  # Fixed size - no resizing
        
        self._build_ui()
        self._load_settings_into_ui()
        self._apply_theme()
        
        if logger:
            logger.success("Settings Panel initialized")
    
    def _build_ui(self) -> None:
        """Build the tabbed settings panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setUsesScrollButtons(False)  # Disable scroll arrows
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideNone)  # Don't truncate tab text
        self.tab_widget.tabBar().setExpanding(True)  # Make tabs expand to fill width
        
        # Create tabs
        self.tab_widget.addTab(self._create_history_tab(), "History")
        self.tab_widget.addTab(self._create_sessions_tab(), "Sessions")
        self.tab_widget.addTab(self._create_harmony_tab(), "Harmony")
        self.tab_widget.addTab(self._create_accessibility_tab(), "Accessibility")
        self.tab_widget.addTab(self._create_shortcuts_tab(), "Shortcuts")
        self.tab_widget.addTab(self._create_settings_tab(), "Settings")
        
        layout.addWidget(self.tab_widget, 1)
        
        # Close button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    # =========================================================================
    # HISTORY TAB
    # =========================================================================
    
    def _create_history_tab(self) -> QWidget:
        """Create the History tab for viewing recently picked colors."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Recent Picked Colors")
        if CACHE_AVAILABLE and StylesheetCache:
            header.setStyleSheet(StylesheetCache.get_header_stylesheet())
        else:
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        desc = QLabel("Click any color to load it into an empty slot")
        if CACHE_AVAILABLE and StylesheetCache:
            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(300)
        self.history_list.itemDoubleClicked.connect(self._load_color_from_history)
        layout.addWidget(self.history_list)
        
        # Refresh history list
        self._refresh_history_list()
        
        # History buttons
        btn_layout = QHBoxLayout()
        
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.clicked.connect(self._clear_color_history)
        clear_history_btn.setToolTip("Clear all color history")
        btn_layout.addWidget(clear_history_btn)
        
        export_history_btn = QPushButton("Export History")
        export_history_btn.clicked.connect(self._export_color_history)
        export_history_btn.setToolTip("Export color history to file")
        btn_layout.addWidget(export_history_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_history_list)
        refresh_btn.setToolTip("Refresh the history list")
        btn_layout.addWidget(refresh_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return widget
    
    def _refresh_history_list(self) -> None:
        """Refresh the list of color history."""
        self.history_list.clear()
        
        if self.color_history:
            history = self.color_history.get_history()
            
            for entry in history:
                hex_code = entry.get("hex", MISSING_HEX_PLACEHOLDER)
                timestamp = entry.get("timestamp", "")
                
                # Format timestamp for display
                time_str = self.color_history.format_timestamp(timestamp)
                
                # Create list item
                item = ColorHistoryItem(hex_code, time_str, entry)
                self.history_list.addItem(item)
            
            if logger:
                logger.debug(f"Loaded {len(history)} colors in history")
        else:
            # Add placeholder item
            item = QListWidgetItem("(Color history not available)")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.history_list.addItem(item)
    
    def _load_color_from_history(self, item: QListWidgetItem = None) -> None:
        """Load a color from history into the palette."""
        if item is None:
            item = self.history_list.currentItem()
        
        if not item or not hasattr(item, 'color_data'):
            return
        
        try:
            rgb = tuple(item.color_data.get("rgb", [0, 0, 0]))
            hex_code = item.color_data.get("hex", MISSING_HEX_PLACEHOLDER)
            
            # Emit signal to add color to palette
            self.color_loaded_from_history.emit(rgb)
            
            if logger:
                logger.success(f"Loaded color from history: {hex_code}")
                
        except Exception as e:
            if logger:
                logger.error(f"Error loading color from history: {e}")
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, f"Failed to load color: {e}", title="Error")
            else:
                QMessageBox.warning(self, "Error", f"Failed to load color: {e}")
    
    def _clear_color_history(self) -> None:
        """Clear all color history."""
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            confirmed = DialogHelper.confirm(
                self, "Clear all color history?\nThis cannot be undone.",
                title="Confirm Clear"
            )
        else:
            reply = QMessageBox.question(
                self, "Confirm Clear",
                "Clear all color history?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            confirmed = (reply == QMessageBox.StandardButton.Yes)
        
        if confirmed:
            if self.color_history:
                self.color_history.clear_history()
                self._refresh_history_list()
                if logger:
                    logger.info("Color history cleared")
    
    def _export_color_history(self) -> None:
        """Export color history to a file."""
        if not self.color_history:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "Color history not available", title="Error")
            else:
                QMessageBox.warning(self, "Error", "Color history not available")
            return
        
        history = self.color_history.get_history()
        if not history:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "No colors in history to export", title="No History")
            else:
                QMessageBox.warning(self, "No History", "No colors in history to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Color History",
            "color_history.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if file_path:
            if file_path.endswith('.txt'):
                # Export as simple text list
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("# RNV Color Picker - Color History\n")
                        f.write(f"# Exported: {datetime.now().isoformat()}\n")
                        f.write(f"# Total colors: {len(history)}\n\n")
                        
                        for entry in history:
                            hex_code = entry.get("hex", MISSING_HEX_PLACEHOLDER)
                            rgb = entry.get("rgb", [0, 0, 0])
                            timestamp = entry.get("timestamp", "")
                            f.write(f"{hex_code}  RGB({rgb[0]}, {rgb[1]}, {rgb[2]})  {timestamp}\n")
                    
                    if DIALOG_HELPER_AVAILABLE and DialogHelper:
                        DialogHelper.show_info(
                            self, f"Exported {len(history)} colors to:\n{file_path}",
                            title="Success"
                        )
                    else:
                        QMessageBox.information(
                            self, "Success", 
                            f"Exported {len(history)} colors to:\n{file_path}"
                        )
                except Exception as e:
                    if DIALOG_HELPER_AVAILABLE and DialogHelper:
                        DialogHelper.show_warning(self, f"Failed to export: {e}", title="Error")
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to export: {e}")
            else:
                # Export as JSON
                if self.color_history.export_history(file_path):
                    if DIALOG_HELPER_AVAILABLE and DialogHelper:
                        DialogHelper.show_info(
                            self, f"Exported {len(history)} colors to:\n{file_path}",
                            title="Success"
                        )
                    else:
                        QMessageBox.information(
                            self, "Success", 
                            f"Exported {len(history)} colors to:\n{file_path}"
                        )
                else:
                    if DIALOG_HELPER_AVAILABLE and DialogHelper:
                        DialogHelper.show_warning(self, "Failed to export color history", title="Error")
                    else:
                        QMessageBox.warning(self, "Error", "Failed to export color history")
    
    # =========================================================================
    # SESSIONS TAB
    # =========================================================================
    
    def _create_sessions_tab(self) -> QWidget:
        """Create the Sessions tab for saving/loading palettes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Saved Sessions")
        if CACHE_AVAILABLE and StylesheetCache:
            header.setStyleSheet(StylesheetCache.get_header_stylesheet())
        else:
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        desc = QLabel("Save and restore your color palettes between sessions")
        if CACHE_AVAILABLE and StylesheetCache:
            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)
        
        # Session list
        self.session_list = QListWidget()
        self.session_list.setMinimumHeight(200)
        self.session_list.itemDoubleClicked.connect(self._load_selected_session)
        layout.addWidget(self.session_list)
        
        # Refresh session list
        self._refresh_session_list()
        
        # Session buttons
        btn_layout = QHBoxLayout()
        
        save_session_btn = QPushButton("Save Current")
        save_session_btn.clicked.connect(self._save_current_session)
        save_session_btn.setToolTip("Save current palette as a new session")
        btn_layout.addWidget(save_session_btn)
        
        load_session_btn = QPushButton("Load Selected")
        load_session_btn.clicked.connect(self._load_selected_session)
        load_session_btn.setToolTip("Load the selected session")
        btn_layout.addWidget(load_session_btn)
        
        delete_session_btn = QPushButton("Delete Selected")
        delete_session_btn.clicked.connect(self._delete_selected_session)
        delete_session_btn.setToolTip("Delete the selected session")
        btn_layout.addWidget(delete_session_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_session_list)
        refresh_btn.setToolTip("Refresh the session list")
        btn_layout.addWidget(refresh_btn)
        
        layout.addLayout(btn_layout)
        
        # Auto-save options
        layout.addWidget(self._create_section_divider())
        
        auto_header = QLabel("Auto-Save Options")
        auto_header.setStyleSheet(StylesheetCache.get_subheader_stylesheet(self._get_accent()))
        layout.addWidget(auto_header)
        
        self.session_autosave_check = QCheckBox("Auto-save session on exit")
        self.session_autosave_check.setToolTip("Automatically save current palette when closing")
        self.session_autosave_check.stateChanged.connect(self._sync_autosave_checkbox_from_sessions)
        layout.addWidget(self.session_autosave_check)
        
        self.session_autoload_check = QCheckBox("Auto-load last session on startup")
        self.session_autoload_check.setToolTip("Restore palette from previous session")
        self.session_autoload_check.stateChanged.connect(self._sync_autoload_checkbox_from_sessions)
        layout.addWidget(self.session_autoload_check)
        
        layout.addStretch()
        
        return widget
    
    def _sync_autosave_checkbox_from_general(self, state: int) -> None:
        """Sync autosave checkbox from General tab to Sessions tab."""
        if hasattr(self, 'session_autosave_check') and self.session_autosave_check:
            # Block signals to prevent infinite loop
            self.session_autosave_check.blockSignals(True)
            self.session_autosave_check.setChecked(state == 2)  # Qt.CheckState.Checked = 2
            self.session_autosave_check.blockSignals(False)
    
    def _sync_autosave_checkbox_from_sessions(self, state: int) -> None:
        """Sync autosave checkbox from Sessions tab to General tab."""
        if hasattr(self, 'autosave_session_check') and self.autosave_session_check:
            # Block signals to prevent infinite loop
            self.autosave_session_check.blockSignals(True)
            self.autosave_session_check.setChecked(state == 2)  # Qt.CheckState.Checked = 2
            self.autosave_session_check.blockSignals(False)
    
    def _sync_autoload_checkbox_from_general(self, state: int) -> None:
        """Sync autoload checkbox from General tab to Sessions tab."""
        if hasattr(self, 'session_autoload_check') and self.session_autoload_check:
            # Block signals to prevent infinite loop
            self.session_autoload_check.blockSignals(True)
            self.session_autoload_check.setChecked(state == 2)  # Qt.CheckState.Checked = 2
            self.session_autoload_check.blockSignals(False)
    
    def _sync_autoload_checkbox_from_sessions(self, state: int) -> None:
        """Sync autoload checkbox from Sessions tab to General tab."""
        if hasattr(self, 'autoload_session_check') and self.autoload_session_check:
            # Block signals to prevent infinite loop
            self.autoload_session_check.blockSignals(True)
            self.autoload_session_check.setChecked(state == 2)  # Qt.CheckState.Checked = 2
            self.autoload_session_check.blockSignals(False)
    
    def _refresh_session_list(self) -> None:
        """Refresh the list of saved sessions."""
        self.session_list.clear()
        
        if self.session_manager:
            sessions = self.session_manager.list_sessions()
            for session in sessions:
                # session is a dict with keys: name, filepath, modified, color_count, description
                session_name = session.get('name', 'Unnamed Session') if isinstance(session, dict) else str(session)
                item = QListWidgetItem(session_name)
                # Store the full session data for later retrieval
                item.setData(Qt.ItemDataRole.UserRole, session)
                self.session_list.addItem(item)
            
            if logger:
                logger.debug(f"Loaded {len(sessions)} sessions")
        else:
            # Add placeholder item
            item = QListWidgetItem("(Session manager not available)")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.session_list.addItem(item)
    
    def _save_current_session(self) -> None:
        """Save the current palette as a session."""
        if not self.session_manager:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "Session manager not available", title="Error")
            else:
                QMessageBox.warning(self, "Error", "Session manager not available")
            return
        
        if not self.parent_app or not self.parent_app.colors:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "No colors to save!", title="No Colors")
            else:
                QMessageBox.warning(self, "No Colors", "No colors to save!")
            return
        
        # Get session name from user
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            name, ok = DialogHelper.get_text(
                self, "Save Session", "Enter session name:",
                text=f"palette_{len(self.parent_app.colors)}_colors"
            )
        else:
            name, ok = QInputDialog.getText(
                self, "Save Session", "Enter session name:",
                text=f"palette_{len(self.parent_app.colors)}_colors"
            )
        
        if ok and name:
            # Convert colors to session format - ensure all values are Python native types
            # to avoid numpy uint8 JSON serialization issues
            colors_data = [
                {
                    "rgb": [int(v) for v in color[0]], 
                    "hsl": [int(v) for v in color[1]], 
                    "hilbert": int(color[2]), 
                    "locked": bool(color[3])
                }
                for color in self.parent_app.colors
            ]
            
            success = self.session_manager.save_session(name, {"colors": colors_data})
            
            if success:
                self._refresh_session_list()
                if DIALOG_HELPER_AVAILABLE and DialogHelper:
                    DialogHelper.show_info(
                        self, f"Session '{name}' saved with {len(colors_data)} colors",
                        title="Success"
                    )
                else:
                    QMessageBox.information(
                        self, "Success", 
                        f"Session '{name}' saved with {len(colors_data)} colors"
                    )
                if logger:
                    logger.success(f"Saved session: {name}")
            else:
                if DIALOG_HELPER_AVAILABLE and DialogHelper:
                    DialogHelper.show_warning(self, "Failed to save session", title="Error")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save session")
    
    def _load_selected_session(self) -> None:
        """Load the selected session."""
        current_item = self.session_list.currentItem()
        if not current_item:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "Please select a session to load", title="No Selection")
            else:
                QMessageBox.warning(self, "No Selection", "Please select a session to load")
            return
        
        session_name = current_item.text()
        
        if not self.session_manager:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "Session manager not available", title="Error")
            else:
                QMessageBox.warning(self, "Error", "Session manager not available")
            return
        
        session_data = self.session_manager.load_session(session_name)
        
        if session_data and "colors" in session_data:
            # Emit signal to load colors
            self.session_loaded.emit(session_name)
            
            # Load colors into parent app
            if self.parent_app:
                colors_data = session_data["colors"]
                self.parent_app.colors.clear()
                
                for color_info in colors_data:
                    rgb = tuple(color_info["rgb"])
                    hsl = tuple(color_info["hsl"])
                    hilbert = color_info["hilbert"]
                    locked = color_info.get("locked", False)
                    self.parent_app.colors.append((rgb, hsl, hilbert, locked))
                
                self.parent_app.refresh_color_display()
                
                if DIALOG_HELPER_AVAILABLE and DialogHelper:
                    DialogHelper.show_info(
                        self, f"Loaded {len(colors_data)} colors from '{session_name}'",
                        title="Success"
                    )
                else:
                    QMessageBox.information(
                        self, "Success",
                        f"Loaded {len(colors_data)} colors from '{session_name}'"
                    )
                if logger:
                    logger.success(f"Loaded session: {session_name}")
        else:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, f"Failed to load session: {session_name}", title="Error")
            else:
                QMessageBox.warning(self, "Error", f"Failed to load session: {session_name}")
    
    def _delete_selected_session(self) -> None:
        """Delete the selected session."""
        current_item = self.session_list.currentItem()
        if not current_item:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_warning(self, "Please select a session to delete", title="No Selection")
            else:
                QMessageBox.warning(self, "No Selection", "Please select a session to delete")
            return
        
        session_name = current_item.text()
        
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            confirmed = DialogHelper.confirm(
                self, f"Delete session '{session_name}'?\nThis cannot be undone.",
                title="Confirm Delete"
            )
        else:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete session '{session_name}'?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            confirmed = (reply == QMessageBox.StandardButton.Yes)
        
        if confirmed:
            if self.session_manager:
                success = self.session_manager.delete_session(session_name)
                if success:
                    self._refresh_session_list()
                    if logger:
                        logger.info(f"Deleted session: {session_name}")
                else:
                    if DIALOG_HELPER_AVAILABLE and DialogHelper:
                        DialogHelper.show_warning(self, "Failed to delete session", title="Error")
                    else:
                        QMessageBox.warning(self, "Error", "Failed to delete session")
    
    # =========================================================================
    # COLOR HARMONY TAB
    # =========================================================================
    
    def _create_harmony_tab(self) -> QWidget:
        """Create the Color Harmony tab for generating color schemes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Color Harmony Generator")
        if CACHE_AVAILABLE and StylesheetCache:
            header.setStyleSheet(StylesheetCache.get_header_stylesheet())
        else:
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        desc = QLabel("Generate harmonious color schemes from a base color")
        if CACHE_AVAILABLE and StylesheetCache:
            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)
        
        # Check if ColorHarmony is available
        if not ColorHarmony:
            no_module = QLabel("Color Harmony module not available.\nPlace color_harmony.py in core/ folder.")
            no_module.setStyleSheet(StylesheetCache.get_error_stylesheet())
            no_module.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_module)
            layout.addStretch()
            return widget
        
        # Base color selection
        base_group = QGroupBox("Base Color")
        base_layout = QHBoxLayout(base_group)
        
        # Color preview
        self.harmony_base_preview = QLabel()
        self.harmony_base_preview.setFixedSize(60, 60)
        self.harmony_base_preview.setStyleSheet(f"""
            background-color: {self._get_accent()};
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        base_layout.addWidget(self.harmony_base_preview)
        
        # RGB inputs
        rgb_layout = QGridLayout()
        
        self.harmony_r_spin = QSpinBox()
        self.harmony_r_spin.setRange(0, 255)
        self.harmony_r_spin.setValue(191)
        self.harmony_r_spin.valueChanged.connect(self._update_harmony_base)
        
        self.harmony_g_spin = QSpinBox()
        self.harmony_g_spin.setRange(0, 255)
        self.harmony_g_spin.setValue(145)
        self.harmony_g_spin.valueChanged.connect(self._update_harmony_base)
        
        self.harmony_b_spin = QSpinBox()
        self.harmony_b_spin.setRange(0, 255)
        self.harmony_b_spin.setValue(69)
        self.harmony_b_spin.valueChanged.connect(self._update_harmony_base)
        
        rgb_layout.addWidget(QLabel("R:"), 0, 0)
        rgb_layout.addWidget(self.harmony_r_spin, 0, 1)
        rgb_layout.addWidget(QLabel("G:"), 1, 0)
        rgb_layout.addWidget(self.harmony_g_spin, 1, 1)
        rgb_layout.addWidget(QLabel("B:"), 2, 0)
        rgb_layout.addWidget(self.harmony_b_spin, 2, 1)
        
        base_layout.addLayout(rgb_layout)
        
        # Pick from palette button
        pick_btn = QPushButton("Pick from Palette")
        pick_btn.clicked.connect(self._pick_harmony_base_from_palette)
        base_layout.addWidget(pick_btn)
        
        base_layout.addStretch()
        layout.addWidget(base_group)
        
        # Harmony type selection
        type_group = QGroupBox("Harmony Type")
        type_layout = QVBoxLayout(type_group)
        
        self.harmony_type_combo = QComboBox()
        self.harmony_type_combo.setView(QListView())
        harmony_types = [
            ("Complementary", "2 colors opposite on the wheel"),
            ("Triadic", "3 colors evenly spaced (120 deg)"),
            ("Analogous", "3 adjacent colors on the wheel"),
            ("Split-Complementary", "Base + 2 colors adjacent to complement"),
            ("Tetradic (Square)", "4 colors evenly spaced (90 deg)"),
            ("Compound (Rectangle)", "4 colors in rectangular pattern"),
            ("Monochromatic", "5 variations of same hue"),
        ]
        for name, tooltip in harmony_types:
            self.harmony_type_combo.addItem(name)
        self.harmony_type_combo.currentIndexChanged.connect(self._generate_harmony)
        type_layout.addWidget(self.harmony_type_combo)
        
        # Description
        self.harmony_desc_label = QLabel()
        self.harmony_desc_label.setStyleSheet("color: gray; font-size: 11px; padding: 5px;")
        self.harmony_desc_label.setWordWrap(True)
        type_layout.addWidget(self.harmony_desc_label)
        
        layout.addWidget(type_group)
        
        # Generated colors display
        result_group = QGroupBox("Generated Harmony")
        result_layout = QVBoxLayout(result_group)
        
        # Color swatches container
        self.harmony_swatches_widget = QWidget()
        self.harmony_swatches_layout = QHBoxLayout(self.harmony_swatches_widget)
        self.harmony_swatches_layout.setSpacing(8)
        result_layout.addWidget(self.harmony_swatches_widget)
        
        # Add to palette button
        add_btn = QPushButton("Add All to Palette")
        add_btn.clicked.connect(self._add_harmony_to_palette)
        result_layout.addWidget(add_btn)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        # Generate initial harmony
        self._generate_harmony()
        
        return widget
    
    def _update_harmony_base(self) -> None:
        """Update the base color preview and regenerate harmony."""
        r = self.harmony_r_spin.value()
        g = self.harmony_g_spin.value()
        b = self.harmony_b_spin.value()
        
        self.harmony_base_preview.setStyleSheet(f"""
            background-color: rgb({r}, {g}, {b});
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        
        self._generate_harmony()
    
    def _pick_harmony_base_from_palette(self) -> None:
        """Pick a base color from the current palette."""
        if not self.parent_app or not self.parent_app.colors:
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_info(self, "No colors in palette to pick from", title="No Colors")
            else:
                QMessageBox.information(self, "No Colors", "No colors in palette to pick from")
            return
        
        # Use the first color from the palette
        rgb = self.parent_app.colors[0][0]
        self.harmony_r_spin.setValue(rgb[0])
        self.harmony_g_spin.setValue(rgb[1])
        self.harmony_b_spin.setValue(rgb[2])
    
    def _generate_harmony(self) -> None:
        """Generate color harmony based on current settings."""
        if not ColorHarmony:
            return
        
        r = self.harmony_r_spin.value()
        g = self.harmony_g_spin.value()
        b = self.harmony_b_spin.value()
        base_color = (r, g, b)
        
        # Get harmony type
        harmony_name = self.harmony_type_combo.currentText().lower()
        if "square" in harmony_name:
            harmony_name = "tetradic"
        elif "rectangle" in harmony_name:
            harmony_name = "compound"
        
        # Map to HarmonyType enum
        type_map = {
            "complementary": HarmonyType.COMPLEMENTARY,
            "triadic": HarmonyType.TRIADIC,
            "analogous": HarmonyType.ANALOGOUS,
            "split-complementary": HarmonyType.SPLIT_COMPLEMENTARY,
            "tetradic": HarmonyType.TETRADIC,
            "compound": HarmonyType.COMPOUND,
            "monochromatic": HarmonyType.MONOCHROMATIC,
        }
        
        harmony_type = type_map.get(harmony_name, HarmonyType.COMPLEMENTARY)
        
        # Update description
        desc = ColorHarmony.get_harmony_description(harmony_type)
        self.harmony_desc_label.setText(desc)
        
        # Generate colors
        colors = ColorHarmony.generate_harmony(base_color, harmony_type)
        self.harmony_colors = colors
        
        # Clear existing swatches
        while self.harmony_swatches_layout.count():
            item = self.harmony_swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create new swatches
        for idx, rgb in enumerate(colors):
            swatch = self._create_harmony_swatch(rgb, idx == 0)
            self.harmony_swatches_layout.addWidget(swatch)
        
        self.harmony_swatches_layout.addStretch()
    
    def _create_harmony_swatch(self, rgb: tuple, is_base: bool = False) -> QWidget:
        """Create a color swatch widget for harmony display."""
        widget = QWidget()
        widget.setFixedSize(70, 90)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Color box
        color_box = QLabel()
        color_box.setFixedSize(66, 50)
        border = f"3px solid {self._get_accent()}" if is_base else f"2px solid {PREVIEW_BORDER_THIN}"
        color_box.setStyleSheet(f"""
            background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]});
            border: {border};
            border-radius: 4px;
        """)
        layout.addWidget(color_box)
        
        # Hex label (use cache if available)
        if CACHE_AVAILABLE and ColorCache:
            hex_code = ColorCache.rgb_to_hex(rgb)
        else:
            hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        hex_label = QLabel(hex_code.upper())
        hex_label.setStyleSheet(StylesheetCache.get_monospace_stylesheet(9))
        hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hex_label)
        
        # Label (only show "Base" for base color)
        label = QLabel("Base" if is_base else "")
        label.setStyleSheet("font-size: 8px; color: gray;")  # Keep as inline - unique pattern
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        return widget
    
    def _add_harmony_to_palette(self) -> None:
        """Add all harmony colors to the main palette."""
        if not hasattr(self, 'harmony_colors') or not self.harmony_colors:
            return
        
        if not self.parent_app:
            return
        
        added = 0
        for rgb in self.harmony_colors:
            try:
                # Track in color history
                if hasattr(self.parent_app, 'color_history') and self.parent_app.color_history:
                    self.parent_app.color_history.add_color(rgb, source="harmony")
                
                # Use parent app's add_color method which handles HSL and Hilbert
                if self.parent_app.add_color(rgb):
                    added += 1
            except Exception as e:
                if logger:
                    logger.error(f"Failed to add harmony color: {e}")
        
        if added > 0:
            self.parent_app.refresh_color_display()
            if DIALOG_HELPER_AVAILABLE and DialogHelper:
                DialogHelper.show_info(
                    self, f"Added {added} harmony colors to palette",
                    title="Success"
                )
            else:
                QMessageBox.information(
                    self, "Success", 
                    f"Added {added} harmony colors to palette"
                )
            if logger:
                logger.success(f"Added {added} harmony colors to palette")
    
    # =========================================================================
    # ACCESSIBILITY TAB
    # =========================================================================
    
    def _create_accessibility_tab(self) -> QWidget:
        """Create the Accessibility tab for WCAG compliance checking."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Color Accessibility Checker")
        if CACHE_AVAILABLE and StylesheetCache:
            header.setStyleSheet(StylesheetCache.get_header_stylesheet())
        else:
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        desc = QLabel("Check WCAG contrast ratios and simulate color blindness")
        if CACHE_AVAILABLE and StylesheetCache:
            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)
        
        # Check if ColorAccessibility is available
        if not ColorAccessibility:
            no_module = QLabel("Accessibility module not available.\nPlace accessibility.py in core/ folder.")
            no_module.setStyleSheet(StylesheetCache.get_error_stylesheet())
            no_module.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_module)
            layout.addStretch()
            return widget
        
        # Contrast Checker Section
        contrast_group = QGroupBox("WCAG Contrast Checker")
        contrast_layout = QVBoxLayout(contrast_group)
        
        # Foreground/Background selection
        colors_layout = QHBoxLayout()
        
        # Foreground
        fg_layout = QVBoxLayout()
        fg_header = QHBoxLayout()
        fg_header.addWidget(QLabel("Foreground (Text)"))
        fg_header.addStretch()
        
        # Copy/Paste buttons for foreground
        fg_copy_btn = QPushButton("⧉")
        fg_copy_btn.setFixedSize(40, 32)
        fg_copy_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        fg_copy_btn.setToolTip("Copy foreground color (HEX)")
        fg_copy_btn.clicked.connect(self._copy_fg_color)
        fg_header.addWidget(fg_copy_btn)
        
        fg_paste_btn = QPushButton("⎘")
        fg_paste_btn.setFixedSize(40, 32)
        fg_paste_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        fg_paste_btn.setToolTip("Paste foreground color (HEX)")
        fg_paste_btn.clicked.connect(self._paste_fg_color)
        fg_header.addWidget(fg_paste_btn)
        
        fg_layout.addLayout(fg_header)
        
        self.access_fg_preview = QLabel("Aa")
        self.access_fg_preview.setFixedSize(80, 60)
        self.access_fg_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.access_fg_preview.setStyleSheet(f"""
            background-color: {CONTRAST_DEMO_BLACK_BG};
            color: {CONTRAST_DEMO_WHITE_FG};
            font-size: 24px;
            font-weight: bold;
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        fg_layout.addWidget(self.access_fg_preview)
        
        fg_rgb_layout = QHBoxLayout()
        self.access_fg_r = QSpinBox()
        self.access_fg_r.setRange(0, 255)
        self.access_fg_r.setValue(0)
        self.access_fg_r.valueChanged.connect(self._update_contrast_check)
        
        self.access_fg_g = QSpinBox()
        self.access_fg_g.setRange(0, 255)
        self.access_fg_g.setValue(0)
        self.access_fg_g.valueChanged.connect(self._update_contrast_check)
        
        self.access_fg_b = QSpinBox()
        self.access_fg_b.setRange(0, 255)
        self.access_fg_b.setValue(0)
        self.access_fg_b.valueChanged.connect(self._update_contrast_check)
        
        fg_rgb_layout.addWidget(self.access_fg_r)
        fg_rgb_layout.addWidget(self.access_fg_g)
        fg_rgb_layout.addWidget(self.access_fg_b)
        fg_layout.addLayout(fg_rgb_layout)
        
        colors_layout.addLayout(fg_layout)
        
        # Background
        bg_layout = QVBoxLayout()
        bg_header = QHBoxLayout()
        bg_header.addWidget(QLabel("Background"))
        bg_header.addStretch()
        
        # Copy/Paste buttons for background
        bg_copy_btn = QPushButton("⧉")
        bg_copy_btn.setFixedSize(40, 32)
        bg_copy_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        bg_copy_btn.setToolTip("Copy background color (HEX)")
        bg_copy_btn.clicked.connect(self._copy_bg_color)
        bg_header.addWidget(bg_copy_btn)
        
        bg_paste_btn = QPushButton("⎘")
        bg_paste_btn.setFixedSize(40, 32)
        bg_paste_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        bg_paste_btn.setToolTip("Paste background color (HEX)")
        bg_paste_btn.clicked.connect(self._paste_bg_color)
        bg_header.addWidget(bg_paste_btn)
        
        bg_layout.addLayout(bg_header)
        
        self.access_bg_preview = QLabel()
        self.access_bg_preview.setFixedSize(80, 60)
        self.access_bg_preview.setStyleSheet(f"""
            background-color: {CONTRAST_DEMO_WHITE_BG};
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        bg_layout.addWidget(self.access_bg_preview)
        
        bg_rgb_layout = QHBoxLayout()
        self.access_bg_r = QSpinBox()
        self.access_bg_r.setRange(0, 255)
        self.access_bg_r.setValue(255)
        self.access_bg_r.valueChanged.connect(self._update_contrast_check)
        
        self.access_bg_g = QSpinBox()
        self.access_bg_g.setRange(0, 255)
        self.access_bg_g.setValue(255)
        self.access_bg_g.valueChanged.connect(self._update_contrast_check)
        
        self.access_bg_b = QSpinBox()
        self.access_bg_b.setRange(0, 255)
        self.access_bg_b.setValue(255)
        self.access_bg_b.valueChanged.connect(self._update_contrast_check)
        
        bg_rgb_layout.addWidget(self.access_bg_r)
        bg_rgb_layout.addWidget(self.access_bg_g)
        bg_rgb_layout.addWidget(self.access_bg_b)
        bg_layout.addLayout(bg_rgb_layout)
        
        colors_layout.addLayout(bg_layout)
        
        # Preview
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(QLabel("Preview"))
        
        self.access_preview_box = QLabel("Sample Text")
        self.access_preview_box.setFixedSize(150, 60)
        self.access_preview_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.access_preview_box.setStyleSheet(f"""
            background-color: {CONTRAST_DEMO_WHITE_BG};
            color: {CONTRAST_DEMO_BLACK_FG};
            font-size: 14px;
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        preview_layout.addWidget(self.access_preview_box)
        preview_layout.addStretch()
        
        colors_layout.addLayout(preview_layout)
        colors_layout.addStretch()
        
        contrast_layout.addLayout(colors_layout)
        
        # Results
        self.contrast_ratio_label = QLabel("Contrast Ratio: 21.00:1")
        self.contrast_ratio_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        contrast_layout.addWidget(self.contrast_ratio_label)
        
        # WCAG levels
        wcag_layout = QGridLayout()
        
        self.wcag_aa_normal = QLabel("AA Normal Text")
        self.wcag_aa_large = QLabel("AA Large Text")
        self.wcag_aaa_normal = QLabel("AAA Normal Text")
        self.wcag_aaa_large = QLabel("AAA Large Text")
        
        for i, label in enumerate([self.wcag_aa_normal, self.wcag_aa_large, 
                                   self.wcag_aaa_normal, self.wcag_aaa_large]):
            label.setStyleSheet("padding: 5px; border-radius: 4px;")
            wcag_layout.addWidget(label, i // 2, i % 2)
        
        contrast_layout.addLayout(wcag_layout)
        layout.addWidget(contrast_group)
        
        # Color Blindness Simulation
        blindness_group = QGroupBox("Color Blindness Simulation")
        blindness_layout = QVBoxLayout(blindness_group)
        
        blindness_desc = QLabel("See how your colors appear to people with color vision deficiencies")
        if CACHE_AVAILABLE and StylesheetCache:
            blindness_desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            blindness_desc.setStyleSheet("color: gray; font-size: 11px;")
        blindness_layout.addWidget(blindness_desc)
        
        # Color to simulate
        sim_color_layout = QHBoxLayout()
        sim_color_layout.addWidget(QLabel("Color:"))
        
        self.sim_color_preview = QLabel()
        self.sim_color_preview.setFixedSize(40, 30)
        self.sim_color_preview.setStyleSheet(f"background-color: {self._get_accent()}; border: 1px solid {PREVIEW_BORDER_THIN};")
        sim_color_layout.addWidget(self.sim_color_preview)
        
        self.sim_r = QSpinBox()
        self.sim_r.setRange(0, 255)
        self.sim_r.setValue(191)
        self.sim_r.valueChanged.connect(self._update_blindness_sim)
        
        self.sim_g = QSpinBox()
        self.sim_g.setRange(0, 255)
        self.sim_g.setValue(145)
        self.sim_g.valueChanged.connect(self._update_blindness_sim)
        
        self.sim_b = QSpinBox()
        self.sim_b.setRange(0, 255)
        self.sim_b.setValue(70)
        self.sim_b.valueChanged.connect(self._update_blindness_sim)
        
        sim_color_layout.addWidget(self.sim_r)
        sim_color_layout.addWidget(self.sim_g)
        sim_color_layout.addWidget(self.sim_b)
        
        # Copy/Paste buttons for simulation color
        sim_copy_btn = QPushButton("⧉")
        sim_copy_btn.setFixedSize(40, 32)
        sim_copy_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sim_copy_btn.setToolTip("Copy simulation color (HEX)")
        sim_copy_btn.clicked.connect(self._copy_sim_color)
        sim_color_layout.addWidget(sim_copy_btn)
        
        sim_paste_btn = QPushButton("⎘")
        sim_paste_btn.setFixedSize(40, 32)
        sim_paste_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sim_paste_btn.setToolTip("Paste simulation color (HEX)")
        sim_paste_btn.clicked.connect(self._paste_sim_color)
        sim_color_layout.addWidget(sim_paste_btn)
        
        sim_color_layout.addStretch()
        
        blindness_layout.addLayout(sim_color_layout)
        
        # Simulation results
        self.blindness_results_widget = QWidget()
        self.blindness_results_layout = QHBoxLayout(self.blindness_results_widget)
        self.blindness_results_layout.setSpacing(10)
        blindness_layout.addWidget(self.blindness_results_widget)
        
        layout.addWidget(blindness_group)
        
        layout.addStretch()
        
        # Initial update
        self._update_contrast_check()
        self._update_blindness_sim()
        
        return widget
    
    def _update_contrast_check(self) -> None:
        """Update the contrast ratio display."""
        if not ColorAccessibility:
            return
        
        fg = (self.access_fg_r.value(), self.access_fg_g.value(), self.access_fg_b.value())
        bg = (self.access_bg_r.value(), self.access_bg_g.value(), self.access_bg_b.value())
        
        # Update previews
        self.access_fg_preview.setStyleSheet(f"""
            background-color: rgb({fg[0]}, {fg[1]}, {fg[2]});
            color: rgb({bg[0]}, {bg[1]}, {bg[2]});
            font-size: 24px;
            font-weight: bold;
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        
        self.access_bg_preview.setStyleSheet(f"""
            background-color: rgb({bg[0]}, {bg[1]}, {bg[2]});
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        
        self.access_preview_box.setStyleSheet(f"""
            background-color: rgb({bg[0]}, {bg[1]}, {bg[2]});
            color: rgb({fg[0]}, {fg[1]}, {fg[2]});
            font-size: 14px;
            border: 2px solid {PREVIEW_BORDER_THIN};
            border-radius: 4px;
        """)
        
        # Calculate contrast
        result = ColorAccessibility.check_contrast(fg, bg)
        
        # Update ratio display
        rating_color = ColorAccessibility.get_contrast_rating_color(result.ratio)
        self.contrast_ratio_label.setText(f"Contrast Ratio: {result.ratio:.2f}:1  ({result.rating_text})")
        self.contrast_ratio_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
            color: rgb({rating_color[0]}, {rating_color[1]}, {rating_color[2]});
        """)
        
        # Update WCAG levels
        def set_pass_fail(label, passes):
            if passes:
                label.setStyleSheet(
                    f"padding: 5px; border-radius: 4px; "
                    f"background-color: {STATUS_SUCCESS_BG}; "
                    f"color: {STATUS_SUCCESS_FG};"
                )
                label.setText(label.text().split(" - ")[0] + " - PASS")
            else:
                label.setStyleSheet(
                    f"padding: 5px; border-radius: 4px; "
                    f"background-color: {STATUS_ERROR_BG}; "
                    f"color: {STATUS_ERROR_FG};"
                )
                label.setText(label.text().split(" - ")[0] + " - FAIL")
        
        self.wcag_aa_normal.setText("AA Normal Text")
        self.wcag_aa_large.setText("AA Large Text")
        self.wcag_aaa_normal.setText("AAA Normal Text")
        self.wcag_aaa_large.setText("AAA Large Text")
        
        set_pass_fail(self.wcag_aa_normal, result.passes_aa_normal)
        set_pass_fail(self.wcag_aa_large, result.passes_aa_large)
        set_pass_fail(self.wcag_aaa_normal, result.passes_aaa_normal)
        set_pass_fail(self.wcag_aaa_large, result.passes_aaa_large)
    
    def _update_blindness_sim(self) -> None:
        """Update color blindness simulation."""
        if not ColorAccessibility or not ColorBlindnessType:
            return
        
        rgb = (self.sim_r.value(), self.sim_g.value(), self.sim_b.value())
        
        # Update color preview
        self.sim_color_preview.setStyleSheet(f"""
            background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]});
            border: 1px solid {PREVIEW_BORDER_THIN};
        """)
        
        # Clear existing results
        while self.blindness_results_layout.count():
            item = self.blindness_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Generate simulations
        simulations = [
            (ColorBlindnessType.NORMAL, "Normal"),
            (ColorBlindnessType.PROTANOPIA, "Protanopia"),
            (ColorBlindnessType.DEUTERANOPIA, "Deuteranopia"),
            (ColorBlindnessType.TRITANOPIA, "Tritanopia"),
            (ColorBlindnessType.ACHROMATOPSIA, "Achromatopsia"),
        ]
        
        for blindness_type, name in simulations:
            sim_rgb = ColorAccessibility.simulate_colorblindness(rgb, blindness_type)
            
            swatch = QWidget()
            swatch.setFixedSize(80, 80)
            swatch_layout = QVBoxLayout(swatch)
            swatch_layout.setContentsMargins(2, 2, 2, 2)
            swatch_layout.setSpacing(2)
            
            color_box = QLabel()
            color_box.setFixedSize(76, 50)
            color_box.setStyleSheet(f"""
                background-color: rgb({sim_rgb[0]}, {sim_rgb[1]}, {sim_rgb[2]});
                border: 2px solid {PREVIEW_BORDER_THIN};
                border-radius: 4px;
            """)
            swatch_layout.addWidget(color_box)
            
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 8px;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            swatch_layout.addWidget(name_label)
            
            self.blindness_results_layout.addWidget(swatch)
        
        self.blindness_results_layout.addStretch()
    
    # =========================================================================
    # ACCESSIBILITY COPY/PASTE METHODS
    # =========================================================================
    
    def _copy_fg_color(self) -> None:
        """Copy foreground color to clipboard."""
        r, g, b = self.access_fg_r.value(), self.access_fg_g.value(), self.access_fg_b.value()
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        clipboard = QApplication.clipboard()
        clipboard.setText(hex_color)
        if logger:
            logger.info(f"Copied foreground color: {hex_color}")
    
    def _paste_fg_color(self) -> None:
        """Paste color from clipboard to foreground."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        rgb = self._parse_color_text(text)
        if rgb:
            self.access_fg_r.setValue(rgb[0])
            self.access_fg_g.setValue(rgb[1])
            self.access_fg_b.setValue(rgb[2])
            if logger:
                logger.info(f"Pasted foreground color: {text}")
    
    def _copy_bg_color(self) -> None:
        """Copy background color to clipboard."""
        r, g, b = self.access_bg_r.value(), self.access_bg_g.value(), self.access_bg_b.value()
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        clipboard = QApplication.clipboard()
        clipboard.setText(hex_color)
        if logger:
            logger.info(f"Copied background color: {hex_color}")
    
    def _paste_bg_color(self) -> None:
        """Paste color from clipboard to background."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        rgb = self._parse_color_text(text)
        if rgb:
            self.access_bg_r.setValue(rgb[0])
            self.access_bg_g.setValue(rgb[1])
            self.access_bg_b.setValue(rgb[2])
            if logger:
                logger.info(f"Pasted background color: {text}")
    
    def _copy_sim_color(self) -> None:
        """Copy simulation color to clipboard."""
        r, g, b = self.sim_r.value(), self.sim_g.value(), self.sim_b.value()
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        clipboard = QApplication.clipboard()
        clipboard.setText(hex_color)
        if logger:
            logger.info(f"Copied simulation color: {hex_color}")
    
    def _paste_sim_color(self) -> None:
        """Paste color from clipboard to simulation."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        rgb = self._parse_color_text(text)
        if rgb:
            self.sim_r.setValue(rgb[0])
            self.sim_g.setValue(rgb[1])
            self.sim_b.setValue(rgb[2])
            if logger:
                logger.info(f"Pasted simulation color: {text}")
    
    def _parse_color_text(self, text: str) -> tuple[int, int, int] | None:
        """
        Parse color from text (HEX or RGB format).
        
        Supports:
            - #RRGGBB or RRGGBB
            - RGB(r, g, b)
            - r, g, b
        
        Returns:
            RGB tuple or None if parsing fails
        """
        import re
        
        text = text.strip().upper()
        
        # Try HEX format: #RRGGBB or RRGGBB
        hex_match = re.match(r'^#?([0-9A-F]{6})$', text)
        if hex_match:
            hex_str = hex_match.group(1)
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b)
        
        # Try RGB format: RGB(r, g, b) or r, g, b
        rgb_match = re.match(r'^RGB\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$', text)
        if rgb_match:
            r = min(255, int(rgb_match.group(1)))
            g = min(255, int(rgb_match.group(2)))
            b = min(255, int(rgb_match.group(3)))
            return (r, g, b)
        
        # Try simple comma-separated: r, g, b
        csv_match = re.match(r'^(\d+)\s*,\s*(\d+)\s*,\s*(\d+)$', text)
        if csv_match:
            r = min(255, int(csv_match.group(1)))
            g = min(255, int(csv_match.group(2)))
            b = min(255, int(csv_match.group(3)))
            return (r, g, b)
        
        return None
    
    # =========================================================================
    # SHORTCUTS TAB
    # =========================================================================
    
    def _create_shortcuts_tab(self) -> QWidget:
        """Create the Shortcuts tab with keyboard shortcuts reference."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Keyboard Shortcuts")
        if CACHE_AVAILABLE and StylesheetCache:
            header.setStyleSheet(StylesheetCache.get_header_stylesheet())
        else:
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        desc = QLabel("Quick reference for keyboard shortcuts")
        if CACHE_AVAILABLE and StylesheetCache:
            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())
        else:
            desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)
        
        # Shortcuts list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        shortcuts_layout = QVBoxLayout(scroll_content)
        shortcuts_layout.setSpacing(8)
        
        # Define shortcuts
        shortcuts = [
            ("File Operations", [
                ("Ctrl+O", "Upload Image"),
                ("Ctrl+S", "Save Colors as Image"),
                ("Ctrl+E", "Export Palette"),
            ]),
            ("Color Operations", [
                ("Ctrl+G", "Grab ALL Colors from image"),
                ("Ctrl+K", "Extract Dominant Colors"),
                ("Ctrl+Shift+C", "Screen Color Picker"),
                ("Ctrl+D", "Clear All Colors"),
            ]),
            ("View Controls", [
                ("Ctrl+0", "Reset Zoom/Pan"),
                ("Scroll Wheel", "Zoom In/Out"),
                ("Double-Click", "Pick color from pixel"),
                ("Click+Drag", "Select region for extraction"),
            ]),
            ("Application", [
                ("Ctrl+,", "Open Settings"),
                ("Ctrl+P", "Open Settings (alternate)"),
                ("Ctrl+/", "About Dialog"),
                ("F11", "Toggle Tooltips"),
                ("F12", "Toggle Debug Overlay"),
            ]),
        ]
        
        for section_name, section_shortcuts in shortcuts:
            # Section header
            section_header = QLabel(section_name)
            section_header.setStyleSheet(f"font-weight: bold; color: {self._get_accent()}; padding-top: 8px;")
            shortcuts_layout.addWidget(section_header)
            
            # Shortcuts in section
            for shortcut_key, shortcut_action in section_shortcuts:
                row = self._create_shortcut_row(shortcut_key, shortcut_action)
                shortcuts_layout.addLayout(row)
        
        shortcuts_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # Tip
        tip = QLabel("Tip: Use keyboard shortcuts for fastest workflow!")
        tip.setStyleSheet(f"color: {self._get_accent()}; font-style: italic; padding-top: 10px;")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        
        return widget
    
    def _create_shortcut_row(self, key: str, action: str) -> QHBoxLayout:
        """Create a row for displaying a keyboard shortcut."""
        row = QHBoxLayout()
        row.setSpacing(15)
        
        # Key label with styled background - wider to fit longer shortcuts
        key_label = QLabel(key)
        key_label.setMinimumWidth(100)
        key_label.setMaximumWidth(140)
        _t = self._get_theme()
        key_label.setStyleSheet(f"""
            background-color: {_t['pressed_bg']};
            color: {_t['text_primary']};
            padding: 4px 8px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-weight: bold;
        """)
        key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(key_label)
        
        # Action label
        action_label = QLabel(action)
        row.addWidget(action_label)
        row.addStretch()
        
        return row
    
    # =========================================================================
    # SETTINGS TAB
    # =========================================================================
    
    def _create_settings_tab(self) -> QWidget:
        """Create the Settings tab with application preferences."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(12)
        
        # === GENERAL PREFERENCES ===
        content_layout.addWidget(self._create_section_header("General Preferences"))
        
        # Theme preference
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Default Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setView(QListView())
        self.theme_combo.addItems(["Dark Mode", "Light Mode", "Image Mode"])
        self.theme_combo.setMinimumWidth(180)
        self.theme_combo.setToolTip("Select the default application theme")
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        content_layout.addLayout(theme_layout)
        
        # Auto-save session (linked to Sessions tab)
        self.autosave_session_check = QCheckBox("Auto-save session on exit")
        self.autosave_session_check.setToolTip("Automatically save colors when closing")
        content_layout.addWidget(self.autosave_session_check)
        
        # Sync with Sessions tab checkbox
        self.autosave_session_check.stateChanged.connect(self._sync_autosave_checkbox_from_general)
        
        # Auto-load session
        self.autoload_session_check = QCheckBox("Auto-load last session on startup")
        self.autoload_session_check.setToolTip("Restore colors from previous session")
        content_layout.addWidget(self.autoload_session_check)
        
        # Sync with Sessions tab checkbox
        self.autoload_session_check.stateChanged.connect(self._sync_autoload_checkbox_from_general)
        
        # === COLOR SETTINGS ===
        content_layout.addWidget(self._create_section_header("Color Settings"))
        
        # Max colors
        max_colors_layout = QHBoxLayout()
        max_colors_layout.addWidget(QLabel("Maximum Colors:"))
        self.max_colors_input = QLineEdit("333")
        self.max_colors_input.setMaximumWidth(80)
        self.max_colors_input.setToolTip("Maximum number of colors in palette (1-1000)")
        max_colors_layout.addWidget(self.max_colors_input)
        max_colors_layout.addStretch()
        content_layout.addLayout(max_colors_layout)
        
        # Default sort method
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Default Sort Method:"))
        self.sort_combo = QComboBox()
        self.sort_combo.setView(QListView())
        self.sort_combo.addItems(["Hilbert Curve", "HSL"])
        self.sort_combo.setMinimumWidth(180)
        self.sort_combo.setToolTip("How colors are sorted in the palette")
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        content_layout.addLayout(sort_layout)
        
        # Preserve colors
        self.preserve_colors_check = QCheckBox("Preserve colors when extracting new colors")
        self.preserve_colors_check.setToolTip("Keep existing colors when extracting from images")
        content_layout.addWidget(self.preserve_colors_check)
        
        # === EXPORT SETTINGS ===
        content_layout.addWidget(self._create_section_header("Export Settings"))
        
        # Default export format
        export_layout = QHBoxLayout()
        export_layout.addWidget(QLabel("Default Export Format:"))
        self.export_format_combo = QComboBox()
        self.export_format_combo.setView(QListView())
        self.export_format_combo.addItems([
            "PNG Image", "JPEG Image", "GIMP Palette (GPL)", 
            "Adobe Swatch (ASE)", "JSON Data", "CSS Variables"
        ])
        self.export_format_combo.setMinimumWidth(180)
        self.export_format_combo.setToolTip("Default format when exporting palettes")
        export_layout.addWidget(self.export_format_combo)
        export_layout.addStretch()
        content_layout.addLayout(export_layout)
        
        # === UI PREFERENCES ===
        content_layout.addWidget(self._create_section_header("UI Preferences"))
        
        # Show tooltips
        self.show_tooltips_check = QCheckBox("Show tooltips")
        self.show_tooltips_check.setToolTip("Display helpful tooltips on buttons and controls (F11)")
        content_layout.addWidget(self.show_tooltips_check)
        
        # Show debug overlay
        self.debug_overlay_check = QCheckBox("Show debug dimension overlay")
        self.debug_overlay_check.setToolTip("Display window dimensions in top-left corner (F12)")
        content_layout.addWidget(self.debug_overlay_check)
        
        # Remember window size
        self.remember_size_check = QCheckBox("Remember window size")
        self.remember_size_check.setToolTip("Restore window size on next launch")
        content_layout.addWidget(self.remember_size_check)
        
        # Remember window position
        self.remember_position_check = QCheckBox("Remember window position")
        self.remember_position_check.setToolTip("Restore window position on next launch")
        content_layout.addWidget(self.remember_position_check)
        
        content_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # === ACTION BUTTONS ===
        button_layout = QHBoxLayout()
        
        # Save Settings button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings_to_file)
        save_btn.setMinimumWidth(100)
        save_btn.setToolTip("Save current settings")
        button_layout.addWidget(save_btn)
        
        # Reset to Defaults button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_settings_to_defaults)
        reset_btn.setMinimumWidth(120)
        reset_btn.setToolTip("Reset all settings to default values")
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_settings)
        apply_btn.setMinimumWidth(90)
        apply_btn.setToolTip("Apply settings to application")
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_accent(self) -> str:
        """Return the correct brand gold for the current theme."""
        if self.parent_app and hasattr(self.parent_app, 'theme_manager'):
            is_dark = self.parent_app.theme_manager.current_theme in ('dark', 'image')
            return BRAND_GOLD if is_dark else BRAND_GOLD_DARK
        return BRAND_GOLD  # Default to dark gold

    def _get_theme(self) -> dict:
        """Return the current theme color dict for theme-aware styling."""
        if self.parent_app and hasattr(self.parent_app, 'theme_manager'):
            return self.parent_app.theme_manager.get_current_theme()
        from utils.config import DARK_THEME_COLORS
        return DARK_THEME_COLORS

    def _create_section_header(self, text: str) -> QLabel:
        """Create a section header label."""
        header = QLabel(text)
        accent = self._get_accent()
        header.setStyleSheet(f"""
            font-weight: bold;
            font-size: 13px;
            color: {accent};
            padding-top: 10px;
            padding-bottom: 5px;
        """)
        return header
    
    def _create_section_divider(self) -> QFrame:
        """Create a horizontal divider line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        # 'border_hover' is the divider key used across the app — the previous
        # 'border_light' key never existed in any theme dict, causing the
        # fallback hex to silently render in every theme.
        divider_color = self._get_theme()['border_hover']
        line.setStyleSheet(f"color: {divider_color};")
        return line
    
    # =========================================================================
    # SETTINGS MANAGEMENT
    # =========================================================================
    
    def _load_settings_into_ui(self) -> None:
        """Load settings from file into UI controls."""
        if not self.settings_manager:
            return
        
        settings = self.settings_manager.settings
        
        # Theme
        theme = settings.get("theme", "image")
        theme_map = {"dark": 0, "light": 1, "image": 2}
        self.theme_combo.setCurrentIndex(theme_map.get(theme, 0))
        
        # Session options (in both tabs)
        self.autosave_session_check.setChecked(settings.get("auto_save_session", True))
        self.autoload_session_check.setChecked(settings.get("auto_load_session", False))
        
        # Also update Sessions tab checkboxes if they exist
        if hasattr(self, 'session_autosave_check'):
            self.session_autosave_check.setChecked(settings.get("auto_save_session", True))
        if hasattr(self, 'session_autoload_check'):
            self.session_autoload_check.setChecked(settings.get("auto_load_session", False))
        
        # Max colors
        self.max_colors_input.setText(str(settings.get("max_colors", 333)))
        
        # Sort method
        sort_method = settings.get("default_sort_method", "hilbert")
        self.sort_combo.setCurrentIndex(0 if sort_method == "hilbert" else 1)
        
        # Preserve colors
        self.preserve_colors_check.setChecked(settings.get("preserve_colors", False))
        
        # Export format
        export_format = settings.get("export_format", "png")
        format_map = {"png": 0, "jpeg": 1, "gpl": 2, "ase": 3, "json": 4, "css": 5}
        self.export_format_combo.setCurrentIndex(format_map.get(export_format, 0))
        
        # UI preferences
        self.show_tooltips_check.setChecked(settings.get("show_tooltips", True))
        self.debug_overlay_check.setChecked(settings.get("show_debug_overlay", True))
        self.remember_size_check.setChecked(settings.get("remember_window_size", True))
        self.remember_position_check.setChecked(settings.get("remember_window_position", False))
        
        if logger:
            logger.debug("Settings loaded into UI")
    
    def _save_ui_to_settings(self, skip_theme: bool = False) -> None:
        """Save UI control values to settings."""
        if not self.settings_manager:
            return
        
        # Theme
        if not skip_theme:
            theme_map = {0: "dark", 1: "light", 2: "image"}
            self.settings_manager.set("theme", theme_map.get(self.theme_combo.currentIndex(), "image"))
        
        # Session options (sync both tabs)
        # Use session_autosave_check if available (Sessions tab), otherwise use autosave_session_check (General tab)
        auto_save_enabled = False
        if hasattr(self, 'session_autosave_check') and self.session_autosave_check:
            auto_save_enabled = self.session_autosave_check.isChecked()
        elif hasattr(self, 'autosave_session_check') and self.autosave_session_check:
            auto_save_enabled = self.autosave_session_check.isChecked()
        self.settings_manager.set("auto_save_session", auto_save_enabled)
        
        auto_load_enabled = False
        if hasattr(self, 'session_autoload_check') and self.session_autoload_check:
            auto_load_enabled = self.session_autoload_check.isChecked()
        elif hasattr(self, 'autoload_session_check') and self.autoload_session_check:
            auto_load_enabled = self.autoload_session_check.isChecked()
        self.settings_manager.set("auto_load_session", auto_load_enabled)
        
        # Max colors (validate)
        try:
            max_colors = int(self.max_colors_input.text())
            max_colors = max(1, min(1000, max_colors))
            self.max_colors_input.setText(str(max_colors))
        except ValueError:
            max_colors = 333
            self.max_colors_input.setText("333")
        self.settings_manager.set("max_colors", max_colors)
        
        # Sort method
        sort_method = "hilbert" if self.sort_combo.currentIndex() == 0 else "hsl"
        self.settings_manager.set("default_sort_method", sort_method)
        
        # Preserve colors
        self.settings_manager.set("preserve_colors", self.preserve_colors_check.isChecked())
        
        # Export format
        format_map = {0: "png", 1: "jpeg", 2: "gpl", 3: "ase", 4: "json", 5: "css"}
        self.settings_manager.set("export_format", format_map.get(self.export_format_combo.currentIndex(), "png"))
        
        # UI preferences
        self.settings_manager.set("show_tooltips", self.show_tooltips_check.isChecked())
        self.settings_manager.set("show_debug_overlay", self.debug_overlay_check.isChecked())
        self.settings_manager.set("remember_window_size", self.remember_size_check.isChecked())
        self.settings_manager.set("remember_window_position", self.remember_position_check.isChecked())
        
        # Save to file
        self.settings_manager.save_settings()
        
        if logger:
            logger.success("Settings saved")
    
    def _save_settings_to_file(self) -> None:
        """Save settings to file."""
        self._save_ui_to_settings(skip_theme=True)
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            DialogHelper.show_info(self, "Settings have been saved successfully.", title="Settings Saved")
        else:
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
    
    def _reset_settings_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            confirmed = DialogHelper.confirm(
                self, "Reset all settings to default values?\nThis cannot be undone.",
                title="Reset Settings"
            )
        else:
            reply = QMessageBox.question(
                self, "Reset Settings",
                "Reset all settings to default values?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            confirmed = (reply == QMessageBox.StandardButton.Yes)
        
        if confirmed:
            if self.settings_manager:
                self.settings_manager.reset_to_defaults()
                self._load_settings_into_ui()
                if DIALOG_HELPER_AVAILABLE and DialogHelper:
                    DialogHelper.show_info(self, "Settings have been reset to defaults.", title="Reset Complete")
                else:
                    QMessageBox.information(self, "Reset Complete", "Settings have been reset to defaults.")
                if logger:
                    logger.info("Settings reset to defaults")
    
    def _apply_settings(self) -> None:
        """Apply settings and emit signals."""
        # Save settings
        self._save_ui_to_settings(skip_theme=True)
        
        # Emit signals for changed settings
        try:
            max_colors = int(self.max_colors_input.text())
            self.settings_changed.emit("max_colors", max_colors)
        except ValueError:
            pass
        
        sort_method = "hilbert" if self.sort_combo.currentIndex() == 0 else "hsl"
        self.settings_changed.emit("default_sort_method", sort_method)
        
        self.settings_changed.emit("preserve_colors", self.preserve_colors_check.isChecked())
        self.settings_changed.emit("show_tooltips", self.show_tooltips_check.isChecked())
        self.settings_changed.emit("show_debug_overlay", self.debug_overlay_check.isChecked())
        
        # Handle theme change
        theme_map = {0: "dark", 1: "light", 2: "image"}
        selected_theme = theme_map.get(self.theme_combo.currentIndex(), "image")
        
        # Get current theme from parent app
        current_theme = "image"
        if self.parent_app and hasattr(self.parent_app, 'theme_manager'):
            current_theme = self.parent_app.theme_manager.current_theme
        
        if selected_theme != current_theme:
            self.theme_change_requested.emit(selected_theme)
        
        if logger:
            logger.success("Settings applied")
        
        if DIALOG_HELPER_AVAILABLE and DialogHelper:
            DialogHelper.show_info(self, "Settings have been applied.", title="Applied")
        else:
            QMessageBox.information(self, "Applied", "Settings have been applied.")
    
    # =========================================================================
    # THEME
    # =========================================================================
    
    def _apply_theme(self) -> None:
        """Apply theme styling to the dialog."""
        self.update_theme()
    
    def update_theme(self) -> None:
        """Update/apply theme styling to the dialog. Can be called externally."""
        from PyQt6.QtGui import QPalette
        
        # Get active theme dict (fallback to dark)
        if self.parent_app and hasattr(self.parent_app, 'theme_manager'):
            theme = self.parent_app.theme_manager.get_current_theme()
        else:
            from utils.config import DARK_THEME_COLORS
            theme = DARK_THEME_COLORS
        
        # Override Qt system highlight palette to match brand selection colors
        palette = self.palette()
        highlight_bg = theme['selected_bg']
        highlight_fg = theme['text_on_accent']
        if CACHE_AVAILABLE and QColorCache:
            hl_bg_q = QColorCache.get(highlight_bg)
            hl_fg_q = QColorCache.get(highlight_fg)
        else:
            hl_bg_q = QColor(highlight_bg)
            hl_fg_q = QColor(highlight_fg)
        palette.setColor(QPalette.ColorRole.Highlight, hl_bg_q)
        palette.setColor(QPalette.ColorRole.HighlightedText, hl_fg_q)
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight, hl_bg_q)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, hl_bg_q)
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText, hl_fg_q)
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, hl_fg_q)
        self.setPalette(palette)
        
        # Build the entire dialog stylesheet from theme keys
        self.setStyleSheet(self._build_dialog_stylesheet(theme))
    
    @staticmethod
    def _build_dialog_stylesheet(theme: dict) -> str:
        """
        Build the complete settings-panel stylesheet from a theme dict.
        
        All colors come from the theme — no hardcoded values. This method is
        shared between dark, light, and image modes; each theme dict provides
        its own brand-appropriate values.
        """
        return f"""
            QDialog {{
                background-color: {theme['dialog_bg']};
                color: {theme['text_primary']};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['tab_border']};
                background-color: {theme['dialog_bg']};
            }}
            QTabWidget::tab-bar {{
                alignment: center;
            }}
            QTabBar {{
                qproperty-drawBase: 0;
            }}
            QTabBar::tab {{
                background-color: {theme['tab_bg']};
                color: {theme['text_primary']};
                padding: 8px 0px;
                border: 1px solid {theme['tab_border']};
                border-bottom: none;
                margin-right: 0px;
                min-width: 80px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['tab_selected_bg']};
                color: {theme['tab_selected_text']};
                border-bottom: 2px solid {theme['tab_indicator']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {theme['tab_hover_bg']};
                color: {theme['tab_hover_text']};
            }}
            QLabel {{
                color: {theme['text_primary']};
            }}
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['button_border']};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover_bg']};
                color: {theme['button_hover_text']};
                border: 1px solid {theme['button_hover_border']};
            }}
            QPushButton:pressed {{
                background-color: {theme['button_pressed_bg']};
                color: {theme['button_pressed_text']};
                border: 1px solid {theme['button_pressed_bg']};
            }}
            QPushButton:disabled {{
                background-color: {theme['pressed_bg']};
                color: {theme['text_disabled']};
                border: 1px solid {theme['border_default']};
            }}
            QComboBox {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['input_border']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QComboBox:hover {{
                border-color: {theme['border_focus']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                selection-background-color: {theme['hover_bg']};
                selection-color: {theme['text_accent']};
                border: 1px solid {theme['input_border']};
                outline: 0px;
                show-decoration-selected: 1;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                padding: 6px 10px;
                min-height: 22px;
                border: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {theme['hover_bg']};
                color: {theme['text_accent']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {theme['hover_bg']};
                color: {theme['text_accent']};
            }}
            QComboBox::item {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                padding: 6px 10px;
            }}
            QComboBox::item:selected {{
                background-color: {theme['hover_bg']};
                color: {theme['text_accent']};
            }}
            QCheckBox {{
                color: {theme['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {theme['checkbox_border']};
                border-radius: 3px;
                background-color: {theme['checkbox_bg']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme['checkbox_hover_border']};
                background-color: {theme['hover_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme['checkbox_checked_bg']};
                border-color: {theme['checkbox_checked_border']};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {theme['accent_hover']};
                border-color: {theme['accent_hover']};
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['input_border']};
                padding: 4px;
                border-radius: 4px;
                selection-background-color: {theme['selected_bg']};
                selection-color: {theme['text_on_accent']};
            }}
            QLineEdit:focus {{
                border-color: {theme['border_focus']};
            }}
            QSpinBox {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['input_border']};
                padding: 4px;
                border-radius: 4px;
                selection-background-color: {theme['selected_bg']};
                selection-color: {theme['text_on_accent']};
            }}
            QSpinBox:focus {{
                border-color: {theme['border_focus']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {theme['border_hover']};
                border: none;
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {theme['text_accent']};
            }}
            QListWidget {{
                background-color: {theme['list_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border_hover']};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {theme['list_selected_bg']};
                color: {theme['list_selected_text']};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {theme['list_hover_bg']};
                color: {theme['list_hover_text']};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {theme['scrollbar_bg']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['scrollbar_handle']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme['text_accent']};
            }}
            QGroupBox {{
                color: {theme['text_primary']};
                border: 1px solid {theme['border_hover']};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                color: {theme['text_accent']};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
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
            QMenu::icon {{
                padding-left: 6px;
            }}
        """
    
    def closeEvent(self, event) -> None:
        """Handle dialog close - cleanup signal connections."""
        # Disconnect all tracked signals to prevent memory leaks
        if self.signal_manager:
            self.signal_manager.disconnect_all(quiet=True)
        
        super().closeEvent(event)
    
    def showEvent(self, event) -> None:
        """Handle dialog show - sync UI preferences with main app state."""
        super().showEvent(event)
        self.sync_ui_preferences()
    
    def sync_ui_preferences(self) -> None:
        """Sync UI preference checkboxes with main app state."""
        if not self.parent_app:
            return
        
        try:
            # Sync tooltips checkbox
            if hasattr(self.parent_app, 'tooltips_enabled'):
                self.show_tooltips_check.setChecked(self.parent_app.tooltips_enabled)
            
            # Sync debug overlay checkbox
            if hasattr(self.parent_app, 'debug_label') and self.parent_app.debug_label:
                self.debug_overlay_check.setChecked(self.parent_app.debug_label.isVisible())
            
            if logger:
                logger.debug("UI preferences synced with main app")
        except Exception as e:
            if logger:
                logger.error(f"Error syncing UI preferences: {e}")
    
    def update_tooltips_checkbox(self, enabled: bool) -> None:
        """Update the tooltips checkbox state (called from main app)."""
        try:
            self.show_tooltips_check.setChecked(enabled)
        except Exception as e:
            if logger:
                logger.error(f"Error updating tooltips checkbox: {e}")
    
    def update_debug_overlay_checkbox(self, visible: bool) -> None:
        """Update the debug overlay checkbox state (called from main app)."""
        try:
            self.debug_overlay_check.setChecked(visible)
        except Exception as e:
            if logger:
                logger.error(f"Error updating debug overlay checkbox: {e}")