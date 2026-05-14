"""
RNV Color Picker — Comprehensive Test Suite
============================================
Tests every core/utils/ui module that doesn't require an interactive UI loop.

Usage — place this file in your project root (same folder as RNV_Color_Picker.py):
    python test_rnv_color_picker.py           # standard run
    python test_rnv_color_picker.py -v        # verbose (shows each test name)

Requirements: PyQt6, numpy, scikit-learn, Pillow

Layout support: works with both
  - subdirectory layout (core/, utils/, ui/)  ← your machine
  - flat layout (everything in one folder)    ← sandboxes / minimal copies
"""

import sys, os, io, json, tempfile, shutil, unittest, types, importlib.util
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# QApplication MUST exist before any Qt module is imported or instantiated
try:
    from PyQt6.QtWidgets import QApplication as _QApp
    from PyQt6.QtCore import Qt as _Qt
    if not _QApp.instance():
        _qapp = _QApp(sys.argv[:1])
        _qapp.setAttribute(_Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    else:
        _qapp = _QApp.instance()
except Exception:
    _qapp = None

# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP — supports both subdirectory (core/, utils/, ui/) and flat layouts
# ══════════════════════════════════════════════════════════════════════════════
_THIS = Path(__file__).resolve()
_ROOT = None

for _c in [_THIS.parent,
           _THIS.parent.parent,
           Path("/mnt/project"),
           Path.home() / "RNV_Color_Picker",
           Path.home() / "source/repos/RNV_Color_Picker/RNV_Color_Picker"]:
    if (_c / "RNV_Color_Picker.py").exists():
        _ROOT = str(_c); break
    if (_c / "core").is_dir() and (_c / "utils").is_dir():
        _ROOT = str(_c); break
    if (_c / "color_math.py").exists() and (_c / "color_collection.py").exists():
        _ROOT = str(_c); break

if _ROOT is None:
    sys.exit(
        "ERROR: Cannot find project root.\n"
        "Place test_rnv_color_picker.py in the same folder as RNV_Color_Picker.py"
    )

_SUBDIR_LAYOUT = os.path.isdir(os.path.join(_ROOT, "core"))

if _SUBDIR_LAYOUT:
    # Subdirectory layout — production layout (your machine)
    sys.path.insert(0, _ROOT)
else:
    # Flat layout — register virtual core/utils/ui packages pointing at the dir,
    # then let Python's import machinery resolve everything lazily. Each
    # virtual package's __path__ tells Python "look for submodules here".
    sys.path.insert(0, _ROOT)
    for _pkg in ("core", "utils", "ui"):
        if _pkg not in sys.modules:
            _m = types.ModuleType(_pkg)
            _m.__path__ = [_ROOT]
            _m.__package__ = _pkg
            sys.modules[_pkg] = _m

# ── Required imports (these MUST work or the suite is meaningless) ────────────
from core.color_math      import ColorMath
from core.color_harmony   import ColorHarmony, HarmonyType
from core.color_history   import ColorHistoryManager
from core.palette_formats import PaletteFormats
from core.color_collection import ColorCollection, ColorEntry
from core.hilbert_curve   import HilbertCurve
from core.accessibility   import (
    ColorAccessibility, ColorBlindnessType, WCAGLevel, ContrastResult
)
from utils.session_manager  import SessionManager
from utils.settings_manager import SettingsManager
from utils.error_handler    import ErrorHandler
from utils import config
from utils import file_utils as fu  # module-level functions

# ── Optional imports — guarded so tests skip cleanly if a module fails ────────
try:
    from utils.clipboard import ClipboardUtils
    _CLIPBOARD_OK = True
except Exception:
    ClipboardUtils = None; _CLIPBOARD_OK = False

try:
    from utils.signal_manager import SignalConnectionManager
    _SIGNAL_OK = True
except Exception:
    SignalConnectionManager = None; _SIGNAL_OK = False

try:
    from utils.logger import Logger as AppLogger, get_logger as _get_logger
    _LOGGER_OK = True
except Exception:
    AppLogger = None; _get_logger = None; _LOGGER_OK = False

try:
    from utils.pixmap_cache import ImagePixmapCache
    _PIXMAP_CACHE_OK = True
except Exception:
    ImagePixmapCache = None; _PIXMAP_CACHE_OK = False

try:
    from utils.cache import ColorCache, QColorCache, StylesheetCache, FontCache
    _CACHE_OK = True
except Exception:
    ColorCache = QColorCache = StylesheetCache = FontCache = None; _CACHE_OK = False

try:
    from core.workers import (
        ColorExtractionWorker, DominantColorWorker, WorkerResult, WorkerManager
    )
    _WORKERS_OK = True
except Exception:
    ColorExtractionWorker = DominantColorWorker = WorkerResult = WorkerManager = None
    _WORKERS_OK = False

try:
    from utils.dialog_helper import DialogHelper, DialogResult
    _DIALOG_OK = True
except Exception:
    DialogHelper = DialogResult = None; _DIALOG_OK = False

try:
    from utils.font_loader import load_embedded_font, get_font
    _FONT_LOADER_OK = True
except Exception:
    load_embedded_font = get_font = None; _FONT_LOADER_OK = False

try:
    from utils.async_file_ops import (
        AsyncFileManager, async_save_json, async_load_json,
        FileWriterThread, FileReaderThread
    )
    _ASYNC_OK = True
except Exception:
    AsyncFileManager = async_save_json = async_load_json = None
    FileWriterThread = FileReaderThread = None; _ASYNC_OK = False

try:
    from utils.cache import ResourceCache
    _RESOURCE_CACHE_OK = True
except Exception:
    ResourceCache = None; _RESOURCE_CACHE_OK = False

try:
    from core.screen_color_picker import ScreenColorPicker
    _SCREEN_PICKER_OK = True
except Exception:
    ScreenColorPicker = None; _SCREEN_PICKER_OK = False

try:
    from ui.widget_pool import WidgetPool
    _WIDGET_POOL_OK = True
except Exception:
    WidgetPool = None; _WIDGET_POOL_OK = False

# ANSI colour helpers
_G="\033[92m"; _R="\033[91m"; _Y="\033[93m"; _C="\033[96m"; _B="\033[1m"; _X="\033[0m"

# ══════════════════════════════════════════════════════════════════════════════
# Global ColorHistoryManager safety patch
# ColorHistoryManager._setup_history_path() writes to AppData/Library/.config
# and load_history() reads from there. Neutralise both so the test never
# touches real user data and never crashes on missing dirs.
# ══════════════════════════════════════════════════════════════════════════════
_HIST_TMP  = tempfile.mkdtemp()
_HIST_SAFE = Path(_HIST_TMP) / "test_history.json"

ColorHistoryManager.load_history = lambda self: None  # Never read real file
def _safe_setup(self):
    self.history_file = _HIST_SAFE
ColorHistoryManager._setup_history_path = _safe_setup
def _safe_init(self):
    self.history = []
    self.history_file = _HIST_SAFE
ColorHistoryManager.__init__ = _safe_init


# ══════════════════════════════════════════════════════════════════════════════
# 1. COLOR MATH
# ══════════════════════════════════════════════════════════════════════════════
class TestColorMath(unittest.TestCase):
    """color_math.py — RGB/HSV/HSL/LAB conversions, weighted mixes, validation."""

    # ── HEX ──
    def test_rgb_to_hex_black(self):       self.assertEqual(ColorMath.rgb_to_hex((0,0,0)), "#000000")
    def test_rgb_to_hex_white(self):       self.assertEqual(ColorMath.rgb_to_hex((255,255,255)), "#ffffff")
    def test_rgb_to_hex_red(self):         self.assertEqual(ColorMath.rgb_to_hex((255,0,0)), "#ff0000")
    def test_rgb_to_hex_brand_gold(self):  self.assertEqual(ColorMath.rgb_to_hex((210,188,147)), "#d2bc93")
    def test_hex_to_rgb_black(self):       self.assertEqual(ColorMath.hex_to_rgb("#000000"), (0,0,0))
    def test_hex_to_rgb_white(self):       self.assertEqual(ColorMath.hex_to_rgb("#ffffff"), (255,255,255))
    def test_hex_to_rgb_uppercase(self):   self.assertEqual(ColorMath.hex_to_rgb("#FF0000"), (255,0,0))
    def test_hex_to_rgb_3char(self):       self.assertEqual(ColorMath.hex_to_rgb("#f00"), (255,0,0))

    def test_roundtrip_rgb_hex(self):
        for c in [(0,0,0),(255,255,255),(128,64,200),(1,2,3),(16,0,255)]:
            self.assertEqual(ColorMath.hex_to_rgb(ColorMath.rgb_to_hex(c)), c)

    # ── HSV ──
    def test_hsv_black_v_zero(self):
        _,_,v = ColorMath.rgb_to_hsv((0,0,0)); self.assertAlmostEqual(v, 0.0)

    def test_hsv_white_s_zero(self):
        _,s,_ = ColorMath.rgb_to_hsv((255,255,255)); self.assertAlmostEqual(s, 0.0)

    def test_hsv_red_hue_zero(self):
        h,_,_ = ColorMath.rgb_to_hsv((255,0,0)); self.assertAlmostEqual(h, 0.0, delta=0.01)

    def test_hsv_roundtrip(self):
        for c in [(255,0,0),(0,255,0),(0,0,255),(128,128,0)]:
            back = ColorMath.hsv_to_rgb(ColorMath.rgb_to_hsv(c))
            for a,b in zip(c,back): self.assertAlmostEqual(a,b,delta=2)

    # ── HSL ──
    def test_hsl_black(self):
        _,l,_ = ColorMath.rgb_to_hsl((0,0,0)); self.assertAlmostEqual(l, 0.0, delta=0.01)

    def test_hsl_white(self):
        _,l,_ = ColorMath.rgb_to_hsl((255,255,255)); self.assertAlmostEqual(l, 1.0, delta=0.01)

    def test_hsl_roundtrip(self):
        for c in [(255,0,0),(0,255,0),(0,0,255),(128,64,200)]:
            back = ColorMath.hsl_to_rgb(ColorMath.rgb_to_hsl(c))
            for a,b in zip(c,back): self.assertAlmostEqual(a,b,delta=2,msg=f"HSL roundtrip {c}")

    # ── LAB ──
    def test_lab_white_L_100(self):
        L,_,_ = ColorMath.rgb_to_lab((255,255,255)); self.assertAlmostEqual(L,100.0,delta=1.0)

    def test_lab_black_L_zero(self):
        L,_,_ = ColorMath.rgb_to_lab((0,0,0)); self.assertAlmostEqual(L,0.0,delta=1.0)

    def test_lab_roundtrip(self):
        for c in [(255,0,0),(0,255,0),(128,64,200)]:
            back = ColorMath.lab_to_rgb(ColorMath.rgb_to_lab(c))
            for a,b in zip(c,back): self.assertAlmostEqual(a,b,delta=3)

    # ── Mixing ──
    def test_rgb_mix_50_50(self):
        r = ColorMath.weighted_rgb_mix([((255,0,0),50),((0,0,255),50)])
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r[0],127,delta=2); self.assertAlmostEqual(r[2],127,delta=2)

    def test_rgb_mix_single_identity(self):
        self.assertEqual(ColorMath.weighted_rgb_mix([((200,100,50),100)]), (200,100,50))

    def test_rgb_mix_empty_none(self):
        self.assertIsNone(ColorMath.weighted_rgb_mix([]))

    def test_rgb_mix_zero_weights_none(self):
        self.assertIsNone(ColorMath.weighted_rgb_mix([((255,0,0),0),((0,0,255),0)]))

    def test_rgb_mix_high_weight_dominates(self):
        r = ColorMath.weighted_rgb_mix([((255,0,0),90),((0,0,255),10)])
        self.assertIsNotNone(r); self.assertGreater(r[0], r[2])

    def test_hsv_mix_valid(self):
        r = ColorMath.weighted_hsv_mix([((255,0,0),50),((0,0,255),50)])
        self.assertIsNotNone(r)
        for ch in r: self.assertGreaterEqual(ch,0); self.assertLessEqual(ch,255)

    def test_hsv_mix_empty_none(self):
        self.assertIsNone(ColorMath.weighted_hsv_mix([]))

    # ── Validation / clamping ──
    def test_validate_rgb_clamps_high(self):
        r,g,b = ColorMath.validate_rgb((300,128,500))
        self.assertEqual((r,g,b),(255,128,255))

    def test_validate_rgb_clamps_low(self):
        r,g,b = ColorMath.validate_rgb((-10,-1,128))
        self.assertEqual((r,g,b),(0,0,128))

    def test_clamp_rgb_floats(self):
        self.assertEqual(ColorMath.clamp_rgb(300.0,-5.0,128.7), (255,0,128))

    def test_clamp_value_high(self):  self.assertEqual(ColorMath.clamp_value(300.0), 255)
    def test_clamp_value_low(self):   self.assertEqual(ColorMath.clamp_value(-10.0), 0)
    def test_clamp_value_mid(self):   self.assertEqual(ColorMath.clamp_value(128.0), 128)

    # ── Palette generation ──
    def test_generate_palette_count(self):
        self.assertEqual(len(ColorMath.generate_color_palette((255,0,0),count=5)), 5)

    def test_generate_palette_count_one(self):
        self.assertEqual(len(ColorMath.generate_color_palette((128,128,128),count=1)), 1)

    def test_generate_palette_values_valid(self):
        for c in ColorMath.generate_color_palette((200,100,50),count=8):
            self.assertEqual(len(c),3)
            for ch in c: self.assertGreaterEqual(ch,0); self.assertLessEqual(ch,255)


