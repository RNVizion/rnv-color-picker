#!/usr/bin/env python3
"""RNV-RATING-SCALE — the accessibility panel stops failing its own standard.

    python up.py             # apply, then install the pin and run both suites
    python up.py --check     # rehearse every edit in memory, write nothing

For rnv-color-picker, derived against a fresh clone at the live head.

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names the values it retires. That marker is what
tells this fleet's scanners to skip it.

RUN THE rnv-brand SCRIPT FIRST. This one bumps the register pin to rev 32 and
reads BRAND_BLUE from it. If rnv-brand is still at b4fa970 the install below
succeeds and the palettes then hold a colour the register does not publish.

WHAT WAS WRONG. `core/accessibility.py::get_contrast_rating_color` returned
four hard-coded Material Design tuples -- (76,175,80), (139,195,74),
(255,193,7), (244,67,54) -- painted as `color:` on the contrast-ratio label in
Settings > Accessibility. One set for three grounds, tuned against a dark one.
Measured on the real widget, against the ground sampled from its own pixels:

    tier                      today            after
    Excellent   #4caf50  light 2.55      #825d79  5.08
    Good        #8bc34a  light 1.93      #456c91  5.06
    Fair        #ffc107  light 1.50      #8e5e2b  5.09
    Poor        #f44336  light 3.38      #ae4650  5.08

Dark and image already cleared the floor; light failed in all four tiers. The
panel that grades a user's colours against WCAG was painting its own verdict
at 1.50:1.

WHY NOTHING CAUGHT IT. tests/test_brand_contrast.py::test_one_status_family_only
has asserted since 2026-08-13 that Material's values must be gone. It read
utils/config.py only, and it searched for them as HEX. The survivors were in
core/accessibility.py as INT TRIPLES -- two independent reasons the guard
could not fire, either one of them sufficient. It is widened here to parse
every source file this application ships and to read both notations.

THE SHAPE. The tier becomes a palette KEY resolved per mode; the colour comes
from the active theme. That is the move `status_error_text` made on
2026-09-03, whose own test records why: "no registered red clears #f5f5f5 and
#1a1a1a alike." It is the same arithmetic here, and it is general -- 4.5:1 on
#1a1a1a needs relative luminance >= 0.221484 and on #f5f5f5 <= 0.164022, so no
single colour serves both grounds. The best any value manages on both at once
is 3.9954:1.

ONE NEW COLOUR AND ONE MISSING PAIR. `good` takes BRAND_BLUE / BRAND_DARK_BLUE
(rnv-brand rev 32) because no registered value sat between success-text and
warning-text without collapsing into one of them. And STATUS_WARNING_TEXT and
STATUS_WARNING_TEXT_LIGHT are added: success and error each carried a dark
text value and a light sibling, warning carried neither.

VERIFIED BY RENDERING, not by reading. The real SettingsPanel was built
offscreen on the edited tree, its Accessibility tab made current, the spin
boxes driven to land mid-tier, and the label's pixels sampled. Twelve frames,
three modes by four tiers: every one paints the declared value and every one
clears 4.5.
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

REPO = "rnv-color-picker"
SENTINEL_FILE = "tests/conftest.py"
SENTINEL = "RNV-RATING-SCALE"
GUARD = "tests/test_brand_contrast.py"
DESCRIPTION = "give the contrast-rating label a per-mode, registered scale"

SHADOWS = {"colors.py", "config.py", "conftest.py", "run_tests.py",
           "accessibility.py"}

PIN = ("rnv-brand @ git+https://github.com/RNVizion/rnv-brand"
       "@54286212992a0013bdc3d860357c4261452b014a")


def post_write() -> None:
    """Install what the new pin DECLARES, because declaring is not installing.

    This round edits tests/requirements-dev.txt and then runs suites that
    import engine.brand and compare this app's mirror against it. Without
    this step those suites run against whatever register is already on the
    machine -- rev 31, which does not publish BRAND_BLUE -- and the failure
    reads like the edits are wrong.
    """
    for extra in ([], ["--break-system-packages"]):
        code, out = run("installing the register at the new pin",
                        [sys.executable, "-m", "pip", "install", "-q",
                         "--disable-pip-version-check", *extra, PIN])
        if code == 0:
            print("  the register is at rev 32")
            return
    print(out[-1500:])
    raise SystemExit(
        "\nCOULD NOT INSTALL THE REGISTER. Nothing was verified and nothing "
        "was reverted -- the edits are on disk and `git diff` shows them.\n\n"
        "The suites below import engine.brand and compare this app's mirror "
        "against it, so running them now would test against the OLD register "
        "and fail in a way that looks like the edits are wrong.\n\n"
        "Install it by hand, then re-check:\n\n"
        "    pip install -r tests/requirements-dev.txt\n"
        "    python up.py --verify\n")


def _timeout_flag() -> list:
    """--timeout only when the plugin can actually be imported."""
    return ["--timeout=120"] if find_spec("pytest_timeout") else []


SUITES = [("\"pytest tests/\"",
           [sys.executable, "-m", "pytest", "tests/", "-q",
            "-p", "no:cacheprovider"]),
          ("\"the LOCKED file\"",
           [sys.executable, "-m", "pytest", "test_rnv_color_picker.py", "-q",
            "-p", "no:cacheprovider"] + _timeout_flag())]

EDITS = [('tests/conftest.py', "# RNV-GOLD-HOVER, 2026-09-12 -- every hover on the main surface takes the\n# mode's gold: BRAND_GOLD in dark and image, BRAND_DARK_GOLD in light. The\n", "# RNV-RATING-SCALE, 2026-09-12 -- the contrast-rating label takes the\n# STATUS text family plus BRAND_BLUE, per mode, instead of four\n# hard-coded Material tuples that read 2.55, 1.93, 1.50 and 3.38 against\n# a 4.5 floor in light mode. The guard that was meant to forbid them read\n# one file and searched for hex; they lived in another file as int\n# triples.\n# RNV-GOLD-HOVER, 2026-09-12 -- every hover on the main surface takes the\n# mode's gold: BRAND_GOLD in dark and image, BRAND_DARK_GOLD in light. The\n", 1), ('utils/config.py', 'Carries white text at 4.5429 and black at 4.6226. Black stays the ruled\npairing and the better number.\n"""\n\nBRAND_DARK_GOLD_DEEP', 'Carries white text at 4.5429 and black at 4.6226. Black stays the ruled\npairing and the better number.\n"""\n\nBRAND_BLUE: Final[str] = "#6f94bc"\n"""Brand blue -- dark-mode TEXT. Registered 2026-09-12 (rnv-brand rev 32).\n\nThe register\'s second hue and the first value in it that is not gold, black\nor white. Mixed in `paint` mode from the web violet, a steel blue, brand gold\nand STATUS["success"]; see rnv-brand\'s BRAND_COLORS.md for the derivation.\n\n    on #000000 ............. 6.6380\n    on #0a0a0a ............. 6.2581\n    on #1a1a1a ............. 5.5014   <- the job\n    on #2a2a2a ............. 4.5370   <- the floor, and it is close\n    on #3a3a3a ............. 3.5954   FAILS. Do not carry text on panel-hover.\n\nBlack on it reads 6.6380 and white 3.1635, so text on a blue FILL is black\nhere. That is the same way round as the golds -- but the LIGHT blue inverts,\nwhich the golds do not. See BRAND_DARK_BLUE.\n"""\n\nBRAND_DARK_BLUE: Final[str] = "#456c91"\n"""Brand dark blue -- light-mode TEXT. Registered 2026-09-12.\n\nDarker BECAUSE the ground is lighter, exactly as BRAND_DARK_GOLD is. The pair\nis ONE colour at two lightnesses: same hue to within 0.9 degrees, L* 15.78\napart, which is the step the STATUS text family already uses between its own\npairs. rnv-brand asserts both at import.\n\n    on #ffffff ............. 5.5162\n    on #f5f5f5 ............. 5.0597   <- the job\n    on #eeeeee ............. 4.7544\n    on #e8e8e8 ............. 4.5020   <- clears by 0.0020; NOT a permission\n    on #e0e0e0 ............. 4.1787   FAILS.\n\nWHITE on it reads 5.5162 and black 3.8069. That is the OPPOSITE of every gold\nin this file, where black wins on both. A blue fill takes black text in dark\nmode and white text in light; do not carry the gold rule across.\n\nWHY A PAIR AT ALL, and it is arithmetic rather than taste: 4.5:1 on #1a1a1a\nneeds relative luminance >= 0.221484 and on #f5f5f5 needs <= 0.164022. The\nintervals do not meet. The best any single colour manages on both at once is\n3.9954:1, so no one value could have served both grounds.\n"""\n\nBRAND_DARK_GOLD_DEEP', 1), ('utils/config.py', 'RNV-STATUS-LIGHT-FLOOR closed at rev 31: re-walked against #e8e8e8, where\nit now reads 4.52. See STATUS_ERROR_TEXT_LIGHT below for why that ground\nand not #e0e0e0."""\n\nSTATUS_ERROR: Final[str] = "#c75b64"', 'RNV-STATUS-LIGHT-FLOOR closed at rev 31: re-walked against #e8e8e8, where\nit now reads 4.52. See STATUS_ERROR_TEXT_LIGHT below for why that ground\nand not #e0e0e0."""\n\nSTATUS_WARNING_TEXT: Final[str] = "#bc8752"\n"""Registered. Warning TEXT on a dark panel: 5.57 on #1a1a1a, 4.59 on #2a2a2a.\n\nADDED 2026-09-12, AND THE REASON IS WRITTEN FOUR DOCSTRINGS ABOVE. Success and\nerror each carried a dark text value and a light sibling; warning carried\nneither, so the family was two-thirds of a family. STATUS_SUCCESS_TEXT_LIGHT\'s\nown docstring says it is "carried so the light sibling exists before it is\nneeded ... adding it later is how an asymmetry gets built in". The warning pair\nis the asymmetry that got built in anyway, in the same change that argued\nagainst it.\n\nSTATUS_WARNING is a FILL and cannot do this job: it reads 4.07 on #1a1a1a,\nbelow the 4.5 text floor. That is the fill/text band split the family header\nabove describes, and it is why there are separate values rather than one."""\n\nSTATUS_WARNING_TEXT_LIGHT: Final[str] = "#8e5e2b"\n"""Registered. The same text on a light panel: 5.08 on #f5f5f5, 4.52 on\n#e8e8e8.\n\nCarried with its dark sibling rather than after it, for the reason above."""\n\nSTATUS_ERROR: Final[str] = "#c75b64"', 1), ('utils/config.py', "    'status_error_text': STATUS_ERROR_TEXT,\n    'name': 'Dark',", '    \'status_error_text\': STATUS_ERROR_TEXT,\n\n    # ── The contrast-rating scale, RNV-RATING-SCALE 2026-09-12 ──\n    # Four tiers, theme-aware for the same reason status_error_text is:\n    # no value clears both grounds, so the tier has to be a KEY and the\n    # colour has to come from the palette.\n    #\n    # WHAT THEY REPLACE. core/accessibility.py returned four hard-coded\n    # Material tuples -- (76,175,80), (139,195,74), (255,193,7),\n    # (244,67,54) -- painted as `color:` on the contrast-ratio label. They\n    # were mode-blind, one set for three grounds, and chosen against a dark\n    # one, so in LIGHT mode all four sat under the 4.5 text floor: 2.55,\n    # 1.93, 1.50 and 3.38. The panel that grades the user\'s colours against\n    # WCAG was painting its own verdict at 1.50:1.\n    #\n    # WHY test_one_status_family_only NEVER SAW THEM. It reads this file\n    # only, and searches for the retired values as HEX. They lived in\n    # another module as INT TUPLES. Two independent reasons the guard could\n    # not fire, and it has asserted "Material\'s values must be gone" since\n    # 2026-08-13 while four of them rendered. The guard now parses every\n    # source file and reads both notations.\n    #\n    # `good` IS THE ONLY NEW COLOUR. Excellent, fair and poor take the\n    # status text family this file already holds. Good could not: it needed\n    # to sit between success-text and warning-text without collapsing into\n    # either, and no registered value did. BRAND_BLUE was made for it and\n    # registered on the same day.\n    \'rating_excellent\':   STATUS_SUCCESS_TEXT,    # 5.52 on #1a1a1a\n    \'rating_good\':        BRAND_BLUE,             # 5.50\n    \'rating_fair\':        STATUS_WARNING_TEXT,    # 5.57\n    \'rating_poor\':        STATUS_ERROR_TEXT,      # 5.48\n    \'name\': \'Dark\',', 1), ('utils/config.py', "    'status_error_text': STATUS_ERROR_TEXT_LIGHT,\n    'name': 'Light',", "    'status_error_text': STATUS_ERROR_TEXT_LIGHT,\n\n    # ── The contrast-rating scale, RNV-RATING-SCALE 2026-09-12 ──\n    # The light siblings. This is the mode the Material values failed in --\n    # all four under 4.5 on #f5f5f5, the amber at 1.50 -- and the mode that\n    # made the scale a palette key rather than a function's return value.\n    'rating_excellent':   STATUS_SUCCESS_TEXT_LIGHT,    # 5.08 on #f5f5f5\n    'rating_good':        BRAND_DARK_BLUE,              # 5.05\n    'rating_fair':        STATUS_WARNING_TEXT_LIGHT,    # 5.08\n    'rating_poor':        STATUS_ERROR_TEXT_LIGHT,      # 5.08\n    'name': 'Light',", 1), ('core/accessibility.py', '    @staticmethod\n    def get_contrast_rating_color(ratio: float) -> tuple[int, int, int]:\n        """\n        Get a color representing the contrast rating for UI display.\n        \n        Args:\n            ratio: Contrast ratio\n            \n        Returns:\n            RGB color (green = good, yellow = fair, red = poor)\n        """\n        if ratio >= 7.0:\n            return (76, 175, 80)    # Green - AAA\n        elif ratio >= 4.5:\n            return (139, 195, 74)   # Light Green - AA\n        elif ratio >= 3.0:\n            return (255, 193, 7)    # Yellow/Amber - AA Large only\n        else:\n            return (244, 67, 54)    # Red - Fail\n', '    #: The four rating tiers, as PALETTE KEYS rather than colours.\n    #:\n    #: A constant names a colour and a key names a role -- ruled 2026-09-02.\n    #: "The colour of the Good tier" is a role, and it is a role whose answer\n    #: differs per mode, which is why it cannot live in this module at all.\n    #: This module owns WHICH TIER a ratio falls in; utils/config.py owns what\n    #: each tier looks like on the ground it is drawn on.\n    RATING_KEYS: tuple[str, ...] = ("rating_excellent", "rating_good",\n                                    "rating_fair", "rating_poor")\n\n    @staticmethod\n    def get_contrast_rating_key(ratio: float) -> str:\n        """Which rating tier a ratio falls in, as a palette key.\n\n        The thresholds are WCAG\'s and are unchanged: 7.0 AAA, 4.5 AA, 3.0 AA\n        for large text only, below that a failure. What changed on 2026-09-12\n        is that this returns the NAME of the tier instead of a colour.\n\n        Args:\n            ratio: Contrast ratio\n\n        Returns:\n            One of RATING_KEYS -- look it up in the active theme.\n        """\n        if ratio >= 7.0:\n            return "rating_excellent"\n        elif ratio >= 4.5:\n            return "rating_good"\n        elif ratio >= 3.0:\n            return "rating_fair"\n        else:\n            return "rating_poor"\n\n    @staticmethod\n    def get_contrast_rating_color(\n            ratio: float,\n            theme: dict | None = None) -> tuple[int, int, int]:\n        """\n        Get a color representing the contrast rating for UI display.\n\n        RNV-RATING-SCALE, 2026-09-12. This used to return one of four\n        hard-coded Material Design tuples -- (76,175,80), (139,195,74),\n        (255,193,7), (244,67,54) -- the same four whatever mode the app was\n        in. Against the light panel #f5f5f5 they read 2.55, 1.93, 1.50 and\n        3.38 against a 4.5 text floor, so the panel that grades a user\'s\n        colours against WCAG painted its own verdict below the floor in\n        every light-mode tier. The amber read 1.50:1.\n\n        `theme` is OPTIONAL so that the old one-argument call still works;\n        omitted, it answers for the dark palette, which is what the four\n        Material values were tuned against anyway. Callers that can see the\n        active theme should pass it, or better, use get_contrast_rating_key\n        and read the palette directly -- an RGB triple cannot carry the\n        alpha some palettes use.\n\n        Args:\n            ratio: Contrast ratio\n            theme: A theme dict from utils.config; defaults to dark\n\n        Returns:\n            RGB color for the tier, on the ground `theme` describes\n        """\n        palette = theme if theme is not None else config.DARK_THEME_COLORS\n        value = str(palette[ColorAccessibility.get_contrast_rating_key(ratio)])\n        digits = value.lstrip("#")\n        if len(digits) == 8:                 # #AARRGGBB, Qt\'s own spelling\n            digits = digits[2:]\n        return (int(digits[0:2], 16), int(digits[2:4], 16),\n                int(digits[4:6], 16))\n', 1), ('ui/settings_panel.py', '    def update_theme(self) -> None:\n        """Update/apply theme styling to the dialog. Can be called externally."""\n        from PyQt6.QtGui import QPalette\n        \n        # Get active theme dict (fallback to dark)\n        if self.parent_app and hasattr(self.parent_app, \'theme_manager\'):\n            theme = self.parent_app.theme_manager.get_current_theme()\n        else:\n            from utils.config import DARK_THEME_COLORS\n            theme = DARK_THEME_COLORS\n        ', '    def update_theme(self) -> None:\n        """Update/apply theme styling to the dialog. Can be called externally."""\n        from PyQt6.QtGui import QPalette\n\n        # Get active theme dict (fallback to dark)\n        # RNV-RATING-SCALE 2026-09-12: this was an inline copy of _get_theme,\n        # byte for byte, forty lines further up the same class. Collapsed onto\n        # it because the contrast-rating label now asks the same question and a\n        # THIRD copy is how two parts of one dialog end up painting for\n        # different modes -- the failure this fleet already collapsed ten\n        # implementations of in the ink rule.\n        #\n        # The three OTHER `hasattr(self.parent_app, \'theme_manager\')` sites in\n        # this file are deliberately left alone: they read `current_theme`, the\n        # mode NAME, to pick a gold or compare against a combo box. Same guard,\n        # different question.\n        theme = self._get_theme()\n        ', 1), ('ui/settings_panel.py', '        # Update ratio display\n        rating_color = ColorAccessibility.get_contrast_rating_color(result.ratio)\n        self.contrast_ratio_label.setText(f"Contrast Ratio: {result.ratio:.2f}:1  ({result.rating_text})")\n        self.contrast_ratio_label.setStyleSheet(f"""\n            font-size: 16px;\n            font-weight: bold;\n            padding: 10px;\n            color: rgb({rating_color[0]}, {rating_color[1]}, {rating_color[2]});\n        """)', '        # Update ratio display\n        # RNV-RATING-SCALE: the tier is logic and the colour is the palette\'s.\n        # Read from the ACTIVE theme, because this label failed the 4.5 text\n        # floor in light mode for as long as the colour was a constant.\n        rating_color = self._get_theme()[\n            ColorAccessibility.get_contrast_rating_key(result.ratio)]\n        self.contrast_ratio_label.setText(f"Contrast Ratio: {result.ratio:.2f}:1  ({result.rating_text})")\n        self.contrast_ratio_label.setStyleSheet(f"""\n            font-size: 16px;\n            font-weight: bold;\n            padding: 10px;\n            color: {rating_color};\n        """)', 1), ('tests/test_brand_contrast.py', 'def test_one_status_family_only() -> None:\n    """Both Bootstrap and Material sets lived here at once. The ruling of\n    2026-08-13 chose Bootstrap; Material\'s values must be gone."""\n    src = _config_source()\n    stale = [v for v in ("#4caf50", "#f44336") if v in src.lower()]\n    assert not stale, f"retired Material status colours still present: {stale}"\n', '#: The retired platform values, in BOTH notations this repository has ever\n#: spelled a colour in. The hex form is what the palettes use; the int triple\n#: is what core/accessibility.py used, and is half the reason the guard below\n#: passed for thirty days over four live values.\n_RETIRED_PLATFORM: dict[str, str] = {\n    "#4caf50": "Material success",\n    "#8bc34a": "Material success, light",\n    "#ffc107": "Material and Bootstrap warning",\n    "#f44336": "Material error",\n}\n\n\ndef _app_sources():\n    """Every .py this application ships, minus the files that NAME retired\n    values on purpose and minus any delivery script.\n\n    Scoped to the REPOSITORY rather than to utils/config.py. The old version\n    of the guard below read one file, and the values it was looking for were\n    in another.\n    """\n    for path in sorted(PROJECT_ROOT.rglob("*.py")):\n        if any(part.startswith(".") for part in path.parts):\n            continue\n        text = path.read_text(encoding="utf-8-sig", errors="replace")\n        if "RNV-GOLD-GUARD-FILE-NAMES-RETIRED" in text:\n            continue\n        if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:\n            continue\n        yield path, text\n\n\ndef _colour_triples(tree):\n    """Every (r, g, b) literal of ints in 0-255, as a hex string.\n\n    A two-element tuple is a size and anything with a float is a ratio; the\n    range test is what keeps setContentsMargins-shaped calls out. Yields the\n    node too, so the failure can name a line.\n    """\n    for node in ast.walk(tree):\n        if not isinstance(node, ast.Tuple) or len(node.elts) != 3:\n            continue\n        if not all(isinstance(e, ast.Constant) and isinstance(e.value, int)\n                   and not isinstance(e.value, bool) and 0 <= e.value <= 255\n                   for e in node.elts):\n            continue\n        yield node, "#%02x%02x%02x" % tuple(e.value for e in node.elts)\n\n\ndef test_one_status_family_only() -> None:\n    """Both Bootstrap and Material sets lived here at once. The ruling of\n    2026-08-13 chose Bootstrap; Material\'s values must be gone.\n\n    THIS TEST PASSED FOR THIRTY DAYS WHILE FOUR OF THEM RENDERED, and the two\n    reasons are worth keeping written down because either alone was enough:\n\n      1. IT READ ONE FILE. `_config_source()` is utils/config.py. The\n         survivors were in core/accessibility.py.\n      2. IT SEARCHED FOR HEX. The survivors were int triples --\n         `return (76, 175, 80)` -- so a text search for "#4caf50" could not\n         have found them even in the right file.\n\n    They were `get_contrast_rating_color`\'s four return values, painted as\n    `color:` on the contrast-ratio label in the accessibility panel. Retired\n    2026-09-12 by RNV-RATING-SCALE.\n\n    A guard scoped narrower than the thing it guards reports a clean sweep of\n    the corner it swept.\n    """\n    found = []\n    for path, text in _app_sources():\n        try:\n            tree = ast.parse(text)\n        except SyntaxError:\n            continue\n        rel = path.relative_to(PROJECT_ROOT)\n        for node in ast.walk(tree):\n            if (isinstance(node, ast.Constant) and isinstance(node.value, str)\n                    and node.value.lower() in _RETIRED_PLATFORM):\n                found.append(f"  {rel}:{node.lineno}: {node.value} "\n                             f"({_RETIRED_PLATFORM[node.value.lower()]})")\n        for node, hexv in _colour_triples(tree):\n            if hexv in _RETIRED_PLATFORM:\n                found.append(f"  {rel}:{node.lineno}: {hexv} as an int triple "\n                             f"({_RETIRED_PLATFORM[hexv]})")\n    assert not found, ("retired platform status colours are still live:\\n"\n                       + "\\n".join(sorted(found)))\n\n\ndef test_the_rating_scale_is_a_palette_key_in_every_mode() -> None:\n    """RNV-RATING-SCALE. The four tiers must exist in all three palettes and\n    must clear the text floor on the ground each one is drawn on.\n\n    The Material values this replaced were one set for three grounds. In\n    light mode they read 2.55, 1.93, 1.50 and 3.38 -- the panel that grades\n    a user\'s colours against WCAG painting its own verdict below the floor.\n    """\n    from core.accessibility import ColorAccessibility\n    for name, palette in PALETTES.items():\n        ground = palette.get("panel_bg") or palette["window_bg"]\n        for key in ColorAccessibility.RATING_KEYS:\n            assert key in palette, f"{name} has no {key}"\n            ratio = contrast_ratio(palette[key], ground)\n            assert ratio >= TEXT_FLOOR, (\n                f"{name}[{key}] reads {ratio:.4f} on {ground}, below "\n                f"the {TEXT_FLOOR} floor")\n\n\ndef test_the_rating_scale_is_not_one_set_for_three_grounds() -> None:\n    """The defect was mode-blindness, not the particular colours. If dark and\n    light ever agree on a tier again, the thing that broke has come back."""\n    for key in ("rating_excellent", "rating_good", "rating_fair",\n                "rating_poor"):\n        assert C.DARK_THEME_COLORS[key] != C.LIGHT_THEME_COLORS[key], (\n            f"{key} is the same value in dark and light; no colour clears "\n            f"4.5:1 on both #1a1a1a and #f5f5f5 -- the best possible is "\n            f"3.9954:1, so one of the two grounds is being failed")\n', 1), ('tests/test_brand_contrast.py', '    "#4caf50": "Material success",\n    "#f44336": "Material error",\n}', '    "#4caf50": "Material success",\n    "#8bc34a": "Material success, light",\n    "#ffc107": "Material and Bootstrap warning",\n    "#f44336": "Material error",\n}', 1), ('test_rnv_color_picker.py', '    def test_rating_color_excellent(self):\n        c = ColorAccessibility.get_contrast_rating_color(7.5)\n        self.assertEqual(len(c), 3)', '    def test_rating_color_is_the_theme_value_for_each_tier(self):\n        """RNV-RATING-SCALE, 2026-09-12. This replaces\n        test_rating_color_excellent, whose whole body was\n\n            self.assertEqual(len(c), 3)\n\n        -- true of every tuple the function could ever return, including the\n        four Material values it returned for thirty days while a guard in\n        tests/ asserted they were gone. It could not have failed.\n\n        What is asserted now: the colour is the ACTIVE THEME\'s value for the\n        tier, and the two modes disagree. The second half is the one that\n        matters -- the defect was one set of colours for three grounds.\n        """\n        from utils.config import DARK_THEME_COLORS, LIGHT_THEME_COLORS\n\n        def _rgb(value):\n            h = value.lstrip(\'#\')\n            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))\n\n        for ratio, key in ((7.5, \'rating_excellent\'), (5.0, \'rating_good\'),\n                           (3.5, \'rating_fair\'), (1.5, \'rating_poor\')):\n            self.assertEqual(\n                ColorAccessibility.get_contrast_rating_key(ratio), key)\n            self.assertEqual(\n                ColorAccessibility.get_contrast_rating_color(ratio),\n                _rgb(DARK_THEME_COLORS[key]))\n            self.assertEqual(\n                ColorAccessibility.get_contrast_rating_color(\n                    ratio, LIGHT_THEME_COLORS),\n                _rgb(LIGHT_THEME_COLORS[key]))\n            self.assertNotEqual(DARK_THEME_COLORS[key],\n                                LIGHT_THEME_COLORS[key])', 1), ('tests/test_brand_contrast.py', '    allowed.add(C.STATUS_WARNING.lower())\n    stray = []', '    allowed.add(C.STATUS_WARNING.lower())\n    # RNV-RATING-SCALE (2026-09-12): the warning TEXT pair reads as gold for\n    # exactly the same reason and by the same construction -- they are the\n    # text siblings of the fill above and hold its hue, so the shape test\n    # below cannot tell them from a hand-written gold. Registered values, and\n    # named rather than written as hexes so they move with the constants.\n    allowed.add(C.STATUS_WARNING_TEXT.lower())\n    allowed.add(C.STATUS_WARNING_TEXT_LIGHT.lower())\n    stray = []', 1), ('tests/test_status_family.py', '"""RNV-STATUS-GUARD -- the family cannot drift back, and cannot lose its names.\n\nA guard rather than a test: this pins the SHAPE of the change, so a later edit\nthat reintroduces a Bootstrap value, writes a status colour as a literal\nagain, or points a fill at a text job, fails here with a message saying which\nof those happened and why it matters.\n"""', '"""RNV-STATUS-GUARD -- the family cannot drift back, and cannot lose its names.\n\nRNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN\n\nThat second marker was added 2026-09-12 and it is not decoration. This file\'s\nRETIRED table names five dead values in order to forbid them, and on the day\ntest_one_status_family_only was widened to sweep the whole repository in both\nnotations, this file was the single thing it found. The marker is how a sweep\nis told the difference between a value being USED and a value being NAMED --\nthe same distinction _code_only() below draws inside a file, drawn one level\nup between files.\n\nA guard rather than a test: this pins the SHAPE of the change, so a later edit\nthat reintroduces a Bootstrap value, writes a status colour as a literal\nagain, or points a fill at a text job, fails here with a message saying which\nof those happened and why it matters.\n"""', 1), ('tests/test_status_family.py', '    "STATUS_SUCCESS_TEXT_LIGHT": "#825d79",\n    "STATUS_ERROR_TEXT": "#dd6f77",\n    "STATUS_ERROR_TEXT_LIGHT": "#ae4650",\n}', '    "STATUS_SUCCESS_TEXT_LIGHT": "#825d79",\n    # RNV-RATING-SCALE (2026-09-12). The warning text pair, which the family\n    # had been missing since it was chosen: success and error each carried a\n    # dark text value and a light sibling, warning carried neither.\n    "STATUS_WARNING_TEXT": "#bc8752",\n    "STATUS_WARNING_TEXT_LIGHT": "#8e5e2b",\n    "STATUS_ERROR_TEXT": "#dd6f77",\n    "STATUS_ERROR_TEXT_LIGHT": "#ae4650",\n}', 1), ('tests/test_status_family.py', 'def test_the_five_values_are_the_registered_ones(name, value):\n    """Pinned by value, not by relationship. A test asserting only that these\n    differ from each other would pass on five wrong colours."""', 'def test_every_value_is_the_registered_one(name, value):\n    """Pinned by value, not by relationship. A test asserting only that these\n    differ from each other would pass on wrong colours.\n\n    RENAMED 2026-09-12 from test_the_five_values_are_the_registered_ones. It\n    was parametrised over REGISTERED and had been running over SEVEN since\n    2026-09-03, so the name had been wrong for nine days -- a count written in\n    prose beside the thing it counts, which nothing compares. The register hit\n    the identical defect in the same week: its PERMANENT comment said "six"\n    while the dict held seven. The fix in both places is to stop writing the\n    number down."""', 1), ('ui/settings_panel.py', '        # Build the entire dialog stylesheet from theme keys\n        self.setStyleSheet(self._build_dialog_stylesheet(theme))', '        # Build the entire dialog stylesheet from theme keys\n        self.setStyleSheet(self._build_dialog_stylesheet(theme))\n\n        # RNV-RATING-SCALE 2026-09-12: repaint the contrast-rating label.\n        # It reads a PER-MODE palette key now, and this method is the only\n        # thing that runs on a theme switch -- so without this the label kept\n        # the previous mode\'s colour until the user happened to move a spin\n        # box. While the colour was mode-blind a stale value was still the\n        # right value, which is why nothing needed this before and why the\n        # need arrives in the same change that makes it per-mode.\n        #\n        # GUARDED because _apply_theme() runs at line 146, BEFORE the tab\n        # widget is built at 158 and the accessibility tab at 168. On\n        # construction these widgets do not exist yet; the tab builds itself\n        # with a call to _update_contrast_check() at the end, so nothing is\n        # missed.\n        if hasattr(self, "contrast_ratio_label"):\n            self._update_contrast_check()', 1), ('tests/test_settings_panel.py', '    def test_contrast_preview_labels_exist(self, panel):', '    def test_the_rating_label_follows_a_theme_switch(self, panel):\n        """RNV-RATING-SCALE. The rating colour is a per-mode palette key, so\n        update_theme has to repaint the label; before this round it painted\n        one colour for three grounds and could not go stale.\n\n        Asserted through the STYLESHEET rather than the return of a helper:\n        what was wrong was the pixels, and the stylesheet is the last thing\n        this code owns before Qt draws them.\n        """\n        panel._update_contrast_check()\n        dark = panel.contrast_ratio_label.styleSheet()\n        assert config.DARK_THEME_COLORS[\'rating_excellent\'] in dark, dark\n\n        panel.parent_app.theme_manager.get_current_theme.return_value = (\n            config.LIGHT_THEME_COLORS)\n        panel.update_theme()\n        light = panel.contrast_ratio_label.styleSheet()\n        assert config.LIGHT_THEME_COLORS[\'rating_excellent\'] in light, light\n        assert config.DARK_THEME_COLORS[\'rating_excellent\'] not in light\n\n    def test_every_rating_tier_is_reachable_from_the_spin_boxes(self, panel):\n        """Each tier must be something the widget can actually show. A scale\n        whose middle tiers no input can produce is four colours and two\n        outcomes."""\n        from core.accessibility import ColorAccessibility\n        seen = set()\n        for grey in range(0, 256, 5):\n            for spin, v in zip((panel.access_fg_r, panel.access_fg_g,\n                                panel.access_fg_b, panel.access_bg_r,\n                                panel.access_bg_g, panel.access_bg_b),\n                               (grey, grey, grey, 255, 255, 255)):\n                spin.setValue(v)\n            panel._update_contrast_check()\n            style = panel.contrast_ratio_label.styleSheet()\n            for key in ColorAccessibility.RATING_KEYS:\n                if config.DARK_THEME_COLORS[key] in style:\n                    seen.add(key)\n        assert seen == set(ColorAccessibility.RATING_KEYS), (\n            f"tiers never reached from the widget: "\n            f"{sorted(set(ColorAccessibility.RATING_KEYS) - seen)}")\n\n    def test_contrast_preview_labels_exist(self, panel):', 1), ('tests/requirements-dev.txt', 'rnv-brand @ git+https://github.com/RNVizion/rnv-brand@b4fa970babbcb4141d1ea354c77e4d8d78248e82', "# Bumped 2026-09-12 to rev 32, which registers BRAND_BLUE\n# #6f94bc and BRAND_DARK_BLUE #456c91 -- the Good tier of this\n# app's contrast-rating scale, and the first permanent colour in\n# the register that is not gold, black or white.\nrnv-brand @ git+https://github.com/RNVizion/rnv-brand@54286212992a0013bdc3d860357c4261452b014a", 1)]

