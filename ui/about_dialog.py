# -*- coding: utf-8 -*-
"""
About Dialog for RNV Color Picker.

Displays application information, features, credits, and keyboard shortcuts.
Activated by Ctrl+/ shortcut.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QScrollArea, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QColor, QPalette
import sys
import os

from utils.logger import Logger
from utils.cache import QColorCache, StylesheetCache
from utils.config import APP_NAME, APP_VERSION, APP_TAGLINE, BRAND_GOLD, BRAND_GOLD_DARK

logger = Logger("AboutDialog")
CACHE_AVAILABLE = True


class AboutDialog(QDialog):
    """
    About dialog showing application information in a tabbed interface.
    
    Tabs:
    - About: App info, description, system info
    - Features: Feature overview organized by category
    - Shortcuts: Keyboard shortcuts reference
    - Credits: Acknowledgments and tech stack
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(f"About {APP_NAME}")
        self.setModal(True)
        # Use MSWindowsFixedSizeDialogHint to prevent redraw glitch on Windows
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setFixedSize(650, 520)
        
        # Delete dialog when closed to prevent state corruption on reopen
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        self._build_ui()
        self._apply_theme()
        
        if logger:
            logger.success("About dialog initialized")
    
    def _build_ui(self) -> None:
        """Build the about dialog UI with tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 15)
        layout.setSpacing(10)
        
        # ===== HEADER SECTION =====
        self.header_widget = QWidget()
        _theme = self._get_theme()
        self.header_widget.setStyleSheet(
            f"background-color: {_theme['pressed_bg']}; padding: 10px;"
        )
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Logo - use icon image
        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        
        icon_loaded = False
        
        # Try to get icon from parent window first
        if self.parent() and self.parent().windowIcon() and not self.parent().windowIcon().isNull():
            pixmap = self.parent().windowIcon().pixmap(96, 96)
            if not pixmap.isNull():
                logo_label.setPixmap(pixmap)
                icon_loaded = True
        
        # Fallback: try to load from file
        if not icon_loaded:
            base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "resources", "icons", "icon.png")
            
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        96, 96,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    logo_label.setPixmap(scaled_pixmap)
                    icon_loaded = True
        
        # Final fallback to text if icon not found
        if not icon_loaded:
            logo_label.setText("RNV")
            logo_label.setStyleSheet(f"""
                font-size: 32px;
                font-weight: bold;
                color: {self._get_accent()};
                background: transparent;
                padding: 5px 15px;
            """)
        
        header_layout.addWidget(logo_label)
        
        # Title and version
        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(15, 0, 0, 0)
        title_layout.setSpacing(2)
        
        self.name_label = QLabel(APP_NAME)
        self.name_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {_theme['text_primary']}; background: transparent;"
        )
        title_layout.addWidget(self.name_label)
        
        self.version_label = QLabel(f"Version {APP_VERSION}")
        self.version_label.setStyleSheet(f"font-size: 11px; color: {self._get_accent()}; background: transparent;")
        title_layout.addWidget(self.version_label)
        
        self.tagline_label = QLabel(APP_TAGLINE)
        self.tagline_label.setStyleSheet(
            f"font-size: 10px; color: {_theme['text_muted']}; background: transparent;"
        )
        title_layout.addWidget(self.tagline_label)
        
        header_layout.addWidget(title_widget)
        header_layout.addStretch()
        
        layout.addWidget(self.header_widget)
        
        # ===== TAB WIDGET =====
        self.tab_widget = QTabWidget()
        # Don't use documentMode - it can cause the white line on some platforms
        self.tab_widget.setDocumentMode(False)
        
        self.tab_widget.addTab(self._create_about_tab(), "About")
        self.tab_widget.addTab(self._create_features_tab(), "Features")
        self.tab_widget.addTab(self._create_shortcuts_tab(), "Shortcuts")
        self.tab_widget.addTab(self._create_credits_tab(), "Credits")
        
        layout.addWidget(self.tab_widget)
        
        # ===== CLOSE BUTTON =====
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 0, 20, 0)
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.close)
        _theme = self._get_theme()
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_theme['button_bg']};
                color: {_theme['button_text']};
                border: 1px solid {_theme['button_border']};
                padding: 8px 25px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {_theme['button_hover_bg']};
                color: {_theme['button_hover_text']};
                border: 1px solid {_theme['button_hover_border']};
            }}
            QPushButton:pressed {{
                background-color: {_theme['button_pressed_bg']};
                color: {_theme['button_pressed_text']};
                border: 1px solid {_theme['button_pressed_bg']};
            }}
            QPushButton:disabled {{
                background-color: {_theme['pressed_bg']};
                color: {_theme['text_disabled']};
                border: 1px solid {_theme['button_border']};
            }}
        """)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
    
    def _create_about_tab(self) -> QWidget:
        """Create the About tab with app description and system info."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # App description header
        desc_header = QLabel("Professional Color Extraction Application")
        desc_header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent()};")
        layout.addWidget(desc_header)
        
        # Description text
        desc_text = QLabel(
            "RNV Color Picker is a desktop application for extracting and managing "
            "color palettes from images. It uses advanced algorithms to help artists, "
            "designers, and color enthusiasts create precise color collections."
        )
        desc_text.setWordWrap(True)
        desc_text.setStyleSheet("font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc_text)
        
        # Core Capabilities
        cap_header = QLabel("Core Capabilities:")
        cap_header.setStyleSheet("font-weight: bold; font-size: 12px; padding-top: 10px;")
        layout.addWidget(cap_header)
        
        capabilities = [
            "Color Extraction - Extract all unique colors from any image",
            "Dominant Colors - K-means clustering for key color detection",
            "Screen Color Picker - Sample colors from anywhere on screen",
            "Hilbert Curve Sorting - Visual harmony through mathematical sorting",
            "Color Harmonies - Generate complementary, triadic, and more",
            "Accessibility Tools - WCAG contrast checker and colorblind simulation",
            "Export Formats - ASE, ACO, GPL, JSON, CSS, and 10+ more formats",
            "Session Management - Save and restore your color palettes",
        ]
        
        for cap in capabilities:
            cap_label = QLabel(f"   •  {cap}")
            cap_label.setStyleSheet("font-size: 11px; padding: 1px 0;")
            layout.addWidget(cap_label)
        
        layout.addStretch()
        
        # System Information
        layout.addWidget(self._create_divider())
        
        sys_header = QLabel("System Information:")
        sys_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(sys_header)
        
        # Get system info
        try:
            from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            qt_version = QT_VERSION_STR
            pyqt_version = PYQT_VERSION_STR
        except ImportError:
            qt_version = "Unknown"
            pyqt_version = "Unknown"
        
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        platform = sys.platform
        
        sys_info = QWidget()
        sys_layout = QGridLayout(sys_info)
        sys_layout.setContentsMargins(10, 5, 10, 5)
        sys_layout.setSpacing(5)
        
        info_items = [
            ("Python:", python_version),
            ("PyQt6:", pyqt_version),
            ("Qt:", qt_version),
            ("Platform:", platform),
        ]
        
        muted = self._get_theme()['text_muted']
        for row, (label, value) in enumerate(info_items):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
            val = QLabel(value)
            val.setStyleSheet(f"font-size: 11px; color: {muted};")
            sys_layout.addWidget(lbl, row, 0)
            sys_layout.addWidget(val, row, 1)
        
        sys_layout.setColumnStretch(1, 1)
        layout.addWidget(sys_info)
        
        return widget
    
    def _create_features_tab(self) -> QWidget:
        """Create the Features tab with categorized feature list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("Feature Overview")
        header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent()};")
        layout.addWidget(header)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        features_layout = QVBoxLayout(scroll_content)
        features_layout.setSpacing(12)
        
        # Feature categories
        feature_categories = [
            ("Color Extraction", [
                ("Grab All Colors", "Extract every unique color from loaded image"),
                ("Dominant Colors", "K-means clustering identifies key colors"),
                ("Selection Extraction", "Drag to select region for color sampling"),
                ("Real-time Preview", "See extracted colors instantly"),
            ]),
            ("Screen Color Picker", [
                ("Global Picking", "Sample colors from any application"),
                ("Magnified Preview", "Zoomed view for precise selection"),
                ("Color History", "Track recently picked colors"),
            ]),
            ("Color Tools", [
                ("Hilbert Curve Sorting", "Mathematical sorting for visual harmony"),
                ("Color Harmonies", "Complementary, triadic, split-complementary, etc."),
                ("Accessibility Checker", "WCAG contrast ratios and guidelines"),
                ("Colorblind Simulation", "Preview for different vision types"),
            ]),
            ("Session & Export", [
                ("Session Management", "Save and restore your palettes"),
                ("Auto-Save", "Never lose your work"),
                ("15+ Export Formats", "ASE, ACO, GPL, JSON, CSS, SCSS, and more"),
                ("Color History", "Track all colors you've picked"),
            ]),
            ("Themes & Display", [
                ("Dark Mode", "Easy on the eyes for long sessions"),
                ("Light Mode", "Clean, bright interface"),
                ("Image Mode", "Custom background from your images"),
            ]),
        ]
        
        for category, features in feature_categories:
            # Category header
            cat_label = QLabel(f"# {category}")
            cat_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {self._get_accent()}; padding-top: 5px;")
            features_layout.addWidget(cat_label)
            
            # Features in category
            for title, desc in features:
                feat_label = QLabel(f"   •  {title} - {desc}")
                feat_label.setStyleSheet("font-size: 11px; padding: 1px 0;")
                feat_label.setWordWrap(True)
                features_layout.addWidget(feat_label)
        
        features_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_shortcuts_tab(self) -> QWidget:
        """Create the Shortcuts tab with categorized shortcuts."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("Keyboard Shortcuts")
        header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent()};")
        layout.addWidget(header)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        shortcuts_layout = QVBoxLayout(scroll_content)
        shortcuts_layout.setSpacing(8)
        
        # Shortcut categories
        shortcut_categories = [
            ("File Operations", [
                ("Ctrl+O", "Open/Upload Image"),
                ("Ctrl+S", "Save Color Swatch"),
                ("Ctrl+E", "Export Palette"),
            ]),
            ("Color Operations", [
                ("Ctrl+G", "Grab All Colors from Image"),
                ("Ctrl+K", "Extract Dominant Colors"),
                ("Ctrl+Shift+C", "Screen Color Picker"),
                ("Ctrl+D", "Clear All Colors"),
            ]),
            ("Application", [
                ("Ctrl+,", "Open Settings & Features Panel"),
                ("Ctrl+P", "Open Settings & Features Panel (Alt)"),
                ("Ctrl+/", "Open About Dialog (This Window)"),
            ]),
            ("Debug & Display", [
                ("F11", "Toggle Tooltips On/Off"),
                ("F12", "Toggle Debug Overlay"),
            ]),
            ("Image Navigation", [
                ("Mouse Wheel", "Zoom In/Out"),
                ("Click & Drag", "Pan Image"),
                ("Double Click", "Pick Color from Pixel"),
                ("Shift + Drag", "Select Region for Extraction"),
            ]),
            ("Color Swatches", [
                ("Right Click", "Context Menu (Copy, Remove, Lock)"),
                ("Click Lock Icon", "Lock/Unlock Color"),
            ]),
        ]
        
        for category, shortcuts in shortcut_categories:
            # Category header
            cat_label = QLabel(category)
            cat_label.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {self._get_accent()}; padding-top: 8px;")
            shortcuts_layout.addWidget(cat_label)
            
            # Shortcuts grid
            muted = self._get_theme()['text_muted']
            for key, action in shortcuts:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(5, 2, 5, 2)
                row_layout.setSpacing(20)
                
                key_label = QLabel(key)
                key_label.setFixedWidth(100)
                key_label.setStyleSheet(f"font-size: 11px; color: {muted};")
                row_layout.addWidget(key_label)
                
                action_label = QLabel(action)
                action_label.setStyleSheet("font-size: 11px;")
                row_layout.addWidget(action_label)
                row_layout.addStretch()
                
                shortcuts_layout.addWidget(row_widget)
        
        shortcuts_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_credits_tab(self) -> QWidget:
        """Create the Credits tab with acknowledgments."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Credits & Acknowledgments")
        header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent()};")
        layout.addWidget(header)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        credits_layout = QVBoxLayout(scroll_content)
        credits_layout.setSpacing(10)
        
        # Development
        dev_header = QLabel("Development")
        dev_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        credits_layout.addWidget(dev_header)
        
        dev_text = QLabel(
            "RNV Color Picker was created with passion for color science and "
            "practical tools for artists and designers."
        )
        dev_text.setWordWrap(True)
        dev_text.setStyleSheet("font-size: 11px; padding-left: 10px;")
        credits_layout.addWidget(dev_text)
        
        # Technologies
        tech_header = QLabel("Technologies")
        tech_header.setStyleSheet("font-weight: bold; font-size: 12px; padding-top: 10px;")
        credits_layout.addWidget(tech_header)
        
        tech_grid = QWidget()
        tech_layout = QGridLayout(tech_grid)
        tech_layout.setContentsMargins(10, 5, 10, 5)
        tech_layout.setSpacing(5)
        
        technologies = [
            ("Framework:", "PyQt6"),
            ("Language:", "Python 3"),
            ("Image Processing:", "Pillow (PIL)"),
            ("Color Science:", "NumPy, scikit-learn"),
        ]
        
        tech_muted = self._get_theme()['text_muted']
        for row, (label, value) in enumerate(technologies):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
            val = QLabel(value)
            val.setStyleSheet(f"font-size: 11px; color: {tech_muted};")
            tech_layout.addWidget(lbl, row, 0)
            tech_layout.addWidget(val, row, 1)
        
        tech_layout.setColumnStretch(1, 1)
        credits_layout.addWidget(tech_grid)
        
        # Color Science References
        ref_header = QLabel("Color Science References")
        ref_header.setStyleSheet("font-weight: bold; font-size: 12px; padding-top: 10px;")
        credits_layout.addWidget(ref_header)
        
        references = [
            "Hilbert Curve - Space-filling curve for color sorting",
            "CIE LAB Color Space - Perceptually uniform color model",
            "K-means Clustering - Dominant color extraction algorithm",
            "WCAG Guidelines - Web accessibility contrast standards",
        ]
        
        for ref in references:
            ref_label = QLabel(f"   •  {ref}")
            ref_label.setStyleSheet("font-size: 11px;")
            credits_layout.addWidget(ref_label)
        
        # Special Thanks
        thanks_header = QLabel("Special Thanks")
        thanks_header.setStyleSheet("font-weight: bold; font-size: 12px; padding-top: 10px;")
        credits_layout.addWidget(thanks_header)
        
        thanks = [
            "The PyQt community for excellent documentation",
            "Color science researchers and educators",
            "Beta testers and early adopters",
            "Everyone who provided feedback and suggestions",
        ]
        
        for thank in thanks:
            thank_label = QLabel(f"   •  {thank}")
            thank_label.setStyleSheet("font-size: 11px;")
            credits_layout.addWidget(thank_label)
        
        credits_layout.addStretch()
        
        # Footer — professional brand-aligned signature
        footer = QLabel(
            f"\n{APP_NAME}\n"
            f"Extracting colors with precision for the creative community\n"
            f"© 2026 RNV Development. All rights reserved."
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"font-size: 11px; color: {self._get_accent()}; padding-top: 15px;"
        )
        credits_layout.addWidget(footer)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_divider(self) -> QFrame:
        """Create a horizontal divider."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        divider_color = self._get_theme()['border_hover']
        line.setStyleSheet(f"color: {divider_color};")
        return line
    
    def _get_accent(self) -> str:
        """Return the correct brand gold for the current theme."""
        try:
            if self.parent() and hasattr(self.parent(), 'theme_manager'):
                is_dark = self.parent().theme_manager.current_theme in ('dark', 'image')
                return BRAND_GOLD if is_dark else BRAND_GOLD_DARK
        except Exception:
            pass
        return BRAND_GOLD  # Default to dark gold

    def _get_theme(self) -> dict:
        """Return the current theme color dict for theme-aware styling."""
        try:
            if self.parent() and hasattr(self.parent(), 'theme_manager'):
                return self.parent().theme_manager.get_current_theme()
        except Exception:
            pass
        # Fallback to dark theme values if parent theme unavailable
        from utils.config import DARK_THEME_COLORS
        return DARK_THEME_COLORS

    def _apply_theme(self) -> None:
        """Apply theme styling to the dialog — all colors from theme dict."""
        theme = self._get_theme()
        
        # Tab styling block — uses theme keys for full brand consistency
        tab_style = f"""
            QTabWidget {{
                background-color: {theme['dialog_bg']};
                border: none;
            }}
            QTabWidget::pane {{
                border: none;
                border-top: none;
                background-color: {theme['dialog_bg']};
                padding: 5px;
                top: -1px;
            }}
            QTabBar {{
                background-color: {theme['dialog_bg']};
                border: none;
                border-bottom: none;
            }}
            QTabBar::tab {{
                background-color: {theme['tab_bg']};
                color: {theme['text_muted']};
                padding: 8px 18px;
                margin-right: 2px;
                border: none;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['dialog_bg']};
                color: {theme['tab_selected_text']};
                border: none;
                border-bottom: 2px solid {theme['dialog_bg']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {theme['tab_hover_bg']};
                color: {theme['tab_hover_text']};
            }}
            QTabBar::scroller {{
                border: none;
            }}
            QTabBar QToolButton {{
                border: none;
                background-color: {theme['dialog_bg']};
            }}
        """
        
        # Header widget (the "RNV Color Picker" banner)
        self.header_widget.setStyleSheet(
            f"background-color: {theme['pressed_bg']}; padding: 10px;"
        )
        self.name_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; "
            f"color: {theme['text_primary']}; background: transparent;"
        )
        self.version_label.setStyleSheet(
            f"font-size: 11px; color: {theme['text_accent']}; background: transparent;"
        )
        self.tagline_label.setStyleSheet(
            f"font-size: 10px; color: {theme['text_muted']}; background: transparent;"
        )
        
        # Main dialog stylesheet
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['dialog_bg']};
                color: {theme['text_primary']};
            }}
            QLabel {{
                color: {theme['text_primary']};
            }}
            QScrollArea {{
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            {tab_style}
        """)


def show_about_dialog(parent=None) -> None:
    """Convenience function to show the about dialog."""
    dialog = AboutDialog(parent)
    dialog.exec()