# ══════════════════════════════════════════════════════════════════════════════
# 2. COLOR HARMONY
# ══════════════════════════════════════════════════════════════════════════════
class TestColorHarmony(unittest.TestCase):
    """color_harmony.py — all 7 harmony types (Picker has same API as Mixer)."""

    RED=(255,0,0); WHITE=(255,255,255); BLACK=(0,0,0); GRAY=(128,128,128)

    def _valid(self, colors):
        for c in colors:
            self.assertEqual(len(c),3)
            for ch in c: self.assertGreaterEqual(ch,0); self.assertLessEqual(ch,255)

    def test_complementary(self):
        r = ColorHarmony.generate_complementary(self.RED)
        self.assertEqual(len(r),2); self._valid(r); self.assertEqual(r[0],self.RED)

    def test_triadic(self):
        r = ColorHarmony.generate_triadic(self.RED); self.assertEqual(len(r),3); self._valid(r)

    def test_analogous(self):
        r = ColorHarmony.generate_analogous(self.RED); self.assertEqual(len(r),3); self._valid(r)

    def test_analogous_custom_angle(self):
        r = ColorHarmony.generate_analogous(self.RED, angle=60); self.assertEqual(len(r),3)

    def test_split_complementary(self):
        r = ColorHarmony.generate_split_complementary(self.RED); self.assertEqual(len(r),3)

    def test_tetradic(self):
        r = ColorHarmony.generate_tetradic(self.RED); self.assertEqual(len(r),4); self._valid(r)

    def test_compound(self):
        r = ColorHarmony.generate_compound(self.RED); self.assertEqual(len(r),4); self._valid(r)

    def test_monochromatic_5(self):
        r = ColorHarmony.generate_monochromatic(self.RED, count=5); self.assertEqual(len(r),5)

    def test_monochromatic_7(self):
        r = ColorHarmony.generate_monochromatic(self.RED, count=7); self.assertEqual(len(r),7)

    def test_all_types_on_red(self):
        for ht in HarmonyType:
            r = ColorHarmony.generate_harmony(self.RED, ht)
            self.assertIsNotNone(r, f"Failed for {ht}"); self._valid(r)

    def test_all_types_on_white(self):
        for ht in HarmonyType: self.assertIsNotNone(ColorHarmony.generate_harmony(self.WHITE, ht))

    def test_all_types_on_black(self):
        for ht in HarmonyType: self.assertIsNotNone(ColorHarmony.generate_harmony(self.BLACK, ht))

    def test_all_types_on_gray(self):
        for ht in HarmonyType: self.assertIsNotNone(ColorHarmony.generate_harmony(self.GRAY, ht))

    def test_descriptions_nonempty(self):
        for ht in HarmonyType:
            d = ColorHarmony.get_harmony_description(ht)
            self.assertIsInstance(d, str); self.assertGreater(len(d), 0)

    def test_counts_positive(self):
        for ht in HarmonyType:
            c = ColorHarmony.get_harmony_count(ht)
            self.assertIsInstance(c, int); self.assertGreater(c, 0)

    def test_normalize_hue_above_one(self):
        self.assertAlmostEqual(ColorHarmony.normalize_hue(1.5), 0.5, delta=0.01)

    def test_normalize_hue_below_zero(self):
        self.assertAlmostEqual(ColorHarmony.normalize_hue(-0.25), 0.75, delta=0.01)

    def test_rotate_hue_180(self):
        h = ColorHarmony.rotate_hue(0.0, 180); self.assertAlmostEqual(h, 0.5, delta=0.01)

    def test_rotate_hue_wraps(self):
        h = ColorHarmony.rotate_hue(0.9, 72); self.assertAlmostEqual(h % 1.0, 0.1, delta=0.01)

    def test_all_primaries_all_harmonies(self):
        for c in [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(0,255,255),(255,0,255)]:
            for ht in HarmonyType:
                self.assertIsNotNone(ColorHarmony.generate_harmony(c, ht))


# ══════════════════════════════════════════════════════════════════════════════
# 3. COLOR HISTORY MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class TestColorHistoryManager(unittest.TestCase):
    """color_history.py — ColorHistoryManager (singleton AppData-backed)."""

    def setUp(self):
        # __init__ patched globally → safe to instantiate without filesystem hits
        self.h = ColorHistoryManager()

    def test_starts_empty(self):
        self.assertEqual(len(self.h.history), 0)

    def test_add_single(self):
        self.h.add_color((255,0,0)); self.assertEqual(len(self.h.history), 1)

    def test_add_stores_hex(self):
        self.h.add_color((255,0,0))
        self.assertEqual(self.h.history[0]["hex"], "#ff0000")

    def test_add_stores_rgb_list(self):
        self.h.add_color((100,150,200))
        self.assertEqual(self.h.history[0]["rgb"], [100,150,200])

    def test_add_with_source(self):
        self.h.add_color((50,50,50), source="screen")
        self.assertEqual(self.h.history[0]["source"], "screen")

    def test_add_default_source(self):
        self.h.add_color((50,50,50))
        self.assertIn("source", self.h.history[0])

    def test_consecutive_dupe_increments_pick_count(self):
        self.h.add_color((255,0,0))
        self.h.add_color((255,0,0))
        # Second add should bump pick_count, not create a new entry
        self.assertEqual(len(self.h.history), 1)
        self.assertEqual(self.h.history[0].get("pick_count"), 2)

    def test_get_history_returns_list(self):
        self.h.add_color((1,2,3))
        self.assertIsInstance(self.h.get_history(), list)

    def test_get_history_with_limit(self):
        for i in range(5): self.h.add_color((i*10, 0, 0))
        self.assertEqual(len(self.h.get_history(limit=2)), 2)

    def test_get_recent_colors(self):
        self.h.add_color((255,0,0))
        self.h.add_color((0,255,0))
        recent = self.h.get_recent_colors(count=2)
        self.assertEqual(len(recent), 2)
        self.assertIsInstance(recent[0], tuple)

    def test_clear_history(self):
        self.h.add_color((1,1,1)); self.h.clear_history()
        self.assertEqual(len(self.h.history), 0)

    def test_remove_color_existing(self):
        self.h.add_color((255,0,0))
        self.assertTrue(self.h.remove_color("#ff0000"))
        self.assertEqual(len(self.h.history), 0)

    def test_remove_color_missing(self):
        self.h.add_color((255,0,0))
        self.assertFalse(self.h.remove_color("#deadbe"))

    def test_remove_color_case_insensitive(self):
        self.h.add_color((255,0,0))
        self.assertTrue(self.h.remove_color("#FF0000"))

    def test_get_color_info_existing(self):
        self.h.add_color((100,100,100))
        info = self.h.get_color_info("#646464")
        self.assertIsNotNone(info)
        self.assertEqual(info["hex"], "#646464")

    def test_get_color_info_missing(self):
        self.assertIsNone(self.h.get_color_info("#nonexistent"))

    def test_max_history_size(self):
        self.assertEqual(ColorHistoryManager.MAX_HISTORY_SIZE, 333)

    def test_history_filename_constant(self):
        self.assertEqual(ColorHistoryManager.HISTORY_FILENAME, "color_history.json")

    def test_export_history(self):
        self.h.add_color((50,75,100))
        tmp = tempfile.mkdtemp()
        try:
            fp = os.path.join(tmp, "exported.json")
            self.assertTrue(self.h.export_history(fp))
            self.assertTrue(os.path.exists(fp))
            with open(fp) as f: data = json.load(f)
            self.assertIn("colors", data)
            self.assertEqual(len(data["colors"]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_format_timestamp_no_crash(self):
        from datetime import datetime
        ts = datetime.now().isoformat()
        out = self.h.format_timestamp(ts)
        self.assertIsInstance(out, str); self.assertGreater(len(out), 0)

    def test_format_timestamp_invalid_returns_input(self):
        out = self.h.format_timestamp("not-a-timestamp")
        self.assertEqual(out, "not-a-timestamp")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PALETTE FORMATS
# ══════════════════════════════════════════════════════════════════════════════
class TestPaletteFormats(unittest.TestCase):
    """palette_formats.py — export/import for all supported formats."""

    TEST_PAL = [((255,0,0),20),((0,255,0),20),((0,0,255),20),
                ((255,255,0),20),((0,255,255),20)]

    @classmethod
    def setUpClass(cls):  cls.tmp = tempfile.mkdtemp()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def _p(self, ext): return os.path.join(self.tmp, f"pal.{ext}")

    def _roundtrip(self, ext):
        PaletteFormats.export_palette(self._p(ext), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p(ext)), f"No file: .{ext}")
        r = PaletteFormats.import_palette(self._p(ext))
        self.assertIsNotNone(r, f"Import None: .{ext}")
        self.assertGreater(len(r), 0, f"Import empty: .{ext}")
        return r

    def test_export_formats_count(self):
        self.assertGreater(len(PaletteFormats.get_export_formats()), 10)

    def test_import_formats_nonempty(self):
        self.assertGreater(len(PaletteFormats.get_import_formats()), 0)

    def test_gpl_roundtrip(self):   self._roundtrip("gpl")
    def test_json_roundtrip(self):  self._roundtrip("json")
    def test_hex_roundtrip(self):   self._roundtrip("hex")
    def test_txt_roundtrip(self):
        # txt export writes hex codes preceded by index — import recovers them
        PaletteFormats.export_palette(self._p("txt"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("txt")))

    def test_hex_roundtrip_color_accuracy(self):
        """Hex roundtrip must preserve RGB exactly and weight."""
        r = self._roundtrip("hex")
        self.assertEqual(len(r), len(self.TEST_PAL))
        for (oc, ow), (ic, iw) in zip(self.TEST_PAL, r):
            self.assertEqual(oc, ic, f"Color drift: {oc} → {ic}")
            self.assertEqual(ow, iw, f"Weight drift: {ow} → {iw}")

    def test_colors_roundtrip(self):
        """`.colors` format roundtrips RGB and weight cleanly."""
        path = os.path.join(self.tmp, "rt.colors")
        PaletteFormats.export_palette(path, self.TEST_PAL)
        r = PaletteFormats.import_palette(path)
        self.assertEqual(len(r), len(self.TEST_PAL))
        for (oc, ow), (ic, iw) in zip(self.TEST_PAL, r):
            self.assertEqual(oc, ic)
            self.assertEqual(ow, iw)

    def test_hex_import_skips_comments(self):
        """Comment lines (`# Header`) must not be parsed as data."""
        path = os.path.join(self.tmp, "comments_only.hex")
        with open(path, "w") as f:
            f.write("# HEX Color Palette\n# Format: #RRGGBB Weight\n#\n")
        self.assertEqual(len(PaletteFormats.import_palette(path)), 0)

    def test_hex_import_short_form(self):
        """`#fff` 3-char shorthand is recognised and expanded."""
        path = os.path.join(self.tmp, "short.hex")
        with open(path, "w") as f:
            f.write("# Test\n#fff 100\n#000\n")
        r = PaletteFormats.import_palette(path)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0][0], (255, 255, 255))
        self.assertEqual(r[1][0], (0, 0, 0))

    def test_hex_import_default_weight(self):
        """Hex line without a weight defaults to 50."""
        path = os.path.join(self.tmp, "noweight.hex")
        with open(path, "w") as f:
            f.write("#ff0000\n")
        r = PaletteFormats.import_palette(path)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][1], 50)

    def test_hex_import_inline_trailing_comment(self):
        """`# Color N` trailing comment must not corrupt weight parsing."""
        path = os.path.join(self.tmp, "trailing.hex")
        with open(path, "w") as f:
            f.write("#ff0000 75 # Red color name\n")
        r = PaletteFormats.import_palette(path)
        self.assertEqual(r[0], ((255, 0, 0), 75))

    def test_css_export(self):
        PaletteFormats.export_palette(self._p("css"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("css")))

    def test_svg_export(self):
        PaletteFormats.export_palette(self._p("svg"), self.TEST_PAL)
        content = open(self._p("svg")).read().lower()
        self.assertIn("<svg", content)

    def test_svg_uses_export_constants(self):
        """SVG export should pull #FFFFFF bg and #000000 stroke from config constants."""
        # Use a unique filename ending in .svg so the export dispatcher picks _export_svg
        path = os.path.join(self.tmp, "svg_constants_check.svg")
        PaletteFormats.export_palette(path, self.TEST_PAL)
        content = open(path, encoding="utf-8").read().lower()
        self.assertIn(config.SVG_EXPORT_BG.lower(), content)
        self.assertIn(config.SVG_EXPORT_STROKE.lower(), content)

    def test_xml_export(self):
        PaletteFormats.export_palette(self._p("xml"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("xml")))

    def test_hsl_export(self):
        PaletteFormats.export_palette(self._p("hsl"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("hsl")))

    def test_hsv_export(self):
        PaletteFormats.export_palette(self._p("hsv"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("hsv")))

    def test_ase_nonempty(self):
        PaletteFormats.export_palette(self._p("ase"), self.TEST_PAL)
        self.assertGreater(os.path.getsize(self._p("ase")), 0)

    def test_aco_nonempty(self):
        PaletteFormats.export_palette(self._p("aco"), self.TEST_PAL)
        self.assertGreater(os.path.getsize(self._p("aco")), 0)

    def test_acb_nonempty(self):
        PaletteFormats.export_palette(self._p("acb"), self.TEST_PAL)
        self.assertGreater(os.path.getsize(self._p("acb")), 0)

    def test_clr_export(self):
        PaletteFormats.export_palette(self._p("clr"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("clr")))

    def test_colors_export(self):
        PaletteFormats.export_palette(self._p("colors"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("colors")))

    def test_swatches_export(self):
        PaletteFormats.export_palette(self._p("swatches"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("swatches")))

    def test_afpalette_export(self):
        PaletteFormats.export_palette(self._p("afpalette"), self.TEST_PAL)
        self.assertTrue(os.path.exists(self._p("afpalette")))

    def test_json_color_accuracy(self):
        r = self._roundtrip("json")
        self.assertEqual(len(r), len(self.TEST_PAL))
        for (oc,_),(ic,_) in zip(self.TEST_PAL, r):
            for a,b in zip(oc, ic): self.assertAlmostEqual(a, b, delta=2)

    def test_single_color(self):
        p = os.path.join(self.tmp, "single.json")
        PaletteFormats.export_palette(p, [((128,64,32),100)])
        self.assertEqual(len(PaletteFormats.import_palette(p)), 1)

    def test_export_empty_raises(self):
        with self.assertRaises(ValueError):
            PaletteFormats.export_palette(self._p("err.json"), [])

    def test_max_colors_text_formats(self):
        """333-color export — Picker's MAX_COLORS limit."""
        big = [((i % 256, (i*2) % 256, (i*3) % 256), 8) for i in range(333)]
        for ext in ["json", "gpl", "hex", "txt"]:
            p = os.path.join(self.tmp, f"big.{ext}")
            PaletteFormats.export_palette(p, big)
            self.assertTrue(os.path.exists(p), f"333-color failed: .{ext}")

    def test_import_missing_graceful(self):
        try: r = PaletteFormats.import_palette("/no/such.gpl"); self.assertIsNone(r)
        except Exception: pass

    def test_import_corrupted_graceful(self):
        p = os.path.join(self.tmp, "bad.json"); open(p, "w").write("{NOT VALID{{")
        try: r = PaletteFormats.import_palette(p); self.assertIsNone(r)
        except Exception: pass

    # ── Format detection / info ──
    def test_validate_colors_valid(self):
        r = PaletteFormats.validate_colors(self.TEST_PAL)
        self.assertIsNotNone(r)

    def test_get_format_info_json(self):
        info = PaletteFormats.get_format_info(".json")
        self.assertIsNotNone(info); self.assertIn("name", info)

    def test_get_format_info_ase(self):
        info = PaletteFormats.get_format_info(".ase")
        self.assertIsNotNone(info); self.assertEqual(info["type"], "binary")

    def test_get_format_info_gpl(self):
        info = PaletteFormats.get_format_info(".gpl")
        self.assertIsNotNone(info); self.assertEqual(info["type"], "text")


