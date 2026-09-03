#!/usr/bin/env python3
"""
RNV-NAMING-TOOL-DO-NOT-SWEEP

One rule for which ink goes on a colour, and the neutrals named for what
they are rather than what they do.

    python up.py             # apply, then verify
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the suites only, change nothing
    python up.py --finish    # delete this file

WHY

Chris, reading the colour tree on 2026-09-02:

    "_DRAG_HIGHLIGHT_GOLD reads as a constant but it should read as a key --
     the constant should denote the colour, as that is what will change to
     affect the rest of the app elements, not the keys."

That is the naming half of rule 1: a constant names a COLOUR, a key names a
ROLE. A name that answers both is a role frozen to a colour, and a brand swap
cannot flow through it.

The survey proposed turning CONTRAST_ON_DARK / CONTRAST_ON_LIGHT and the
SWATCH_BORDER pair into palette keys. Reading the call sites showed that was
wrong, and it is worth writing down why, because the name is what misled the
survey: "on dark" does not mean "in dark mode". It means "on a dark GROUND",
and the ground is a colour the user picked at run time. The picker proves it
by using CONTRAST_ON_LIGHT inside its is_dark branch -- correctly, because in
dark mode the button is filled with BRIGHT gold, which is a light ground.

A per-swatch runtime choice cannot be a palette key. Ruled by Chris: make it
a function.

THE FOUR ANSWERS TO ONE QUESTION

    core/palette_formats.py:426   sum(color) / 3 < 128
    core/accessibility.py:240     relative luminance < 0.179    -- correct, and
                                                                  called by no
                                                                  one else
    and over in rnv-icon-builder, two more that disagree with both.

The mean and the ITU-R 601 luma part company on saturated colour: 601 weights
green 587/1000 where the mean weights it 333. On pure green the mean calls it
dark and puts WHITE on it at 1.37:1, where the right answer is black at
15.30:1. Rendered for Chris and ruled: unify on WCAG relative luminance.

Stated as a ratio comparison rather than a threshold, so swatch_edge() can
share the rule with contrast_ink() -- a threshold would have to be
re-derived for every pair of candidates.

WHAT MOVES

  * an arbitrary swatch whose colour is saturated may get the other ink or
    the other edge. That is the fix, and it is the whole pixel cost.
  * NOTHING on a brand surface. The gold buttons keep black-on-bright and
    white-on-dark by ruling, not by measurement -- dark gold measures 4.54
    white against 4.62 black, and flipping it on a 0.08 margin would be
    obeying the arithmetic instead of the brand.

ALSO HERE

    PREVIEW_BORDER "#444444"      dead -- named, exported, never used
    PREVIEW_BORDER_THIN "#444"    the same value, three digits, 13 uses
                                  -> both become GREY_44 "#444444"
    SWATCH_BORDER_ON_DARK "#ccc"  -> GREY_CC "#cccccc"

Three-digit hexes are why these were invisible to the census, which reads
six. Naming them puts them on the chart for the first time.

    core/palette_formats.py       four cp1252 em-dashes, not valid UTF-8

CPython tolerates them because they sit in comments, so the app has always
run. Tooling does not: an audit script of mine read the file with plain UTF-8,
caught the decode error, skipped the file, and reported two live constants as
dead. The shipped guards all pass errors="replace" and were never fooled, but
the byte is a landmine for the next sweep that is not so careful. Normalised
to real em-dashes here.

NOT HERE, DELIBERATELY

    IMAGE_CANVAS_LIGHT "#e8e8e8"  role + mode in one name, so class C by the
                                  letter of the rule. Left alone: rev 27
                                  retires #e8e8e8 into pressed-light
                                  "#e0e0e0", and the ladder guard pins this
                                  constant BY NAME. Renaming it now means
                                  editing that guard twice in a fortnight.

    SVG_EXPORT_BG / _STROKE       reclassified. These read as roles, but
                                  their whole point is that they must NOT
                                  follow a brand swap -- an exported SVG is
                                  paper white and ink black whatever the app
                                  is wearing. Same category as
                                  CONTRAST_DEMO_*: fixed reference values,
                                  not paint. Class D, left alone.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "rnv-color-picker"
DESCRIPTION = "one ink rule, and the neutrals named for their colour"
SENTINEL_FILE = "utils/config.py"
SENTINEL = "RNV-INK-RULE"
GUARD = "tests/test_ink_rule.py"
SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py"}

SUITES = [
    ('pytest tests/',
     [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"]),
    ('unittest suite',
     [sys.executable, "-m", "unittest", "test_rnv_color_picker"]),
]

RETIRED = ("CONTRAST_ON_DARK", "CONTRAST_ON_LIGHT",
           "SWATCH_BORDER_ON_DARK", "SWATCH_BORDER_ON_LIGHT",
           "PREVIEW_BORDER", "PREVIEW_BORDER_THIN")

EDITS = [
    ('utils/config.py',
     'CONTRAST_ON_LIGHT: Final[str] = "#000000"\n"""Black text for use on light/bright backgrounds (e.g. color swatches)"""\n\nCONTRAST_ON_DARK: Final[str] = "#ffffff"\n"""White text for use on dark/dim backgrounds (e.g. color swatches)"""\n\nSWATCH_BORDER_ON_LIGHT: Final[str] = "#333"\n"""Dark border for color swatches on light-colored surfaces"""\n\nSWATCH_BORDER_ON_DARK: Final[str] = "#ccc"\n"""Light border for color swatches on dark-colored surfaces"""\n\n# ── Swatch preview border ──\n# Neutral gray that reads well on both dark and light backgrounds.\n# Color-preview widgets need a consistent subtle outline so the swatch\n# is visible even when the color itself is near-white or near-black.\nPREVIEW_BORDER: Final[str] = "#444444"\nPREVIEW_BORDER_THIN: Final[str] = "#444"\n',
     '# ── Neutral edges ──\n# RNV-INK-RULE (2026-09-02). Named for the colour, not the job.\n#\n# GREY_44 was the swatch-preview outline, held under two role names at once:\n# the same value written twice, once in full and once in three digits, which\n# is how it stayed invisible to a census that reads six. Only the short form\n# was ever used.\n#\n# GREY_CC is the light edge swatch_edge() reaches for on a dark ground. It\n# was three digits too, and equally invisible.\nGREY_44: Final[str] = "#444444"\nGREY_CC: Final[str] = "#cccccc"\n\n\n# ── Which ink goes on this ground ──\n#\n# RNV-INK-RULE (2026-09-02, ruled by Chris). Four places in the fleet asked\n# this question and gave three different answers, none of them a contrast\n# measurement:\n#\n#     core/palette_formats.py   sum(color) / 3 < 128\n#     ui/settings_dialog.py     (r + g + b) / 3 > 128     (icon-builder)\n#     ui/preview_utils.py       ITU-R 601 luma > 128      (icon-builder)\n#     core/accessibility.py     relative luminance < 0.179   -- correct, unused\n#\n# The mean and the 601 luma disagree with each other on saturated colour,\n# because 601 weights green 587/1000 where the mean weights it 333. On pure\n# green the mean puts white on it at 1.37:1 where the right answer is black\n# at 15.30:1.\n#\n# So: one rule, stated once, as a real comparison rather than a threshold --\n# whichever candidate has the higher contrast ratio against the ground wins.\n# A threshold would need re-deriving for every pair; a ratio does not, which\n# is what lets swatch_edge() share the rule with contrast_ink().\n#\n# This is the same maths as the surface ladder and the 4.5 floor.\n\n\ndef _channel(value: float) -> float:\n    """One sRGB channel, 0-255, linearised."""\n    c = value / 255.0\n    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4\n\n\ndef _rgb(color: "str | tuple[int, int, int]") -> tuple[int, int, int]:\n    """Accept either shape. Callers hold hex strings and RGB triples both."""\n    if isinstance(color, str):\n        h = color.lstrip("#")\n        if len(h) == 3:\n            h = "".join(ch * 2 for ch in h)\n        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))\n    return (int(color[0]), int(color[1]), int(color[2]))\n\n\ndef relative_luminance(color: "str | tuple[int, int, int]") -> float:\n    """WCAG 2.x relative luminance, 0.0 (black) to 1.0 (white)."""\n    r, g, b = _rgb(color)\n    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)\n\n\ndef contrast_ratio(a: "str | tuple[int, int, int]",\n                   b: "str | tuple[int, int, int]") -> float:\n    """WCAG contrast ratio between two colours, 1.0 to 21.0."""\n    la, lb = relative_luminance(a), relative_luminance(b)\n    hi, lo = (la, lb) if la >= lb else (lb, la)\n    return (hi + 0.05) / (lo + 0.05)\n\n\ndef better_on(background: "str | tuple[int, int, int]", *candidates: str) -> str:\n    """Whichever candidate reads best on this ground. Ties go to the first."""\n    return max(candidates, key=lambda c: contrast_ratio(background, c))\n\n\ndef contrast_ink(background: "str | tuple[int, int, int]") -> str:\n    """Text colour for an arbitrary ground: WHITE or TRUE_BLACK.\n\n    For a colour the USER chose -- a swatch, an exported palette entry. Not\n    for brand surfaces: what sits on a brand gold is a ruling, not a\n    measurement, and the two are only 0.08 apart on BRAND_DARK_GOLD.\n    """\n    return better_on(background, TRUE_BLACK, WHITE)\n\n\ndef prefers_dark_ink(background: "str | tuple[int, int, int]") -> bool:\n    """True when TRUE_BLACK reads better on this ground than WHITE does.\n\n    The shape the old call sites wanted: they all read\n    `X if brightness > 128 else Y`, so this drops straight into the\n    condition and leaves the two branches alone.\n    """\n    return contrast_ink(background) == TRUE_BLACK\n\n\ndef contrast_ink_rgb(background: "str | tuple[int, int, int]") -> tuple[int, int, int]:\n    """The same answer as an RGB triple, for the QColor and Pillow callers."""\n    return (0, 0, 0) if prefers_dark_ink(background) else (255, 255, 255)\n\n\ndef swatch_edge(background: "str | tuple[int, int, int]") -> str:\n    """Outline for a swatch of an arbitrary colour: GREY_CC or APP_BORDER."""\n    return better_on(background, APP_BORDER, GREY_CC)\n',
     1),
    ('utils/config.py',
     '- Standalone constants (CONTRAST_ON_LIGHT, PREVIEW_BORDER, DEBUG_TEXT, etc.)\n',
     '- Standalone constants (GREY_44, DEBUG_TEXT, etc.) and the ink rule\n',
     1),
    ('utils/config.py',
     "    'CONTRAST_ON_LIGHT',\n    'CONTRAST_ON_DARK',",
     "    'GREY_44',\n    'GREY_CC',\n    'relative_luminance',\n    'contrast_ratio',\n    'better_on',\n    'contrast_ink',\n    'contrast_ink_rgb',\n    'prefers_dark_ink',\n    'swatch_edge',",
     1),
    ('utils/config.py',
     "    'SWATCH_BORDER_ON_LIGHT',\n    'SWATCH_BORDER_ON_DARK',\n",
     '',
     1),
    ('utils/config.py',
     "    'PREVIEW_BORDER',\n    'PREVIEW_BORDER_THIN',\n",
     '',
     1),
    ('utils/cache.py',
     '    SWATCH_BORDER_ON_LIGHT,\n    CONTRAST_ON_LIGHT, CONTRAST_ON_DARK,\n',
     '    TRUE_BLACK, WHITE,\n    swatch_edge, contrast_ink_rgb,\n',
     1),
    ('utils/cache.py',
     '                bg      = BRAND_GOLD\n                fg      = CONTRAST_ON_LIGHT   # black text on bright gold\n',
     '                bg      = BRAND_GOLD\n                # RNV-INK-RULE: a brand decision, not a measurement. Bright\n                # gold is a light ground and takes black; dark gold takes\n                # white. Measured, dark gold is 4.54 white against 4.62 black\n                # -- a coin flip that would have moved a pixel for nothing.\n                fg      = TRUE_BLACK\n',
     1),
    ('utils/cache.py',
     '                bg      = BRAND_DARK_GOLD\n                fg      = CONTRAST_ON_DARK    # white text on dark gold\n',
     '                bg      = BRAND_DARK_GOLD\n                fg      = WHITE\n',
     1),
    ('utils/cache.py',
     '        r, g, b = rgb\n        # Perceived brightness formula (ITU-R BT.601)\n        brightness = (r * 299 + g * 587 + b * 114) / 1000\n        return (0, 0, 0) if brightness > 128 else (255, 255, 255)\n',
     '        # RNV-INK-RULE (2026-09-02): was ITU-R BT.601 perceived brightness,\n        # which is a photographic weighting, not a contrast measurement. It\n        # put white on a mid grey that reads 5.32:1 in black and 3.95:1 in\n        # white. One rule now, stated in utils/config.py.\n        return contrast_ink_rgb(rgb)\n',
     1),
    ('utils/cache.py',
     '                    border: 2px solid {SWATCH_BORDER_ON_LIGHT};\n',
     '                    border: 2px solid {swatch_edge(hex_color)};\n',
     1),
    ('core/palette_formats.py',
     '    CONTRAST_ON_LIGHT, CONTRAST_ON_DARK,\n',
     '    contrast_ink,\n',
     1),
    ('core/palette_formats.py',
     '                brightness = sum(color) / 3\n                text_color = CONTRAST_ON_DARK if brightness < 128 else CONTRAST_ON_LIGHT\n',
     '                # RNV-INK-RULE: was sum(color) / 3 < 128, which is not a\n                # contrast measurement and put white on pure green.\n                text_color = contrast_ink(color)\n',
     1),
    ('core/accessibility.py',
     'from utils.logger import Logger\nfrom utils.cache import ColorCache\n',
     'from utils import config\nfrom utils.logger import Logger\nfrom utils.cache import ColorCache\n',
     1),
    ('ui/settings_panel.py',
     '    PREVIEW_BORDER_THIN,\n',
     '    GREY_44,\n',
     1),
]

BAD_BYTES_FILE = "core/palette_formats.py"

# Every file that inlined its own copy of the rule as a ColorCache fallback.
FALLBACKS = ("RNV_Color_Picker.py", "core/workers.py",
             "ui/settings_panel.py", "ui/color_swatch_widget.py")

IMPORT_ANCHORS = {
    "RNV_Color_Picker.py": None,
    "core/workers.py": None,
    "ui/settings_panel.py": None,
    "ui/color_swatch_widget.py": None,
}


def _add_import(rel: str, text: str) -> str:
    """Put prefers_dark_ink on an existing `from utils.config import (` list.

    Every one of these files already imports from utils.config, so there is
    an anchor to extend rather than a new import line to place.
    """
    m = re.search(r"from utils\.config import \(\n", text)
    if m:
        return text[:m.end()] + "    prefers_dark_ink,\n" + text[m.end():]
    m = re.search(r"^from utils\.config import (.+)$", text, re.M)
    if m:
        return text[:m.end()] + ", prefers_dark_ink" + text[m.end():]
    # No utils.config import yet. Land it beside the other utils imports
    # rather than at the top of the file, where it would sit above the
    # third-party block and read as a mistake.
    m = re.search(r"^from utils\.[a-z_]+ import [^\n]*\n", text, re.M)
    if m:
        return text[:m.start()] + "from utils.config import prefers_dark_ink\n" + text[m.start():]
    m = re.search(r"^(import |from )", text, re.M)
    if not m:
        raise SystemExit(f"{rel}: nowhere to add the import")
    return text[:m.start()] + "from utils.config import prefers_dark_ink\n" + text[m.start():]

ACC_PATTERN = '        luminance = ColorAccessibility\\.get_relative_luminance\\(background\\)\\n[ \\t]*\\n        # If background is dark, use white text; otherwise black\\n        if luminance < 0\\.179:\\n            return \\(255, 255, 255\\)\\n        else:\\n            return \\(0, 0, 0\\)\\n'
ACC_REPLACEMENT = '        # RNV-INK-RULE (2026-09-02): one rule, one implementation. This used\n        # to hold its own copy -- luminance < 0.179, the rounded WCAG\n        # crossover -- while three other places in the fleet each held a\n        # different one. It now asks the palette module, which compares the\n        # two ratios outright instead of rounding the crossover.\n        #\n        # The two agree on 16,772,703 of the 16,777,216 sRGB colours. The\n        # 4,513 that differ all sit inside luminance 0.17900 to 0.17913,\n        # where both inks land within 0.01 of 4.5:1 and neither is visibly\n        # better than the other.\n        ink = config.contrast_ink(background)\n        return (255, 255, 255) if ink == config.WHITE else (0, 0, 0)\n'


def edits(tree) -> None:
    # FIRST, before anything reads it. The harness reads UTF-8 and this file
    # is not UTF-8, so any earlier tree.read() of it raises rather than edits.
    # That is the landmine this fix is about, met on the way to defusing it.
    raw = (Path(tree.root) / BAD_BYTES_FILE).read_bytes()
    hits = raw.count(b"\x97")
    if hits != 4:
        raise SystemExit(f"expected 4 cp1252 dashes in {BAD_BYTES_FILE}, "
                         f"found {hits} -- the file moved")
    tree.write(BAD_BYTES_FILE, raw.decode("cp1252"))
    print(f"  {BAD_BYTES_FILE}: {hits} cp1252 byte(s) normalised to UTF-8")

    for rel, old, new, times in EDITS:
        tree.sub(rel, old, new, times)
    print(f"  {len(EDITS)} edit(s) composed")

    # core/accessibility.py's block carries a trailing space on its blank
    # line, so it is anchored by pattern rather than by literal text -- a
    # hand-typed anchor with the whitespace guessed is a script that fails
    # on the machine it was not written on.
    # The four CACHE_AVAILABLE fallback branches. Each is the same two lines
    # as the canonical helper, inlined because ColorCache might not import.
    # config always imports, so the condition can just ask the rule; the two
    # branches around it are left exactly as they were.
    BRIGHT = re.compile(
        r"(?P<i>[ \t]*)brightness = \(\s*(?P<r>[^*]+?)\s*\* 299 \+\s*"
        r"(?P<g>[^*]+?)\s*\* 587 \+\s*(?P<b>[^*]+?)\s*\* 114\s*\) / 1000\n"
        r"(?P=i)(?P<rest>[^\n]*?)brightness > 128(?P<tail>[^\n]*)\n")
    swept = 0
    for rel in FALLBACKS:
        text = tree.read(rel)
        def _one(m):
            return (f"{m.group('i')}{m.group('rest')}"
                    f"prefers_dark_ink(({m.group('r')}, {m.group('g')}, "
                    f"{m.group('b')})){m.group('tail')}\n")
        text, n = BRIGHT.subn(_one, text)
        if n != 1:
            raise SystemExit(f"{rel}: expected 1 hand-rolled brightness rule, "
                             f"found {n}")
        if "prefers_dark_ink" not in text.split("\n\n")[0]:
            text = _add_import(rel, text)
        tree.write(rel, text)
        swept += n
    print(f"  {swept} inlined copy/copies of the rule replaced by a call")

    src = tree.read("core/accessibility.py")
    src, n = re.subn(ACC_PATTERN, lambda m: ACC_REPLACEMENT, src)
    if n != 1:
        raise SystemExit(f"expected 1 optimal-text-colour block, found {n}")
    tree.write("core/accessibility.py", src)
    print("  core/accessibility.py: delegated to the one rule")

    # ui/settings_panel.py holds the only heavy user of the retired thin
    # border: 13 f-string interpolations. A token swap, whole words only.
    src = tree.read("ui/settings_panel.py")
    src, n = re.subn(r"\bPREVIEW_BORDER_THIN\b", "GREY_44", src)
    if n != 12:
        raise SystemExit(f"expected 12 uses in ui/settings_panel.py, found {n}")
    tree.write("ui/settings_panel.py", src)
    print(f"  ui/settings_panel.py: {n} border reference(s) renamed")


def checks(tree) -> None:
    src = tree.read(SENTINEL_FILE)
    if SENTINEL not in src:
        raise SystemExit("the ruling note did not land")

    root = Path(tree.root)
    strays = []
    for path in sorted(root.rglob("*.py")):
        if any(p in {".git", "build", "dist", ".venv", "__pycache__"}
               for p in path.parts):
            continue
        if path.name in ("up.py", "up1.py", "up2.py"):
            continue
        rel = str(path.relative_to(root))
        text = tree.files.get(rel)
        if text is None:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "RNV-NAMING-TOOL-DO-NOT-SWEEP" in text or "RNV-INK-RULE-GUARD" in text:
            continue
        for old in RETIRED:
            if re.search(r"\b%s\b" % re.escape(old), text):
                strays.append(f"{rel}: {old}")
    if strays:
        raise SystemExit("retired names survived:\n  " + "\n  ".join(strays))

    for name in ("GREY_44", "GREY_CC", "contrast_ink", "contrast_ink_rgb",
                 "prefers_dark_ink", "swatch_edge", "relative_luminance",
                 "contrast_ratio", "better_on"):
        if f"'{name}'," not in src:
            raise SystemExit(f"{name} is not exported from {SENTINEL_FILE}")

    # A three-digit hex is what hid two of these from the census. None left.
    for rel in (SENTINEL_FILE,):
        for m in re.finditer(r"""['"]#[0-9a-fA-F]{3}['"]""", tree.read(rel)):
            raise SystemExit(f"{rel} still writes a three-digit hex: {m.group(0)}")

    body = tree.read(BAD_BYTES_FILE)
    body.encode("utf-8")            # would raise if anything survived
    if "—" not in body:
        raise SystemExit("the em-dashes did not survive the re-encode")

    print(f"  guards: {len(RETIRED)} names retired, ink rule stated once, "
          f"{BAD_BYTES_FILE} is UTF-8")