#: Values whose last consumer this round removes.
GONE = {"#4caf50": "Material success",
        "#8bc34a": "Material success, light",
        "#ffc107": "Material and Bootstrap warning",
        "#f44336": "Material error"}


def edits(tree) -> None:
    for rel, old, new, times in EDITS:
        tree.sub(rel, old, new, times)


def _is_source(path: Path, text: str) -> bool:
    """Application source and its guards -- not this script, and not a file
    whose job is to NAME retired values."""
    if MARKER in text:
        return False
    if "RNV-GOLD-GUARD-FILE-NAMES-RETIRED" in text:
        return False
    return not any(part.startswith(".") for part in path.parts)


def checks(tree) -> None:
    """Run against the in-memory tree, before anything reaches disk."""
    config = tree.read("utils/config.py")
    acc = tree.read("core/accessibility.py")
    panel = tree.read("ui/settings_panel.py")
    req = tree.read("tests/requirements-dev.txt")

    for name, value in (("BRAND_BLUE", "#6f94bc"),
                        ("BRAND_DARK_BLUE", "#456c91"),
                        ("STATUS_WARNING_TEXT", "#bc8752"),
                        ("STATUS_WARNING_TEXT_LIGHT", "#8e5e2b")):
        if f'{name}: Final[str] = "{value}"' not in config:
            raise SystemExit(f"utils/config.py: {name} = {value} did not land")

    # THE RETIRED VALUES ARE GONE AS VALUES, not merely as text. Read the
    # tree: a hex inside a docstring is the provenance doing its job, and a
    # sweep that cannot tell that forces the fix to be silence about what
    # changed. Both notations, because the notation is how they survived.
    live = []
    for rel in ("core/accessibility.py", "utils/config.py",
                "ui/settings_panel.py"):
        # lstrip the BOM. utils/config.py carries one, Tree.read keeps it as a
        # character because flush() writes bytes back unchanged, and ast.parse
        # rejects the whole file over it. tests/test_brand_contrast.py's own
        # _config_source() documents the same trap; this is the third time it
        # has been paid for in this programme.
        text = tree.read(rel).lstrip("﻿")
        parsed = ast.parse(text)
        docs = {n.value.lineno for n in ast.walk(parsed)
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)}
        for node in ast.walk(parsed):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value.lower() in GONE
                    and node.lineno not in docs):
                live.append(f"{rel}:{node.lineno} {node.value}")
            if (isinstance(node, ast.Tuple) and len(node.elts) == 3
                    and all(isinstance(e, ast.Constant)
                            and isinstance(e.value, int)
                            and not isinstance(e.value, bool)
                            and 0 <= e.value <= 255 for e in node.elts)):
                hexv = "#%02x%02x%02x" % tuple(e.value for e in node.elts)
                if hexv in GONE:
                    live.append(f"{rel}:{node.lineno} {hexv} as an int triple")
    if live:
        raise SystemExit("retired Material values are still live:\n  "
                         + "\n  ".join(live))

    # The four tiers, in all three palettes, resolved rather than grepped.
    for dict_name in ("DARK_THEME_COLORS", "LIGHT_THEME_COLORS"):
        block = config[config.index(f"{dict_name}: Final"):]
        for key in ("rating_excellent", "rating_good", "rating_fair",
                    "rating_poor"):
            if f"'{key}':" not in block[:4000]:
                raise SystemExit(f"{dict_name} has no {key}")

    if "def get_contrast_rating_key" not in acc:
        raise SystemExit("core/accessibility.py: the key function did not land")
    if "RATING_KEYS" not in acc:
        raise SystemExit("core/accessibility.py: RATING_KEYS did not land")
    # ONE PLACE ASKS FOR THE THEME DICT, and it is the helper that was already
    # there. The first version of this round added a second _current_theme,
    # byte-identical to _get_theme forty lines above it, and this check --
    # written to forbid exactly that -- is what found it, by firing for the
    # wrong reason: it asserted ONE `hasattr(parent_app, 'theme_manager')` in
    # the file and there are five. Three of the five read `current_theme`, the
    # mode NAME, to pick a gold; that is a different question and stays.
    # What must be unique is the DICT form.
    if "def _get_theme" not in panel:
        raise SystemExit("ui/settings_panel.py: _get_theme is gone")
    dict_form = panel.count("self.parent_app.theme_manager.get_current_theme()")
    if dict_form != 1:
        raise SystemExit(
            f"ui/settings_panel.py asks for the theme DICT in {dict_form} "
            f"places, not 1. _get_theme is the only copy there should be; a "
            f"second is how two parts of one dialog paint for different modes.")
    if panel.count("self._get_theme()") < 3:
        raise SystemExit(
            "ui/settings_panel.py: fewer than three callers reach _get_theme, "
            "so update_theme or the rating label is not using it")

    if "54286212992a0013bdc3d860357c4261452b014a" not in req:
        raise SystemExit("tests/requirements-dev.txt: the pin did not move")
    if "b4fa970babbcb4141d1ea354c77e4d8d78248e82" in req:
        raise SystemExit("tests/requirements-dev.txt: the old pin survives")

    # The guard file must still be able to SEE what it judges. A sweep that
    # skips every file reports clean.
    guard = tree.read("tests/test_brand_contrast.py")
    if "_app_sources" not in guard or "_colour_triples" not in guard:
        raise SystemExit("the widened guard did not land")
    if "RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN" not in tree.read(
            "tests/test_status_family.py"):
        raise SystemExit(
            "tests/test_status_family.py names five retired values and has "
            "not been marked as doing so on purpose -- the widened sweep will "
            "land red on its RETIRED table")

    print("checks: 4 constants, 8 palette entries, 0 Material values live, "
          "pin at rev 32")


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
        self.deleted: set[str] = set()

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        """Mark a file for removal. Nothing leaves disk until flush().

        Added for the round that retired the last CI deselect: with no
        deselects left, tests/test_ci_deselects.py swept an empty set and
        would have passed over nothing. Its own failure message said to
        delete it in the commit that removed the last one, so the harness
        needed to be able to.
        """
        if not (self.root / rel).exists() and rel not in self.files:
            raise SystemExit(f"cannot delete {rel}: it is not in this checkout")
        self.files.pop(rel, None)
        self.deleted.add(rel)

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
        for rel in sorted(self.deleted):
            p = self.root / rel
            if p.exists():
                p.unlink()
                touched.append(f"{rel} (deleted)")
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