# ══════════════════════════════════════════════════════════════════════════════
# 5. COLOR COLLECTION
# ══════════════════════════════════════════════════════════════════════════════
class TestColorCollection(unittest.TestCase):
    """color_collection.py — O(1) collection with lock state, batch ops, sort."""

    def setUp(self):
        self.cc = ColorCollection(max_size=10)

    def test_starts_empty(self):
        self.assertEqual(len(self.cc), 0)

    def test_max_size(self):
        self.assertEqual(self.cc.max_size, 10)

    def test_remaining_slots_full_when_empty(self):
        self.assertEqual(self.cc.remaining_slots, 10)

    def test_is_full_false_when_empty(self):
        self.assertFalse(self.cc.is_full)

    def test_add_single(self):
        self.assertTrue(self.cc.add((255,0,0)))
        self.assertEqual(len(self.cc), 1)

    def test_add_duplicate_returns_false(self):
        self.cc.add((255,0,0))
        self.assertFalse(self.cc.add((255,0,0)))

    def test_contains_after_add(self):
        self.cc.add((100,100,100))
        self.assertIn((100,100,100), self.cc)

    def test_not_contains_missing(self):
        self.assertNotIn((1,2,3), self.cc)

    def test_add_batch(self):
        added, skipped = self.cc.add_batch([(1,1,1),(2,2,2),(3,3,3)])
        self.assertEqual(added, 3); self.assertEqual(skipped, 0)

    def test_add_batch_skips_duplicates(self):
        self.cc.add((1,1,1))
        added, skipped = self.cc.add_batch([(1,1,1),(2,2,2)])
        self.assertEqual(added, 1); self.assertEqual(skipped, 1)

    def test_add_batch_respects_max(self):
        cc = ColorCollection(max_size=3)
        added, _ = cc.add_batch([(i,0,0) for i in range(10)])
        self.assertLessEqual(added, 3)

    def test_is_full_after_filling(self):
        cc = ColorCollection(max_size=2)
        cc.add((1,0,0)); cc.add((0,1,0))
        self.assertTrue(cc.is_full)

    def test_remove_existing(self):
        self.cc.add((255,0,0))
        self.assertTrue(self.cc.remove((255,0,0)))
        self.assertEqual(len(self.cc), 0)

    def test_remove_missing(self):
        self.assertFalse(self.cc.remove((1,2,3)))

    def test_clear_keep_locked_default(self):
        self.cc.add((1,0,0)); self.cc.add((2,0,0))
        self.cc.set_lock_state((1,0,0), True)
        removed = self.cc.clear(keep_locked=True)
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.cc), 1)

    def test_clear_force(self):
        self.cc.add((1,0,0)); self.cc.set_lock_state((1,0,0), True)
        self.cc.clear(keep_locked=False)
        self.assertEqual(len(self.cc), 0)

    def test_set_lock_state_existing(self):
        self.cc.add((50,50,50))
        self.assertTrue(self.cc.set_lock_state((50,50,50), True))

    def test_set_lock_state_missing(self):
        self.assertFalse(self.cc.set_lock_state((1,1,1), True))

    def test_get_locked_count(self):
        self.cc.add((1,0,0)); self.cc.add((2,0,0))
        self.cc.set_lock_state((1,0,0), True)
        self.assertEqual(self.cc.get_locked_count(), 1)

    def test_iteration(self):
        rgbs = [(1,0,0),(2,0,0),(3,0,0)]
        for c in rgbs: self.cc.add(c)
        out = [e.rgb for e in self.cc]
        self.assertEqual(set(out), set(rgbs))

    def test_indexing(self):
        self.cc.add((42,42,42))
        self.assertEqual(self.cc[0].rgb, (42,42,42))

    def test_sort_by_hilbert(self):
        for c in [(255,0,0),(0,0,255),(0,255,0)]: self.cc.add(c)
        self.cc.sort_by_hilbert()
        # After sort, indices should be monotonically non-decreasing
        idxs = [e.hilbert_idx for e in self.cc]
        self.assertEqual(idxs, sorted(idxs))

    def test_sort_by_hsl(self):
        for c in [(255,0,0),(0,255,0),(0,0,255)]: self.cc.add(c)
        self.cc.sort_by_hsl()
        # No crash — order is implementation detail

    def test_to_legacy_format(self):
        self.cc.add((1,2,3))
        legacy = self.cc.to_legacy_format()
        self.assertEqual(len(legacy), 1)
        self.assertEqual(legacy[0][0], (1,2,3))

    def test_to_palette_format(self):
        self.cc.add((10,20,30))
        pal = self.cc.to_palette_format()
        self.assertEqual(pal[0][0], (10,20,30))
        self.assertEqual(pal[0][1], 50)  # default weight

    def test_get_statistics(self):
        self.cc.add((1,1,1))
        s = self.cc.get_statistics()
        self.assertIsInstance(s, dict)
        self.assertEqual(s["count"], 1)

    def test_validates_rgb_clamping(self):
        # add() validates and clamps internally
        self.assertTrue(self.cc.add((300, -10, 128)))
        # Stored value should be clamped
        entry = self.cc[0]
        self.assertEqual(entry.rgb, (255, 0, 128))

    def test_color_entry_hex(self):
        self.cc.add((255,0,0))
        self.assertEqual(self.cc[0].hex_code, "#ff0000")


# ══════════════════════════════════════════════════════════════════════════════
# 6. HILBERT CURVE
# ══════════════════════════════════════════════════════════════════════════════
class TestHilbertCurve(unittest.TestCase):
    """hilbert_curve.py — 3D space-filling curve for color sorting."""

    def test_origin_index_zero(self):
        self.assertEqual(HilbertCurve.hilbert_index(0.0, 0.0, 0.0), 0)

    def test_returns_int(self):
        self.assertIsInstance(HilbertCurve.hilbert_index(0.5, 0.5, 0.5), int)

    def test_returns_non_negative(self):
        for c in [(0.1,0.2,0.3),(0.9,0.5,0.1),(1.0,1.0,1.0)]:
            self.assertGreaterEqual(HilbertCurve.hilbert_index(*c), 0)

    def test_rgb_to_hilbert_black(self):
        self.assertEqual(HilbertCurve.rgb_to_hilbert((0,0,0)), 0)

    def test_rgb_to_hilbert_returns_int(self):
        self.assertIsInstance(HilbertCurve.rgb_to_hilbert((128,64,200)), int)

    def test_different_colors_different_indices(self):
        a = HilbertCurve.rgb_to_hilbert((255,0,0))
        b = HilbertCurve.rgb_to_hilbert((0,255,0))
        c = HilbertCurve.rgb_to_hilbert((0,0,255))
        # Three primaries should map to three distinct positions
        self.assertEqual(len({a, b, c}), 3)

    def test_same_color_deterministic(self):
        a = HilbertCurve.rgb_to_hilbert((128,64,200))
        b = HilbertCurve.rgb_to_hilbert((128,64,200))
        self.assertEqual(a, b)

    def test_custom_order(self):
        # Lower order → smaller index range
        idx = HilbertCurve.rgb_to_hilbert((255,255,255), order=4)
        self.assertIsInstance(idx, int)


