"""the picker's rulings of 5 October: what nothing called or read goes, the flaky worker test waits, the workflow's actions are at the versions built for Node 24, and the README's test counts cannot go stale

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (e28a49a).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-10-05, items 5, 6, 8, 14 and 18 of the list of 4 October:

  5   "Yes."
  6   "Yes."
  8   "Yes fix it."
  14  "Yes do it."
  18  "Do B."

ITEM 5. The stored preference default_slot_color goes from the settings'
defaults. Nothing read it and no control set it.

ITEM 6. Two cached stylesheet functions that nothing in the application
called go from utils/cache.py: the one for the frame behind the main
buttons, and the one for the close button. With them go the four names only
they read: BRAND_GOLD_PRESSED, BRAND_DARK_GOLD_PRESSED,
IMAGE_BUTTON_FRAME_BG, and IMAGE_BUTTON_FRAME_ALPHA, the alpha that one was
made from. A pressed button in this application paints its palette's
accent, which is the value the two pressed names held, so nothing drawn
moves. The tests that went with them: two in the root suite called the
close-button function to see that it returned a string; two under tests/
held the pressed names equal to the accent; four tables under tests/ lose
the rows that listed the names, and the number of eight-digit values those
tests expect drops from nine to eight.

ONE TEST MOVES ITS EYES. The guard of the ink rule held the decision of
2026-09-02, black text on bright gold and white on dark gold, "ruled, not
measured", by reading two lines of the close-button function: lines that
painted nothing. It reads the palettes now, where that decision paints: the
ink on a pressed dialog button, a selected row, and a pressed menu item or
selected text, in each mode.

ITEM 8. tests/test_workers.py asserted the worker manager's cleanup the
moment the worker's finished signal arrived. The cleanup is a second slot
on that signal and may still be queued. Run alone the test failed 14 times
in 15 on one day and 4 in 30 on the next. It waits for the cleanup itself
now, and for the thread to end: 0 failures in 100 runs. Only the test
moves.

ITEM 14. The workflow used actions/checkout@v4, actions/setup-python@v5
and actions/upload-artifact@v4. Each is built for Node 20, which GitHub
took off its runners on 2026-09-23; since then they are run on Node 24 with
a warning on every job. They move to the first versions built for Node 24:
checkout v5, setup-python v6, upload-artifact v6, the versions the brand
repository moved to on 2026-10-04. Each action's own action.yml was read at
both versions: every input this workflow passes is an input of the newer
one, with the same default.

ITEM 18. The README stated 1,641 tests; pytest collected 1,949. Every count
is a floor now: over 1,800 tests, over 300 in the root suite, over 1,400
under tests/. A floor is the number of test functions the suite defines,
rounded down to the hundred, so the next test leaves it true. The two
counts beside the file tree are dropped, and the runner's banner no longer
counts the root suite.

THE GUARDS. tests/test_nothing_calls_is_gone.py keeps what went from being
written again, and holds every cached stylesheet function to having a
caller in the application; it lists four more that have none, found on the
way and not removed. tests/test_workflow_actions.py holds every action at
its floor. tests/test_readme_test_counts.py holds every count in the README
to a floor, and every floor to the truth.

WHAT ONLY A RUN ON GITHUB SHOWS. That the workflow runs with the newer
actions. The first run after this is committed is that test.
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
SENTINEL = 'RNV-RULINGS-2026-10-05'
SENTINEL_FILE = '.github/workflows/tests.yml'
GUARD = 'tests/test_nothing_calls_is_gone.py'
GUARD_FILES = ['tests/test_nothing_calls_is_gone.py', 'tests/test_workflow_actions.py', 'tests/test_readme_test_counts.py']
ROOT_SUITE = 'test_rnv_color_picker.py'
ACTIONS_GUARD = 'tests/test_workflow_actions.py'
README_GUARD = 'tests/test_readme_test_counts.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_nothing_calls_is_gone.py', 'tests/test_workflow_actions.py', 'tests/test_readme_test_counts.py']
DESCRIPTION = "the picker's rulings of 5 October: what nothing called or read goes, the flaky worker test waits, the workflow's actions are at the versions built for Node 24, and the README's test counts cannot go stale"

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

SHADOWS = {"cache.py", "config.py", "conftest.py", "run_tests.py", "settings_manager.py", "test_rnv_color_picker.py", "test_brand_contrast.py", "test_derived_values.py", "test_ink_rule.py", "test_named_and_used.py", "test_workers.py", "test_nothing_calls_is_gone.py", "test_workflow_actions.py", "test_readme_test_counts.py"}

LEFT_ALONE = ["four more cached stylesheet functions nothing in the application calls: the scroll area's, the scrollbar's, the zoom label's and the colour preview's. Found while removing the two; held by name in the new guard. Removing them is a ruling.", 'white or black on the light gold fill (item 4, still open): this application paints white there, written as a decision on 2026-09-02. The test that holds that decision reads the palettes now; what it holds has not moved.', 'the step that uploads coverage: it names `.coverage` and `.coverage.*`, which are hidden files, and upload-artifact leaves hidden files out unless it is told otherwise (its `include-hidden-files` input, off by default at v4 as it runs today and at v6). So the step uploads nothing, before this round and after it. Whether to keep a copy of the coverage is a ruling.', 'the counts other documents state: TESTING.md. Item 18 ruled the README.', 'the coverage figures printed beside the counts: a coverage figure depends on the platform it was taken on.', "the rulings still open on the list of 5 October: white or black text on the light gold fill (item 4), the Find and Replace dialog's clipped buttons (12), the transformer's line-number editor (7) and its Export tab (9). Nothing here touches them."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('utils/settings_manager.py',
             '                "default_slot_weight": 50,\n                "default_slot_color": [200, 200, 200],  # RGB\n                "max_color_slots": 12,\n',
             '                "default_slot_weight": 50,\n                "max_color_slots": 12,\n')
    tree.sub('tests/test_named_and_used.py',
             '    ("ui/color_swatch_widget.py", "(0, 0, 0)"):\n        "a swatch built with no colour given, and its hue, saturation and lightness: defaults, as data",\n    ("utils/settings_manager.py", "[200, 200, 200]"):\n        "the stored default of a preference, default_slot_color: data in the settings file, not the look",\n}\n',
             '    ("ui/color_swatch_widget.py", "(0, 0, 0)"):\n        "a swatch built with no colour given, and its hue, saturation and lightness: defaults, as data",\n}\n')
    tree.sub('utils/cache.py',
             'from utils.config import (\n    BRAND_GOLD, BRAND_DARK_GOLD,\n    BRAND_GOLD_HOVER, BRAND_GOLD_PRESSED,\n    BRAND_DARK_GOLD_HOVER, BRAND_DARK_GOLD_PRESSED,\n    TRUE_BLACK, WHITE,\n    swatch_edge, contrast_ink_rgb,\n    STATUS_ERROR_BG,\n    IMAGE_MENU_BG, IMAGE_BUTTON_FRAME_BG,\n)\n',
             'from utils.config import (\n    BRAND_GOLD,\n    TRUE_BLACK, WHITE,\n    swatch_edge, contrast_ink_rgb,\n    STATUS_ERROR_BG,\n    IMAGE_MENU_BG,\n)\n')
    tree.sub('utils/cache.py',
             '    @classmethod\n    def get_button_frame_stylesheet(\n        cls, \n        theme_name: str, \n        theme: dict, \n        is_image_mode: bool\n    ) -> str:\n        """Get cached button frame stylesheet."""\n        key = (theme_name, is_image_mode, \'button_frame\')\n        \n        if key not in cls._cache:\n            if is_image_mode:\n                cls._cache[key] = f"""\n                    QFrame {{\n                        background-color: {IMAGE_BUTTON_FRAME_BG};\n                        border-radius: 8px;\n                    }}\n                """\n            else:\n                cls._cache[key] = f"""\n                    QFrame {{\n                        background-color: {theme[\'window_bg\']};\n                        border-radius: 8px;\n                    }}\n                """\n        \n        return cls._cache[key]\n    \n    @classmethod\n    def get_scroll_area_stylesheet(',
             '    @classmethod\n    def get_scroll_area_stylesheet(')
    tree.sub('utils/cache.py',
             '    @classmethod\n    def get_close_button_stylesheet(cls, is_dark: bool = True) -> str:\n        """Get cached close/OK button stylesheet (gold themed, theme-aware)."""\n        key = (\'static\', \'close_button\', is_dark)\n        \n        if key not in cls._cache:\n            if is_dark:\n                bg      = BRAND_GOLD\n                # RNV-INK-RULE: a brand decision, not a measurement. Bright\n                # gold is a light ground and takes black; dark gold takes\n                # white. Measured, dark gold is 4.54 white against 4.62 black\n                # -- a coin flip that would have moved a pixel for nothing.\n                fg      = TRUE_BLACK\n                hover   = BRAND_GOLD_HOVER\n                pressed = BRAND_GOLD_PRESSED\n            else:\n                bg      = BRAND_DARK_GOLD\n                fg      = WHITE\n                hover   = BRAND_DARK_GOLD_HOVER\n                pressed = BRAND_DARK_GOLD_PRESSED\n            cls._cache[key] = f"""\n                QPushButton {{\n                    background-color: {bg};\n                    color: {fg};\n                    border: none;\n                    padding: 8px 24px;\n                    border-radius: 4px;\n                    font-weight: bold;\n                    min-width: 80px;\n                }}\n                QPushButton:hover {{\n                    background-color: {hover};\n                }}\n                QPushButton:pressed {{\n                    background-color: {pressed};\n                }}\n            """\n        \n        return cls._cache[key]\n    \n    @classmethod\n    def get_header_stylesheet(',
             '    @classmethod\n    def get_header_stylesheet(')
    tree.sub('utils/config.py',
             'BRAND_DARK_GOLD_PRESSED: Final[str] = BRAND_DARK_GOLD\n"""Light-mode pressed. It IS the accent. Read by the cached close-button\nsheet alone since the palettes\' `accent_pressed` went (2026-10-04).\n\nTwo reasons, and either alone would be enough. The brand runs two golds\nper mode and light spends its second on BRAND_DARK_GOLD_DEEP. And\ndarkening past BRAND_DARK_GOLD drops black-on-gold under the floor, which\nwould force white text and break the register\'s text-on-gold rule.\n"""\n\nBRAND_GOLD_HOVER: Final[str] = lighten(BRAND_GOLD, 13)',
             'BRAND_GOLD_HOVER: Final[str] = lighten(BRAND_GOLD, 13)')
    tree.sub('utils/config.py',
             'BRAND_GOLD_PRESSED: Final[str] = BRAND_GOLD\n"""Dark-mode pressed. It IS the accent, mirroring light mode exactly.\n\nThe brand runs TWO golds per mode -- the registered one and one derived\nfrom it -- and no more. Dark spends its second on hover, so pressed\nreturns to the accent rather than claiming a third.\n\nThe interaction still reads: rest sits at the accent, hover lifts away\nfrom the dark ground, pressed drops back to rest. That is the same shape\nlight uses, where hover deepens away from the light ground and pressed\nreturns. The hand-written #b7a480 it replaces was a third gold serving\none key.\n"""\n\nBRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)\n',
             'BRAND_GOLD_RGB: Final[tuple[int, int, int]] = _to_rgb(BRAND_GOLD)\n')
    tree.sub('utils/config.py',
             'IMAGE_MENU_ALPHA: Final[int] = 0xC8\n"""200. The context menu\'s ground in image mode (TRUE_BLACK)."""\n\nIMAGE_BUTTON_FRAME_ALPHA: Final[int] = 0x64\n"""100. The frame behind the main buttons in image mode (TRUE_BLACK)."""\n\n',
             'IMAGE_MENU_ALPHA: Final[int] = 0xC8\n"""200. The context menu\'s ground in image mode (TRUE_BLACK)."""\n\n')
    tree.sub('utils/config.py',
             '# Image-mode grounds painted by stylesheets that are not built from\n# IMAGE_MODE_COLORS -- the context menu, three copies of it, and the\n# frame behind the main buttons. Named here so they derive with the rest.\nIMAGE_MENU_BG: Final[str] = translucent(TRUE_BLACK, IMAGE_MENU_ALPHA)\nIMAGE_BUTTON_FRAME_BG: Final[str] = translucent(TRUE_BLACK, IMAGE_BUTTON_FRAME_ALPHA)\n',
             "# The image-mode ground painted by stylesheets that are not built from\n# IMAGE_MODE_COLORS: the context menu, three copies of it. Named here so\n# it derives with the rest.\n# RNV-RULINGS-2026-10-05, item 6: the frame behind the main buttons had a name\n# here too, read only by a cached stylesheet function nothing called. The\n# function, the name and its alpha are gone, and so are the two pressed\n# golds only the other such function read. A pressed button paints its\n# palette's accent, which is what those two names held.\nIMAGE_MENU_BG: Final[str] = translucent(TRUE_BLACK, IMAGE_MENU_ALPHA)\n")
    tree.sub('utils/config.py',
             "    'BRAND_GOLD_HOVER',\n    'BRAND_GOLD_PRESSED',\n    'BRAND_DARK_GOLD_HOVER',\n    'BRAND_DARK_GOLD_PRESSED',\n",
             "    'BRAND_GOLD_HOVER',\n    'BRAND_DARK_GOLD_HOVER',\n")
    tree.sub('utils/config.py',
             "    'IMAGE_MENU_BG',\n    'IMAGE_BUTTON_FRAME_BG',\n",
             "    'IMAGE_MENU_BG',\n")
    tree.sub('test_rnv_color_picker.py',
             '    def test_close_button_stylesheet_dark(self):\n        ss = StylesheetCache.get_close_button_stylesheet(is_dark=True)\n        self.assertIsInstance(ss, str)\n\n    def test_close_button_stylesheet_light(self):\n        ss = StylesheetCache.get_close_button_stylesheet(is_dark=False)\n        self.assertIsInstance(ss, str)\n\n',
             '')
    tree.sub('tests/test_brand_contrast.py',
             '    "BRAND_DARK_GOLD_HOVER",\n    "BRAND_DARK_GOLD_PRESSED",\n    "BRAND_GOLD_HOVER",\n    "BRAND_GOLD_PRESSED",\n    "BRAND_GOLD_RGB",\n',
             '    "BRAND_DARK_GOLD_HOVER",\n    "BRAND_GOLD_HOVER",\n    "BRAND_GOLD_RGB",\n')
    tree.sub('tests/test_brand_contrast.py',
             'def test_dark_pressed_is_the_accent_itself() -> None:\n    """Mirrors light. Pressed returns to rest rather than claiming a third\n    gold -- see test_two_golds_per_mode below, which is the rule this\n    serves."""\n    assert C.BRAND_GOLD_PRESSED == C.BRAND_GOLD\n\n\ndef test_light_pressed_is_the_accent_itself() -> None:\n    """There is nowhere darker for a light-mode pressed state to go.\n\n    Darkening past BRAND_DARK_GOLD drops black-on-gold under the floor,\n    which would force white text and break the register\'s text-on-gold\n    rule. So pressed IS the accent, deliberately.\n    """\n    assert C.BRAND_DARK_GOLD_PRESSED == C.BRAND_DARK_GOLD\n\n\ndef test_light_hover_moves_away_from_its_ground() -> None:\n',
             'def test_light_hover_moves_away_from_its_ground() -> None:\n')
    tree.sub('tests/test_brand_contrast.py',
             '             ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",\n              "BRAND_GOLD_HOVER", "BRAND_GOLD_PRESSED",\n              "BRAND_DARK_GOLD_HOVER", "BRAND_DARK_GOLD_PRESSED")}\n',
             '             ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",\n              "BRAND_GOLD_HOVER", "BRAND_DARK_GOLD_HOVER")}\n')
    tree.sub('tests/test_derived_values.py',
             '    "IMAGE_MENU_ALPHA": 0xC8,\n    "IMAGE_BUTTON_FRAME_ALPHA": 0x64,\n}\n',
             '    "IMAGE_MENU_ALPHA": 0xC8,\n}\n')
    tree.sub('tests/test_derived_values.py',
             '    "IMAGE_MENU_BG": ("TRUE_BLACK", 0xC8),\n    "IMAGE_BUTTON_FRAME_BG": ("TRUE_BLACK", 0x64),\n',
             '    "IMAGE_MENU_BG": ("TRUE_BLACK", 0xC8),\n')
    tree.sub('tests/test_derived_values.py',
             "#: 10 until RNV-NAMED-AND-USED (2026-10-04), when image mode's unread\n#: scroll_area_bg override went.\nLOWER8_FLOOR = 9\n",
             "#: 10 until RNV-NAMED-AND-USED (2026-10-04), when image mode's unread\n#: scroll_area_bg override went. 9 until 2026-10-05, when the frame colour\n#: only an uncalled stylesheet function read went.\nLOWER8_FLOOR = 8\n")
    tree.sub('run_tests.py',
             '  Suite 1 — test_rnv_color_picker.py    (400 unittest tests, ~4s)\n',
             '  Suite 1 — test_rnv_color_picker.py    (the unittest suite, ~4s)\n')
    tree.sub('tests/test_workers.py',
             '        m = WorkerManager()\n        w = ColorExtractionWorker(small_pixels)\n        with qtbot.waitSignal(w.finished, timeout=5000):\n            m.start_worker(w)\n        # After finished, the auto-cleanup should have removed it\n        assert w not in m._active_workers\n',
             "        m = WorkerManager()\n        w = ColorExtractionWorker(small_pixels)\n        with qtbot.waitSignal(w.finished, timeout=5000):\n            m.start_worker(w)\n        # RNV-RULINGS-2026-10-05, item 8. The manager's cleanup is a second slot on\n        # the same signal, queued to this thread like the one waitSignal\n        # waits on. The wait ends on the first to arrive, and the cleanup\n        # may still be in the queue. Asserted there and then, this failed\n        # when run alone: 14 times in 15 one day, 4 in 30 the next. So it\n        # waits for the cleanup itself: 0 in 100.\n        qtbot.waitUntil(lambda: w not in m._active_workers, timeout=5000)\n        # After finished, the auto-cleanup has removed it\n        assert w not in m._active_workers\n        # and the thread has ended before the worker goes out of scope\n        assert w.wait(5000)\n")
    tree.sub('tests/test_ink_rule.py',
             'def test_the_brand_golds_are_ruled_not_measured():\n    """The close button keeps black on bright gold and white on dark gold.\n\n    Dark gold measures 4.54 white against 4.62 black -- close enough that the\n    arithmetic would flip it, which is exactly why the two call sites in\n    utils/cache.py name the colour outright instead of asking the rule. This\n    test states the margin so that a later \'cleanup\' that routes them through\n    contrast_ink() has to argue with a number."""\n    white = config.contrast_ratio(config.BRAND_DARK_GOLD, config.WHITE)\n    black = config.contrast_ratio(config.BRAND_DARK_GOLD, config.TRUE_BLACK)\n    assert abs(white - black) < 0.15, (\n        "the golds moved; re-take the ruling rather than the measurement")\n    src = (ROOT / "utils" / "cache.py").read_text(encoding="utf-8-sig")\n    assert "fg      = TRUE_BLACK" in src and "fg      = WHITE" in src, (\n        "the gold button inks are no longer written as a decision")\n\n\n',
             'def test_the_brand_golds_are_ruled_not_measured():\n    """Text on the gold fill keeps black on bright gold and white on dark gold.\n\n    Dark gold measures 4.54 white against 4.62 black -- close enough that the\n    arithmetic would flip it, which is exactly why the palettes name the\n    colour outright instead of asking the rule. This test states the margin\n    so that a later \'cleanup\' that routes them through contrast_ink() has to\n    argue with a number.\n\n    RNV-RULINGS-2026-10-05, item 6. Until then this read two lines of the\n    cached close-button stylesheet, a function nothing in the application\n    called, and which is gone (tests/test_nothing_calls_is_gone.py names\n    it). The decision is held where it paints: the ink each palette puts on\n    its gold fill, for a pressed dialog button, a selected row, and a\n    pressed menu item or selected text."""\n    white = config.contrast_ratio(config.BRAND_DARK_GOLD, config.WHITE)\n    black = config.contrast_ratio(config.BRAND_DARK_GOLD, config.TRUE_BLACK)\n    assert abs(white - black) < 0.15, (\n        "the golds moved; re-take the ruling rather than the measurement")\n    on_gold = (("dialog_btn_pressed_bg", "dialog_btn_pressed_text"),\n               ("list_selected_bg", "list_selected_text"),\n               ("selected_bg", "text_on_accent"))\n    for palette, gold, ink in ((config.DARK_THEME_COLORS, config.BRAND_GOLD, config.TRUE_BLACK),\n                               (config.LIGHT_THEME_COLORS, config.BRAND_DARK_GOLD, config.WHITE)):\n        for ground, text in on_gold:\n            assert palette[ground] == gold, (\n                f"{palette[\'name\']}: {ground} is no longer the gold fill")\n            assert palette[text] == ink, (\n                f"{palette[\'name\']}: {text} is {palette[text]}: the gold fill\'s ink is no "\n                f"longer written as a decision")\n\n\n')
    tree.sub('.github/workflows/tests.yml',
             'uses: actions/checkout@v4\n',
             'uses: actions/checkout@v5\n')
    tree.sub('.github/workflows/tests.yml',
             'uses: actions/setup-python@v5\n',
             'uses: actions/setup-python@v6\n')
    tree.sub('.github/workflows/tests.yml',
             'uses: actions/upload-artifact@v4\n',
             'uses: actions/upload-artifact@v6\n')
    tree.sub('.github/workflows/tests.yml',
             '\njobs:\n',
             '\n# RNV-RULINGS-2026-10-05, item 14. Each action below is at the first version\n# built for Node 24: checkout v5, setup-python v6 and upload-artifact v6.\n# GitHub took Node 20 off its runners on 2026-09-23, and ran the versions\n# before these on Node 24 with a warning. tests/test_workflow_actions.py\n# holds the floor.\njobs:\n')
    tree.sub('README.md',
             '![Tests](https://img.shields.io/badge/tests-1641%20passing-brightgreen)\n',
             '![Tests](https://img.shields.io/badge/tests-1800%2B%20passing-brightgreen)\n')
    tree.sub('README.md',
             '- **86% branch coverage** across 1,641 tests (unittest + pytest with',
             '- **86% branch coverage** across over 1,800 tests (unittest + pytest with')
    tree.sub('README.md',
             '├── tests/                        # 1,241 pytest tests (test_*.py)\n',
             '├── tests/                        # pytest tests (test_*.py)\n')
    tree.sub('README.md',
             '└── test_rnv_color_picker.py      # 400 unittest tests (legacy harness)\n',
             '└── test_rnv_color_picker.py      # unittest tests (legacy harness)\n')
    tree.sub('README.md',
             'The project carries 1,641 tests across two harnesses:\n',
             'The project carries over 1,800 tests across two harnesses:\n')
    tree.sub('README.md',
             '| `unittest` | 400 | Legacy regression suite |\n',
             '| `unittest` | over 300 | Legacy regression suite |\n')
    tree.sub('README.md',
             '| `pytest` | 1,241 | Modern suite',
             '| `pytest` | over 1,400 | Modern suite')
    tree.sub('README.md',
             '| **Total** | **1,641** | **86% TOTAL coverage**',
             '| **Total** | **over 1,800** | **86% TOTAL coverage**')
    tree.sub('README.md',
             '  Built with PyQt6 · 1,641 tests · 86% coverage\n',
             '  Built with PyQt6 · over 1,800 tests · 86% coverage\n')
    if (tree.root / 'tests/test_nothing_calls_is_gone.py').exists():
        raise Stop('tests/test_nothing_calls_is_gone.py' + ' exists already: this round creates it', EXIT_CANNOT_RUN)
    tree.write('tests/test_nothing_calls_is_gone.py', '"""What nothing called is gone, and stays gone.\n\nRNV-RULINGS-2026-10-05, items 5 and 6. Ruled 2026-10-05: "Yes." to each.\n\nWHAT WENT.\n\nItem 6. Two cached stylesheet functions that nothing in the application\ncalled: StylesheetCache.get_button_frame_stylesheet() and\nStylesheetCache.get_close_button_stylesheet(). The root suite called the\nsecond, twice, to see that it returned a string; those two tests went with\nit. So did what only those functions read: BRAND_GOLD_PRESSED and\nBRAND_DARK_GOLD_PRESSED, IMAGE_BUTTON_FRAME_BG, and the alpha that one was\nmade from, IMAGE_BUTTON_FRAME_ALPHA. A pressed button in this application\npaints its palette\'s accent, which is the value the two pressed names held.\n\nItem 5. The stored preference default_slot_color. It sat in the settings\'\ndefaults, nothing read it, and no control set it.\n\nWHAT THIS GUARD HOLDS.\n\n1. None of those names is written in the repository\'s Python again: not in\n   the application, not in a test. This file mentions them in order to\n   forbid them, and is the one file the sweep leaves out.\n2. The colour module and the cache do not define them.\n3. Every cached stylesheet function is called by the application, itself or\n   through another that is. A test that calls one does not make it used.\n   HELD lists four more that nothing calls, found while removing the two; a\n   ruling is asked on them. A fifth is a failure, and so is a held one that\n   has gained a caller.\n4. The sweeps are looking.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nCACHE = "utils/cache.py"\n\n#: What went, and may not come back.\nFUNCTIONS_GONE = ("get_button_frame_stylesheet", "get_close_button_stylesheet")\nCOLOURS_GONE = ("BRAND_GOLD_PRESSED", "BRAND_DARK_GOLD_PRESSED", "IMAGE_BUTTON_FRAME_BG",\n                "IMAGE_BUTTON_FRAME_ALPHA")\nPREFERENCE_GONE = "default_slot_color"\nGONE = FUNCTIONS_GONE + COLOURS_GONE + (PREFERENCE_GONE,)\n\n#: Cached stylesheet functions nothing in the application calls, found on\n#: 2026-10-05 and not removed: only the two above were ruled. name -> why it\n#: is here.\nHELD = {\n    "get_scroll_area_stylesheet": "nothing calls it",\n    "get_scrollbar_stylesheet": "called only by get_scroll_area_stylesheet(), which nothing calls; "\n                                "the root suite calls it to see that it returns a string",\n    "get_zoom_label_stylesheet": "nothing calls it",\n    "get_color_preview_stylesheet": "nothing calls it; the root suite calls it to see that it holds the hex",\n}\n\n#: The one file that names what went, to forbid it.\nMENTION_ONLY = {pathlib.Path(__file__).name}\nDELIVERY_MARK = "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP"\nSKIP_DIRS = {"build", "dist", "__pycache__", "venv", "env", "node_modules", "htmlcov"}\nAPP_SKIP_DIRS = SKIP_DIRS | {"tests", "docs", "resources", "scripts", "snapshots"}\n\n#: Fewer Python files than this and a walk has gone blind.\nMIN_PYTHON = 60\nMIN_APP = 30\n\n\ndef _python(app_only: bool = False):\n    """(repository-relative path, text) of the repository\'s Python: all of\n    it, or the application\'s alone (no tests, no runner, no delivery script)."""\n    skip = APP_SKIP_DIRS if app_only else SKIP_DIRS\n    for path in sorted(ROOT.rglob("*.py")):\n        rel = path.relative_to(ROOT).as_posix()\n        parts = rel.split("/")\n        if any(part in skip or part.startswith(".") for part in parts[:-1]):\n            continue\n        text = path.read_text(encoding="utf-8-sig", errors="replace")\n        if len(parts) == 1 and DELIVERY_MARK in text:\n            continue                                  # a delivery script names what it retires\n        if app_only and len(parts) == 1 and parts[0].startswith(("test_", "conftest", "run_tests")):\n            continue\n        yield rel, text\n\n\ndef _named(pairs) -> list:\n    found = []\n    for rel, text in pairs:\n        if pathlib.PurePosixPath(rel).name in MENTION_ONLY:\n            continue\n        for number, line in enumerate(text.splitlines(), 1):\n            for name in GONE:\n                if name in line:\n                    found.append(f"{rel}:{number}: {name}")\n    return found\n\n\ndef _cached_sheet_functions(source: str) -> dict:\n    """StylesheetCache\'s get_*_stylesheet methods: name -> the other such\n    methods its body reaches for."""\n    tree = ast.parse(source)\n    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "StylesheetCache")\n    methods = {n.name: n for n in cls.body\n               if isinstance(n, ast.FunctionDef) and n.name.startswith("get_") and n.name.endswith("_stylesheet")}\n    return {name: {a.attr for a in ast.walk(node) if isinstance(a, ast.Attribute) and a.attr in methods} - {name}\n            for name, node in methods.items()}\n\n\ndef _called_from_outside(names: set, pairs) -> set:\n    """Which of `names` the application reaches for, outside StylesheetCache\'s own methods."""\n    called = set()\n    for rel, text in pairs:\n        tree = ast.parse(text)\n        inside = set()\n        if rel == CACHE:\n            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "StylesheetCache")\n            inside = {id(a) for a in ast.walk(cls)}\n        for node in ast.walk(tree):\n            if isinstance(node, ast.Attribute) and node.attr in names and id(node) not in inside:\n                called.add(node.attr)\n    return called\n\n\ndef _uncalled(source: str, pairs) -> set:\n    reaches = _cached_sheet_functions(source)\n    live = _called_from_outside(set(reaches), pairs)\n    grew = True\n    while grew:                                       # what a called function calls is called too\n        more = {callee for name in live for callee in reaches[name]} - live\n        live |= more\n        grew = bool(more)\n    return set(reaches) - live\n\n\ndef test_what_went_is_not_written_again():\n    found = _named(_python())\n    assert not found, (\n        "a name removed on 2026-10-05 is written again:\\n  " + "\\n  ".join(found)\n        + "\\nThe two functions were called by nothing, the colours were read only by them, and the "\n          "preference was read by nothing. If one is wanted, it needs a caller or a reader, and a ruling.")\n\n\ndef test_the_colour_module_and_the_cache_do_not_define_it():\n    from utils import cache, config\n    for name in COLOURS_GONE:\n        assert not hasattr(config, name), f"utils.config defines {name} again"\n        assert name not in config.__all__, f"utils.config exports {name}"\n        assert not hasattr(cache, name), f"utils.cache imports {name} again"\n    for name in FUNCTIONS_GONE:\n        assert not hasattr(cache.StylesheetCache, name), f"StylesheetCache.{name}() is back"\n    from utils.settings_manager import SettingsManager\n    assert PREFERENCE_GONE not in SettingsManager._get_default_settings()["preferences"], \\\n        f"the settings\' defaults store {PREFERENCE_GONE} again"\n\n\ndef test_every_cached_stylesheet_function_is_called():\n    source = (ROOT / CACHE).read_text(encoding="utf-8-sig")\n    uncalled = _uncalled(source, list(_python(app_only=True)))\n    new = sorted(uncalled - set(HELD))\n    assert not new, (\n        f"nothing in the application calls StylesheetCache.{\', .\'.join(n + \'()\' for n in new)}. "\n        f"A sheet nothing asks for paints nothing, and keeps its colours looking used. Call it, or remove it.")\n    stale = sorted(set(HELD) - uncalled)\n    assert not stale, (\n        f"{\', \'.join(stale)}: held as called by nothing, and it is called now, or gone. Take it out of HELD.")\n\n\ndef test_the_sweeps_are_looking():\n    everything, application = list(_python()), list(_python(app_only=True))\n    assert len(everything) >= MIN_PYTHON and len(application) >= MIN_APP, (len(everything), len(application))\n    paths = {rel for rel, _ in everything}\n    for must in (CACHE, "utils/config.py", "utils/settings_manager.py", "test_rnv_color_picker.py",\n                 "tests/test_brand_contrast.py"):\n        assert must in paths, f"the sweep is not reading {must}"\n    assert not any(rel.startswith("tests/") or rel.startswith("test_") for rel, _ in application), \\\n        "a test is counted as the application: its calls would make a function look used"\n\n    # the name sweep flags a line that names one, and leaves this file out\n    assert _named([("ui/sample.py", "x = StylesheetCache.get_close_button_stylesheet()\\n")]) \\\n        == ["ui/sample.py:1: get_close_button_stylesheet"]\n    assert _named([("tests/" + next(iter(MENTION_ONLY)), "BRAND_GOLD_PRESSED\\n")]) == []\n    assert _named([("tests/other.py", pathlib.Path(__file__).read_text(encoding="utf-8"))]), \\\n        "this file no longer names what went: drop the exemption"\n\n    # the call sweep: called from outside, called only from inside, called by nothing, called by a test\n    sample = ("class StylesheetCache:\\n"\n              "    def get_a_stylesheet(cls):\\n        return cls.get_b_stylesheet()\\n"\n              "    def get_b_stylesheet(cls):\\n        return \'\'\\n"\n              "    def get_c_stylesheet(cls):\\n        return cls.get_d_stylesheet()\\n"\n              "    def get_d_stylesheet(cls):\\n        return \'\'\\n"\n              "    def get_e_stylesheet(cls):\\n        return \'\'\\n")\n    app = [(CACHE, sample), ("ui/window.py", "from utils.cache import StylesheetCache\\n"\n                                             "s = StylesheetCache.get_a_stylesheet()\\n")]\n    assert _uncalled(sample, app) == {"get_c_stylesheet", "get_d_stylesheet", "get_e_stylesheet"}\n')
    if (tree.root / 'tests/test_workflow_actions.py').exists():
        raise Stop('tests/test_workflow_actions.py' + ' exists already: this round creates it', EXIT_CANNOT_RUN)
    tree.write('tests/test_workflow_actions.py', '"""Every action the workflows use is at a version built for the Node the runners have.\n\nRNV-RULINGS-2026-10-05, item 14. Ruled 2026-10-05: "Yes do it".\n\nWHAT WAS THERE. actions/checkout@v4, actions/setup-python@v5 and, where a\nworkflow keeps something from the run, actions/upload-artifact@v4. Each of\nthose declares `using: node20` in its own action.yml. GitHub took Node 20\noff its hosted runners on 2026-09-23. Since then an action that declares it\nis run on Node 24 instead, and the job carries a warning that names it.\n\nWHAT IS THERE NOW. The first version of each that declares node24: checkout\nv5, setup-python v6, upload-artifact v6. They are the versions the brand\nrepository moved its own workflows to on 2026-10-04.\n\nREAD, NOT ASSUMED. Each action\'s action.yml was read at both tags on\n2026-10-05. Every input these workflows pass is an input of the newer\nversion, with the same default and the same `required`. No input the older\nversion had is gone from the newer one.\n\nWHAT THIS GUARD HOLDS.\n\n1. Every `uses:` in every workflow names an action in FLOOR, at that major\n   version or a later one. An action that is not in FLOOR is a new one: read\n   which Node it is built for, then add it.\n2. The reader is looking. It finds the steps of every workflow, in either\n   way YAML writes one, and it flags a version under the floor.\n\nWHAT IT CANNOT HOLD. That a workflow runs. Only a run on GitHub shows that.\n"""\nfrom __future__ import annotations\n\nimport pathlib\nimport re\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nWORKFLOWS = ROOT / ".github" / "workflows"\n\n#: The lowest major version of each action that declares node24.\nFLOOR = {\n    "actions/checkout": 5,\n    "actions/setup-python": 6,\n    "actions/upload-artifact": 6,\n}\n\n#: Every workflow checks the repository out and sets Python up.\nEVERY_WORKFLOW_USES = ("actions/checkout", "actions/setup-python")\n\nUSES = re.compile(r"^\\s*(?:-\\s+)?uses:\\s*([^\\s#]+)")\nVERSION = re.compile(r"^v(\\d+)(?:\\.\\d+)*$")\n\n\ndef _uses(text: str) -> list:\n    """(line number, action, ref) for every step that uses an action."""\n    found = []\n    for number, line in enumerate(text.splitlines(), 1):\n        match = USES.match(line)\n        if match:\n            action, _, ref = match.group(1).partition("@")\n            found.append((number, action, ref))\n    return found\n\n\ndef _problems(name: str, text: str) -> list:\n    out = []\n    for number, action, ref in _uses(text):\n        where = f"{name}:{number}: {action}@{ref}"\n        if action not in FLOOR:\n            out.append(f"{where} is not an action this guard knows. Read which Node its "\n                       f"action.yml declares at that version, then add it to FLOOR.")\n            continue\n        version = VERSION.match(ref)\n        if not version:\n            out.append(f"{where} is pinned by something other than a version tag, which "\n                       f"this guard cannot compare.")\n        elif int(version.group(1)) < FLOOR[action]:\n            out.append(f"{where} is under v{FLOOR[action]}, the first version built for "\n                       f"Node 24.")\n    return out\n\n\ndef _workflows() -> dict:\n    return {path.name: path.read_text(encoding="utf-8")\n            for path in sorted(WORKFLOWS.glob("*.y*ml"))}\n\n\ndef test_every_action_is_at_a_version_built_for_node_24():\n    problems = [p for name, text in _workflows().items() for p in _problems(name, text)]\n    assert not problems, (\n        "GitHub\'s runners no longer have Node 20:\\n  " + "\\n  ".join(problems))\n\n\ndef test_the_reader_is_looking():\n    """A reader that finds no step passes the test above."""\n    workflows = _workflows()\n    assert workflows, f"no workflow found under {WORKFLOWS}"\n    for name, text in workflows.items():\n        used = {action for _n, action, _ref in _uses(text)}\n        missing = [a for a in EVERY_WORKFLOW_USES if a not in used]\n        assert not missing, f"{name}: the reader finds no step that uses {missing}"\n\n    sample = ("    steps:\\n"\n              "      - uses: actions/checkout@v4\\n"\n              "      - name: Python\\n"\n              "        uses: actions/setup-python@v6  # a comment\\n"\n              "      - name: Something new\\n"\n              "        uses: someone/something@v1\\n"\n              "      - name: Pinned\\n"\n              "        uses: actions/upload-artifact@main\\n"\n              "      - run: echo uses: actions/checkout@v1\\n")\n    assert _uses(sample) == [(2, "actions/checkout", "v4"), (4, "actions/setup-python", "v6"),\n                             (6, "someone/something", "v1"), (8, "actions/upload-artifact", "main")], \\\n        "the reader does not find a step written as a list item, or under a name"\n    flagged = _problems("sample.yml", sample)\n    assert len(flagged) == 3, flagged\n    assert "under v5" in flagged[0] and "not an action this guard knows" in flagged[1] \\\n        and "other than a version tag" in flagged[2], flagged\n')
    if (tree.root / 'tests/test_readme_test_counts.py').exists():
        raise Stop('tests/test_readme_test_counts.py' + ' exists already: this round creates it', EXIT_CANNOT_RUN)
    tree.write('tests/test_readme_test_counts.py', '"""The README says how many tests there are in a way that stays true.\n\nRNV-RULINGS-2026-10-05, item 18. Ruled 2026-10-05: "Do B".\n\nWHAT WAS THERE. Exact totals, written once and kept in step by nothing. On\n2026-10-05 the README said 1,641 tests and pytest collected 1,949.\n\nWHAT IS THERE NOW. Every figure is a floor: "over N". N is the number of\ntest functions the suites define, rounded down to the hundred. A test added\nleaves it true, so there is nothing to keep in step. pytest collects more\nthan that number, because a parametrised function is written once and\ncollected once for each case.\n\nWHAT THIS GUARD HOLDS.\n\n1. Every number of tests the README states is a floor. An exact count,\n   written as a sentence, as a badge or as a cell of the suites\' table, is\n   how the old ones went stale.\n2. Every floor is true. The suite it speaks of defines more test functions\n   than it says. Take tests away until one is not, and this names it: lower\n   the README\'s number.\n3. The reader is looking. It finds the README\'s floors, and it tells an\n   exact count from a floor in each of the three ways one is written.\n\nWHAT IT DOES NOT HOLD. The coverage figures beside the counts: a coverage\nfigure depends on the platform it was taken on.\n"""\nfrom __future__ import annotations\n\nimport ast\nimport pathlib\nimport re\n\nROOT = pathlib.Path(__file__).resolve().parents[1]\nREADME = ROOT / "README.md"\n\n#: The unittest suite at the repository root.\nROOT_SUITE = "test_rnv_color_picker.py"\n\n#: The README states this many floors. Fewer and the reader has gone blind,\n#: or the README has stopped saying.\nMIN_FLOORS = 7\n\nNUMBER = r"\\d{1,3}(?:,\\d{3})+|\\d+"\nSENTENCE = re.compile(rf"(?P<n>{NUMBER})\\s+(?:(?:unittest|pytest|passing|automated)\\s+)?tests\\b", re.I)\nBADGE = re.compile(r"\\btests-(?P<n>\\d+)(?P<plus>%2B)?", re.I)\nCELL = re.compile(rf"\\|\\s*\\**(?P<over>over\\s+)?(?P<n>{NUMBER})\\**\\s*(?=\\|)", re.I)\nOVER_BEFORE = re.compile(r"over\\s+\\**$", re.I)\nA_SUITE_ROW = re.compile(r"unittest|pytest|\\btests\\b|coverage", re.I)\n\n\ndef _claims(text: str) -> list:\n    """(line number, the number, whether it is a floor, which suites it\n    counts) for every number of tests the text states."""\n    found = []\n    for number, line in enumerate(text.splitlines(), 1):\n        seen = set()\n\n        def add(match, floor: bool) -> None:\n            if match.start("n") in seen:\n                return\n            seen.add(match.start("n"))\n            low = line.lower()\n            root = "unittest" in low or ROOT_SUITE.lower() in low\n            modern = "pytest" in low or "`tests/`" in low\n            suites = "root" if root and not modern else "pytest" if modern and not root else "all"\n            found.append((number, int(match.group("n").replace(",", "")), floor, suites))\n\n        for match in BADGE.finditer(line):\n            add(match, bool(match.group("plus")))\n        for match in SENTENCE.finditer(line):\n            add(match, bool(OVER_BEFORE.search(line[:match.start("n")])))\n        if line.lstrip().startswith("|") and A_SUITE_ROW.search(line):\n            for match in CELL.finditer(line):\n                add(match, bool(match.group("over")))\n    return found\n\n\ndef _defined_in(source: str, unittest_file: bool) -> int:\n    """How many test functions a file\'s text defines: a lower bound on what\n    is collected from it, since a function is collected at least once."""\n    tree = ast.parse(source)\n    count = 0\n    for node in tree.body:\n        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):\n            count += node.name.startswith("test_") and not unittest_file\n        elif isinstance(node, ast.ClassDef) and (unittest_file or node.name.startswith("Test")):\n            prefix = "test" if unittest_file else "test_"\n            count += sum(1 for member in node.body\n                         if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))\n                         and member.name.startswith(prefix))\n    return count\n\n\ndef _defined(path: pathlib.Path, unittest_file: bool) -> int:\n    return _defined_in(path.read_text(encoding="utf-8-sig"), unittest_file)\n\n\ndef _suites() -> dict:\n    root = _defined(ROOT / ROOT_SUITE, unittest_file=True)\n    modern = sum(_defined(path, unittest_file=False)\n                 for path in sorted((ROOT / "tests").glob("test_*.py")))\n    return {"root": root, "pytest": modern, "all": root + modern}\n\n\ndef test_every_number_of_tests_the_readme_states_is_a_floor():\n    exact = [f"README.md:{line}: {n:,}" for line, n, floor, _s in\n             _claims(README.read_text(encoding="utf-8")) if not floor]\n    assert not exact, (\n        "the README states an exact number of tests, which goes stale with the next "\n        "test:\\n  " + "\\n  ".join(exact) + "\\nSay it as a floor: over N.")\n\n\ndef test_every_floor_is_true():\n    defined = _suites()\n    names = {"root": ROOT_SUITE, "pytest": "tests/", "all": "the two suites together"}\n    false = [f"README.md:{line}: over {n:,}, and {names[suites]} defines {defined[suites]:,}"\n             for line, n, floor, suites in _claims(README.read_text(encoding="utf-8"))\n             if floor and not n < defined[suites]]\n    assert not false, (\n        "the README promises more tests than the suites define:\\n  " + "\\n  ".join(false)\n        + "\\nLower the README\'s number.")\n\n\ndef test_the_reader_is_looking():\n    """A reader that finds nothing passes both tests above."""\n    floors = [c for c in _claims(README.read_text(encoding="utf-8")) if c[2]]\n    assert len(floors) >= MIN_FLOORS, f"the reader finds {len(floors)} floors in the README, not {MIN_FLOORS}"\n    assert {c[3] for c in floors} == {"root", "pytest", "all"}, \\\n        f"the README\'s floors speak of {sorted({c[3] for c in floors})}, not of each suite and of both"\n    defined = _suites()\n    assert defined["root"] > 100 and defined["pytest"] > 100, f"the count of test functions has gone blind: {defined}"\n\n    sample = ("![Tests](https://img.shields.io/badge/tests-786%20passing-brightgreen)\\n"\n              "![Tests](https://img.shields.io/badge/tests-1000%2B%20passing-brightgreen)\\n"\n              "ships with **786 tests across two suites**, and with **over 1,000 tests** too\\n"\n              f"| `{ROOT_SUITE}` (unittest) | 398 | Frozen |\\n"\n              "| `tests/` (pytest) | over 600 | Modern, with 27 snapshots |\\n"\n              "| Ctrl+T | 12 | a row of some other table |\\n"\n              "Python 3.13, 2 suites, tests/test_x.py\\n")\n    assert _claims(sample) == [\n        (1, 786, False, "all"), (2, 1000, True, "all"),\n        (3, 786, False, "all"), (3, 1000, True, "all"),\n        (4, 398, False, "root"),\n        (5, 600, True, "pytest"),\n    ], _claims(sample)\n')


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
    def units(src):
        """Every function, method and assignment a source defines, each under its
        name -> its text. A comment is not part of it; a docstring is."""
        out = dict()
        for node in ast.parse(src).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[node.name + "()"] = ast.unparse(node)
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out[node.name + "." + sub.name + "()"] = ast.unparse(sub)
                    elif isinstance(sub, (ast.Assign, ast.AnnAssign)) and sub.value is not None:
                        t = sub.targets[0] if isinstance(sub, ast.Assign) else sub.target
                        if isinstance(t, ast.Name):
                            out[node.name + "." + t.id] = ast.unparse(sub.value)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                t = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(t, ast.Name):
                    out[t.id] = ast.unparse(node.value)
        return out

    def code(src):
        """units() of a source with every docstring taken out: what the code
        does, not what it says of itself."""
        module = ast.parse(src)
        for node in ast.walk(module):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                        and isinstance(first.value.value, str):
                    node.body = node.body[1:] or [ast.Pass()]
        return units(ast.unparse(module))

    def moved(was_src, now_src):
        """(what arrives, what goes, what changes) between two sources, by name."""
        was, now = units(was_src), units(now_src)
        return (sorted(set(now) - set(was)), sorted(set(was) - set(now)),
                sorted(k for k in set(was) & set(now) if was[k] != now[k]))

    def as_written(rel):
        """A file as this round leaves it: from the tree if the round holds it, else from disk."""
        if rel in tree.files:
            return tree.files[rel]
        return (tree.root / rel).read_text(encoding="utf-8-sig", errors="replace")

    def app_sources():
        """(path, text) of the application's Python as this round leaves it: no
        tests, no runner, no delivery script."""
        skip = ("tests", "build", "dist", "docs", "resources", "scripts", "snapshots", "__pycache__",
                "venv", "env", "htmlcov", "node_modules")
        paths = set(p.relative_to(tree.root).as_posix() for p in tree.root.rglob("*.py"))
        paths |= set(r for r in tree.files if r.endswith(".py"))
        for rel in sorted(paths - tree.deleted):
            parts = rel.split("/")
            if any(q in skip or q.startswith(".") for q in parts[:-1]):
                continue
            if len(parts) == 1 and parts[0].startswith(("test_", "conftest", "run_tests")):
                continue
            text = as_written(rel)
            if len(parts) == 1 and "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:
                continue
            yield rel, text

    def names_in(text):
        """Every name, attribute and imported name a source reaches for, and
        every string it writes out whole."""
        found = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                found.update(a.name for a in node.names)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                found.add(node.value)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(node.name)
        return found

    def tests_in(src):
        return [n.name for n in ast.walk(ast.parse(src))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]

    def check_moves(table):
        """Each file moves by what the table lists for it, and by nothing else."""
        for rel, arrives, goes, changes in table:
            got = moved(_original(tree, rel), tree.read(rel))
            assert got == (arrives, goes, changes), (
                f"{rel} moved by other than what this round lists: arrives {got[0]}, goes {got[1]}, "
                f"changes {got[2]}")
    CFG, CACHE, SETTINGS = "utils/config.py", "utils/cache.py", "utils/settings_manager.py"
    WORKERS, RUNNER = "tests/test_workers.py", "run_tests.py"
    MOVES = [('run_tests.py', [], [], []), ('test_rnv_color_picker.py', [], ['TestStylesheetCache.test_close_button_stylesheet_dark()', 'TestStylesheetCache.test_close_button_stylesheet_light()'], []), ('tests/test_brand_contrast.py', [], ['test_dark_pressed_is_the_accent_itself()', 'test_light_pressed_is_the_accent_itself()'], ['DERIVED_CONSTANTS', '_golds_in()']), ('tests/test_derived_values.py', [], [], ['ALPHAS', 'LOWER8_FLOOR', 'MADE_OF']), ('tests/test_ink_rule.py', [], [], ['test_the_brand_golds_are_ruled_not_measured()']), ('tests/test_named_and_used.py', [], [], ['DATA']), ('tests/test_workers.py', [], [], ['TestWorkerManagerStartWorker.test_start_worker_registers_and_starts()']), ('utils/cache.py', [], ['StylesheetCache.get_button_frame_stylesheet()', 'StylesheetCache.get_close_button_stylesheet()'], []), ('utils/config.py', [], ['BRAND_DARK_GOLD_PRESSED', 'BRAND_GOLD_PRESSED', 'IMAGE_BUTTON_FRAME_ALPHA', 'IMAGE_BUTTON_FRAME_BG'], ['__all__']), ('utils/settings_manager.py', [], [], ['SettingsManager._get_default_settings()'])]
    GONE = ('get_button_frame_stylesheet', 'get_close_button_stylesheet', 'BRAND_GOLD_PRESSED', 'BRAND_DARK_GOLD_PRESSED', 'IMAGE_BUTTON_FRAME_BG', 'IMAGE_BUTTON_FRAME_ALPHA')
    PREFERENCE = 'default_slot_color'
    ON_GOLD = (('dialog_btn_pressed_bg', 'dialog_btn_pressed_text'), ('list_selected_bg', 'list_selected_text'), ('selected_bg', 'text_on_accent'))
    check_moves(MOVES)

    # ---- items 5 and 6, over the whole application as this round leaves it: nothing reaches for what goes
    swept = []
    for rel, text in app_sources():
        swept.append(rel)
        hit = sorted(names_in(text) & set(GONE + (PREFERENCE,)))
        assert not hit, f"{rel} reaches for {hit}, which this round removes: it is not unused here"
    assert len(swept) >= 34 and all(rel in swept for rel in (CFG, CACHE, SETTINGS)), \
        f"the sweep read {len(swept)} files of the application"

    # ---- the cache imports what it reads, and the colour module still defines it
    cache, config = ast.parse(tree.read(CACHE)), units(tree.read(CFG))
    imported = [a.asname or a.name for n in ast.walk(cache)
                if isinstance(n, ast.ImportFrom) and n.module == "utils.config" for a in n.names]
    read = set(n.id for n in ast.walk(cache) if isinstance(n, ast.Name))
    idle = [name for name in imported if name not in read]
    assert imported and not idle, f"{CACHE} imports {idle} from the colour module and reads none of them"
    undefined = [name for name in imported if name not in config and name + "()" not in config]
    assert not undefined, f"{CACHE} imports {undefined}, which {CFG} does not define"
    was_all = ast.literal_eval(units(_original(tree, CFG))["__all__"])
    now_all = ast.literal_eval(config["__all__"])
    assert now_all == [name for name in was_all if name not in GONE] and len(was_all) - len(now_all) == 3, \
        f"{CFG}: __all__ moved by other than the three colours it listed"

    # ---- the settings' defaults lose the one key
    def keys_of(src):
        fn = _function(src, "_get_default_settings", cls="SettingsManager")
        return sorted(k.value for d in ast.walk(fn) if isinstance(d, ast.Dict)
                      for k in d.keys if isinstance(k, ast.Constant))
    was_keys, now_keys = keys_of(_original(tree, SETTINGS)), keys_of(tree.read(SETTINGS))
    assert [k for k in was_keys if k not in now_keys] == [PREFERENCE] and len(was_keys) - len(now_keys) == 1, \
        f"{SETTINGS}: the defaults moved by other than {PREFERENCE}"

    # ---- the ink on gold, where the ink rule's guard now reads it: each palette names it outright
    palettes = dict()
    for node in ast.parse(tree.read(CFG)).body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if getattr(target, "id", None) in ("DARK_THEME_COLORS", "LIGHT_THEME_COLORS"):
            palettes[target.id] = dict((k.value, ast.unparse(v)) for k, v in zip(node.value.keys, node.value.values)
                                       if k is not None)
    for name, gold, ink in (("DARK_THEME_COLORS", "BRAND_GOLD", "TRUE_BLACK"),
                            ("LIGHT_THEME_COLORS", "BRAND_DARK_GOLD", "WHITE")):
        for ground, text in ON_GOLD:
            got = (palettes[name].get(ground), palettes[name].get(text))
            assert got == (gold, ink), f"{name}: {ground} / {text} are {got}, not {gold} / {ink}"

    # ---- item 8: the worker test waits for the cleanup before it asserts it, and for the thread
    test = _function(tree.read(WORKERS), "test_start_worker_registers_and_starts", cls="TestWorkerManagerStartWorker")
    steps = [ast.unparse(s) for s in test.body]
    waits = [n for n, s in enumerate(steps) if s.startswith("qtbot.waitUntil(lambda: w not in m._active_workers")]
    asserts = [n for n, s in enumerate(steps) if s == "assert w not in m._active_workers"]
    assert len(waits) == 1 and len(asserts) == 1 and waits[0] < asserts[0], \
        "the worker test does not wait for the cleanup before it asserts it"
    assert steps[-1] == "assert w.wait(5000)", "the worker test does not wait for the thread to end"

    # ---- the runner's banner counts no tests
    assert not re.search(r"\d+ unittest tests", tree.read(RUNNER)), f"{RUNNER} still counts the root suite"
    assert tests_in(tree.read(GUARD)) == ['test_what_went_is_not_written_again', 'test_the_colour_module_and_the_cache_do_not_define_it', 'test_every_cached_stylesheet_function_is_called', 'test_the_sweeps_are_looking'], f"{GUARD}: its tests are {tests_in(tree.read(GUARD))}"

    # ================= item 14: the workflows' actions, each at the first version built for Node 24
    ACTIONS = (('actions/checkout', 'v4', 'v5'), ('actions/setup-python', 'v5', 'v6'), ('actions/upload-artifact', 'v4', 'v6'))
    WORKFLOW_STEPS = (('.github/workflows/tests.yml', (('actions/checkout', 1), ('actions/setup-python', 1), ('actions/upload-artifact', 1))),)
    NOTE_OPENS = '# RNV-RULINGS-2026-10-05, item 14. Each action below is at the first version'
    here = sorted(p.relative_to(tree.root).as_posix()
                  for p in (tree.root / ".github" / "workflows").glob("*.y*ml"))
    assert here == [wf for wf, _steps in WORKFLOW_STEPS], f"the workflows here are {here}"
    ag = dict(__name__="workflow_actions_guard", __file__=str(tree.root / ACTIONS_GUARD))
    exec(compile(tree.read(ACTIONS_GUARD), ACTIONS_GUARD, "exec"), ag)
    assert ag["FLOOR"] == dict((action, int(new[1:])) for action, _old, new in ACTIONS), \
        f"{ACTIONS_GUARD}: its floor is {ag['FLOOR']}"
    assert tests_in(tree.read(ACTIONS_GUARD)) == ['test_every_action_is_at_a_version_built_for_node_24', 'test_the_reader_is_looking'], f"{ACTIONS_GUARD}: its tests are {tests_in(tree.read(ACTIONS_GUARD))}"
    for wf, steps in WORKFLOW_STEPS:
        was, now = _original(tree, wf).splitlines(), tree.read(wf).splitlines()
        opens = [n for n, line in enumerate(now) if line == NOTE_OPENS]
        assert len(opens) == 1, f"{wf}: the note is there {len(opens)} times"
        ends = opens[0]
        while now[ends].startswith("#"):
            ends += 1
        assert now[ends] == "jobs:" and ends - opens[0] == 5, f"{wf}: the note is not the five lines above jobs:"
        short = [action.split("/")[1] + " " + new for action, _old, new in ACTIONS if dict(steps).get(action)]
        said = (", ".join(short[:-1]) + " and " + short[-1]) if len(short) > 1 else short[0]
        assert now[opens[0] + 1] == f"# built for Node 24: {said}.", \
            f"{wf}: the note names {now[opens[0] + 1]!r}, and the file's steps are {said}"
        rest = now[:opens[0]] + now[ends:]
        assert len(rest) == len(was), f"{wf}: lines came or went beyond the note"
        counted = dict()
        for before, after in zip(was, rest):
            if before == after:
                continue
            hit = [action for action, old, new in ACTIONS
                   if before.strip() in (f"uses: {action}@{old}", f"- uses: {action}@{old}")
                   and after == before.replace(f"{action}@{old}", f"{action}@{new}")]
            assert len(hit) == 1, (
                f"{wf}: a line moved that is not one of the three actions going to its new version: "
                f"{before.strip()!r} -> {after.strip()!r}")
            counted[hit[0]] = counted.get(hit[0], 0) + 1
        assert sorted(counted.items()) == sorted(steps), f"{wf}: the steps moved are {sorted(counted.items())}"
        name = wf.rsplit("/", 1)[1]
        flagged = ag["_problems"](name, "\n".join(was))
        assert len(flagged) == sum(n for _a, n in steps) and all("is under v" in p for p in flagged), \
            f"{wf}: as it is here, the guard names {flagged}"
        still = ag["_problems"](name, "\n".join(now))
        assert still == [], f"{wf}: the guard would still name {still}"

    # ================= item 18: every count the README states is a floor, and true of this checkout as it will be
    FLOORS = [(300, 'root'), (1400, 'pytest'), (1800, 'all'), (1800, 'all'), (1800, 'all'), (1800, 'all'), (1800, 'all')]
    WAS_EXACT = 9
    rg = dict(__name__="readme_counts_guard", __file__=str(tree.root / README_GUARD))
    exec(compile(tree.read(README_GUARD), README_GUARD, "exec"), rg)
    assert rg["ROOT_SUITE"] == ROOT_SUITE and rg["MIN_FLOORS"] == len(FLOORS), \
        f"{README_GUARD}: it is set for {rg['ROOT_SUITE']} and {rg['MIN_FLOORS']} floors"
    assert tests_in(tree.read(README_GUARD)) == ['test_every_number_of_tests_the_readme_states_is_a_floor', 'test_every_floor_is_true', 'test_the_reader_is_looking'], f"{README_GUARD}: its tests are {tests_in(tree.read(README_GUARD))}"
    was_claims, now_claims = rg["_claims"](_original(tree, "README.md")), rg["_claims"](tree.read("README.md"))
    exact = [f"README.md:{line}: {n:,}" for line, n, floor, _s in was_claims if not floor]
    assert len(exact) == WAS_EXACT and len(was_claims) == WAS_EXACT, \
        f"README.md states {len(exact)} exact counts here, of {len(was_claims)} counts: {exact}"
    left = [f"README.md:{line}: {n:,}" for line, n, floor, _s in now_claims if not floor]
    assert not left, f"README.md would still state an exact count: {left}"
    assert sorted((n, s) for _l, n, _f, s in now_claims) == FLOORS, \
        f"README.md would state {sorted((n, s) for _l, n, _f, s in now_claims)}"
    modern = sorted((set(p.relative_to(tree.root).as_posix() for p in (tree.root / "tests").glob("test_*.py"))
                     | set(r for r in tree.files if r.startswith("tests/test_") and r.count("/") == 1
                           and r.endswith(".py"))) - tree.deleted)
    defined = dict(root=rg["_defined_in"](as_written(ROOT_SUITE), True),
                   pytest=sum(rg["_defined_in"](as_written(rel), False) for rel in modern))
    defined["all"] = defined["root"] + defined["pytest"]
    assert len(modern) >= 37 and defined["root"] > 100, f"the count of tests has gone blind: {len(modern)} files, {defined}"
    for number, suites in FLOORS:
        assert number < defined[suites], \
            f"README.md would say over {number:,}, and here {suites} defines {defined[suites]:,}"
    for wf, _steps in WORKFLOW_STEPS[:1]:
        assert SENTINEL in tree.read(wf) and SENTINEL in tree.read(ACTIONS_GUARD) and SENTINEL in tree.read(README_GUARD), \
            "the sentinel is not in the workflow and the two guards"
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
