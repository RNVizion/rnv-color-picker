"""
Font loading utilities for RNV Color Picker.

Loads the bundled Montserrat-Black font from resources/fonts/, with a
graceful fallback to the system default (Arial) if the file cannot be
found or registered with Qt.

Python 3.13 optimized - using modern type hints.
"""

import os
from PyQt6.QtGui import QFont, QFontDatabase

from utils.logger import Logger

logger = Logger("FontLoader")


# Filename of the bundled font, expected under resources/fonts/
_FONT_FILENAME = "Montserrat-Black.ttf"

# Fallback font family used when the bundled file cannot be loaded
_FALLBACK_FAMILY = "Arial"


def load_embedded_font(default_size: int = 10) -> QFont:
    """
    Load the bundled Montserrat-Black font from resources/fonts/.

    Priority:
    1. Try loading from resources/fonts/Montserrat-Black.ttf
    2. Fallback to system Arial

    Args:
        default_size: Font size in points (default: 10)

    Returns:
        QFont object with the loaded font
    """
    # Search known locations for the bundled font file
    possible_paths = [
        os.path.join(os.getcwd(), "resources", "fonts", _FONT_FILENAME),
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources", "fonts", _FONT_FILENAME,
        ),
    ]

    for font_path in possible_paths:
        if os.path.exists(font_path):
            try:
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        if logger:
                            logger.success("Loaded Montserrat-Black (file)")
                        return QFont(families[0], default_size)
            except Exception as e:
                if logger:
                    logger.warning(f"Failed to load font from file: {e}")

    # Fallback to system font
    if logger:
        logger.warning(f"Using fallback font ({_FALLBACK_FAMILY})")
    return QFont(_FALLBACK_FAMILY, default_size)


def get_font(
    size: int = 10,
    bold: bool = False,
    family: str | None = None,
) -> QFont:
    """
    Get a QFont with specified properties.

    Args:
        size: Font size in points
        bold: Whether font should be bold
        family: Font family name (None = use app default)

    Returns:
        QFont object
    """
    if family:
        font = QFont(family, size)
    else:
        font = load_embedded_font(size)

    if bold:
        font.setBold(True)

    return font