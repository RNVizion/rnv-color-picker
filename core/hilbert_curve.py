"""
Hilbert Curve implementation for 3D color space sorting.

The Hilbert curve is a space-filling curve that maps multi-dimensional space
to one dimension while preserving locality. This implementation is used for
sorting colors in RGB space to create smooth color transitions.

Python 3.13 optimized.
"""

from utils.logger import Logger

logger = Logger("HilbertCurve")


class HilbertCurve:
    """Hilbert Curve implementation for 3D color space sorting."""
    
    @staticmethod
    def hilbert_index(x: float, y: float, z: float, order: int = 8) -> int:
        """
        Calculate Hilbert curve index for 3D coordinates.
        
        Args:
            x: X coordinate (0.0 to 1.0)
            y: Y coordinate (0.0 to 1.0)
            z: Z coordinate (0.0 to 1.0)
            order: Hilbert curve order (default: 8)
            
        Returns:
            Integer index along the Hilbert curve
        """
        def interleave(xi: int, yi: int, zi: int) -> int:
            """Interleave bits of three integers."""
            result = 0
            for i in range(order):
                result |= ((xi & (1 << i)) << (2 * i)) | \
                         ((yi & (1 << i)) << (2 * i + 1)) | \
                         ((zi & (1 << i)) << (2 * i + 2))
            return result
        
        max_val = (1 << order) - 1
        xi = int(x * max_val)
        yi = int(y * max_val)
        zi = int(z * max_val)
        
        return interleave(xi, yi, zi)
    
    @staticmethod
    def rgb_to_hilbert(rgb: tuple[int, int, int], order: int = 8) -> int:
        """
        Convert RGB color to Hilbert curve index.
        
        Args:
            rgb: RGB color tuple (0-255, 0-255, 0-255)
            order: Hilbert curve order (default: 8)
            
        Returns:
            Integer index for sorting along Hilbert curve
        """
        r, g, b = (x / 255.0 for x in rgb)
        return HilbertCurve.hilbert_index(r, g, b, order)
