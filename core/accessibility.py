"""
Color Accessibility Utilities.

Provides WCAG contrast ratio checking and color blindness simulation.
Supports: Protanopia, Deuteranopia, Tritanopia, Achromatopsia.
"""

import colorsys
from enum import Enum
from dataclasses import dataclass

from utils.logger import Logger
from utils.cache import ColorCache

logger = Logger("Accessibility")
CACHE_AVAILABLE = True


class ColorBlindnessType(Enum):
    """Types of color blindness for simulation."""
    NORMAL = "Normal Vision"
    PROTANOPIA = "Protanopia (Red-Blind)"
    DEUTERANOPIA = "Deuteranopia (Green-Blind)"
    TRITANOPIA = "Tritanopia (Blue-Blind)"
    ACHROMATOPSIA = "Achromatopsia (Monochromacy)"


class WCAGLevel(Enum):
    """WCAG compliance levels."""
    FAIL = "Fail"
    AA_LARGE = "AA Large Text"
    AA = "AA"
    AAA = "AAA"


@dataclass
class ContrastResult:
    """Result of a contrast ratio calculation."""
    ratio: float
    level: WCAGLevel
    passes_aa_normal: bool
    passes_aa_large: bool
    passes_aaa_normal: bool
    passes_aaa_large: bool
    
    @property
    def rating_text(self) -> str:
        """Get human-readable rating."""
        if self.ratio >= 7.0:
            return "Excellent"
        elif self.ratio >= 4.5:
            return "Good"
        elif self.ratio >= 3.0:
            return "Fair (Large Text Only)"
        else:
            return "Poor"


