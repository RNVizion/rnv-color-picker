"""the About dialog follows a mode switch, its divider draws its grey, its About tab scrolls

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (307cb0a).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-27: "Script run you can work on those. Fixes now" -- the
About dialog items the Save-and-divider round left alone.

1. A switch made with the About dialog open restyled only its banner. The
   Close button, the gold headings and category names, the muted values and
   shortcut keys, and the footer kept the mode the dialog was opened in, on
   all four tabs -- the fault the Settings panel had. Thirteen stylesheets
   are registered with _style_for_mode() now, the helper of the same name
   in the settings panel, and _apply_theme() -- which the app calls on every
   switch while the dialog is open -- builds each again. The sheets are the
   same text as before.
2. Its divider was sunken, like the Sessions one: Qt's own shading, a white
   line on the dark dialog, border_hover never drawn. It is a plain 1px line
   in border_hover now, and follows a switch.
3. Found on the way, in the same dialog: the About tab could not be read.
   Its content needs about 507px and the fixed 650x520 dialog gives it 260,
   so its layout squeezed every label to two or three pixels. It scrolls
   now, as the Features, Shortcuts and Credits tabs already do. Every line
   of its text is kept.

Rendered with the app's own main(): after each switch through image, dark,
light and back, every tab matches a dialog opened fresh, pixel for pixel --
12 of 12 (4 before). A dialog opened fresh changes only on its About tab:
the scroll area and the divider.
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
SENTINEL = 'RNV-ABOUT-SWITCH'
SENTINEL_FILE = 'tests/test_about_dialog.py'
GUARD = 'tests/test_about_dialog.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_about_dialog.py']
DESCRIPTION = 'the About dialog follows a mode switch, its divider draws its grey, its About tab scrolls'

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

SHADOWS = {"config.py", "conftest.py", "about_dialog.py", "test_rnv_color_picker.py"}

LEFT_ALONE = ['the banner -- header, name, version and tagline -- which _apply_theme() already restyled on every switch.', "the dialog's fixed size, 650 x 520, which a test pins; the About tab scrolls instead."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('ui/about_dialog.py',
             'import sys\nimport os\n',
             'import sys\nimport os\nfrom typing import Callable\n')
    tree.sub('ui/about_dialog.py',
             '        self._build_ui()\n        self._apply_theme()\n',
             '        # RNV-ABOUT-SWITCH 2026-09-27: every stylesheet that reads the mode\n        # when it is built, as (widget, the function that builds it).\n        # _apply_theme() calls each function again on a switch. See\n        # _style_for_mode().\n        self._mode_styled: list[tuple[QWidget, Callable[[], str]]] = []\n\n        self._build_ui()\n        self._apply_theme()\n')
    tree.sub('ui/about_dialog.py',
             '            logo_label.setText("RNV")\n            logo_label.setStyleSheet(f"""\n',
             '            logo_label.setText("RNV")\n            self._style_for_mode(logo_label, lambda: f"""\n')
    tree.sub('ui/about_dialog.py',
             '        close_btn.clicked.connect(self.close)\n        _theme = self._get_theme()\n        close_btn.setStyleSheet(f"""\n',
             '        close_btn.clicked.connect(self.close)\n        def close_sheet() -> str:\n            _theme = self._get_theme()\n            return f"""\n')
    tree.sub('ui/about_dialog.py',
             '                border: 1px solid {_theme[\'dialog_btn_border\']};\n            }}\n        """)\n        btn_layout.addWidget(close_btn)\n',
             '                border: 1px solid {_theme[\'dialog_btn_border\']};\n            }}\n        """\n        self._style_for_mode(close_btn, close_sheet)\n        btn_layout.addWidget(close_btn)\n')
    tree.sub('ui/about_dialog.py',
             '        desc_header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent_text()};")\n',
             '        self._style_for_mode(desc_header, lambda: (\n            f"font-weight: bold; font-size: 13px; color: {self._get_accent_text()};"))\n')
    tree.sub('ui/about_dialog.py',
             "        muted = self._get_theme()['text_muted']\n        for row, (label, value) in enumerate(info_items):\n",
             '        for row, (label, value) in enumerate(info_items):\n')
    tree.sub('ui/about_dialog.py',
             '            val.setStyleSheet(f"font-size: 11px; color: {muted};")\n',
             '            self._style_for_mode(val, lambda: (\n                f"font-size: 11px; color: {self._get_theme()[\'text_muted\']};"))\n')
    tree.sub('ui/about_dialog.py',
             '        header.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._get_accent_text()};")\n',
             '        self._style_for_mode(header, lambda: (\n            f"font-weight: bold; font-size: 13px; color: {self._get_accent_text()};"))\n', times=3)
    tree.sub('ui/about_dialog.py',
             '            cat_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {self._get_accent_text()}; padding-top: 5px;")\n',
             '            self._style_for_mode(cat_label, lambda: (\n                f"font-weight: bold; font-size: 12px; color: {self._get_accent_text()}; padding-top: 5px;"))\n')
    tree.sub('ui/about_dialog.py',
             '            cat_label.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {self._get_accent_text()}; padding-top: 8px;")\n',
             '            self._style_for_mode(cat_label, lambda: (\n                f"font-weight: bold; font-size: 11px; color: {self._get_accent_text()}; padding-top: 8px;"))\n')
    tree.sub('ui/about_dialog.py',
             "            # Shortcuts grid\n            muted = self._get_theme()['text_muted']\n",
             '            # Shortcuts grid\n')
    tree.sub('ui/about_dialog.py',
             '                key_label.setStyleSheet(f"font-size: 11px; color: {muted};")\n',
             '                self._style_for_mode(key_label, lambda: (\n                    f"font-size: 11px; color: {self._get_theme()[\'text_muted\']};"))\n')
    tree.sub('ui/about_dialog.py',
             "        tech_muted = self._get_theme()['text_muted']\n",
             '')
    tree.sub('ui/about_dialog.py',
             '            val.setStyleSheet(f"font-size: 11px; color: {tech_muted};")\n',
             '            self._style_for_mode(val, lambda: (\n                f"font-size: 11px; color: {self._get_theme()[\'text_muted\']};"))\n')
    tree.sub('ui/about_dialog.py',
             '        footer.setStyleSheet(\n            f"font-size: 11px; color: {self._get_accent_text()}; padding-top: 15px;"\n        )\n',
             '        self._style_for_mode(footer, lambda: (\n            f"font-size: 11px; color: {self._get_accent_text()}; padding-top: 15px;"\n        ))\n')
    tree.sub('ui/about_dialog.py',
             '    def _create_about_tab(self) -> QWidget:\n        """Create the About tab with app description and system info."""\n        widget = QWidget()\n        layout = QVBoxLayout(widget)\n        layout.setContentsMargins(20, 15, 20, 15)\n        layout.setSpacing(15)\n',
             '    def _create_about_tab(self) -> QWidget:\n        """Create the About tab with app description and system info."""\n        # RNV-ABOUT-SCROLL 2026-09-27: in a scroll area, as the other three\n        # tabs are. This tab\'s content needs about 507px and the fixed-size\n        # dialog gives it 260, so its layout squeezed every label to two or\n        # three pixels and none of the text could be read.\n        widget = QWidget()\n        outer = QVBoxLayout(widget)\n        outer.setContentsMargins(0, 0, 0, 0)\n        scroll = QScrollArea()\n        scroll.setWidgetResizable(True)\n        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\n        scroll.setStyleSheet("QScrollArea { border: none; }")\n        outer.addWidget(scroll)\n        content = QWidget()\n        scroll.setWidget(content)\n        layout = QVBoxLayout(content)\n        layout.setContentsMargins(20, 15, 20, 15)\n        layout.setSpacing(15)\n')
    tree.sub('ui/about_dialog.py',
             '        line.setFrameShadow(QFrame.Shadow.Sunken)\n        divider_color = self._get_theme()[\'border_hover\']\n        line.setStyleSheet(f"color: {divider_color};")\n',
             '        # RNV-ABOUT-DIVIDER 2026-09-27: Plain, so the line is drawn in the\n        # colour below, as the Sessions divider now is. It was Sunken, and Qt\n        # draws a sunken line in its own shading -- #9f9f9f and #ffffff in\n        # every mode, a white line on the dark dialog -- so border_hover was\n        # never drawn.\n        line.setFrameShadow(QFrame.Shadow.Plain)\n        self._style_for_mode(line, lambda: f"color: {self._get_theme()[\'border_hover\']};")\n')
    tree.sub('ui/about_dialog.py',
             '    def _get_accent_text(self) -> str:\n',
             '    def _style_for_mode(self, widget: QWidget, sheet: Callable[[], str]) -> None:\n        """Style widget with sheet(), now and again after every theme switch.\n\n        RNV-ABOUT-SWITCH, 2026-09-27 -- the settings panel\'s helper of the\n        same name, for the same fault. For a stylesheet that reads the mode\n        when it is built. Set once, it kept the mode the dialog was opened\n        in: a switch made with the dialog open left the Close button, the\n        gold headings and the muted text in the old mode\'s colours.\n        _apply_theme() calls every registered sheet() again.\n        """\n        widget.setStyleSheet(sheet())\n        self._mode_styled.append((widget, sheet))\n\n    def _get_accent_text(self) -> str:\n')
    tree.sub('ui/about_dialog.py',
             '            {tab_style}\n        """)\n',
             '            {tab_style}\n        """)\n\n        # RNV-ABOUT-SWITCH 2026-09-27: restyle everything styled for a mode.\n        # The app calls this on every switch made while the dialog is open,\n        # and it restyled the banner alone -- the Close button, the gold\n        # headings, the muted values and keys, the footer and the divider\n        # kept the mode the dialog was opened in.\n        for widget, sheet in getattr(self, "_mode_styled", ()):\n            widget.setStyleSheet(sheet())\n')
    tree.sub('tests/test_about_dialog.py',
             '        show_about_dialog()\n        assert captured_parents == [None]\n',
             '        show_about_dialog()\n        assert captured_parents == [None]\n\n\n# RNV-ABOUT-SWITCH\n# ─────────────────────────────────────────────────────────────────────────────\n# 9.  A SWITCH WITH THE DIALOG OPEN leaves it as a dialog built in that mode\n# ─────────────────────────────────────────────────────────────────────────────\n\nclass TestAboutFollowsASwitch:\n    """RNV-ABOUT-SWITCH and RNV-ABOUT-DIVIDER, 2026-09-27. A switch made with\n    the About dialog open restyled only its banner: the Close button, the\n    gold headings and categories, the muted values and keys, and the footer\n    kept the mode the dialog was opened in. And its divider was sunken, which\n    Qt draws in its own shading in every mode, so border_hover was never\n    drawn.\n\n    The first test is the general one: after any switch, every widget\n    carries the stylesheet a dialog built in that mode gives it."""\n\n    THEMES = {"dark": config.DARK_THEME_COLORS, "light": config.LIGHT_THEME_COLORS,\n              "image": config.IMAGE_MODE_COLORS}\n    GOLD_TEXT = {"dark": config.BRAND_GOLD, "image": config.BRAND_GOLD,\n                 "light": config.BRAND_DARK_GOLD_DEEP}\n    GOLD = ("RNV", "Professional Color Extraction Application", "Feature Overview",\n            "Keyboard Shortcuts", "Credits & Acknowledgments", "# Color Extraction",\n            "# Themes & Display", "File Operations", "Color Swatches")\n    MUTED = ("PyQt6", "Ctrl+O", "Ctrl+Shift+C", "F12", "Shift + Drag", "Pillow (PIL)",\n             "NumPy, scikit-learn")\n    #: from a dialog built in dark, every ordered pair of different modes\n    WALK = ("light", "image", "dark", "light", "dark", "image", "light")\n\n    @classmethod\n    def _build(cls, qtbot, monkeypatch, mode):\n        """A dialog built in `mode`, as the `dialog` fixture builds one."""\n        parent = _make_mock_parent(mode, with_window_icon=False)\n        parent.theme_manager.get_current_theme = MagicMock(return_value=cls.THEMES[mode])\n        monkeypatch.setattr(os.path, "exists", lambda p: False)\n        dlg = AboutDialog(parent=parent)\n        dlg._test_real_parent = parent\n        qtbot.addWidget(dlg)\n        return dlg\n\n    @classmethod\n    def _switch(cls, dlg, mode):\n        """What the app does on a switch with the dialog open: the theme\n        manager moves, then the app calls _apply_theme()."""\n        tm = dlg.parent().theme_manager\n        tm.current_theme = mode\n        tm.get_current_theme.return_value = cls.THEMES[mode]\n        dlg._apply_theme()\n\n    @staticmethod\n    def _styles(dlg):\n        return [dlg.styleSheet()] + [(type(w).__name__, w.objectName(), w.styleSheet())\n                                     for w in dlg.findChildren(QWidget)]\n\n    @staticmethod\n    def _label(dlg, text):\n        found = [w for w in dlg.findChildren(QLabel) if w.text() == text]\n        assert len(found) == 1, (text, len(found))\n        return found[0]\n\n    @staticmethod\n    def _ink(widget) -> str:\n        from PyQt6.QtGui import QPalette\n        widget.ensurePolished()\n        return widget.palette().color(QPalette.ColorRole.WindowText).name()\n\n    @pytest.mark.parametrize("built, to", [(a, b) for a in ("dark", "light", "image")\n                                           for b in ("dark", "light", "image") if a != b])\n    def test_a_switched_dialog_is_styled_as_one_built_in_that_mode(self, qtbot, monkeypatch,\n                                                                   built, to):\n        switched = self._build(qtbot, monkeypatch, built)\n        self._switch(switched, to)\n        fresh = self._build(qtbot, monkeypatch, to)\n        a, b = self._styles(switched), self._styles(fresh)\n        assert len(a) == len(b), (len(a), len(b))\n        differ = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]\n        assert not differ, differ[:3]\n\n    def test_the_gold_text_follows_every_switch(self, qtbot, monkeypatch):\n        dlg = self._build(qtbot, monkeypatch, "dark")\n        footer = [w for w in dlg.findChildren(QLabel) if "rights reserved" in w.text()]\n        assert len(footer) == 1\n        for mode in self.WALK:\n            self._switch(dlg, mode)\n            for label in [self._label(dlg, t) for t in self.GOLD] + footer:\n                ink = self._ink(label)\n                assert ink == self.GOLD_TEXT[mode].lower(), (mode, label.text()[:30], ink)\n\n    def test_the_muted_text_follows_every_switch(self, qtbot, monkeypatch):\n        dlg = self._build(qtbot, monkeypatch, "dark")\n        for mode in self.WALK:\n            self._switch(dlg, mode)\n            for text in self.MUTED:\n                ink = self._ink(self._label(dlg, text))\n                assert ink == self.THEMES[mode]["text_muted"].lower(), (mode, text, ink)\n\n    def test_the_close_button_follows_every_switch(self, qtbot, monkeypatch):\n        dlg = self._build(qtbot, monkeypatch, "dark")\n        close = [b for b in dlg.findChildren(QPushButton) if b.text() == "Close"]\n        assert len(close) == 1\n        for mode in self.WALK:\n            self._switch(dlg, mode)\n            image = close[0].grab().toImage()\n            ground = image.pixelColor(3, image.height() // 2).name()\n            assert ground == self.THEMES[mode]["dialog_btn_bg"].lower(), (mode, ground)\n\n    def test_every_label_on_the_about_tab_gets_its_height(self, qtbot, monkeypatch):\n        """RNV-ABOUT-SCROLL. The tab needs about 507px and the dialog gives it\n        260; without a scroll area every label was squeezed to 2-3px."""\n        dlg = self._build(qtbot, monkeypatch, "dark")\n        dlg.show()\n        qtbot.waitExposed(dlg)\n        dlg.tab_widget.setCurrentIndex(0)\n        QApplication.processEvents()\n        page = dlg.tab_widget.widget(0)\n        assert page.findChildren(QScrollArea), "the About tab does not scroll"\n        labels = page.findChildren(QLabel)\n        assert len(labels) >= 15, len(labels)\n        for label in labels:\n            need = (label.heightForWidth(label.width()) if label.hasHeightForWidth()\n                    else label.sizeHint().height())\n            assert label.height() >= need, (label.text()[:40], label.height(), need)\n\n    def test_the_divider_draws_its_grey_in_every_mode(self, qtbot, monkeypatch):\n        dlg = self._build(qtbot, monkeypatch, "dark")\n        lines = [f for f in dlg.findChildren(QFrame) if f.frameShape() == QFrame.Shape.HLine]\n        assert len(lines) == 1, len(lines)\n        for step, mode in enumerate(("dark",) + self.WALK):\n            if step:                                        # built in dark; then the walk\n                self._switch(dlg, mode)\n            image = lines[0].grab().toImage()\n            row = {image.pixelColor(x, image.height() // 2).name() for x in range(image.width())}\n            want = self.THEMES[mode]["border_hover"].lower()\n            assert row == {want}, (mode, sorted(row), want)\n')


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

    DIALOG = "ui/about_dialog.py"
    old_d, new_d = _original(tree, DIALOG), tree.read(DIALOG)
    old_t, new_t = ast.parse(old_d), ast.parse(new_d)
    MODE = {"_get_accent_text", "_get_theme"}

    def the_class(t):
        return next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == "AboutDialog")

    def methods(t):
        return {n.name: n for n in the_class(t).body if isinstance(n, ast.FunctionDef)}

    def reads_mode(node):
        return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr in MODE and ast.unparse(c.func.value) == "self"
                   for c in ast.walk(node))

    def calls(fn, name):
        return sum(1 for c in ast.walk(fn) if isinstance(c, ast.Call)
                   and isinstance(c.func, ast.Attribute) and c.func.attr == name)

    om, nm = methods(old_t), methods(new_t)

    # --- the register and the loop that uses it
    assert [ast.unparse(s) for s in nm["_style_for_mode"].body[1:]] == [
        "widget.setStyleSheet(sheet())", "self._mode_styled.append((widget, sheet))"]
    init = nm["__init__"].body
    at = [i for i, s in enumerate(init) if "self._mode_styled" in ast.unparse(s)]
    build = [i for i, s in enumerate(init) if ast.unparse(s) == "self._build_ui()"]
    assert len(at) == 1 and len(build) == 1 and at[0] < build[0], "the register is made after the build"
    assert ast.unparse(nm["_apply_theme"].body[-1]) == (
        "for widget, sheet in getattr(self, '_mode_styled', ()):\n"
        "    widget.setStyleSheet(sheet())"), "_apply_theme() does not restyle what was styled for a mode"

    # --- 2. the divider: Plain, and still border_hover
    div = ast.unparse(nm["_create_divider"])
    assert "QFrame.Shadow.Plain" in div and "QFrame.Shadow.Sunken" not in div, "the divider is still sunken"
    assert "border_hover" in div

    # --- 3. the About tab scrolls, and says what it said
    tab = nm["_create_about_tab"]
    assert calls(tab, "setWidget") == 1 and "QScrollArea()" in ast.unparse(tab), "the About tab does not scroll"
    assert ast.unparse(tab.body[-1]) == "return widget"
    texts = lambda fn: sorted(ast.unparse(c.args[0]) for c in ast.walk(fn)   # noqa: E731
                              if isinstance(c, ast.Call) and getattr(c.func, "id", None) == "QLabel" and c.args)
    assert texts(om["_create_about_tab"]) == texts(tab), "the About tab lost or changed a line of text"

    # --- what moved: eight methods, one new helper, one import; nothing else
    assert set(nm) - set(om) == {"_style_for_mode"} and not set(om) - set(nm), set(nm) ^ set(om)
    moved = sorted(n for n in om if ast.dump(om[n]) != ast.dump(nm[n]))
    assert moved == sorted(["__init__", "_build_ui", "_create_about_tab", "_create_features_tab",
                            "_create_shortcuts_tab", "_create_credits_tab", "_create_divider",
                            "_apply_theme"]), moved
    outside = lambda t: [ast.dump(n) for n in t.body if n is not the_class(t)]   # noqa: E731
    added = [n for n in outside(new_t) if n not in outside(old_t)]
    assert len(outside(new_t)) == len(outside(old_t)) + 1 and len(added) == 1 \
        and "Callable" in added[0], "the module moved beyond the dialog"

    # --- 1. the same sheets as before, now built again on every switch
    def with_locals(fn, expr):
        local = {n.targets[0].id: n.value for n in ast.walk(fn)
                 if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and reads_mode(n.value)}

        class Sub(ast.NodeTransformer):
            def visit_Name(self, node):
                return copy.deepcopy(local[node.id]) if node.id in local else node
        return Sub().visit(copy.deepcopy(expr))

    def direct(fn):
        out = []
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "setStyleSheet" and c.args:
                arg = with_locals(fn, c.args[0])
                if reads_mode(arg):
                    out.append((ast.unparse(c.func.value), ast.dump(arg)))
        return sorted(out)

    def registered(fn):
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
        if name in ("__init__", "_apply_theme"):
            continue
        before, after = direct(om[name]), sorted(direct(nm[name]) + registered(nm[name]))
        assert before == after, f"{name}: a stylesheet changed on the way"
        count += len(registered(nm[name]))
    assert count == 13, f"{count} stylesheets registered, not 13"

    # ... and what is still set straight away is set again by _apply_theme()
    at_build = {target for target, _ in direct(nm["_build_ui"])}
    redone = {target for target, _ in direct(nm["_apply_theme"])} | {
        ast.unparse(c.func.value) for c in ast.walk(nm["_apply_theme"])
        if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "setStyleSheet"}
    assert at_build <= redone, f"read at build and never again: {sorted(at_build - redone)}"
    for name in ("_create_about_tab", "_create_features_tab", "_create_shortcuts_tab",
                 "_create_credits_tab", "_create_divider"):
        assert not direct(nm[name]), f"{name}: a stylesheet reads the mode at build and nothing redraws it"

    # --- the guard: appended, nothing above it touched
    old_g, new_g = _original(tree, "tests/test_about_dialog.py"), tree.read("tests/test_about_dialog.py")
    assert new_g.startswith(old_g), "the guard file changed above its new class"
    ast.parse(new_g)
    assert SENTINEL in new_g[len(old_g):] and "class TestAboutFollowsASwitch" in new_g[len(old_g):]
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