GUARD_SOURCE = r'''"""One rule for which ink goes on a ground. RNV-INK-RULE-GUARD

Ruled by Chris on 2026-09-02 after seeing the three rules rendered side by
side: unify on WCAG relative luminance.

Four places in the fleet answered this question and gave three different
answers, none of them a contrast measurement. This guard exists because that
is a failure that reappears -- the next person who needs an ink for a swatch
will reach for (r+g+b)/3 unless something stops them.
"""
from __future__ import annotations

import re
from pathlib import Path

from utils import config

ROOT = Path(__file__).resolve().parent.parent
RETIRED = ('CONTRAST_ON_DARK', 'CONTRAST_ON_LIGHT', 'SWATCH_BORDER_ON_DARK', 'SWATCH_BORDER_ON_LIGHT', 'PREVIEW_BORDER', 'PREVIEW_BORDER_THIN')
SKIP = {".git", "build", "dist", ".venv", "__pycache__"}


def _code_only(text: str) -> str:
    """The file with every comment and string literal removed.

    Written after the first version of this guard failed on its own
    explanation. A guard that sweeps for the thing it forbids must be able to
    tell a use from a mention, and every previous attempt at that in this
    programme did it by excluding files, which stops working the moment a
    third file has a legitimate reason to say the word. Tokenising is the
    version that does not need a list."""
    import io
    import tokenize
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text          # unparseable: fall back to the whole text
    return " ".join(out)


def _sources():
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in SKIP for p in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "RNV-INK-RULE-GUARD" in text or "RNV-NAMING-TOOL-DO-NOT-SWEEP" in text:
            continue
        yield path, text


def test_the_rule_is_a_real_contrast_measurement():
    """Black on white and white on black, the two ends. If the rule were
    inverted or the luminance formula wrong, these are what break first."""
    assert config.contrast_ink("#ffffff") == config.TRUE_BLACK
    assert config.contrast_ink("#000000") == config.WHITE
    assert round(config.contrast_ratio("#ffffff", "#000000"), 2) == 21.0
    assert round(config.contrast_ratio("#777777", "#777777"), 2) == 1.0


def test_the_rule_gets_saturated_colour_right():
    """The case the mean got wrong. Pure green is a LIGHT ground -- it is 71%
    of the luminance of white -- and the mean called it dark because it only
    looked at how many channels were lit."""
    assert config.contrast_ink((0, 255, 0)) == config.TRUE_BLACK
    assert config.contrast_ratio((0, 255, 0), config.TRUE_BLACK) > 15
    # and the mean, for the record, would have chosen the other one
    assert sum((0, 255, 0)) / 3 < 128


def test_it_takes_a_hex_string_or_an_rgb_triple():
    """Callers hold both shapes, and a silent TypeError inside an f-string
    renders as an empty colour rather than an exception."""
    assert config.contrast_ink("#00ff00") == config.contrast_ink((0, 255, 0))
    assert config.contrast_ink("#0f0") == config.contrast_ink("#00ff00")


def test_the_edge_rule_shares_the_ink_rule():
    """swatch_edge answers the same question with a different pair. If it
    ever grows its own threshold, this is what catches it."""
    assert config.swatch_edge("#ffffff") == config.APP_BORDER
    assert config.swatch_edge("#000000") == config.GREY_CC
    for ground in ("#ffffff", "#000000", "#8c7337", "#00ff00", "#777777"):
        edge = config.swatch_edge(ground)
        other = config.GREY_CC if edge == config.APP_BORDER else config.APP_BORDER
        assert config.contrast_ratio(ground, edge) >= \
            config.contrast_ratio(ground, other)


def test_the_brand_golds_are_ruled_not_measured():
    """The close button keeps black on bright gold and white on dark gold.

    Dark gold measures 4.54 white against 4.62 black -- close enough that the
    arithmetic would flip it, which is exactly why the two call sites in
    utils/cache.py name the colour outright instead of asking the rule. This
    test states the margin so that a later 'cleanup' that routes them through
    contrast_ink() has to argue with a number."""
    white = config.contrast_ratio(config.BRAND_DARK_GOLD, config.WHITE)
    black = config.contrast_ratio(config.BRAND_DARK_GOLD, config.TRUE_BLACK)
    assert abs(white - black) < 0.15, (
        "the golds moved; re-take the ruling rather than the measurement")
    src = (ROOT / "utils" / "cache.py").read_text(encoding="utf-8-sig")
    assert "fg      = TRUE_BLACK" in src and "fg      = WHITE" in src, (
        "the gold button inks are no longer written as a decision")


def test_the_accessibility_helper_does_not_hold_a_second_copy():
    """It held its own luminance < 0.179 while three other places each held
    something else. One rule, one implementation."""
    src = _code_only(
        (ROOT / "core" / "accessibility.py").read_text(encoding="utf-8-sig"))
    assert "0.179" not in src, "a second crossover threshold is back"
    assert config.contrast_ink("#ffffff") == config.TRUE_BLACK
    from core.accessibility import ColorAccessibility
    assert ColorAccessibility.get_optimal_text_color((255, 255, 255)) == (0, 0, 0)
    assert ColorAccessibility.get_optimal_text_color((0, 0, 0)) == (255, 255, 255)
    assert ColorAccessibility.get_optimal_text_color((0, 255, 0)) == (0, 0, 0)


def test_no_call_site_measures_brightness_by_hand():
    """The rule is only one rule while nothing else computes its own.

    Matches the two shapes that were actually here -- a mean of the three
    channels, and the ITU-R 601 weights -- rather than any arithmetic, so it
    stays readable and does not fire on unrelated maths."""
    mean = re.compile(r"sum \( colou?r \) / 3|\( r \+ g \+ b \) / 3")
    luma = re.compile(r"\* 299\b|\* 587\b|\* 114\b")
    strays = []
    for path, text in _sources():
        code = _code_only(text)
        if mean.search(code) or luma.search(code):
            strays.append(str(path.relative_to(ROOT)))
    assert not strays, f"hand-rolled brightness rules are back in: {strays}"


def test_the_fallback_branches_no_longer_hold_their_own_copy():
    """Four files inlined the rule as a `if CACHE_AVAILABLE ... else` fallback,
    each an exact copy of ColorCache's own. Seven implementations of one
    question in one application, on three different rules, is what the sweep
    above exists to stop coming back."""
    for rel in ("RNV_Color_Picker.py", "core/workers.py",
                "ui/settings_panel.py", "ui/color_swatch_widget.py",
                "utils/cache.py"):
        code = _code_only((ROOT / rel).read_text(encoding="utf-8-sig"))
        assert "brightness > 128" not in code, f"{rel} still rolls its own"
    from utils.cache import ColorCache
    assert ColorCache.get_text_color_for_background((128, 128, 128)) == (0, 0, 0)
    assert ColorCache.get_text_color_for_background((0, 0, 0)) == (255, 255, 255)


def test_the_retired_names_are_gone():
    strays = []
    for path, text in _sources():
        for old in RETIRED:
            if re.search(r"\b%s\b" % re.escape(old), text):
                strays.append(f"{path.relative_to(ROOT)}: {old}")
    assert not strays, "retired names are still in use:\n  " + "\n  ".join(strays)


def test_every_source_file_is_utf8():
    """core/palette_formats.py carried four cp1252 em-dashes. CPython let it
    run because they sat in comments; an audit script read it with plain
    UTF-8, swallowed the decode error, skipped the file, and reported two
    live constants as dead. A sweep that cannot read a file is worse than one
    that fails."""
    bad = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in SKIP for p in path.parts):
            continue
        try:
            path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            bad.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not bad, "not valid UTF-8:\n  " + "\n  ".join(bad)


def test_no_three_digit_hex_in_the_palette():
    """Two of the retired constants were "#333" and "#ccc". The census reads
    six-digit hexes, so a three-digit one is a value the chart cannot see."""
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    hits = re.findall(r"""['"]#[0-9a-fA-F]{3}['"]""", src)
    assert not hits, f"three-digit hexes are back: {hits}"
'''


