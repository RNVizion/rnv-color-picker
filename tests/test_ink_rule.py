"""One rule for which ink goes on a ground. RNV-INK-RULE-GUARD

Ruled by Chris on 2026-09-02 after seeing the three rules rendered side by
side: unify on WCAG relative luminance.

Four places in the fleet answered this question and gave three different
answers, none of them a contrast measurement. This guard exists because that
is a failure that reappears -- the next person who needs an ink for a swatch
will reach for (r+g+b)/3 unless something stops them.
"""
from __future__ import annotations

import re
from pathlib import Path

from utils import config

ROOT = Path(__file__).resolve().parent.parent
RETIRED = ('CONTRAST_ON_DARK', 'CONTRAST_ON_LIGHT', 'SWATCH_BORDER_ON_DARK', 'SWATCH_BORDER_ON_LIGHT', 'PREVIEW_BORDER', 'PREVIEW_BORDER_THIN')
SKIP = {".git", "build", "dist", ".venv", "__pycache__"}


def _code_only(text: str) -> str:
    """The file with every comment and string literal removed.

    Written after the first version of this guard failed on its own
    explanation. A guard that sweeps for the thing it forbids must be able to
    tell a use from a mention, and every previous attempt at that in this
    programme did it by excluding files, which stops working the moment a
    third file has a legitimate reason to say the word. Tokenising is the
    version that does not need a list."""
    import io
    import tokenize
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text          # unparseable: fall back to the whole text
    return " ".join(out)


def _sources():
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in SKIP for p in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "RNV-INK-RULE-GUARD" in text or "RNV-NAMING-TOOL-DO-NOT-SWEEP" in text:
            continue
        yield path, text


def test_the_rule_is_a_real_contrast_measurement():
    """Black on white and white on black, the two ends. If the rule were
    inverted or the luminance formula wrong, these are what break first."""
    assert config.contrast_ink("#ffffff") == config.TRUE_BLACK
    assert config.contrast_ink("#000000") == config.WHITE
    assert round(config.contrast_ratio("#ffffff", "#000000"), 2) == 21.0
    assert round(config.contrast_ratio("#777777", "#777777"), 2) == 1.0


def test_the_rule_gets_saturated_colour_right():
    """The case the mean got wrong. Pure green is a LIGHT ground -- it is 71%
    of the luminance of white -- and the mean called it dark because it only
    looked at how many channels were lit."""
    assert config.contrast_ink((0, 255, 0)) == config.TRUE_BLACK
    assert config.contrast_ratio((0, 255, 0), config.TRUE_BLACK) > 15
    # and the mean, for the record, would have chosen the other one
    assert sum((0, 255, 0)) / 3 < 128


def test_it_takes_a_hex_string_or_an_rgb_triple():
    """Callers hold both shapes, and a silent TypeError inside an f-string
    renders as an empty colour rather than an exception."""
    assert config.contrast_ink("#00ff00") == config.contrast_ink((0, 255, 0))
    assert config.contrast_ink("#0f0") == config.contrast_ink("#00ff00")


def test_the_edge_rule_shares_the_ink_rule():
    """swatch_edge answers the same question with a different pair. If it
    ever grows its own threshold, this is what catches it."""
    assert config.swatch_edge("#ffffff") == config.APP_BORDER
    assert config.swatch_edge("#000000") == config.GREY_CC
    for ground in ("#ffffff", "#000000", "#8c7337", "#00ff00", "#777777"):
        edge = config.swatch_edge(ground)
        other = config.GREY_CC if edge == config.APP_BORDER else config.APP_BORDER
        assert config.contrast_ratio(ground, edge) >= \
            config.contrast_ratio(ground, other)


