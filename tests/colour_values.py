"""Every colour value the tests need that is not one of the application's own.

RNV-COLOUR-SYNC (#53 A), 2026-10-17. The application's colours, brand and its
own, are named in utils/config.py and a test reads them from there. Every
other colour value a test or the root suite writes is named here, once, with
why, grouped by kind. tests/test_colour_values.py holds this file: no colour
value is written anywhere else, each name says what kind it is and why, each
is used, and each REGISTER_ value is the brand's at the pin.

RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN
    test_brand_contrast's status sweep skips files carrying this, and this file
    names the retired Material and Bootstrap values in order to forbid them.
RNV-COLLAPSE-GUARD
    test_collapse_252525's sweep skips files carrying this, and this file names
    the collapsed RETIRED_GREY_25, the guard's OLD_HEX.
"""

# ---------------------------------------------------------------------------
# Examples: samples given to a helper or to the colour maths
# ---------------------------------------------------------------------------

EXAMPLE_BLACK = "#000000"
"""Pure black handed to or returned by a conversion, contrast or clamp helper."""

EXAMPLE_WHITE = "#ffffff"
"""Pure white handed to or returned by a conversion, contrast or clamp helper."""

EXAMPLE_PURE_RED = "#ff0000"
"""(255, 0, 0) as rgb_to_hex writes it, and a hex any colour cache can parse."""

EXAMPLE_PURE_RED_UPPER = "#FF0000"
"""The same red in upper case: hex_to_rgb must read either case."""

EXAMPLE_PURE_RED_SHORT = "#f00"
"""The same red in three digits: hex_to_rgb must expand the shorthand."""

EXAMPLE_LIGHT_STEEL_SHORT = "#abc"
"""A three-digit hex that expands digit by digit, to (0xaa, 0xbb, 0xcc)."""

EXAMPLE_PURE_GREEN = "#00ff00"
"""Pure green for the ink rule: a light ground the channel mean called dark."""

EXAMPLE_PURE_GREEN_SHORT = "#0f0"
"""The same green in three digits: the ink rule takes either length."""

EXAMPLE_MID_GREY = "#777777"
"""A grey measured against itself, which must give 1:1."""

EXAMPLE_GOLD = "#d2bc93"
"""A gold sample whose channels, (210, 188, 147), the same test writes as a
tuple. It equals BRAND_GOLD today and must not follow it: a brand move would
leave the tuple behind."""

EXAMPLE_GOLD_RGB = "rgb(210, 188, 147)"
"""The gold sample as a swatch copies it in rgb() form."""

EXAMPLE_GOLD_HSL = "hsl(38, 43%, 70%)"
"""The gold sample as a swatch copies it in hsl() form, from its hsl (38, 43, 70)."""

EXAMPLE_DARK_GOLD = "#8c7337"
"""A sample for lighten()'s uniform per-channel shift: every channel is at least
14, so a -14 step does not clamp. It equals BRAND_DARK_GOLD today and must not
follow it."""

EXAMPLE_CHARCOAL = "#1a1a1a"
"""A base for translucent(). It equals BRAND_BLACK today; the composed value the
test expects is written out, so the base must not follow the brand."""

EXAMPLE_CHARCOAL_AT_ED = "#ed1a1a1a"
"""translucent(EXAMPLE_CHARCOAL, 0xED): eight digits, alpha first, lower case."""

EXAMPLE_NEAR_BLACK_BARE_UPPER = "0A0A0A"
"""A base for translucent() with no hash and in upper case, both of which it accepts."""

EXAMPLE_NEAR_BLACK_AT_ED = "#ed0a0a0a"
"""translucent(EXAMPLE_NEAR_BLACK_BARE_UPPER, 0xED), which comes back lower case."""

EXAMPLE_GREY_44 = "#444444"
"""What the integer sweep reads from its probe's QColor(68, 68, 68)."""

EXAMPLE_CLEAR_RGBA = "rgba(0, 0, 0, 0)"
"""Black at alpha 0: clear, not a colour, which the named-and-used sweep must not
report."""

EXAMPLE_PALE_PINK = "#ffcccc"
"""The hex in the named-and-used sweep's probe line, which the sweep must report."""

EXAMPLE_WHITE_RGBA_230 = "rgba(255, 255, 255, 230)"
"""The rgba() in the same probe, which the sweep must report as written."""

EXAMPLE_CACHE_REPEAT_KEY = "#deadbe"
"""A hex fetched from QColorCache twice, to show the second fetch is the same object."""

