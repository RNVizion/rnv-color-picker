"""every colour named, and every name used: the picker's unread palette keys and constants go

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (a692bb6).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-10-04, items 6 to 9 of decisions-pending-2026-09-29.md:

  "As long as a color exist in the app it should be named and used no
   hardcoded or pointless literals should exist, only literals with a
   purpose, like data or comparison are allowed. Colors are name for swap
   ability and alignment."

USED. Seventeen palette keys no mode read go from the dark and light
palettes (image inherits them): accent_pressed, bg_secondary, border_accent,
dialog_border, error, info, list_alt_bg, list_grid, list_header_bg,
output_text_color, panel_bg, success, text_accent_secondary, text_secondary,
tooltip_bg, tooltip_text, warning. Image mode's scroll_area_bg override goes:
in image mode the scroll area is transparent and both of its sheets read the
key only in their other branch. Six constants nothing in the application
read go: BRAND_DARK_GOLD_RGB, STATUS_ACTIVE_COLOR, STATUS_WARNING,
APP_SURFACE_LIGHT_2, GREY_EE, GREY_DD. So do the NOT CONSUMED notes and
tests/test_unconsumed_keys.py, and one name __all__ listed and the module
never defined.

NAMED. The selection box's "yellow", written twice, is SELECTION_BOX_COLOR.
The cache's black and white are made from TRUE_BLACK and WHITE. The exported
palette sheet's paper and ink, written as integer tuples in two files, are
the export's own two names; the ink on a swatch comes from contrast_ink_rgb().
An entry with no rgb was read as [0, 0, 0] in four places, beside the hex
that already had its name: it is MISSING_RGB_PLACEHOLDER, made from that hex.

PROVEN BEFORE BUILDING. No line of the application looks up any of the
seventeen keys, on any receiver. Every palette read in this application has
a constant key the colour chart's resolver follows; none is computed. And
171 captures of every window, tab and combo in every mode, with 1,653
stylesheet and palette entries, are the same with the round as without.

The tests that named what went are changed with it. Where a test measured
text against panel_bg, a key nothing painted, it now measures against
dialog_bg, the key that paints that ground, at the same value.
"""
from __future__ import annotations

import argparse
import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = 'rnv-color-picker'
SENTINEL = 'RNV-NAMED-AND-USED'
SENTINEL_FILE = 'utils/config.py'
GUARD = 'tests/test_named_and_used.py'
GUARD_FILES = ['tests/test_named_and_used.py', 'tests/test_status_family.py', 'tests/test_app_mirror.py', 'tests/test_brand_contrast.py', 'tests/test_derived_values.py', 'tests/test_ladder_and_plate.py', 'tests/test_light_wiring.py', 'tests/test_gold_as_text.py']
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_named_and_used.py', 'tests/test_status_family.py', 'tests/test_app_mirror.py', 'tests/test_brand_contrast.py', 'tests/test_derived_values.py', 'tests/test_ladder_and_plate.py', 'tests/test_light_wiring.py', 'tests/test_gold_as_text.py']
DESCRIPTION = "every colour named, and every name used: the picker's unread palette keys and constants go"

SUITES = [
    ("CI step 1: unittest -v test_rnv_color_picker",
     [sys.executable, "-m", "coverage", "run", "--data-file=.coverage.unittest",
      "--source=core,utils,ui", "--branch", "-m", "unittest", "-v",
      "test_rnv_color_picker"]),
    ("CI step 2: pytest tests/ --timeout=60",
     [sys.executable, "-m", "pytest", "tests/", "-v", "--timeout=60",
      "--timeout-method=thread", "--cov=core", "--cov=ui", "--cov=utils",
      "--cov-branch", "--cov-report=term"]),
]

#: The environment the workflow sets for every step. verify() calls
#: post_write() before the guards and the suites, and they inherit os.environ.
CI_ENV = {"PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1",
          "QT_QPA_PLATFORM": "offscreen", "COVERAGE_FILE": ".coverage.pytest"}


def post_write() -> None:
    """CI's environment. PYTHONPATH is the checkout, as the workflow's
    `PYTHONPATH: ${{ github.workspace }}`."""
    os.environ.update(CI_ENV)
    here = str(Path.cwd())
    existing = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = here + (os.pathsep + existing if existing else "")
    print("CI environment: " + ", ".join(f"{k}={v}" for k, v in CI_ENV.items())
          + f", PYTHONPATH={here}")

#: The workflows SUITES was written from, by content hash.
CI_MIRRORS = {'.github/workflows/tests.yml': '8d472651b899dcf403c7e77919fdfb90f1a31e06d663973f54e6b903c853fbba'}

SHADOWS = {"config.py", "conftest.py", "cache.py", "image_viewer.py", "workers.py", "accessibility.py", "color_history.py", "settings_panel.py", "test_rnv_color_picker.py"}

