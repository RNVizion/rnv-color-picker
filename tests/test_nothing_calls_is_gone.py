"""What nothing called is gone, and stays gone.

RNV-RULINGS-2026-10-05, items 5 and 6. Ruled 2026-10-05: "Yes." to each.

WHAT WENT.

Item 6. Two cached stylesheet functions that nothing in the application
called: StylesheetCache.get_button_frame_stylesheet() and
StylesheetCache.get_close_button_stylesheet(). The root suite called the
second, twice, to see that it returned a string; those two tests went with
it. So did what only those functions read: BRAND_GOLD_PRESSED and
BRAND_DARK_GOLD_PRESSED, IMAGE_BUTTON_FRAME_BG, and the alpha that one was
made from, IMAGE_BUTTON_FRAME_ALPHA. A pressed button in this application
paints its palette's accent, which is the value the two pressed names held.

Item 5. The stored preference default_slot_color. It sat in the settings'
defaults, nothing read it, and no control set it.

WHAT THIS GUARD HOLDS.

1. None of those names is written in the repository's Python again: not in
   the application, not in a test. This file mentions them in order to
   forbid them, and is the one file the sweep leaves out.
2. The colour module and the cache do not define them.
3. Every cached stylesheet function is called by the application, itself or
   through another that is. A test that calls one does not make it used.
   HELD lists four more that nothing calls, found while removing the two; a
   ruling is asked on them. A fifth is a failure, and so is a held one that
   has gained a caller.
4. The sweeps are looking.
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = "utils/cache.py"

#: What went, and may not come back.
FUNCTIONS_GONE = ("get_button_frame_stylesheet", "get_close_button_stylesheet")
COLOURS_GONE = ("BRAND_GOLD_PRESSED", "BRAND_DARK_GOLD_PRESSED", "IMAGE_BUTTON_FRAME_BG",
                "IMAGE_BUTTON_FRAME_ALPHA")
PREFERENCE_GONE = "default_slot_color"
GONE = FUNCTIONS_GONE + COLOURS_GONE + (PREFERENCE_GONE,)

#: Cached stylesheet functions nothing in the application calls, found on
#: 2026-10-05 and not removed: only the two above were ruled. name -> why it
#: is here.
HELD = {
    "get_scroll_area_stylesheet": "nothing calls it",
    "get_scrollbar_stylesheet": "called only by get_scroll_area_stylesheet(), which nothing calls; "
                                "the root suite calls it to see that it returns a string",
    "get_zoom_label_stylesheet": "nothing calls it",
    "get_color_preview_stylesheet": "nothing calls it; the root suite calls it to see that it holds the hex",
}

#: The one file that names what went, to forbid it.
MENTION_ONLY = {pathlib.Path(__file__).name}
DELIVERY_MARK = "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP"
SKIP_DIRS = {"build", "dist", "__pycache__", "venv", "env", "node_modules", "htmlcov"}
APP_SKIP_DIRS = SKIP_DIRS | {"tests", "docs", "resources", "scripts", "snapshots"}

#: Fewer Python files than this and a walk has gone blind.
MIN_PYTHON = 60
MIN_APP = 30


def _python(app_only: bool = False):
    """(repository-relative path, text) of the repository's Python: all of
    it, or the application's alone (no tests, no runner, no delivery script)."""
    skip = APP_SKIP_DIRS if app_only else SKIP_DIRS
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        parts = rel.split("/")
        if any(part in skip or part.startswith(".") for part in parts[:-1]):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if len(parts) == 1 and DELIVERY_MARK in text:
            continue                                  # a delivery script names what it retires
        if app_only and len(parts) == 1 and parts[0].startswith(("test_", "conftest", "run_tests")):
            continue
        yield rel, text


def _named(pairs) -> list:
    found = []
    for rel, text in pairs:
        if pathlib.PurePosixPath(rel).name in MENTION_ONLY:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for name in GONE:
                if name in line:
                    found.append(f"{rel}:{number}: {name}")
    return found


def _cached_sheet_functions(source: str) -> dict:
    """StylesheetCache's get_*_stylesheet methods: name -> the other such
    methods its body reaches for."""
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "StylesheetCache")
    methods = {n.name: n for n in cls.body
               if isinstance(n, ast.FunctionDef) and n.name.startswith("get_") and n.name.endswith("_stylesheet")}
    return {name: {a.attr for a in ast.walk(node) if isinstance(a, ast.Attribute) and a.attr in methods} - {name}
            for name, node in methods.items()}


