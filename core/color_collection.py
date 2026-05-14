"""
Optimized color collection with O(1) lookups and batch operations.

Provides:
- O(1) color existence checking via set
- Batch add operations with deferred sorting
- Efficient color removal
- Lock state management

Python 3.13 optimized.
"""

from dataclasses import dataclass, field
from typing import Iterator, Callable

from utils.logger import Logger
from utils.cache import ColorCache

logger = Logger("ColorCollection")


@dataclass(slots=True)
class ColorEntry:
    """
    Single color entry with all metadata.
    
    Uses __slots__ for memory efficiency with 333 colors.
    """
    rgb: tuple[int, int, int]
    hsl: tuple[int, int, int]
    hilbert_idx: int
    is_locked: bool = False
    
    def __hash__(self) -> int:
        return hash(self.rgb)
    
    def __eq__(self, other) -> bool:
        if isinstance(other, ColorEntry):
            return self.rgb == other.rgb
        return False
    
    @property
    def hex_code(self) -> str:
        """Get hex color code."""
        return ColorCache.rgb_to_hex(self.rgb)
    
    def to_tuple(self) -> tuple[tuple[int, int, int], tuple[int, int, int], int, bool]:
        """Convert to legacy tuple format for compatibility."""
        return (self.rgb, self.hsl, self.hilbert_idx, self.is_locked)