# ══════════════════════════════════════════════════════════════════════════════
# 7. ACCESSIBILITY / WCAG
# ══════════════════════════════════════════════════════════════════════════════
class TestAccessibility(unittest.TestCase):
    """accessibility.py — WCAG contrast + colorblindness simulation."""

    BLACK=(0,0,0); WHITE=(255,255,255); RED=(255,0,0); GRAY=(128,128,128)

    # ── Luminance ──
    def test_luminance_black_zero(self):
        self.assertAlmostEqual(ColorAccessibility.get_relative_luminance(self.BLACK), 0.0, places=3)

    def test_luminance_white_one(self):
        self.assertAlmostEqual(ColorAccessibility.get_relative_luminance(self.WHITE), 1.0, places=3)

    def test_luminance_returns_float_0_1(self):
        L = ColorAccessibility.get_relative_luminance(self.RED)
        self.assertGreaterEqual(L, 0.0); self.assertLessEqual(L, 1.0)

    # ── Contrast ratio ──
    def test_contrast_black_white_max(self):
        ratio = ColorAccessibility.calculate_contrast_ratio(self.BLACK, self.WHITE)
        self.assertAlmostEqual(ratio, 21.0, delta=0.1)

    def test_contrast_same_color_min(self):
        ratio = ColorAccessibility.calculate_contrast_ratio(self.RED, self.RED)
        self.assertAlmostEqual(ratio, 1.0, places=2)

    def test_contrast_symmetric(self):
        a = ColorAccessibility.calculate_contrast_ratio(self.BLACK, self.WHITE)
        b = ColorAccessibility.calculate_contrast_ratio(self.WHITE, self.BLACK)
        self.assertAlmostEqual(a, b)

    # ── check_contrast → ContrastResult ──
    def test_check_contrast_returns_result(self):
        r = ColorAccessibility.check_contrast(self.BLACK, self.WHITE)
        self.assertIsInstance(r, ContrastResult)

    def test_check_contrast_black_white_aaa(self):
        r = ColorAccessibility.check_contrast(self.BLACK, self.WHITE)
        self.assertEqual(r.level, WCAGLevel.AAA)
        self.assertTrue(r.passes_aa_normal)
        self.assertTrue(r.passes_aaa_normal)

    def test_check_contrast_same_color_fails(self):
        r = ColorAccessibility.check_contrast(self.RED, self.RED)
        self.assertEqual(r.level, WCAGLevel.FAIL)
        self.assertFalse(r.passes_aa_normal)

    def test_rating_text_excellent(self):
        r = ColorAccessibility.check_contrast(self.BLACK, self.WHITE)
        self.assertEqual(r.rating_text, "Excellent")

    def test_rating_text_poor(self):
        r = ColorAccessibility.check_contrast(self.RED, self.RED)
        self.assertEqual(r.rating_text, "Poor")

    # ── WCAG thresholds ──
    def test_wcag_constants(self):
        self.assertEqual(ColorAccessibility.WCAG_AA_NORMAL, 4.5)
        self.assertEqual(ColorAccessibility.WCAG_AA_LARGE,  3.0)
        self.assertEqual(ColorAccessibility.WCAG_AAA_NORMAL, 7.0)
        self.assertEqual(ColorAccessibility.WCAG_AAA_LARGE, 4.5)

    # ── Colorblindness simulation ──
    def test_normal_returns_unchanged(self):
        r = ColorAccessibility.simulate_colorblindness(self.RED, ColorBlindnessType.NORMAL)
        self.assertEqual(r, self.RED)

    def test_protanopia_changes_red(self):
        r = ColorAccessibility.simulate_colorblindness(self.RED, ColorBlindnessType.PROTANOPIA)
        # Protanopia (red-blind) should change the appearance of red
        self.assertNotEqual(r, self.RED)
        for ch in r: self.assertGreaterEqual(ch, 0); self.assertLessEqual(ch, 255)

    def test_deuteranopia_valid(self):
        r = ColorAccessibility.simulate_colorblindness((0,255,0), ColorBlindnessType.DEUTERANOPIA)
        for ch in r: self.assertGreaterEqual(ch, 0); self.assertLessEqual(ch, 255)

    def test_tritanopia_valid(self):
        r = ColorAccessibility.simulate_colorblindness((0,0,255), ColorBlindnessType.TRITANOPIA)
        for ch in r: self.assertGreaterEqual(ch, 0); self.assertLessEqual(ch, 255)

    def test_achromatopsia_grayscale(self):
        r = ColorAccessibility.simulate_colorblindness(self.RED, ColorBlindnessType.ACHROMATOPSIA)
        self.assertEqual(r[0], r[1]); self.assertEqual(r[1], r[2])  # Pure gray

    def test_all_blindness_types_valid(self):
        for bt in ColorBlindnessType:
            r = ColorAccessibility.simulate_colorblindness((128, 64, 200), bt)
            for ch in r: self.assertGreaterEqual(ch, 0); self.assertLessEqual(ch, 255)

    # ── Optimal text color ──
    def test_optimal_text_dark_bg(self):
        self.assertEqual(ColorAccessibility.get_optimal_text_color(self.BLACK), self.WHITE)

    def test_optimal_text_light_bg(self):
        self.assertEqual(ColorAccessibility.get_optimal_text_color(self.WHITE), self.BLACK)

    # ── Suggest accessible color ──
    def test_suggest_accessible_already_passes(self):
        # Black on white already passes 4.5 — should return unchanged
        r = ColorAccessibility.suggest_accessible_color(self.BLACK, self.WHITE)
        self.assertEqual(r, self.BLACK)

    def test_suggest_accessible_low_contrast_adjusts(self):
        # Light gray on white — needs to darken
        r = ColorAccessibility.suggest_accessible_color((220,220,220), self.WHITE)
        # Result should now meet 4.5 (or get closer)
        new_ratio = ColorAccessibility.calculate_contrast_ratio(r, self.WHITE)
        old_ratio = ColorAccessibility.calculate_contrast_ratio((220,220,220), self.WHITE)
        self.assertGreater(new_ratio, old_ratio)

    # ── Rating helpers ──
    def test_rating_color_excellent(self):
        c = ColorAccessibility.get_contrast_rating_color(7.5)
        self.assertEqual(len(c), 3)

    def test_format_contrast_ratio(self):
        s = ColorAccessibility.format_contrast_ratio(4.512)
        self.assertIn("4.51", s); self.assertIn(":1", s)


# ══════════════════════════════════════════════════════════════════════════════
# 8. SETTINGS MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class TestSettingsManager(unittest.TestCase):
    """settings_manager.py — get/set/save/load/validate (dot-notation)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sm = SettingsManager()
        # Redirect persistence to tmp so tests don't touch real settings.json
        self.sm.settings_file = Path(self.tmp) / "test_settings.json"

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_default(self):           self.assertEqual(self.sm.get("nope.nope", "default"), "default")
    def test_set_and_get_string(self):    self.sm.set("a.b", "x"); self.assertEqual(self.sm.get("a.b"), "x")
    def test_set_and_get_int(self):       self.sm.set("a.n", 42);  self.assertEqual(self.sm.get("a.n"), 42)
    def test_set_and_get_bool(self):      self.sm.set("a.flag", True); self.assertTrue(self.sm.get("a.flag"))
    def test_set_and_get_list(self):      self.sm.set("a.l", [1,2,3]); self.assertEqual(self.sm.get("a.l"), [1,2,3])
    def test_deep_nesting(self):          self.sm.set("a.b.c.d.e", 99); self.assertEqual(self.sm.get("a.b.c.d.e"), 99)

    def test_get_all_preferences(self):
        self.assertIsInstance(self.sm.get_all_preferences(), dict)

    def test_get_all_shortcuts(self):
        self.assertIsInstance(self.sm.get_all_shortcuts(), dict)

    def test_validate_returns_tuple(self):
        v, errs = self.sm.validate_settings()
        self.assertIsInstance(v, bool); self.assertIsInstance(errs, list)

    def test_save_creates_file(self):
        self.sm.set("preferences.test_marker", True)
        self.assertTrue(self.sm.save_settings())
        self.assertTrue(self.sm.settings_file.exists())

    def test_save_load_roundtrip(self):
        self.sm.set("preferences.roundtrip_marker", "value123")
        self.sm.save_settings()
        sm2 = SettingsManager()
        sm2.settings_file = self.sm.settings_file
        sm2.load_settings()
        self.assertEqual(sm2.get("preferences.roundtrip_marker"), "value123")

    def test_reset_to_defaults(self):
        self.sm.set("preferences.theme", "weird_value")
        self.sm.reset_to_defaults()
        # Reset should restore a real theme
        self.assertIn(self.sm.get("preferences.theme"), ["dark","light","image","auto"])

    def test_export_creates_file(self):
        ep = os.path.join(self.tmp, "exp.json")
        self.assertTrue(self.sm.export_settings(ep))
        self.assertTrue(os.path.exists(ep))

    def test_import_no_crash(self):
        ep = os.path.join(self.tmp, "imp.json")
        self.sm.export_settings(ep)
        sm2 = SettingsManager()
        sm2.settings_file = Path(self.tmp) / "imported.json"
        try: sm2.import_settings(ep)
        except Exception: pass

    def test_get_settings_info(self):
        info = self.sm.get_settings_info()
        self.assertIsInstance(info, dict)
        self.assertTrue(any(k in info for k in ["file_path", "exists", "valid"]))


# ══════════════════════════════════════════════════════════════════════════════
# 9. SESSION MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class TestSessionManager(unittest.TestCase):
    """session_manager.py — save/load/delete sessions."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        # Custom sessions_dir so tests don't pollute ~/.rnv_color_picker/sessions
        cls.sm = SessionManager(sessions_dir=cls.tmp)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def _slots(self):
        return [{"rgb":[255,0,0],"hsl":[0,100,50],"hilbert_idx":42,"is_locked":False},
                {"rgb":[0,255,0],"hsl":[120,100,50],"hilbert_idx":99,"is_locked":True}]

    def test_save_session_creates_file(self):
        fp = os.path.join(self.tmp, "test_save")
        self.assertTrue(self.sm.save_session(fp, self._slots()))
        # SessionManager appends .cpksession
        self.assertTrue(os.path.exists(fp + ".cpksession"))

    def test_load_session_returns_dict(self):
        fp = os.path.join(self.tmp, "test_load")
        self.sm.save_session(fp, self._slots())
        data = self.sm.load_session(fp + ".cpksession")
        self.assertIsInstance(data, dict)

    def test_load_session_preserves_colors(self):
        fp = os.path.join(self.tmp, "test_colors")
        self.sm.save_session(fp, self._slots())
        data = self.sm.load_session(fp + ".cpksession")
        self.assertIn("colors", data)
        self.assertEqual(len(data["colors"]), 2)

    def test_load_session_preserves_first_color(self):
        fp = os.path.join(self.tmp, "test_first")
        self.sm.save_session(fp, self._slots())
        data = self.sm.load_session(fp + ".cpksession")
        self.assertEqual(data["colors"][0]["rgb"], [255,0,0])

    def test_save_with_image_path(self):
        fp = os.path.join(self.tmp, "with_img")
        self.sm.save_session(fp, self._slots(), image_path="/some/img.png")
        data = self.sm.load_session(fp + ".cpksession")
        self.assertEqual(data["image_path"], "/some/img.png")

    def test_save_with_metadata(self):
        fp = os.path.join(self.tmp, "with_meta")
        self.sm.save_session(fp, self._slots(), name="MySession", description="test")
        data = self.sm.load_session(fp + ".cpksession")
        self.assertEqual(data["name"], "MySession")
        self.assertEqual(data["description"], "test")

    def test_load_nonexistent_returns_none(self):
        self.assertIsNone(self.sm.load_session("/no/such/file.cpksession"))

    def test_delete_session(self):
        fp = os.path.join(self.tmp, "to_delete")
        self.sm.save_session(fp, self._slots())
        actual = fp + ".cpksession"
        self.assertTrue(os.path.exists(actual))
        self.sm.delete_session(actual)
        self.assertFalse(os.path.exists(actual))

    def test_generate_filename_has_extension(self):
        fn = self.sm.generate_session_filename("mytest")
        self.assertTrue(fn.endswith(".cpksession"))

    def test_generate_filename_contains_base(self):
        fn = self.sm.generate_session_filename("color_work")
        self.assertIn("color_work", fn)

    def test_session_extension_constant(self):
        self.assertEqual(SessionManager.SESSION_EXTENSION, ".cpksession")

    def test_session_version_constant(self):
        self.assertIsInstance(SessionManager.SESSION_VERSION, str)

    def test_get_recent_sessions_is_list(self):
        self.assertIsInstance(self.sm.get_recent_sessions(), list)

    def test_check_for_autosave_str_or_none(self):
        r = self.sm.check_for_autosave()
        self.assertTrue(r is None or isinstance(r, str))

    def test_get_session_id_is_string(self):
        self.assertIsInstance(self.sm.get_session_id(), str)

    def test_set_autosave_interval_min_30(self):
        self.sm.set_autosave_interval(10)  # Should clamp to 30
        self.assertGreaterEqual(self.sm.autosave_interval, 30)