EXAMPLE_CACHE_FILL_KEY = "#abc123"
"""A hex fetched from QColorCache only to fill it before clear()."""

EXAMPLE_SIMULATED_SENTINEL_RGB = "rgb(42, 84, 168)"
"""What a monkeypatched simulate_colorblindness returns, (42, 84, 168), as the
blindness swatch's stylesheet spells it."""

EXAMPLE_OLD_RULE_ERROR_TEXT_LIGHT = "#b44753"
"""lighten(STATUS_ERROR, -20) at the base registered on 2026-09-03: what the
retired derivation rule for the light error text gives. Neither
RETIRED_ORPHAN_ERROR_TEXT_LIGHT nor STATUS_ERROR_TEXT_LIGHT, and never drawn."""

EXAMPLE_RENDER_PROBE_MAGENTA = "#ff00ff"
"""What a render set the canvas overlay to, RNV-CANVAS-OVERLAY-GONE (2026-09-26),
to show that no pixel changed."""

EXAMPLE_HAND_EDIT = "#123456"
"""A value tests/test_colours_in_sync.py writes into the colour file's text as a
hand edit, for the sync to put back."""

EXAMPLE_HAND_EDIT_FALLBACK = "#654321"
"""The hand edit to use when the line already holds EXAMPLE_HAND_EDIT."""

EXAMPLE_MOVED_ACCENT = "#6f94bc"
"""Where tests/test_colours_in_sync.py moves the brand's accent to see the move
reach one line. Any value but the accent will do."""

EXAMPLE_MOVED_ACCENT_FALLBACK = "#456c91"
"""The move to use when the accent already is EXAMPLE_MOVED_ACCENT."""

# ---------------------------------------------------------------------------
# Data: what a user, a file or the clipboard supplies, and what the app writes
# back for it
# ---------------------------------------------------------------------------

DATA_RED = "#ff0000"
"""A user's (255, 0, 0) as the app stores and writes it: a history entry, a
collection entry, a swatch, the clipboard, a palette file."""

DATA_RED_UPPER = "#FF0000"
"""The same red in upper case, as a user or a palette file may write it."""

DATA_RED_BARE = "ff0000"
"""The same red without its hash, as a copied palette is searched for it."""

DATA_RED_RGB = "rgb(255, 0, 0)"
"""The same red as copy_rgb_color writes it."""

DATA_RED_HSV = "hsv(0, 100%, 100%)"
"""The same red as hsv() text on the clipboard."""

DATA_RED_HSL = "hsl(0, 100%, 50%)"
"""The same red as hsl() text on the clipboard."""

DATA_GREEN = "#00ff00"
"""A user's (0, 255, 0): a history entry, a palette file's hex field."""

DATA_GREEN_UPPER = "#00FF00"
"""The same green in upper case, alone on a palette file's line."""

DATA_GREEN_BARE = "00ff00"
"""The same green without its hash, searched for in a copied palette."""

DATA_BLUE = "#0000ff"
"""A user's (0, 0, 255) in the history."""

DATA_BLUE_BARE = "0000ff"
"""The same blue without its hash, searched for in a copied palette."""

DATA_BLUE_UPPER = "#0000FF"
"""A user's (0, 0, 255) in upper case, on a palette file's line."""

DATA_BLACK = "#000000"
"""A user's (0, 0, 0): a history entry, the clipboard, text to parse."""

DATA_BLACK_SHORT = "#000"
"""Black in three digits: the label of a history item that has no rgb, and a
.hex palette file's line."""

DATA_BLACK_RGB_COMPACT = "rgb(0,0,0)"
"""Black as rgb() text with no spaces, for the panel's parser."""

DATA_WHITE_SHORT = "#fff"
"""White in three digits, on a .hex palette file's line."""

DATA_WHITE = "#ffffff"
"""A user's (255, 255, 255): a history item, the clipboard."""

DATA_WHITE_UPPER = "#FFFFFF"
"""White in upper case, for the panel's parser."""

DATA_PALE_BLUE = "#abcdef"
"""A user's (171, 205, 239): a history entry, the panel's copied colour."""

DATA_PALE_BLUE_UPPER = "#ABCDEF"
"""The same pale blue in upper case, alone on a .hex file's line."""

DATA_LIGHT_STEEL = "#aabbcc"
"""A user's (170, 187, 204) as an SVG palette file's six-digit fill."""

DATA_LIGHT_STEEL_SHORT = "#abc"
"""The same colour in three digits: an SVG fill the importer skips, and the
start of a palette file's line."""