class ColorCollection:
    """
    High-performance color collection with O(1) operations.
    
    Key features:
    - O(1) color existence checking via internal set
    - Batch operations with deferred index computation
    - Efficient iteration and sorting
    - Memory-efficient storage
    
    Example:
        colors = ColorCollection(max_size=333)
        colors.add((255, 0, 0))  # Returns True
        colors.add((255, 0, 0))  # Returns False (duplicate)
        colors.add_batch([(0, 255, 0), (0, 0, 255)])
        colors.sort_by_hilbert()
    """
    
    def __init__(self, max_size: int = 333):
        """
        Initialize color collection.
        
        Args:
            max_size: Maximum number of colors allowed
        """
        self._max_size = max_size
        self._colors: list[ColorEntry] = []
        self._color_set: set[tuple[int, int, int]] = set()
        self._sorted = False
        self._sort_key: str = "hilbert"
    
    @property
    def max_size(self) -> int:
        """Maximum collection size."""
        return self._max_size
    
    def __len__(self) -> int:
        """Get number of colors."""
        return len(self._colors)
    
    def __iter__(self) -> Iterator[ColorEntry]:
        """Iterate over colors."""
        return iter(self._colors)
    
    def __contains__(self, rgb: tuple[int, int, int]) -> bool:
        """O(1) color existence check."""
        return rgb in self._color_set
    
    def __getitem__(self, index: int) -> ColorEntry:
        """Get color by index."""
        return self._colors[index]
    
    @property
    def is_full(self) -> bool:
        """Check if collection is at max capacity."""
        return len(self._colors) >= self._max_size
    
    @property
    def remaining_slots(self) -> int:
        """Get number of remaining slots."""
        return self._max_size - len(self._colors)
    
    def add(self, rgb: tuple[int, int, int]) -> bool:
        """
        Add a single color.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            True if added, False if duplicate or full
        """
        # Validate
        rgb = self._validate_rgb(rgb)
        
        # Check capacity and duplicates (O(1))
        if self.is_full or rgb in self._color_set:
            return False
        
        # Compute metadata
        hsl = ColorCache.rgb_to_hsl(rgb)
        hilbert_idx = ColorCache.hilbert_index(rgb)
        
        # Add to collection
        entry = ColorEntry(rgb=rgb, hsl=hsl, hilbert_idx=hilbert_idx)
        self._colors.append(entry)
        self._color_set.add(rgb)
        self._sorted = False
        
        return True
    
    def add_batch(
        self,
        rgb_list: list[tuple[int, int, int]],
        progress_callback: Callable[[int, int], None] | None = None
    ) -> tuple[int, int]:
        """
        Add multiple colors efficiently.
        
        Uses batch processing to minimize overhead.
        
        Args:
            rgb_list: List of RGB tuples
            progress_callback: Optional callback(current, total)
            
        Returns:
            Tuple of (added_count, skipped_duplicates)
        """
        added = 0
        skipped = 0
        total = len(rgb_list)
        
        for i, rgb in enumerate(rgb_list):
            if self.is_full:
                break
            
            rgb = self._validate_rgb(rgb)
            
            if rgb in self._color_set:
                skipped += 1
                continue
            
            # Compute metadata
            hsl = ColorCache.rgb_to_hsl(rgb)
            hilbert_idx = ColorCache.hilbert_index(rgb)
            
            # Add entry
            entry = ColorEntry(rgb=rgb, hsl=hsl, hilbert_idx=hilbert_idx)
            self._colors.append(entry)
            self._color_set.add(rgb)
            added += 1
            
            # Progress callback
            if progress_callback and i % 100 == 0:
                progress_callback(i, total)
        
        if added > 0:
            self._sorted = False
        
        return added, skipped
    
    def remove(self, rgb: tuple[int, int, int]) -> bool:
        """
        Remove a color by RGB value.
        
        Args:
            rgb: RGB tuple to remove
            
        Returns:
            True if removed, False if not found
        """
        if rgb not in self._color_set:
            return False
        
        # Find and remove entry
        for i, entry in enumerate(self._colors):
            if entry.rgb == rgb:
                self._colors.pop(i)
                self._color_set.remove(rgb)
                return True
        
        return False
    
    def remove_entry(self, entry: ColorEntry) -> bool:
        """Remove a specific color entry."""
        return self.remove(entry.rgb)
    
    def clear(self, keep_locked: bool = True) -> int:
        """
        Clear colors from collection.
        
        Args:
            keep_locked: If True, preserve locked colors
            
        Returns:
            Number of colors removed
        """
        if keep_locked:
            locked = [c for c in self._colors if c.is_locked]
            removed = len(self._colors) - len(locked)
            self._colors = locked
            self._color_set = {c.rgb for c in locked}
        else:
            removed = len(self._colors)
            self._colors.clear()
            self._color_set.clear()
        
        self._sorted = False
        return removed
    
    def set_lock_state(self, rgb: tuple[int, int, int], locked: bool) -> bool:
        """
        Set lock state for a color.
        
        Args:
            rgb: RGB tuple
            locked: New lock state
            
        Returns:
            True if found and updated
        """
        for entry in self._colors:
            if entry.rgb == rgb:
                entry.is_locked = locked
                return True
        return False
    
    def get_locked_count(self) -> int:
        """Get number of locked colors."""
        return sum(1 for c in self._colors if c.is_locked)
    
    def sort(self, method: str = "hilbert") -> None:
        """
        Sort colors in place.
        
        Args:
            method: "hilbert" or "hsl"
        """
        self._sort_key = method
        
        if method == "hilbert":
            self._colors.sort(key=lambda c: c.hilbert_idx)
        else:  # hsl
            self._colors.sort(key=lambda c: (c.hsl[0], c.hsl[2], c.hsl[1]))
        
        self._sorted = True
    
    def sort_by_hilbert(self) -> None:
        """Sort by Hilbert curve index."""
        self.sort("hilbert")
    
    def sort_by_hsl(self) -> None:
        """Sort by HSL values."""
        self.sort("hsl")
    
    def ensure_sorted(self) -> None:
        """Sort if not already sorted."""
        if not self._sorted:
            self.sort(self._sort_key)
    
    def to_legacy_format(self) -> list[tuple[tuple[int, int, int], tuple[int, int, int], int, bool]]:
        """
        Convert to legacy tuple format for compatibility.
        
        Returns:
            List of (rgb, hsl, hilbert_idx, is_locked) tuples
        """
        return [entry.to_tuple() for entry in self._colors]
    
    def to_palette_format(self) -> list[tuple[tuple[int, int, int], int]]:
        """
        Convert to palette export format.
        
        Returns:
            List of (rgb, weight) tuples
        """
        return [(entry.rgb, 50) for entry in self._colors]
    
    @staticmethod
    def _validate_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """Validate and clamp RGB values."""
        return (
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2])))
        )
    
    def get_statistics(self) -> dict:
        """Get collection statistics."""
        return {
            'count': len(self._colors),
            'max_size': self._max_size,
            'remaining': self.remaining_slots,
            'locked': self.get_locked_count(),
            'sorted': self._sorted,
            'sort_method': self._sort_key,
        }