# ------------------------------------------------------------------ plumbing
def refuse_to_shadow() -> None:
    name = Path(__file__).name
    if name in SHADOWS:
        sys.exit(f"refusing to run as {name} -- it would shadow a module on "
                 f"sys.path. Rename to up.py and run again.")


class Tree:
    """Every edit lands here first. Disk is written only after all guards pass,
    so --check is a real rehearsal and a half-applied state is impossible."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, str] = {}

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def sub(self, rel: str, old: str, new: str, times: int = 1) -> None:
        src = self.read(rel)
        found = src.count(old)
        if found != times:
            raise SystemExit(
                f"{rel}: expected {times} occurrence(s) of the anchor, found "
                f"{found}. The file moved; re-derive this edit before trusting "
                f"the script.")
        self.write(rel, src.replace(old, new, times))

    def flush(self) -> list[str]:
        """Compare and write BYTES, not decoded text.

        read_text('utf-8') here raised on a file that was not valid UTF-8 --
        which is precisely the file some scripts exist to fix. Bytes compare
        identically for everything else and cannot refuse to look."""
        touched = []
        for rel, text in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = text.encode("utf-8")
            if not p.exists() or p.read_bytes() != data:
                p.write_bytes(data)
                touched.append(rel)
        return touched


def _tail(out: str, lines: int = 40) -> str:
    text = out.strip()
    marker = "short test summary info"
    if marker in text:
        return text[max(0, text.rindex(marker) - 30):]
    return "\n".join(text.splitlines()[-lines:])


def _outcome(code: int, out: str) -> str:
    """"pass", "fail", "abort" or "env" -- only exit code 1 means a test failed.

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
        return "fail"
    return "env"


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
    return code