class ColorAccessibility:
    """
    Color accessibility utilities for WCAG compliance and 
    color blindness simulation.
    """
    
    # WCAG 2.1 contrast ratio thresholds
    WCAG_AA_NORMAL = 4.5    # Normal text
    WCAG_AA_LARGE = 3.0     # Large text (18pt+ or 14pt bold)
    WCAG_AAA_NORMAL = 7.0   # Enhanced contrast
    WCAG_AAA_LARGE = 4.5    # Enhanced for large text
    
    # Color blindness simulation matrices (LMS color space transformations)
    # Based on Brettel, Viénot, and Mollon (1997)
    COLORBLIND_MATRICES = {
        ColorBlindnessType.PROTANOPIA: [
            [0.567, 0.433, 0.000],
            [0.558, 0.442, 0.000],
            [0.000, 0.242, 0.758]
        ],
        ColorBlindnessType.DEUTERANOPIA: [
            [0.625, 0.375, 0.000],
            [0.700, 0.300, 0.000],
            [0.000, 0.300, 0.700]
        ],
        ColorBlindnessType.TRITANOPIA: [
            [0.950, 0.050, 0.000],
            [0.000, 0.433, 0.567],
            [0.000, 0.475, 0.525]
        ],
    }
    
    @staticmethod
    def get_relative_luminance(rgb: tuple[int, int, int]) -> float:
        """
        Calculate relative luminance of a color per WCAG 2.1.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            Relative luminance (0-1)
        """
        def linearize(channel: int) -> float:
            """Convert sRGB channel to linear RGB."""
            c = channel / 255.0
            if c <= 0.03928:
                return c / 12.92
            else:
                return ((c + 0.055) / 1.055) ** 2.4
        
        r, g, b = rgb
        r_lin = linearize(r)
        g_lin = linearize(g)
        b_lin = linearize(b)
        
        # Luminance formula per WCAG
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
    
    @staticmethod
    def calculate_contrast_ratio(
        color1: tuple[int, int, int],
        color2: tuple[int, int, int]
    ) -> float:
        """
        Calculate WCAG contrast ratio between two colors.
        
        Args:
            color1: First RGB color
            color2: Second RGB color
            
        Returns:
            Contrast ratio (1 to 21)
        """
        lum1 = ColorAccessibility.get_relative_luminance(color1)
        lum2 = ColorAccessibility.get_relative_luminance(color2)
        
        # Lighter color should be L1
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    @staticmethod
    def check_contrast(
        foreground: tuple[int, int, int],
        background: tuple[int, int, int]
    ) -> ContrastResult:
        """
        Check WCAG contrast compliance between foreground and background.
        
        Args:
            foreground: Text/foreground color
            background: Background color
            
        Returns:
            ContrastResult with compliance details
        """
        ratio = ColorAccessibility.calculate_contrast_ratio(foreground, background)
        
        passes_aa_normal = ratio >= ColorAccessibility.WCAG_AA_NORMAL
        passes_aa_large = ratio >= ColorAccessibility.WCAG_AA_LARGE
        passes_aaa_normal = ratio >= ColorAccessibility.WCAG_AAA_NORMAL
        passes_aaa_large = ratio >= ColorAccessibility.WCAG_AAA_LARGE
        
        # Determine overall level
        if passes_aaa_normal:
            level = WCAGLevel.AAA
        elif passes_aa_normal:
            level = WCAGLevel.AA
        elif passes_aa_large:
            level = WCAGLevel.AA_LARGE
        else:
            level = WCAGLevel.FAIL
        
        return ContrastResult(
            ratio=round(ratio, 2),
            level=level,
            passes_aa_normal=passes_aa_normal,
            passes_aa_large=passes_aa_large,
            passes_aaa_normal=passes_aaa_normal,
            passes_aaa_large=passes_aaa_large
        )
    
    @staticmethod
    def simulate_colorblindness(
        rgb: tuple[int, int, int],
        blindness_type: ColorBlindnessType
    ) -> tuple[int, int, int]:
        """
        Simulate how a color appears to someone with color blindness.
        
        Args:
            rgb: Original RGB color
            blindness_type: Type of color blindness to simulate
            
        Returns:
            Simulated RGB color
        """
        if blindness_type == ColorBlindnessType.NORMAL:
            return rgb
        
        if blindness_type == ColorBlindnessType.ACHROMATOPSIA:
            # Complete color blindness - convert to grayscale
            # Using luminance weights
            r, g, b = rgb
            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
            return (gray, gray, gray)
        
        # Get transformation matrix
        matrix = ColorAccessibility.COLORBLIND_MATRICES.get(blindness_type)
        if not matrix:
            return rgb
        
        # Apply transformation
        r, g, b = [c / 255.0 for c in rgb]
        
        new_r = matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b
        new_g = matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b
        new_b = matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b
        
        # Clamp and convert back to 0-255
        new_r = max(0, min(1, new_r))
        new_g = max(0, min(1, new_g))
        new_b = max(0, min(1, new_b))
        
        return (int(new_r * 255), int(new_g * 255), int(new_b * 255))
    
    @staticmethod
    def get_optimal_text_color(
        background: tuple[int, int, int]
    ) -> tuple[int, int, int]:
        """
        Determine optimal text color (black or white) for a background.
        
        Args:
            background: Background RGB color
            
        Returns:
            Black (0,0,0) or White (255,255,255)
        """
        luminance = ColorAccessibility.get_relative_luminance(background)
        
        # If background is dark, use white text; otherwise black
        if luminance < 0.179:
            return (255, 255, 255)
        else:
            return (0, 0, 0)
    
    @staticmethod
    def suggest_accessible_color(
        target_color: tuple[int, int, int],
        background: tuple[int, int, int],
        target_ratio: float = 4.5
    ) -> tuple[int, int, int]:
        """
        Suggest an accessible version of a color against a background.
        
        Adjusts the lightness of the target color until it meets
        the target contrast ratio.
        
        Args:
            target_color: Color to adjust
            background: Background color
            target_ratio: Minimum contrast ratio to achieve
            
        Returns:
            Adjusted RGB color that meets the contrast requirement
        """
        # Check if already accessible
        current_ratio = ColorAccessibility.calculate_contrast_ratio(
            target_color, background
        )
        if current_ratio >= target_ratio:
            return target_color
        
        # Convert to HSL for lightness adjustment
        r, g, b = [c / 255.0 for c in target_color]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        
        bg_luminance = ColorAccessibility.get_relative_luminance(background)
        
        # Determine direction to adjust
        # If background is dark, we need lighter colors
        # If background is light, we need darker colors
        direction = 1 if bg_luminance < 0.5 else -1
        
        # Binary search for optimal lightness
        best_color = target_color
        step = 0.05
        
        for _ in range(20):  # Max iterations
            new_l = max(0, min(1, l + (direction * step)))
            
            # Convert back to RGB
            new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
            new_color = (int(new_r * 255), int(new_g * 255), int(new_b * 255))
            
            new_ratio = ColorAccessibility.calculate_contrast_ratio(
                new_color, background
            )
            
            if new_ratio >= target_ratio:
                best_color = new_color
                break
            
            l = new_l
        
        return best_color
    
    @staticmethod
    def get_contrast_rating_color(ratio: float) -> tuple[int, int, int]:
        """
        Get a color representing the contrast rating for UI display.
        
        Args:
            ratio: Contrast ratio
            
        Returns:
            RGB color (green = good, yellow = fair, red = poor)
        """
        if ratio >= 7.0:
            return (76, 175, 80)    # Green - AAA
        elif ratio >= 4.5:
            return (139, 195, 74)   # Light Green - AA
        elif ratio >= 3.0:
            return (255, 193, 7)    # Yellow/Amber - AA Large only
        else:
            return (244, 67, 54)    # Red - Fail
    
    @staticmethod
    def format_contrast_ratio(ratio: float) -> str:
        """Format contrast ratio for display."""
        return f"{ratio:.2f}:1"


# Convenience functions for external use
def check_wcag_contrast(
    foreground: tuple[int, int, int],
    background: tuple[int, int, int]
) -> ContrastResult:
    """Check WCAG contrast compliance."""
    return ColorAccessibility.check_contrast(foreground, background)


def simulate_color_blindness(
    rgb: tuple[int, int, int],
    blindness_type: str
) -> tuple[int, int, int]:
    """
    Simulate color blindness by type name.
    
    Args:
        rgb: RGB color tuple
        blindness_type: One of 'normal', 'protanopia', 'deuteranopia', 
                       'tritanopia', 'achromatopsia'
    """
    type_map = {
        'normal': ColorBlindnessType.NORMAL,
        'protanopia': ColorBlindnessType.PROTANOPIA,
        'deuteranopia': ColorBlindnessType.DEUTERANOPIA,
        'tritanopia': ColorBlindnessType.TRITANOPIA,
        'achromatopsia': ColorBlindnessType.ACHROMATOPSIA,
    }
    
    blindness = type_map.get(blindness_type.lower(), ColorBlindnessType.NORMAL)
    return ColorAccessibility.simulate_colorblindness(rgb, blindness)