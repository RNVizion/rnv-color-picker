"""Save applies, Apply leaves the mode unsaved, and the Sessions divider draws its grey

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (abc3092).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-27: "Yes fix session divider" and "Also apply does not save
but save does apply".

The divider. The line under the session buttons was a sunken line. Qt draws
a sunken line in its own shading -- #9f9f9f over #ffffff in every mode, a
white line on the dark panel -- so the border_hover its stylesheet asks for
was never drawn. It is a plain line now: 1px of #444444 on the dark panel,
#aaaaaa in light, and it follows a switch like the rest of the panel.

Save and Apply. Apply goes on doing what it did: it saves every setting but
the mode and hands them all to the app, the mode switch included, which
lasts until the app closes. Save Settings used to do less than Apply -- it
skipped the mode and handed nothing to the app. It now writes every
setting, the mode included, and hands them over exactly as Apply does.

On the way: the panel hands "preserve_colors" to the app, and the app
listened for "preserve_colors_on_extract", which nothing sends. Ticking
"Preserve colors when extracting" and pressing Apply never reached the main
window's own Preserve Colors checkbox. It does now, from Apply and Save.

Measured with the app's own buttons: Save with the box on another mode
switches the app and writes the mode to the settings file; Apply switches
it and leaves the file alone; the Preserve setting reaches the main window
from both. Rendered: the Sessions tab changes in every mode, at the divider
only -- 1,196 pixels, the two rows of the old bevel -- and after every
switch every tab still matches a panel opened fresh.
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
SENTINEL = 'RNV-SAVE-APPLIES'
SENTINEL_FILE = 'tests/test_settings_panel.py'
GUARD = 'tests/test_settings_panel.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_settings_panel.py']
DESCRIPTION = 'Save applies, Apply leaves the mode unsaved, and the Sessions divider draws its grey'

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

SHADOWS = {"config.py", "conftest.py", "settings_panel.py", "test_rnv_color_picker.py", "RNV_Color_Picker.py"}

LEFT_ALONE = ['the About dialog. Switch with it open and its Close button, gold headings, shortcut keys and credit names keep the old mode, 4 tabs of 4 whenever light is involved -- the fault the Settings panel had. Its divider is built like the Sessions one and draws the same white line. Making it draw its grey alone would add one more stale colour, so both wait for a ruling.', "Apply's other settings: it still saves them, as it always has. Only the mode is left unsaved."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('ui/settings_panel.py',
             '        line.setFrameShape(QFrame.Shape.HLine)\n        line.setFrameShadow(QFrame.Shadow.Sunken)\n',
             '        line.setFrameShape(QFrame.Shape.HLine)\n        # RNV-SESSION-DIVIDER 2026-09-27: Plain, so the line is drawn in the\n        # colour below. It was Sunken, and Qt draws a sunken line in its own\n        # shading -- #9f9f9f, #efefef and #ffffff in every mode, a white line\n        # on the dark panel -- so border_hover was never drawn.\n        line.setFrameShadow(QFrame.Shadow.Plain)\n')
    tree.sub('ui/settings_panel.py',
             '    def _save_settings_to_file(self) -> None:\n        """Save settings to file."""\n        self._save_ui_to_settings(skip_theme=True)\n        if DIALOG_HELPER_AVAILABLE and DialogHelper:\n            DialogHelper.show_info(self, "Settings have been saved successfully.", title="Settings Saved")\n        else:\n            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")\n',
             '    def _save_settings_to_file(self) -> None:\n        """Save settings to file, the Default Theme with them, and apply them.\n\n        RNV-SAVE-APPLIES, 2026-09-27: "apply does not save but save does\n        apply". Apply hands the settings to the app and leaves the mode\n        unsaved. Save writes every setting, the mode included, then hands\n        them to the app exactly as Apply does. It used to skip the mode, as\n        Apply does, and apply nothing.\n        """\n        self._save_ui_to_settings()\n        self._apply_to_app()\n        if DIALOG_HELPER_AVAILABLE and DialogHelper:\n            DialogHelper.show_info(self, "Settings have been saved and applied.", title="Settings Saved")\n        else:\n            QMessageBox.information(self, "Settings Saved", "Settings have been saved and applied.")\n')
    tree.sub('ui/settings_panel.py',
             '    def _apply_settings(self) -> None:\n        """Apply settings and emit signals."""\n        # Save settings\n        self._save_ui_to_settings(skip_theme=True)\n        \n        # Emit signals for changed settings\n',
             '    def _apply_settings(self) -> None:\n        """Apply settings and emit signals."""\n        # Save settings -- all but the mode. RNV-SAVE-APPLIES: "apply does\n        # not save". The mode Apply switches to lasts until the app closes;\n        # Save Settings is what keeps it.\n        self._save_ui_to_settings(skip_theme=True)\n        self._apply_to_app()\n        \n        if logger:\n            logger.success("Settings applied")\n        \n        if DIALOG_HELPER_AVAILABLE and DialogHelper:\n            DialogHelper.show_info(self, "Settings have been applied.", title="Applied")\n        else:\n            QMessageBox.information(self, "Applied", "Settings have been applied.")\n    \n    def _apply_to_app(self) -> None:\n        """Hand this panel\'s settings to the app: settings_changed for the five\n        it acts on while it runs, and theme_change_requested when the Default\n        Theme box differs from the mode the app is in.\n\n        RNV-SAVE-APPLIES, 2026-09-27: split out of _apply_settings() so that\n        Save Settings applies exactly what Apply does.\n        """\n        # Emit signals for changed settings\n')
    tree.sub('ui/settings_panel.py',
             '        if selected_theme != current_theme:\n            self.theme_change_requested.emit(selected_theme)\n        \n        if logger:\n            logger.success("Settings applied")\n        \n        if DIALOG_HELPER_AVAILABLE and DialogHelper:\n            DialogHelper.show_info(self, "Settings have been applied.", title="Applied")\n        else:\n            QMessageBox.information(self, "Applied", "Settings have been applied.")\n',
             '        if selected_theme != current_theme:\n            self.theme_change_requested.emit(selected_theme)\n')
    tree.sub('RNV_Color_Picker.py',
             '            elif key == "preserve_colors_on_extract":\n',
             '            # RNV-SAVE-APPLIES 2026-09-27: the settings panel sends\n            # "preserve_colors" -- the key the settings file and this\n            # window\'s own checkbox use. This listened for\n            # "preserve_colors_on_extract", which nothing sends, so the\n            # setting never reached the checkbox from Apply.\n            elif key == "preserve_colors":\n')
    tree.sub('tests/test_settings_panel.py',
             '    """`_save_settings_to_file` is the \'Save Settings\' button handler. Calls\n    `_save_ui_to_settings(skip_theme=True)` then shows an info dialog."""\n\n    def test_calls_save_with_skip_theme(self, panel, monkeypatch):\n',
             '    """`_save_settings_to_file` is the \'Save Settings\' button handler. Calls\n    `_save_ui_to_settings()` -- the Default Theme included -- then applies\n    what it saved, then shows an info dialog. RNV-SAVE-APPLIES, 2026-09-27:\n    until then it skipped the theme, as Apply does, and applied nothing."""\n\n    def test_calls_save_with_the_theme(self, panel, monkeypatch):\n')
    tree.sub('tests/test_settings_panel.py',
             '        panel._save_settings_to_file()\n        assert captured == [True]\n',
             '        panel._save_settings_to_file()\n        assert captured == [False]\n')
    tree.sub('tests/test_settings_panel.py',
             '    def test_reset_still_loads_the_saved_default_into_the_box(self, qtbot, monkeypatch):\n        panel = self._build(qtbot, "light")\n        monkeypatch.setitem(panel.settings_manager.settings, "theme", "dark")\n        panel._load_settings_into_ui()\n        assert panel.theme_combo.currentText() == "Dark Mode"\n',
             '    def test_reset_still_loads_the_saved_default_into_the_box(self, qtbot, monkeypatch):\n        panel = self._build(qtbot, "light")\n        monkeypatch.setitem(panel.settings_manager.settings, "theme", "dark")\n        panel._load_settings_into_ui()\n        assert panel.theme_combo.currentText() == "Dark Mode"\n\n\n# RNV-SAVE-APPLIES\n# ═════════════════════════════════════════════════════════════════════════════\n# SAVE APPLIES; APPLY LEAVES THE MODE UNSAVED; THE SESSIONS DIVIDER DRAWS ITS GREY\n# ═════════════════════════════════════════════════════════════════════════════\nclass TestSaveAppliesAndTheDivider:\n    """RNV-SAVE-APPLIES and RNV-SESSION-DIVIDER, 2026-09-27.\n\n    "apply does not save but save does apply": Save Settings writes every\n    setting, the Default Theme included, and hands them to the app exactly\n    as Apply does. Apply still leaves the mode unsaved. And every setting\n    the panel hands over is one the app acts on -- the panel sent\n    "preserve_colors" while the app listened for "preserve_colors_on_extract".\n\n    "Yes fix session divider": the divider was a sunken line, which Qt draws\n    in its own shading in every mode, so its border_hover was never drawn."""\n\n    SENT = ["max_colors", "default_sort_method", "preserve_colors", "show_tooltips",\n            "show_debug_overlay"]\n\n    @staticmethod\n    def _quiet(panel, monkeypatch):\n        """Save and Apply with no dialog and no file: what they write and send."""\n        written, sent, asked = [], [], []\n        monkeypatch.setattr(panel.settings_manager, "set", lambda k, v: written.append((k, v)))\n        monkeypatch.setattr(panel.settings_manager, "save_settings", lambda: None)\n        monkeypatch.setattr(_DH, "show_info", lambda *a, **k: None)\n        panel.settings_changed.connect(lambda k, v: sent.append((k, v)))\n        panel.theme_change_requested.connect(asked.append)\n        return written, sent, asked\n\n    @staticmethod\n    def _set_controls(panel):\n        panel.max_colors_input.setText("256")\n        panel.sort_combo.setCurrentIndex(1)                 # HSL\n        panel.preserve_colors_check.setChecked(True)\n        panel.show_tooltips_check.setChecked(False)\n        panel.debug_overlay_check.setChecked(True)\n        panel.theme_combo.setCurrentText("Image Mode")\n\n    def test_save_writes_the_mode_and_applies_it(self, qtbot, monkeypatch):\n        panel = TestPanelFollowsASwitch._build(qtbot, "dark")\n        written, sent, asked = self._quiet(panel, monkeypatch)\n        panel.theme_combo.setCurrentText("Light Mode")\n        panel._save_settings_to_file()\n        assert ("theme", "light") in written\n        assert asked == ["light"]\n        assert [k for k, _ in sent] == self.SENT\n\n    def test_save_applies_exactly_what_apply_applies(self, qtbot, monkeypatch):\n        applied = TestPanelFollowsASwitch._build(qtbot, "dark")\n        saved = TestPanelFollowsASwitch._build(qtbot, "dark")\n        for panel in (applied, saved):\n            self._set_controls(panel)\n        # one settings manager serves both panels, so one after the other\n        written_a, sent_a, asked_a = self._quiet(applied, monkeypatch)\n        applied._apply_settings()\n        written_s, sent_s, asked_s = self._quiet(saved, monkeypatch)\n        saved._save_settings_to_file()\n        assert sent_a == sent_s and asked_a == asked_s == ["image"], (sent_a, sent_s)\n        assert [k for k, _ in sent_a] == self.SENT\n        # the one difference: Save writes the mode, Apply does not\n        assert [w for w in written_s if w[0] != "theme"] == written_a\n        assert ("theme", "image") in written_s and "theme" not in [k for k, _ in written_a]\n\n    def test_apply_still_leaves_the_mode_unsaved(self, qtbot, monkeypatch):\n        panel = TestPanelFollowsASwitch._build(qtbot, "dark")\n        written, _sent, asked = self._quiet(panel, monkeypatch)\n        panel.theme_combo.setCurrentText("Light Mode")\n        panel._apply_settings()\n        assert asked == ["light"]\n        assert "theme" not in [k for k, _ in written]\n\n    def test_save_on_the_current_mode_switches_nothing(self, qtbot, monkeypatch):\n        panel = TestPanelFollowsASwitch._build(qtbot, "light")\n        written, _sent, asked = self._quiet(panel, monkeypatch)\n        panel._save_settings_to_file()\n        assert asked == []\n        assert ("theme", "light") in written\n\n    def test_every_setting_the_panel_sends_is_one_the_app_acts_on(self, qtbot, monkeypatch):\n        from types import SimpleNamespace\n        import RNV_Color_Picker\n        panel = TestPanelFollowsASwitch._build(qtbot, "dark")\n        self._set_controls(panel)\n        _written, sent, _asked = self._quiet(panel, monkeypatch)\n        panel._apply_settings()\n        app = SimpleNamespace(MAX_COLORS=333, sort_method="hilbert", preserve_colors=False,\n                              tooltips_enabled=True, sort_checkbox=MagicMock(),\n                              preserve_checkbox=MagicMock(), debug_label=MagicMock(),\n                              _apply_tooltips=MagicMock())\n        for key, value in sent:\n            RNV_Color_Picker.ColorPickerApp._on_setting_changed(app, key, value)\n        assert app.MAX_COLORS == 256\n        assert app.sort_method == "hsl"\n        assert app.preserve_colors is True\n        app.preserve_checkbox.setChecked.assert_called_with(True)\n        assert app.tooltips_enabled is False and app._apply_tooltips.called\n        app.debug_label.setVisible.assert_called_with(True)\n\n    def test_the_sessions_divider_draws_its_grey_in_every_mode(self, qtbot):\n        panel = TestPanelFollowsASwitch._build(qtbot, "dark")\n        lines = [f for f in panel.findChildren(QFrame) if f.frameShape() == QFrame.Shape.HLine]\n        assert len(lines) == 1, len(lines)\n        for step, mode in enumerate(("dark",) + TestPanelFollowsASwitch.WALK):\n            if step:                                        # built in dark; then the walk\n                TestPanelFollowsASwitch._switch(panel, mode)\n            image = lines[0].grab().toImage()\n            row = {image.pixelColor(x, image.height() // 2).name() for x in range(image.width())}\n            want = TestPanelFollowsASwitch.THEMES[mode]["border_hover"].lower()\n            assert row == {want}, (mode, sorted(row), want)\n')


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
    PANEL, APP, GUARD = "ui/settings_panel.py", "RNV_Color_Picker.py", "tests/test_settings_panel.py"
    old_p, new_p = _original(tree, PANEL), tree.read(PANEL)
    old_t, new_t = ast.parse(old_p), ast.parse(new_p)

    def a_class(t, name):
        return next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == name)

    def methods(t, cls):
        return {n.name: n for n in a_class(t, cls).body if isinstance(n, ast.FunctionDef)}

    def dumps(stmts):
        return [ast.dump(s) for s in stmts]

    # --- what moved in the panel: three methods, one new; nothing else
    om, nm = methods(old_t, "SettingsPanel"), methods(new_t, "SettingsPanel")
    assert set(nm) - set(om) == {"_apply_to_app"} and not set(om) - set(nm), set(nm) ^ set(om)
    moved = sorted(n for n in om if ast.dump(om[n]) != ast.dump(nm[n]))
    assert moved == ["_apply_settings", "_create_section_divider", "_save_settings_to_file"], moved
    outside = lambda t: [ast.dump(n) for n in t.body if not (isinstance(n, ast.ClassDef)   # noqa: E731
                                                            and n.name == "SettingsPanel")]
    assert outside(old_t) == outside(new_t), "the module moved beyond the panel"

    # --- the divider: Plain, and nothing else about it moved
    div_old, div_new = ast.unparse(om["_create_section_divider"]), ast.unparse(nm["_create_section_divider"])
    assert "QFrame.Shadow.Sunken" in div_old
    assert div_new == div_old.replace("QFrame.Shadow.Sunken", "QFrame.Shadow.Plain"), \
        "the divider changed beyond its shadow"

    # --- Apply: the same steps, the hand-over moved into _apply_to_app()
    old_apply, new_apply, hand = om["_apply_settings"].body, nm["_apply_settings"].body, nm["_apply_to_app"].body
    assert ast.unparse(new_apply[1]) == "self._save_ui_to_settings(skip_theme=True)", \
        "Apply saves the mode"
    assert ast.unparse(new_apply[2]) == "self._apply_to_app()", "Apply does not hand the settings over"
    assert dumps(hand[1:]) == dumps(old_apply[2:-2]), "a setting changed on its way into _apply_to_app()"
    assert dumps(new_apply[:2] + new_apply[3:]) == dumps(old_apply[:2] + old_apply[-2:]), \
        "Apply changed beyond the hand-over"

    # --- Save: every setting, the mode included, then the same hand-over
    save = nm["_save_settings_to_file"].body
    assert ast.unparse(save[1]) == "self._save_ui_to_settings()", "Save does not write the mode"
    assert ast.unparse(save[2]) == "self._apply_to_app()", "Save does not apply"
    assert dumps(save[3:]) == dumps([ast.parse(ast.unparse(s).replace(
        "saved successfully", "saved and applied")).body[0] for s in om["_save_settings_to_file"].body[2:]])

    # --- the app acts on every setting the panel hands it
    sent = {c.args[0].value for c in ast.walk(nm["_apply_to_app"]) if isinstance(c, ast.Call)
            and getattr(c.func, "attr", None) == "emit" and ast.unparse(c.func.value) == "self.settings_changed"}
    old_a, new_a = _original(tree, APP), tree.read(APP)
    handler = methods(ast.parse(new_a), "ColorPickerApp")["_on_setting_changed"]
    heard = {n.comparators[0].value for n in ast.walk(handler) if isinstance(n, ast.Compare)
             and ast.unparse(n.left) == "key" and isinstance(n.comparators[0], ast.Constant)}
    assert sent == heard, f"the panel sends {sorted(sent - heard)} and the app does not listen"
    assert ast.dump(ast.parse(new_a.replace('key == "preserve_colors":', 'key == "preserve_colors_on_extract":'))) \
        == ast.dump(ast.parse(old_a)), "the app moved beyond the preserve key"

    # --- the guard: Save's pinned test turned round, one class appended; nothing else
    old_g, new_g = _original(tree, GUARD), tree.read(GUARD)
    og, ng = ast.parse(old_g), ast.parse(new_g)
    assert isinstance(ng.body[-1], ast.ClassDef) and ng.body[-1].name == "TestSaveAppliesAndTheDivider"
    assert SENTINEL in (ast.get_docstring(ng.body[-1]) or "")
    assert dumps([n for n in og.body if getattr(n, "name", None) != "TestSaveSettingsToFile"]) == \
        dumps([n for n in ng.body[:-1] if getattr(n, "name", None) != "TestSaveSettingsToFile"]), \
        "the guard file changed beyond Save's tests"
    ot, nt = methods(og, "TestSaveSettingsToFile"), methods(ng, "TestSaveSettingsToFile")
    assert set(ot) == {"test_calls_save_with_skip_theme", "test_shows_info_dialog"}
    assert set(nt) == {"test_calls_save_with_the_theme", "test_shows_info_dialog"}
    assert ast.dump(ot["test_shows_info_dialog"]) == ast.dump(nt["test_shows_info_dialog"])
    assert ast.unparse(nt["test_calls_save_with_the_theme"].body[-1]) == "assert captured == [False]", \
        "Save's pinned test still expects the mode skipped"
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