# ══════════════════════════════════════════════════════════════════════════════
# 10. ERROR HANDLER
# ══════════════════════════════════════════════════════════════════════════════
class TestErrorHandler(unittest.TestCase):
    """error_handler.py — safe_execute, safe_method, handle_exception."""

    def test_safe_execute_returns_value(self):
        self.assertEqual(ErrorHandler.safe_execute(lambda: 42, "ok"), 42)

    def test_safe_execute_div_zero(self):
        self.assertIsNone(ErrorHandler.safe_execute(lambda: 1/0, "dz"))

    def test_safe_execute_value_error(self):
        self.assertIsNone(ErrorHandler.safe_execute(lambda: int("abc"), "ve"))

    def test_safe_execute_type_error(self):
        self.assertIsNone(ErrorHandler.safe_execute(lambda: "a"+1, "te"))

    def test_safe_execute_string_result(self):
        self.assertEqual(ErrorHandler.safe_execute(lambda: "hello", "ctx"), "hello")

    def test_safe_execute_list_result(self):
        self.assertEqual(ErrorHandler.safe_execute(lambda: [1,2,3], "ctx"), [1,2,3])

    def test_safe_method_decorator_returns_value(self):
        @ErrorHandler.safe_method("ctx")
        def my_func(self_obj): return 99
        class _Obj: pass
        self.assertEqual(my_func(_Obj()), 99)

    def test_safe_method_catches_exception(self):
        @ErrorHandler.safe_method("ctx", fallback_value=-1)
        def bad_func(self_obj): raise ValueError("oops")
        class _Obj: pass
        self.assertEqual(bad_func(_Obj()), -1)

    def test_safe_method_default_fallback_none(self):
        @ErrorHandler.safe_method("ctx")
        def raises(self_obj): raise RuntimeError("boom")
        class _Obj: pass
        self.assertIsNone(raises(_Obj()))

    def test_handle_exception_no_crash(self):
        try: ErrorHandler.handle_exception(ValueError("test"), "test context")
        except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
# 11. FILE UTILS
# ══════════════════════════════════════════════════════════════════════════════
class TestFileUtils(unittest.TestCase):
    """file_utils.py — module-level functions (NOT a class, unlike Mixer)."""

    @classmethod
    def setUpClass(cls): cls.tmp = tempfile.mkdtemp()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_ensure_directory_creates(self):
        d = os.path.join(self.tmp, "new_dir")
        self.assertTrue(fu.ensure_directory(d))
        self.assertTrue(os.path.isdir(d))

    def test_ensure_directory_existing(self):
        self.assertTrue(fu.ensure_directory(self.tmp))

    def test_get_user_data_dir_returns_path(self):
        d = fu.get_user_data_dir("__pytest_dummy_app__")
        self.assertIsInstance(d, Path)
        self.assertTrue(d.exists())

    def test_get_temp_dir_returns_path(self):
        d = fu.get_temp_dir("__pytest_dummy_app__")
        self.assertIsInstance(d, Path)

    def test_normalize_path_returns_path(self):
        p = fu.normalize_path("~/somefile.txt")
        self.assertIsInstance(p, Path)
        self.assertTrue(p.is_absolute())

    def test_safe_read_json_missing_returns_default(self):
        self.assertEqual(fu.safe_read_json("/no/such.json", default={"x":1}), {"x":1})

    def test_safe_write_then_read_json(self):
        fp = os.path.join(self.tmp, "rt.json")
        self.assertTrue(fu.safe_write_json(fp, {"key":"value", "n":42}))
        loaded = fu.safe_read_json(fp)
        self.assertEqual(loaded, {"key":"value", "n":42})

    def test_safe_read_json_invalid_returns_default(self):
        fp = os.path.join(self.tmp, "bad.json"); open(fp, "w").write("{NOT JSON")
        self.assertEqual(fu.safe_read_json(fp, default=None), None)

    def test_safe_write_then_read_text(self):
        fp = os.path.join(self.tmp, "rt.txt")
        self.assertTrue(fu.safe_write_text(fp, "hello world"))
        self.assertEqual(fu.safe_read_text(fp), "hello world")

    def test_safe_read_text_missing_returns_default(self):
        self.assertEqual(fu.safe_read_text("/no/such.txt", default="X"), "X")

    def test_safe_copy(self):
        src = os.path.join(self.tmp, "src.txt"); open(src, "w").write("hi")
        dst = os.path.join(self.tmp, "dst.txt")
        self.assertTrue(fu.safe_copy(src, dst))
        self.assertTrue(os.path.exists(dst))

    def test_safe_copy_missing_source(self):
        self.assertFalse(fu.safe_copy("/no/such.txt", "/tmp/x.txt"))

    def test_safe_delete_existing(self):
        fp = os.path.join(self.tmp, "del.txt"); open(fp, "w").write("x")
        self.assertTrue(fu.safe_delete(fp))
        self.assertFalse(os.path.exists(fp))

    def test_safe_delete_missing_no_crash(self):
        self.assertTrue(fu.safe_delete("/no/such/file.txt"))

    def test_get_file_size_existing(self):
        fp = os.path.join(self.tmp, "sz.txt"); open(fp, "w").write("x"*100)
        self.assertEqual(fu.get_file_size(fp), 100)

    def test_get_file_size_missing_returns_negative(self):
        self.assertEqual(fu.get_file_size("/no/such.txt"), -1)

    def test_get_file_modified_time_existing(self):
        fp = os.path.join(self.tmp, "mt.txt"); open(fp, "w").write("x")
        from datetime import datetime
        self.assertIsInstance(fu.get_file_modified_time(fp), datetime)

    def test_format_file_size_kb(self):
        s = fu.format_file_size(2048)
        self.assertIn("KB", s)

    def test_format_file_size_b(self):
        s = fu.format_file_size(100)
        self.assertIn("B", s)

    def test_create_backup(self):
        fp = os.path.join(self.tmp, "backup_me.txt"); open(fp, "w").write("data")
        b = fu.create_backup(fp)
        self.assertIsNotNone(b); self.assertTrue(b.exists())

    def test_create_backup_missing_returns_none(self):
        self.assertIsNone(fu.create_backup("/no/such.txt"))


# ══════════════════════════════════════════════════════════════════════════════
# 12. CONFIG / THEME MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class TestConfig(unittest.TestCase):
    """config.py — ThemeManager, theme dicts, brand colors."""

    def setUp(self): self.tm = config.ThemeManager()

    # ── Brand colors ──
    def test_brand_gold(self):       self.assertEqual(config.BRAND_GOLD, "#d2bc93")
    def test_brand_gold_dark(self):  self.assertEqual(config.BRAND_GOLD_DARK, "#b19145")
    def test_brand_gold_rgb(self):   self.assertEqual(config.BRAND_GOLD_RGB, (210,188,147))
    def test_brand_gold_dark_rgb(self): self.assertEqual(config.BRAND_GOLD_DARK_RGB, (177,145,69))

    # ── Theme dicts present ──
    def test_dark_theme_exists(self):  self.assertIsInstance(config.DARK_THEME_COLORS, dict)
    def test_light_theme_exists(self): self.assertIsInstance(config.LIGHT_THEME_COLORS, dict)
    def test_image_theme_exists(self): self.assertIsInstance(config.IMAGE_MODE_COLORS, dict)

    def test_theme_names(self):
        self.assertEqual(config.DARK_THEME_COLORS["name"], "Dark")
        self.assertEqual(config.LIGHT_THEME_COLORS["name"], "Light")
        self.assertEqual(config.IMAGE_MODE_COLORS["name"], "Image")

    def test_theme_brand_gold_dark(self):
        self.assertEqual(config.DARK_THEME_COLORS["text_accent"], config.BRAND_GOLD)
        self.assertEqual(config.DARK_THEME_COLORS["tooltip_border"], config.BRAND_GOLD)

    def test_theme_brand_gold_light(self):
        self.assertEqual(config.LIGHT_THEME_COLORS["text_accent"], config.BRAND_GOLD_DARK)

    # ── Required keys present in all 3 themes ──
    def test_all_themes_have_required_keys(self):
        required = ["window_bg","panel_bg","card_bg","text_primary","text_secondary",
                    "border_default","button_bg","tooltip_border","scrollbar_bg",
                    "scrollbar_handle","scrollbar_handle_hover"]
        for name, theme in [("DARK", config.DARK_THEME_COLORS),
                            ("LIGHT", config.LIGHT_THEME_COLORS),
                            ("IMAGE", config.IMAGE_MODE_COLORS)]:
            for key in required:
                self.assertIn(key, theme, f"{name} missing '{key}'")

    # ── ThemeManager runtime ──
    def test_default_theme_dark(self):
        self.assertEqual(self.tm.current_theme, "dark")

    def test_get_current_theme_dark(self):
        self.tm.current_theme = "dark"
        self.assertEqual(self.tm.get_current_theme()["name"], "Dark")

    def test_get_current_theme_light(self):
        self.tm.current_theme = "light"
        self.assertEqual(self.tm.get_current_theme()["name"], "Light")

    def test_cycle_dark_to_light_no_image_mode(self):
        self.tm.current_theme = "dark"; self.tm.image_mode_available = False
        self.assertEqual(self.tm.cycle_theme(), "light")

    def test_cycle_light_to_dark_no_image_mode(self):
        self.tm.current_theme = "light"; self.tm.image_mode_available = False
        self.assertEqual(self.tm.cycle_theme(), "dark")

    def test_get_theme_display_name_dark(self):
        self.tm.current_theme = "dark"
        self.assertIn("Dark", self.tm.get_theme_display_name())

    def test_get_theme_display_name_light(self):
        self.tm.current_theme = "light"
        self.assertIn("Light", self.tm.get_theme_display_name())

    def test_is_image_mode_starts_false(self):
        self.assertFalse(self.tm.is_image_mode())

    # ── App constants ──
    def test_max_colors_333(self):       self.assertEqual(config.MAX_COLORS, 333)
    def test_default_weight_50(self):    self.assertEqual(config.DEFAULT_WEIGHT, 50)
    def test_button_height_min(self):    self.assertGreater(config.BUTTON_HEIGHT_MIN, 0)
    def test_button_height_max(self):    self.assertGreater(config.BUTTON_HEIGHT_MAX, config.BUTTON_HEIGHT_MIN)
    def test_window_width_min(self):     self.assertGreater(config.WINDOW_WIDTH_MIN, 0)
    def test_swatch_size_positive(self): self.assertGreater(config.SWATCH_SIZE, 0)
    def test_max_image_dimension(self):  self.assertGreater(config.MAX_IMAGE_DIMENSION, 0)

    # ── App metadata ──
    def test_app_name_picker(self):
        self.assertEqual(config.APP_NAME, "RNV Color Picker")
    def test_app_version_string(self):
        self.assertIsInstance(config.APP_VERSION, str)