LEFT_ALONE = ['BRAND_GOLD_PRESSED, BRAND_DARK_GOLD_PRESSED and IMAGE_BUTTON_FRAME_BG: read only by two cached stylesheet functions nothing in the application calls. They go only if those functions go, which is a ruling of its own.', "image mode's image_viewer_bg and scroll_area_bg as KEYS: they come through the splat with dark's values, unread and unwritten.", "image mode's status_error_text, restated at dark's value: image mode reads it.", 'SVG_EXPORT_STROKE and MISSING_HEX_PLACEHOLDER: data, written into files and used as a stand-in, not painted.', "clear: 'transparent', alpha 0 and Qt's transparent are how a widget is told to paint nothing, and are left as written.", "the starting colours the guard's DATA table lists: where the screen picker and a swatch start, and what a failed conversion falls back to.", 'the preference default_slot_color: its stored default is listed as data. Nothing reads the preference, which is a ruling of its own.']


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('utils/config.py',
             'BRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)\n"""Derived. A hardcoded tuple is invisible to every hex-based search, so\nit survives sweeps that catch every other reference to the colour."""\n\nBRAND_DARK_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_DARK_GOLD)\n"""Derived, same reason. This one held (177, 145, 69) -- the retired gold,\nin the one form no sweep would have found."""\n',
             'BRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)\n"""Derived. A hardcoded tuple is invisible to every hex-based search, so\nit survives sweeps that catch every other reference to the colour.\n\nRNV-NAMED-AND-USED (2026-10-04): its dark-gold twin went. Nothing in the\napplication read it; a name is kept for what uses it."""\n')
    tree.sub('utils/config.py',
             'APP_SURFACE_LIGHT_2: Final[str] = "#fbfbfb"\n"""engine/brand.py APP["surface-light-2"]. One rung above the panel ground.\n\nRNV-LIGHT-WIRING (2026-09-06): new to this application. It arrives\nbecause two strays collapse onto it -- #f8f8f8 and #fafafa, which sat\n0.60 and 0.20 CIEDE2000 from this rung and on no ladder at all. Same\nruling as #252525 onto the card: a value a fraction of a step from a\nregistered one is that one, misspelled."""\n\n',
             '')
    tree.sub('utils/config.py',
             'GREY_EE: Final[str] = "#eeeeee"\n"""grey(14) on the ramp, #eeeeee. Static surfaces that share a hex with\nAPP_HOVER_LIGHT without being a hover: a list header, a scroll ground.\nSame split rnv-text-transformer ruled for its diff headers."""\n\nGREY_DD: Final[str] = "#dddddd"\n"""grey(13) on the ramp, #dddddd. Edges and grid lines that share a hex\nwith APP_TEXT without being text. The register\'s APP["text"] is ink;\na gridline is not, and moving the ink should not move the grid."""\n',
             '# RNV-NAMED-AND-USED (2026-10-04): two more ramp steps stood here, #eeeeee\n# and #dddddd, each feeding one light list key that nothing read. They went\n# with the keys.\n')
    tree.sub('utils/config.py',
             '    "APP_SURFACE_LIGHT_3": "register",\n    "APP_SURFACE_LIGHT_2": "register",\n    "APP_PRESSED_LIGHT": "register",\n    "GREY_E0": "app-ramp",\n    "GREY_EE": "app-ramp",\n    "GREY_DD": "app-ramp",\n',
             '    "APP_SURFACE_LIGHT_3": "register",\n    "APP_PRESSED_LIGHT": "register",\n    "GREY_E0": "app-ramp",\n')
    tree.sub('utils/config.py',
             'WAS #28a745, written out four times in this file with no constant between the\nvalue and its uses -- twice in the palettes, once as STATUS_SUCCESS_BG and\nonce as STATUS_ACTIVE_COLOR. Named here so it has one home."""\n\nSTATUS_WARNING: Final[str] = "#a2703c"\n"""Registered. WAS #ffc107, retired on arithmetic rather than taste: it read\n1.63 on #ffffff and 1.49 on #f5f5f5, so it could not legally carry a boundary\non a light ground at all.\n\nIt reads as gold-adjacent because it half IS one -- the register derives it\n50% toward BRAND_DARK_GOLD in OKLab, landing 9.1 CIEDE2000 away, which clears\nthe register\'s own 8.40 "clearly different" threshold by 0.7."""\n\nSTATUS_SUCCESS_TEXT: Final[str] = "#ad85a3"\n"""Registered. Success TEXT on a dark panel: 5.52 on #1a1a1a, 4.55 on #2a2a2a.\n\nHere for STATUS_ACTIVE_COLOR below, which is painted with `color:` and cannot\ntake the fill. The register ruled on 2026-09-04 that an active label aliases\nsuccess-text rather than success, after finding the same alias in\nrnv-icon-builder about to fail on adoption day."""\n',
             'WAS #28a745, written out four times in this file with no constant between the\nvalue and its uses -- twice in the palettes, once as STATUS_SUCCESS_BG and\nonce as an alias for an active label. Named here so it has one home.\n\nRNV-NAMED-AND-USED (2026-10-04): the palettes\' `success` key and that alias\nwent, read by nothing. STATUS_SUCCESS_BG is what paints this."""\n\n# RNV-NAMED-AND-USED (2026-10-04): the register\'s warning FILL, #a2703c, is\n# not carried here. This application draws no warning fill: the name fed only\n# the palettes\' `warning` key, which nothing read. The warning TEXT pair\n# below is what the rating scale paints.\n\nSTATUS_SUCCESS_TEXT: Final[str] = "#ad85a3"\n"""Registered. Success TEXT on a dark panel: 5.52 on #1a1a1a, 4.55 on #2a2a2a.\n\nThe rating scale\'s `excellent` tier in the dark palette. The register ruled\non 2026-09-04 that an active label aliases success-text rather than success,\nafter finding the same alias in rnv-icon-builder about to fail on adoption\nday."""\n')
    tree.sub('utils/config.py',
             'STATUS_WARNING is a FILL and cannot do this job: it reads 4.07 on #1a1a1a,\n',
             "The register's warning FILL, #a2703c, cannot do this job: it reads 4.07 on #1a1a1a,\n")
    tree.sub('utils/config.py',
             'STATUS_ERROR_FG:   Final[str] = "#000000"\n# Unreferenced outside this file. Kept as an alias rather than\n# deleted -- rnv-icon-builder holds the same name for the folder\n# watcher, and the register still has no name for `running` as\n# distinct from `succeeded`; it recorded on 2026-09-04 that the\n# trigger for registering one is a SECOND consumer, not a date.\n#\n# IT ALIASES success-text, NOT success. Ruled by the register the\n# same day, after the identically-named constant in icon-builder --\n# which IS painted, with `color:` -- turned out to be about to fail\n# the 4.5 text floor on adoption day. Bootstrap\'s green read 5.55 on\n# BRAND_BLACK and doubled as text by accident; the RNV fills are\n# mid-tones by design and #926c89 reads 3.91 there. Nothing paints\n# this one today, and that is the reason to get it right now rather\n# than the reason not to: it is what the next reader will copy.\nSTATUS_ACTIVE_COLOR: Final[str] = STATUS_SUCCESS_TEXT\n',
             'STATUS_ERROR_FG:   Final[str] = "#000000"\n# RNV-NAMED-AND-USED (2026-10-04): an alias for an active label stood\n# here, on success-text, unreferenced outside this file. It went: a name\n# is kept for what uses it. If this application ever paints a running\n# state as TEXT, it takes STATUS_SUCCESS_TEXT -- the register\'s ruling\n# of 2026-09-04 -- and never the fill, which reads 3.91 on BRAND_BLACK.\n')
    tree.sub('utils/config.py',
             "    'window_bg':          TRUE_BLACK,\n    'panel_bg':           BRAND_BLACK,\n    'card_bg':            APP_CARD,\n    'bg_secondary':       APP_CARD,   # alias for card_bg\n    'input_bg':           BRAND_BLACK,\n",
             "    'window_bg':          TRUE_BLACK,\n    'card_bg':            APP_CARD,\n    'input_bg':           BRAND_BLACK,\n")
    tree.sub('utils/config.py',
             "    'text_primary':       APP_TEXT,\n    # NOT CONSUMED. Nothing reads this key -- 'text_muted' below carries the\n    # same value and does the job in six places. Kept, and kept correct, so\n    # wiring it up is a one-line change rather than a colour decision.\n    'text_secondary':     GREY_88,\n    'text_muted':         GREY_88,\n",
             "    'text_primary':       APP_TEXT,\n    'text_muted':         GREY_88,\n")
    tree.sub('utils/config.py',
             "    'border_hover':       GREY_44,\n    'border_accent':      BRAND_GOLD,\n    'input_border':       APP_BORDER,\n",
             "    'border_hover':       GREY_44,\n    'input_border':       APP_BORDER,\n")
    tree.sub('utils/config.py',
             "    'list_bg':            APP_CARD,   # was #252525, see scrollbar_bg\n    'list_alt_bg':        BRAND_BLACK,\n    'list_selected_bg':   BRAND_GOLD,\n    'list_selected_text': TRUE_BLACK,\n    'list_hover_bg':      APP_PANEL_HOVER,\n    'list_hover_text':    BRAND_GOLD,\n    'list_header_bg':     APP_CARD,\n    'list_grid':          APP_BORDER,\n    \n    # ── Dialog / status ──\n    'dialog_bg':          BRAND_BLACK,\n    'dialog_border':      APP_BORDER,\n    \n    # ── Tooltip ──\n    'tooltip_bg':         APP_CARD,\n    'tooltip_border':     BRAND_GOLD,\n    'tooltip_text':       APP_TEXT,\n    \n",
             "    'list_bg':            APP_CARD,   # was #252525, see scrollbar_bg\n    'list_selected_bg':   BRAND_GOLD,\n    'list_selected_text': TRUE_BLACK,\n    'list_hover_bg':      APP_PANEL_HOVER,\n    'list_hover_text':    BRAND_GOLD,\n    \n    # ── Dialog ──\n    'dialog_bg':          BRAND_BLACK,\n    \n    # ── Tooltip ──\n    'tooltip_border':     BRAND_GOLD,\n    \n")
    tree.sub('utils/config.py',
             "    # ── Semantic status ──\n    # RNV-STATUS-FAMILY: the fills, now named. All three were\n    # bare literals; every hex a palette carries needs a\n    # constant, or nothing can move it. These three keys are\n    # looked up nowhere in this application and are not wired\n    # up by this pass -- if any is ever painted as TEXT it\n    # must take a _TEXT value instead, because a fill sits at\n    # L* 48-59 and cannot reach 4.5:1 on either ground.\n    'success':            STATUS_SUCCESS,\n    'warning':            STATUS_WARNING,\n    'error':              STATUS_ERROR,\n    'info':               BRAND_GOLD,\n    \n    # ── Picker-specific (unique to this app) ──\n",
             '    # ── Picker-specific (unique to this app) ──\n')
    tree.sub('utils/config.py',
             "    'swatch_border_color':   APP_TEXT,\n    'output_text_color':     BRAND_GOLD,\n    'text_accent_secondary': BRAND_GOLD,\n    \n    # ── Gold accent hover/pressed tints (no better semantic name exists) ──\n    'accent_hover':       BRAND_GOLD_HOVER,\n    'accent_pressed':     BRAND_GOLD_PRESSED,\n}\n",
             "    'swatch_border_color':   APP_TEXT,\n    \n    # ── Gold accent hover tint (no better semantic name exists) ──\n    'accent_hover':       BRAND_GOLD_HOVER,\n}\n")
    tree.sub('utils/config.py',
             "    'window_bg':          APP_SURFACE_LIGHT_3,\n    'panel_bg':           APP_SURFACE_LIGHT_3,\n    'card_bg':            WHITE,\n    'bg_secondary':       WHITE,\n    'input_bg':           WHITE,\n",
             "    'window_bg':          APP_SURFACE_LIGHT_3,\n    'card_bg':            WHITE,\n    'input_bg':           WHITE,\n")
    tree.sub('utils/config.py',
             "    'text_primary':       TRUE_BLACK,\n    # NOT CONSUMED -- see the note in the dark palette.\n    'text_secondary':     GREY_66,\n    'text_muted':         GREY_66,\n",
             "    'text_primary':       TRUE_BLACK,\n    'text_muted':         GREY_66,\n")
    tree.sub('utils/config.py',
             "    'border_hover':       APP_TEXT_DIM,\n    'border_accent':      BRAND_DARK_GOLD,\n    'input_border':       GREY_CC,\n",
             "    'border_hover':       APP_TEXT_DIM,\n    'input_border':       GREY_CC,\n")
    tree.sub('utils/config.py',
             "    'list_bg':            WHITE,\n    'list_alt_bg':        APP_SURFACE_LIGHT_2,   # was #f8f8f8, collapsed onto #fbfbfb\n    'list_selected_bg':   BRAND_DARK_GOLD,\n    'list_selected_text': WHITE,\n    'list_hover_bg':      APP_HOVER_LIGHT,\n    'list_hover_text':    BRAND_DARK_GOLD_DEEP,\n    'list_header_bg':     GREY_EE,   # was #f0f0f0, collapsed onto #eeeeee\n    'list_grid':          GREY_DD,\n    \n    # ── Dialog / status ──\n    'dialog_bg':          APP_SURFACE_LIGHT_3,\n    'dialog_border':      GREY_CC,\n    \n    # ── Tooltip ──\n    'tooltip_bg':         WHITE,\n    'tooltip_border':     BRAND_DARK_GOLD,\n    'tooltip_text':       TRUE_BLACK,\n    \n",
             "    'list_bg':            WHITE,\n    'list_selected_bg':   BRAND_DARK_GOLD,\n    'list_selected_text': WHITE,\n    'list_hover_bg':      APP_HOVER_LIGHT,\n    'list_hover_text':    BRAND_DARK_GOLD_DEEP,\n    \n    # ── Dialog ──\n    'dialog_bg':          APP_SURFACE_LIGHT_3,\n    \n    # ── Tooltip ──\n    'tooltip_border':     BRAND_DARK_GOLD,\n    \n")
    tree.sub('utils/config.py',
             "    # ── Semantic status ──\n    # RNV-STATUS-FAMILY: the fills, now named. All three were\n    # bare literals; every hex a palette carries needs a\n    # constant, or nothing can move it. These three keys are\n    # looked up nowhere in this application and are not wired\n    # up by this pass -- if any is ever painted as TEXT it\n    # must take a _TEXT value instead, because a fill sits at\n    # L* 48-59 and cannot reach 4.5:1 on either ground.\n    'success':            STATUS_SUCCESS,\n    'warning':            STATUS_WARNING,\n    'error':              STATUS_ERROR,\n    'info':               BRAND_DARK_GOLD,\n    \n    # ── Picker-specific ──\n",
             '    # ── Picker-specific ──\n')
    tree.sub('utils/config.py',
             "    'swatch_border_color':   TRUE_BLACK,\n    'output_text_color':     BRAND_DARK_GOLD,\n    'text_accent_secondary': BRAND_DARK_GOLD,\n    \n    # ── Gold accent hover/pressed tints (no better semantic name exists) ──\n    'accent_hover':       BRAND_DARK_GOLD_HOVER,\n    'accent_pressed':     BRAND_DARK_GOLD_PRESSED,\n}\n",
             "    'swatch_border_color':   TRUE_BLACK,\n    \n    # ── Gold accent hover tint (no better semantic name exists) ──\n    'accent_hover':       BRAND_DARK_GOLD_HOVER,\n}\n")
    tree.sub('utils/config.py',
             "    # No image_viewer_bg here. In image mode the viewer paints\n    # OVERLAY_BLACK_MEDIUM and never reads the key, so its override,\n    # APP_CANVAS_OVERLAY, painted nothing and was removed -- proven by\n    # render first, RNV-CANVAS-OVERLAY-GONE, 2026-09-26. The key comes\n    # through the splat with dark's value, unread.\n    'scroll_area_bg':     APP_WINDOW_OVERLAY,\n    'zoom_label_bg':      APP_PANEL_OVERLAY,\n",
             "    # No image_viewer_bg here. In image mode the viewer paints\n    # OVERLAY_BLACK_MEDIUM and never reads the key, so its override,\n    # APP_CANVAS_OVERLAY, painted nothing and was removed -- proven by\n    # render first, RNV-CANVAS-OVERLAY-GONE, 2026-09-26. The key comes\n    # through the splat with dark's value, unread.\n    # No scroll_area_bg either, since RNV-NAMED-AND-USED (2026-10-04):\n    # in image mode the scroll area is transparent over the same\n    # OVERLAY_BLACK_MEDIUM, and both of its sheets read the key only in\n    # their other branch. Its override, APP_WINDOW_OVERLAY, went.\n    'zoom_label_bg':      APP_PANEL_OVERLAY,\n")
    tree.sub('utils/config.py',
             'BRAND_DARK_GOLD_PRESSED: Final[str] = BRAND_DARK_GOLD\n"""Light-mode pressed. It IS the accent.\n',
             'BRAND_DARK_GOLD_PRESSED: Final[str] = BRAND_DARK_GOLD\n"""Light-mode pressed. It IS the accent. Read by the cached close-button\nsheet alone since the palettes\' `accent_pressed` went (2026-10-04).\n')
    tree.sub('utils/config.py',
             '# ── SVG palette export (printable artifact) ──\n# Fixed paper-white background and ink-black stroke for the SVG export\n# format. Theme-independent because exported SVGs need to look the same\n# regardless of which theme was active at export time.\nSVG_EXPORT_BG:     Final[str] = "#ffffff"\n"""Background fill for SVG palette export (paper white)."""\n\nSVG_EXPORT_STROKE: Final[str] = "#000000"\n"""Stroke color for SVG palette export swatch borders (ink black)."""\n',
             '# ── The selection box (fixed, like the overlays above) ──\n# RNV-NAMED-AND-USED (2026-10-04): the dotted box dragged over an image.\n# It was written "yellow" twice in ui/image_viewer.py, once for the cache\n# and once for the road without it. CSS yellow is this value; the same\n# pixels. No register value holds it, so the name is the application\'s.\nSELECTION_BOX_COLOR: Final[str] = "#ffff00"\n"""The image viewer\'s selection rectangle (CSS yellow)."""\n\n# ── Palette export (printable artifact) ──\n# Fixed paper-white background and ink-black stroke for the exported\n# palette: the SVG file and, since RNV-NAMED-AND-USED (2026-10-04), the\n# image sheet, which wrote the same two as integer tuples. Theme-\n# independent because an export needs to look the same regardless of\n# which theme was active at export time.\nSVG_EXPORT_BG:     Final[str] = "#ffffff"\n"""Background fill for palette export (paper white)."""\n\nSVG_EXPORT_STROKE: Final[str] = "#000000"\n"""Stroke color for palette export swatch borders (ink black)."""\n')
    tree.sub('utils/config.py',
             '    """The same answer as an RGB triple, for the QColor and Pillow callers."""\n    return (0, 0, 0) if prefers_dark_ink(background) else (255, 255, 255)\n',
             '    """The same answer as an RGB triple, for the QColor and Pillow callers."""\n    return _to_rgb(contrast_ink(background))\n')
    tree.sub('utils/config.py',
             "    'BRAND_GOLD_RGB',\n    'BRAND_DARK_GOLD_RGB',\n",
             "    'BRAND_GOLD_RGB',\n")
    tree.sub('utils/config.py',
             "    'STATUS_ERROR',\n    'STATUS_ERROR_LIGHT',\n    'STATUS_ERROR_BG',\n    'STATUS_ERROR_FG',\n    'STATUS_ACTIVE_COLOR',\n",
             "    'STATUS_ERROR',\n    'STATUS_ERROR_BG',\n    'STATUS_ERROR_FG',\n")
    tree.sub('utils/config.py',
             "    'SVG_EXPORT_BG',\n",
             "    'SELECTION_BOX_COLOR',\n    'SVG_EXPORT_BG',\n")
    tree.sub('utils/config.py',
             'MISSING_HEX_PLACEHOLDER: Final[str] = "#000000"\n"""Placeholder hex when a color entry dict lacks its \'hex\' key."""\n',
             'MISSING_HEX_PLACEHOLDER: Final[str] = "#000000"\n"""Placeholder hex when a color entry dict lacks its \'hex\' key."""\n\nMISSING_RGB_PLACEHOLDER: Final[tuple[int, int, int]] = _to_rgb(MISSING_HEX_PLACEHOLDER)\n"""The same sentinel as channels, when an entry lacks its \'rgb\' key.\nRNV-NAMED-AND-USED (2026-10-04): this was [0, 0, 0], written out in the four\nplaces that read an entry, beside the hex that already had its name. Made\nfrom that hex, so the two cannot part."""\n')
    tree.sub('utils/config.py',
             "    'MISSING_HEX_PLACEHOLDER',\n",
             "    'MISSING_HEX_PLACEHOLDER',\n    'MISSING_RGB_PLACEHOLDER',\n")
    tree.sub('utils/cache.py',
             '            cls.BLACK = QColor(0, 0, 0)\n            cls.WHITE = QColor(255, 255, 255)\n',
             '            # RNV-NAMED-AND-USED (2026-10-04): were QColor(0, 0, 0) and\n            # QColor(255, 255, 255). The same two colours, by name.\n            cls.BLACK = QColor(TRUE_BLACK)\n            cls.WHITE = QColor(WHITE)\n')
    tree.sub('ui/image_viewer.py',
             'from utils.config import BRAND_GOLD, IMAGE_MENU_BG\n',
             'from utils.config import BRAND_GOLD, IMAGE_MENU_BG, SELECTION_BOX_COLOR\n')
    tree.sub('ui/image_viewer.py',
             '                # Use cached yellow color for selection\n                if CACHE_AVAILABLE and QColorCache:\n                    yellow = QColorCache.get("yellow")\n                else:\n                    yellow = QColor("yellow")\n',
             '                # Use cached yellow color for selection\n                # RNV-NAMED-AND-USED (2026-10-04): was "yellow", twice.\n                if CACHE_AVAILABLE and QColorCache:\n                    yellow = QColorCache.get(SELECTION_BOX_COLOR)\n                else:\n                    yellow = QColor(SELECTION_BOX_COLOR)\n')
    tree.sub('RNV_Color_Picker.py',
             'from utils.config import (\n    prefers_dark_ink,\n    ThemeManager, MAX_COLORS, APP_VERSION,\n',
             'from utils.config import (\n    contrast_ink_rgb, SVG_EXPORT_BG, SVG_EXPORT_STROKE,\n    ThemeManager, MAX_COLORS, APP_VERSION,\n')
    tree.sub('RNV_Color_Picker.py',
             '        if is_png:\n            palette_img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))\n        else:\n            palette_img = Image.new("RGB", (page_width, page_height), (255, 255, 255))\n',
             '        # RNV-NAMED-AND-USED (2026-10-04): the sheet\'s paper and ink, by\n        # name. They were (255, 255, 255) and (0, 0, 0); the same pixels.\n        if is_png:\n            palette_img = Image.new("RGBA", (page_width, page_height), SVG_EXPORT_BG)\n        else:\n            palette_img = Image.new("RGB", (page_width, page_height), SVG_EXPORT_BG)\n')
    tree.sub('RNV_Color_Picker.py',
             '                fill=rgb, outline=(0, 0, 0), width=2\n            )\n',
             '                fill=rgb, outline=SVG_EXPORT_STROKE, width=2\n            )\n')
    tree.sub('RNV_Color_Picker.py',
             '                    text_color = (0, 0, 0) if prefers_dark_ink((r, g, b)) else (255, 255, 255)\n',
             '                    text_color = contrast_ink_rgb((r, g, b))\n')
    tree.sub('core/workers.py',
             'from utils.config import prefers_dark_ink\n',
             'from utils.config import contrast_ink_rgb, SVG_EXPORT_BG, SVG_EXPORT_STROKE\n')
    tree.sub('core/workers.py',
             '            if is_png:\n                palette_img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))\n            else:\n                palette_img = Image.new("RGB", (page_width, page_height), (255, 255, 255))\n',
             '            # RNV-NAMED-AND-USED (2026-10-04): the sheet\'s paper and ink,\n            # by name. They were (255, 255, 255) and (0, 0, 0).\n            if is_png:\n                palette_img = Image.new("RGBA", (page_width, page_height), SVG_EXPORT_BG)\n            else:\n                palette_img = Image.new("RGB", (page_width, page_height), SVG_EXPORT_BG)\n')
    tree.sub('core/workers.py',
             '                    fill=rgb, outline=(0, 0, 0), width=2\n                )\n',
             '                    fill=rgb, outline=SVG_EXPORT_STROKE, width=2\n                )\n')
    tree.sub('core/workers.py',
             '                    text_color = (0, 0, 0) if prefers_dark_ink((r, g, b)) else (255, 255, 255)\n',
             '                    text_color = contrast_ink_rgb((r, g, b))\n')
    tree.sub('core/color_history.py',
             'from utils.cache import ColorCache\n',
             'from utils.cache import ColorCache\nfrom utils.config import MISSING_RGB_PLACEHOLDER\n')
    tree.sub('core/color_history.py',
             '            rgb = entry.get("rgb", [0, 0, 0])\n            colors.append(tuple(rgb))\n',
             '            rgb = entry.get("rgb", MISSING_RGB_PLACEHOLDER)\n            colors.append(tuple(rgb))\n')
    tree.sub('ui/settings_panel.py',
             '    MISSING_HEX_PLACEHOLDER,\n)\n',
             '    MISSING_HEX_PLACEHOLDER, MISSING_RGB_PLACEHOLDER,\n)\n')
    tree.sub('ui/settings_panel.py',
             '            rgb = color_data.get("rgb", [0, 0, 0])\n',
             '            rgb = color_data.get("rgb", MISSING_RGB_PLACEHOLDER)\n')
    tree.sub('ui/settings_panel.py',
             '            rgb = tuple(item.color_data.get("rgb", [0, 0, 0]))\n',
             '            rgb = tuple(item.color_data.get("rgb", MISSING_RGB_PLACEHOLDER))\n')
    tree.sub('ui/settings_panel.py',
             '                            rgb = entry.get("rgb", [0, 0, 0])\n',
             '                            rgb = entry.get("rgb", MISSING_RGB_PLACEHOLDER)\n')
    tree.sub('core/accessibility.py',
             '        ink = config.contrast_ink(background)\n        return (255, 255, 255) if ink == config.WHITE else (0, 0, 0)\n',
             '        # RNV-NAMED-AND-USED (2026-10-04): the triple comes from the same\n        # place; it was written out here as (255, 255, 255) and (0, 0, 0).\n        return config.contrast_ink_rgb(background)\n')
    tree.sub('test_rnv_color_picker.py',
             '    def test_brand_gold_dark_rgb(self): self.assertEqual(config.BRAND_DARK_GOLD_RGB, (140,115,55))\n',
             '    def test_brand_gold_dark_rgb(self): self.assertEqual(ColorMath.hex_to_rgb(config.BRAND_DARK_GOLD), (140,115,55))\n')
    tree.sub('test_rnv_color_picker.py',
             '        required = ["window_bg","panel_bg","card_bg","text_primary","text_secondary",\n',
             '        required = ["window_bg","card_bg","text_primary",\n')
    tree.sub('test_rnv_color_picker.py',
             '        ratio = ColorAccessibility.calculate_contrast_ratio(\n            config.BRAND_DARK_GOLD_RGB, (255,255,255))\n',
             '        ratio = ColorAccessibility.calculate_contrast_ratio(\n            ColorMath.hex_to_rgb(config.BRAND_DARK_GOLD), (255,255,255))\n')
    tree.sub('tests/test_app_mirror.py',
             "    'APP_SURFACE_LIGHT_3': '#f5f5f5',\n    'APP_SURFACE_LIGHT_2': '#fbfbfb',\n",
             "    'APP_SURFACE_LIGHT_3': '#f5f5f5',\n")
    tree.sub('tests/test_app_mirror.py',
             "INK_KEYS = ('text_primary', 'dialog_btn_text', 'main_btn_text',\n            'main_btn_hover_text', 'tooltip_text', 'swatch_border_color')\n",
             "INK_KEYS = ('text_primary', 'dialog_btn_text', 'main_btn_text',\n            'main_btn_hover_text', 'swatch_border_color')\n")
    tree.sub('tests/test_brand_contrast.py',
             '    "BRAND_GOLD_RGB",\n    "BRAND_DARK_GOLD_RGB",\n}\n',
             '    "BRAND_GOLD_RGB",\n}\n')
    tree.sub('tests/test_brand_contrast.py',
             '@pytest.mark.parametrize("const,rgb", [\n    ("BRAND_GOLD", "BRAND_GOLD_RGB"),\n    ("BRAND_DARK_GOLD", "BRAND_DARK_GOLD_RGB"),\n])\n',
             '@pytest.mark.parametrize("const,rgb", [\n    ("BRAND_GOLD", "BRAND_GOLD_RGB"),\n])\n')
    tree.sub('tests/test_brand_contrast.py',
             '    for name, palette in PALETTES.items():\n        ground = palette.get("panel_bg") or palette["window_bg"]\n',
             '    # RNV-NAMED-AND-USED (2026-10-04): the settings panel paints dialog_bg.\n    # This read panel_bg, a key nothing painted, which held the same value.\n    for name, palette in PALETTES.items():\n        ground = palette["dialog_bg"]\n')
    tree.sub('tests/test_brand_contrast.py',
             '    assert contrast_ratio(dark["status_error_text"],\n                          dark["panel_bg"]) >= TEXT_FLOOR\n',
             '    assert contrast_ratio(dark["status_error_text"],\n                          dark["dialog_bg"]) >= TEXT_FLOOR\n')
    tree.sub('tests/test_brand_contrast.py',
             '    assert contrast_ratio(d["status_error_text"], d["panel_bg"]) >= TEXT_FLOOR\n',
             '    assert contrast_ratio(d["status_error_text"], d["dialog_bg"]) >= TEXT_FLOOR\n')
    tree.sub('tests/test_brand_contrast.py',
             '    ratio = contrast_ratio(light["status_error_text"], light["panel_bg"])\n',
             '    ratio = contrast_ratio(light["status_error_text"], light["dialog_bg"])\n')
    tree.sub('tests/test_brand_contrast.py',
             "    # RNV-STATUS-FAMILY (2026-09-03): the semantic warning is not a\n    # gold, but it reads as one to the shape test below because it\n    # half IS one -- the register derives it 50% toward\n    # BRAND_DARK_GOLD in OKLab. CIEDE2000 9.1 from that gold, which\n    # clears the register's own 8.40 threshold. Named rather than\n    # written as a hex so it moves with the constant.\n    allowed.add(C.STATUS_WARNING.lower())\n    # RNV-RATING-SCALE (2026-09-12): the warning TEXT pair reads as gold for\n    # exactly the same reason and by the same construction -- they are the\n    # text siblings of the fill above and hold its hue, so the shape test\n    # below cannot tell them from a hand-written gold. Registered values, and\n    # named rather than written as hexes so they move with the constants.\n",
             '    # RNV-RATING-SCALE (2026-09-12): the warning TEXT pair reads as gold to\n    # the shape test below because it half IS one -- the register derives\n    # the warning 50% toward BRAND_DARK_GOLD in OKLab -- so the test cannot\n    # tell them from a hand-written gold. Registered values, and named\n    # rather than written as hexes so they move with the constants. The\n    # warning FILL was allowed here too until RNV-NAMED-AND-USED\n    # (2026-10-04): no palette holds it now.\n')
    tree.sub('tests/test_derived_values.py',
             '    assert IMAGE["window_bg"] == IMAGE["scroll_area_bg"] == colors.APP_WINDOW_OVERLAY\n',
             '    # RNV-NAMED-AND-USED (2026-10-04): scroll_area_bg held it too, and image\n    # mode never read that key; it comes through the splat now, unread.\n    assert IMAGE["window_bg"] == colors.APP_WINDOW_OVERLAY\n    assert IMAGE["scroll_area_bg"] == DARK["scroll_area_bg"]\n')
    tree.sub('tests/test_derived_values.py',
             '#: Found when this was written; below the floor, the sweep has gone blind.\nLOWER8_FLOOR = 10\n',
             "#: Found when this was written; below the floor, the sweep has gone blind.\n#: 10 until RNV-NAMED-AND-USED (2026-10-04), when image mode's unread\n#: scroll_area_bg override went.\nLOWER8_FLOOR = 9\n")
    tree.sub('tests/test_ladder_and_plate.py',
             "    'IMAGE_MODE_COLORS': ('window_bg', 'scroll_area_bg', 'zoom_label_bg'),\n",
             "    'IMAGE_MODE_COLORS': ('window_bg', 'zoom_label_bg'),\n")
    tree.sub('tests/test_ladder_and_plate.py',
             "    # 13 until 2026-09-26, when image mode's image_viewer_bg override went:\n    # nothing read it (RNV-CANVAS-OVERLAY-GONE, tests/test_derived_values.py).\n    assert sum(len(v) for v in WIRED.values()) >= 12\n",
             "    # 13 until 2026-09-26, when image mode's image_viewer_bg override went:\n    # nothing read it (RNV-CANVAS-OVERLAY-GONE, tests/test_derived_values.py).\n    # 12 until 2026-10-04, when its scroll_area_bg override went the same\n    # way (RNV-NAMED-AND-USED).\n    assert sum(len(v) for v in WIRED.values()) >= 11\n")
    tree.sub('tests/test_status_family.py',
             '    "STATUS_SUCCESS": "#926c89",\n    "STATUS_WARNING": "#a2703c",\n    "STATUS_ERROR": "#c75b64",\n',
             '    "STATUS_SUCCESS": "#926c89",\n    "STATUS_ERROR": "#c75b64",\n')
    tree.sub('tests/test_status_family.py',
             'FILLS = ("STATUS_SUCCESS", "STATUS_WARNING", "STATUS_ERROR")\n',
             '#: The fills this application draws. The register holds a third, the warning\n#: fill; nothing here drew it, so since RNV-NAMED-AND-USED (2026-10-04) it\n#: is not carried.\nFILLS = ("STATUS_SUCCESS", "STATUS_ERROR")\n')
    tree.sub('tests/test_status_family.py',
             '@pytest.mark.parametrize("key,const", [\n    ("success", "STATUS_SUCCESS"),\n    ("warning", "STATUS_WARNING"),\n    ("error", "STATUS_ERROR"),\n])\ndef test_every_semantic_key_is_wired_through_a_constant(key, const):\n    """Swapping one literal for another passes a value check and defeats the\n    point: the constant is what a later register change moves.\n\n    Before 2026-09-03 all three of these were bare literals in two palettes,\n    and the green additionally had two more copies in the file tail -- one\n    colour at four addresses, none of them naming it.\n    """\n    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")\n    found = len(re.findall(r"\'%s\':\\s+%s,\\n" % (key, const), src))\n    assert found == 2, (\n        f"\'{key}\' is wired through {const} in {found} palettes, not 2")\n',
             "# RNV-NAMED-AND-USED (2026-10-04): a test stood here that held the palettes'\n# semantic keys to the fills by name. The keys went: no line of this\n# application looked one up. What it paints from the family is the badges,\n# the error text and the rating scale, each held below; and\n# tests/test_named_and_used.py fails for any palette colour nothing reads.\n")
    tree.sub('tests/test_status_family.py',
             '    ("dark", "panel_bg"), ("light", "panel_bg"), ("image", "panel_bg"),\n',
             '    ("dark", "dialog_bg"), ("light", "dialog_bg"), ("image", "dialog_bg"),\n')
    tree.sub('tests/test_status_family.py',
             '    STATUS_ERROR_BG was already this shape. STATUS_SUCCESS_BG and\n    STATUS_ACTIVE_COLOR each held their own copy of the green instead.\n    """\n    assert C.STATUS_SUCCESS_BG == C.STATUS_SUCCESS\n    assert C.STATUS_ERROR_BG == C.STATUS_ERROR\n    assert C.STATUS_ACTIVE_COLOR == C.STATUS_SUCCESS_TEXT\n    assert C.STATUS_ACTIVE_COLOR != C.STATUS_SUCCESS, (\n        "the active alias points at the FILL. An `active` label is painted "\n        "with `color:` -- the register ruled on 2026-09-04 that it aliases "\n        "success-text -- and the fill reads 3.91 on BRAND_BLACK against a 4.5 "\n        "text floor. Nothing paints this constant in THIS app, which is why "\n        "it has to be right: it is what the next reader copies.")\n',
             '    STATUS_ERROR_BG was already this shape. STATUS_SUCCESS_BG held its own\n    copy of the green instead, and so did an alias for an active label,\n    which nothing painted; that alias went on 2026-10-04 (RNV-NAMED-AND-\n    USED).\n    """\n    assert C.STATUS_SUCCESS_BG == C.STATUS_SUCCESS\n    assert C.STATUS_ERROR_BG == C.STATUS_ERROR\n')
    tree.sub('tests/test_light_wiring.py',
             '        frozenset({"APP_PRESSED_LIGHT", "GREY_E0"}),\n        frozenset({"APP_HOVER_LIGHT", "GREY_EE"}),\n        frozenset({"APP_TEXT", "GREY_DD"}),\n',
             '        frozenset({"APP_PRESSED_LIGHT", "GREY_E0"}),\n')
    tree.sub('tests/test_gold_as_text.py',
             "#: Keys tried, in order, when a rule inherits its ground.\nGROUND_KEYS = ('panel_bg', 'window_bg', 'card_bg')\n",
             "#: Keys tried, in order, when a rule inherits its ground. dialog_bg was\n#: panel_bg until RNV-NAMED-AND-USED (2026-10-04): nothing painted panel_bg,\n#: and dialog_bg is the key that paints the same ground at the same value.\nGROUND_KEYS = ('dialog_bg', 'window_bg', 'card_bg')\n")
    if (tree.root / 'tests/test_named_and_used.py').exists():
        raise Stop('tests/test_named_and_used.py' + ' exists already: this round creates it', EXIT_CANNOT_RUN)
    tree.write('tests/test_named_and_used.py', '"""\ntests/test_named_and_used.py\n============================\nRNV-NAMED-AND-USED, 2026-10-04. Every colour in the application is named,\nand every name is used.\n\nRuled 2026-10-04: "As long as a color exist in the app it should be named\nand used no hardcoded or pointless literals should exist, only literals with\na purpose, like data or comparison are allowed. Colors are name for swap\nability and alignment."\n\nIn this application that removed 17 palette keys no mode read, image mode\'s\nscroll_area_bg override, and six constants only tests held; and it named the\nselection box\'s yellow, the cache\'s black and white, the paper and ink of\nthe exported palette sheet, and the channels an entry with no rgb is read as.\n\nThree sweeps hold it, each over the application\'s own source:\n\n1. NAMED. No colour is written out in the code. Every spelling is read: hex,\n   rgb() and rgba(), a CSS colour name, QColor built from numbers, a Qt\n   global colour, a tuple or a list of channels, an alpha set as a number.\n   A colour is written once, in the colour module, under a name; everything\n   else reads the name. What stays written is DATA, each entry with its\n   reason, and the sweep fails for an entry that no longer matches anything.\n2. USED, the palettes. Every colour a palette holds is looked up by key\n   somewhere in the application.\n3. USED, the constants. Every colour the colour module names is read\n   somewhere in the application: by the palettes, by another constant, or by\n   the code.\n\nClear is not a colour: \'transparent\', alpha 0 and Qt\'s transparent are how a\nwidget is told to paint nothing, and are left as written.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport importlib\nimport pathlib\nimport re\n\nimport pytest\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\n\n#: Where this application writes its colours: the one place a literal belongs.\nCOLOUR_MODULES = ("utils/config.py",)\n#: Where its palettes are written: their own keys are not lookups.\nPALETTE_MODULES = COLOUR_MODULES\nSKIP_DIRS = {"tests", "build", "dist", "docs", "resources", "scripts", "snapshots", "__pycache__"}\n\nfrom utils.config import DARK_THEME_COLORS, IMAGE_MODE_COLORS, LIGHT_THEME_COLORS  # noqa: E402\n\nPALETTES = {"DARK_THEME_COLORS": DARK_THEME_COLORS, "LIGHT_THEME_COLORS": LIGHT_THEME_COLORS,\n            "IMAGE_MODE_COLORS": IMAGE_MODE_COLORS}\n\n#: Below these a sweep has gone blind.\nMIN_FILES = 30\nMIN_ENTRIES = 150\nMIN_CONSTANTS = 40\n\n#: What stays written, and why: (file, literal) -> the reason. Data a person\n#: starts from or a conversion falls back to is not the application\'s look,\n#: and a brand move should not change it.\nDATA = {\n    ("core/color_math.py", "(0, 0, 0)"):\n        "what safe_rgb() hands back for channels it cannot use: a fallback, as data",\n    ("core/screen_color_picker.py", "(0, 0, 0)"):\n        "the colour under the cursor before the first reading: where the picker starts",\n    ("ui/color_swatch_widget.py", "(0, 0, 0)"):\n        "a swatch built with no colour given, and its hue, saturation and lightness: defaults, as data",\n    ("utils/settings_manager.py", "[200, 200, 200]"):\n        "the stored default of a preference, default_slot_color: data in the settings file, not the look",\n}\n\nCSS_NAMES = frozenset("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue\nblueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue\ndarkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid\ndarkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink\ndeepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold\ngoldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush\nlawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey\nlightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime\nlimegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen\nmediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin\nnavajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise\npalevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue\nsaddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow\nspringgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow\nyellowgreen""".split())\nQT_GLOBAL = frozenset({"white", "black", "red", "darkRed", "green", "darkGreen", "blue", "darkBlue", "cyan",\n                       "darkCyan", "magenta", "darkMagenta", "yellow", "darkYellow", "gray", "darkGray",\n                       "lightGray"})\nHEX = re.compile(r"(?<![\\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_])")\nFUNC = re.compile(r"\\b(?:rgba?|hsla?|hsva?)\\(\\s*[0-9.]+%?\\s*,[^)]*\\)", re.I)\nPROP = re.compile(r"(?:^|[;{\\s\\"\'])((?:[a-z-]*color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-[a-z]+)*|"\n                  r"fill|stroke))\\s*[:=]\\s*([^;{}<>]*)", re.I)\nWORD = re.compile(r"(?<![\\w#.-])([a-z]+)(?![\\w(-])", re.I)\nNOT_A_COLOUR = re.compile(r"margin|padding|spacing|size|offset|geometry|rect|pos|range|version|ratio|weight", re.I)\nA_COLOUR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})|rgba?\\([^)]*\\)")\n\n\ndef _sources():\n    """(repo-relative path, text) of every file of the application: not the\n    tests, not a delivery script, not what a build leaves behind."""\n    for path in sorted(ROOT.rglob("*.py")):\n        rel = path.relative_to(ROOT).as_posix()\n        parts = rel.split("/")\n        if any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):\n            continue\n        if len(parts) == 1 and (parts[0].startswith(("test_", "up", "conftest", "run_tests"))):\n            continue\n        text = path.read_text(encoding="utf-8-sig", errors="replace")\n        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:\n            continue\n        yield rel, text\n\n\ndef _prose(tree) -> set:\n    """ids of the strings that are prose: docstrings and bare string statements."""\n    return {id(n.value) for n in ast.walk(tree)\n            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}\n\n\ndef _clear(literal: str) -> bool:\n    """rgba(..., 0) and QColor(..., 0): clear, not a colour."""\n    nums = re.findall(r"[0-9.]+", literal)\n    return len(nums) == 4 and float(nums[3]) == 0\n\n\ndef _written(rel: str, text: str) -> list:\n    """(line, kind, literal) for every colour this file writes out."""\n    tree = ast.parse(text)\n    prose, out = _prose(tree), []\n    parent = {}\n    for node in ast.walk(tree):\n        for child in ast.iter_child_nodes(node):\n            parent[id(child)] = node\n\n    def named_like(node) -> str:\n        """The name a value is given: its assignment target, keyword or parameter."""\n        up = parent.get(id(node))\n        while isinstance(up, (ast.IfExp, ast.BoolOp, ast.Tuple, ast.List)):\n            node, up = up, parent.get(id(up))\n        if isinstance(up, ast.keyword):\n            return up.arg or ""\n        if isinstance(up, (ast.Assign, ast.AnnAssign)):\n            target = up.targets[0] if isinstance(up, ast.Assign) else up.target\n            return ast.unparse(target)\n        if isinstance(up, ast.arguments):\n            both = up.posonlyargs + up.args\n            if node in up.defaults:\n                return both[len(both) - len(up.defaults) + up.defaults.index(node)].arg\n            if node in up.kw_defaults:\n                return up.kwonlyargs[up.kw_defaults.index(node)].arg\n        return ""\n\n    def a_name_on_its_own(node, up) -> bool:\n        """A CSS colour name that is the whole string, where a colour is given:\n        handed to a call, chosen by an if, assigned, returned, a default or a\n        value in a table. A key, an index and a comparison are not a colour\n        given to anything."""\n        s = node.value\n        if isinstance(up, (ast.Call, ast.keyword, ast.IfExp)):\n            return s.lower() in CSS_NAMES              # Qt and PIL read a name in any case\n        if s not in CSS_NAMES:\n            return False\n        if isinstance(up, ast.Dict):\n            return any(v is node for v in up.values)\n        if isinstance(up, ast.arguments):\n            return node in up.defaults or node in up.kw_defaults\n        return isinstance(up, (ast.Assign, ast.AnnAssign, ast.Return)) and up.value is node\n\n    for node in ast.walk(tree):\n        up = parent.get(id(node))\n        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:\n            s = node.value\n            for m in HEX.finditer(s):\n                out.append((node.lineno, "hex", m.group(0)))\n            for m in FUNC.finditer(s):\n                if not _clear(m.group(0)):\n                    out.append((node.lineno, "func", " ".join(m.group(0).split())))\n            for m in PROP.finditer(s):\n                for w in WORD.finditer(m.group(2)):\n                    if w.group(1).lower() in CSS_NAMES:\n                        out.append((node.lineno, "name", f"{m.group(1).lower()}: {w.group(1)}"))\n            # a colour name on its own: QColor("yellow"), fill="white", ink = "black"\n            if a_name_on_its_own(node, up):\n                out.append((node.lineno, "name", s))\n        elif isinstance(node, ast.Call):\n            name = getattr(node.func, "id", getattr(node.func, "attr", None))\n            if name in ("QColor", "fromRgb", "fromRgbF", "qRgb", "qRgba") and node.args \\\n                    and all(isinstance(a, ast.Constant) and not isinstance(a.value, str) for a in node.args):\n                literal = ast.unparse(node)\n                if not _clear(literal):\n                    out.append((node.lineno, "qcolor", literal))\n            # an alpha set as a number: colour.setAlpha(171). Clear and solid are not a choice of alpha.\n            elif name in ("setAlpha", "setAlphaF") and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) \\\n                    and type(node.args[0].value) in (int, float) \\\n                    and node.args[0].value not in ((0, 255) if name == "setAlpha" else (0, 1)):\n                out.append((node.lineno, "alpha", f"{name}({node.args[0].value!r})"))\n        elif isinstance(node, ast.Attribute) and node.attr in QT_GLOBAL \\\n                and ast.unparse(node.value) in ("Qt.GlobalColor", "Qt", "QtCore.Qt.GlobalColor", "QtCore.Qt"):\n            out.append((node.lineno, "global", ast.unparse(node)))\n        elif isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) in (3, 4) and all(\n                isinstance(e, ast.Constant) and type(e.value) is int and 0 <= e.value <= 255 for e in node.elts):\n            if (isinstance(up, (ast.comprehension, ast.For)) and up.iter is node) \\\n                    or isinstance(up, (ast.Compare, ast.Subscript)):\n                continue                                   # an index, a membership or a comparison\n            if isinstance(up, ast.Call) and getattr(up.func, "id", getattr(up.func, "attr", "")) in QCOLOR_CALLS:\n                continue                                   # counted with its QColor(...)\n            if len(node.elts) == 4 and node.elts[3].value == 0:\n                continue                                   # clear\n            if NOT_A_COLOUR.search(named_like(node)):\n                continue\n            out.append((node.lineno, "list" if isinstance(node, ast.List) else "tuple", ast.unparse(node)))\n    return out\n\n\nQCOLOR_CALLS = ("QColor", "fromRgb", "fromRgbF", "qRgb", "qRgba")\n\n\ndef _all_written() -> list:\n    """(rel, line, kind, literal) outside the colour module."""\n    out = []\n    for rel, text in _sources():\n        if rel in COLOUR_MODULES:\n            continue\n        out += [(rel, line, kind, literal) for line, kind, literal in _written(rel, text)]\n    return out\n\n\ndef _data(rel: str, literal: str):\n    """The DATA entry that covers this literal, or None."""\n    for (where, what) in DATA:\n        if where == rel and what in ("*", literal):\n            return (where, what)\n    return None\n\n\n# ------------------------------------------------------------ guard the guard\n\ndef test_the_sweep_reads_the_application():\n    files = [rel for rel, _text in _sources()]\n    assert len(files) >= MIN_FILES, f"only {len(files)} files swept: the sweep has gone blind"\n    for rel in COLOUR_MODULES:\n        assert rel in files, f"{rel} is not among the files swept"\n    assert not [f for f in files if f.startswith("tests/")], "the sweep reads the tests"\n\n\ndef test_the_sweep_reads_every_spelling():\n    """Each spelling of a colour, in a line of the kind the application\n    writes, is seen; clear, an index and a margin are not."""\n    seen = {(kind, literal) for _line, kind, literal in _written("probe.py", (\n        "from PyQt6.QtGui import QColor\\n"\n        "from PyQt6.QtCore import Qt\\n"\n        "a = \'background-color: #ffcccc; border: 2px solid red;\'\\n"\n        "b = f\'color: rgba(255, 255, 255, 230); padding: {4}px\'\\n"\n        "c = QColor(128, 128, 128)\\n"\n        "d = Qt.GlobalColor.darkGreen\\n"\n        "e = QColor(\'yellow\')\\n"\n        "text_color = (0, 0, 0) if a else (255, 255, 255)\\n"\n        "f = saved.get(\'color\', [200, 200, 200])\\n"\n        "ink = \'white\'\\n"\n        "g = {\'ground\': \'black\'}\\n"\n        "h = Image.new(\'RGB\', (8, 8), \'Gray\')\\n"\n        "c.setAlpha(171)\\n"))}\n    assert seen == {("hex", "#ffcccc"), ("name", "border: red"), ("func", "rgba(255, 255, 255, 230)"),\n                    ("qcolor", "QColor(128, 128, 128)"), ("global", "Qt.GlobalColor.darkGreen"),\n                    ("name", "yellow"), ("tuple", "(0, 0, 0)"), ("tuple", "(255, 255, 255)"),\n                    ("list", "[200, 200, 200]"), ("name", "white"), ("name", "black"), ("name", "Gray"),\n                    ("alpha", "setAlpha(171)")}, seen\n    quiet = _written("probe.py", (\n        "from PyQt6.QtGui import QColor\\n"\n        "from PyQt6.QtCore import Qt\\n"\n        "a = \'background: transparent; border: none; color: rgba(0, 0, 0, 0);\'\\n"\n        "b = QColor(0, 0, 0, 0)\\n"\n        "b.setAlpha(0)\\n"\n        "b.setAlpha(255)\\n"\n        "c = Qt.GlobalColor.transparent\\n"\n        "d = [int(h[i:i + 2], 16) for i in (0, 2, 4)]\\n"\n        "margins = (10, 10, 10, 10)\\n"\n        "sizes = [16, 32, 48]\\n"\n        "\'\'\'a bare string is prose: color: red, #ffcccc\'\'\'\\n"\n        "if d in (5, 10, 20) or d == (0, 0, 0) or a == \'red\':\\n"\n        "    pass\\n"\n        "for size in [16, 32, 48]:\\n"\n        "    e = {\'red\': 1}[\'red\']\\n"))\n    assert quiet == [], quiet\n\n\n# ----------------------------------------------------------------- 1. named\n\ndef test_no_colour_is_written_out_in_the_code():\n    stray = [f"{rel}:{line}  {literal}" for rel, line, _kind, literal in _all_written()\n             if _data(rel, literal) is None]\n    assert not stray, (\n        "a colour is written out where a name belongs. Name it in "\n        f"{COLOUR_MODULES[0]} and read the name; or, if it is data, add it to DATA "\n        "with its reason:\\n  " + "\\n  ".join(stray))\n\n\ndef test_every_data_entry_still_covers_something():\n    """An exemption that outlives what it excused is a licence for the next\n    literal written in that file."""\n    used = {_data(rel, literal) for rel, _line, _kind, literal in _all_written()}\n    stale = [f"{where}: {what}" for (where, what) in DATA if (where, what) not in used]\n    assert not stale, "DATA entries that match nothing now:\\n  " + "\\n  ".join(stale)\n    assert all(reason.strip() for reason in DATA.values()), "a DATA entry has no reason"\n\n\n# ---------------------------------------------------- 2. used: the palettes\n\ndef _strings_the_application_reads() -> set:\n    """Every string the code holds outside the palettes\' own keys: what a\n    lookup by key, or a table of keys, is written with. A module\'s __all__\n    is a list of the names it exports, not of keys, and is left out: a\n    function called warning() does not look up a palette\'s \'warning\'."""\n    out = set()\n    for rel, text in _sources():\n        tree = ast.parse(text)\n        not_keys = _prose(tree)\n        if rel in PALETTE_MODULES:\n            for node in ast.walk(tree):\n                if isinstance(node, ast.Dict):\n                    not_keys |= {id(k) for k in node.keys if k is not None}\n        for node in tree.body:\n            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else\n                      node.target if isinstance(node, ast.AnnAssign) else None)\n            if getattr(target, "id", None) == "__all__" and node.value is not None:\n                not_keys |= {id(n) for n in ast.walk(node.value)}\n        for node in ast.walk(tree):\n            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in not_keys:\n                if (rel, node.value) in NOT_LOOKUPS:        # spelled like a key, and not a lookup of one\n                    _NOT_A_READ_SEEN.add((rel, node.value))\n                    continue\n                out.add(node.value)\n    return out\n\n\ndef test_every_colour_a_palette_holds_is_looked_up():\n    read = _strings_the_application_reads()\n    unread = sorted({f"{name}[{key!r}]" for name, palette in PALETTES.items() for key, value in palette.items()\n                     if isinstance(value, str) and (A_COLOUR.fullmatch(value) or value == "transparent")\n                     and key not in read})\n    assert not unread, (\n        "palette entries nothing in the application looks up. A colour is kept "\n        "for what uses it:\\n  " + "\\n  ".join(unread))\n    assert sum(len(p) for p in PALETTES.values()) >= MIN_ENTRIES, "the palettes have gone missing"\n\n\n# --------------------------------------------------- 3. used: the constants\n\ndef _colour_constants() -> dict:\n    """NAME -> where it is defined, for every module-level constant of the\n    colour module whose value is a colour: a hex string, an rgb() string, or\n    channels under a name that says so."""\n    out = {}\n    for rel in COLOUR_MODULES:\n        module = importlib.import_module(rel[:-3].replace("/", "."))\n        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))\n        for node in tree.body:\n            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else\n                      node.target if isinstance(node, ast.AnnAssign) else None)\n            if not isinstance(target, ast.Name) or not target.id.isupper():\n                continue\n            value = getattr(module, target.id, None)\n            if isinstance(value, str) and A_COLOUR.fullmatch(value):\n                out[target.id] = rel\n            elif isinstance(value, tuple) and len(value) in (3, 4) and all(type(v) is int for v in value) \\\n                    and re.search(r"RGB|COLOR|COLOUR|OVERLAY", target.id):\n                out[target.id] = rel\n    return out\n\n\ndef _names_the_application_reads() -> dict:\n    """NAME -> how many times the code reads it: as a name or as an attribute."""\n    counts: dict[str, int] = {}\n    for rel, text in _sources():\n        for node in ast.walk(ast.parse(text)):\n            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):\n                counts[node.id] = counts.get(node.id, 0) + 1\n            elif isinstance(node, ast.Attribute):\n                if (rel, node.attr) in NOT_READS:           # spelled like a constant, and not a read of one\n                    _NOT_A_READ_SEEN.add((rel, node.attr))\n                    continue\n                counts[node.attr] = counts.get(node.attr, 0) + 1\n    return counts\n\n\ndef test_every_colour_constant_is_read():\n    constants = _colour_constants()\n    assert len(constants) >= MIN_CONSTANTS, f"only {len(constants)} colour constants found"\n    reads = _names_the_application_reads()\n    unread = sorted(name for name in constants if not reads.get(name))\n    assert not unread, (\n        "colour constants nothing in the application reads. A name is kept for "\n        "what uses it:\\n  " + "\\n  ".join(f"{name}  ({constants[name]})" for name in unread))\n\n\ndef test_every_exported_name_exists():\n    """__all__ names what the colour module offers. A name it lists and does\n    not define makes `from module import *` fail."""\n    for rel in COLOUR_MODULES:\n        module = importlib.import_module(rel[:-3].replace("/", "."))\n        missing = [n for n in getattr(module, "__all__", []) if not hasattr(module, n)]\n        assert not missing, f"{rel} exports names it does not define: {missing}"\n\n\n# ---------------------------------------------- image mode\'s own palette\n\n#: Image mode is the dark palette under its own name and, after the spread,\n#: the entries image mode reads and draws for itself. A new one is a\n#: decision: it is added here with the entry.\nIMAGE_OWN = (\'status_error_text\', \'window_bg\', \'zoom_label_bg\', \'checkbox_bg\', \'scrollbar_bg\', \'scrollbar_handle\', \'scrollbar_handle_hover\', \'scrollbar_border\')\n\n\ndef _palette_display(name: str) -> ast.Dict:\n    """The dict display NAME is assigned, at module level or in a class body."""\n    for rel in PALETTE_MODULES:\n        for node in ast.walk(ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))):\n            target = (node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else\n                      node.target if isinstance(node, ast.AnnAssign) else None)\n            if getattr(target, "id", None) == name and isinstance(node.value, ast.Dict):\n                return node.value\n    raise AssertionError(f"{name} is not written as a dict display")\n\n\ndef test_image_mode_is_the_dark_palette_and_its_own_entries():\n    node = _palette_display("IMAGE_MODE_COLORS")\n    spreads = [ast.unparse(v) for k, v in zip(node.keys, node.values) if k is None]\n    assert spreads == ["DARK_THEME_COLORS"] and node.keys[0] is None, (\n        f"IMAGE_MODE_COLORS spreads {spreads}: it is the dark palette first, and no other")\n    written = sorted(k.value for k in node.keys if k is not None and k.value != "name")\n    assert written == sorted(IMAGE_OWN), (\n        "the entries image mode writes for itself are not the ones listed. An entry "\n        f"image mode never reads is a value nothing shows:\\n  written {written}\\n  listed  {sorted(IMAGE_OWN)}")\n\n\n# ------------------------------------------- what only looks like a read\n\n#: A string the code holds that is spelled like a palette key and is not a\n#: lookup of one: (file, string) -> what it is. Left uncounted, so a key\n#: this round removed cannot come back and be taken for read by a line\n#: that never read it.\nNOT_LOOKUPS = {\n    (\'utils/cache.py\', \'error\'):\n        "a part of a cached stylesheet\'s own key, (\'static\', \'error\', colour): it names the "\n        \'sheet, and looks up no palette\',\n}\n\n#: An attribute the code reads that is spelled like a colour constant and is\n#: not one: (file, name) -> what it is. Left uncounted for the same reason.\nNOT_READS = dict()\n\n_NOT_A_READ_SEEN: set = set()\n\n\ndef test_what_only_looks_like_a_read_is_still_in_the_code():\n    """An entry that matches no line excuses nothing, and is taken out."""\n    _strings_the_application_reads()\n    _names_the_application_reads()\n    listed = set(NOT_LOOKUPS) | set(NOT_READS)\n    stale = sorted(listed - _NOT_A_READ_SEEN)\n    assert not stale, f"listed as only looking like a read, and no longer in the code: {stale}"\n    assert all(reason.strip() for reason in list(NOT_LOOKUPS.values()) + list(NOT_READS.values())), (\n        "an entry has no reason")\n')
    tree.delete('tests/test_unconsumed_keys.py')


def _original(tree, rel: str) -> str:
    """The file as it is on disk, which checks() runs before flush() changes,
    normalised the way Tree.read() normalises it."""
    raw = (tree.root / rel).read_bytes()
    text = (raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw).decode("utf-8")
    crlf = text.count("\r\n")
    if crlf and crlf == text.count("\n"):
        text = text.replace("\r\n", "\n")
    return text


def _function(src: str, name: str, cls: str | None = None):
    """The named function, at module level or inside the named class."""
    body = ast.parse(src).body
    if cls is not None:
        body = next(n for n in body if isinstance(n, ast.ClassDef) and n.name == cls).body
    return next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)


def _top(src: str) -> dict:
    """Module-level NAME -> ast.dump of the value it is assigned."""
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            t = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(t, ast.Name):
                out[t.id] = ast.dump(node.value)
    return out


def _entries(node) -> dict:
    """A dict display's literal keys -> ast.dump of each value; ** spreads
    under their own ast.dump, so a moved spread is seen too."""
    return {(k.value if k is not None else "**" + ast.dump(v)): ast.dump(v)
             for k, v in zip(node.keys, node.values)}


def _sheet_parts(call) -> list:
    """The literal text of a setStyleSheet(f"...") call, the parts between
    its placeholders, in order."""
    arg = call.args[0]
    assert isinstance(arg, ast.JoinedStr), ast.unparse(arg)[:80]
    return [v.value for v in arg.values if isinstance(v, ast.Constant)]