DATA_GREY_64 = "#646464"
"""A user's (100, 100, 100) in the history."""

DATA_DARK_NAVY = "#0a141e"
"""A user's (10, 20, 30) in the history, and in its export."""

DATA_DARK_NAVY_RGB_COMPACT = "rgb(10,20,30)"
"""The same navy as rgb() text with no spaces, on the clipboard."""

DATA_ORANGE = "#ffa500"
"""A user's (255, 165, 0), CSS orange, as the clipboard holds it. Not a brand
colour."""

DATA_PURPLE = "#800080"
"""A user's (128, 0, 128), CSS purple, copied as a CSS custom property."""

DATA_BROWN_RGB = "rgb(128, 64, 32)"
"""A user's (128, 64, 32) as copy_rgb_color and copy_multiple_formats write it."""

DATA_DARK_ORANGE = "#ff8800"
"""A user's (255, 136, 0): text to parse, and what the panel copies."""

DATA_DARK_ORANGE_UPPER = "#FF8800"
"""The same orange in upper case, for a parser."""

DATA_DARK_ORANGE_PADDED = "  #FF8800  "
"""The same orange with spaces around it, which a parser strips."""

DATA_DARK_ORANGE_BARE_UPPER = "FF8800"
"""The same orange with no hash, upper case, for the panel's parser."""

DATA_DARK_ORANGE_BARE = "ff8800"
"""The same orange with no hash, lower case, for the panel's parser."""

DATA_DARK_ORANGE_RGB = "rgb(255, 136, 0)"
"""The same orange as rgb() text, for the panel's parser."""

DATA_DARK_ORANGE_RGB_UPPER = "RGB(255, 136, 0)"
"""The same rgb() text with the function name in upper case."""

DATA_DEEP_BLUE = "#123456"
"""A user's (0x12, 0x34, 0x56) as the panel copies it."""

DATA_STEEL_BLUE_RGB = "rgb(50, 100, 150)"
"""A user's (50, 100, 150) as rgb() text: in a preview's stylesheet, and pasted."""

DATA_STEEL_BLUE_RGB_SPACED = "rgb( 50 , 100 , 150 )"
"""The same rgb() text with spaces inside, which the panel's parser tolerates."""

DATA_BLUE_VIOLET_RGB = "rgb(100, 50, 200)"
"""A user's (100, 50, 200) as rgb() text on the clipboard."""

DATA_MEDIUM_PURPLE_RGB = "rgb(128, 64, 200)"
"""A user's (128, 64, 200) as rgb() text on the clipboard."""

DATA_OUT_OF_RANGE_RGB = "rgb(300, 400, 500)"
"""rgb() text above 255, which the panel's parser clamps rather than refuses."""

DATA_WINE_RGB = "rgb(123, 45, 67)"
"""A user's (123, 45, 67) in the accessibility foreground preview's stylesheet."""

DATA_TAUPE_RGB = "rgb(99, 88, 77)"
"""A user's (99, 88, 77) in the blindness simulator's preview stylesheet."""

DATA_CERULEAN = "#1e90c8"
"""A user's harmony base (30, 144, 200) as Qt draws it: QColor.name(), lower case."""

DATA_CERULEAN_UPPER = "#1E90C8"
"""The same harmony base as the panel labels it, upper case."""

DATA_ROSE_BARE_UPPER = "FF0080"
"""A harmony colour (255, 0, 128) as its swatch label shows it, without the hash."""

DATA_HISTORY_ABSENT_PINK = "#deadbe"
"""A hex the history does not hold, for a lookup or removal that must miss."""

DATA_HISTORY_ABSENT_PALE_BLUE = "#abcdef"
"""A hex the history does not hold, for a removal that must miss."""

# ---------------------------------------------------------------------------
# Retired: values the application no longer uses, kept so a test can say so
# ---------------------------------------------------------------------------

RETIRED_GREY_25 = "#252525"
"""RNV-COLLAPSE-252525: on neither ladder nor grid, collapsed onto APP_CARD."""

RETIRED_GREY_50 = "#505050"
"""RNV-COLLAPSE-505050: the image scrollbar handle, ruled onto GREY_44."""

RETIRED_SCROLLBAR_HANDLE_RGBA = "rgba(80, 80, 80, 150)"
"""The image scrollbar handle as it was written before RNV-COLLAPSE-505050."""

RETIRED_SCROLLBAR_GROOVE_RGBA = "rgba(51, 51, 51, 100)"
"""The image scrollbar groove as it was written until RNV-DERIVE-ALPHA
(2026-09-25): APP_BORDER at alpha 100, spelled rgba(). It is
translucent(APP_BORDER, SCROLLBAR_BG_ALPHA) now."""