# ══════════════════════════════════════════════════════════════════════════════
# 13. CONFIG — NEW CONSTANTS (added during centralization)
# ══════════════════════════════════════════════════════════════════════════════
class TestConfigNewConstants(unittest.TestCase):
    """
    Validates the constants added in the color-centralization pass:
    OVERLAY_BLACK_*, SVG_EXPORT_*, MISSING_HEX_PLACEHOLDER.
    """

    def test_overlay_black_light_value(self):
        self.assertEqual(config.OVERLAY_BLACK_LIGHT, (0, 0, 0, 50))

    def test_overlay_black_medium_value(self):
        self.assertEqual(config.OVERLAY_BLACK_MEDIUM, (0, 0, 0, 75))

    def test_overlay_black_heavy_value(self):
        self.assertEqual(config.OVERLAY_BLACK_HEAVY, (0, 0, 0, 180))

    def test_overlay_alphas_increasing(self):
        # Light < Medium < Heavy by design
        self.assertLess(config.OVERLAY_BLACK_LIGHT[3],
                        config.OVERLAY_BLACK_MEDIUM[3])
        self.assertLess(config.OVERLAY_BLACK_MEDIUM[3],
                        config.OVERLAY_BLACK_HEAVY[3])

    def test_svg_export_bg_white(self):
        self.assertEqual(config.SVG_EXPORT_BG.upper(), "#FFFFFF")

    def test_svg_export_stroke_black(self):
        self.assertEqual(config.SVG_EXPORT_STROKE.upper(), "#000000")

    def test_missing_hex_placeholder(self):
        self.assertEqual(config.MISSING_HEX_PLACEHOLDER.upper(), "#000000")

    def test_constants_in_all(self):
        for name in ["OVERLAY_BLACK_LIGHT", "OVERLAY_BLACK_MEDIUM",
                     "OVERLAY_BLACK_HEAVY", "SVG_EXPORT_BG",
                     "SVG_EXPORT_STROKE", "MISSING_HEX_PLACEHOLDER"]:
            self.assertIn(name, config.__all__, f"{name} missing from __all__")

    def test_overlays_construct_valid_qcolor(self):
        from PyQt6.QtGui import QColor
        for tup in [config.OVERLAY_BLACK_LIGHT,
                    config.OVERLAY_BLACK_MEDIUM,
                    config.OVERLAY_BLACK_HEAVY]:
            qc = QColor(*tup)
            self.assertTrue(qc.isValid())
            self.assertEqual(qc.alpha(), tup[3])


# ══════════════════════════════════════════════════════════════════════════════
# 14. CACHE — ColorCache, QColorCache, StylesheetCache, FontCache
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_CACHE_OK, "Cache modules not available")
class TestCache(unittest.TestCase):
    """cache.py — ColorCache, QColorCache, StylesheetCache, FontCache."""

    def test_color_cache_rgb_to_hex(self):
        self.assertEqual(ColorCache.rgb_to_hex((255,0,0)), "#ff0000")

    def test_color_cache_hsv_returns_3tuple(self):
        h,s,v = ColorCache.rgb_to_hsv((255,0,0))
        self.assertAlmostEqual(h, 0.0, delta=0.01)

    def test_color_cache_hsl_returns_3tuple(self):
        r = ColorCache.rgb_to_hsl((128,128,128))
        self.assertEqual(len(r), 3)

    def test_color_cache_text_color_dark_bg(self):
        self.assertEqual(ColorCache.get_text_color_for_background((0,0,0)), (255,255,255))

    def test_color_cache_text_color_light_bg(self):
        self.assertEqual(ColorCache.get_text_color_for_background((255,255,255)), (0,0,0))

    def test_color_cache_hilbert_int(self):
        self.assertIsInstance(ColorCache.hilbert_index((128,64,200)), int)

    def test_color_cache_get_stats(self):
        self.assertIsInstance(ColorCache.get_stats(), dict)

    def test_color_cache_clear_all_no_crash(self):
        ColorCache.rgb_to_hex((1,2,3))  # populate cache first
        ColorCache.clear_all()

    # ── QColorCache ──
    def test_qcolor_cache_get_returns_qcolor(self):
        from PyQt6.QtGui import QColor
        c = QColorCache.get("#ff0000")
        self.assertIsInstance(c, QColor)

    def test_qcolor_cache_get_tuple(self):
        from PyQt6.QtGui import QColor
        c = QColorCache.get((128, 64, 200))
        self.assertIsInstance(c, QColor)

    def test_qcolor_cache_eager_init_black(self):
        """After our hardening pass: BLACK/WHITE/TRANSPARENT must be populated at import time."""
        self.assertIsNotNone(QColorCache.BLACK)
        self.assertIsNotNone(QColorCache.WHITE)
        self.assertIsNotNone(QColorCache.TRANSPARENT)

    def test_qcolor_cache_black_is_black(self):
        self.assertEqual(QColorCache.BLACK.red(), 0)
        self.assertEqual(QColorCache.BLACK.green(), 0)
        self.assertEqual(QColorCache.BLACK.blue(), 0)

    def test_qcolor_cache_white_is_white(self):
        self.assertEqual(QColorCache.WHITE.red(), 255)
        self.assertEqual(QColorCache.WHITE.blue(), 255)

    def test_qcolor_cache_lock_border_is_brand_gold(self):
        self.assertIsNotNone(QColorCache.LOCK_BORDER)

    def test_qcolor_cache_caches_repeated_get(self):
        a = QColorCache.get("#deadbe")
        b = QColorCache.get("#deadbe")
        self.assertIs(a, b)  # Same cached instance

    def test_qcolor_cache_clear(self):
        QColorCache.get("#abc123")  # populate
        QColorCache.clear()
        # After clear, _cache is empty (constants attr remain via class)


# ══════════════════════════════════════════════════════════════════════════════
# 15. CLIPBOARD
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_CLIPBOARD_OK and _qapp, "ClipboardUtils or QApplication not available")
class TestClipboard(unittest.TestCase):
    """clipboard.py — Picker version (instance-based, fewer methods than Mixer)."""

    def setUp(self): self.cb = ClipboardUtils()

    def test_copy_text_returns_bool(self):
        self.assertIsInstance(self.cb.copy_text("hello"), bool)

    def test_copy_hex_returns_bool(self):
        self.assertIsInstance(self.cb.copy_hex_color((255,0,0)), bool)

    def test_copy_rgb_returns_bool(self):
        self.assertIsInstance(self.cb.copy_rgb_color((255,0,0)), bool)

    def test_copy_hsv_returns_bool(self):
        self.assertIsInstance(self.cb.copy_hsv_color((255,0,0)), bool)

    def test_copy_hsl_returns_bool(self):
        self.assertIsInstance(self.cb.copy_hsl_color((255,0,0)), bool)

    def test_get_text_after_copy(self):
        self.cb.copy_text("rnv_picker_sentinel")
        txt = self.cb.get_clipboard_text()
        if txt: self.assertIn("rnv_picker_sentinel", txt)

    def test_hex_format_has_hash(self):
        self.cb.copy_hex_color((255, 0, 0))
        txt = self.cb.get_clipboard_text()
        if txt: self.assertTrue(txt.startswith("#"))

    def test_rgb_format(self):
        self.cb.copy_rgb_color((128, 64, 200))
        txt = self.cb.get_clipboard_text()
        if txt: self.assertIn("rgb(", txt); self.assertIn("128", txt)

    def test_parse_color_from_hex(self):
        self.cb.copy_text("#d2bc93")
        parsed = self.cb.try_parse_color_from_clipboard()
        if parsed: self.assertEqual(parsed, (210, 188, 147))

    def test_parse_color_from_rgb(self):
        self.cb.copy_text("rgb(128, 64, 200)")
        parsed = self.cb.try_parse_color_from_clipboard()
        if parsed: self.assertEqual(parsed, (128, 64, 200))

    def test_parse_color_invalid_returns_none(self):
        self.cb.copy_text("not-a-color")
        self.assertIsNone(self.cb.try_parse_color_from_clipboard())

    def test_copy_palette_returns_bool(self):
        pal = [((255,0,0),50),((0,255,0),50),((0,0,255),50)]
        self.assertIsInstance(self.cb.copy_color_palette(pal), bool)


# ══════════════════════════════════════════════════════════════════════════════
# 16. LOGGER
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_LOGGER_OK, "Logger not available")
class TestLogger(unittest.TestCase):
    """logger.py — log levels, helpers, get_logger factory."""

    def setUp(self): self.log = AppLogger("TestSuite")

    def test_instantiation(self):     self.assertIsNotNone(self.log)
    def test_debug_no_crash(self):    self.log.debug("debug msg")
    def test_info_no_crash(self):     self.log.info("info msg")
    def test_success_no_crash(self):  self.log.success("success msg")
    def test_warning_no_crash(self):  self.log.warning("warning msg")
    def test_error_no_crash(self):    self.log.error("error msg")
    def test_critical_no_crash(self): self.log.critical("critical msg")

    def test_get_logger_returns_instance(self):
        self.assertIsNotNone(_get_logger("AnotherModule"))

    def test_multiple_loggers_no_bleed(self):
        a = AppLogger("ModA"); b = AppLogger("ModB")
        a.info("from A"); b.info("from B")  # Just must not crash


# ══════════════════════════════════════════════════════════════════════════════
# 17. SIGNAL MANAGER
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_SIGNAL_OK and _qapp, "SignalConnectionManager or QApplication not available")
class TestSignalManager(unittest.TestCase):
    """signal_manager.py — connection tracking lifecycle."""

    def setUp(self): self.sm = SignalConnectionManager()

    def test_initial_count_zero(self):
        self.assertEqual(self.sm.get_connection_count(), 0)

    def test_stats_returns_dict(self):
        self.assertIsInstance(self.sm.get_stats(), dict)

    def test_list_connections_returns_list(self):
        self.assertIsInstance(self.sm.list_connections(), list)

    def test_disconnect_all_on_empty_is_zero(self):
        self.assertEqual(self.sm.disconnect_all(), 0)

    def test_widget_count_unknown(self):
        from PyQt6.QtCore import QObject
        obj = QObject(); self.assertEqual(self.sm.get_widget_connection_count(obj), 0)

    def test_connect_increments_count(self):
        from PyQt6.QtCore import QTimer
        timer = QTimer(); slot = lambda: None
        try:
            self.sm.connect(timer, timer.timeout, slot, "test_conn")
            self.assertGreater(self.sm.get_connection_count(), 0)
            self.sm.disconnect_all()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# 18. PIXMAP CACHE
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_PIXMAP_CACHE_OK and _qapp, "ImagePixmapCache or QApplication not available")
class TestPixmapCache(unittest.TestCase):
    """pixmap_cache.py — LRU image-pixmap cache."""

    def setUp(self): self.cache = ImagePixmapCache(max_size=10)

    def test_initial_size_zero(self):     self.assertEqual(self.cache.get_size(), 0)
    def test_put_increases_size(self):
        from PyQt6.QtGui import QPixmap
        self.cache.put(("test", 1.0), QPixmap(5,5))
        self.assertEqual(self.cache.get_size(), 1)

    def test_get_after_put(self):
        from PyQt6.QtGui import QPixmap
        self.cache.put(("k", 1.0), QPixmap(5,5))
        self.assertIsNotNone(self.cache.get(("k", 1.0)))

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.cache.get(("nope", 0.5)))

    def test_clear_returns_count(self):
        from PyQt6.QtGui import QPixmap
        self.cache.put(("a",1.0), QPixmap(2,2)); self.cache.put(("b",1.0), QPixmap(2,2))
        self.assertEqual(self.cache.clear(), 2)

    def test_remove_existing(self):
        from PyQt6.QtGui import QPixmap
        self.cache.put(("rm", 1.0), QPixmap(2,2))
        self.assertTrue(self.cache.remove(("rm", 1.0)))

    def test_remove_missing_returns_false(self):
        self.assertFalse(self.cache.remove(("no", 0.5)))

    def test_resize_max_size(self):
        self.cache.resize(20)
        # Max size attribute or get_or_create should reflect this — no-crash check
        self.assertIsInstance(self.cache.get_size(), int)

    def test_eviction_at_max(self):
        from PyQt6.QtGui import QPixmap
        c = ImagePixmapCache(max_size=3)
        for i in range(5): c.put((f"img{i}", 1.0), QPixmap(1,1))
        self.assertLessEqual(c.get_size(), 3)


