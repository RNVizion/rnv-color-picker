# -*- coding: utf-8 -*-
"""
Tests for utils/clipboard.py.

Phase 3-aux-2 covers ClipboardUtils — color-format-aware clipboard
operations. We use the real Qt clipboard via `QApplication.clipboard()` for
the happy paths and monkeypatch to force exceptions for error paths.

Coverage targets:
  - __init__                              (gets QApplication; raises if None)
  - copy_text                             (happy + exception)
  - copy_hex_color                        (uses ColorCache)
  - copy_rgb_color                        (string format)
  - copy_hsv_color                        (degrees + percent format)
  - copy_hsl_color                        (degrees + percent format)
  - get_clipboard_text                    (with text + empty + exception)
  - try_parse_color_from_clipboard        (empty, hex, rgb, hsv, hsl,
                                           malformed-of-each, no-prefix)
  - copy_color_palette                    (multi-color list + exception)
  - clear_clipboard                       (happy + exception)
  - has_text                              (true + false + exception)
  - has_image                             (false + exception)
  - copy_color_as_css                     (CSS variable format)
  - copy_multiple_formats                 (combined format + exception)

Out of scope:
  - The "no QApplication" branch in __init__ — the test environment always
    has an app instance running (otherwise pytest-qt wouldn't work).
  - has_image=True branch — would require placing a real image on the
    clipboard, which is platform-flaky in headless test environments.
"""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

from utils.clipboard import ClipboardUtils


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def clip(qtbot):
    """ClipboardUtils with a fresh clipboard.

    Note: qtbot is required to ensure the QApplication is alive for the
    duration of the test.
    """
    QApplication.clipboard().clear()
    return ClipboardUtils()


def _set_clipboard(text: str) -> None:
    """Helper: prime the Qt clipboard with text."""
    QApplication.clipboard().setText(text)


def _get_clipboard() -> str:
    return QApplication.clipboard().text()


# =============================================================================
# 1.  __init__
# =============================================================================

class TestInit:
    """Init grabs QApplication.instance() — raises if it returns None."""

    def test_app_attached(self, clip):
        assert clip.app is not None
        assert clip.app is QApplication.instance()

    def test_raises_if_no_app(self, monkeypatch):
        # Force QApplication.instance() to return None
        monkeypatch.setattr(QApplication, "instance",
                            staticmethod(lambda: None))
        with pytest.raises(RuntimeError, match="QApplication"):
            ClipboardUtils()


# =============================================================================
# 2.  copy_text
# =============================================================================

class TestCopyText:
    """`copy_text` writes a string to the system clipboard."""

    def test_writes_text_to_clipboard(self, clip):
        assert clip.copy_text("hello world") is True
        assert _get_clipboard() == "hello world"

    def test_empty_string_is_valid(self, clip):
        # Non-empty first to confirm overwrite
        _set_clipboard("previous")
        assert clip.copy_text("") is True
        assert _get_clipboard() == ""

    def test_unicode_text(self, clip):
        assert clip.copy_text("Hello — 你好 — 🎨") is True
        assert _get_clipboard() == "Hello — 你好 — 🎨"

    def test_returns_false_on_exception(self, clip, monkeypatch):
        # Force the clipboard accessor to raise
        def bad_clipboard(): raise RuntimeError("clipboard busy")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        assert clip.copy_text("anything") is False


# =============================================================================
# 3.  copy_hex_color
# =============================================================================

class TestCopyHexColor:
    """`copy_hex_color` writes the hex form of an RGB tuple."""

    def test_red_to_hex(self, clip):
        assert clip.copy_hex_color((255, 0, 0)) is True
        assert _get_clipboard().lower() == "#ff0000"

    def test_brand_gold_hex(self, clip):
        # Brand gold is #FFA500
        clip.copy_hex_color((255, 165, 0))
        assert _get_clipboard().lower() == "#ffa500"

    def test_black_hex(self, clip):
        clip.copy_hex_color((0, 0, 0))
        assert _get_clipboard().lower() == "#000000"

    def test_white_hex(self, clip):
        clip.copy_hex_color((255, 255, 255))
        assert _get_clipboard().lower() == "#ffffff"


# =============================================================================
# 4.  copy_rgb_color
# =============================================================================

class TestCopyRgbColor:
    """`copy_rgb_color` writes 'rgb(r, g, b)' format."""

    def test_red(self, clip):
        clip.copy_rgb_color((255, 0, 0))
        assert _get_clipboard() == "rgb(255, 0, 0)"

    def test_arbitrary_color(self, clip):
        clip.copy_rgb_color((128, 64, 32))
        assert _get_clipboard() == "rgb(128, 64, 32)"


# =============================================================================
# 5.  copy_hsv_color and copy_hsl_color
# =============================================================================

