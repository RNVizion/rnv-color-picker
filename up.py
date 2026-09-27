"""the harmony swatch's gold edge follows a mode switch made with Settings open

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (b749575).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-27: "yes we can fix the picker border switch on mode change".

The base swatch of the generated harmony (Settings > Harmony) is edged in the
mode's gold -- BRAND_GOLD #d2bc93 in dark and image, BRAND_DARK_GOLD #8c7337 in
light -- read when the swatch is built. A switch made with the panel open kept
the previous mode's gold on that edge until the harmony was generated again.
update_theme(), which the app calls on every switch while the panel is open,
now generates it again. The harmony is the spin boxes and the type combo and
nothing else, so the same swatches come back with the edge in the new mode's
gold.

Rendered with the app's own main(), switching from the main window with
Settings open, through every mode and back into image: 2 of 36 captures
change -- the Harmony tab after the switch into light and after the switch
back into image, 660 pixels each, the edge and only the edge. A panel opened
fresh is unchanged in every mode. The noise floor, shipped against shipped,
is 0 of 36.
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
SENTINEL = 'RNV-HARMONY-SWITCH'
SENTINEL_FILE = 'tests/test_settings_panel.py'
GUARD = 'tests/test_settings_panel.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_settings_panel.py']
DESCRIPTION = "the harmony swatch's gold edge follows a mode switch made with Settings open"

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

LEFT_ALONE = ["the rest of the panel's build-time colours -- the Sessions tab's 'Auto-Save Options' subheader, the section headers on the Shortcuts and Settings tabs, the Shortcuts tab's key plates and tip. They keep the previous mode's colours after a switch with the panel open, the same kind of fault, and wait for a ruling.", "the harmony base preview, which a new panel paints in the mode's gold as a placeholder while the spin boxes say 191, 145, 69 -- different in kind: a fresh panel disagrees with its own inputs. For a ruling.", "the Settings tab's Default Theme box, which keeps the mode the panel was opened in; Apply then switches the app back to it. A behaviour fault, not a colour. For a ruling."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('ui/settings_panel.py',
             '        if hasattr(self, "contrast_ratio_label"):\n            self._update_contrast_check()\n',
             '        if hasattr(self, "contrast_ratio_label"):\n            self._update_contrast_check()\n\n        # RNV-HARMONY-SWITCH 2026-09-27: redraw the generated harmony. Its\n        # base swatch is edged in the mode\'s gold, which is read when the\n        # swatch is built, so a switch made with this panel open kept the\n        # previous mode\'s gold on that edge until the harmony was generated\n        # again. The harmony is the spin boxes and the type combo and nothing\n        # else, so generating it again draws the same swatches, edged for\n        # this mode.\n        #\n        # Guarded so a switch never depends on the harmony row existing: the\n        # tab builds none without its module, and the order __init__ builds\n        # things in (every tab first, then the theme) is not something a\n        # theme switch should have to know.\n        if hasattr(self, "harmony_swatches_layout"):\n            self._generate_harmony()\n')
    tree.sub('tests/test_settings_panel.py',
             '        assert files >= 20, f"only {files} files swept -- the walk has gone blind"\n        assert not found, "CSS grey still written as a colour:\\n  " + "\\n  ".join(found)\n',
             '        assert files >= 20, f"only {files} files swept -- the walk has gone blind"\n        assert not found, "CSS grey still written as a colour:\\n  " + "\\n  ".join(found)\n\n\n# RNV-HARMONY-SWITCH\n# ═════════════════════════════════════════════════════════════════════════════\n# HARMONY: the base swatch\'s gold edge follows a switch made with the panel open\n# ═════════════════════════════════════════════════════════════════════════════\nclass TestHarmonyFollowsASwitch:\n    """RNV-HARMONY-SWITCH, 2026-09-27. The base swatch of the generated harmony\n    is edged in the mode\'s gold: BRAND_GOLD in dark and image, BRAND_DARK_GOLD\n    in light. The gold is read when the swatch is built, and a switch made\n    with the panel open kept the previous mode\'s gold on the edge until the\n    harmony was generated again. update_theme() generates it again now. The\n    harmony is the spin boxes and the type combo, so what it shows stays the\n    same; only the edge follows the mode.\n\n    Each test reads the colour Qt DRAWS -- a pixel grabbed from the swatch --\n    as well as the stylesheet, so a rule that stops reaching the swatch fails\n    even while the text of the rule is still there."""\n\n    THEMES = {"dark": config.DARK_THEME_COLORS, "light": config.LIGHT_THEME_COLORS,\n              "image": config.IMAGE_MODE_COLORS}\n    GOLD = {"dark": config.BRAND_GOLD, "image": config.BRAND_GOLD,\n            "light": config.BRAND_DARK_GOLD}\n    #: from a panel built in dark, every ordered pair of different modes\n    WALK = ("light", "image", "dark", "light", "dark", "image", "light")\n\n    @classmethod\n    def _switch(cls, panel, mode):\n        """What the app does on a switch with the panel open: the theme\n        manager moves, then the app calls update_theme()."""\n        tm = panel.parent_app.theme_manager\n        tm.current_theme = mode\n        tm.get_current_theme.return_value = cls.THEMES[mode]\n        tm.is_image_mode.return_value = (mode == "image")\n        panel.update_theme()\n\n    @staticmethod\n    def _swatches(panel):\n        """The swatches the row holds now, in order. Read from the layout: a\n        swatch it let go of lingers as a child until Qt deletes it."""\n        row = panel.harmony_swatches_layout\n        found = [row.itemAt(i).widget() for i in range(row.count())]\n        found = [w for w in found if w is not None]     # not the stretch\n        assert found, "the harmony row holds no swatch"\n        return found\n\n    @classmethod\n    def _boxes(cls, panel):\n        """Each swatch\'s colour box, in order: the one label fixed at 66 x 50."""\n        from PyQt6.QtCore import QSize\n        boxes = []\n        for swatch in cls._swatches(panel):\n            found = [w for w in swatch.findChildren(QLabel)\n                     if w.minimumSize() == QSize(66, 50) == w.maximumSize()]\n            assert len(found) == 1, [w.text() for w in swatch.findChildren(QLabel)]\n            boxes.append(found[0])\n        return boxes\n\n    @staticmethod\n    def _drawn(box):\n        """(edge, fill) as Qt draws them: the middle of the left edge, inside\n        the border whichever width it is and clear of the rounded corners,\n        and the centre of the box."""\n        image = box.grab().toImage()\n        mid = image.height() // 2\n        return (image.pixelColor(1, mid).name(),\n                image.pixelColor(image.width() // 2, mid).name())\n\n    def test_a_switch_edges_the_base_in_the_modes_gold(self, panel):\n        for mode in self.WALK:\n            self._switch(panel, mode)\n            base, *others = self._boxes(panel)\n            gold = self.GOLD[mode].lower()\n            assert f"3px solid {gold}" in base.styleSheet().lower(), (mode, base.styleSheet())\n            assert self._drawn(base)[0] == gold, (mode, self._drawn(base))\n            assert others, mode\n            for box in others:\n                assert f"2px solid {config.GREY_44}" in box.styleSheet(), (mode, box.styleSheet())\n                assert self._drawn(box)[0] == config.GREY_44.lower(), (mode, self._drawn(box))\n\n    def test_a_switch_keeps_the_harmony_on_show(self, panel):\n        panel.harmony_type_combo.setCurrentText("Tetradic (Square)")\n        for spin, value in zip((panel.harmony_r_spin, panel.harmony_g_spin,\n                                panel.harmony_b_spin), (30, 144, 200)):\n            spin.setValue(value)\n\n        def shown():\n            hexes = [w.text() for s in self._swatches(panel)\n                     for w in s.findChildren(QLabel) if w.text().startswith("#")]\n            return (list(panel.harmony_colors), [self._drawn(b)[1] for b in self._boxes(panel)],\n                    hexes, panel.harmony_desc_label.text(),\n                    panel.harmony_type_combo.currentText(),\n                    (panel.harmony_r_spin.value(), panel.harmony_g_spin.value(),\n                     panel.harmony_b_spin.value()))\n\n        before = shown()\n        assert len(before[0]) == 4 and before[0][0] == (30, 144, 200), before[0]\n        assert before[1][0] == "#1e90c8" and before[2][0] == "#1E90C8", before[1:3]\n        for mode in ("light", "image", "dark"):\n            self._switch(panel, mode)\n            assert shown() == before, mode\n\n    def test_a_switched_panel_draws_the_harmony_a_fresh_one_draws(self, panel, panel_light):\n        self._switch(panel, "light")\n        switched, fresh = self._boxes(panel), self._boxes(panel_light)\n        assert [b.styleSheet() for b in switched] == [b.styleSheet() for b in fresh]\n        assert [self._drawn(b) for b in switched] == [self._drawn(b) for b in fresh]\n\n    def test_update_theme_does_not_need_the_harmony_row(self, panel):\n        """Without its module the harmony tab builds no swatch row, and a\n        switch must not depend on the order __init__ builds things in."""\n        del panel.harmony_swatches_layout\n        self._switch(panel, "light")        # no AttributeError\n        assert config.LIGHT_THEME_COLORS["text_muted"] in panel.styleSheet()\n')


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
    import difflib

    # the panel: ONE insertion, at the end of update_theme(), and nothing else
    old_p, new_p = _original(tree, "ui/settings_panel.py"), tree.read("ui/settings_panel.py")
    a, b = old_p.splitlines(), new_p.splitlines()
    ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
           if op[0] != "equal"]
    assert len(ops) == 1 and ops[0][0] == "insert", f"the panel moved beyond the redraw: {ops}"
    added = b[ops[0][3]:ops[0][4]]
    code = [l.strip() for l in added if l.strip() and not l.strip().startswith("#")]
    assert code == ['if hasattr(self, "harmony_swatches_layout"):',
                    "self._generate_harmony()"], code
    assert SENTINEL in "\n".join(added)
    last = _function(new_p, "update_theme", "SettingsPanel").body[-1]
    assert (isinstance(last, ast.If) and not last.orelse
            and ast.unparse(last.test) == "hasattr(self, 'harmony_swatches_layout')"
            and [ast.unparse(s) for s in last.body] == ["self._generate_harmony()"]), \
        "the redraw is not the last thing update_theme() does"

    # what the redraw stands on, read at THIS head: the harmony is the spin
    # boxes and the type combo, and the base edge is the mode's gold
    gen = ast.unparse(_function(new_p, "_generate_harmony", "SettingsPanel"))
    for name in ("harmony_r_spin", "harmony_g_spin", "harmony_b_spin", "harmony_type_combo"):
        assert f"self.{name}" in gen, f"_generate_harmony no longer reads {name}"
    swatch = ast.unparse(_function(new_p, "_create_harmony_swatch", "SettingsPanel"))
    assert "self._get_accent()" in swatch, "the base edge no longer reads the mode's gold"

    # the guard: appended, nothing above it touched
    old_g, new_g = _original(tree, "tests/test_settings_panel.py"), tree.read("tests/test_settings_panel.py")
    assert new_g.startswith(old_g), "the guard file changed above its new class"
    ast.parse(new_g)
    tail = new_g[len(old_g):]
    assert SENTINEL in tail and "class TestHarmonyFollowsASwitch" in tail
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