RETIRED_SCROLLBAR_HOVER_RGBA = "rgba(100, 100, 100, 200)"
"""The image scrollbar handle's hover as the fixed SCROLLBAR_IMAGE sheet wrote it
until RNV-DERIVE-ALPHA: grey, while the palette's hover said BRAND_GOLD."""

RETIRED_CANVAS_OVERLAY = "#ed0a0a0a"
"""APP_CANVAS at IMAGE_OVERLAY_ALPHA: the canvas overlay, image mode's
image_viewer_bg, which nothing read. Removed by RNV-CANVAS-OVERLAY-GONE
(2026-09-26)."""

RETIRED_PANEL_OVERLAY_UPPER = "#ED1A1A1A"
"""APP_PANEL_OVERLAY as translucent() spelled it until RNV-LOWER-EIGHT
(2026-09-25): eight digits in upper case."""

RETIRED_GREY_33_SHORT = "#333"
"""A retired constant's three-digit grey(3), a spelling a six-digit census cannot
see. APP_BORDER holds grey(3) in six digits."""

RETIRED_GREY_CC_SHORT = "#ccc"
"""GREY_CC as it was once spelled, in three digits."""

RETIRED_CSS_GREY = "#808080"
"""CSS gray, what `color: gray` drew on the panel's descriptions until
RNV-MUTED-DESCRIPTIONS (2026-09-27): 4.40:1 on the dark panel and 3.62:1 in
light, both under the 4.5 floor."""

RETIRED_LIGHT_STRAY_FA = "#fafafa"
"""A light stray RNV-LIGHT-WIRING (2026-09-06) collapsed onto the register's
surface-light-2. No register value holds it, and the app no longer draws it."""

RETIRED_LIGHT_STRAY_F8 = "#f8f8f8"
"""A light stray RNV-LIGHT-WIRING (2026-09-06) collapsed onto the register's
surface-light-2. No register value holds it."""

RETIRED_LIGHT_STRAY_F0 = "#f0f0f0"
"""A light stray RNV-LIGHT-WIRING (2026-09-06) collapsed onto APP_HOVER_LIGHT. No
register value holds it, and the app no longer draws it."""

RETIRED_MATERIAL_SUCCESS = "#4caf50"
"""Material's success green, retired with the platform status sets."""

RETIRED_MATERIAL_SUCCESS_LIGHT = "#8bc34a"
"""Material's light success green, retired with them."""

RETIRED_MATERIAL_ERROR = "#f44336"
"""Material's error red, retired with them."""

RETIRED_WARNING_AMBER = "#ffc107"
"""The warning amber Material and Bootstrap shared: 1.63 on WHITE and 1.49 on
APP_SURFACE_LIGHT_3 against a 3:1 fill floor. Retired by RNV-STATUS-FAMILY."""

RETIRED_BOOTSTRAP_SUCCESS = "#28a745"
"""Bootstrap's green, retired by RNV-STATUS-FAMILY."""

RETIRED_BOOTSTRAP_ERROR = "#dc3545"
"""Bootstrap's red, retired by RNV-STATUS-FAMILY."""

RETIRED_ORPHAN_ERROR_TEXT = "#e56b77"
"""The dark error text derived from Bootstrap's red, an orphan once it went."""

RETIRED_ORPHAN_ERROR_TEXT_LIGHT = "#c82131"
"""The light error text derived from Bootstrap's red, an orphan once it went. It
read 4.6100 on the gold text floor, a rung lower than its first replacement
reached."""

RETIRED_APP_LOCAL_DARK_GOLD = "#b19145"
"""The app-local dark gold BRAND_DARK_GOLD replaced: as text on white it measured
2.9976 against a 4.5 floor."""

RETIRED_ORPHANED_LIGHT_HOVER = "#c4a458"
"""The light hover that was a tint of RETIRED_APP_LOCAL_DARK_GOLD, orphaned the
moment the accent changed. It went lighter on a light ground, toward it, and
white measured 2.3868 on it."""

RETIRED_HAND_WRITTEN_LIGHT_PRESSED = "#8a7236"
"""The hand-written light-mode pressed gold, replaced by the accent."""

RETIRED_HAND_WRITTEN_DARK_HOVER = "#dcc9a3"
"""The hand-written dark hover gold, replaced by the derived BRAND_GOLD_HOVER."""