def _called_from_outside(names: set, pairs) -> set:
    """Which of `names` the application reaches for, outside StylesheetCache's own methods."""
    called = set()
    for rel, text in pairs:
        tree = ast.parse(text)
        inside = set()
        if rel == CACHE:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "StylesheetCache")
            inside = {id(a) for a in ast.walk(cls)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in names and id(node) not in inside:
                called.add(node.attr)
    return called


def _uncalled(source: str, pairs) -> set:
    reaches = _cached_sheet_functions(source)
    live = _called_from_outside(set(reaches), pairs)
    grew = True
    while grew:                                       # what a called function calls is called too
        more = {callee for name in live for callee in reaches[name]} - live
        live |= more
        grew = bool(more)
    return set(reaches) - live


def test_what_went_is_not_written_again():
    found = _named(_python())
    assert not found, (
        "a name removed on 2026-10-05 is written again:\n  " + "\n  ".join(found)
        + "\nThe two functions were called by nothing, the colours were read only by them, and the "
          "preference was read by nothing. If one is wanted, it needs a caller or a reader, and a ruling.")


def test_the_colour_module_and_the_cache_do_not_define_it():
    from utils import cache, config
    for name in COLOURS_GONE:
        assert not hasattr(config, name), f"utils.config defines {name} again"
        assert name not in config.__all__, f"utils.config exports {name}"
        assert not hasattr(cache, name), f"utils.cache imports {name} again"
    for name in FUNCTIONS_GONE:
        assert not hasattr(cache.StylesheetCache, name), f"StylesheetCache.{name}() is back"
    from utils.settings_manager import SettingsManager
    assert PREFERENCE_GONE not in SettingsManager._get_default_settings()["preferences"], \
        f"the settings' defaults store {PREFERENCE_GONE} again"


def test_every_cached_stylesheet_function_is_called():
    source = (ROOT / CACHE).read_text(encoding="utf-8-sig")
    uncalled = _uncalled(source, list(_python(app_only=True)))
    new = sorted(uncalled - set(HELD))
    assert not new, (
        f"nothing in the application calls StylesheetCache.{', .'.join(n + '()' for n in new)}. "
        f"A sheet nothing asks for paints nothing, and keeps its colours looking used. Call it, or remove it.")
    stale = sorted(set(HELD) - uncalled)
    assert not stale, (
        f"{', '.join(stale)}: held as called by nothing, and it is called now, or gone. Take it out of HELD.")


def test_the_sweeps_are_looking():
    everything, application = list(_python()), list(_python(app_only=True))
    assert len(everything) >= MIN_PYTHON and len(application) >= MIN_APP, (len(everything), len(application))
    paths = {rel for rel, _ in everything}
    for must in (CACHE, "utils/config.py", "utils/settings_manager.py", "test_rnv_color_picker.py",
                 "tests/test_brand_contrast.py"):
        assert must in paths, f"the sweep is not reading {must}"
    assert not any(rel.startswith("tests/") or rel.startswith("test_") for rel, _ in application), \
        "a test is counted as the application: its calls would make a function look used"

    # the name sweep flags a line that names one, and leaves this file out
    assert _named([("ui/sample.py", "x = StylesheetCache.get_close_button_stylesheet()\n")]) \
        == ["ui/sample.py:1: get_close_button_stylesheet"]
    assert _named([("tests/" + next(iter(MENTION_ONLY)), "BRAND_GOLD_PRESSED\n")]) == []
    assert _named([("tests/other.py", pathlib.Path(__file__).read_text(encoding="utf-8"))]), \
        "this file no longer names what went: drop the exemption"

    # the call sweep: called from outside, called only from inside, called by nothing, called by a test
    sample = ("class StylesheetCache:\n"
              "    def get_a_stylesheet(cls):\n        return cls.get_b_stylesheet()\n"
              "    def get_b_stylesheet(cls):\n        return ''\n"
              "    def get_c_stylesheet(cls):\n        return cls.get_d_stylesheet()\n"
              "    def get_d_stylesheet(cls):\n        return ''\n"
              "    def get_e_stylesheet(cls):\n        return ''\n")
    app = [(CACHE, sample), ("ui/window.py", "from utils.cache import StylesheetCache\n"
                                             "s = StylesheetCache.get_a_stylesheet()\n")]
    assert _uncalled(sample, app) == {"get_c_stylesheet", "get_d_stylesheet", "get_e_stylesheet"}