def test_the_brand_golds_are_ruled_not_measured():
    """The close button keeps black on bright gold and white on dark gold.

    Dark gold measures 4.54 white against 4.62 black -- close enough that the
    arithmetic would flip it, which is exactly why the two call sites in
    utils/cache.py name the colour outright instead of asking the rule. This
    test states the margin so that a later 'cleanup' that routes them through
    contrast_ink() has to argue with a number."""
    white = config.contrast_ratio(config.BRAND_DARK_GOLD, config.WHITE)
    black = config.contrast_ratio(config.BRAND_DARK_GOLD, config.TRUE_BLACK)
    assert abs(white - black) < 0.15, (
        "the golds moved; re-take the ruling rather than the measurement")
    src = (ROOT / "utils" / "cache.py").read_text(encoding="utf-8-sig")
    assert "fg      = TRUE_BLACK" in src and "fg      = WHITE" in src, (
        "the gold button inks are no longer written as a decision")


def test_the_accessibility_helper_does_not_hold_a_second_copy():
    """It held its own luminance < 0.179 while three other places each held
    something else. One rule, one implementation."""
    src = _code_only(
        (ROOT / "core" / "accessibility.py").read_text(encoding="utf-8-sig"))
    assert "0.179" not in src, "a second crossover threshold is back"
    assert config.contrast_ink("#ffffff") == config.TRUE_BLACK
    from core.accessibility import ColorAccessibility
    assert ColorAccessibility.get_optimal_text_color((255, 255, 255)) == (0, 0, 0)
    assert ColorAccessibility.get_optimal_text_color((0, 0, 0)) == (255, 255, 255)
    assert ColorAccessibility.get_optimal_text_color((0, 255, 0)) == (0, 0, 0)


def test_no_call_site_measures_brightness_by_hand():
    """The rule is only one rule while nothing else computes its own.

    Matches the two shapes that were actually here -- a mean of the three
    channels, and the ITU-R 601 weights -- rather than any arithmetic, so it
    stays readable and does not fire on unrelated maths."""
    mean = re.compile(r"sum \( colou?r \) / 3|\( r \+ g \+ b \) / 3")
    luma = re.compile(r"\* 299\b|\* 587\b|\* 114\b")
    strays = []
    for path, text in _sources():
        code = _code_only(text)
        if mean.search(code) or luma.search(code):
            strays.append(str(path.relative_to(ROOT)))
    assert not strays, f"hand-rolled brightness rules are back in: {strays}"


def test_the_fallback_branches_no_longer_hold_their_own_copy():
    """Four files inlined the rule as a `if CACHE_AVAILABLE ... else` fallback,
    each an exact copy of ColorCache's own. Seven implementations of one
    question in one application, on three different rules, is what the sweep
    above exists to stop coming back."""
    for rel in ("RNV_Color_Picker.py", "core/workers.py",
                "ui/settings_panel.py", "ui/color_swatch_widget.py",
                "utils/cache.py"):
        code = _code_only((ROOT / rel).read_text(encoding="utf-8-sig"))
        assert "brightness > 128" not in code, f"{rel} still rolls its own"
    from utils.cache import ColorCache
    assert ColorCache.get_text_color_for_background((128, 128, 128)) == (0, 0, 0)
    assert ColorCache.get_text_color_for_background((0, 0, 0)) == (255, 255, 255)


def test_the_retired_names_are_gone():
    strays = []
    for path, text in _sources():
        for old in RETIRED:
            if re.search(r"\b%s\b" % re.escape(old), text):
                strays.append(f"{path.relative_to(ROOT)}: {old}")
    assert not strays, "retired names are still in use:\n  " + "\n  ".join(strays)


def test_every_source_file_is_utf8():
    """core/palette_formats.py carried four cp1252 em-dashes. CPython let it
    run because they sat in comments; an audit script read it with plain
    UTF-8, swallowed the decode error, skipped the file, and reported two
    live constants as dead. A sweep that cannot read a file is worse than one
    that fails."""
    bad = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in SKIP for p in path.parts):
            continue
        try:
            path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            bad.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not bad, "not valid UTF-8:\n  " + "\n  ".join(bad)


def test_no_three_digit_hex_in_the_palette():
    """Two of the retired constants were "#333" and "#ccc". The census reads
    six-digit hexes, so a three-digit one is a value the chart cannot see."""
    src = (ROOT / "utils" / "config.py").read_text(encoding="utf-8-sig")
    hits = re.findall(r"""['"]#[0-9a-fA-F]{3}['"]""", src)
    assert not hits, f"three-digit hexes are back: {hits}"
