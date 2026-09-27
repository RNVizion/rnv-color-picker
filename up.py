"""the Settings panel follows a mode switch made while it is open

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (cd87fd6).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-27: "Yes we should fix those to 1 - 4" -- the four things a
switch made with Settings open left behind, measured with the app's own
buttons and a render of every tab after every switch.

1. The gold headings on the Sessions, Shortcuts and Settings tabs, the
   sixteen shortcut key plates and the tip kept the mode the panel was
   opened in: their stylesheets read the mode once, at build. Each is now
   built by a function registered with _style_for_mode(), and update_theme()
   builds it again on every switch -- the same sheet, read for the mode the
   app is in. The divider and the two missing-module notes read the mode the
   same way and are registered too.
2. A new panel painted the harmony base preview in the mode's gold, a
   placeholder, while its inputs said 191, 145, 69. The tab now paints it
   from its inputs as it is built, as the colour-blindness tab already does.
3. The Default Theme box kept the mode the panel was opened in, and Apply --
   which switches the app to whatever the box says -- switched it back.
   update_theme() now sets the box to the mode the app is in, on every
   switch and when a panel is built. Reset to Defaults still loads the
   default into it, and a mode picked in the box still applies.
4. The comment on the rating label's guard said _apply_theme() runs before
   the tabs are built. It does not; corrected.

Rendered with the app's own main(): after each switch through image, dark,
light and back into image, every tab matches a panel opened fresh, pixel for
pixel -- 18 of 18 (9 before). A panel opened fresh changes in one place, the
harmony preview, in every mode. Apply after a switch kept the mode 6 times
in 6 (before, it switched back 3 times in 5).
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
SENTINEL = 'RNV-PANEL-SWITCH'
SENTINEL_FILE = 'tests/test_settings_panel.py'
GUARD = 'tests/test_settings_panel.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_settings_panel.py']
DESCRIPTION = 'the Settings panel follows a mode switch made while it is open'

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

SHADOWS = {"config.py", "conftest.py", "settings_panel.py", "test_rnv_color_picker.py"}

LEFT_ALONE = ["the Sessions tab's divider line. It asks for border_hover and never draws it: the line is sunken, and a sunken line takes Qt's default shading (#9f9f9f, #efefef, #ffffff) in every mode -- a white line on the dark panel. Its stylesheet now follows a switch like the rest, but a change to what it draws needs a ruling.", "a switch made with Apply is not saved. The next launch opens in the mode last chosen with the main window's button. The box now shows the mode the app is in either way. Whether Apply should save it needs a ruling.", 'the two preview placeholders, harmony and colour blindness, which still read the accent and are painted over from their inputs before the panel is shown.', "_get_accent_text() and the palette's text_accent: the same gold in every mode, by two routes. A note for the chart."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('ui/settings_panel.py',
             'from typing import TYPE_CHECKING\n',
             'from typing import TYPE_CHECKING, Callable\n')
    tree.sub('ui/settings_panel.py',
             '        super().__init__(parent)\n        \n        self.parent_app = parent\n        \n',
             '        super().__init__(parent)\n        \n        self.parent_app = parent\n\n        # RNV-PANEL-SWITCH 2026-09-27: every stylesheet that reads the mode\n        # when it is built, as (widget, the function that builds it).\n        # update_theme() calls each function again on a switch. See\n        # _style_for_mode().\n        self._mode_styled: list[tuple[QWidget, Callable[[], str]]] = []\n        \n')
    tree.sub('ui/settings_panel.py',
             '        auto_header.setStyleSheet(StylesheetCache.get_subheader_stylesheet(self._get_accent_text()))\n',
             '        self._style_for_mode(auto_header, lambda: StylesheetCache.get_subheader_stylesheet(\n            self._get_accent_text()))\n')
    tree.sub('ui/settings_panel.py',
             "            no_module.setStyleSheet(StylesheetCache.get_error_stylesheet(\n                self._get_theme()['status_error_text']))\n",
             "            self._style_for_mode(no_module, lambda: StylesheetCache.get_error_stylesheet(\n                self._get_theme()['status_error_text']))\n", times=2)
    tree.sub('ui/settings_panel.py',
             '            section_header.setStyleSheet(f"font-weight: bold; color: {self._get_accent_text()}; padding-top: 8px;")\n',
             '            self._style_for_mode(section_header, lambda: (\n                f"font-weight: bold; color: {self._get_accent_text()}; padding-top: 8px;"))\n')
    tree.sub('ui/settings_panel.py',
             '        tip.setStyleSheet(f"color: {self._get_accent_text()}; font-style: italic; padding-top: 10px;")\n',
             '        self._style_for_mode(tip, lambda: (\n            f"color: {self._get_accent_text()}; font-style: italic; padding-top: 10px;"))\n')
    tree.sub('ui/settings_panel.py',
             '        _t = self._get_theme()\n        key_label.setStyleSheet(f"""\n',
             '        def key_sheet() -> str:\n            _t = self._get_theme()\n            return f"""\n')
    tree.sub('ui/settings_panel.py',
             '            font-family: \'Consolas\', \'Courier New\', monospace;\n            font-weight: bold;\n        """)\n        key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n',
             '            font-family: \'Consolas\', \'Courier New\', monospace;\n            font-weight: bold;\n        """\n        self._style_for_mode(key_label, key_sheet)\n        key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n')
    tree.sub('ui/settings_panel.py',
             '        header = QLabel(text)\n        accent = self._get_accent_text()\n        header.setStyleSheet(f"""\n            font-weight: bold;\n            font-size: 13px;\n            color: {accent};\n',
             '        header = QLabel(text)\n        self._style_for_mode(header, lambda: f"""\n            font-weight: bold;\n            font-size: 13px;\n            color: {self._get_accent_text()};\n')
    tree.sub('ui/settings_panel.py',
             '        divider_color = self._get_theme()[\'border_hover\']\n        line.setStyleSheet(f"color: {divider_color};")\n',
             '        self._style_for_mode(line, lambda: f"color: {self._get_theme()[\'border_hover\']};")\n')
    tree.sub('ui/settings_panel.py',
             '    def _create_section_header(self, text: str) -> QLabel:\n',
             '    def _style_for_mode(self, widget: QWidget, sheet: Callable[[], str]) -> None:\n        """Style widget with sheet(), now and again after every theme switch.\n\n        RNV-PANEL-SWITCH, 2026-09-27. For a stylesheet that reads the mode --\n        _get_accent_text(), _get_theme() -- when it is built. Set once, it\n        kept the mode the panel was opened in: a switch made with the panel\n        open left the headers, the key plates and the tip in the old mode\'s\n        colours until the panel was opened again. update_theme() calls every\n        registered sheet() again, so each reads the mode the app is in.\n        For widgets that live as long as the panel.\n        """\n        widget.setStyleSheet(sheet())\n        self._mode_styled.append((widget, sheet))\n\n    def _create_section_header(self, text: str) -> QLabel:\n')
    tree.sub('ui/settings_panel.py',
             '        layout.addStretch()\n        \n        # Generate initial harmony\n        self._generate_harmony()\n        \n        return widget\n',
             "        layout.addStretch()\n        \n        # Paint the base preview from its inputs, then generate the first\n        # harmony. RNV-PANEL-SWITCH (2), 2026-09-27: this called\n        # _generate_harmony() alone, so the preview kept the placeholder it\n        # was built with -- the mode's gold -- while the inputs said 191,\n        # 145, 69, until one of them moved. The colour-blindness preview is\n        # painted from its inputs the same way, at the end of its own tab.\n        self._update_harmony_base()\n        \n        return widget\n")
    tree.sub('ui/settings_panel.py',
             '        # GUARDED because _apply_theme() runs at line 146, BEFORE the tab\n        # widget is built at 158 and the accessibility tab at 168. On\n        # construction these widgets do not exist yet; the tab builds itself\n        # with a call to _update_contrast_check() at the end, so nothing is\n        # missed.\n',
             '        # GUARDED so a switch never depends on the order __init__ builds\n        # things in. Corrected 2026-09-27 (RNV-PANEL-SWITCH): this said\n        # _apply_theme() runs before the tabs are built. It does not --\n        # __init__ calls _build_ui() first, so every tab exists by the time\n        # the theme is first applied. The accessibility tab also paints the\n        # label itself, with a call to _update_contrast_check() at the end\n        # of its build.\n')
    tree.sub('ui/settings_panel.py',
             '        if hasattr(self, "harmony_swatches_layout"):\n            self._generate_harmony()\n    \n    @staticmethod\n    def _build_dialog_stylesheet(theme: dict) -> str:\n',
             '        if hasattr(self, "harmony_swatches_layout"):\n            self._generate_harmony()\n\n        # RNV-PANEL-SWITCH 2026-09-27: restyle everything styled for a mode\n        # -- the section headers, the Sessions subheader, the shortcut key\n        # plates, the tip, the divider and the missing-module notes. Each\n        # sheet is built again, so each reads the mode the app is in now.\n        for widget, sheet in getattr(self, "_mode_styled", ()):\n            widget.setStyleSheet(sheet())\n\n        # RNV-PANEL-SWITCH (3): the Default Theme box shows the mode the app\n        # is in. Apply switches the app to whatever the box says when it\n        # differs from the current mode, and nothing saves the box -- so a\n        # box left on the mode the panel was opened with made Apply switch\n        # the app back. This runs on every switch made while the panel is\n        # open, and when a panel is built, after the saved mode is loaded.\n        # Reset to Defaults still puts the default mode in the box.\n        if (hasattr(self, "theme_combo") and self.parent_app\n                and hasattr(self.parent_app, "theme_manager")):\n            index = {"dark": 0, "light": 1, "image": 2}.get(\n                self.parent_app.theme_manager.current_theme)\n            if index is not None:\n                self.theme_combo.setCurrentIndex(index)\n    \n    @staticmethod\n    def _build_dialog_stylesheet(theme: dict) -> str:\n')
    tree.sub('tests/test_settings_panel.py',
             '        del panel.harmony_swatches_layout\n        self._switch(panel, "light")        # no AttributeError\n        assert config.LIGHT_THEME_COLORS["text_muted"] in panel.styleSheet()\n',
             '        del panel.harmony_swatches_layout\n        self._switch(panel, "light")        # no AttributeError\n        assert config.LIGHT_THEME_COLORS["text_muted"] in panel.styleSheet()\n\n\n# RNV-PANEL-SWITCH\n# ═════════════════════════════════════════════════════════════════════════════\n# A SWITCH WITH THE PANEL OPEN leaves it as a panel built in that mode\n# ═════════════════════════════════════════════════════════════════════════════\nclass TestPanelFollowsASwitch:\n    """RNV-PANEL-SWITCH, 2026-09-27. A switch made with Settings open left\n    parts of the panel in the mode it was opened in: the gold headers on the\n    Sessions, Shortcuts and Settings tabs, the shortcut key plates, the tip,\n    and the Default Theme box -- which then made Apply switch the app back.\n    And a new panel painted the harmony base preview in the mode\'s gold while\n    its inputs said 191, 145, 69.\n\n    The first test is the general one. After any switch, every widget in the\n    panel carries the stylesheet a panel built in that mode gives it; a\n    stylesheet that reads the mode once, at build, fails it. The others read\n    what Qt resolves and draws."""\n\n    THEMES = {"dark": config.DARK_THEME_COLORS, "light": config.LIGHT_THEME_COLORS,\n              "image": config.IMAGE_MODE_COLORS}\n    GOLD_TEXT = {"dark": config.BRAND_GOLD, "image": config.BRAND_GOLD,\n                 "light": config.BRAND_DARK_GOLD_DEEP}\n    GOLD_LABELS = ("Auto-Save Options", "File Operations", "Color Operations",\n                   "View Controls", "Application", "General Preferences",\n                   "Color Settings", "Export Settings", "UI Preferences",\n                   "Tip: Use keyboard shortcuts for fastest workflow!")\n    KEYS = ("Ctrl+O", "Ctrl+S", "Ctrl+E", "Ctrl+G", "Ctrl+K", "Ctrl+Shift+C", "Ctrl+D",\n            "Ctrl+0", "Scroll Wheel", "Double-Click", "Click+Drag", "Ctrl+,", "Ctrl+P",\n            "Ctrl+/", "F11", "F12")\n    BOX = {"dark": "Dark Mode", "light": "Light Mode", "image": "Image Mode"}\n    #: from a panel built in dark, every ordered pair of different modes\n    WALK = ("light", "image", "dark", "light", "dark", "image", "light")\n\n    @staticmethod\n    def _build(qtbot, mode):\n        """A panel built in `mode`, the way the `panel` fixture builds one."""\n        real_parent = QWidget()\n        mock = _make_mock_parent_app(mode)\n        real_parent.theme_manager = mock.theme_manager\n        real_parent.tooltips_enabled = mock.tooltips_enabled\n        real_parent.debug_label = mock.debug_label\n        built = SettingsPanel(parent=real_parent)\n        qtbot.addWidget(built)\n        built._test_real_parent = real_parent\n        return built\n\n    @classmethod\n    def _switch(cls, panel, mode):\n        """What the app does on a switch with the panel open: the theme\n        manager moves, then the app calls update_theme()."""\n        tm = panel.parent_app.theme_manager\n        tm.current_theme = mode\n        tm.get_current_theme.return_value = cls.THEMES[mode]\n        tm.is_image_mode.return_value = (mode == "image")\n        panel.update_theme()\n\n    @staticmethod\n    def _styles(panel):\n        """The dialog\'s stylesheet, then every widget\'s class, name and\n        stylesheet in the order the panel made them -- once Qt has deleted\n        the swatches the harmony let go of."""\n        from PyQt6.QtCore import QCoreApplication, QEvent\n        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)\n        return [panel.styleSheet()] + [(type(w).__name__, w.objectName(), w.styleSheet())\n                                       for w in panel.findChildren(QWidget)]\n\n    @staticmethod\n    def _label(panel, text):\n        found = [w for w in panel.findChildren(QLabel) if w.text() == text]\n        assert len(found) == 1, (text, len(found))\n        return found[0]\n\n    @staticmethod\n    def _ink(widget) -> str:\n        from PyQt6.QtGui import QPalette\n        widget.ensurePolished()\n        return widget.palette().color(QPalette.ColorRole.WindowText).name()\n\n    @staticmethod\n    def _quiet_apply(panel, monkeypatch):\n        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: None)\n        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)\n        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)\n        asked = []\n        panel.theme_change_requested.connect(asked.append)\n        return asked\n\n    @pytest.mark.parametrize("built, to", [(a, b) for a in ("dark", "light", "image")\n                                           for b in ("dark", "light", "image") if a != b])\n    def test_a_switched_panel_is_styled_as_one_built_in_that_mode(self, qtbot, built, to):\n        switched = self._build(qtbot, built)\n        self._switch(switched, to)\n        fresh = self._build(qtbot, to)\n        a, b = self._styles(switched), self._styles(fresh)\n        assert len(a) == len(b), (len(a), len(b))\n        differ = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]\n        assert not differ, differ[:3]\n\n    def test_the_gold_text_follows_every_switch(self, qtbot):\n        panel = self._build(qtbot, "dark")\n        for mode in self.WALK:\n            self._switch(panel, mode)\n            for text in self.GOLD_LABELS:\n                ink = self._ink(self._label(panel, text))\n                assert ink == self.GOLD_TEXT[mode].lower(), (mode, text, ink)\n\n    def test_the_key_plates_follow_every_switch(self, qtbot):\n        panel = self._build(qtbot, "dark")\n        for mode in self.WALK:\n            self._switch(panel, mode)\n            theme = self.THEMES[mode]\n            for key in self.KEYS:\n                plate = self._label(panel, key)\n                image = plate.grab().toImage()\n                ground = image.pixelColor(2, image.height() // 2).name()\n                assert ground == theme["pressed_bg"].lower(), (mode, key, ground)\n                assert self._ink(plate) == theme["text_primary"].lower(), (mode, key)\n\n    def test_the_missing_module_notes_follow_a_switch(self, qtbot, monkeypatch):\n        """Without its module the Harmony or the Accessibility tab shows a\n        note in the mode\'s error red -- and light has a red of its own."""\n        import ui.settings_panel as settings_panel\n        monkeypatch.setattr(settings_panel, "ColorHarmony", None)\n        monkeypatch.setattr(settings_panel, "ColorAccessibility", None)\n        panel = self._build(qtbot, "dark")\n        notes = [w for w in panel.findChildren(QLabel) if "module not available" in w.text()]\n        assert len(notes) == 2, [w.text() for w in notes]\n        assert self.THEMES["dark"]["status_error_text"] != self.THEMES["light"]["status_error_text"]\n        for mode in self.WALK:\n            self._switch(panel, mode)\n            for note in notes:\n                ink = self._ink(note)\n                assert ink == self.THEMES[mode]["status_error_text"].lower(), (mode, note.text(), ink)\n\n    @pytest.mark.parametrize("mode", ["dark", "light", "image"])\n    def test_a_new_panel_paints_the_harmony_preview_from_its_inputs(self, qtbot, mode):\n        panel = self._build(qtbot, mode)\n        rgb = (panel.harmony_r_spin.value(), panel.harmony_g_spin.value(),\n               panel.harmony_b_spin.value())\n        image = panel.harmony_base_preview.grab().toImage()\n        centre = image.pixelColor(image.width() // 2, image.height() // 2).name()\n        assert centre == QColor(*rgb).name(), (mode, rgb, centre)\n        assert panel.harmony_colors[0] == rgb\n\n    def test_apply_after_a_switch_keeps_the_mode(self, qtbot, monkeypatch):\n        panel = self._build(qtbot, "dark")\n        asked = self._quiet_apply(panel, monkeypatch)\n        for mode in self.WALK:\n            self._switch(panel, mode)\n            assert panel.theme_combo.currentText() == self.BOX[mode], mode\n            panel._apply_settings()\n            assert asked == [], (mode, asked)\n\n    def test_a_new_panel_shows_the_mode_the_app_is_in(self, qtbot, monkeypatch):\n        """Nothing saves a switch made with Apply. A panel opened after one\n        showed the saved mode, and its Apply switched the app back to it."""\n        from utils.settings_manager import get_settings_manager\n        monkeypatch.setitem(get_settings_manager().settings, "theme", "dark")\n        panel = self._build(qtbot, "light")\n        assert panel.theme_combo.currentText() == "Light Mode"\n        asked = self._quiet_apply(panel, monkeypatch)\n        panel._apply_settings()\n        assert asked == []\n\n    def test_the_box_still_switches_the_mode_when_it_is_changed(self, qtbot, monkeypatch):\n        panel = self._build(qtbot, "dark")\n        self._switch(panel, "light")\n        asked = self._quiet_apply(panel, monkeypatch)\n        panel.theme_combo.setCurrentText("Image Mode")\n        panel._apply_settings()\n        assert asked == ["image"]\n\n    def test_reset_still_loads_the_saved_default_into_the_box(self, qtbot, monkeypatch):\n        panel = self._build(qtbot, "light")\n        monkeypatch.setitem(panel.settings_manager.settings, "theme", "dark")\n        panel._load_settings_into_ui()\n        assert panel.theme_combo.currentText() == "Dark Mode"\n')


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
    import copy

    PANEL = "ui/settings_panel.py"
    old_p, new_p = _original(tree, PANEL), tree.read(PANEL)
    old_t, new_t = ast.parse(old_p), ast.parse(new_p)
    MODE = {"_get_accent", "_get_accent_text", "_get_theme"}

    def panel_class(t):
        return next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == "SettingsPanel")

    def methods(t):
        return {n.name: n for n in panel_class(t).body if isinstance(n, ast.FunctionDef)}

    def reads_mode(node):
        return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr in MODE and ast.unparse(c.func.value) == "self"
                   for c in ast.walk(node))

    def calls(fn, name):
        return sum(1 for c in ast.walk(fn) if isinstance(c, ast.Call)
                   and isinstance(c.func, ast.Attribute) and c.func.attr == name
                   and ast.unparse(c.func.value) == "self")

    # --- what moved: nine methods, one new helper, the typing import; nothing else
    om, nm = methods(old_t), methods(new_t)
    assert set(nm) - set(om) == {"_style_for_mode"} and not set(om) - set(nm), set(nm) ^ set(om)
    moved = sorted(n for n in om if ast.dump(om[n]) != ast.dump(nm[n]))
    assert moved == sorted(["__init__", "_create_sessions_tab", "_create_harmony_tab",
                            "_create_accessibility_tab", "_create_shortcuts_tab",
                            "_create_shortcut_row", "_create_section_header",
                            "_create_section_divider", "update_theme"]), moved
    assert ([ast.dump(n) for n in panel_class(old_t).body if not isinstance(n, ast.FunctionDef)]
            == [ast.dump(n) for n in panel_class(new_t).body if not isinstance(n, ast.FunctionDef)])
    outside = lambda t: [ast.dump(n) for n in t.body if n is not panel_class(t)]   # noqa: E731
    differ = [(a, b) for a, b in zip(outside(old_t), outside(new_t)) if a != b]
    assert len(outside(old_t)) == len(outside(new_t)) and len(differ) == 1, "the module moved beyond the panel"
    assert "Callable" in differ[0][1] and "Callable" not in differ[0][0], differ

    # --- 1. the same sheets as before, now built again on every switch
    def with_locals(fn, expr):
        """expr with each local it reads replaced by what fn assigned it"""
        local = {n.targets[0].id: n.value for n in ast.walk(fn)
                 if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and reads_mode(n.value)}

        class Sub(ast.NodeTransformer):
            def visit_Name(self, node):
                return copy.deepcopy(local[node.id]) if node.id in local else node
        return Sub().visit(copy.deepcopy(expr))

    def direct(fn):
        """the stylesheets fn sets straight away that read the mode"""
        out = []
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "setStyleSheet" and c.args:
                arg = with_locals(fn, c.args[0])
                if reads_mode(arg):
                    out.append((ast.unparse(c.func.value), ast.dump(arg)))
        return sorted(out)

    def registered(fn):
        """the stylesheets fn hands to _style_for_mode"""
        nested = {n.name: n for n in ast.walk(fn) if isinstance(n, ast.FunctionDef) and n is not fn}
        out = []
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "_style_for_mode":
                target, sheet = c.args
                if isinstance(sheet, ast.Lambda):
                    body = sheet.body
                else:
                    inner = nested[sheet.id]
                    ret = [s for s in inner.body if isinstance(s, ast.Return)]
                    assert len(ret) == 1, ast.unparse(inner)
                    body = with_locals(inner, ret[0].value)
                out.append((ast.unparse(target), ast.dump(body)))
        return sorted(out)

    count = 0
    for name in moved:
        if name in ("__init__", "update_theme"):
            continue
        before, after = direct(om[name]), sorted(direct(nm[name]) + registered(nm[name]))
        assert before == after, f"{name}: a stylesheet changed on the way"
        count += len(registered(nm[name]))
    assert count == 8, f"{count} stylesheets registered, not 8"
    left = sorted((n, target) for n in nm for target, _ in direct(nm[n]))
    assert left == [("_create_accessibility_tab", "self.sim_color_preview"),
                    ("_create_harmony_swatch", "color_box"),
                    ("_create_harmony_tab", "self.harmony_base_preview"),
                    ("_update_contrast_check", "self.contrast_ratio_label"),
                    ("update_theme", "self")], \
        f"a stylesheet reads the mode at build and nothing redraws it: {left}"

    # ... and each that is left is drawn again on a switch, or painted over
    # from its inputs before the panel is shown
    ut = nm["update_theme"]
    assert calls(ut, "_update_contrast_check") == 1, "update_theme() no longer repaints the rating label"
    assert calls(ut, "_generate_harmony") == 1, "update_theme() no longer redraws the harmony"
    assert calls(nm["_generate_harmony"], "_create_harmony_swatch") == 1
    assert calls(nm["_create_accessibility_tab"], "_update_blindness_sim") == 1, \
        "the colour-blindness preview is not painted from its inputs"
    assert calls(nm["_create_harmony_tab"], "_update_harmony_base") == 1, \
        "the harmony tab does not paint its preview from its inputs"
    assert calls(nm["_create_harmony_tab"], "_generate_harmony") == 0
    base = ast.unparse(nm["_update_harmony_base"])
    assert "self.harmony_r_spin.value()" in base and "self.harmony_base_preview.setStyleSheet" in base
    assert calls(nm["_update_harmony_base"], "_generate_harmony") == 1

    # --- the register and the loop that uses it
    sfm = nm["_style_for_mode"]
    assert [ast.unparse(s) for s in sfm.body[1:]] == [
        "widget.setStyleSheet(sheet())", "self._mode_styled.append((widget, sheet))"]
    init = nm["__init__"].body
    at = [i for i, s in enumerate(init) if "self._mode_styled" in ast.unparse(s)]
    build = [i for i, s in enumerate(init) if ast.unparse(s) == "self._build_ui()"]
    assert len(at) == 1 and len(build) == 1 and at[0] < build[0], "the register is made after the build"
    assert ast.unparse(init[at[0]]).endswith("= []")
    loops = [ast.unparse(s) for s in ut.body if isinstance(s, ast.For)]
    assert loops == ["for widget, sheet in getattr(self, '_mode_styled', ()):\n"
                     "    widget.setStyleSheet(sheet())"], \
        "update_theme() does not restyle what was styled for a mode"

    # --- 3. the box shows the mode the app is in; the loader still loads the saved one
    box = [ast.unparse(s) for s in ut.body if isinstance(s, ast.If) and "theme_combo" in ast.unparse(s)]
    assert (len(box) == 1 and "self.parent_app.theme_manager.current_theme" in box[0]
            and "self.theme_combo.setCurrentIndex(index)" in box[0]
            and "settings" not in box[0]), "the Default Theme box does not follow the mode"
    assert ast.dump(om["_load_settings_into_ui"]) == ast.dump(nm["_load_settings_into_ui"])

    # --- 4. the guard's comment gives the right reason
    assert "BEFORE the tab" in old_p
    assert "BEFORE the tab" not in new_p and "__init__ calls _build_ui() first" in new_p, \
        "the rating label's comment still gives the wrong reason"

    # --- the guard: appended, nothing above it touched
    old_g, new_g = _original(tree, "tests/test_settings_panel.py"), tree.read("tests/test_settings_panel.py")
    assert new_g.startswith(old_g), "the guard file changed above its new class"
    ast.parse(new_g)
    tail_g = new_g[len(old_g):]
    assert SENTINEL in tail_g and "class TestPanelFollowsASwitch" in tail_g
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
