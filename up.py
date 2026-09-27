"""chart ruling 1: the settings panel's descriptions in the muted text

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (2449675).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-09-27, decision 1 of the colour chart: "If they all split it for
each mode then it's fine to have 2 values, but make sure they are values we
are already using." They all split it the same way. Muted text is #888888 in
dark and image and #666666 in light in all five applications, and the
description labels that wrote `color: gray`/`grey` -- #808080 in every mode,
4.40:1 on the dark panels and 3.62:1 in light, under the 4.5 floor -- now read
the app's own muted key. No new colour: both values are already painted.

Here: nine labels on the settings panel -- six tab descriptions, the colour-
blindness one, the harmony description and the caption under each harmony
swatch. Each is named "muted_text", and the panel's own stylesheet, which
update_theme() rebuilds on every switch, draws that name in text_muted.
Rendered: 18 of 171 captures change, 6 per mode, and every changed pixel is the
grey recoloured -- same glyph coverage, new ink, within 2 levels.
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
SENTINEL = 'RNV-MUTED-DESCRIPTIONS'
SENTINEL_FILE = 'tests/test_settings_panel.py'
GUARD = 'tests/test_settings_panel.py'
#: Every guard this round touches, run before CI's own commands.
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             'tests/test_settings_panel.py']
DESCRIPTION = "chart ruling 1: the settings panel's descriptions in the muted text"

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

SHADOWS = {"cache.py", "config.py", "conftest.py", "settings_panel.py", "test_rnv_color_picker.py"}

LEFT_ALONE = ["text_secondary, the picker's second muted key. It holds the same two values and nothing paints it; text_muted is the one that paints.", "the harmony swatches' borders. They take the accent when the harmony is generated, so a theme switch with the panel open leaves the old gold until the next generation -- the same kind of fault as ruling 3, for a ruling.", "the About dialog's muted text, which already reads text_muted."]


def edits(tree) -> None:
    """Every substitution, against the in-memory tree. Each anchor is
    checked for its exact number of occurrences before anything is
    written."""
    tree.sub('utils/cache.py',
             '    @classmethod\n    def get_description_stylesheet(cls) -> str:\n        """Get cached description label stylesheet."""\n        key = (\'static\', \'description\')\n        \n        if key not in cls._cache:\n            cls._cache[key] = "color: gray; font-size: 11px;"\n',
             '    @classmethod\n    def get_description_stylesheet(cls) -> str:\n        """Get cached description label stylesheet: its size, not its colour.\n\n        RNV-MUTED-DESCRIPTIONS, 2026-09-27 (ruling 1). This carried\n        "color: gray" -- #808080 in every mode, under the text floor on the\n        dark panel and in light. The colour is the palette\'s text_muted now,\n        drawn by the settings panel\'s own stylesheet on every label named\n        "muted_text", which is rebuilt on each theme switch."""\n        key = (\'static\', \'description\')\n        \n        if key not in cls._cache:\n            cls._cache[key] = "font-size: 11px;"\n')
    tree.sub('ui/settings_panel.py',
             '        if CACHE_AVAILABLE and StylesheetCache:\n            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())\n        else:\n            desc.setStyleSheet("color: gray; font-size: 11px;")\n',
             '        desc.setObjectName("muted_text")\n        if CACHE_AVAILABLE and StylesheetCache:\n            desc.setStyleSheet(StylesheetCache.get_description_stylesheet())\n        else:\n            desc.setStyleSheet("font-size: 11px;")\n', times=5)
    tree.sub('ui/settings_panel.py',
             '        if CACHE_AVAILABLE and StylesheetCache:\n            blindness_desc.setStyleSheet(StylesheetCache.get_description_stylesheet())\n        else:\n            blindness_desc.setStyleSheet("color: gray; font-size: 11px;")\n',
             '        blindness_desc.setObjectName("muted_text")\n        if CACHE_AVAILABLE and StylesheetCache:\n            blindness_desc.setStyleSheet(StylesheetCache.get_description_stylesheet())\n        else:\n            blindness_desc.setStyleSheet("font-size: 11px;")\n')
    tree.sub('ui/settings_panel.py',
             '        self.harmony_desc_label.setStyleSheet("color: gray; font-size: 11px; padding: 5px;")\n',
             '        self.harmony_desc_label.setObjectName("muted_text")\n        self.harmony_desc_label.setStyleSheet("font-size: 11px; padding: 5px;")\n')
    tree.sub('ui/settings_panel.py',
             '        label.setStyleSheet("font-size: 8px; color: gray;")  # Keep as inline - unique pattern\n',
             '        label.setObjectName("muted_text")\n        label.setStyleSheet("font-size: 8px;")  # Keep as inline - unique pattern\n')
    tree.sub('ui/settings_panel.py',
             "            QLabel {{\n                color: {theme['text_primary']};\n            }}\n            QPushButton {{\n",
             "            QLabel {{\n                color: {theme['text_primary']};\n            }}\n            /* RNV-MUTED-DESCRIPTIONS, ruling 1: descriptions and captions */\n            QLabel#muted_text {{\n                color: {theme['text_muted']};\n            }}\n            QPushButton {{\n")
    tree.sub('tests/test_settings_panel.py',
             '        panel._apply_settings()\n        assert captured == [True]\n',
             '        panel._apply_settings()\n        assert captured == [True]\n\n\n# RNV-MUTED-DESCRIPTIONS\n# ═════════════════════════════════════════════════════════════════════════════\n# MUTED TEXT: the descriptions draw in the mode\'s text_muted (ruling 1)\n# ═════════════════════════════════════════════════════════════════════════════\nclass TestMutedDescriptions:\n    """RNV-MUTED-DESCRIPTIONS, ruling 1 of 2026-09-27. The panel\'s tab\n    descriptions and the harmony captions were `color: gray` -- #808080 in\n    every mode, 4.40:1 on the dark panel and 3.62:1 in light, both under the\n    4.5 floor. They are named "muted_text" now, and the panel\'s own\n    stylesheet draws that name in text_muted: #888888 in dark and image,\n    #666666 in light, the muted text all five applications already paint.\n    That stylesheet is rebuilt by update_theme() on every switch, so the\n    descriptions follow the mode without anything tracking them."""\n\n    THEMES = {"dark": config.DARK_THEME_COLORS, "light": config.LIGHT_THEME_COLORS,\n              "image": config.IMAGE_MODE_COLORS}\n\n    @staticmethod\n    def _muted(panel):\n        return [w for w in panel.findChildren(QLabel) if w.objectName() == "muted_text"]\n\n    @staticmethod\n    def _ink(widget) -> str:\n        from PyQt6.QtGui import QPalette\n        widget.ensurePolished()\n        return widget.palette().color(QPalette.ColorRole.WindowText).name()\n\n    def test_every_description_is_named_and_carries_no_colour_of_its_own(self, panel):\n        labels = self._muted(panel)\n        texts = [w.text() for w in labels]\n        # the six tab descriptions, the colour-blindness one and the harmony one\n        for fragment in ("Click any color", "Save and restore", "Generate harmonious",\n                         "Check WCAG", "See how your colors", "Quick reference"):\n            assert any(fragment in t for t in texts), (fragment, texts)\n        assert panel.harmony_desc_label in labels\n        for w in labels:\n            assert "color" not in w.styleSheet(), (w.text(), w.styleSheet())\n\n    @pytest.mark.parametrize("mode", ["dark", "light", "image", "dark"])\n    def test_a_switch_redraws_them_in_the_modes_muted_text(self, panel, mode):\n        theme = self.THEMES[mode]\n        tm = panel._test_real_parent.theme_manager\n        tm.current_theme = mode\n        tm.get_current_theme.return_value = theme\n        tm.is_image_mode.return_value = (mode == "image")\n        panel.update_theme()\n        labels = self._muted(panel)\n        assert labels, "no description is named muted_text"\n        for w in labels:\n            assert self._ink(w) == theme["text_muted"].lower(), (mode, w.text()[:40])\n        # and nothing else in the panel took the muted colour by accident\n        primary = [w for w in panel.findChildren(QLabel)\n                   if w.objectName() != "muted_text" and not w.styleSheet()]\n        assert primary and all(self._ink(w) == theme["text_primary"].lower()\n                               for w in primary), mode\n\n    def test_the_two_values_are_the_ones_the_fleet_already_uses(self):\n        assert config.DARK_THEME_COLORS["text_muted"] == "#888888"\n        assert config.IMAGE_MODE_COLORS["text_muted"] == "#888888"\n        assert config.LIGHT_THEME_COLORS["text_muted"] == "#666666"\n\n    def test_no_label_is_written_in_a_css_grey(self):\n        """The literal the ruling retired, anywhere the application EVALUATES a\n        string. Docstrings and comments may still name it; code may not."""\n        import ast\n        import pathlib\n        import re\n        root = pathlib.Path(__file__).resolve().parents[1]\n        css_grey = re.compile(r"color\\s*:\\s*(gray|grey)\\b", re.I)\n        found, files = [], 0\n        for path in sorted(root.rglob("*.py")):\n            rel = path.relative_to(root)\n            if any(p in {"tests", ".git", "__pycache__", "build", "dist", ".venv"}\n                   for p in rel.parts):\n                continue\n            if len(rel.parts) == 1 and rel.name.startswith(("test_", "up")):\n                continue\n            text = path.read_text(encoding="utf-8-sig", errors="replace")\n            if "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP" in text:\n                continue\n            files += 1\n            tree = ast.parse(text)\n            docs = {id(st.value) for node in ast.walk(tree)\n                    for st in (node.body if isinstance(getattr(node, "body", None), list) else [])\n                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)}\n            found += [f"{rel}:{node.lineno}" for node in ast.walk(tree)\n                      if isinstance(node, ast.Constant) and isinstance(node.value, str)\n                      and id(node) not in docs and css_grey.search(node.value)]\n        assert files >= 20, f"only {files} files swept -- the walk has gone blind"\n        assert not found, "CSS grey still written as a colour:\\n  " + "\\n  ".join(found)\n')


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
    def css_greys(src):
        tree = ast.parse(src)
        docs = {id(st.value) for node in ast.walk(tree)
                for st in (node.body if isinstance(getattr(node, "body", None), list) else [])
                if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)}
        pat = re.compile(r"color\s*:\s*(gray|grey)\b", re.I)
        return [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in docs and pat.search(n.value)]

    # the panel: eight labels named, their colour gone from their own sheets,
    # and NOTHING else in the file moved
    old_p, new_p = _original(tree, "ui/settings_panel.py"), tree.read("ui/settings_panel.py")
    assert css_greys(old_p) and not css_greys(new_p), css_greys(new_p)
    assert new_p.count('.setObjectName("muted_text")') == 8
    rule = ("            /* RNV-MUTED-DESCRIPTIONS, ruling 1: descriptions and captions */\n"
            "            QLabel#muted_text {{\n"
            "                color: {theme['text_muted']};\n"
            "            }}\n")
    assert new_p.count(rule) == 1, "the muted rule is not in the dialog stylesheet"
    named = [l for l in new_p.splitlines() if l.strip().endswith('.setObjectName("muted_text")')]
    back = "\n".join(l for l in new_p.replace(rule, "").splitlines() if l not in named)
    was = old_p.replace("color: gray; ", "").replace(" color: gray;", "")
    assert back == was.rstrip("\n") or back + "\n" == was, "the panel moved beyond the colour"
    fn = _function(new_p, "_build_dialog_stylesheet", "SettingsPanel")
    assert "QLabel#muted_text" in ast.unparse(fn)

    # the cache: the size, no colour
    old_c, new_c = _original(tree, "utils/cache.py"), tree.read("utils/cache.py")
    assert css_greys(old_c) and not css_greys(new_c)
    fn = _function(new_c, "get_description_stylesheet", "StylesheetCache")
    values = [n.value.value for n in ast.walk(fn) if isinstance(n, ast.Assign)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]
    assert values == ["font-size: 11px;"], values

    guard = tree.read("tests/test_settings_panel.py")
    ast.parse(guard)
    assert SENTINEL in guard and "class TestMutedDescriptions" in guard
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
