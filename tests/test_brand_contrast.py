"""
RNV Color Picker — Brand contrast and derivation guards
========================================================
RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

That marker tells any value-sweeping tool to skip this file. Its whole
purpose is to name retired colours -- #b19145, #c4a458, #4caf50 -- and
assert they never come back. A sweep that rewrites those mentions turns
the guard into "#8c7337 must never equal #8c7337", which passes forever
and protects nothing. Use and mention are different things, and the file
that states a rule about a value must never be searched for that value.

These tests do not check that colours have particular values. They check
what a value test cannot see:

  1. Every constant labelled "derived" is genuinely computed from its
     source, checked by parsing the source rather than comparing at
     runtime. A literal that happens to equal lighten(BRAND_DARK_GOLD, -14)
     is indistinguishable from the real thing once imported -- and it is
     exactly what breaks the next time the source colour moves. This
     repository shipped SIX such literals before this pass.

  2. Every foreground/background pair the app actually renders clears the
     WCAG floor, resolved against the real background in scope and against
     the palette that actually renders it. In almost every defect of this
     kind both colours are individually correct and the pairing fails, so
     a value census reports the repository clean.

The exemption list is asserted in BOTH directions. An unexpected failure
fails the suite, and so does an exemption that no longer matches anything.
Exemption lists go stale in the direction that reports clean, so the
second half is the half that matters.
"""

from __future__ import annotations

import ast
import functools
import re
import subprocess
from pathlib import Path

import pytest

from utils import config as C


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PY = PROJECT_ROOT / "utils" / "config.py"

TEXT_FLOOR = 4.5          # WCAG 1.4.3, normal-size text
COMPONENT_FLOOR = 3.0     # WCAG 1.4.11, UI components and graphics


# ══════════════════════════════════════════════════════════════════════════
# CONTRAST
# ══════════════════════════════════════════════════════════════════════════

def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
          for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted([relative_luminance(fg), relative_luminance(bg)],
                    reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ══════════════════════════════════════════════════════════════════════════
# DERIVATION GUARD
# ══════════════════════════════════════════════════════════════════════════

# Every one of these was a hand-written literal before the alignment. A
# derivative written down is stale the moment its base moves, and nothing
# flags it -- this repository's old light hover, #c4a458, was a tint of the
# retired #b19145 and was orphaned the instant the accent changed.
DERIVED_CONSTANTS = {
    "BRAND_DARK_GOLD_DEEP",
    "BRAND_DARK_GOLD_HOVER",
    "BRAND_DARK_GOLD_PRESSED",
    "BRAND_GOLD_HOVER",
    "BRAND_GOLD_PRESSED",
    "BRAND_GOLD_RGB",
    "BRAND_DARK_GOLD_RGB",
}

# Registered brand values. These must be literals: the register is the
# source, so a registered colour cannot be computed from something else.
REGISTERED_CONSTANTS = {
    "BRAND_GOLD",
    "BRAND_DARK_GOLD",
}


def _config_source() -> str:
    """utils/config.py carries a UTF-8 BOM. read_text('utf-8') leaves it in
    the string as U+FEFF and ast.parse then rejects the whole file."""
    return CONFIG_PY.read_text(encoding="utf-8-sig")


def _module_level_assignments() -> dict[str, ast.expr]:
    tree = ast.parse(_config_source())
    out: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                out[node.target.id] = node.value
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and node.value is not None:
                    out[t.id] = node.value
    return out


@pytest.mark.parametrize("name", sorted(DERIVED_CONSTANTS))
def test_derived_constant_is_not_a_literal(name: str) -> None:
    """Derived means computed. A literal wearing the label is the bug."""
    assigns = _module_level_assignments()
    assert name in assigns, (
        f"{name} is expected in utils/config.py and is not there. If it was "
        f"deliberately removed, remove it from DERIVED_CONSTANTS too.")
    node = assigns[name]
    assert isinstance(node, (ast.Call, ast.Name)), (
        f"{name} is documented as derived but is assigned a literal "
        f"({ast.dump(node)[:70]}). Written down, it stops tracking the "
        f"colour it came from, and the next time that colour moves this "
        f"one silently does not.")


@pytest.mark.parametrize("name", sorted(REGISTERED_CONSTANTS))
def test_registered_constant_is_a_literal(name: str) -> None:
    assigns = _module_level_assignments()
    assert name in assigns, f"{name} missing from utils/config.py"
    node = assigns[name]
    assert isinstance(node, ast.Constant) and isinstance(node.value, str), (
        f"{name} is a registered brand colour and must be written down. "
        f"Deriving it would make the register depend on the app instead "
        f"of the other way round.")


def test_deep_gold_tracks_its_source() -> None:
    assert C.BRAND_DARK_GOLD_DEEP == C.lighten(C.BRAND_DARK_GOLD, -14)
    assert C.BRAND_DARK_GOLD_DEEP != C.BRAND_DARK_GOLD


def test_dark_hover_tracks_its_source() -> None:
    assert C.BRAND_GOLD_HOVER == C.lighten(C.BRAND_GOLD, 13)


def test_dark_pressed_is_the_accent_itself() -> None:
    """Mirrors light. Pressed returns to rest rather than claiming a third
    gold -- see test_two_golds_per_mode below, which is the rule this
    serves."""
    assert C.BRAND_GOLD_PRESSED == C.BRAND_GOLD


def test_light_pressed_is_the_accent_itself() -> None:
    """There is nowhere darker for a light-mode pressed state to go.

    Darkening past BRAND_DARK_GOLD drops black-on-gold under the floor,
    which would force white text and break the register's text-on-gold
    rule. So pressed IS the accent, deliberately.
    """
    assert C.BRAND_DARK_GOLD_PRESSED == C.BRAND_DARK_GOLD


def test_light_hover_moves_away_from_its_ground() -> None:
    """A dark ground takes a lighter hover; a light ground takes a deeper
    one. The retired #c4a458 went lighter on a light ground -- toward it --
    which is why white measured 2.3868 on it."""
    light_bg = C.LIGHT_THEME_COLORS["window_bg"]
    assert (relative_luminance(C.BRAND_DARK_GOLD_HOVER)
            < relative_luminance(C.BRAND_DARK_GOLD))
    assert relative_luminance(C.BRAND_DARK_GOLD_HOVER) < relative_luminance(light_bg)
    dark_bg = C.DARK_THEME_COLORS["window_bg"]
    assert relative_luminance(C.BRAND_GOLD_HOVER) > relative_luminance(C.BRAND_GOLD)
    assert relative_luminance(C.BRAND_GOLD_HOVER) > relative_luminance(dark_bg)


@pytest.mark.parametrize("const,rgb", [
    ("BRAND_GOLD", "BRAND_GOLD_RGB"),
    ("BRAND_DARK_GOLD", "BRAND_DARK_GOLD_RGB"),
])
def test_rgb_tuple_matches_its_hex(const: str, rgb: str) -> None:
    """The RGB-tuple blind spot.

    A hardcoded (177, 145, 69) is invisible to every hex-based search, so
    it survives sweeps that catch every other reference. Deriving it
    removes the hiding place; this keeps it removed.
    """
    r, g, b = getattr(C, rgb)
    assert getattr(C, const).lower() == f"#{r:02x}{g:02x}{b:02x}"


def test_lighten_shifts_every_channel_equally() -> None:
    """Uniform per-channel is what preserves hue, and it is the method the
    light palettes already used before this pass."""
    out = C.lighten("#8c7337", -14)
    a = C._to_rgb("#8c7337")
    b = C._to_rgb(out)
    assert [x - y for x, y in zip(a, b)] == [14, 14, 14]


def test_lighten_clamps_instead_of_wrapping() -> None:
    assert C.lighten("#ffffff", 40) == "#ffffff"
    assert C.lighten("#000000", -40) == "#000000"


# ══════════════════════════════════════════════════════════════════════════
# PAIRING AUDIT
# ══════════════════════════════════════════════════════════════════════════

PALETTES: dict[str, dict[str, str]] = {
    "LIGHT": C.LIGHT_THEME_COLORS,
    "DARK": C.DARK_THEME_COLORS,
    "IMAGE": C.IMAGE_MODE_COLORS,
}

_PIN_CONST = {
    "LIGHT_THEME_COLORS": "LIGHT",
    "DARK_THEME_COLORS": "DARK",
    "IMAGE_MODE_COLORS": "IMAGE",
}
_PIN = re.compile(
    r"^\s*(\w+)\s*=\s*(LIGHT_THEME_COLORS|DARK_THEME_COLORS|IMAGE_MODE_COLORS)\s*$",
    re.M)

# Pairs below the floor on purpose, keyed by the palette that renders them.
# Both halves are asserted. An exemption for a pairing that does not exist
# is worse than no exemption: it is a licence waiting for a real defect.
ACCEPTED: dict[tuple[str, str, str], str] = {
    ("LIGHT", "#000000", "#333333"):
        "main-window button hover. The main window runs a white/near-black "
        "inverse scheme where the text stays black while the background "
        "darkens. Deliberate, and separate from the gold dialog scheme.",
    ("DARK", "#000000", "#444444"):
        "main-window button pressed, dark. Same inverse scheme mirrored.",
    ("IMAGE", "#000000", "#444444"):
        "main-window button pressed, image mode (inherits dark).",
    ("LIGHT", "#aaaaaa", "#ffffff"):
        "disabled control text. WCAG 1.4.3 exempts disabled controls.",
    ("LIGHT", "#aaaaaa", "#e0e0e0"):
        "disabled control text on a tinted surface. Same exemption.",
    ("DARK", "#555555", "#333333"):
        "disabled control text, dark. Same exemption.",
    ("DARK", "#555555", "#2a2a2a"):
        "disabled control text on the dark card. Same exemption.",
    ("IMAGE", "#555555", "#333333"):
        "disabled control text, image mode. Same exemption.",
    ("IMAGE", "#555555", "#2a2a2a"):
        "disabled control text on the card, image mode. Same exemption.",
    ("LIGHT", "#666666", "#e0e0e0"):
        "unselected tab label. Secondary text on an inactive tab; the "
        "selected tab carries the accent and the contrast.",
    ("DARK", "#888888", "#2a2a2a"):
        "unselected tab label, dark. Same reason.",
    ("IMAGE", "#888888", "#2a2a2a"):
        "unselected tab label, image mode. Same reason.",
}

_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_LOOKUP = re.compile(r"\{\s*(\w+)\[['\"]([\w\-]+)['\"]\]\s*\}")


def _rules(src: str) -> list[tuple[str, str]]:
    """(selector, body) for each QSS rule in one source file.

    A scan, not a regex. ``([^{}]+?)\\{\\{(.*?)\\}\\}`` backtracks
    quadratically on files this size. Tightening the body to ``[^{}]*`` is
    fast and wrong: QSS bodies are full of placeholders like
    ``{theme['tab_bg']}``, so a brace-free class stops at the first one and
    finds a fraction of the rules -- which reads exactly like finding no
    defects. test_the_audit_finds_something_to_audit catches that.
    """
    out, cursor = [], 0
    while True:
        start = src.find("{{", cursor)
        if start == -1:
            break
        end = src.find("}}", start + 2)
        if end == -1:
            break
        lead = src[cursor:start].strip()
        out.append((lead.splitlines()[-1].strip() if lead else "",
                    src[start + 2:end]))
        cursor = end + 2
    return out


def _normalise(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h.lower()


def _pins(src: str) -> dict[str, str]:
    return {m.group(1): _PIN_CONST[m.group(2)] for m in _PIN.finditer(src)}


def _resolve(token: str, palette: dict[str, str],
             pins: dict[str, str]) -> str | None:
    token = token.strip().rstrip(";").strip()
    if _HEX.fullmatch(token):
        return _normalise(token)
    m = _LOOKUP.fullmatch(token)
    if m:
        var, key = m.groups()
        source = PALETTES[pins[var]] if var in pins else palette
        v = source.get(key)
        return _normalise(v) if isinstance(v, str) and _HEX.fullmatch(v) else None
    m = re.fullmatch(r"\{\s*([A-Z_][A-Z0-9_]*)\s*\}", token)
    if m:
        v = getattr(C, m.group(1), None)
        return _normalise(v) if isinstance(v, str) and _HEX.fullmatch(v) else None
    return None


def _palette_can_render(body: str, palette: dict[str, str],
                        pins: dict[str, str], palette_name: str) -> bool:
    """Could this palette be the one this block renders with?

    A block pinned by an `im = IMAGE_MODE_COLORS`-style binding renders
    with that palette and no other. And a palette missing a key the block
    asks for cannot be the one rendering it. Without this, every block is
    measured against every palette and the audit reports pairings the app
    never renders while missing the ones it does.
    """
    lookups = _LOOKUP.findall(body)
    if not lookups:
        return True
    pinned = {pins[var] for var, _ in lookups if var in pins}
    if pinned and palette_name not in pinned:
        return False
    return all(key in palette for var, key in lookups if var not in pins)


# A migration tool committed into the repository so it can be pulled into a
# codespace. Its source quotes the very patterns these tests hunt for --
# the old `color: {self._get_accent()}` lines it exists to replace -- so
# scanning it reports the tool's replacement strings as live call sites.
#
# Same rule as the guard marker at the top of this file, pointed the other
# way: any tool that talks about a value must be excluded from the scan for
# that value. This one was found the hard way, because the delivery script
# is copied in UNTRACKED during rehearsal and COMMITTED in real use, so
# git ls-files saw it only in the real run.
TOOL_MARKER = "RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP"


def _tracked_python_files() -> list[Path]:
    """From git, not a list written here, minus any migration tool.

    A hardcoded file list goes stale the moment a module is added, in the
    direction that reports clean.
    """
    r = subprocess.run(["git", "ls-files", "-z", "*.py"],
                       cwd=PROJECT_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        found = sorted(p for p in PROJECT_ROOT.rglob("*.py")
                       if "__pycache__" not in p.parts)
    else:
        found = sorted((PROJECT_ROOT / n) for n in r.stdout.split("\0")
                       if n and (PROJECT_ROOT / n).exists())
    keep = []
    for p in found:
        try:
            if TOOL_MARKER in p.read_text(encoding="utf-8-sig", errors="ignore"):
                continue
        except OSError:
            pass
        keep.append(p)
    return keep


@functools.lru_cache(maxsize=1)
def _sources() -> tuple[tuple[str, str], ...]:
    """Every tracked source, read once, BOM stripped.

    utf-8-sig rather than utf-8: utils/config.py carries a BOM, and a
    U+FEFF left at the head of the string makes ast.parse reject the whole
    file. Reading it correctly here is better than teaching each caller to
    cope, which is how one caller ends up not coping.
    """
    return tuple((str(p.relative_to(PROJECT_ROOT)),
                  p.read_text(encoding="utf-8-sig", errors="ignore"))
                 for p in _tracked_python_files())


@functools.lru_cache(maxsize=8)
def audit_palette(palette_name: str) -> tuple[tuple[str, str, float, str], ...]:
    palette = PALETTES[palette_name]
    findings = []
    for rel, src in _sources():
        pins = _pins(src)
        for selector, body in _rules(src):
            if not _palette_can_render(body, palette, pins, palette_name):
                continue
            fg = bg = None
            for decl in body.split(";"):
                if ":" not in decl:
                    continue
                prop, _, value = decl.partition(":")
                prop = prop.strip()
                if prop == "color":
                    fg = _resolve(value, palette, pins)
                elif prop in ("background-color", "background"):
                    bg = _resolve(value, palette, pins)
            if fg and bg:
                ratio = contrast_ratio(fg, bg)
                if ratio < TEXT_FLOOR:
                    findings.append((fg, bg, round(ratio, 4),
                                     f"{rel} :: {selector}"))
    return tuple(findings)


def test_the_audit_finds_something_to_audit() -> None:
    """Guard the guard. If the walker stops parsing, every contrast test
    below passes vacuously."""
    total = sum(len(_rules(src)) for _rel, src in _sources())
    assert total > 100, (
        f"the QSS walker matched only {total} rules across the repository, "
        f"which means it stopped parsing the stylesheets rather than that "
        f"the stylesheets got smaller")


def test_every_palette_gets_audited() -> None:
    """Guard the palette binding. If it ever excluded everything, every
    palette below would pass by measuring nothing."""
    for name in PALETTES:
        checked = sum(
            1 for _rel, src in _sources()
            for _sel, body in _rules(src)
            if _LOOKUP.search(body)
            and _palette_can_render(body, PALETTES[name], _pins(src), name))
        assert checked > 10, (
            f"palette {name} matched only {checked} blocks -- the binding "
            f"rule has stopped letting anything through")


@pytest.mark.parametrize("palette_name", sorted(PALETTES))
def test_no_unaccepted_contrast_failures(palette_name: str) -> None:
    bad = [f for f in audit_palette(palette_name)
           if (palette_name, f[0], f[1]) not in ACCEPTED]
    assert not bad, "\n".join(
        f"  {palette_name}  {r:>7}:1  {fg} on {bg}  <- {where}"
        for fg, bg, r, where in bad)


def test_every_exemption_still_applies() -> None:
    """The half that matters. An exemption for a pairing that no longer
    exists will silently cover a future defect."""
    seen = set()
    for name in PALETTES:
        for fg, bg, _r, _w in audit_palette(name):
            seen.add((name, fg, bg))
    dead = sorted(k for k in ACCEPTED if k not in seen)
    assert not dead, (
        "these exemptions no longer match anything the app renders and "
        f"should be deleted: {dead}")


# ══════════════════════════════════════════════════════════════════════════
# THE TWO GOLD ROLES
# ══════════════════════════════════════════════════════════════════════════
#
# Light mode uses exactly two golds because one cannot do both jobs. A gold
# light enough to carry white text at 4.5:1 is too light to BE text on
# anything but pure white -- the luminance bands do not overlap.

LIGHT_SURFACES = ["#ffffff", "#fafafa", "#f5f5f5", "#f0f0f0", "#eeeeee"]


def test_fill_gold_carries_white_text() -> None:
    assert contrast_ratio("#ffffff", C.BRAND_DARK_GOLD) >= TEXT_FLOOR


def test_fill_gold_still_carries_black_text() -> None:
    """The register rules black on gold, and the value move must not cost
    that. Black is 4.6226 at the new value -- the margin is thin, which is
    exactly when a check earns its place."""
    assert contrast_ratio("#000000", C.BRAND_DARK_GOLD) >= TEXT_FLOOR


def test_text_gold_clears_every_light_surface() -> None:
    failures = [(s, round(contrast_ratio(C.BRAND_DARK_GOLD_DEEP, s), 4))
                for s in LIGHT_SURFACES
                if contrast_ratio(C.BRAND_DARK_GOLD_DEEP, s) < TEXT_FLOOR]
    assert not failures, (
        f"the text gold no longer clears every light surface: {failures}")


@pytest.mark.parametrize("key", [
    "text_accent", "button_hover_text", "list_hover_text",
    "tab_hover_text", "tab_selected_text",
])
def test_gold_text_keys_use_the_text_gold(key: str) -> None:
    assert C.LIGHT_THEME_COLORS[key] == C.BRAND_DARK_GOLD_DEEP


@pytest.mark.parametrize("key", [
    "selected_bg", "button_pressed_bg", "checkbox_checked_bg",
    "list_selected_bg",
])
def test_gold_fill_keys_use_the_fill_gold(key: str) -> None:
    """Fills must not take the text gold: black on it is 3.78, under the
    floor, and these fills carry text."""
    assert C.LIGHT_THEME_COLORS[key] == C.BRAND_DARK_GOLD


def test_tab_hover_ground_is_light_enough_for_gold_text() -> None:
    """Hover reads as hover because the ground lightens toward the selected
    tab's white, and the gold text stays legible on it."""
    ground = C.LIGHT_THEME_COLORS["tab_hover_bg"]
    rest = C.LIGHT_THEME_COLORS["tab_bg"]
    assert relative_luminance(ground) > relative_luminance(rest)
    assert contrast_ratio(C.LIGHT_THEME_COLORS["tab_hover_text"],
                          ground) >= TEXT_FLOOR


# ══════════════════════════════════════════════════════════════════════════
# STATUS
# ══════════════════════════════════════════════════════════════════════════

def test_one_status_family_only() -> None:
    """Both Bootstrap and Material sets lived here at once. The ruling of
    2026-08-13 chose Bootstrap; Material's values must be gone."""
    src = _config_source()
    stale = [v for v in ("#4caf50", "#f44336") if v in src.lower()]
    assert not stale, f"retired Material status colours still present: {stale}"


@pytest.mark.parametrize("bg,fg", [
    ("STATUS_SUCCESS_BG", "STATUS_SUCCESS_FG"),
    ("STATUS_ERROR_BG", "STATUS_ERROR_FG"),
])
def test_status_badge_text_clears_its_fill(bg: str, fg: str) -> None:
    """These are a real pair -- background and colour on the same label.
    White fails on both Bootstrap fills (3.13 and 4.53 borderline); black
    clears both."""
    assert contrast_ratio(getattr(C, fg), getattr(C, bg)) >= TEXT_FLOOR


def test_error_text_is_theme_aware() -> None:
    """The error label used one static colour on both grounds, and no
    registered red clears #f5f5f5 and #1a1a1a alike. It takes a palette
    key now, so each theme gets a value that suits its ground."""
    for name, palette in PALETTES.items():
        assert "status_error_text" in palette, (
            f"{name} has no status_error_text key")
    dark = C.DARK_THEME_COLORS
    assert contrast_ratio(dark["status_error_text"],
                          dark["panel_bg"]) >= TEXT_FLOOR


RETIRED = {
    "#b19145": "the app-local dark gold",
    "#c4a458": "the orphaned lighter light-mode hover",
    "#8a7236": "the hand-written light-mode pressed",
    "#dcc9a3": "the hand-written dark hover",
    "#b7a480": "the hand-written dark pressed",
    "#d0d0d0": "the tab hover ground no gold cleared",
    "#4caf50": "Material success",
    "#f44336": "Material error",
}


def _assigned_string_values() -> list[tuple[int, str]]:
    """Every string this module actually assigns, as (line, value).

    Deliberately not a text search. utils/config.py DOCUMENTS the values it
    retired -- "it replaced the app-local #b19145" -- and a text search
    cannot tell that sentence from a live constant. Use and mention again:
    the docstring explaining a retirement is the one place the retired value
    belongs. The AST only sees values, never prose.
    """
    out = []
    for node in ast.walk(ast.parse(_config_source())):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parent_is_doc = False
            out.append((node.lineno, node.value))
    # drop docstrings: a bare string expression statement is documentation
    docs = {n.value.lineno for n in ast.walk(ast.parse(_config_source()))
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)}
    return [(ln, v) for ln, v in out if ln not in docs]


def test_retired_values_are_gone() -> None:
    """Everything this alignment replaced, in one place, so nothing walks
    back in unnoticed."""
    back = [(ln, v, RETIRED[v.lower()])
            for ln, v in _assigned_string_values()
            if v.lower() in RETIRED]
    assert not back, "\n".join(
        f"  utils/config.py:{ln}: {what} ({v}) is back" for ln, v, what in back)


# ══════════════════════════════════════════════════════════════════════════
# THE PAIRING THE WALKER CANNOT SEE
# ══════════════════════════════════════════════════════════════════════════
#
# The error label sets a colour and no background of its own -- it inherits
# the panel it sits on. The stylesheet walker only records a pair when both
# halves appear in one rule, so this pairing is invisible to it and has to
# be asserted by hand.

LIGHT_ERROR_SHORTFALL = 4.1528   # measured, #dc3545 on #f5f5f5


def test_dark_error_text_clears_its_panel() -> None:
    d = C.DARK_THEME_COLORS
    assert contrast_ratio(d["status_error_text"], d["panel_bg"]) >= TEXT_FLOOR


def test_light_error_text_is_the_ruled_value_and_no_worse() -> None:
    """The register rules #dc3545 for light mode and explicitly declines to
    derive a darker variant. Its #e56b77 error-text is a dark-theme value
    and measures 2.8745 here -- worse than what we have.

    So this pairing is short at 4.1528, against 3.3777 for the retired
    Material red. The test holds the improvement and fails if it regresses.
    """
    light = C.LIGHT_THEME_COLORS
    ratio = contrast_ratio(light["status_error_text"], light["panel_bg"])
    assert ratio >= LIGHT_ERROR_SHORTFALL - 0.0001, (
        f"light error text regressed to {ratio:.4f}, below the "
        f"{LIGHT_ERROR_SHORTFALL} this pass established")
    assert ratio < TEXT_FLOOR, (
        f"light error text now measures {ratio:.4f} and CLEARS the floor. "
        f"Brand Infrastructure has presumably ruled a light-mode error "
        f"text -- delete this test and its exemption rather than leaving a "
        f"standing note about a problem that no longer exists.")


# ══════════════════════════════════════════════════════════════════════════
# GOLD DELIVERED THROUGH A HELPER
# ══════════════════════════════════════════════════════════════════════════
#
# This is the blind spot that nearly shipped. Two dialogs hand gold to
# labels through a method -- `color: {self._get_accent()}` -- and a method
# call inside an f-string is neither a palette key nor a bare constant, so
# the stylesheet walker resolves nothing and reports nothing. Reporting
# nothing reads exactly like reporting no defects.
#
# about_dialog had NINE such uses, every one of them text on #f5f5f5, where
# the fill gold measures 4.1670. The walker was silent on all nine.
#
# The structural rule these tests hold: a helper is named for the ROLE it
# serves, and a helper may not cross roles. `_get_accent` is a fill;
# `_get_accent_text` is text. They return different golds because a light
# ground needs different golds for the two jobs.

GUARD_TEST_PATH_NAME = "tests/test_brand_contrast.py"

ACCENT_HELPERS = {
    "_get_accent": "FILL",
    "_get_accent_text": "TEXT",
}

_DECL = re.compile(
    r"(?<![\w-])(color|background-color|background|border-color|border)"
    r"\s*:\s*([^;\"']*)")


def _helper_uses() -> list[tuple[str, int, str, str]]:
    """(file, line, helper, role) for every accent-helper call in a
    stylesheet declaration."""
    found = []
    for rel, src in _sources():
        if rel.startswith("tests/") or rel == GUARD_TEST_PATH_NAME:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            for helper in ACCENT_HELPERS:
                call = f"self.{helper}()"
                if call not in line:
                    continue
                # the longer name contains the shorter one
                if (helper == "_get_accent"
                        and "self._get_accent_text()" in line):
                    continue
                m = _DECL.search(line)
                if not m:
                    continue
                prop = m.group(1)
                role = ("TEXT" if prop == "color"
                        else "FILL" if prop.startswith("background")
                        else "BORDER")
                found.append((rel, i, helper, role))
    return found


def test_the_helper_scan_finds_helpers() -> None:
    """Guard the guard. If the scan stops matching, every assertion below
    passes by looking at nothing."""
    uses = _helper_uses()
    assert len(uses) >= 10, (
        f"the accent-helper scan found only {len(uses)} call sites. It has "
        f"stopped matching rather than the app having stopped using them.")


def test_no_accent_helper_crosses_its_role() -> None:
    """A fill helper must never colour text, and vice versa."""
    wrong = [(f, ln, h, role) for f, ln, h, role in _helper_uses()
             if ACCENT_HELPERS[h] == "TEXT" and role != "TEXT"
             or ACCENT_HELPERS[h] == "FILL" and role == "TEXT"]
    assert not wrong, "\n".join(
        f"  {f}:{ln}  {h}() is a {ACCENT_HELPERS[h]} helper used as {role}"
        for f, ln, h, role in wrong)


def test_text_helpers_return_the_text_gold() -> None:
    """Read the helper bodies. A helper that hands gold to text must hand
    over the deep derivative on a light ground, and the walker cannot check
    this because it never sees the value."""
    offenders = []
    for rel, src in _sources():
        if rel.startswith("tests/"):
            continue
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in ACCENT_HELPERS:
                continue
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            want = ("BRAND_DARK_GOLD_DEEP" if ACCENT_HELPERS[node.name] == "TEXT"
                    else "BRAND_DARK_GOLD")
            if want not in names:
                offenders.append(f"  {rel}:{node.lineno} {node.name}() is a "
                                 f"{ACCENT_HELPERS[node.name]} helper and does "
                                 f"not return {want}")
    assert not offenders, "\n".join(offenders)


# ══════════════════════════════════════════════════════════════════════════
# THE RULE: TWO GOLDS PER MODE
# ══════════════════════════════════════════════════════════════════════════
#
# The brand registers two golds -- BRAND_GOLD for dark grounds,
# BRAND_DARK_GOLD for light -- and derives the rest when needed. "When
# needed" is the load-bearing part: a mode gets ONE derivative, and every
# other gold role reuses the accent or that derivative.
#
# Light spends its derivative on BRAND_DARK_GOLD_DEEP, because gold as text
# on any light surface below white needs a darker value than gold as a fill
# under black text -- those two luminance bands do not overlap, so the
# second value is structural rather than decorative.
#
# Dark spends its derivative on hover, which must lift away from the dark
# ground.
#
# In both modes the pressed state returns to the accent. That is what keeps
# the count at two: before this pass, light carried four golds and dark
# three, each extra one a hand-written value serving a single key.

BASE_GOLD = {"LIGHT": "BRAND_DARK_GOLD", "DARK": "BRAND_GOLD",
             "IMAGE": "BRAND_GOLD"}


def _golds_in(palette: dict[str, str]) -> dict[str, list[str]]:
    """Distinct gold values a palette holds, and the keys holding each."""
    known = {getattr(C, n).lower() for n in
             ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",
              "BRAND_GOLD_HOVER", "BRAND_GOLD_PRESSED",
              "BRAND_DARK_GOLD_HOVER", "BRAND_DARK_GOLD_PRESSED")}
    out: dict[str, list[str]] = {}
    for key, value in palette.items():
        if isinstance(value, str) and value.lower() in known:
            out.setdefault(value.lower(), []).append(key)
    return out


@pytest.mark.parametrize("palette_name", sorted(PALETTES))
def test_two_golds_per_mode(palette_name: str) -> None:
    """The rule, made machine-checkable.

    A third gold is how this repository ended up with #c4a458 -- a tint of
    a value that had already been retired, orphaned and serving one key,
    with nothing anywhere to flag it. Counting is what catches that; no
    contrast test would, because an orphaned gold can be perfectly legible.
    """
    found = _golds_in(PALETTES[palette_name])
    assert len(found) <= 2, "\n".join(
        [f"{palette_name} renders {len(found)} distinct golds, and the brand "
         f"allows two -- the registered one and one derived from it:"]
        + [f"  {v}  ({len(ks)} keys)  {', '.join(sorted(ks)[:5])}"
           for v, ks in sorted(found.items())])


@pytest.mark.parametrize("palette_name", sorted(PALETTES))
def test_the_registered_gold_is_one_of_the_two(palette_name: str) -> None:
    """Guard the guard above. Two golds neither of which is registered
    would satisfy a bare count while being entirely off-brand."""
    found = _golds_in(PALETTES[palette_name])
    base = getattr(C, BASE_GOLD[palette_name]).lower()
    assert base in found, (
        f"{palette_name} holds golds {sorted(found)} and none of them is "
        f"{BASE_GOLD[palette_name]} ({base}), the registered value for this "
        f"mode")


def test_every_gold_is_the_accent_or_derived_from_it() -> None:
    """No palette may hold a gold that is neither registered nor one of
    this module's derivatives -- which is what a hand-written variant is."""
    allowed = {getattr(C, n).lower() for n in
               ("BRAND_GOLD", "BRAND_DARK_GOLD", "BRAND_DARK_GOLD_DEEP",
                "BRAND_GOLD_HOVER")}
    stray = []
    for name, palette in PALETTES.items():
        for key, value in palette.items():
            if not isinstance(value, str) or not value.startswith("#"):
                continue
            v = value.lower()
            # a gold-ish value: warm, and close to one of ours in hue
            if v in allowed:
                continue
            r, g, b = C._to_rgb(v) if len(v) == 7 else (0, 0, 0)
            if r > g > b and r - b > 40 and 90 < r < 240:
                stray.append(f"  {name}.{key} = {value}")
    assert not stray, (
        "these look like golds and are neither registered nor derived "
        "here:\n" + "\n".join(stray))


def test_the_tool_exclusion_does_not_swallow_the_repository() -> None:
    """Guard the exclusion.

    Skipping files that carry TOOL_MARKER is right, and a marker that
    matched everything would empty the scan while every test above passed
    by looking at nothing.
    """
    kept = _tracked_python_files()
    assert len(kept) > 20, (
        f"only {len(kept)} Python files survived the tool-marker "
        f"exclusion -- it is matching far more than a migration script")