def verify() -> int:
    code = _step("guard",
                 [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                  GUARD])
    if code != 0:
        return code
    for label, args in SUITES:
        code = _step(label, args)
        if code != 0:
            return code
    print("\nGreen.")
    return 0


def apply(check_only: bool) -> int:
    root = Path.cwd()
    if not (root / SENTINEL_FILE).exists():
        # A script whose sentinel file is created by an EARLIER script cannot
        # tell "wrong directory" from "prerequisite not run", and the default
        # message asserts the first while the second is more likely. Such a
        # script sets MISSING_HELP and says which one to run.
        raise SystemExit(globals().get("MISSING_HELP") or
                         f"run this from the root of a {REPO} checkout "
                         f"(no {SENTINEL_FILE} here)")
    if SENTINEL in (root / SENTINEL_FILE).read_text(encoding="utf-8"):
        raise SystemExit(f"already applied -- {SENTINEL!r} is present in "
                         f"{SENTINEL_FILE}")

    tree = Tree(root)
    edits(tree)
    tree.write(GUARD, GUARD_SOURCE)
    checks(tree)

    if check_only:
        print("--check: every edit composes and every guard passes. "
              "Nothing written.")
        return 0

    touched = tree.flush()
    print("wrote: " + ", ".join(touched) + "\n")
    return verify()


def finish() -> None:
    me = Path(__file__).resolve()
    print(f"removing {me.name}")
    me.unlink()


def main() -> int:
    refuse_to_shadow()
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--check", action="store_true",
                    help="rehearse every edit in memory, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run the suites only, change nothing")
    ap.add_argument("--finish", action="store_true", help="delete this script")
    args = ap.parse_args()
    if args.finish:
        finish()
        return 0
    if args.verify:
        return verify()
    return apply(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
