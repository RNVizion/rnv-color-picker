"""
Worker threads for CPU-intensive operations.

Provides non-blocking execution of:
- Color extraction from images
- K-means dominant color clustering
- Palette export operations

Python 3.13 optimized.
"""

from PyQt6.QtCore import QThread, pyqtSignal, QMutex
import numpy as np
from sklearn.cluster import KMeans
from typing import Callable
from dataclasses import dataclass

from utils.logger import Logger
from utils.error_handler import ErrorHandler, ErrorContext
from utils.signal_manager import SignalConnectionManager
from utils.cache import ColorCache

logger = Logger("Workers")
ERROR_HANDLER_AVAILABLE = True
SIGNAL_MANAGER_AVAILABLE = True
CACHE_AVAILABLE = True


@dataclass
class WorkerResult:
    """Result container for worker operations."""
    success: bool
    data: any
    error: str | None = None
    

class ColorExtractionWorker(QThread):
    """
    Worker thread for extracting unique colors from images.
    
    Signals:
        progress: Emits (current, total) progress updates
        finished: Emits WorkerResult with extracted colors
        error: Emits error message string
    """
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(object)     # WorkerResult
    error = pyqtSignal(str)
    
    def __init__(
        self, 
        pixels: np.ndarray,
        max_colors: int = 333,
        parent=None
    ):
        super().__init__(parent)
        self.pixels = pixels
        self.max_colors = max_colors
        self._cancelled = False
        self._mutex = QMutex()
        if logger:
            logger.debug("ColorExtractionWorker initialized")
    
    def cancel(self) -> None:
        """Request cancellation of the operation."""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        self._mutex.lock()
        result = self._cancelled
        self._mutex.unlock()
        return result
    
    def run(self) -> None:
        """Extract unique colors in background thread."""
        try:
            if logger:
                logger.info("Starting color extraction...")
            self.progress.emit(0, 100)
            
            # Reshape pixels
            flat_pixels = self.pixels.reshape(-1, 3)
            total_pixels = len(flat_pixels)
            
            self.progress.emit(10, 100)
            
            if self.is_cancelled():
                self.finished.emit(WorkerResult(False, None, "Cancelled"))
                return
            
            # Get unique colors with counts
            unique_colors, counts = np.unique(
                flat_pixels, axis=0, return_counts=True
            )
            
            self.progress.emit(60, 100)
            
            if self.is_cancelled():
                self.finished.emit(WorkerResult(False, None, "Cancelled"))
                return
            
            # Sort by frequency (most common first)
            sorted_idx = np.argsort(counts)[::-1]
            unique_colors = unique_colors[sorted_idx]
            
            self.progress.emit(80, 100)
            
            # Limit to max colors
            if len(unique_colors) > self.max_colors:
                unique_colors = unique_colors[:self.max_colors]
            
            # Convert to list of tuples
            color_list = [tuple(map(int, rgb)) for rgb in unique_colors]
            
            self.progress.emit(100, 100)
            
            if logger:
                logger.success(f"Extracted {len(color_list)} colors from {total_pixels} pixels")
            
            self.finished.emit(WorkerResult(
                success=True,
                data={
                    'colors': color_list,
                    'total_unique': len(unique_colors),
                    'total_pixels': total_pixels
                }
            ))
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="extracting colors from image",
                    show_traceback=True
                )
            else:
                if logger:
                    logger.error(f"Color extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(WorkerResult(False, None, str(e)))


class DominantColorWorker(QThread):
    """
    Worker thread for K-means dominant color extraction.
    
    Signals:
        progress: Emits (current, total) progress updates
        finished: Emits WorkerResult with dominant colors
        error: Emits error message string
    """
    
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        pixels: np.ndarray,
        num_clusters: int = 5,
        max_iterations: int = 100,
        parent=None
    ):
        super().__init__(parent)
        self.pixels = pixels
        self.num_clusters = num_clusters
        self.max_iterations = max_iterations
        self._cancelled = False
        self._mutex = QMutex()
        if logger:
            logger.debug(f"DominantColorWorker initialized (clusters={num_clusters})")
    
    def cancel(self) -> None:
        """Request cancellation."""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()
    
    def is_cancelled(self) -> bool:
        """Check cancellation status."""
        self._mutex.lock()
        result = self._cancelled
        self._mutex.unlock()
        return result
    
    def run(self) -> None:
        """Run K-means clustering in background."""
        try:
            if logger:
                logger.info(f"Starting K-means clustering ({self.num_clusters} clusters)...")
            self.progress.emit(0, 100)
            
            # Reshape pixels
            flat_pixels = self.pixels.reshape(-1, 3)
            
            self.progress.emit(10, 100)
            
            if self.is_cancelled():
                self.finished.emit(WorkerResult(False, None, "Cancelled"))
                return
            
            # Run K-means with iteration limit for safety
            kmeans = KMeans(
                n_clusters=self.num_clusters,
                random_state=0,
                n_init=10,
                max_iter=self.max_iterations
            )
            
            self.progress.emit(20, 100)
            
            labels = kmeans.fit_predict(flat_pixels)
            
            self.progress.emit(80, 100)
            
            if self.is_cancelled():
                self.finished.emit(WorkerResult(False, None, "Cancelled"))
                return
            
            # Get cluster centers and counts
            centers = kmeans.cluster_centers_.astype(int)
            counts = np.bincount(labels)
            
            # Sort by frequency
            sorted_idx = np.argsort(counts)[::-1]
            
            # Convert to list of tuples
            color_list = [tuple(map(int, centers[idx])) for idx in sorted_idx]
            
            self.progress.emit(100, 100)
            
            if logger:
                logger.success(f"K-means extracted {len(color_list)} dominant colors")
            
            self.finished.emit(WorkerResult(
                success=True,
                data={
                    'colors': color_list,
                    'counts': [int(counts[idx]) for idx in sorted_idx]
                }
            ))
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="K-means dominant color extraction",
                    show_traceback=True
                )
            else:
                if logger:
                    logger.error(f"K-means extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(WorkerResult(False, None, str(e)))


class ImageLoadWorker(QThread):
    """
    Worker thread for loading and processing images.
    
    Signals:
        progress: Emits progress percentage
        finished: Emits WorkerResult with processed image data
        error: Emits error message
    """
    
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    # Maximum dimension for display (larger images downsampled)
    MAX_DISPLAY_DIMENSION = 3840
    # Maximum pixels for color extraction
    MAX_EXTRACTION_PIXELS = 500 * 500
    
    def __init__(
        self,
        file_path: str,
        parent=None
    ):
        super().__init__(parent)
        self.file_path = file_path
        self._cancelled = False
        if logger:
            logger.debug(f"ImageLoadWorker initialized for: {file_path}")
    
    def cancel(self) -> None:
        self._cancelled = True
    
    def run(self) -> None:
        """Load and optionally downsample image."""
        try:
            from PIL import Image
            
            if logger:
                logger.info("Loading image...")
            self.progress.emit(0, 100)
            
            # Load image
            img = Image.open(self.file_path)
            original_size = img.size
            
            self.progress.emit(30, 100)
            
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            self.progress.emit(50, 100)
            
            # Check if downsampling needed for display
            max_dim = max(img.size)
            if max_dim > self.MAX_DISPLAY_DIMENSION:
                ratio = self.MAX_DISPLAY_DIMENSION / max_dim
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                if logger:
                    logger.debug(f"Resized image to {new_size[0]}x{new_size[1]}")
            
            self.progress.emit(70, 100)
            
            # Create extraction-sized version
            extraction_img = img
            if img.width * img.height > self.MAX_EXTRACTION_PIXELS:
                # Downsample for color extraction
                ratio = (self.MAX_EXTRACTION_PIXELS / (img.width * img.height)) ** 0.5
                extract_size = (int(img.width * ratio), int(img.height * ratio))
                extraction_img = img.resize(extract_size, Image.Resampling.LANCZOS)
            
            self.progress.emit(90, 100)
            
            # Convert to numpy array
            img_array = np.array(img)
            extract_array = np.array(extraction_img)
            
            self.progress.emit(100, 100)
            
            if logger:
                logger.success(f"Image loaded: {img.width}x{img.height}")
            
            self.finished.emit(WorkerResult(
                success=True,
                data={
                    'image': img,
                    'array': img_array,
                    'extraction_array': extract_array,
                    'original_size': original_size,
                    'display_size': img.size
                }
            ))
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="loading image file",
                    show_traceback=True
                )
            else:
                if logger:
                    logger.error(f"Image load failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(WorkerResult(False, None, str(e)))


class PaletteExportWorker(QThread):
    """
    Worker thread for exporting large palette images.
    
    Signals:
        progress: Emits progress percentage
        finished: Emits WorkerResult
        error: Emits error message
    """
    
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        colors: list[tuple[tuple[int, int, int], tuple[int, int, int], int, bool]],
        file_path: str,
        font_path: str | None = None,
        parent=None
    ):
        super().__init__(parent)
        self.colors = colors
        self.file_path = file_path
        self.font_path = font_path
        self._cancelled = False
        if logger:
            logger.debug(f"PaletteExportWorker initialized ({len(colors)} colors)")
    
    def cancel(self) -> None:
        self._cancelled = True
    
    def run(self) -> None:
        """Export palette as image in background."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
            
            if logger:
                logger.info(f"Exporting palette ({len(self.colors)} colors)...")
            self.progress.emit(0, 100)
            
            # Image dimensions
            cols = 3
            rows = (len(self.colors) + cols - 1) // cols
            page_width, page_height = 2550, 3300
            margin, spacing = 150, 10
            
            usable_width = page_width - (2 * margin)
            usable_height = page_height - (2 * margin)
            swatch_width = (usable_width - (cols - 1) * spacing) // cols
            swatch_height = (usable_height - (rows - 1) * spacing) // rows
            
            content_width = cols * swatch_width + (cols - 1) * spacing
            content_height = rows * swatch_height + (rows - 1) * spacing
            offset_x = (page_width - content_width) // 2
            offset_y = (page_height - content_height) // 2
            
            # Create image
            is_png = self.file_path.lower().endswith('.png')
            if is_png:
                palette_img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))
            else:
                palette_img = Image.new("RGB", (page_width, page_height), (255, 255, 255))
            
            draw = ImageDraw.Draw(palette_img)
            
            self.progress.emit(10, 100)
            
            # Load fonts ONCE (cached)
            font_size = max(14, min(swatch_width, swatch_height) // 12)
            font = None
            small_font = None
            
            if self.font_path and os.path.exists(self.font_path):
                try:
                    font = ImageFont.truetype(self.font_path, font_size)
                    small_font = ImageFont.truetype(self.font_path, max(10, font_size - 4))
                except Exception:
                    pass
            
            if not font:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                    small_font = ImageFont.truetype("arial.ttf", max(10, font_size - 4))
                except Exception:
                    font = ImageFont.load_default()
                    small_font = font
            
            self.progress.emit(20, 100)
            
            # Draw swatches
            total = len(self.colors)
            for idx, (rgb, hsl, hilbert_idx, is_locked) in enumerate(self.colors):
                if self._cancelled:
                    self.finished.emit(WorkerResult(False, None, "Cancelled"))
                    return
                
                col = idx % cols
                row = idx // cols
                x = offset_x + col * (swatch_width + spacing)
                y = offset_y + row * (swatch_height + spacing)
                
                # Draw swatch
                draw.rectangle(
                    [x, y, x + swatch_width, y + swatch_height],
                    fill=rgb, outline=(0, 0, 0), width=2
                )
                
                # Text color based on brightness (use cache if available)
                r, g, b = rgb
                if CACHE_AVAILABLE and ColorCache:
                    text_color = ColorCache.get_text_color_for_background((r, g, b))
                    hex_code = ColorCache.rgb_to_hex((r, g, b))
                else:
                    brightness = (r * 299 + g * 587 + b * 114) / 1000
                    text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                    hex_code = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                
                # Draw text
                draw.text((x + 10, y + 10), f"#{idx + 1}", fill=text_color, font=font)
                draw.text((x + 10, y + swatch_height - 50), hex_code, fill=text_color, font=small_font)
                rgb_text = f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"
                draw.text((x + 10, y + swatch_height - 25), rgb_text, fill=text_color, font=small_font)
                
                # Update progress
                if idx % 10 == 0:
                    self.progress.emit(20 + int(70 * idx / total), 100)
            
            self.progress.emit(90, 100)
            
            # Save image
            fmt = 'PNG' if is_png else 'JPEG'
            palette_img.save(self.file_path, fmt, quality=95, dpi=(300, 300))
            
            self.progress.emit(100, 100)
            
            if logger:
                logger.success(f"Palette exported: {self.file_path}")
            
            self.finished.emit(WorkerResult(
                success=True,
                data={'file_path': self.file_path, 'color_count': len(self.colors)}
            ))
            
        except Exception as e:
            # Use ErrorHandler for consistent error handling
            if ERROR_HANDLER_AVAILABLE:
                ErrorHandler.handle_exception(
                    e,
                    context="exporting palette image",
                    show_traceback=True
                )
            else:
                if logger:
                    logger.error(f"Palette export failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(WorkerResult(False, None, str(e)))

class WorkerManager:
    """
    Centralized manager for worker threads.
    
    Tracks active workers and ensures proper cleanup on application exit.
    
    Usage:
        manager = WorkerManager()
        worker = manager.create_worker(ColorExtractionWorker, pixels, max_colors=333)
        worker.finished.connect(on_complete)
        manager.start_worker(worker)
        
        # On app close:
        manager.cancel_all()
    """
    
    def __init__(self):
        """Initialize worker manager."""
        self._active_workers: list[QThread] = []
        
        # Initialize signal manager for tracked connections
        if SIGNAL_MANAGER_AVAILABLE:
            self.signal_manager = SignalConnectionManager()
        else:
            self.signal_manager = None
        
        if logger:
            logger.debug("WorkerManager initialized")
    
    def register(self, worker: QThread) -> None:
        """
        Register a worker for tracking.
        
        Args:
            worker: Worker thread to track
        """
        if worker not in self._active_workers:
            self._active_workers.append(worker)
            # Auto-remove when finished with tracked connection
            if self.signal_manager:
                self.signal_manager.connect(
                    worker,
                    worker.finished,
                    lambda: self._on_worker_finished(worker),
                    track_as=f"worker_{id(worker)}"
                )
            else:
                worker.finished.connect(lambda: self._on_worker_finished(worker))
    
    def _on_worker_finished(self, worker: QThread) -> None:
        """Handle worker completion."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
    
    def start_worker(self, worker: QThread) -> None:
        """
        Register and start a worker.
        
        Args:
            worker: Worker thread to start
        """
        self.register(worker)
        worker.start()
    
    def cancel_all(self, timeout: int = 2000) -> int:
        """
        Cancel all active workers.
        
        Args:
            timeout: Maximum time to wait per worker (ms)
            
        Returns:
            Number of workers cancelled
        """
        cancelled = 0
        
        for worker in list(self._active_workers):
            if worker.isRunning():
                # Try graceful cancellation first
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                
                worker.quit()
                
                if not worker.wait(timeout):
                    # Force terminate if graceful shutdown fails
                    worker.terminate()
                    worker.wait(500)
                
                cancelled += 1
        
        self._active_workers.clear()
        
        if logger and cancelled > 0:
            logger.info(f"Cancelled {cancelled} worker threads")
        
        return cancelled
    
    def wait_all(self, timeout: int = 5000) -> bool:
        """
        Wait for all workers to complete.
        
        Args:
            timeout: Maximum time to wait per worker (ms)
            
        Returns:
            True if all completed, False if timeout
        """
        for worker in self._active_workers:
            if worker.isRunning():
                if not worker.wait(timeout):
                    return False
        return True
    
    @property
    def active_count(self) -> int:
        """Number of currently active workers."""
        return sum(1 for w in self._active_workers if w.isRunning())
    
    def cleanup(self) -> None:
        """Clean up all workers (for app shutdown)."""
        self.cancel_all()
        self._active_workers.clear()


# Singleton instance
_worker_manager: WorkerManager | None = None


def get_worker_manager() -> WorkerManager:
    """Get or create the singleton WorkerManager instance."""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager
