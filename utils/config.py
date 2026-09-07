"""
Application configuration and theme management for RNV Color Picker.

This module is the SINGLE SOURCE OF TRUTH for all colors in the application.

Structure:
- Brand colors (BRAND_GOLD, BRAND_DARK_GOLD) — referenced everywhere, never duplicated
- Theme color dicts (DARK_THEME_COLORS, LIGHT_THEME_COLORS, IMAGE_MODE_COLORS)
- Standalone constants (GREY_44, DEBUG_TEXT, etc.) and the ink rule
- get_theme_colors() entry function
- ThemeManager class for runtime theme state

Any hardcoded color in another file is a bug. All colors must come from here.

Python 3.13 optimized - using modern type hints.
"""

from __future__ import annotations

import os
import io
from typing import Final
from PIL import Image
from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QPixmap

from utils.logger import Logger

_logger = Logger("Config")


# ============================================================================
# APPLICATION CONSTANTS
# ============================================================================

# Application metadata
APP_NAME = "RNV Color Picker"
APP_VERSION = "3.0.3"
APP_AUTHOR = "RNV"
APP_TAGLINE = "Professional Color Extraction & Palette Management"

# Color limits
MAX_COLORS = 333
DEFAULT_WEIGHT = 50

# UI dimensions
BUTTON_HEIGHT_MIN = 40
BUTTON_HEIGHT_MAX = 55
WINDOW_WIDTH_MIN = 1059
WINDOW_WIDTH_MAX = 1920
SWATCH_SIZE = 150

# Image handling
MAX_IMAGE_DIMENSION = 3840

# Paths - using __file__ to get correct path relative to this module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
BUTTON_IMAGES_DIR = os.path.join(RESOURCES_DIR, "button_images")
BACKGROUND_IMAGES_DIR = os.path.join(RESOURCES_DIR, "background_images")
FONTS_DIR = os.path.join(RESOURCES_DIR, "fonts")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")


# ============================================================================
# BRAND COLORS
# ============================================================================

# Registered values are mirrored from RNVizion/rnv-brand (engine/brand.py).
# Everything else is COMPUTED from them, never written down, so a derivative
# cannot drift away from the colour it was derived from.
#
# This file previously held six hand-written variants. One of them, the light
# hover #c4a458, was a tint of a value that had since been retired -- orphaned,
# with nothing to flag it. That is the failure derivation prevents.


def _to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Split a six-digit hex colour into an (r, g, b) tuple."""
    h = hex_color.lstrip('#')
    if len(h) != 6:
        raise ValueError(f"expected a six-digit hex colour, got {hex_color!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lighten(hex_color: str, step: int) -> str:
    """Shift every channel by the same number of 8-bit steps.

    A uniform per-channel shift holds hue exactly, which is what keeps a
    derived gold recognisably the same gold. It is also the method the light
    palettes already used before the alignment. Negative darkens.
    """
    return '#' + ''.join(
        f'{max(0, min(255, c + step)):02x}' for c in _to_rgb(hex_color)
    )


BRAND_GOLD: Final[str] = "#d2bc93"
"""Primary brand gold -- dark-mode accents, highlights, tooltips.

Registered brand value. Unchanged by the alignment.
"""

BRAND_DARK_GOLD: Final[str] = "#8c7337"
"""Brand dark gold -- light-mode FILLS, borders and pressed states.

Registered brand value. It replaced the app-local #b19145, which did one
job of six: as text on white it measured 2.9976 against a 4.5 floor, and
as a border 2.9976 against 3.0 -- short by 0.0024, which is why a contrast
tool displaying "3.00" never surfaced it.

Carries white text at 4.5429 and black at 4.6226. Black stays the ruled
pairing and the better number.
"""

BRAND_DARK_GOLD_DEEP: Final[str] = lighten(BRAND_DARK_GOLD, -14)  # -> #7e6529
"""Derived. The one light-mode derivative, serving two roles.

BRAND_DARK_GOLD clears 4.5:1 as TEXT against pure white and nothing else
(#f5f5f5 4.1670, #eeeeee 3.9156). And a hover background carrying white
text needs a gold dark enough for white. Both roles want the same thing,
so they share one value rather than each getting its own.

    white on it ............ 5.5547
    as text on #f5f5f5 ..... 5.0949
    as text on #eeeeee ..... 4.7875
    as text on #e8e8e8 ..... 4.5334   <- binding

-14 is the smallest uniform step that clears all four; -13 gives 4.4675
on #e8e8e8 and fails. Hue is unchanged.

NEVER use as a fill under black text -- black on it is 3.7806. Below
#e8e8e8 gold does not carry text at all; that is a ruling, not a gap.
"""

BRAND_DARK_GOLD_HOVER: Final[str] = BRAND_DARK_GOLD_DEEP
"""Light-mode hover. Hover moves AWAY from its ground.

A dark ground takes a lighter hover; a light ground takes a deeper one.
The retired #c4a458 went lighter on a light ground -- toward it -- which
is why white measured 2.3868 on it. Stated as "a lighter tint for hover
feedback", the old rule was wrong half the time.
"""

BRAND_DARK_GOLD_PRESSED: Final[str] = BRAND_DARK_GOLD
"""Light-mode pressed. It IS the accent.

Two reasons, and either alone would be enough. The brand runs two golds
per mode and light spends its second on BRAND_DARK_GOLD_DEEP. And
darkening past BRAND_DARK_GOLD drops black-on-gold under the floor, which
would force white text and break the register's text-on-gold rule.
"""

BRAND_GOLD_HOVER: Final[str] = lighten(BRAND_GOLD, 13)      # -> #dfc9a0
"""Dark-mode hover. Derived, replacing the hand-written #dcc9a3.

The old hand-written value's deltas were +10/+13/+16 -- non-uniform, so it had
drifted off BRAND_GOLD's hue. A uniform step snaps it back.
"""

BRAND_GOLD_PRESSED: Final[str] = BRAND_GOLD
"""Dark-mode pressed. It IS the accent, mirroring light mode exactly.

The brand runs TWO golds per mode -- the registered one and one derived
from it -- and no more. Dark spends its second on hover, so pressed
returns to the accent rather than claiming a third.

The interaction still reads: rest sits at the accent, hover lifts away
from the dark ground, pressed drops back to rest. That is the same shape
light uses, where hover deepens away from the light ground and pressed
returns. The hand-written #b7a480 it replaces was a third gold serving
one key.
"""

BRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)
"""Derived. A hardcoded tuple is invisible to every hex-based search, so
it survives sweeps that catch every other reference to the colour."""

BRAND_DARK_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_DARK_GOLD)
"""Derived, same reason. This one held (177, 145, 69) -- the retired gold,
in the one form no sweep would have found."""


# ==================== APP Neutrals ====================
#
# MIRRORED FROM RNVizion/rnv-brand engine/brand.py APP. Until 2026-08-28 these
# were bare hex literals in the palettes below -- no constant, no provenance --
# and every one of them is a REGISTERED brand value. A registered value could
# move upstream and this app would keep the old one silently, which is the
# failure #c4a458 had, one level down. It nearly happened: APP["text"] moved
# from #e0e0e0 to #dddddd in rnv-brand@68d195e.
#
# THE INK GRID, published in the brand beside that move:
#
#     grey(n) = n * 0x11, n in 0..15.   TRUE_BLACK -> WHITE in fifteen steps.
#
# IT GOVERNS INKS AND EDGES AND DELIBERATELY DOES NOT GOVERN SURFACES.
# BRAND_BLACK sits at n = 1.53 and APP_CARD at n = 2.47; BRAND_BLACK is a
# permanent and will not move to fit a ladder. The scope is part of the rule.
#
# THIS PASS WIRES THE INK ONLY. The other five constants are defined and
# mirrored here so drift is caught, but the palettes below still spell them as
# literals; rewiring those is the grey-ramp derivation pass, and doing it here
# would have mixed a mechanical substitution into a value change.

TRUE_BLACK: Final[str] = "#000000"
"""engine/brand.py TRUE_BLACK, and APP["window"]. Primary text in light mode,
and the label on a pressed control in dark. grey(0)."""

WHITE: Final[str] = "#ffffff"
"""engine/brand.py WHITE. Control surface in light mode. grey(15)."""

BRAND_BLACK: Final[str] = "#1a1a1a"
"""engine/brand.py BRAND_BLACK, and APP["panel"]. Charcoal; a permanent.
Not on the ink grid (n = 1.53) and not required to be -- it is a surface."""

APP_CARD: Final[str] = "#2a2a2a"
"""engine/brand.py APP["card"]. A surface, not on the grid (n = 2.47)."""

APP_BORDER: Final[str] = "#333333"
"""engine/brand.py APP["border"]. grey(3). An edge, so the grid governs it."""

APP_TEXT: Final[str] = "#dddddd"
"""engine/brand.py APP["text"]. grey(13). Primary ink in dark and image mode.

MOVED FROM #e0e0e0 ON 2026-08-28, with the brand rather than after it.
#e0e0e0 was one hex doing two unrelated jobs -- ink in dark mode, and a light
SURFACE in the light palette below. It refused to sit on the grid because the
grid governs inks and half its uses were not ink. Only the ink half moved.
Contrast falls 0.21 to 0.45 and the floor afterwards is 7.17:1 on the pressed
plate #444444, the darkest ground it is ever drawn on.
"""

APP_TEXT_DIM: Final[str] = "#aaaaaa"
"""engine/brand.py APP["text-dim"]. grey(10)."""

APP_CANVAS: Final[str] = "#0a0a0a"
"""engine/brand.py APP["canvas"]. The n=-1 rung of the dark surface ladder.

REGISTERED 2026-08-29 in rnv-brand rev 22, app-owned here until then.

    BRAND_BLACK + n * 0x10,  n in -1..+2
    #0a0a0a canvas   #1a1a1a panel   #2a2a2a card   #3a3a3a panel-hover

NOT WEB_BLACK. The web ground is #0a0a0f -- same lightness, blue channel
lifted. App neutrals are pure grey, R = G = B, without exception, and the web
carries a tint the apps do not. The two are one byte apart on purpose, and that
byte is why invert(#0a0a0a) = #f5f5f5 once looked like a light-ground rule and
was not: the register's canvas inverts to #f5f5f0.
"""

APP_PANEL_HOVER: Final[str] = "#3a3a3a"
"""engine/brand.py APP["panel-hover"]. The n=+2 rung, and the dark interaction
plate.

REGISTERED 2026-08-29, app-owned here until then. The register had called the
ladder "two-thirds specified" because APP_BORDER #333333 is not #3a3a3a and so
looked like a missing rung. It is not a rung at all: #333333 is grey(3) on the
INK grid, which governs inks and EDGES, and a border is an edge. The ladder was
complete when the question was first asked.
"""

APP_HOVER_LIGHT: Final[str] = "#eeeeee"
"""engine/brand.py APP["hover-light"]. grey(14). The light interaction plate.

REGISTERED 2026-08-29 as #e8e8e8 and MOVED to #eeeeee on 2026-08-30 in rev 23,
before any app had been wired to it. Nothing here changes value -- the four
entries below already held #eeeeee.

#e8e8e8 is the ground BRAND_DARK_GOLD_DEEP is calibrated against, and rev 24
registered it under its own name for exactly that reason. Putting the hover
plate on it would have pinned every hover in the app to the one value the gold
cannot afford to lose, clearing the 4.5 floor by 0.0334. A boundary is not a
plate. This value is a grid step inside it and gold reads 4.7875 on it.
"""

# RNV-LIGHT-WIRING (2026-09-06): the constants below name values the
# palettes already carried as literals. Nothing here is a new colour.
# Registered values take the register's key; ramp greys take their byte.

APP_SURFACE_LIGHT_3: Final[str] = "#f5f5f5"
"""engine/brand.py APP["surface-light-3"]. The light window and panel
ground -- what a dialog sits on in light mode.

RNV-LIGHT-WIRING (2026-09-06): this value was written out as a literal
in every palette that used it, so nothing could move it. Registered by
rev 27 as the third rung of the light surface ladder; named here under
the register's key, the way APP_PANEL_HOVER and APP_HOVER_LIGHT are.
Every key that carries it is a surface, so it is not split."""

APP_SURFACE_LIGHT_2: Final[str] = "#fbfbfb"
"""engine/brand.py APP["surface-light-2"]. One rung above the panel ground.

RNV-LIGHT-WIRING (2026-09-06): new to this application. It arrives
because two strays collapse onto it -- #f8f8f8 and #fafafa, which sat
0.60 and 0.20 CIEDE2000 from this rung and on no ladder at all. Same
ruling as #252525 onto the card: a value a fraction of a step from a
registered one is that one, misspelled."""

APP_PRESSED_LIGHT: Final[str] = "#e0e0e0"
"""engine/brand.py APP["pressed-light"]. The light PRESSED plate -- an
interaction state, which is why this name goes only on `pressed_bg`.

RNV-LIGHT-WIRING (2026-09-06): SPLIT, NOT RENAMED. Other keys hold
#e0e0e0 as a static surface (a tab, a scrollbar track) and keep the
ramp-step name GREY_E0 below. Wiring a resting ground to a pressed
state would claim a role for it on the strength of a shared hex --
the same ruling rnv-text-transformer made for GREY_EE / APP_HOVER_LIGHT."""

GREY_E0: Final[str] = "#e0e0e0"
"""grey(14) on the ramp, #e0e0e0. Static surfaces that share a hex with
APP_PRESSED_LIGHT without being a pressed state. See the split note
there. Named by its byte, like every other ramp step."""

GREY_EE: Final[str] = "#eeeeee"
"""grey(14) on the ramp, #eeeeee. Static surfaces that share a hex with
APP_HOVER_LIGHT without being a hover: a list header, a scroll ground.
Same split rnv-text-transformer ruled for its diff headers."""

GREY_DD: Final[str] = "#dddddd"
"""grey(13) on the ramp, #dddddd. Edges and grid lines that share a hex
with APP_TEXT without being text. The register's APP["text"] is ink;
a gridline is not, and moving the ink should not move the grid."""

GREY_66: Final[str] = "#666666"
"""grey(6) on the ramp, #666666. Secondary and muted text on light."""

GREY_88: Final[str] = "#888888"
"""grey(8) on the ramp, #888888. Muted text on dark, a scrollbar handle
hover on light."""

GREY_55: Final[str] = "#555555"
"""grey(5) on the ramp, #555555. Disabled text and a checkbox edge on dark."""

# RNV-LIGHT-WIRING (2026-09-06): moved up from below the
# palettes, unchanged. It now has palette callers, and a
# name defined after its use is a NameError at import.
# ── Neutral edges ──
# RNV-INK-RULE (2026-09-02). Named for the colour, not the job.
#
# GREY_44 was the swatch-preview outline, held under two role names at once:
# the same value written twice, once in full and once in three digits, which
# is how it stayed invisible to a census that reads six. Only the short form
# was ever used.
#
# GREY_CC is the light edge swatch_edge() reaches for on a dark ground. It
# was three digits too, and equally invisible.
GREY_44: Final[str] = "#444444"
GREY_CC: Final[str] = "#cccccc"



IMAGE_CANVAS_LIGHT: Final[str] = "#e8e8e8"
"""APP-OWNED. The image viewer's ground in light mode.

A COINCIDENCE, NOT A MIRROR, and the distinction is the whole reason this
constant exists rather than the literal that was here before. rnv-brand rev 24
registered #e8e8e8 as GOLD_TEXT_GROUND_FLOOR -- the darkest light ground on
which the gold family carries text, and the value BRAND_DARK_GOLD_DEEP is
derived against.

This is not that role. It is the empty canvas behind a loaded image in
RNV_Color_Picker.py: a QGraphicsView background brush with the user's own
image drawn on it. No gold, no error red, no text of any kind is ever drawn on
it. It shares a hex with the floor and shares nothing else.

SO IT MUST NOT FOLLOW. If the register ever moves GOLD_TEXT_GROUND_FLOOR, this
value stays where it is, and tests/test_ladder_and_plate.py asserts the
coincidence in both directions so that neither the sharing nor the separation
can rot silently.
"""

IMAGE_OVERLAY_ALPHA: Final[str] = "ED"
"""The alpha byte image mode composites its chrome at -- 0xED, about 93%.

WHY THE OVERLAYS BELOW ARE WRITTEN OUT RATHER THAN COMPOSED. Qt wants the
eight-digit #AARRGGBB form, and building it from the six-digit constant would
make the palette entries resolve to an expression rather than a value, which
this app's own before/after comparison cannot check. The relationship is
enforced by tests/test_ladder_and_plate.py instead: it asserts that each
overlay's last six digits ARE the register value it claims, and that its alpha
byte is this one. If the register moves a base, those tests fail and these move
with it.

THEY WERE INVISIBLE BEFORE. The 2026-08-29 wiring pass claimed no registered
value was left spelled as a literal in a dark palette. That was true of
six-digit spellings only: its sweep compared whole strings, so #ED000000 never
matched #000000 and four of these sat in IMAGE_MODE_COLORS while the test
reported clean. The sweep now normalises both lengths.
"""

APP_WINDOW_OVERLAY: Final[str] = "#ED000000"
"""TRUE_BLACK, and APP["window"], at IMAGE_OVERLAY_ALPHA."""

APP_CANVAS_OVERLAY: Final[str] = "#ED0A0A0A"
"""APP_CANVAS, and APP["canvas"], at IMAGE_OVERLAY_ALPHA."""

APP_PANEL_OVERLAY: Final[str] = "#ED1A1A1A"
"""BRAND_BLACK, and APP["panel"], at IMAGE_OVERLAY_ALPHA."""
APP_PROVENANCE: Final[dict[str, str]] = {
    "TRUE_BLACK": "register",
    "WHITE": "register",
    "BRAND_BLACK": "register",
    "APP_CARD": "register",
    "APP_BORDER": "register",
    "APP_TEXT": "register",
    "APP_TEXT_DIM": "register",
    "APP_CANVAS": "register",
    "APP_PANEL_HOVER": "register",
    "APP_HOVER_LIGHT": "register",
    "APP_WINDOW_OVERLAY": "register-overlay",
    "APP_CANVAS_OVERLAY": "register-overlay",
    "APP_PANEL_OVERLAY": "register-overlay",
    "IMAGE_CANVAS_LIGHT": "app-canvas",
    "APP_SURFACE_LIGHT_3": "register",
    "APP_SURFACE_LIGHT_2": "register",
    "APP_PRESSED_LIGHT": "register",
    "GREY_E0": "app-ramp",
    "GREY_EE": "app-ramp",
    "GREY_DD": "app-ramp",
    "GREY_66": "app-ramp",
    "GREY_88": "app-ramp",
    "GREY_55": "app-ramp",
}
"""Declarative, and read by tests/test_app_mirror.py. A classification that
lives only in a test drifts from the thing it classifies."""

# ============================================================================
# THE STATUS FAMILY
# ============================================================================
#
# RNV-STATUS-FAMILY (2026-09-03). The register replaced Bootstrap's three
# values outright. Two measurements made keeping them indefensible: the amber
# read 1.63 on #ffffff and 1.49 on #f5f5f5 against a 3:1 fill floor, and
# success and error sat about 4 apart under deuteranopia -- one olive, and
# they are the two most consequential colours in any interface. The RNV family
# leaves the red-green axis entirely.
#
# The shape this block already described for the red now holds for all three:
# one registered FILL per role, and separate TEXT values per ground, because
# the fill and text jobs occupy non-overlapping luminance bands. A value that
# clears 3:1 on a dark AND a light ground sits at L* 48-59 by arithmetic, and
# a mid-tone reaches 4.5:1 on neither side. That is why there are five values
# here rather than three.
#
# The Material red this family retired is deliberately not written here,
# because test_one_status_family_only forbids it appearing in this file at
# all.

STATUS_SUCCESS: Final[str] = "#926c89"
"""Registered. Fills, badges, and the ground that black is drawn on.

Black on it reads 4.73, so STATUS_SUCCESS_FG stays #000000.

WAS #28a745, written out four times in this file with no constant between the
value and its uses -- twice in the palettes, once as STATUS_SUCCESS_BG and
once as STATUS_ACTIVE_COLOR. Named here so it has one home."""

STATUS_WARNING: Final[str] = "#a2703c"
"""Registered. WAS #ffc107, retired on arithmetic rather than taste: it read
1.63 on #ffffff and 1.49 on #f5f5f5, so it could not legally carry a boundary
on a light ground at all.

It reads as gold-adjacent because it half IS one -- the register derives it
50% toward BRAND_DARK_GOLD in OKLab, landing 9.1 CIEDE2000 away, which clears
the register's own 8.40 "clearly different" threshold by 0.7."""

STATUS_SUCCESS_TEXT: Final[str] = "#ad85a3"
"""Registered. Success TEXT on a dark panel: 5.52 on #1a1a1a, 4.55 on #2a2a2a.

Here for STATUS_ACTIVE_COLOR below, which is painted with `color:` and cannot
take the fill. The register ruled on 2026-09-04 that an active label aliases
success-text rather than success, after finding the same alias in
rnv-icon-builder about to fail on adoption day."""

STATUS_SUCCESS_TEXT_LIGHT: Final[str] = "#825d79"
"""Registered. The same text on a light panel: 4.52 on #f5f5f5.

Carried so the light sibling exists before it is needed. Every value the
register has published this month has needed one, and adding it later is how
an asymmetry gets built in -- which is exactly what Bootstrap's missing light
variants cost this fleet.

RNV-STATUS-LIGHT-FLOOR closed at rev 31: re-walked against #e8e8e8, where
it now reads 4.52. See STATUS_ERROR_TEXT_LIGHT below for why that ground
and not #e0e0e0."""

STATUS_ERROR: Final[str] = "#c75b64"
"""Registered. Fills, borders, and the ground that black is drawn on.

Black on it reads 5.11, which passes and is not affected by the text values
below. WAS #dc3545."""

STATUS_ERROR_TEXT: Final[str] = "#dd6f77"
"""Registered. Error TEXT on a dark panel. 5.48 on #1a1a1a, 4.52 on #2a2a2a.

WAS #e56b77, which this file carried as a literal in two palettes. That value
was derived from #dc3545; with the base retired it is an ORPHAN -- a value
derived from something no longer in the palette -- so it moves with its base.
The replacement has slightly LESS headroom on every dark ground -- 4.5210
against 4.5801 on the card -- and is still above the floor.

Named rather than written out, so the two palettes that carry it move
together. They previously held it as a bare literal in two places."""

STATUS_ERROR_TEXT_LIGHT: Final[str] = "#ae4650"
"""Registered. The same text on a light panel. 4.51 on #f5f5f5, where the
undarkened fill reads 3.77.

WAS STATUS_ERROR_LIGHT, and was lighten(STATUS_ERROR, -20). RENAMED because
the register records that this one colour was derived independently under TWO
identifiers across three applications, and names it error-text-light -- which
is also the more accurate name here: it is not "the light error", it is the
error TEXT for a light ground.

WRITTEN DOWN rather than derived, and that is a change. The formula no longer
produces the registered value: against the new base it yields #b44753, which
is neither the old #c82131 nor #ae4650. The register's family rule is a
different one -- hold hue and chroma, move lightness only, take the first step
clearing 4.5 on the worst ground -- and it publishes the RESULT with the walk
as provenance, so retuning the rule cannot silently change what an error looks
like in five applications. Same call the register made for
BRAND_STANDBY_GOLD.

RNV-STATUS-LIGHT-FLOOR, CLOSED 2026-09-05 at register rev 31.

These were first walked against #f5f5f5 as "the worst light ground". It was
not the worst: rev 27 had put APP hover-light #eeeeee, GOLD_TEXT_GROUND_FLOOR
#e8e8e8 and pressed-light #e0e0e0 below it, and because the rule takes the
FIRST step that clears, each value stopped at 4.52 with no margin and they
failed one rung down together.

Re-walked against #e8e8e8. THE DECIDING REASON IS NOT THE SIZE OF THE MOVE --
#e0e0e0 was affordable on identical grounds, so cost does not pick between
them. It is that #e8e8e8 is where BRAND_DARK_GOLD_DEEP already stops:

    on #e8e8e8   gold-deep 4.53   these 4.52 / 4.53 / 4.52   pass
    on #e0e0e0   gold-deep 4.21   these 4.20 / 4.20 / 4.20   fail

ONE boundary for every brand text family instead of two. Walking to #e0e0e0
would have covered the pressed plate and left an author having to remember
which family they were in to know where text stops. Below #e8e8e8, no brand
text of any family.

This value reads 4.52 on #e8e8e8 and 5.08 on #f5f5f5, so it reaches the
coverage boundary its predecessor #c82131 did -- which the intermediate
#ae4650 did not, at 4.0150."""


# ============================================================================
# DARK THEME COLORS
# ============================================================================

DARK_THEME_COLORS: Final[dict[str, str | int]] = {
    # Error message text. Theme-aware because no single red clears both
    # grounds: this value reads 5.48 on #1a1a1a and 2.91 on #f5f5f5.
    # RNV-STATUS-FAMILY: was the literal #e56b77, an orphan of the
    # retired #dc3545. Named now, so this palette and image mode
    # cannot drift apart. See the STATUS FAMILY block above.
    'status_error_text': STATUS_ERROR_TEXT,
    'name': 'Dark',
    
    # ── Base surfaces ──
    'window_bg':          TRUE_BLACK,
    'panel_bg':           BRAND_BLACK,
    'card_bg':            APP_CARD,
    'bg_secondary':       APP_CARD,   # alias for card_bg
    'input_bg':           BRAND_BLACK,
    'hover_bg':           APP_PANEL_HOVER,
    'pressed_bg':         APP_BORDER,
    'selected_bg':        BRAND_GOLD,
    
    # ── Text ──
    'text_primary':       APP_TEXT,
    # NOT CONSUMED. Nothing reads this key -- 'text_muted' below carries the
    # same value and does the job in six places. Kept, and kept correct, so
    # wiring it up is a one-line change rather than a colour decision.
    'text_secondary':     GREY_88,
    'text_muted':         GREY_88,
    'text_disabled':      GREY_55,
    'text_accent':        BRAND_GOLD,
    'text_on_accent':     TRUE_BLACK,
    
    # ── Borders ──
    'border_default':     APP_BORDER,
    'border_focus':       BRAND_GOLD,
    'border_hover':       GREY_44,
    'border_accent':      BRAND_GOLD,
    'input_border':       APP_BORDER,
    
    # ── Dialog buttons (gold accent system) ──
    'dialog_btn_bg':          APP_CARD,
    'dialog_btn_text':        APP_TEXT,
    'dialog_btn_hover_bg':    APP_PANEL_HOVER,
    'dialog_btn_hover_text':  BRAND_GOLD,
    'dialog_btn_hover_border': BRAND_GOLD,
    'dialog_btn_pressed_bg':  BRAND_GOLD,
    'dialog_btn_pressed_text': TRUE_BLACK,
    'dialog_btn_border':      APP_BORDER,
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          BRAND_BLACK,
    'main_btn_text':        APP_TEXT,
    'main_btn_border':      APP_BORDER,
    'main_btn_hover_bg':    APP_BORDER,
    'main_btn_hover_text':  APP_TEXT,
    'main_btn_pressed_bg':  GREY_44,
    'main_btn_pressed_text': TRUE_BLACK,
    
    # ── Checkbox ──
    'checkbox_bg':            BRAND_BLACK,
    'checkbox_border':        GREY_55,
    'checkbox_checked_bg':    BRAND_GOLD,
    'checkbox_checked_border': BRAND_GOLD,
    'checkbox_hover_border':  BRAND_GOLD,
    
    # ── Tabs ──
    'tab_bg':             APP_CARD,
    'tab_selected_bg':    BRAND_BLACK,
    'tab_hover_bg':       APP_BORDER,
    'tab_border':         APP_BORDER,
    'tab_indicator':      BRAND_GOLD,
    'tab_selected_text':  BRAND_GOLD,
    'tab_hover_text':     BRAND_GOLD,
    
    # ── Scrollbars ──
    # RNV-COLLAPSE-252525 (2026-09-02): was #252525, a value a third of
    # the way from panel to card and on neither ladder nor grid. Ruled
    # onto the card rung. Image mode inherits this through the splat.
    'scrollbar_bg':            APP_CARD,
    'scrollbar_handle':        GREY_44,
    'scrollbar_handle_hover':  GREY_66,
    'scrollbar_border':        APP_BORDER,
    
    # ── List / Table ──
    'list_bg':            APP_CARD,   # was #252525, see scrollbar_bg
    'list_alt_bg':        BRAND_BLACK,
    'list_selected_bg':   BRAND_GOLD,
    'list_selected_text': TRUE_BLACK,
    'list_hover_bg':      APP_PANEL_HOVER,
    'list_hover_text':    BRAND_GOLD,
    'list_header_bg':     APP_CARD,
    'list_grid':          APP_BORDER,
    
    # ── Dialog / status ──
    'dialog_bg':          BRAND_BLACK,
    'dialog_border':      APP_BORDER,
    
    # ── Tooltip ──
    'tooltip_bg':         APP_CARD,
    'tooltip_border':     BRAND_GOLD,
    'tooltip_text':       APP_TEXT,
    
    # ── Semantic status ──
    # RNV-STATUS-FAMILY: the fills, now named. All three were
    # bare literals; every hex a palette carries needs a
    # constant, or nothing can move it. These three keys are
    # looked up nowhere in this application and are not wired
    # up by this pass -- if any is ever painted as TEXT it
    # must take a _TEXT value instead, because a fill sits at
    # L* 48-59 and cannot reach 4.5:1 on either ground.
    'success':            STATUS_SUCCESS,
    'warning':            STATUS_WARNING,
    'error':              STATUS_ERROR,
    'info':               BRAND_GOLD,
    
    # ── Picker-specific (unique to this app) ──
    'image_viewer_bg':       APP_CANVAS,
    'scroll_area_bg':        TRUE_BLACK,
    'zoom_label_bg':         BRAND_BLACK,
    'zoom_label_border':     APP_BORDER,
    'swatch_border_width':   2,
    'swatch_border_color':   APP_TEXT,
    'output_text_color':     BRAND_GOLD,
    'text_accent_secondary': BRAND_GOLD,
    
    # ── Gold accent hover/pressed tints (no better semantic name exists) ──
    'accent_hover':       BRAND_GOLD_HOVER,
    'accent_pressed':     BRAND_GOLD_PRESSED,
}


# ============================================================================
# LIGHT THEME COLORS
# ============================================================================

LIGHT_THEME_COLORS: Final[dict[str, str | int]] = {
    # Error message text. 4.5123 on this panel's #f5f5f5, where the
    # undarkened fill reads 3.74. RNV-STATUS-FAMILY: renamed from
    # STATUS_ERROR_LIGHT, and no longer computed -- the old formula
    # against the new base gives #b44753, a third answer.
    'status_error_text': STATUS_ERROR_TEXT_LIGHT,
    'name': 'Light',
    
    # ── Base surfaces ──
    'window_bg':          APP_SURFACE_LIGHT_3,
    'panel_bg':           APP_SURFACE_LIGHT_3,
    'card_bg':            WHITE,
    'bg_secondary':       WHITE,
    'input_bg':           WHITE,
    'hover_bg':           APP_HOVER_LIGHT,
    'pressed_bg':         APP_PRESSED_LIGHT,
    'selected_bg':        BRAND_DARK_GOLD,
    
    # ── Text ──
    'text_primary':       TRUE_BLACK,
    # NOT CONSUMED -- see the note in the dark palette.
    'text_secondary':     GREY_66,
    'text_muted':         GREY_66,
    'text_disabled':      APP_TEXT_DIM,
    'text_accent':        BRAND_DARK_GOLD_DEEP,
    'text_on_accent':     WHITE,
    
    # ── Borders ──
    'border_default':     GREY_CC,
    'border_focus':       BRAND_DARK_GOLD,
    'border_hover':       APP_TEXT_DIM,
    'border_accent':      BRAND_DARK_GOLD,
    'input_border':       GREY_CC,
    
    # ── Dialog buttons (gold accent system) ──
    'dialog_btn_bg':          WHITE,
    'dialog_btn_text':        TRUE_BLACK,
    'dialog_btn_hover_bg':    APP_HOVER_LIGHT,
    'dialog_btn_hover_text':  BRAND_DARK_GOLD_DEEP,
    'dialog_btn_hover_border': BRAND_DARK_GOLD,
    'dialog_btn_pressed_bg':  BRAND_DARK_GOLD,
    'dialog_btn_pressed_text': WHITE,
    'dialog_btn_border':      GREY_CC,
    
    # ── Main window buttons (inverse system: dark hover, darker gray pressed, no gold) ──
    'main_btn_bg':          WHITE,
    'main_btn_text':        TRUE_BLACK,
    'main_btn_border':      GREY_CC,
    'main_btn_hover_bg':    APP_BORDER,
    'main_btn_hover_text':  TRUE_BLACK,
    'main_btn_pressed_bg':  GREY_44,
    'main_btn_pressed_text': WHITE,
    
    # ── Checkbox ──
    'checkbox_bg':            WHITE,
    'checkbox_border':        APP_TEXT_DIM,
    'checkbox_checked_bg':    BRAND_DARK_GOLD,
    'checkbox_checked_border': BRAND_DARK_GOLD,
    'checkbox_hover_border':  BRAND_DARK_GOLD,
    
    # ── Tabs ──
    'tab_bg':             GREY_E0,
    'tab_selected_bg':    WHITE,
    'tab_hover_bg':       APP_HOVER_LIGHT,
    'tab_border':         GREY_CC,
    'tab_indicator':      BRAND_DARK_GOLD,
    'tab_selected_text':  BRAND_DARK_GOLD_DEEP,
    'tab_hover_text':     BRAND_DARK_GOLD_DEEP,
    
    # ── Scrollbars ──
    'scrollbar_bg':            GREY_E0,
    'scrollbar_handle':        APP_TEXT_DIM,
    'scrollbar_handle_hover':  GREY_88,
    'scrollbar_border':        GREY_CC,
    
    # ── List / Table ──
    'list_bg':            WHITE,
    'list_alt_bg':        APP_SURFACE_LIGHT_2,   # was #f8f8f8, collapsed onto #fbfbfb
    'list_selected_bg':   BRAND_DARK_GOLD,
    'list_selected_text': WHITE,
    'list_hover_bg':      APP_HOVER_LIGHT,
    'list_hover_text':    BRAND_DARK_GOLD_DEEP,
    'list_header_bg':     GREY_EE,   # was #f0f0f0, collapsed onto #eeeeee
    'list_grid':          GREY_DD,
    
    # ── Dialog / status ──
    'dialog_bg':          APP_SURFACE_LIGHT_3,
    'dialog_border':      GREY_CC,
    
    # ── Tooltip ──
    'tooltip_bg':         WHITE,
    'tooltip_border':     BRAND_DARK_GOLD,
    'tooltip_text':       TRUE_BLACK,
    
    # ── Semantic status ──
    # RNV-STATUS-FAMILY: the fills, now named. All three were
    # bare literals; every hex a palette carries needs a
    # constant, or nothing can move it. These three keys are
    # looked up nowhere in this application and are not wired
    # up by this pass -- if any is ever painted as TEXT it
    # must take a _TEXT value instead, because a fill sits at
    # L* 48-59 and cannot reach 4.5:1 on either ground.
    'success':            STATUS_SUCCESS,
    'warning':            STATUS_WARNING,
    'error':              STATUS_ERROR,
    'info':               BRAND_DARK_GOLD,
    
    # ── Picker-specific ──
    'image_viewer_bg':       IMAGE_CANVAS_LIGHT,
    'scroll_area_bg':        WHITE,
    'zoom_label_bg':         WHITE,
    'zoom_label_border':     TRUE_BLACK,
    'swatch_border_width':   2,
    'swatch_border_color':   TRUE_BLACK,
    'output_text_color':     BRAND_DARK_GOLD,
    'text_accent_secondary': BRAND_DARK_GOLD,
    
    # ── Gold accent hover/pressed tints (no better semantic name exists) ──
    'accent_hover':       BRAND_DARK_GOLD_HOVER,
    'accent_pressed':     BRAND_DARK_GOLD_PRESSED,
}


# ============================================================================
# IMAGE MODE COLORS (Dark theme with overlay transparency)
# ============================================================================

# Image mode shares dark palette for most keys, with a few picker-specific
# overrides for the transparent overlay look.
IMAGE_MODE_COLORS: Final[dict[str, str | int]] = {
    **DARK_THEME_COLORS,
    # Error message text. Image mode inherits dark's value; the entry sits
    # AFTER the splat because a key listed before it is silently discarded.
    # RNV-STATUS-FAMILY: named rather than written out, so this and
    # dark move together. They held the same literal twice.
    'status_error_text': STATUS_ERROR_TEXT,
    'name': 'Image',
    # ── Picker-specific overrides for image mode ──
    'window_bg':          APP_WINDOW_OVERLAY,
    'image_viewer_bg':    APP_CANVAS_OVERLAY,
    'scroll_area_bg':     APP_WINDOW_OVERLAY,
    'zoom_label_bg':      APP_PANEL_OVERLAY,
    'checkbox_bg':        'rgba(0, 0, 0, 100)',
    # ── Scrollbar overrides — translucent grays (no brand gold) ──
    'scrollbar_bg':            'rgba(51, 51, 51, 100)',
    'scrollbar_handle':        'rgba(80, 80, 80, 150)',
    'scrollbar_handle_hover':  'rgba(100, 100, 100, 200)',
    'scrollbar_border':        'transparent',
}


# ============================================================================
# STANDALONE COLOR CONSTANTS (Fixed — NOT theme-aware)
# ============================================================================
# These colors are intentionally fixed across all themes. Separated from
# the theme dicts so a developer immediately knows:
# "this color is deliberately hardcoded — do not try to theme it."

# ── WCAG Contrast demo swatches ──
# These represent the actual black/white reference pair the user is testing
# contrast against. They must stay black and white regardless of the active
# theme or the demo loses its meaning.
CONTRAST_DEMO_BLACK_BG: Final[str] = "#000000"
CONTRAST_DEMO_WHITE_BG: Final[str] = "#ffffff"
CONTRAST_DEMO_BLACK_FG: Final[str] = "#000000"
CONTRAST_DEMO_WHITE_FG: Final[str] = "#ffffff"

# ── Which ink goes on this ground ──
#
# RNV-INK-RULE (2026-09-02, ruled by Chris). Four places in the fleet asked
# this question and gave three different answers, none of them a contrast
# measurement:
#
#     core/palette_formats.py   sum(color) / 3 < 128
#     ui/settings_dialog.py     (r + g + b) / 3 > 128     (icon-builder)
#     ui/preview_utils.py       ITU-R 601 luma > 128      (icon-builder)
#     core/accessibility.py     relative luminance < 0.179   -- correct, unused
#
# The mean and the 601 luma disagree with each other on saturated colour,
# because 601 weights green 587/1000 where the mean weights it 333. On pure
# green the mean puts white on it at 1.37:1 where the right answer is black
# at 15.30:1.
#
# So: one rule, stated once, as a real comparison rather than a threshold --
# whichever candidate has the higher contrast ratio against the ground wins.
# A threshold would need re-deriving for every pair; a ratio does not, which
# is what lets swatch_edge() share the rule with contrast_ink().
#
# This is the same maths as the surface ladder and the 4.5 floor.


def _channel(value: float) -> float:
    """One sRGB channel, 0-255, linearised."""
    c = value / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(color: "str | tuple[int, int, int]") -> tuple[int, int, int]:
    """Accept either shape. Callers hold hex strings and RGB triples both."""
    if isinstance(color, str):
        h = color.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return (int(color[0]), int(color[1]), int(color[2]))


def relative_luminance(color: "str | tuple[int, int, int]") -> float:
    """WCAG 2.x relative luminance, 0.0 (black) to 1.0 (white)."""
    r, g, b = _rgb(color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: "str | tuple[int, int, int]",
                   b: "str | tuple[int, int, int]") -> float:
    """WCAG contrast ratio between two colours, 1.0 to 21.0."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def better_on(background: "str | tuple[int, int, int]", *candidates: str) -> str:
    """Whichever candidate reads best on this ground. Ties go to the first."""
    return max(candidates, key=lambda c: contrast_ratio(background, c))


def contrast_ink(background: "str | tuple[int, int, int]") -> str:
    """Text colour for an arbitrary ground: WHITE or TRUE_BLACK.

    For a colour the USER chose -- a swatch, an exported palette entry. Not
    for brand surfaces: what sits on a brand gold is a ruling, not a
    measurement, and the two are only 0.08 apart on BRAND_DARK_GOLD.
    """
    return better_on(background, TRUE_BLACK, WHITE)


def prefers_dark_ink(background: "str | tuple[int, int, int]") -> bool:
    """True when TRUE_BLACK reads better on this ground than WHITE does.

    The shape the old call sites wanted: they all read
    `X if brightness > 128 else Y`, so this drops straight into the
    condition and leaves the two branches alone.
    """
    return contrast_ink(background) == TRUE_BLACK


def contrast_ink_rgb(background: "str | tuple[int, int, int]") -> tuple[int, int, int]:
    """The same answer as an RGB triple, for the QColor and Pillow callers."""
    return (0, 0, 0) if prefers_dark_ink(background) else (255, 255, 255)


def swatch_edge(background: "str | tuple[int, int, int]") -> str:
    """Outline for a swatch of an arbitrary colour: GREY_CC or APP_BORDER."""
    return better_on(background, APP_BORDER, GREY_CC)

# ── Debug overlay ──
# High-visibility terminal green on semi-transparent black. Used by the
# floating debug dimension label during development. Must be readable on
# any window contents regardless of theme.
DEBUG_TEXT: Final[str] = "#00ff00"
DEBUG_BG: Final[str] = "rgba(0, 0, 0, 200)"

# ── Status / feedback colors (universal semantic meaning) ──
# RNV-STATUS-FAMILY: these are ROLE names over the colour constants
# above, which is what STATUS_ERROR_BG already was. The other two
# held their own copies of the green, so one colour lived at four
# addresses in this file and none of them named it.
#
# The _FG values stay #000000: black reads 4.73 on the new success
# fill and 5.11 on the new error fill, both above the 4.5 floor
# test_status_badge_text_clears_its_fill asserts. White would fail
# on both, at 4.44 and 4.11.
STATUS_SUCCESS_BG: Final[str] = STATUS_SUCCESS
STATUS_SUCCESS_FG: Final[str] = "#000000"
STATUS_ERROR_BG:   Final[str] = STATUS_ERROR
STATUS_ERROR_FG:   Final[str] = "#000000"
# Unreferenced outside this file. Kept as an alias rather than
# deleted -- rnv-icon-builder holds the same name for the folder
# watcher, and the register still has no name for `running` as
# distinct from `succeeded`; it recorded on 2026-09-04 that the
# trigger for registering one is a SECOND consumer, not a date.
#
# IT ALIASES success-text, NOT success. Ruled by the register the
# same day, after the identically-named constant in icon-builder --
# which IS painted, with `color:` -- turned out to be about to fail
# the 4.5 text floor on adoption day. Bootstrap's green read 5.55 on
# BRAND_BLACK and doubled as text by accident; the RNV fills are
# mid-tones by design and #926c89 reads 3.91 there. Nothing paints
# this one today, and that is the reason to get it right now rather
# than the reason not to: it is what the next reader will copy.
STATUS_ACTIVE_COLOR: Final[str] = STATUS_SUCCESS_TEXT


# ── Semi-transparent black overlays (fixed visual effects) ──
# Alpha-channel overlays used to dim UI surfaces in specific contexts.
# The alpha values are intentional and theme-independent — they create
# consistent dim levels regardless of what's beneath them.
# Stored as RGBA tuples so callers can do `QColor(*OVERLAY_BLACK_MEDIUM)`
# or `QColorCache.get(OVERLAY_BLACK_MEDIUM)` without any string parsing.
OVERLAY_BLACK_LIGHT:  Final[tuple[int, int, int, int]] = (0, 0, 0, 50)
"""Light dim overlay (alpha 50/255) — magnifier outer-area shading."""

OVERLAY_BLACK_MEDIUM: Final[tuple[int, int, int, int]] = (0, 0, 0, 75)
"""Medium dim overlay (alpha 75/255) — transparent scroll widget background."""

OVERLAY_BLACK_HEAVY:  Final[tuple[int, int, int, int]] = (0, 0, 0, 180)
"""Heavy dim overlay (alpha 180/255) — magnifier crosshair shadow."""

# ── SVG palette export (printable artifact) ──
# Fixed paper-white background and ink-black stroke for the SVG export
# format. Theme-independent because exported SVGs need to look the same
# regardless of which theme was active at export time.
SVG_EXPORT_BG:     Final[str] = "#ffffff"
"""Background fill for SVG palette export (paper white)."""

SVG_EXPORT_STROKE: Final[str] = "#000000"
"""Stroke color for SVG palette export swatch borders (ink black)."""

# ── Missing-data placeholder ──
# Default value used when a color history dict entry is missing its 'hex'
# field. Black is a deliberately wrong-looking sentinel so missing data is
# visually obvious in the UI rather than silently rendering as a real color.
MISSING_HEX_PLACEHOLDER: Final[str] = "#000000"
"""Placeholder hex when a color entry dict lacks its 'hex' key."""


# ============================================================================
# THEME ENTRY FUNCTION
# ============================================================================

def get_theme_colors(theme_name: str = 'dark') -> dict[str, str | int]:
    """
    Get the color palette for the specified theme.
    
    Args:
        theme_name: 'dark', 'light', or 'image'
    
    Returns:
        Dictionary of color definitions for that theme
    """
    match theme_name:
        case 'light':
            return LIGHT_THEME_COLORS
        case 'image':
            return IMAGE_MODE_COLORS
        case _:
            return DARK_THEME_COLORS


# ============================================================================
# THEME MANAGER
# ============================================================================

class ThemeManager:
    """
    Manages application theme state (Dark / Light / Image) at runtime.
    
    Theme color dicts are module-level constants in this file. This class
    handles theme switching, image-mode detection, and provides the active
    theme dict via get_current_theme().
    """
    
    def __init__(self):
        self.current_theme = 'dark'
        self.image_mode_available = False
        self.image_mode_active = False
        self.background_pixmap: QPixmap | None = None
    
    def detect_image_resources(self) -> bool:
        """Check if custom images are available for Image Mode."""
        bg_path = os.path.join(BACKGROUND_IMAGES_DIR, "background.png")
        has_background = False

        if os.path.exists(bg_path):
            try:
                img = Image.open(bg_path)

                max_dimension = MAX_IMAGE_DIMENSION
                if img.width > max_dimension or img.height > max_dimension:
                    ratio = min(max_dimension / img.width, max_dimension / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    if _logger:
                        _logger.info(f"Resized background image to {new_size[0]}x{new_size[1]}")

                buffer = QByteArray()
                bio = io.BytesIO()
                img.save(bio, format="PNG")
                buffer.append(bio.getvalue())

                pixmap = QPixmap()
                pixmap.loadFromData(buffer)

                self.background_pixmap = pixmap
                has_background = True
                if _logger:
                    _logger.success(f"Loaded background image: {img.width}x{img.height}")

            except Exception as e:
                if _logger:
                    _logger.error(f"Failed to load background image: {e}")
        
        button_names = ['upload', 'grab', 'dominant', 'screen', 'save', 'export', 'clear', 'reset']
        button_count = sum(
            1 for name in button_names 
            if os.path.exists(os.path.join(BUTTON_IMAGES_DIR, f"{name}.png")) or
               os.path.exists(os.path.join(BUTTON_IMAGES_DIR, f"{name}_base.png"))
        )
        
        self.image_mode_available = has_background or button_count >= 3
        
        if self.image_mode_available:
            self.image_mode_active = True
            self.current_theme = 'image'
        
        return self.image_mode_available
    
    def cycle_theme(self) -> str:
        """Cycle through available themes."""
        if self.image_mode_available:
            if self.current_theme == 'image':
                self.current_theme = 'dark'
                self.image_mode_active = False
            elif self.current_theme == 'dark':
                self.current_theme = 'light'
            else:
                self.current_theme = 'image'
                self.image_mode_active = True
        else:
            self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        
        return self.current_theme
    
    def get_current_theme(self) -> dict[str, str | int]:
        """Get the active theme's color dict."""
        return get_theme_colors(self.current_theme)
    
    def get_theme_display_name(self) -> str:
        """Get display name for current theme."""
        match self.current_theme:
            case 'dark':
                return "Dark Mode"
            case 'light':
                return "Light Mode"
            case 'image':
                return "Image Mode"
            case _:
                return "Unknown"
    
    def is_image_mode(self) -> bool:
        """Check if currently in image mode."""
        return self.image_mode_active and self.current_theme == 'image'
    
    # ------------------------------------------------------------------------
    # Scrollbar stylesheet builders — generate stylesheets from theme dicts.
    # These are classmethods that accept an optional theme dict; if omitted,
    # they use the class-level defaults for backward compatibility with code
    # that references ThemeManager.SCROLLBAR_DARK as a static string.
    # ------------------------------------------------------------------------
    
    @classmethod
    def _build_scrollbar(cls, theme: dict[str, str | int]) -> str:
        """Build a scrollbar stylesheet from a theme dict."""
        bg          = theme['scrollbar_bg']
        handle      = theme['scrollbar_handle']
        hover       = theme['scrollbar_handle_hover']
        border      = theme.get('scrollbar_border', theme.get('border_default', '#333333'))
        return f"""
            QScrollBar:vertical {{
                background: {bg};
                width: 12px;
                margin: 0px;
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background: {bg};
                height: 12px;
                margin: 0px;
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """


# ============================================================================
# SCROLLBAR STYLESHEETS — Module-level (pre-built for backward compatibility)
# ============================================================================
# These exist as module-level class attributes so existing code references
# like `ThemeManager.SCROLLBAR_DARK` continue to work. They're pre-built
# from the theme dicts so there's still a single source of truth.

ThemeManager.SCROLLBAR_DARK  = ThemeManager._build_scrollbar(DARK_THEME_COLORS)
ThemeManager.SCROLLBAR_LIGHT = ThemeManager._build_scrollbar(LIGHT_THEME_COLORS)

# Image mode scrollbar is special — uses custom transparent overlay look
# (not built from theme dict because these rgba values are image-mode specific)
ThemeManager.SCROLLBAR_IMAGE = """
    QScrollBar:vertical {
        background-color: rgba(51, 51, 51, 100);
        width: 15px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: rgba(80, 80, 80, 150);
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: rgba(100, 100, 100, 200);
    }
    QScrollBar::sub-page:vertical {
        background-color: transparent;
    }
    QScrollBar::add-page:vertical {
        background-color: transparent;
    }
    QScrollBar:horizontal {
        background-color: rgba(51, 51, 51, 100);
        height: 15px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: rgba(80, 80, 80, 150);
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: rgba(100, 100, 100, 200);
    }
    QScrollBar::sub-page:horizontal {
        background-color: transparent;
    }
    QScrollBar::add-page:horizontal {
        background-color: transparent;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        border: none;
        background: none;
    }
"""


# ============================================================================
# PUBLIC API
# ============================================================================

__all__: list[str] = [
    # Brand colors
    'BRAND_GOLD',
    'BRAND_DARK_GOLD',
    'BRAND_GOLD_RGB',
    'BRAND_DARK_GOLD_RGB',
    'BRAND_GOLD_HOVER',
    'BRAND_GOLD_PRESSED',
    'BRAND_DARK_GOLD_HOVER',
    'BRAND_DARK_GOLD_PRESSED',
    # Theme dicts + entry function
    'DARK_THEME_COLORS',
    'LIGHT_THEME_COLORS',
    'IMAGE_MODE_COLORS',
    'get_theme_colors',
    # Standalone constants
    'GREY_44',
    'GREY_CC',
    'relative_luminance',
    'contrast_ratio',
    'better_on',
    'contrast_ink',
    'contrast_ink_rgb',
    'prefers_dark_ink',
    'swatch_edge',
    'CONTRAST_DEMO_BLACK_BG',
    'CONTRAST_DEMO_WHITE_BG',
    'CONTRAST_DEMO_BLACK_FG',
    'CONTRAST_DEMO_WHITE_FG',
    'DEBUG_TEXT',
    'DEBUG_BG',
    'STATUS_SUCCESS_BG',
    'STATUS_SUCCESS_FG',
    'STATUS_ERROR',
    'STATUS_ERROR_LIGHT',
    'STATUS_ERROR_BG',
    'STATUS_ERROR_FG',
    'STATUS_ACTIVE_COLOR',
    'OVERLAY_BLACK_LIGHT',
    'OVERLAY_BLACK_MEDIUM',
    'OVERLAY_BLACK_HEAVY',
    'SVG_EXPORT_BG',
    'SVG_EXPORT_STROKE',
    'MISSING_HEX_PLACEHOLDER',
    # Classes
    'ThemeManager',
    # App constants
    'APP_NAME', 'APP_VERSION', 'APP_AUTHOR', 'APP_TAGLINE',
    'MAX_COLORS', 'DEFAULT_WEIGHT',
    'BUTTON_HEIGHT_MIN', 'BUTTON_HEIGHT_MAX',
    'WINDOW_WIDTH_MIN', 'WINDOW_WIDTH_MAX', 'SWATCH_SIZE',
    'MAX_IMAGE_DIMENSION',
    # Paths
    'BASE_DIR', 'RESOURCES_DIR', 'BUTTON_IMAGES_DIR',
    'BACKGROUND_IMAGES_DIR', 'FONTS_DIR', 'ICONS_DIR',
]

# RNV-GOLD-GUARD (2026-09-07): the values below are swept by
# tests/test_gold_as_text.py, which resolves every QSS f-string in this
# repository through these palettes and measures the gold family as text
# and as a fill. A gold that reads correctly here can still be drawn on
# the wrong ground three files away, and that is what it is for.
