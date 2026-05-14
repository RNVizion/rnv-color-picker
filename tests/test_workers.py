"""
Phase 6 part 1: core/workers.py — Qt threading and worker-thread coverage.

The legacy unittest suite covers approximately none of this module — workers
were stuck at 28% coverage because the QThread infrastructure was untested.

Strategy: a *hybrid* of two complementary approaches.

  1. Synchronous run() — call worker.run() directly in the test thread.
     Signals still fire (they're delivered direct-connection when emitted
     from the receiver's thread). This bypasses Qt thread scheduling, which
     means no event-loop pumping, no flake from timing. Perfect for the
     logic of run(): happy paths, cancellation branches, exception paths,
     payload-shape assertions.

  2. Real start() with qtbot.waitSignal — used only where threading
     *behaviour* is the system-under-test (WorkerManager.cancel_all on a
     running worker, signal_manager integration after worker completion).
     A FakeSlowWorker fixture sleeps in run() until cancelled, so tests
     can deterministically observe a worker that's actually running.

Coverage targets:
  - ColorExtractionWorker — happy, cancel-at-10%, cancel-at-60%,
    max_colors truncation, exception path
  - DominantColorWorker — happy, cancel-at-10%, cancel-at-80%, exception
  - ImageLoadWorker — happy, RGB conversion, display-downsample,
    extraction-downsample, file-not-found exception
  - PaletteExportWorker — PNG, JPEG, custom font, font fallback chain,
    cancel mid-loop, exception
  - WorkerManager — register, _on_worker_finished cleanup, start_worker,
    cancel_all (with real running worker), wait_all, active_count,
    cleanup, signal_manager integration
  - get_worker_manager singleton — lazy create + identity

Imports: pytest-qt provides the `qtbot` fixture and the `QApplication`.
"""

import time

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtTest import QSignalSpy

from core.workers import (
    ColorExtractionWorker,
    DominantColorWorker,
    ImageLoadWorker,
    PaletteExportWorker,
    WorkerManager,
    WorkerResult,
    get_worker_manager,
)
import core.workers as workers_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_worker_manager_singleton():
    """Reset the module-level singleton between tests so identity tests
    aren't polluted by other tests' lazy-init."""
    workers_module._worker_manager = None
    yield
    workers_module._worker_manager = None


@pytest.fixture
def small_pixels():
    """A trivial 10x10 image of solid red — fast for color-extraction tests."""
    return np.array([[[255, 0, 0]] * 10] * 10, dtype=np.uint8)


@pytest.fixture
def varied_pixels():
    """20x20 image with three distinct colors so K-means has something to do."""
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    arr[:10, :10] = [255, 0, 0]      # top-left red
    arr[:10, 10:] = [0, 255, 0]      # top-right green
    arr[10:] = [0, 0, 255]            # bottom blue
    return arr


@pytest.fixture
def png_file(tmp_path):
    """A tiny 50x50 RGB PNG on disk."""
    path = tmp_path / "small.png"
    img = Image.new("RGB", (50, 50), (128, 64, 200))
    img.save(path)
    return str(path)


@pytest.fixture
def rgba_png_file(tmp_path):
    """A 50x50 RGBA PNG — exercises the mode != 'RGB' conversion branch."""
    path = tmp_path / "rgba.png"
    img = Image.new("RGBA", (50, 50), (128, 64, 200, 200))
    img.save(path)
    return str(path)


# Signal capture helper — easier to read than QSignalSpy in many cases
def _collect_signals(worker):
    """Hook plain-Python lists onto the worker's three signals.

    Returns (progress_log, finished_log, error_log). After worker.run()
    these contain everything emitted, in order.
    """
    progress_log, finished_log, error_log = [], [], []
    worker.progress.connect(lambda c, t: progress_log.append((c, t)))
    worker.finished.connect(lambda r: finished_log.append(r))
    worker.error.connect(lambda msg: error_log.append(msg))
    return progress_log, finished_log, error_log


# ===========================================================================
# ColorExtractionWorker
# ===========================================================================