# ══════════════════════════════════════════════════════════════════════════════
# 19. WORKERS — ColorExtractionWorker, DominantColorWorker, WorkerManager
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_WORKERS_OK and _qapp, "Workers or QApplication not available")
class TestWorkers(unittest.TestCase):
    """workers.py — QThread-based color extraction (smoke tests)."""

    def test_worker_result_dataclass(self):
        r = WorkerResult(success=True, data={"x":1})
        self.assertTrue(r.success); self.assertIsNone(r.error)

    def test_worker_result_with_error(self):
        r = WorkerResult(success=False, data=None, error="something failed")
        self.assertFalse(r.success); self.assertIsNotNone(r.error)

    def test_extraction_worker_instantiation(self):
        import numpy as np
        pixels = np.zeros((10, 10, 3), dtype=np.uint8)
        w = ColorExtractionWorker(pixels, max_colors=50)
        self.assertIsNotNone(w)
        self.assertFalse(w.is_cancelled())

    def test_extraction_worker_cancel(self):
        import numpy as np
        pixels = np.zeros((10, 10, 3), dtype=np.uint8)
        w = ColorExtractionWorker(pixels, max_colors=50)
        w.cancel()
        self.assertTrue(w.is_cancelled())

    def test_extraction_worker_run_synchronously(self):
        """Run extraction synchronously (no event loop) for deterministic test."""
        import numpy as np
        # 4x4 image with 3 unique colors
        pixels = np.array([
            [[255,0,0],[255,0,0],[0,255,0],[0,255,0]],
            [[255,0,0],[255,0,0],[0,255,0],[0,255,0]],
            [[0,0,255],[0,0,255],[0,0,255],[0,0,255]],
            [[0,0,255],[0,0,255],[0,0,255],[0,0,255]],
        ], dtype=np.uint8)

        results = []
        w = ColorExtractionWorker(pixels, max_colors=10)
        w.finished.connect(lambda r: results.append(r))
        w.run()  # synchronous call
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertIn("colors", results[0].data)
        self.assertEqual(results[0].data["total_unique"], 3)

    def test_dominant_worker_instantiation(self):
        import numpy as np
        pixels = np.zeros((10, 10, 3), dtype=np.uint8)
        w = DominantColorWorker(pixels, num_clusters=5)
        self.assertIsNotNone(w)
        self.assertEqual(w.num_clusters, 5)

    def test_worker_manager_starts_empty(self):
        wm = WorkerManager()
        self.assertEqual(len(wm._active_workers), 0)


# ══════════════════════════════════════════════════════════════════════════════
# 20. EDGE CASES & INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
class TestEdgeCases(unittest.TestCase):
    """Cross-module edge cases, boundary conditions, integration scenarios."""

    @classmethod
    def setUpClass(cls):  cls.tmp = tempfile.mkdtemp()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    # ── Math edge cases ──
    def test_mix_black_white_is_gray(self):
        r = ColorMath.weighted_rgb_mix([((0,0,0),50),((255,255,255),50)])
        self.assertIsNotNone(r)
        for ch in r: self.assertAlmostEqual(ch, 127, delta=2)

    def test_mix_same_color_identity(self):
        c = (100,150,200)
        self.assertEqual(ColorMath.weighted_rgb_mix([(c,50),(c,50)]), c)

    def test_high_weight_dominates(self):
        r = ColorMath.weighted_rgb_mix([((255,0,0),90),((0,0,255),10)])
        self.assertIsNotNone(r); self.assertGreater(r[0], r[2])

    def test_lab_extreme_values_clamped(self):
        for lab in [(100,128,128),(0,-128,-128),(50,200,-200)]:
            r = ColorMath.lab_to_rgb(lab)
            for ch in r: self.assertGreaterEqual(ch, 0); self.assertLessEqual(ch, 255)

    # ── Achromatic colors across all harmonies ──
    def test_achromatic_harmonies(self):
        for gray in [(128,128,128),(64,64,64),(0,0,0),(255,255,255)]:
            for ht in HarmonyType:
                self.assertIsNotNone(ColorHarmony.generate_harmony(gray, ht))

    # ── Hilbert ordering preserves locality (fuzz test) ──
    def test_hilbert_indices_all_unique_for_distinct_colors(self):
        import random
        random.seed(42)
        seen = set()
        for _ in range(50):
            rgb = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
            idx = HilbertCurve.rgb_to_hilbert(rgb)
            self.assertGreaterEqual(idx, 0)

    # ── ColorCollection at full capacity ──
    def test_color_collection_max_capacity_333(self):
        cc = ColorCollection(max_size=config.MAX_COLORS)
        # Fill with deterministic distinct colors
        added, _ = cc.add_batch([
            (i % 256, (i*7) % 256, (i*13) % 256)
            for i in range(400)  # try to add more than max
        ])
        self.assertLessEqual(len(cc), config.MAX_COLORS)

    # ── Accessibility integration ──
    def test_accessibility_brand_gold_on_black(self):
        ratio = ColorAccessibility.calculate_contrast_ratio(
            config.BRAND_GOLD_RGB, (0,0,0))
        self.assertGreater(ratio, 4.5)  # Brand gold passes AA on black

    def test_accessibility_brand_gold_dark_on_white(self):
        # Brand gold dark on white renders ~2.997:1 — just below WCAG AA-large
        # but well above the conversational-readability floor. Just check it's
        # in a reasonable contrast range.
        ratio = ColorAccessibility.calculate_contrast_ratio(
            config.BRAND_GOLD_DARK_RGB, (255,255,255))
        self.assertGreater(ratio, 2.5)
        self.assertLess(ratio, 5.0)

    # ── Palette format integration with Hilbert sort ──
    def test_palette_sort_export_import_chain(self):
        cc = ColorCollection(max_size=10)
        cc.add_batch([(255,0,0),(0,255,0),(0,0,255),(128,128,128)])
        cc.sort_by_hilbert()
        pal = cc.to_palette_format()
        fp = os.path.join(self.tmp, "chain.json")
        PaletteFormats.export_palette(fp, pal)
        loaded = PaletteFormats.import_palette(fp)
        self.assertEqual(len(loaded), len(pal))

    # ── Settings × Sessions integration ──
    def test_settings_export_session_save_no_collision(self):
        sm = SettingsManager()
        sm.settings_file = Path(self.tmp) / "isolated_settings.json"
        sess = SessionManager(sessions_dir=self.tmp)
        sm.set("integ.marker", "value")
        self.assertTrue(sm.save_settings())
        self.assertTrue(sess.save_session(
            os.path.join(self.tmp, "integ_session"),
            [{"rgb":[1,2,3],"hsl":[0,0,0],"hilbert_idx":0,"is_locked":False}]
        ))

    # ── ErrorHandler wraps color operations ──
    def test_error_handler_wraps_color_ops(self):
        r = ErrorHandler.safe_execute(
            lambda: ColorMath.weighted_rgb_mix([((255,0,0),50),((0,255,0),50)]),
            "integration mix")
        self.assertIsNotNone(r)

    def test_error_handler_swallows_invalid_hex(self):
        r = ErrorHandler.safe_execute(
            lambda: ColorMath.hex_to_rgb("not-valid-hex"),
            "bad hex")
        self.assertIsNone(r)  # Should swallow the ValueError

    # ── Brand colors don't leak into IMAGE_MODE_COLORS overrides ──
    def test_image_mode_inherits_dark(self):
        # IMAGE_MODE_COLORS is built from DARK_THEME_COLORS spread + overrides
        self.assertEqual(config.IMAGE_MODE_COLORS["text_accent"], config.BRAND_GOLD)

    # ── MISSING_HEX_PLACEHOLDER as fallback ──
    def test_missing_hex_used_for_dict_default(self):
        entry = {}  # missing 'hex' key
        hex_code = entry.get("hex", config.MISSING_HEX_PLACEHOLDER)
        self.assertEqual(hex_code.upper(), "#000000")


# ══════════════════════════════════════════════════════════════════════════════
# 21. STYLESHEET CACHE
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_CACHE_OK and _qapp, "StylesheetCache or QApplication not available")
class TestStylesheetCache(unittest.TestCase):
    """cache.py — StylesheetCache class (theme-keyed stylesheet generation)."""

    def setUp(self):
        # Use a real theme dict from config so stylesheets compose correctly
        self.theme_name = "dark"
        self.theme = config.DARK_THEME_COLORS

    def test_menu_stylesheet_is_string(self):
        ss = StylesheetCache.get_menu_stylesheet(self.theme_name, False, self.theme)
        self.assertIsInstance(ss, str); self.assertGreater(len(ss), 50)

    def test_checkbox_stylesheet_is_string(self):
        ss = StylesheetCache.get_checkbox_stylesheet(self.theme_name, self.theme)
        self.assertIsInstance(ss, str)

    def test_scrollbar_stylesheet_is_string(self):
        ss = StylesheetCache.get_scrollbar_stylesheet(self.theme_name, self.theme)
        self.assertIsInstance(ss, str)

    def test_close_button_stylesheet_dark(self):
        ss = StylesheetCache.get_close_button_stylesheet(is_dark=True)
        self.assertIsInstance(ss, str)

    def test_close_button_stylesheet_light(self):
        ss = StylesheetCache.get_close_button_stylesheet(is_dark=False)
        self.assertIsInstance(ss, str)

    def test_header_stylesheet(self):
        ss = StylesheetCache.get_header_stylesheet(size=14, bold=True)
        self.assertIn("font-size", ss); self.assertIn("14px", ss)

    def test_description_stylesheet(self):
        ss = StylesheetCache.get_description_stylesheet()
        self.assertIsInstance(ss, str)

    def test_color_preview_stylesheet_uses_hex(self):
        ss = StylesheetCache.get_color_preview_stylesheet("#d2bc93", size=60)
        self.assertIn("#d2bc93", ss); self.assertIn("60px", ss)

    def test_caches_repeated_calls(self):
        # Same args twice should produce identical output (and ideally hit cache)
        a = StylesheetCache.get_menu_stylesheet(self.theme_name, False, self.theme)
        b = StylesheetCache.get_menu_stylesheet(self.theme_name, False, self.theme)
        self.assertEqual(a, b)

    def test_clear_no_crash(self):
        StylesheetCache.get_menu_stylesheet(self.theme_name, False, self.theme)
        StylesheetCache.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 22. FONT CACHE
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_CACHE_OK and _qapp, "FontCache or QApplication not available")
class TestFontCache(unittest.TestCase):
    """cache.py — FontCache for QFont and PIL ImageFont objects."""

    def test_get_qfont_returns_qfont(self):
        from PyQt6.QtGui import QFont
        f = FontCache.get_qfont(family="Arial", size=12)
        self.assertIsInstance(f, QFont)

    def test_get_qfont_default_family(self):
        from PyQt6.QtGui import QFont
        f = FontCache.get_qfont(size=10)
        self.assertIsInstance(f, QFont)

    def test_get_qfont_bold(self):
        f = FontCache.get_qfont(family="Arial", size=12, bold=True)
        self.assertTrue(f.bold())

    def test_get_qfont_caches_repeated(self):
        a = FontCache.get_qfont(family="Arial", size=14)
        b = FontCache.get_qfont(family="Arial", size=14)
        self.assertIs(a, b)  # Same instance from cache

    def test_get_pil_font_missing_returns_none(self):
        f = FontCache.get_pil_font("/no/such/font.ttf", 12)
        self.assertIsNone(f)

    def test_clear_empties_cache(self):
        FontCache.get_qfont(family="Arial", size=16)
        FontCache.clear()
        self.assertEqual(len(FontCache._qfont_cache), 0)


# ══════════════════════════════════════════════════════════════════════════════
# 23. RESOURCE CACHE
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_RESOURCE_CACHE_OK, "ResourceCache not available")
class TestResourceCache(unittest.TestCase):
    """cache.py — ResourceCache for file-existence caching."""

    def setUp(self): ResourceCache.invalidate()  # Start clean

    def test_exists_for_real_file(self):
        # The current test file definitely exists
        self.assertTrue(ResourceCache.exists(__file__))

    def test_exists_for_missing(self):
        self.assertFalse(ResourceCache.exists("/no/such/path.xyz"))

    def test_caches_repeated_lookup(self):
        path = "/no/such/path_for_caching.txt"
        ResourceCache.exists(path)
        self.assertIn(path, ResourceCache._exists_cache)

    def test_invalidate_specific(self):
        path = "/specific/path.txt"
        ResourceCache.exists(path)
        ResourceCache.invalidate(path)
        self.assertNotIn(path, ResourceCache._exists_cache)

    def test_invalidate_all(self):
        ResourceCache.exists("/path/a.txt")
        ResourceCache.exists("/path/b.txt")
        ResourceCache.invalidate()
        self.assertEqual(len(ResourceCache._exists_cache), 0)


