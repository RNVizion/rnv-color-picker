"""The button keys say where the button lives.

RNV-BUTTON-NAMING-GUARD

main_btn_* is the main window at launch. dialog_btn_* is anything that opens
later. This application ships both schemes -- black-and-white in the main
window, gold in the dialogs -- and until this pass the dialog family was called
button_*, a name that means the MAIN scheme in three of the other four
applications. The rename is what makes the name portable; these tests are what
stop it drifting back.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OLD = ("button_bg", "button_text", "button_hover_bg", "button_hover_text",
       "button_hover_border", "button_pressed_bg", "button_pressed_text",
       "button_border")
NEW = tuple("dialog_btn_" + n[len("button_"):] for n in OLD)

MAIN = ("main_btn_bg", "main_btn_text", "main_btn_border", "main_btn_hover_bg",
        "main_btn_hover_text", "main_btn_pressed_bg", "main_btn_pressed_text")

#: The sixteen dialog values, pinned. A rename that moves one is not a rename.
PINNED_DIALOG = {
    "dark": {"dialog_btn_bg": "#2a2a2a", "dialog_btn_text": "#dddddd",
             "dialog_btn_hover_bg": "#3a3a3a", "dialog_btn_hover_text": "#d2bc93",
             "dialog_btn_hover_border": "#d2bc93", "dialog_btn_pressed_bg": "#d2bc93",
             "dialog_btn_pressed_text": "#000000", "dialog_btn_border": "#333333"},
    "light": {"dialog_btn_bg": "#ffffff", "dialog_btn_text": "#000000",
              "dialog_btn_hover_bg": "#eeeeee", "dialog_btn_hover_text": "#7e6529",
              "dialog_btn_hover_border": "#8c7337", "dialog_btn_pressed_bg": "#8c7337",
              "dialog_btn_pressed_text": "#ffffff", "dialog_btn_border": "#cccccc"},
}

#: The main family is not touched by this pass, and saying so is the point:
#: these two schemes are what the naming exists to keep apart.
PINNED_MAIN = {
    "dark": {"main_btn_bg": "#1a1a1a", "main_btn_text": "#dddddd",
             "main_btn_border": "#333333", "main_btn_hover_bg": "#333333",
             "main_btn_hover_text": "#dddddd", "main_btn_pressed_bg": "#444444",
             "main_btn_pressed_text": "#000000"},
    "light": {"main_btn_bg": "#ffffff", "main_btn_text": "#000000",
              "main_btn_border": "#cccccc", "main_btn_hover_bg": "#333333",
              "main_btn_hover_text": "#000000", "main_btn_pressed_bg": "#444444",
              "main_btn_pressed_text": "#ffffff"},
}

SKIP = {".git", "build", "dist", ".venv", "__pycache__"}

#: A sweep for a name cannot tell a USE of that name from a MENTION of it, and
#: the two files certain to mention it are this guard -- which lists the old
#: names in order to forbid them -- and the delivery script that performs the
#: rename. Both are skipped by marker rather than by filename, because the
#: delivery script arrives under whatever name it is saved as.
MARKERS = ("RNV-BUTTON-NAMING-GUARD", "RNV-BUTTON-NAMING-TOOL-DO-NOT-SWEEP")


def _palettes():
    """Read the palettes the way the application reads them.

    Static resolution is not enough here: light's dialog_btn_hover_text is
    BRAND_DARK_GOLD_DEEP, which is derived by lighten() rather than written as
    a literal, and an AST resolver returns None for it -- then compares None
    with None and passes.
    """
    from utils.config import DARK_THEME_COLORS, LIGHT_THEME_COLORS
    return {"dark": DARK_THEME_COLORS, "light": LIGHT_THEME_COLORS}


def _sources():
    for path in sorted(ROOT.rglob("*")):
        # Prose is not swept. docs/ is updated in one pass after alignment
        # settles, so it names the old keys until then, and a guard that failed
        # on that would be failing on a decision rather than a defect.
        if path.is_dir() or path.suffix not in (".py", ".ambr"):
            continue
        if any(part in SKIP for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(marker in text for marker in MARKERS):
            continue
        yield path, text


def test_no_old_button_key_name_survives():
    offenders = []
    for path, text in _sources():
        for old in OLD:
            if re.search(r"(['\"])" + old + r"\1", text):
                offenders.append(f"{path.relative_to(ROOT)}: {old}")
    assert not offenders, (
        "these are dialog button keys and must be named dialog_btn_*:\n  "
        + "\n  ".join(offenders))


TOOL_MARKER = "RNV-BUTTON-NAMING-TOOL-DO-NOT-SWEEP"


def test_no_application_file_is_exempt_from_the_sweep():
    """The exemption is by marker, and the marker is how a file could hide.

    An earlier version of this counted marked files and allowed two. That
    failed in a working tree holding a second copy of the delivery script --
    a guard failing on the state of somebody's checkout rather than on a
    defect in the application, which is the wrong thing to fail on.

    What actually matters is that no APPLICATION file is exempt. This guard
    may carry a marker; it lists the old names in order to forbid them.
    Everything else must be a delivery script, identified by the tool marker
    in its own header -- those arrive under whatever name they are saved as,
    there can be several of them lying around, and none is application source.
    """
    here = Path(__file__).resolve()
    strays = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if not any(marker in text for marker in MARKERS):
            continue
        if path.resolve() == here or TOOL_MARKER in text:
            continue
        strays.append(str(path.relative_to(ROOT)))
    assert not strays, (
        "these files are skipped by the name sweep but are not a delivery "
        f"script: {strays}")
    assert MARKERS[0] in here.read_text(encoding="utf-8-sig"), (
        "this guard lost its own marker and is now sweeping itself")


def test_both_palettes_carry_the_new_dialog_names():
    for mode, palette in _palettes().items():
        missing = [n for n in NEW if n not in palette]
        assert not missing, f"{mode} palette missing {missing}"


def test_the_rename_moved_no_dialog_value():
    for mode, pins in PINNED_DIALOG.items():
        palette = _palettes()[mode]
        actual = {k: palette.get(k) for k in pins}
        assert actual == pins, (
            f"the {mode} dialog button values changed.\n"
            f"  wanted {pins}\n  found  {actual}\n"
            "A rename that changes a value is not a rename.")


def test_the_main_family_is_untouched():
    for mode, pins in PINNED_MAIN.items():
        palette = _palettes()[mode]
        actual = {k: palette.get(k) for k in pins}
        assert actual == pins, (
            f"the {mode} main button values changed. This pass renames the "
            f"DIALOG family and must not reach the main window.\n"
            f"  wanted {pins}\n  found  {actual}")


def test_the_two_schemes_are_still_different():
    """If the families ever converge, the naming stops carrying information.

    Not a style rule: the main button is black-and-white with an inverting
    transition, the dialog button is gold. They differ at rest, at hover and
    at press, in both modes, and that is the whole reason for two families.
    """
    for mode, palette in _palettes().items():
        for main, dialog in (("main_btn_hover_text", "dialog_btn_hover_text"),
                             ("main_btn_pressed_bg", "dialog_btn_pressed_bg")):
            assert palette[main] != palette[dialog], (
                f"{mode}: {main} and {dialog} now hold the same value "
                f"({palette[main]}). Two families holding one scheme is one "
                f"family with extra steps.")


def test_the_main_window_still_reads_the_main_family():
    for rel in ("RNV_Color_Picker.py", "utils/cache.py"):
        src = (ROOT / rel).read_text(encoding="utf-8-sig")
        assert "'main_btn_bg'" in src, f"{rel} no longer reads main_btn_bg"


def test_the_dialogs_read_the_dialog_family():
    for rel in ("utils/dialog_helper.py", "ui/about_dialog.py",
                "ui/progress_dialog.py", "ui/settings_panel.py"):
        src = (ROOT / rel).read_text(encoding="utf-8-sig")
        assert "dialog_btn_" in src, f"{rel} no longer reads the dialog family"
        assert "'main_btn_" not in src, (
            f"{rel} reads the main family. Dialogs open later and take the "
            f"gold scheme; wiring one to main_btn_* fuses the two.")