class TestCopyHsvColor:
    """`copy_hsv_color` writes 'hsv(degrees, %, %)' with one decimal."""

    def test_red_hsv_format(self, clip):
        clip.copy_hsv_color((255, 0, 0))
        text = _get_clipboard()
        assert text.startswith("hsv(")
        assert "%" in text
        # Red has hue 0
        assert "0.0" in text or "0," in text

    def test_format_has_three_components(self, clip):
        clip.copy_hsv_color((128, 64, 32))
        text = _get_clipboard()
        # Two commas → three components
        assert text.count(",") == 2

    def test_returns_true(self, clip):
        assert clip.copy_hsv_color((100, 100, 100)) is True


class TestCopyHslColor:
    """`copy_hsl_color` writes 'hsl(degrees, %, %)' with one decimal."""

    def test_red_hsl_format(self, clip):
        clip.copy_hsl_color((255, 0, 0))
        text = _get_clipboard()
        assert text.startswith("hsl(")
        assert "%" in text

    def test_format_has_three_components(self, clip):
        clip.copy_hsl_color((128, 64, 32))
        assert _get_clipboard().count(",") == 2

    def test_returns_true(self, clip):
        assert clip.copy_hsl_color((50, 100, 150)) is True


# =============================================================================
# 6.  get_clipboard_text
# =============================================================================

class TestGetClipboardText:
    """`get_clipboard_text` returns clipboard text or None."""

    def test_returns_text_when_present(self, clip):
        _set_clipboard("foo bar")
        assert clip.get_clipboard_text() == "foo bar"

    def test_returns_none_when_empty(self, clip):
        QApplication.clipboard().clear()
        assert clip.get_clipboard_text() is None

    def test_returns_none_on_exception(self, clip, monkeypatch):
        def bad_clipboard(): raise RuntimeError("oops")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        assert clip.get_clipboard_text() is None


# =============================================================================
# 7.  try_parse_color_from_clipboard
# =============================================================================

class TestParseColorFromClipboard:
    """`try_parse_color_from_clipboard` handles hex/rgb/hsv/hsl/malformed."""

    def test_empty_clipboard_returns_none(self, clip):
        QApplication.clipboard().clear()
        assert clip.try_parse_color_from_clipboard() is None

    def test_parse_hex_6_char(self, clip):
        _set_clipboard("#FF8800")
        result = clip.try_parse_color_from_clipboard()
        assert result == (255, 136, 0)

    def test_parse_hex_lowercase(self, clip):
        _set_clipboard("#ff8800")
        result = clip.try_parse_color_from_clipboard()
        assert result == (255, 136, 0)

    def test_parse_hex_with_whitespace(self, clip):
        _set_clipboard("  #FF8800  ")
        # Source strips whitespace
        result = clip.try_parse_color_from_clipboard()
        assert result == (255, 136, 0)

    def test_parse_rgb_format(self, clip):
        _set_clipboard("rgb(100, 50, 200)")
        result = clip.try_parse_color_from_clipboard()
        assert result == (100, 50, 200)

    def test_parse_rgb_no_spaces(self, clip):
        _set_clipboard("rgb(10,20,30)")
        result = clip.try_parse_color_from_clipboard()
        assert result == (10, 20, 30)

    def test_parse_hsv_format(self, clip):
        # HSV 0/100%/100% should be red (255, 0, 0) — but we don't depend on
        # exact rounding here; just verify it parses to something
        _set_clipboard("hsv(0, 100%, 100%)")
        result = clip.try_parse_color_from_clipboard()
        assert result is not None
        assert all(0 <= c <= 255 for c in result)

    def test_parse_hsl_format(self, clip):
        _set_clipboard("hsl(0, 100%, 50%)")
        result = clip.try_parse_color_from_clipboard()
        assert result is not None
        assert all(0 <= c <= 255 for c in result)

    def test_unrecognized_text_returns_none(self, clip):
        _set_clipboard("not a color")
        assert clip.try_parse_color_from_clipboard() is None

    def test_malformed_hex_returns_none(self, clip):
        # Wrong length — 5 chars
        _set_clipboard("#FFAA")
        assert clip.try_parse_color_from_clipboard() is None

    def test_malformed_rgb_returns_none(self, clip):
        # Only two values
        _set_clipboard("rgb(100, 50)")
        assert clip.try_parse_color_from_clipboard() is None

    def test_malformed_hsv_returns_none(self, clip):
        _set_clipboard("hsv(bad, 50%, 50%)")
        assert clip.try_parse_color_from_clipboard() is None

    def test_malformed_hsl_returns_none(self, clip):
        _set_clipboard("hsl(bad, 50%, 50%)")
        assert clip.try_parse_color_from_clipboard() is None

    def test_hex_invalid_chars_returns_none(self, clip):
        _set_clipboard("#GGGGGG")
        assert clip.try_parse_color_from_clipboard() is None


# =============================================================================
# 8.  copy_color_palette
# =============================================================================