RETIRED_HAND_WRITTEN_DARK_PRESSED = "#b7a480"
"""The hand-written dark pressed gold, replaced by the accent."""

RETIRED_TAB_HOVER_GROUND = "#d0d0d0"
"""The light tab hover ground no gold cleared as text."""

RETIRED_REV30_SUCCESS_TEXT_LIGHT = "#8a6581"
"""The register's light success text at rev 30, walked against
APP_SURFACE_LIGHT_3 as the worst light ground: 4.5225 there and 4.0241 on the
gold text floor. Rev 31 re-walked it against the floor."""

RETIRED_REV30_WARNING_TEXT_LIGHT = "#976633"
"""The register's light warning text at rev 30, walked the same way: 4.5171 on
APP_SURFACE_LIGHT_3 and 4.0193 on the gold text floor."""

RETIRED_REV30_ERROR_TEXT_LIGHT = "#b84e58"
"""The register's light error text at rev 30, walked the same way: 4.5123 on
APP_SURFACE_LIGHT_3, 4.2401 on APP_HOVER_LIGHT and 4.0150 on the gold text
floor, which it did not reach."""

# ---------------------------------------------------------------------------
# Register: values the brand publishes that this application does not draw
# ---------------------------------------------------------------------------

REGISTER_GOLD_TEXT_GROUND_FLOOR = "#e8e8e8"
"""The darkest light ground the brand's text families carry text on, registered
at rev 24. The app's IMAGE_CANVAS_LIGHT shares the hex by coincidence and
carries no text."""

REGISTER_APP_SURFACE_LIGHT_2 = "#fbfbfb"
"""The register's second light surface rung, which this app does not paint."""

REGISTER_WEB_BLACK = "#0a0a0f"
"""The register's web ground: APP_CANVAS's lightness with the blue channel lifted.
App neutrals are pure grey; this carries a tint the apps do not."""

# ---------------------------------------------------------------------------
# Invalid: written wrongly on purpose, for a test that refuses it
# ---------------------------------------------------------------------------

INVALID_RGB_TWO_CHANNELS = "rgb(100, 50)"
"""rgb() with two values, which the clipboard parser refuses."""

INVALID_RGB_TWO_SMALL_CHANNELS = "rgb(1, 2)"
"""rgb() with two values, which the panel's parser refuses."""

INVALID_RGB_EMPTY = "rgb()"
"""rgb() with no values."""

INVALID_HSV_BAD_HUE = "hsv(bad, 50%, 50%)"
"""hsv() whose hue is not a number."""

INVALID_HSL_BAD_HUE = "hsl(bad, 50%, 50%)"
"""hsl() whose hue is not a number."""

INVALID_HEX_THREE_DIGITS = "#FFF"
"""Three-digit hex, which the panel's parser refuses. Valid CSS, and other
helpers here accept it; invalid for this parser only."""

INVALID_HEX_FOUR_DIGITS = "#FFAA"
"""Hex of the wrong length, four digits."""

INVALID_HEX_FIVE_DIGITS = "#1a1a1"
"""Hex of the wrong length, five digits, refused as translucent()'s base."""

INVALID_HEX_SEVEN_DIGITS = "#FF88000"
"""Hex of the wrong length, seven digits."""

INVALID_HEX_EIGHT_DIGIT_BASE = "#1a1a1a1a"
"""Eight digits: a colour with an alpha to Qt, but not the six-digit base
translucent() takes."""

INVALID_HEX_BAD_DIGITS = "#gggggg"
"""Six characters that are not hex digits, lower case."""

INVALID_HEX_BAD_DIGITS_UPPER = "#GGGGGG"
"""Six characters that are not hex digits, upper case."""

INVALID_HEX_BAD_DIGITS_SHORT = "#GGG"
"""Three characters that are not hex digits."""

INVALID_HEX_HISTORY_LABEL = "#zzz"
"""A history item's hex label that is not a colour, given with a malformed rgb."""

INVALID_HEX_WORD = "#nonexistent"
"""A word written as a hex code, for a history lookup that must miss."""

# ---------------------------------------------------------------------------

REGISTER_REFS = {
    "REGISTER_GOLD_TEXT_GROUND_FLOOR": "GOLD_TEXT_GROUND_FLOOR",
    "REGISTER_APP_SURFACE_LIGHT_2": "APP.surface-light-2",
    "REGISTER_WEB_BLACK": "WEB_BLACK",
}
"""Each REGISTER_ value's name in the brand; tests/test_colour_values.py holds
the value to the brand at the pin."""