class TestColorExtractionWorkerInit:
    def test_signals_defined(self):
        # Class-level signals must exist on the type
        assert hasattr(ColorExtractionWorker, "progress")
        assert hasattr(ColorExtractionWorker, "finished")
        assert hasattr(ColorExtractionWorker, "error")

    def test_init_stores_pixels(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        assert w.pixels is small_pixels

    def test_init_default_max_colors_is_333(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        assert w.max_colors == 333

    def test_init_custom_max_colors(self, small_pixels):
        w = ColorExtractionWorker(small_pixels, max_colors=50)
        assert w.max_colors == 50

    def test_starts_uncancelled(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        assert w.is_cancelled() is False

    def test_cancel_sets_flag(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        w.cancel()
        assert w.is_cancelled() is True

    def test_inherits_qthread(self, small_pixels):
        # WorkerManager treats workers polymorphically as QThread
        assert isinstance(ColorExtractionWorker(small_pixels), QThread)


class TestColorExtractionWorkerHappyPath:
    def test_solid_color_returns_one_color(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        progress, finished, error = _collect_signals(w)
        w.run()
        assert len(finished) == 1
        result = finished[0]
        assert result.success is True
        assert result.data["colors"] == [(255, 0, 0)]
        assert result.data["total_unique"] == 1
        assert result.data["total_pixels"] == 100  # 10x10
        assert error == []

    def test_progress_starts_at_zero_ends_at_hundred(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        progress, _, _ = _collect_signals(w)
        w.run()
        assert progress[0] == (0, 100)
        assert progress[-1] == (100, 100)

    def test_progress_is_monotonically_non_decreasing(self, small_pixels):
        # The progress checkpoints in source are 0 → 10 → 60 → 80 → 100
        w = ColorExtractionWorker(small_pixels)
        progress, _, _ = _collect_signals(w)
        w.run()
        currents = [c for c, _ in progress]
        assert currents == sorted(currents)

    def test_returns_worker_result_object(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        _, finished, _ = _collect_signals(w)
        w.run()
        assert isinstance(finished[0], WorkerResult)

    def test_truncates_to_max_colors(self):
        # 400 distinct colors, max_colors=10 → result trimmed to 10
        pixels = np.array(
            [[[i % 256, (i * 3) % 256, (i * 7) % 256] for i in range(20)]
             for _ in range(20)], dtype=np.uint8)
        w = ColorExtractionWorker(pixels, max_colors=10)
        _, finished, _ = _collect_signals(w)
        w.run()
        assert len(finished[0].data["colors"]) == 10


class TestColorExtractionWorkerCancellation:
    def test_cancel_before_run_emits_cancelled_finished(self, small_pixels):
        w = ColorExtractionWorker(small_pixels)
        w.cancel()
        _, finished, _ = _collect_signals(w)
        w.run()
        # Source's first cancellation check is right after the 10% emit
        assert finished[0].success is False
        assert "Cancelled" in finished[0].error

    def test_cancel_before_run_progresses_to_at_least_ten(self, small_pixels):
        # Even when cancelled, progress fires up to the first checkpoint
        w = ColorExtractionWorker(small_pixels)
        w.cancel()
        progress, _, _ = _collect_signals(w)
        w.run()
        currents = [c for c, _ in progress]
        # 0 and 10 should have been emitted before the cancel-check
        assert 0 in currents
        assert 10 in currents


class TestColorExtractionWorkerExceptionPath:
    def test_invalid_input_emits_error_and_failed_finished(self):
        # Passing a 1-D array trips reshape(-1, 3) since 5 isn't divisible
        bad_pixels = np.array([1, 2, 3, 4, 5], dtype=np.uint8)
        w = ColorExtractionWorker(bad_pixels)
        _, finished, error = _collect_signals(w)
        w.run()
        # Exception path emits BOTH error and finished
        assert len(error) == 1
        assert len(finished) == 1
        assert finished[0].success is False
        assert finished[0].error  # has an error string


# ===========================================================================
# DominantColorWorker
# ===========================================================================


class TestDominantColorWorkerInit:
    def test_signals_defined(self):
        for sig in ("progress", "finished", "error"):
            assert hasattr(DominantColorWorker, sig)

    def test_init_stores_clusters(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=3)
        assert w.num_clusters == 3

    def test_default_clusters_is_five(self, varied_pixels):
        w = DominantColorWorker(varied_pixels)
        assert w.num_clusters == 5

    def test_default_max_iterations_is_hundred(self, varied_pixels):
        w = DominantColorWorker(varied_pixels)
        assert w.max_iterations == 100

    def test_starts_uncancelled(self, varied_pixels):
        assert DominantColorWorker(varied_pixels).is_cancelled() is False

    def test_cancel_sets_flag(self, varied_pixels):
        w = DominantColorWorker(varied_pixels)
        w.cancel()
        assert w.is_cancelled() is True


class TestDominantColorWorkerHappyPath:
    def test_three_color_image_yields_three_clusters(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=3)
        progress, finished, error = _collect_signals(w)
        w.run()
        assert finished[0].success is True
        assert len(finished[0].data["colors"]) == 3
        assert len(finished[0].data["counts"]) == 3
        assert error == []

    def test_progress_reaches_hundred(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=2)
        progress, _, _ = _collect_signals(w)
        w.run()
        assert progress[-1] == (100, 100)

    def test_counts_sum_to_total_pixels(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=3)
        _, finished, _ = _collect_signals(w)
        w.run()
        # Every pixel goes to exactly one cluster — counts must sum to N
        total_pixels = varied_pixels.shape[0] * varied_pixels.shape[1]
        assert sum(finished[0].data["counts"]) == total_pixels

    def test_returned_colors_are_int_tuples(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=2)
        _, finished, _ = _collect_signals(w)
        w.run()
        for c in finished[0].data["colors"]:
            assert isinstance(c, tuple)
            assert len(c) == 3
            assert all(isinstance(v, int) for v in c)


class TestDominantColorWorkerCancellation:
    def test_cancel_before_run_emits_cancelled_finished(self, varied_pixels):
        w = DominantColorWorker(varied_pixels, num_clusters=2)
        w.cancel()
        _, finished, _ = _collect_signals(w)
        w.run()
        assert finished[0].success is False
        assert "Cancelled" in finished[0].error


class TestDominantColorWorkerExceptionPath:
    def test_too_many_clusters_for_pixels_emits_error(self):
        # Asking for 100 clusters from a single pixel should fail in KMeans
        tiny = np.array([[[42, 42, 42]]], dtype=np.uint8)
        w = DominantColorWorker(tiny, num_clusters=100)
        _, finished, error = _collect_signals(w)
        w.run()
        assert len(error) == 1
        assert finished[0].success is False


# ===========================================================================
# ImageLoadWorker
# ===========================================================================


class TestImageLoadWorkerInit:
    def test_init_stores_filepath(self, png_file):
        w = ImageLoadWorker(png_file)
        assert w.file_path == png_file

    def test_signals_defined(self):
        for sig in ("progress", "finished", "error"):
            assert hasattr(ImageLoadWorker, sig)

    def test_max_display_dimension_constant(self):
        assert ImageLoadWorker.MAX_DISPLAY_DIMENSION == 3840

    def test_max_extraction_pixels_constant(self):
        assert ImageLoadWorker.MAX_EXTRACTION_PIXELS == 500 * 500

    def test_cancel_sets_flag(self, png_file):
        w = ImageLoadWorker(png_file)
        w.cancel()
        assert w._cancelled is True


class TestImageLoadWorkerHappyPath:
    def test_loads_small_png_successfully(self, png_file):
        w = ImageLoadWorker(png_file)
        _, finished, error = _collect_signals(w)
        w.run()
        assert error == []
        assert finished[0].success is True
        assert finished[0].data["display_size"] == (50, 50)
        assert finished[0].data["original_size"] == (50, 50)

    def test_returned_arrays_are_numpy_with_three_channels(self, png_file):
        w = ImageLoadWorker(png_file)
        _, finished, _ = _collect_signals(w)
        w.run()
        arr = finished[0].data["array"]
        assert isinstance(arr, np.ndarray)
        assert arr.shape[2] == 3

    def test_progress_reaches_hundred(self, png_file):
        w = ImageLoadWorker(png_file)
        progress, _, _ = _collect_signals(w)
        w.run()
        assert progress[-1] == (100, 100)


class TestImageLoadWorkerModeConversion:
    def test_rgba_image_converted_to_rgb(self, rgba_png_file):
        # Source has `if img.mode != 'RGB': img = img.convert('RGB')`
        w = ImageLoadWorker(rgba_png_file)
        _, finished, _ = _collect_signals(w)
        w.run()
        # Output array must be 3-channel even though input was RGBA
        assert finished[0].data["array"].shape[2] == 3


class TestImageLoadWorkerDownsampling:
    def test_oversized_image_downsampled_for_display(self, tmp_path):
        # Larger than MAX_DISPLAY_DIMENSION (3840) → downsample for display
        big_path = tmp_path / "big.png"
        Image.new("RGB", (5000, 1000), (10, 20, 30)).save(big_path)
        w = ImageLoadWorker(str(big_path))
        _, finished, _ = _collect_signals(w)
        w.run()
        # Display size should now have max dim == 3840
        ds = finished[0].data["display_size"]
        assert max(ds) == ImageLoadWorker.MAX_DISPLAY_DIMENSION
        # Original_size is preserved
        assert finished[0].data["original_size"] == (5000, 1000)

    def test_image_above_extraction_threshold_creates_smaller_array(
            self, tmp_path):
        # 600x600 = 360k pixels; below display limit (3840) but above
        # extraction limit (250k). Display array stays 600x600; extraction
        # array gets downsampled.
        path = tmp_path / "med.png"
        Image.new("RGB", (600, 600), (10, 20, 30)).save(path)
        w = ImageLoadWorker(str(path))
        _, finished, _ = _collect_signals(w)
        w.run()
        display_arr = finished[0].data["array"]
        extract_arr = finished[0].data["extraction_array"]
        assert display_arr.shape[:2] == (600, 600)
        # Extraction array smaller than display
        assert extract_arr.size < display_arr.size

    def test_small_image_extraction_array_equals_display(self, png_file):
        # 50x50 = 2500 pixels; below both thresholds → no downsampling;
        # extraction_img is just an alias of img (same array)
        w = ImageLoadWorker(png_file)
        _, finished, _ = _collect_signals(w)
        w.run()
        assert finished[0].data["array"].shape == \
            finished[0].data["extraction_array"].shape


class TestImageLoadWorkerExceptionPath:
    def test_missing_file_emits_error_and_failed_finished(self, tmp_path):
        w = ImageLoadWorker(str(tmp_path / "nonexistent.png"))
        _, finished, error = _collect_signals(w)
        w.run()
        assert len(error) == 1
        assert finished[0].success is False


# ===========================================================================
# PaletteExportWorker
# ===========================================================================


def _palette_colors(n=3):
    """Build the (rgb, hsl, hilbert_idx, is_locked) tuples PaletteExportWorker
    expects. Real values aren't critical — just the shape."""
    return [
        ((255, 0, 0),   (0,   100, 50), 1, False),
        ((0,   255, 0), (120, 100, 50), 2, True),
        ((0,   0,   255), (240, 100, 50), 3, False),
    ][:n]


class TestPaletteExportWorkerInit:
    def test_init_stores_colors_and_path(self, tmp_path):
        out = str(tmp_path / "out.png")
        w = PaletteExportWorker(_palette_colors(), out)
        assert w.file_path == out
        assert len(w.colors) == 3

    def test_default_font_path_is_none(self, tmp_path):
        w = PaletteExportWorker(_palette_colors(), str(tmp_path / "x.png"))
        assert w.font_path is None

    def test_starts_uncancelled(self, tmp_path):
        w = PaletteExportWorker(_palette_colors(), str(tmp_path / "x.png"))
        assert w._cancelled is False

    def test_cancel_sets_flag(self, tmp_path):
        w = PaletteExportWorker(_palette_colors(), str(tmp_path / "x.png"))
        w.cancel()
        assert w._cancelled is True


class TestPaletteExportWorkerHappyPath:
    def test_png_export_writes_file(self, tmp_path):
        out = str(tmp_path / "palette.png")
        w = PaletteExportWorker(_palette_colors(), out)
        _, finished, error = _collect_signals(w)
        w.run()
        assert error == []
        assert finished[0].success is True
        assert (tmp_path / "palette.png").exists()
        # PNG branch creates an RGBA image (per source line 434)
        img = Image.open(out)
        assert img.mode == "RGBA"

    def test_jpeg_export_writes_file(self, tmp_path):
        out = str(tmp_path / "palette.jpg")
        w = PaletteExportWorker(_palette_colors(), out)
        _, finished, _ = _collect_signals(w)
        w.run()
        assert finished[0].success is True
        assert (tmp_path / "palette.jpg").exists()
        # JPEG branch — RGB mode (per source line 436)
        img = Image.open(out)
        assert img.mode == "RGB"

    def test_finished_payload_includes_filepath_and_count(self, tmp_path):
        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(2), out)
        _, finished, _ = _collect_signals(w)
        w.run()
        assert finished[0].data["file_path"] == out
        assert finished[0].data["color_count"] == 2

    def test_progress_reaches_hundred(self, tmp_path):
        w = PaletteExportWorker(_palette_colors(), str(tmp_path / "p.png"))
        progress, _, _ = _collect_signals(w)
        w.run()
        assert progress[-1] == (100, 100)


class TestPaletteExportWorkerFontFallbacks:
    def test_provided_font_path_that_exists_is_used(
            self, tmp_path, monkeypatch):
        # Source: `if self.font_path and os.path.exists(self.font_path)`.
        # We don't need a real .ttf — we just need ImageFont.truetype to NOT
        # raise. Patch it to return a sentinel and check it's called.
        # Signature uses *args, **kwargs because PIL's internals pass
        # layout_engine= and other kwargs we don't care about.
        from PIL import ImageFont
        original_truetype = ImageFont.truetype
        sentinel_font = ImageFont.load_default()
        truetype_calls = []

        def fake_truetype(path, size=10, *args, **kwargs):
            truetype_calls.append(str(path))
            # Return a real font object so any internal load_default calls work
            if isinstance(path, str) and path.endswith("fake.ttf"):
                return sentinel_font
            return original_truetype(path, size, *args, **kwargs)
        monkeypatch.setattr(ImageFont, "truetype", fake_truetype)

        font_file = tmp_path / "fake.ttf"
        font_file.write_bytes(b"\0")  # exists() == True
        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(), out, font_path=str(font_file))
        _, finished, _ = _collect_signals(w)
        w.run()
        # Custom font path was attempted
        assert any(str(font_file) == c for c in truetype_calls)
        assert finished[0].success is True

    def test_provided_font_that_fails_falls_back_to_arial(
            self, tmp_path, monkeypatch):
        # truetype raises for the user-supplied path → arial fallback path
        from PIL import ImageFont
        original_truetype = ImageFont.truetype
        attempt_log = []

        def fake_truetype(path, size=10, *args, **kwargs):
            attempt_log.append(str(path))
            if isinstance(path, str) and "fake.ttf" in path:
                raise OSError("font corrupted")
            # Arial / system / load_default internals → real behaviour
            return original_truetype(path, size, *args, **kwargs)
        monkeypatch.setattr(ImageFont, "truetype", fake_truetype)

        font_file = tmp_path / "fake.ttf"
        font_file.write_bytes(b"\0")
        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(), out, font_path=str(font_file))
        _, finished, _ = _collect_signals(w)
        w.run()
        # Both the user font and arial were attempted
        assert any("fake.ttf" in p for p in attempt_log)
        assert any("arial" in p.lower() for p in attempt_log)
        assert finished[0].success is True

    def test_no_font_path_and_arial_fails_uses_default(
            self, tmp_path, monkeypatch):
        # Both arial attempts fail → source falls through to load_default().
        # Tricky: PIL's load_default() *internally* calls truetype(BytesIO, 13,
        # layout_engine=...). If our patch fails ALL truetype calls, load_default
        # raises too and we test the wrong branch. Solution: keep a reference
        # to the original truetype, and only fail when the source asks for arial.
        from PIL import ImageFont
        original_truetype = ImageFont.truetype

        def selective_truetype(path, size=10, *args, **kwargs):
            if isinstance(path, str) and "arial" in path.lower():
                raise OSError("no arial")
            # All other paths (BytesIO from load_default) → real behaviour
            return original_truetype(path, size, *args, **kwargs)
        monkeypatch.setattr(ImageFont, "truetype", selective_truetype)

        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(), out, font_path=None)
        _, finished, _ = _collect_signals(w)
        w.run()
        # arial fails → load_default succeeds → export completes
        assert finished[0].success is True

    def test_nonexistent_font_path_skips_to_arial(self, tmp_path, monkeypatch):
        # font_path is a string but the file doesn't exist → source's
        # `os.path.exists(...)` returns False, skipping the custom-font
        # branch. Track which paths are passed to truetype to verify.
        from PIL import ImageFont
        original_truetype = ImageFont.truetype
        attempts = []

        def track_truetype(path, size=10, *args, **kwargs):
            attempts.append(str(path))
            return original_truetype(path, size, *args, **kwargs)
        monkeypatch.setattr(ImageFont, "truetype", track_truetype)

        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(
            _palette_colors(), out, font_path="/nonexistent/font.ttf")
        _, finished, _ = _collect_signals(w)
        w.run()
        # The /nonexistent path was never attempted (the os.path.exists
        # guard short-circuited). Only system paths should appear.
        assert all("/nonexistent" not in a for a in attempts)
        assert finished[0].success is True


class TestPaletteExportWorkerCancellation:
    def test_cancelled_mid_loop_emits_cancelled_finished(self, tmp_path):
        # Pre-cancel before run() — the per-color loop's _cancelled check
        # fires on the first iteration and short-circuits.
        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(), out, font_path=None)
        w.cancel()
        _, finished, _ = _collect_signals(w)
        w.run()
        assert finished[0].success is False
        assert "Cancelled" in finished[0].error
        # File should NOT have been written
        assert not (tmp_path / "p.png").exists()


class TestPaletteExportWorkerExceptionPath:
    def test_unwritable_path_emits_error_and_failed_finished(
            self, tmp_path, monkeypatch):
        # Make Image.save raise to trigger the except-block at line 518
        from PIL import Image as PILImage

        def fail_save(self, *args, **kwargs):
            raise OSError("disk full")
        monkeypatch.setattr(PILImage.Image, "save", fail_save)

        out = str(tmp_path / "p.png")
        w = PaletteExportWorker(_palette_colors(), out)
        _, finished, error = _collect_signals(w)
        w.run()
        assert len(error) == 1
        assert finished[0].success is False


# ===========================================================================
# WorkerManager — needs a real running worker for cancel_all / wait_all tests
# ===========================================================================


class FakeSlowWorker(QThread):
    """A controllable QThread for testing WorkerManager lifecycle.

    Sleeps in run() in 50ms ticks until either:
      - external code sets self._stop = True (graceful)
      - the thread is terminated (forced)

    Has a `finished` signal compatible with WorkerManager's expectations.
    """

    finished = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._stop = False

    def cancel(self):
        # Match the interface WorkerManager.cancel_all expects via hasattr
        self._stop = True

    def run(self):
        # Bounded loop so this can never become an infinite test hang
        for _ in range(200):  # max 10 seconds
            if self._stop:
                break
            self.msleep(50)
        # Emit a synthetic finished — WorkerManager auto-removes on this
        self.finished.emit(WorkerResult(True, None))


class TestWorkerManagerInit:
    def test_starts_with_empty_active_list(self):
        m = WorkerManager()
        assert m._active_workers == []

    def test_active_count_zero_initially(self):
        assert WorkerManager().active_count == 0

    def test_signal_manager_attached_when_available(self):
        # SIGNAL_MANAGER_AVAILABLE is True in the codebase; the manager
        # should have a real signal_manager (not None)
        m = WorkerManager()
        assert m.signal_manager is not None


class TestWorkerManagerRegister:
    def test_register_adds_worker_to_active_list(self, small_pixels):
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        m.register(w)
        assert w in m._active_workers

    def test_register_duplicate_is_idempotent(self, small_pixels):
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        m.register(w)
        m.register(w)
        assert m._active_workers.count(w) == 1

    def test_finished_signal_triggers_removal_from_active(self, small_pixels):
        # When the worker emits finished, _on_worker_finished should remove
        # it from _active_workers. We don't actually start the thread —
        # we manually emit finished to test the wiring.
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        m.register(w)
        assert w in m._active_workers
        # Manually emit finished — connected via signal_manager
        w.finished.emit(WorkerResult(True, None))
        assert w not in m._active_workers

    def test_on_worker_finished_handles_already_removed_worker(
            self, small_pixels):
        # Defensive: _on_worker_finished checks `if worker in self._active`
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        # Don't register — worker isn't tracked
        m._on_worker_finished(w)  # must not raise


class TestWorkerManagerStartWorker:
    def test_start_worker_registers_and_starts(self, qtbot, small_pixels):
        # Real start() — we want to confirm the manager registers the
        # worker AND that the thread actually runs to completion.
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        with qtbot.waitSignal(w.finished, timeout=5000):
            m.start_worker(w)
        # After finished, the auto-cleanup should have removed it
        assert w not in m._active_workers


class TestWorkerManagerCancelAll:
    def test_cancel_all_with_no_active_returns_zero(self):
        m = WorkerManager()
        assert m.cancel_all() == 0

    def test_cancel_all_stops_running_worker_and_returns_count(self, qtbot):
        # The hard test: a real running thread, asked to cancel, should
        # exit gracefully via its cancel() method (no terminate() needed).
        m = WorkerManager()
        w = FakeSlowWorker()
        m.register(w)
        w.start()
        # Give Qt a moment for the thread to actually be running
        qtbot.wait(50)
        cancelled = m.cancel_all(timeout=2000)
        assert cancelled == 1
        # _active_workers cleared
        assert m._active_workers == []
        # Thread is no longer running
        assert not w.isRunning()

    def test_cancel_all_clears_active_list_even_if_none_running(self, small_pixels):
        # Workers in the list but not running (already finished) — list
        # should still be cleared by cancel_all
        m = WorkerManager()
        w = ColorExtractionWorker(small_pixels)
        m._active_workers.append(w)
        # Worker has never been started → isRunning() False
        assert not w.isRunning()
        m.cancel_all()
        assert m._active_workers == []


class TestWorkerManagerWaitAll:
    def test_wait_all_no_workers_returns_true(self):
        assert WorkerManager().wait_all() is True

    def test_wait_all_returns_true_after_workers_finish(self, qtbot):
        m = WorkerManager()
        w = FakeSlowWorker()
        m.register(w)
        w.start()
        qtbot.wait(20)
        # Politely ask the worker to stop
        w.cancel()
        # wait_all should succeed within timeout
        assert m.wait_all(timeout=3000) is True

    def test_wait_all_returns_false_on_timeout(self, qtbot):
        # A worker that won't stop within our short timeout
        m = WorkerManager()
        w = FakeSlowWorker()
        m.register(w)
        w.start()
        qtbot.wait(20)
        # Don't cancel — worker is still busy. Short timeout → False.
        result = m.wait_all(timeout=50)
        # Cleanup
        w.cancel()
        w.wait(2000)
        assert result is False


class TestWorkerManagerActiveCount:
    def test_zero_when_only_unstarted_workers(self, small_pixels):
        m = WorkerManager()
        m.register(ColorExtractionWorker(small_pixels))
        # Registered but not started → isRunning() False → active_count 0
        assert m.active_count == 0

    def test_reflects_running_worker(self, qtbot):
        m = WorkerManager()
        w = FakeSlowWorker()
        m.register(w)
        w.start()
        qtbot.wait(20)
        try:
            assert m.active_count == 1
        finally:
            w.cancel()
            w.wait(2000)


class TestWorkerManagerCleanup:
    def test_cleanup_calls_cancel_all(self, qtbot):
        m = WorkerManager()
        w = FakeSlowWorker()
        m.register(w)
        w.start()
        qtbot.wait(20)
        m.cleanup()
        assert m._active_workers == []
        assert not w.isRunning()


# ===========================================================================
# Singleton + module getter
# ===========================================================================


class TestGetWorkerManagerSingleton:
    def test_first_call_creates_instance(self):
        m = get_worker_manager()
        assert isinstance(m, WorkerManager)

    def test_subsequent_calls_return_same_instance(self):
        first = get_worker_manager()
        second = get_worker_manager()
        assert first is second

    def test_module_state_persists_until_reset(self):
        m = get_worker_manager()
        # Module global should now hold our instance
        assert workers_module._worker_manager is m