def _calls(fn, attr: str) -> list:
    return [c for c in ast.walk(fn) if isinstance(c, ast.Call)
            and getattr(c.func, "attr", getattr(c.func, "id", None)) == attr]


def checks(tree) -> None:
    """Against the IN-MEMORY tree, before anything reaches disk."""
    CFG = "utils/config.py"
    KEYS_GONE = ('accent_pressed', 'bg_secondary', 'border_accent', 'dialog_border', 'error', 'info', 'list_alt_bg', 'list_grid', 'list_header_bg', 'output_text_color', 'panel_bg', 'success', 'text_accent_secondary', 'text_secondary', 'tooltip_bg', 'tooltip_text', 'warning')
    NAMES_GONE = ('BRAND_DARK_GOLD_RGB', 'APP_SURFACE_LIGHT_2', 'GREY_EE', 'GREY_DD', 'STATUS_WARNING', 'STATUS_ACTIVE_COLOR')
    old_cfg, new_cfg = _original(tree, CFG), tree.read(CFG)

    def palette(src, name):
        for node in ast.parse(src).body:
            t = (node.targets[0] if isinstance(node, ast.Assign) else
                 node.target if isinstance(node, ast.AnnAssign) else None)
            if getattr(t, "id", None) == name:
                return _entries(node.value)
        raise AssertionError(f"no {name}")

    def app_sources():
        for p in sorted(tree.root.rglob("*.py")):
            rel = p.relative_to(tree.root).as_posix()
            parts = rel.split("/")
            if any(q in ("tests", "build", "dist", "docs", "resources", "scripts", "snapshots", "__pycache__")
                   or q.startswith(".") for q in parts[:-1]):
                continue
            if len(parts) == 1 and parts[0].startswith(("test_", "up", "conftest", "run_tests")):
                continue
            if rel in tree.deleted:
                continue
            yield rel, (tree.read(rel) if rel in tree.files else p.read_text(encoding="utf-8-sig", errors="replace"))

    # ---- the palettes: seventeen keys out of dark and light, one override out of image, nothing else
    for name in ("DARK_THEME_COLORS", "LIGHT_THEME_COLORS"):
        before, after = palette(old_cfg, name), palette(new_cfg, name)
        assert set(before) - set(after) == set(KEYS_GONE), f"{name} lost {sorted(set(before) - set(after))}"
        assert after == {k: v for k, v in before.items() if k not in KEYS_GONE}, f"{name} moved beyond the keys removed"
    before, after = palette(old_cfg, "IMAGE_MODE_COLORS"), palette(new_cfg, "IMAGE_MODE_COLORS")
    assert set(before) - set(after) == {"scroll_area_bg"} and after == {k: v for k, v in before.items() if k in after}, \
        "IMAGE_MODE_COLORS moved beyond its scroll_area_bg override"
    assert any(k.startswith("**") and "DARK_THEME_COLORS" in k for k in after), \
        "image mode no longer spreads the dark palette: a key removed from dark would not leave it"
    assert not set(KEYS_GONE) & set(after), "image mode overrides a key this round removes"

    # ---- the module: six names go, two come, and only what was derived moves
    old_top, new_top = _top(old_cfg), _top(new_cfg)
    assert set(old_top) - set(new_top) == set(NAMES_GONE), sorted(set(old_top) ^ set(new_top))
    assert set(new_top) - set(old_top) == {"SELECTION_BOX_COLOR", "MISSING_RGB_PLACEHOLDER"}, \
        sorted(set(new_top) - set(old_top))
    assert new_top["SELECTION_BOX_COLOR"] == ast.dump(ast.Constant("#ffff00")), "the selection box is not CSS yellow"
    assert new_top["MISSING_RGB_PLACEHOLDER"] == ast.dump(ast.parse("_to_rgb(MISSING_HEX_PLACEHOLDER)", mode="eval").body), \
        "the sentinel's channels are not made from its hex"
    moved = sorted(n for n in new_top if n in old_top and old_top[n] != new_top[n])
    assert moved == ["APP_PROVENANCE", "DARK_THEME_COLORS", "IMAGE_MODE_COLORS", "LIGHT_THEME_COLORS", "__all__"], moved
    prov_b, prov_a = palette(old_cfg, "APP_PROVENANCE"), palette(new_cfg, "APP_PROVENANCE")
    assert prov_a == {k: v for k, v in prov_b.items() if k not in NAMES_GONE} and set(prov_b) - set(prov_a) <= set(NAMES_GONE)

    def functions(src):
        return {n.name: ast.dump(n) for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    fo, fn = functions(old_cfg), functions(new_cfg)
    assert set(fo) == set(fn) and sorted(k for k in fo if fo[k] != fn[k]) == ["contrast_ink_rgb"], \
        f"config.py: functions moved: {sorted(k for k in fo if fo.get(k) != fn.get(k))}"
    assert "return _to_rgb(contrast_ink(background))" in ast.unparse(_function(new_cfg, "contrast_ink_rgb")), \
        "contrast_ink_rgb() does not take its triple from the ink's own name"
    exported = next(ast.literal_eval(n.value) for n in ast.parse(new_cfg).body
                    if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", None) == "__all__")
    was = next(ast.literal_eval(n.value) for n in ast.parse(old_cfg).body
               if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", None) == "__all__")
    defined = set(new_top) | set(fn)
    assert not [n for n in exported if n not in defined], f"__all__ names what is not defined: {[n for n in exported if n not in defined]}"
    assert set(was) - set(exported) == {"BRAND_DARK_GOLD_RGB", "STATUS_ACTIVE_COLOR", "STATUS_ERROR_LIGHT"} \
        and set(exported) - set(was) == {"SELECTION_BOX_COLOR", "MISSING_RGB_PLACEHOLDER"}, \
        "__all__ moved beyond the names removed and the two added"

    # ---- derived, over the whole application: nothing reads what went
    for rel, text in app_sources():
        for node in ast.walk(ast.parse(text)):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif isinstance(node, ast.Call) and getattr(node.func, "attr", None) in ("get", "pop", "setdefault") \
                    and node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
            assert not (isinstance(key, str) and key in KEYS_GONE), \
                f"{rel}:{node.lineno} looks up {key!r}, a key this round removes"
            name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else \
                [a.name for a in node.names] if isinstance(node, ast.ImportFrom) else None
            for n in ([name] if isinstance(name, str) else name or []):
                assert n not in NAMES_GONE, f"{rel}:{node.lineno} still names {n}, which this round removes"

    # ---- named: the spellings the code held are gone, and the names are read
    viewer = tree.read("ui/image_viewer.py")
    assert "yellow" not in [n.value for n in ast.walk(ast.parse(viewer)) if isinstance(n, ast.Constant)], \
        "ui/image_viewer.py still writes the selection box's colour out"
    assert viewer.count("QColorCache.get(SELECTION_BOX_COLOR)") == 1 and viewer.count("QColor(SELECTION_BOX_COLOR)") == 1
    cache = tree.read("utils/cache.py")
    init = ast.unparse(_function(cache, "_init_constants", "QColorCache"))
    assert "cls.BLACK = QColor(TRUE_BLACK)" in init and "cls.WHITE = QColor(WHITE)" in init, \
        "the cache's black and white are not made from their names"
    old_init = ast.unparse(_function(_original(tree, "utils/cache.py"), "_init_constants", "QColorCache"))
    assert init == old_init.replace("QColor(0, 0, 0)\n", "QColor(TRUE_BLACK)\n").replace("QColor(255, 255, 255)", "QColor(WHITE)"), \
        "QColorCache._init_constants() moved beyond black and white"
    for rel in ("RNV_Color_Picker.py", "core/workers.py"):
        old_src, new_src = _original(tree, rel), tree.read(rel)
        owner = [n for n in ast.walk(ast.parse(new_src)) if isinstance(n, ast.FunctionDef)
                 and "SVG_EXPORT_BG" in ast.unparse(n)]
        assert len(owner) == 1, f"{rel}: the sheet's paper is named in {len(owner)} functions"
        body = ast.unparse(owner[0])
        assert body.count("Image.new('RGBA', (page_width, page_height), SVG_EXPORT_BG)") == 1 \
            and body.count("Image.new('RGB', (page_width, page_height), SVG_EXPORT_BG)") == 1 \
            and body.count("outline=SVG_EXPORT_STROKE") == 1 \
            and body.count("text_color = contrast_ink_rgb((r, g, b))") == 1, f"{rel}: the sheet is not drawn by name"
        was_fn = next(n for n in ast.walk(ast.parse(old_src)) if isinstance(n, ast.FunctionDef) and n.name == owner[0].name
                      and "palette_img = Image.new" in ast.unparse(n))
        want = (ast.unparse(was_fn)
                .replace("(255, 255, 255, 255))", "SVG_EXPORT_BG)").replace("(page_width, page_height), (255, 255, 255))",
                                                                           "(page_width, page_height), SVG_EXPORT_BG)")
                .replace("outline=(0, 0, 0)", "outline=SVG_EXPORT_STROKE")
                .replace("text_color = (0, 0, 0) if prefers_dark_ink((r, g, b)) else (255, 255, 255)",
                         "text_color = contrast_ink_rgb((r, g, b))"))
        assert body == want, f"{rel}: {owner[0].name}() moved beyond naming its paper and ink"
    access = tree.read("core/accessibility.py")
    assert "return config.contrast_ink_rgb(background)" in access and "(255, 255, 255) if ink" not in access

    # ---- an entry with no rgb: its four readers take the sentinel by name, and nothing else in them moves
    for rel, count, old_import, new_import in (
            ("core/color_history.py", 1, "from utils.cache import ColorCache\n",
             "from utils.cache import ColorCache\nfrom utils.config import MISSING_RGB_PLACEHOLDER\n"),
            ("ui/settings_panel.py", 3, "MISSING_HEX_PLACEHOLDER\n", "MISSING_HEX_PLACEHOLDER, MISSING_RGB_PLACEHOLDER\n")):
        was_u, now_u = ast.unparse(ast.parse(_original(tree, rel))), ast.unparse(ast.parse(tree.read(rel)))
        assert was_u.count("[0, 0, 0]") == count and was_u.count(old_import) == 1, f"{rel}: not as this round found it"
        assert now_u == was_u.replace("[0, 0, 0]", "MISSING_RGB_PLACEHOLDER").replace(old_import, new_import), \
            f"{rel}: moved beyond reading the sentinel by its name"

    # ---- the tests: the locked suite keeps every test, one guard file goes, one comes
    def tests_in(src):
        return [n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert tests_in(_original(tree, "test_rnv_color_picker.py")) == tests_in(tree.read("test_rnv_color_picker.py")), \
        "the locked root suite gained or lost a test"
    assert "tests/test_unconsumed_keys.py" in tree.deleted, "the NOT CONSUMED test is not removed"
    assert "NOT CONSUMED" not in new_cfg, "a NOT CONSUMED note is still in the palette"
    assert tests_in(tree.read(GUARD)) == ['test_the_sweep_reads_the_application', 'test_the_sweep_reads_every_spelling', 'test_no_colour_is_written_out_in_the_code', 'test_every_data_entry_still_covers_something', 'test_every_colour_a_palette_holds_is_looked_up', 'test_every_colour_constant_is_read', 'test_every_exported_name_exists', 'test_image_mode_is_the_dark_palette_and_its_own_entries', 'test_what_only_looks_like_a_read_is_still_in_the_code'], f"{GUARD}: its tests are {tests_in(tree.read(GUARD))}"
    for rel in GUARD_FILES[1:]:
        lost = sorted(set(tests_in(_original(tree, rel))) - set(tests_in(tree.read(rel))))
        want = ["test_every_semantic_key_is_wired_through_a_constant"] if rel == "tests/test_status_family.py" else []
        assert lost == want, f"{rel} lost {lost}"
    assert SENTINEL in new_cfg and SENTINEL in tree.read(GUARD), "the sentinel is not in the palette and its guard"
# ------------------------------------------------------------------ plumbing
#
# EXIT CODES ARE A TAXONOMY, NOT A BOOLEAN. Rev 6 §3.0.1. A harness that
# returns non-zero for everything tells the operator something is wrong and
# nothing about what, and the three non-zero cases want three different
# actions: read the diff, install something, re-run.
EXIT_CLEAN = 0       # everything agreed
EXIT_DISAGREES = 1   # something ran and disagreed -- read it
EXIT_CANNOT_RUN = 2  # the environment is not ready -- nothing was asked
EXIT_INCOMPLETE = 3  # it ran and did not finish -- re-run before believing it


class Stop(SystemExit):
    """A refusal this script chose, as opposed to a crash.

    Carries an exit code from the taxonomy. Bare SystemExit('message') exits 1,
    which says A TEST DISAGREED -- so every refusal used to arrive wearing the
    one verdict it was not.
    """

    def __init__(self, message: str, code: int = EXIT_CANNOT_RUN) -> None:
        super().__init__(message)
        self.code = code


#: Two files per repository that exist there and in none of the others.
#: Verified against the live fleet by _fingerprint_check.py at build time,
#: because a fingerprint that has been renamed away identifies nothing and
#: would refuse every correct checkout.
FINGERPRINTS = {
    "rnv-color-mixer": ("core/image_handler.py", "ui/canvas_view.py"),
    "rnv-color-palette-manager": ("core/color_extractor.py",
                                  "ui/batch_export_dialog.py"),
    "rnv-color-picker": ("core/hilbert_curve.py", "ui/color_swatch_widget.py"),
    "rnv-icon-builder": ("core/icon_builder_core.py", "core/project_manager.py"),
    "rnv-text-transformer": ("core/diff_engine.py", "core/text_cleaner.py"),
}


def refuse_wrong_repository(root) -> None:
    """Refuse a checkout that is not the repository this script was built for.

    CALLED FIRST IN apply(), BEFORE THE SENTINEL AND BEFORE ANY ANCHOR, and the
    order is the whole point. The five applications share file names -- four of
    them have a utils/config.py or a ui/colors.py, and several share a
    tests/conftest.py. Run in the wrong sibling, a sentinel check says "already
    applied" or "not a checkout" and an anchor check says "the file moved",
    and BOTH of those are the script guessing at the wrong question.

    A fingerprint is a file only the right repository has. Two, because one
    that gets renamed takes the check with it.
    """
    want = FINGERPRINTS.get(REPO)
    if not want:
        return
    missing = [f for f in want if not (root / f).exists()]
    if missing:
        raise Stop(
            f"this is not a {REPO} checkout.\n"
            f"  expected to find: {', '.join(want)}\n"
            f"  missing here:     {', '.join(missing)}\n"
            f"Run it from the root of {REPO}. Nothing was read or written.",
            EXIT_CANNOT_RUN)


def _left_alone() -> None:
    """Print what this round deliberately did not touch.

    LEFT_ALONE is optional and is prose, not a guard. It exists because a
    reader of a diff can see what changed and cannot see what was considered
    and declined, and the second is where a round's scope actually lives.
    """
    items = globals().get("LEFT_ALONE")
    if not items:
        return
    print("\nleft alone, deliberately:")
    for line in items:
        print(f"  - {line}")


def refuse_to_shadow() -> None:
    name = Path(__file__).name
    if name in SHADOWS:
        raise Stop(f"refusing to run as {name} -- it would shadow a module on "
                   f"sys.path. Rename to up.py and run again.", EXIT_CANNOT_RUN)


class Tree:
    """Every edit lands here first. Disk is written only after all guards pass,
    so --check is a real rehearsal and a half-applied state is impossible."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, str] = {}
        self.deleted: set[str] = set()
        #: rel -> (had a BOM, line endings were CRLF throughout). What a file
        #: was on disk, so flush() can put back exactly that around the edit.
        self.form: dict[str, tuple[bool, bool]] = {}

    def read(self, rel: str) -> str:
        """The file as text with LF line endings, whatever it is on disk.

        A FILE IS ITS BYTES, AND AN EDIT MUST NOT CHANGE THE ONES IT DID NOT
        MEAN TO. This used to read with read_text('utf-8-sig') and flush with
        encode('utf-8'). The first strips a byte-order mark and folds CRLF to
        LF; the second puts neither back. So a one-line edit to a CRLF file
        rewrote every line ending in it, and any edit to a file with a BOM
        deleted its first three bytes. rnv-color-picker's utils/config.py --
        the picker's palette -- carries a BOM, so its next round would have.

        Anchors are written with \\n, so a CRLF file is held as LF in memory
        and its endings are restored on write. A file that MIXES endings is
        held exactly as it is: anchors then match only its LF lines, and
        everything else round-trips untouched.
        """
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise Stop(f"missing file: {rel}", EXIT_CANNOT_RUN)
            raw = p.read_bytes()
            bom = raw.startswith(b"\xef\xbb\xbf")
            text = (raw[3:] if bom else raw).decode("utf-8")
            crlf = text.count("\r\n")
            all_crlf = crlf > 0 and crlf == text.count("\n")
            if all_crlf:
                text = text.replace("\r\n", "\n")
            self.files[rel] = text
            self.form[rel] = (bom, all_crlf)
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        """Mark a file for removal. Nothing leaves disk until flush()."""
        if not (self.root / rel).exists() and rel not in self.files:
            raise Stop(f"cannot delete {rel}: it is not in this checkout",
                       EXIT_CANNOT_RUN)
        self.files.pop(rel, None)
        self.deleted.add(rel)

    def sub(self, rel: str, old: str, new: str, times: int = 1) -> None:
        src = self.read(rel)
        found = src.count(old)
        if found != times:
            raise Stop(
                f"{rel}: expected {times} occurrence(s) of the anchor, found "
                f"{found}. The file moved; re-derive this edit before trusting "
                f"the script.", EXIT_CANNOT_RUN)
        self.write(rel, src.replace(old, new, times))

    def flush(self) -> list[str]:
        """Compare and write BYTES, not decoded text.

        read_text('utf-8') here raised on a file that was not valid UTF-8 --
        which is precisely the file some scripts exist to fix. Bytes compare
        identically for everything else and cannot refuse to look."""
        touched = []
        for rel in sorted(self.deleted):
            p = self.root / rel
            if p.exists():
                p.unlink()
                touched.append(f"{rel} (deleted)")
        for rel, text in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = self.encode(rel, text)
            if not p.exists() or p.read_bytes() != data:
                p.write_bytes(data)
                touched.append(rel)
        return touched

    def encode(self, rel: str, text: str) -> bytes:
        """Text back to bytes in the form the file had when it was read.

        A file never read -- one this script creates -- has no form to keep
        and is written as plain UTF-8 with LF, which is what every file in
        this fleet is unless it says otherwise.
        """
        bom, all_crlf = self.form.get(rel, (False, False))
        if all_crlf:
            text = text.replace("\n", "\r\n")
        return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


def _tail(out: str, lines: int = 40) -> str:
    text = out.strip()
    marker = "short test summary info"
    if marker in text:
        return text[max(0, text.rindex(marker) - 30):]
    return "\n".join(text.splitlines()[-lines:])


def _outcome(code: int, out: str) -> str:
    """"pass", "fail", "abort", "killed" or "env" -- only exit code 1 means a
    test failed.

    pytest exits 0 passed, 1 tests failed, 2 interrupted, 3 internal error,
    4 usage error, 5 nothing collected; a native abort arrives as 134 or -6.
    Treating every non-zero code as a failing assertion is how a tool reports
    a regression that never happened.
    """
    if code == 0:
        return "pass"
    if code in (-9, 137, -15, 143):
        return "killed"
    if code in (134, -6, 139, -11) or "Fatal Python error" in out:
        return "abort"
    if code == 1 and "INTERNALERROR" not in out:
        # EXIT 1 IS NOT ALWAYS A TEST DISAGREEING, and this used to assume it
        # was. A missing pytest PLUGIN or a missing pinned package does not
        # stop collection -- the tests are found, then fail at setup -- so
        # pytest exits 1, the same code a real regression gives.
        #
        # It shipped that way. A fresh Codespace with the app requirements and
        # none of tests/requirements-dev.txt ran a round that had landed
        # cleanly and got 85 errors ("fixture 'qtbot' not found": pytest-qt)
        # and 3 failures ("No module named 'engine'": the rnv-brand pin), and
        # the verdict was "FAILED -- the suite is not green". Not one of the 88
        # was the change disagreeing with anything.
        #
        # The discriminator is the assertion. A regression raises
        # AssertionError; a missing dependency raises nothing of the kind. If
        # the run carries environment signatures and NO assertion failure, it
        # is the environment. If it carries both, it is a failure -- the
        # conservative direction, because under-reporting a real regression is
        # the one way this verdict must never be wrong.
        if _missing_dependency(out) and not _ASSERTION.search(out):
            return "env"
        return "fail"
    return "env"


#: A dependency that is not installed, as pytest reports it. Each of these
#: arrived in a real run of this fleet's suites.
_ENV_SIGNS = (
    re.compile(r"fixture '\w+' not found"),                 # a pytest plugin
    re.compile(r"ModuleNotFoundError: No module named"),    # a package
    re.compile(r"\bis not importable\b"),                   # the register pin
    re.compile(r"ImportError: lib[\w.+-]+\.so"),            # a system library
)
#: A real regression. pytest prints the failing line under `E   ` and the
#: exception class in the summary.
_ASSERTION = re.compile(r"^E\s+assert\b|\bAssertionError\b", re.M)


def _missing_dependency(out: str) -> bool:
    return any(sign.search(out) for sign in _ENV_SIGNS)


#: verdict -> taxonomy. "abort" and "killed" are EXIT_INCOMPLETE rather than
#: EXIT_CANNOT_RUN: the environment WAS ready and the run started, which is a
#: different instruction to the operator -- re-run, do not go installing things.
_VERDICT_CODE = {
    "pass": EXIT_CLEAN,
    "fail": EXIT_DISAGREES,
    "env": EXIT_CANNOT_RUN,
    "abort": EXIT_INCOMPLETE,
    "killed": EXIT_INCOMPLETE,
}


ENV_HELP = """\
THE ENVIRONMENT IS NOT READY. NO TEST DISAGREED WITH THIS CHANGE -- the run
did not get far enough to ask one.

PyQt6 needs system libraries a fresh container does not ship; the give-away is
`ImportError: libGL.so.1`. Install those, then the Python packages:

    sudo apt-get update
    sudo apt-get install -y libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 \\
      libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \\
      libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 \\
      libxcb-xfixes0 libxcb-xkb1

    pip install -r requirements.txt -r tests/requirements-dev.txt
    python up.py --verify
"""

ABORT_HELP = """\
PYTHON ABORTED NATIVELY. That is not a failing assertion. On offscreen Linux
these suites can abort in Qt's thread teardown -- it surfaces during whatever
work is in flight and reads exactly like a regression in it.

Re-run:

    python up.py --verify

If it aborts every time on the same test, that is worth looking at. If it
comes and goes, this change is not involved.
"""

KILLED_HELP = """\
THE TEST PROCESS WAS KILLED FROM OUTSIDE. No test failed and nothing crashed --
something stopped the run, and on a small runner that is almost always the
out-of-memory killer arriving part way through a long Qt suite.

Re-run:

    python up.py --verify

If it keeps dying at roughly the same point, run the suite on its own so you
can watch it, and close anything else heavy first:

    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
"""


def run(label: str, args: list[str]) -> tuple[int, str]:
    """Stream to a temp file rather than capture_output: a long Qt suite emits
    megabytes, and buffering that in memory can get the run killed, which looks
    exactly like a failure."""
    print(f"  {label} ...", flush=True)
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8",
                                errors="replace") as fh:
        proc = subprocess.run(args, stdout=fh, stderr=subprocess.STDOUT, env=env)
        fh.seek(0)
        out = fh.read()
    return proc.returncode, out


def _step(label: str, args: list[str]) -> int:
    code, out = run(label, args)
    verdict = _outcome(code, out)
    print(_tail(out) if verdict != "pass"
          else "\n".join(out.strip().splitlines()[-3:]))
    if verdict == "env":
        print("\n" + ENV_HELP)
    elif verdict == "abort":
        print("\n" + ABORT_HELP)
    elif verdict == "killed":
        print("\n" + KILLED_HELP)
    elif verdict == "fail":
        print("\nFAILED -- the suite is not green. Nothing was reverted; "
              "`git diff` shows exactly what landed.")
    return _VERDICT_CODE[verdict]


def verify() -> int:
    # A script that changes the ENVIRONMENT its suites run in does it here,
    # not in checks(): checks() runs against the in-memory tree before
    # anything is on disk. The register pin is the case that needed it -- it
    # writes a dependency line and then runs tests that import what the line
    # declares, and DECLARING IS NOT INSTALLING.
    #
    # In verify() rather than apply() so that `--verify` gets it too; that is
    # the entry point someone uses to re-check a repository, and it has to
    # prepare the same environment.
    hook = globals().get("post_write")
    if hook is not None:
        hook()
        print()

    # GUARD_CMD is OPTIONAL and exists for a repository with no pytest. Every
    # round until 2026-09-12 ran inside one of the five applications, where a
    # guard is a test file; rnv-brand has no tests directory, no pytest
    # dependency, and a deliberate ZERO-IMPORT policy in engine/brand.py --
    # its own idiom is a function that runs AT IMPORT and raises. Installing
    # pytest there to satisfy this harness would change the shape of someone
    # else's repository to suit a tool, which is backwards. GUARD still names
    # the file that holds the check; GUARD_CMD says how to run it.
    guard_cmd = globals().get("GUARD_CMD") or [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", GUARD]
    code = _step("guard", guard_cmd)
    if code != EXIT_CLEAN:
        return code
    for label, args in SUITES:
        code = _step(label, args)
        if code != EXIT_CLEAN:
            return code
    print("\nGreen.")
    return EXIT_CLEAN


def apply(check_only: bool) -> int:
    root = Path.cwd()

    # FIRST. Before the sentinel, before any anchor. See the docstring.
    refuse_wrong_repository(root)

    if not (root / SENTINEL_FILE).exists():
        # A script whose sentinel file is created by an EARLIER script cannot
        # tell "wrong directory" from "prerequisite not run", and the default
        # message asserts the first while the second is more likely. Such a
        # script sets MISSING_HELP and says which one to run.
        raise Stop(globals().get("MISSING_HELP") or
                   f"run this from the root of a {REPO} checkout "
                   f"(no {SENTINEL_FILE} here)", EXIT_CANNOT_RUN)

    if SENTINEL in (root / SENTINEL_FILE).read_text(encoding="utf-8-sig"):
        # ALREADY APPLIED IS NOT AN ERROR, AND USED TO EXIT 1.
        #
        # The operator runs this from a phone and the honest question behind a
        # second run is "did this land?". Exiting 1 answered "something
        # disagreed", which is the one thing that had not happened. Re-running
        # the suites answers the question that was actually asked, and a
        # repository that has the change and passes its tests is CLEAN.
        print(f"already applied -- {SENTINEL!r} is present in "
              f"{SENTINEL_FILE}.\nNothing to write. Re-running the suites so "
              f"the answer is measured rather than assumed.\n")
        return verify()

    tree = Tree(root)
    edits(tree)

    # THE SCRIPT MUST WRITE ITS OWN SENTINEL WHERE apply() LOOKS FOR IT.
    #
    # Checked here, against the in-memory tree, before anything reaches disk.
    #
    # WHY THIS IS NOT A BUILD-TIME CHECK. The build's `sentinel-written` guard
    # asserts the marker appears at least twice in the composed script -- its
    # own declaration plus somewhere it gets written. That is a PROXY. A round
    # can carry the marker in a new guard file and never put it in
    # SENTINEL_FILE, and the build passes while the already-applied branch can
    # never fire. That shipped once, on 2026-09-24: the operator ran a landed
    # script a second time and got "expected 1 occurrence of the anchor, found
    # 0. The file moved" -- about a file that had not moved, from a script
    # that could not tell it had already run.
    #
    # Here the question is exact rather than approximated: after every edit,
    # is the marker in the file apply() reads? It fires on the FIRST run, in
    # the author's verification, rather than on the operator's second.
    if SENTINEL not in tree.read(SENTINEL_FILE):
        raise Stop(
            f"this script never writes {SENTINEL!r} into {SENTINEL_FILE}, "
            f"which is the file it reads to tell whether it has already run.\n"
            f"Applied once it would work; run again it would re-attempt "
            f"anchors that are already replaced and report them as missing.\n"
            f"Add an edit that marks {SENTINEL_FILE}. Nothing was written.",
            EXIT_CANNOT_RUN)
    # GUARD_SOURCE is OPTIONAL. Every round until 2026-09-12 installed a new
    # guard file, so the harness assumed one; the ramp-condense round adopts
    # three that already exist -- the mixer's SPLITS table and two RETIRED
    # tuples -- and adding a fourth rule for what they already watch is how a
    # suite grows checks that disagree. GUARD still names the file verify()
    # runs first; it just does not have to be a file this script wrote.
    source = globals().get("GUARD_SOURCE")
    if source is not None:
        tree.write(GUARD, source)
    checks(tree)

    if check_only:
        print("--check: every edit composes and every guard passes. "
              "Nothing written.")
        _left_alone()
        return EXIT_CLEAN

    touched = tree.flush()
    print("wrote: " + ", ".join(touched) + "\n")
    code = verify()
    if code == EXIT_CLEAN:
        _left_alone()
    return code


def finish() -> None:
    me = Path(__file__).resolve()
    print(f"removing {me.name}")
    me.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--check", action="store_true",
                    help="rehearse every edit in memory, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run the suites only, change nothing")
    ap.add_argument("--finish", action="store_true", help="delete this script")
    args = ap.parse_args()
    try:
        refuse_to_shadow()
        if args.finish:
            finish()
            return EXIT_CLEAN
        if args.verify:
            return verify()
        return apply(args.check)
    except Stop as stop:
        # Print it ourselves and return the taxonomy code. Letting SystemExit
        # propagate would print the message and exit 1 regardless of .code.
        print(stop.args[0] if stop.args else "", file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    raise SystemExit(main())