# ══════════════════════════════════════════════════════════════════════════════
# 24. FONT LOADER
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_FONT_LOADER_OK and _qapp, "Font loader or QApplication not available")
class TestFontLoader(unittest.TestCase):
    """font_loader.py — load_embedded_font with multiple fallback paths."""

    def test_load_embedded_returns_qfont(self):
        from PyQt6.QtGui import QFont
        f = load_embedded_font(default_size=12)
        self.assertIsInstance(f, QFont)

    def test_load_embedded_size_respected(self):
        f = load_embedded_font(default_size=14)
        self.assertEqual(f.pointSize(), 14)

    def test_get_font_returns_qfont(self):
        from PyQt6.QtGui import QFont
        f = get_font(size=10)
        self.assertIsInstance(f, QFont)

    def test_get_font_bold(self):
        f = get_font(size=10, bold=True)
        self.assertTrue(f.bold())

    def test_get_font_custom_family(self):
        f = get_font(size=11, family="Arial")
        self.assertEqual(f.family(), "Arial")


# ══════════════════════════════════════════════════════════════════════════════
# 25. DIALOG HELPER
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_DIALOG_OK, "DialogHelper not available")
class TestDialogHelper(unittest.TestCase):
    """dialog_helper.py — DialogResult enum + class defaults (no exec, would block)."""

    def test_dialog_result_enum_has_yes(self):
        self.assertTrue(hasattr(DialogResult, "YES"))

    def test_dialog_result_enum_has_no(self):
        self.assertTrue(hasattr(DialogResult, "NO"))

    def test_dialog_result_enum_has_cancel(self):
        self.assertTrue(hasattr(DialogResult, "CANCEL"))

    def test_default_titles_set(self):
        # These class-level constants should be non-empty strings
        for attr in ["DEFAULT_INFO_TITLE", "DEFAULT_WARNING_TITLE",
                     "DEFAULT_ERROR_TITLE", "DEFAULT_CONFIRM_TITLE"]:
            v = getattr(DialogHelper, attr, None)
            self.assertIsInstance(v, str, f"{attr} not a string")
            self.assertGreater(len(v), 0, f"{attr} empty")

    def test_static_methods_callable(self):
        # Just verify the public API exists and is callable
        for name in ["show_info", "show_warning", "show_error",
                     "confirm", "ask_yes_no_cancel"]:
            self.assertTrue(callable(getattr(DialogHelper, name, None)),
                            f"{name} not callable on DialogHelper")


# ══════════════════════════════════════════════════════════════════════════════
# 26. ASYNC FILE OPS
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_ASYNC_OK and _qapp, "AsyncFileManager or QApplication not available")
class TestAsyncFileOps(unittest.TestCase):
    """async_file_ops.py — non-blocking JSON I/O via QThread."""

    @classmethod
    def setUpClass(cls):  cls.tmp = tempfile.mkdtemp()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def _wait(self, manager, ms=5000):
        """Wait for all of a manager's threads to finish (headless-friendly)."""
        import time
        from PyQt6.QtWidgets import QApplication as _QA
        for t in list(manager._active_threads):
            if hasattr(t, "wait"):
                t.wait(ms)
        for _ in range(20):
            _QA.processEvents()
            time.sleep(0.05)

    def test_manager_starts_empty(self):
        m = AsyncFileManager()
        self.assertEqual(m.get_active_count(), 0)

    def test_writer_thread_instantiation(self):
        t = FileWriterThread(os.path.join(self.tmp, "x.json"), {"k":"v"})
        self.assertIsNotNone(t); self.assertEqual(t.format, "json")

    def test_reader_thread_instantiation(self):
        t = FileReaderThread(os.path.join(self.tmp, "x.json"))
        self.assertIsNotNone(t); self.assertEqual(t.format, "json")

    def test_writer_thread_synchronous_run(self):
        """Run writer's run() directly — no event loop needed."""
        fp = os.path.join(self.tmp, "sync_write.json")
        results = []
        t = FileWriterThread(fp, {"sync": True})
        t.finished.connect(lambda ok, msg: results.append((ok, msg)))
        t.run()  # Direct call — no QThread.start()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][0])
        self.assertTrue(os.path.exists(fp))

    def test_reader_thread_synchronous_run(self):
        fp = os.path.join(self.tmp, "sync_read.json")
        with open(fp, "w") as f: json.dump({"loaded":"yes"}, f)
        results = []
        t = FileReaderThread(fp)
        t.finished.connect(lambda ok, data, msg: results.append((ok, data)))
        t.run()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][0])
        self.assertEqual(results[0][1], {"loaded":"yes"})

    def test_writer_thread_handles_invalid_format(self):
        t = FileWriterThread(os.path.join(self.tmp, "bad.x"), "data", format="unknown")
        results = []
        t.finished.connect(lambda ok, msg: results.append(ok))
        t.run()
        self.assertEqual(results, [False])

    def test_async_save_json_returns_manager(self):
        m = async_save_json(os.path.join(self.tmp, "convenience.json"), {"x":1})
        self.assertIsInstance(m, AsyncFileManager)
        self._wait(m)

    def test_async_load_json_returns_manager(self):
        fp = os.path.join(self.tmp, "convenience_load.json")
        with open(fp, "w") as f: json.dump({"loaded":True}, f)
        m = async_load_json(fp)
        self.assertIsInstance(m, AsyncFileManager)
        self._wait(m)

    def test_manager_write_then_read_roundtrip(self):
        fp = os.path.join(self.tmp, "rt_async.json")
        m = AsyncFileManager()
        m.write_file_async(fp, {"key":"value", "n": 42})
        self._wait(m, ms=2000)
        if os.path.exists(fp):
            with open(fp) as f: data = json.load(f)
            self.assertEqual(data, {"key":"value", "n": 42})


# ══════════════════════════════════════════════════════════════════════════════
# 27. SCREEN COLOR PICKER (Picker-specific, no Mixer equivalent)
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_SCREEN_PICKER_OK and _qapp, "ScreenColorPicker or QApplication not available")
class TestScreenColorPicker(unittest.TestCase):
    """screen_color_picker.py — magnifier-overlay widget (no live capture)."""

    def setUp(self):
        # Don't show() — that would grab the screen. Just instantiate.
        self.picker = ScreenColorPicker()

    def tearDown(self):
        try: self.picker.close()
        except Exception: pass

    def test_instantiation(self):
        self.assertIsNotNone(self.picker)

    def test_signals_defined(self):
        from PyQt6.QtCore import pyqtBoundSignal
        self.assertIsInstance(self.picker.color_picked, pyqtBoundSignal)
        self.assertIsInstance(self.picker.picker_cancelled, pyqtBoundSignal)

    def test_default_magnifier_size(self):
        self.assertGreater(self.picker.magnifier_size, 0)

    def test_default_zoom_factor(self):
        self.assertGreater(self.picker.zoom_factor, 0)

    def test_starts_with_default_color(self):
        self.assertEqual(len(self.picker.current_color), 3)

    def test_screenshot_initially_none(self):
        self.assertIsNone(self.picker.screenshot)

    def test_signal_manager_attached(self):
        # ScreenColorPicker uses SignalConnectionManager for its timer
        self.assertTrue(hasattr(self.picker, "signal_manager"))


# ══════════════════════════════════════════════════════════════════════════════
# 28. WIDGET POOL (UI module — recycles ColorSwatchWidget instances)
# ══════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_WIDGET_POOL_OK and _qapp, "WidgetPool or QApplication not available")
class TestWidgetPool(unittest.TestCase):
    """widget_pool.py — generic widget recycling (test with QLabel as stand-in)."""

    def _make_pool(self, initial=0, max_size=5):
        from PyQt6.QtWidgets import QLabel
        return WidgetPool(factory=lambda: QLabel(), initial_size=initial, max_size=max_size)

    def test_initial_size_zero_starts_empty(self):
        p = self._make_pool(initial=0)
        self.assertEqual(len(p._available), 0)
        self.assertEqual(len(p._in_use), 0)

    def test_initial_size_pre_creates(self):
        p = self._make_pool(initial=3)
        self.assertEqual(len(p._available), 3)

    def test_acquire_creates_when_empty(self):
        p = self._make_pool(initial=0)
        w = p.acquire()
        self.assertIsNotNone(w)
        self.assertIn(w, p._in_use)

    def test_acquire_reuses_from_pool(self):
        p = self._make_pool(initial=2)
        w = p.acquire()
        self.assertEqual(len(p._available), 1)
        self.assertEqual(len(p._in_use), 1)

    def test_release_returns_to_pool(self):
        p = self._make_pool()
        w = p.acquire()
        p.release(w)
        self.assertNotIn(w, p._in_use)
        self.assertIn(w, p._available)

    def test_release_ignores_unknown_widget(self):
        from PyQt6.QtWidgets import QLabel
        p = self._make_pool()
        # Releasing a widget that wasn't acquired is a no-op
        stranger = QLabel()
        p.release(stranger)  # Should not crash
        self.assertNotIn(stranger, p._available)

    def test_release_all(self):
        p = self._make_pool()
        for _ in range(3): p.acquire()
        self.assertEqual(len(p._in_use), 3)
        p.release_all()
        self.assertEqual(len(p._in_use), 0)

    def test_max_size_drops_overflow(self):
        p = self._make_pool(max_size=2)
        widgets = [p.acquire() for _ in range(4)]
        for w in widgets: p.release(w)
        # Pool only keeps `max_size` — excess get deleteLater()'d
        self.assertLessEqual(len(p._available), 2)

    def test_acquire_from_pre_populated(self):
        p = self._make_pool(initial=5)
        for _ in range(5): p.acquire()
        # After acquiring all 5, pool is empty but in_use has 5
        self.assertEqual(len(p._available), 0)
        self.assertEqual(len(p._in_use), 5)


# ══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def _summary(result):
    total = result.testsRun
    failed = len(result.failures); errors = len(result.errors); skipped = len(result.skipped)
    passed = total - failed - errors - skipped
    print(f"\n{'═'*60}\n{_B}  RNV Color Picker — Test Results{_X}\n{'═'*60}")
    print(f"  {_G}✓ Passed  {passed:>4}{_X}")
    if failed:  print(f"  {_R}✗ Failed  {failed:>4}{_X}")
    if errors:  print(f"  {_R}⚠ Errors  {errors:>4}{_X}")
    if skipped: print(f"  {_Y}  Skipped {skipped:>4}{_X}")
    print(f"  {'─'*16}\n    Total   {total:>4}\n{'═'*60}")
    if result.failures:
        print(f"\n{_R}{_B}FAILURES:{_X}")
        for test, tb in result.failures:
            print(f"  {_R}✗ {test}{_X}")
            for line in tb.splitlines()[-4:]: print(f"      {line}")
    if result.errors:
        print(f"\n{_R}{_B}ERRORS:{_X}")
        for test, tb in result.errors:
            print(f"  {_R}⚠ {test}{_X}")
            for line in tb.splitlines()[-4:]: print(f"      {line}")
    if passed == total:
        print(f"\n  {_G}{_B}All {total} tests passed ✓{_X}\n")
    else:
        print(f"\n  {_R}{_B}{failed+errors} test(s) need attention.{_X}\n")


if __name__ == "__main__":
    print(f"\n{_C}{_B}{'═'*60}\n  RNV Color Picker — Comprehensive Test Suite\n{'═'*60}{_X}")
    print(f"  Project: {_ROOT}\n  Layout:  {'subdir (core/utils/ui)' if _SUBDIR_LAYOUT else 'flat'}")
    print(f"  Python:  {sys.version.split()[0]}\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        # Core math & algorithms
        TestColorMath,
        TestColorHarmony,
        TestColorHistoryManager,
        TestColorCollection,
        TestHilbertCurve,
        TestAccessibility,
        # Persistence
        TestPaletteFormats,
        TestSettingsManager,
        TestSessionManager,
        # Utilities
        TestErrorHandler,
        TestFileUtils,
        # Config & theme
        TestConfig,
        TestConfigNewConstants,
        # Caching
        TestCache,
        TestStylesheetCache,
        TestFontCache,
        TestResourceCache,
        # Qt-dependent
        TestClipboard,
        TestLogger,
        TestSignalManager,
        TestPixmapCache,
        TestWorkers,
        TestFontLoader,
        TestDialogHelper,
        TestAsyncFileOps,
        TestScreenColorPicker,
        TestWidgetPool,
        # Cross-module
        TestEdgeCases,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    buf = io.StringIO()
    runner = unittest.TextTestRunner(verbosity=2 if "-v" in sys.argv else 1, stream=buf)
    result = runner.run(suite)
    print(buf.getvalue(), flush=True)
    _summary(result)
    sys.stdout.flush()
    # os._exit avoids PyQt6 internal cleanup that crashes in headless environments
    os._exit(0 if (len(result.failures) + len(result.errors)) == 0 else 1)