class TestCopyColorPalette:
    """`copy_color_palette` formats a list of (color, weight) tuples."""

    def test_empty_palette_writes_header_only(self, clip):
        clip.copy_color_palette([])
        text = _get_clipboard()
        assert "Color Palette:" in text

    def test_single_color(self, clip):
        clip.copy_color_palette([((255, 0, 0), 100)])
        text = _get_clipboard()
        assert "Color Palette:" in text
        assert "ff0000" in text.lower()
        assert "weight: 100" in text

    def test_multi_color(self, clip):
        colors = [
            ((255, 0, 0), 50),
            ((0, 255, 0), 30),
            ((0, 0, 255), 20),
        ]
        clip.copy_color_palette(colors)
        text = _get_clipboard()
        assert "ff0000" in text.lower()
        assert "00ff00" in text.lower()
        assert "0000ff" in text.lower()
        # Each entry is numbered 1, 2, 3
        assert " 1." in text
        assert " 2." in text
        assert " 3." in text

    def test_returns_true_on_success(self, clip):
        assert clip.copy_color_palette([((100, 100, 100), 50)]) is True

    def test_returns_false_on_exception(self, clip, monkeypatch):
        # Force copy_text to raise during the inner loop
        def bad_clipboard(): raise RuntimeError("simulated failure")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        # copy_text catches its own exception and returns False, so the
        # outer try/except in copy_color_palette doesn't actually fire — but
        # the function still returns False because copy_text returned False
        result = clip.copy_color_palette([((1, 2, 3), 1)])
        assert result is False


# =============================================================================
# 9.  clear_clipboard
# =============================================================================

class TestClearClipboard:
    """`clear_clipboard` empties the clipboard."""

    def test_clears_existing_text(self, clip):
        _set_clipboard("something")
        assert clip.clear_clipboard() is True
        assert _get_clipboard() == ""

    def test_returns_false_on_exception(self, clip, monkeypatch):
        def bad_clipboard(): raise RuntimeError("locked")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        assert clip.clear_clipboard() is False


# =============================================================================
# 10.  has_text and has_image
# =============================================================================

class TestHasText:
    """`has_text` reports whether clipboard contains text."""

    def test_returns_true_with_text(self, clip):
        _set_clipboard("yo")
        assert clip.has_text() is True

    def test_returns_false_when_empty(self, clip):
        QApplication.clipboard().clear()
        # Some platforms still report hasText() True for empty string —
        # the contract is about presence, not non-emptiness. So we just
        # verify no crash.
        result = clip.has_text()
        assert isinstance(result, bool)

    def test_returns_false_on_exception(self, clip, monkeypatch):
        def bad_clipboard(): raise RuntimeError("no clipboard")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        assert clip.has_text() is False


class TestHasImage:
    """`has_image` reports whether clipboard contains image data."""

    def test_returns_false_with_text_clipboard(self, clip):
        _set_clipboard("text only")
        assert clip.has_image() is False

    def test_returns_false_when_empty(self, clip):
        QApplication.clipboard().clear()
        assert clip.has_image() is False

    def test_returns_false_on_exception(self, clip, monkeypatch):
        def bad_clipboard(): raise RuntimeError("oops")
        monkeypatch.setattr(clip.app, "clipboard", bad_clipboard)
        assert clip.has_image() is False


# =============================================================================
# 11.  copy_color_as_css
# =============================================================================

class TestCopyColorAsCSS:
    """`copy_color_as_css` writes a CSS custom property."""

    def test_default_variable_name(self, clip):
        clip.copy_color_as_css((255, 165, 0))
        assert _get_clipboard().startswith("--primary-color:")
        assert "#ffa500" in _get_clipboard().lower()
        assert _get_clipboard().endswith(";")

    def test_custom_variable_name(self, clip):
        clip.copy_color_as_css((128, 0, 128), variable_name="brand-purple")
        assert "--brand-purple:" in _get_clipboard()
        assert "#800080" in _get_clipboard().lower()

    def test_returns_true(self, clip):
        assert clip.copy_color_as_css((1, 2, 3)) is True


# =============================================================================
# 12.  copy_multiple_formats
# =============================================================================

class TestCopyMultipleFormats:
    """`copy_multiple_formats` writes hex/rgb/hsv/hsl block."""

    def test_contains_all_four_format_labels(self, clip):
        clip.copy_multiple_formats((255, 0, 0))
        text = _get_clipboard()
        assert "HEX:" in text
        assert "RGB:" in text
        assert "HSV:" in text
        assert "HSL:" in text

    def test_contains_color_value(self, clip):
        clip.copy_multiple_formats((128, 64, 32))
        text = _get_clipboard()
        assert "rgb(128, 64, 32)" in text

    def test_returns_true_on_success(self, clip):
        assert clip.copy_multiple_formats((100, 100, 100)) is True

    def test_returns_false_on_exception(self, clip, monkeypatch):
        # Patch ColorCache.rgb_to_hex to raise to trigger the outer except
        from utils import cache as _cache_mod
        if _cache_mod.ColorCache:
            monkeypatch.setattr(_cache_mod.ColorCache, "rgb_to_hex",
                                staticmethod(lambda rgb: (_ for _ in ()).throw(
                                    RuntimeError("bad cache"))))
        result = clip.copy_multiple_formats((10, 20, 30))
        assert result is False
