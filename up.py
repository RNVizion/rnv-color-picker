"""The picker, in American spelling: color, gray, behavior, center

    python up.py             # apply, then run the guards and CI's own commands
    python up.py --check     # rehearse every edit in memory, write nothing
    python up.py --verify    # run the guards and CI's commands, change nothing

For rnv-color-picker, derived against a fresh clone at the live head (fbf26d2).

RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP. This script is a delivery tool, not
application source, and it names what it retires. That marker is what tells
this fleet's scanners to skip it.

RULED 2026-10-18: #59 A, "colour" becomes "color" everywhere: code, comments,
file names, map keys, markers, test names, the root suite and documents; #60 A,
and the other British spellings with it, "grey" (GREY_44 is GRAY_44),
"behaviour" and "centre"; #62 A, and the rest the census found: -ise is -ize,
licence, programme, labelled, dialled, honour, judgement, neighbour, maths.
"cancelled" stays: it is American too, and it names signals. In one round, one
file per app. A dictionary census of the result finds no British-only word.

NO GUARD IN THE APP. The rule lives in the brand, so that everything made from
scratch starts on it: a note goes to the brand chat for rnv-brand, and the
practice doc carries it (Chris, 18 October).

THE RULES, inside words and names, keeping case (COLOUR_FILE is COLOR_FILE):
  colour     -> color
  grey       -> gray
  behaviour  -> behavior
  centre(s?)(?![A-Za-z]) -> center\1
  centr(ed|ing) -> center\1
  centre(?=line|piece|point) -> center
  (normal|recogn|optim|parametr|parameter|serial|token|maxim|minim|neutral|general|organ|real|visual|util|summar|custom|initial|synchron|capital|categor|character|priorit|standard|final|local|sanit|random|stabil|memor|author|apolog|critic|special|material|raster|harmon|emphas|quant|linear|central|rational)is(e|ed|es|ing|er|ers|ation|ations|able|ably|ability) -> \1iz\2
  licenc(e|es|ed|ing) -> licens\1
  (?<![A-Za-z])programme(s?)(?![A-Za-z]) -> program\1
  (?<![A-Za-z])maths(?![A-Za-z]) -> math
  (label|travel|model|level|signal|dial|equal|fuel|channel|tunnel|total|spiral|pedal|marvel|rival|quarrel|counsel|libel|shovel|swivel|unravel|bevel|enamel|jewel|panel|pencil|stencil|duel|barrel|grovel|revel|towel|funnel)l(ed|ing|er|ers) -> \1\2
  (hon|neighb|fav|flav|hum|lab|rum|vap|harb|arm|endeav|sav|od|splend|val|clam|parl|tum|savi)our -> \1or
  dgement    -> dgment
  (off|def|pret)ence -> \1ense
  (met|lit|fib|theat|calib|spect|lust)re(s?)(?![A-Za-z]) -> \1er\2
  practis(e|ed|es|ing) -> practic\1
  sceptic    -> skeptic
  aluminium  -> aluminum
  artefact   -> artifact
  and a note beside a tree diagram keeps its column when a name before it gets shorter.

LEFT AS THEY ARE:
  CSS's own color keywords. CSS defines grey, lightgrey and the rest beside
  gray; a string that holds nothing but CSS keywords, or a regex for them, is
  CSS, and what the user can type (a search for "grey") keeps working.
  LICENSE files, which are legal text.
  Every one this round leaves, by file and count. A plain scan of the whole
  checkout, with no exception applied, must find exactly these and no more:
  tests/test_named_and_used.py (7): CSS_NAMES: CSS's own color keywords, one
      of which a color written by name must be.
  tests/test_settings_panel.py (1): a regex for CSS's gray in either spelling,
      which code must not paint with.

WHAT LANDS.
  45 files, the same text in American spelling, 3 of them renamed:
    tests/colour_values.py -> tests/color_values.py
    tests/test_colour_values.py -> tests/test_color_values.py
    tests/test_colours_in_sync.py -> tests/test_colors_in_sync.py
NO VALUE MOVES. Every value utils/config.py defines is what it was, under its new name.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import tokenize
import types
from pathlib import Path

REPO = 'rnv-color-picker'
SENTINEL = 'RNV-COLOR-SYNC'   # written only by this round: the marker was spelled the other way
SENTINEL_FILE = 'tools/sync_colors.py'
GUARD = 'tests/test_colors_in_sync.py'
GUARD_FILES = ['tests/test_color_values.py', 'tests/test_colors_in_sync.py']
GUARD_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *GUARD_FILES]
DESCRIPTION = "The picker, in American spelling"

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
CI_MIRRORS = {'.github/workflows/tests.yml': '6af546867cb3b83fe0e662987fa297d7a0c8ff07bd5a00dc2750f2647ab94a7d'}

SHADOWS = ['conftest.py', 'run_tests.py', 'sync_colors.py', 'test_color_values.py', 'test_colors_in_sync.py', 'test_rnv_color_picker.py']

LEFT_ALONE = ["every value the application draws: the same, under its American name.",
              "CSS's own color keywords, in data: a table of CSS names, a regex for them, a search the user types.",
              "LICENSE files, which are legal text.",
              "rnv-brand, which the brand chat keeps: a note goes to it."]

# ======================================================================== the transform

import ast
import io
import re
import tokenize

_L = "(?<![A-Za-z])"   # no letter before
_R = "(?![A-Za-z])"    # no letter after

#: (British pattern, American replacement), each tried case-insensitively; the
#: replacement takes the case of the letters it replaces. Patterns match inside
#: names, so COLOUR_FILE and _normalise are reached.
BASE_RULES: list[tuple[str, str]] = [
    ("colour", "color"),                       # colours, coloured, recolour, COLOUR_FILE
    ("grey", "gray"),                          # greys, greyscale, GREY_44
    ("behaviour", "behavior"),                 # behaviours, behavioural
    ("centre(s?)" + _R, r"center\1"),          # centre, centres -> center, centers
    ("centr(ed|ing)", r"center\1"),            # centred, centring -> centered, centering
    ("centre(?=line|piece|point)", "center"),  # centreline
]

#: #62 A: the further British spellings, the -ise family by its stems, so that
#: realistic, organism, criticism and optimism are not touched.
_ISE_STEMS = ("normal recogn optim parametr parameter serial token maxim minim neutral general organ real "
              "visual util summar custom initial synchron capital categor character priorit standard final "
              "local sanit random stabil memor author apolog critic special material raster harmon emphas "
              "quant linear central rational").split()
#: A final l doubled before -ed, -ing, -er: American keeps it single. Not
#: "cancelled", which is American too (#62 A).
_LL_STEMS = ("label travel model level signal dial equal fuel channel tunnel total spiral pedal marvel "
             "rival quarrel counsel libel shovel swivel unravel bevel enamel jewel panel pencil stencil "
             "duel barrel grovel revel towel funnel").split()
EXTRA_RULES: list[tuple[str, str]] = [
    ("(" + "|".join(_ISE_STEMS) + ")is(e|ed|es|ing|er|ers|ation|ations|able|ably|ability)",
     r"\1iz\2"),
    ("licenc(e|es|ed|ing)", r"licens\1"),
    (_L + "programme(s?)" + _R, r"program\1"),
    (_L + "maths" + _R, "math"),
    ("(" + "|".join(_LL_STEMS) + ")l(ed|ing|er|ers)", r"\1\2"),
    ("(hon|neighb|fav|flav|hum|lab|rum|vap|harb|arm|endeav|sav|od|splend|val|clam|parl|tum|savi)our",
     r"\1or"),
    ("dgement", "dgment"),                     # judgement, acknowledgement
    ("(off|def|pret)ence", r"\1ense"),
    ("(met|lit|fib|theat|calib|spect|lust)re(s?)" + _R, r"\1er\2"),
    ("practis(e|ed|es|ing)", r"practic\1"),
    ("sceptic", "skeptic"),
    ("aluminium", "aluminum"),
    ("artefact", "artifact"),
]

#: CSS color keywords spelled with grey; a string of only these is CSS, kept.
CSS_GREYS = frozenset({"grey", "lightgrey", "darkgrey", "dimgrey", "slategrey",
                       "darkslategrey", "lightslategrey"})
#: Every CSS color keyword (CSS Color Module Level 4), and words a regex or a
#: CSS declaration about them carries.
CSS_WORDS = frozenset("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue
darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink
deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold
goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush
lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey
lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime
limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise
palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow
springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
yellowgreen color s b""".split())

DELIVERY_MARKER = "RNV-DELIVERY-SCRIPT-DO-NOT-SWEEP"


def rules() -> list[tuple[str, str]]:
    return BASE_RULES + EXTRA_RULES


_COMPILED: list[tuple[re.Pattern, str]] = []


def _compiled() -> list[tuple[re.Pattern, str]]:
    if len(_COMPILED) != len(rules()):
        _COMPILED[:] = [(re.compile(p, re.I), r) for p, r in rules()]
    return _COMPILED


def _cased(found: str, american: str) -> str:
    """american, in the case found was written in."""
    letters = [c for c in found if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return american.upper()
    if found[:1].isupper():
        return american[:1].upper() + american[1:]
    return american


def fix(text: str) -> str:
    """Every British spelling in text, in American spelling, keeping its case."""
    for pattern, repl in _compiled():
        text = pattern.sub(lambda m: _cased(m.group(0), m.expand(repl).lower()), text)
    return text


def is_css_data(value: str) -> bool:
    """A string of nothing but CSS color keywords and regex or CSS syntax."""
    words = re.findall(r"[A-Za-z]+", value)
    return bool(words) and any(w in CSS_GREYS for w in words) and all(w in CSS_WORDS for w in words)


def _docstring_lines(src: str) -> set[int]:
    """The line numbers that hold a docstring, or an attribute docstring."""
    lines: set[int] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i, item in enumerate(body):
            if isinstance(item, ast.Expr) and isinstance(getattr(item, "value", None), ast.Constant) \
                    and isinstance(item.value.value, str):
                if i == 0 and isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) \
                        or i > 0 and isinstance(body[i - 1], (ast.Assign, ast.AnnAssign)):
                    lines.update(range(item.lineno, item.end_lineno + 1))
    return lines


def _python_spans(src: str) -> list[tuple[int, int]]:
    """(start, end) offsets of the string literals that are CSS data, to keep."""
    keep = []
    docs = _docstring_lines(src)
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError):
        return keep
    for tok in tokens:
        if tok.type != tokenize.STRING or tok.start[0] in docs:
            continue
        try:
            value = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            continue
        if isinstance(value, str) and is_css_data(value):
            keep.append((starts[tok.start[0] - 1] + tok.start[1], starts[tok.end[0] - 1] + tok.end[1]))
    return keep


def skipped(rel: str, text: str | None = None) -> bool:
    """LICENSE files, and a delivery script at the root (up.py) that carries the
    marker. A test that only mentions the marker, to skip such a script, is
    English like any other file."""
    name = rel.rsplit("/", 1)[-1]
    if name.upper().startswith("LICENSE") or name.upper().startswith("LICENCE"):
        return True
    return "/" not in rel and re.fullmatch(r"up(_\w+)?\.py", name) is not None \
        and text is not None and DELIVERY_MARKER in text


#: A line of a tree diagram, and the gap before the note written beside it.
_TREE_LINE = re.compile("[├└]──")   # a branch drawn with box characters
_NOTE_GAP = re.compile("(?<=\\S)( {2,})(?=[#←])")  # two spaces or more, then '#' or a left arrow


def _keep_column(old: str, new: str) -> str:
    """A note beside a tree diagram keeps its column when a name before it gets
    shorter: colour_values.py is color_values.py, and the arrow after it stays
    where the arrows of the lines around it are."""
    if old == new or not _TREE_LINE.search(old):
        return new
    o, n = _NOTE_GAP.search(old), _NOTE_GAP.search(new)
    if not o or not n or o.end() == n.end():
        return new
    gap = max(2, len(n.group(1)) + o.end() - n.end())
    return new[:n.start()] + " " * gap + new[n.end():]


def _columns(old: str, new: str) -> str:
    if old == new or "──" not in old:
        return new
    old_lines, new_lines = old.split("\n"), new.split("\n")
    if len(old_lines) != len(new_lines):
        return new
    return "\n".join(_keep_column(o, n) for o, n in zip(old_lines, new_lines))


def transform_text(text: str, rel: str) -> str:
    if skipped(rel, text):
        return text
    if not rel.endswith(".py"):
        return _columns(text, fix(text))
    out, at = [], 0
    for start, end in _python_spans(text):
        out.append(fix(text[at:start]))
        out.append(text[start:end])
        at = end
    out.append(fix(text[at:]))
    return _columns(text, "".join(out))


def transform_path(rel: str) -> str:
    return fix(rel)


def british(text: str, rel: str) -> list[tuple[int, str]]:
    """Every British spelling left in text: (line, the word it is in)."""
    if skipped(rel, text):
        return []
    keep = _python_spans(text) if rel.endswith(".py") else []
    found = []
    for pattern, _ in _compiled():
        for m in pattern.finditer(text):
            if any(s <= m.start() < e for s, e in keep):
                continue
            lo, hi = m.start(), m.end()
            while lo > 0 and (text[lo - 1].isalnum() or text[lo - 1] == "_"):
                lo -= 1
            while hi < len(text) and (text[hi].isalnum() or text[hi] == "_"):
                hi += 1
            found.append((text.count("\n", 0, m.start()) + 1, text[lo:hi]))
    return sorted(found)

# ======================================================================== this round

#: Hand edits before the transform, where a renamed word would meet a name already there.
PRE = {}

#: sha256 of each file the round reaches, as the head holds it (under its old name if renamed)
BASE_SHAS = {'.github/workflows/brand-sync.yml': '978902cf644424b8ead6af4325d0c9c72b6e035c075aac28d98f34fec6cdab58', 'COLORS.md': 'e5fb771c8ddca46cebc64abe37a26f61a35549c24418659d680989a9fbb0e3ee', 'README.md': '7c7dcc74e74408fdd7f145c816e2e3ed965401cbd7d515272db93e9623c06d12', 'brand_map.json': '5b79fd845ec4f9accc2a306448e52b2737d16c48b583043486812cbf451b2264', 'core/accessibility.py': '83d30cded79b5bc0c2c1be12936cc2ddd78014cb537ad10fc6f78a3f3ec4c851', 'core/palette_formats.py': '3564ff45743a349d96ad47e14c1bd8ebf09fd5311d55fb2747102cf68e7fb7d4', 'test_rnv_color_picker.py': '75da4060e62b0fd60c2f649ed8f86368f06bad473e0e6085d1680c35930e1f0e', 'tests/conftest.py': 'ad8485ce8ba9264b577fb8a210642fa6caf9c32b51f8f1c86b37381cd92a82bb', 'tests/requirements-dev.txt': '022a1de2ef1341c6490d6a0e5096257242e4432fb31540340c5bcc8e1bd35c02', 'tests/test_about_dialog.py': '868176de33057a314f42be456b0131bf405cc1197872fc5c1a8e1cd047d3e660', 'tests/test_app_mirror.py': '863079bbd758c02db94a13247655d112796c7b7a4ef075f57b83d7ed4075766f', 'tests/test_brand_contrast.py': '78b85264d2ef0263de16d75b89dee652ef638e71ecd8a7702ba8b4b2da7feecb', 'tests/test_button_key_names.py': 'e56d9bce1f834d325d0bd808d1a2df9b7b459584900da52e9338b0ca043ed81b', 'tests/test_clipboard.py': 'c9a60127553465c61c74b88f902a8dfff1800ae4264ad8cd6d70346c77c66c30', 'tests/test_collapse_252525.py': '37bf7f73f4e67d05767c00e9a73a1fc87a5f8cb84016ed837f4a07676bf1099b', 'tests/test_color_history.py': 'fc2e3d5355bf5615c83bbfc5af6cdecfbd56e607a8f1ffcf8910145874a4a31a', 'tests/test_color_math.py': '7c3621eef2c92d2f5bf0b00def08934326f45181411d17cbe78cf3606c1b9e5f', 'tests/test_color_swatch_widget.py': '507abf85de21a4a39d6ea1e1b242b9dbab8ff3831182c6d46aa858ba7a0c30ce', 'tests/test_dependency_coherence.py': '40b3b9ecd6a7fa8d9db76bb17aa3125b367ca8b234f231dfa848e096cea3a0ad', 'tests/test_dependency_file_placement.py': 'fffe65f5f46e0f459e3d0aa3f0decbf682d43bbfac296a4830103fb8e788cc79', 'tests/test_derived_values.py': '2a3a2efc850be77caae8fdb526417ccb107ff1e633fbbdd46e29f19300fcb7f4', 'tests/test_fleet_floor.py': '4cc6dba16ba1f616ca3e8ceec0f5497e3e01f166410b3c75d9077707967a86b9', 'tests/test_gold_as_text.py': '5d782352b26da500a47360ad1b2d8fbff39c801f7089bfae843286c5e5a5daf0', 'tests/test_image_budget.py': 'c5aefe05de4bc3d4fdb770f816a57e21783287ef3a4455785d4b26565c7d5bef', 'tests/test_ink_rule.py': '6d82417d8bde76c8d383437b5eb2c1ea5d0182a153650fb1b73ff0ec49740f9b', 'tests/test_ladder_and_plate.py': '4295d377726657c7495f4d1fdb9f3f1dc063d14b349ee3ea12b0712bcf6679ea', 'tests/test_light_rewalk.py': '033887063c6503dcd7121a1f779aa6f6118f875500345f14c94679b4e2fac210', 'tests/test_light_wiring.py': 'dc889edcebc24a8cf6ac392c18668671c955dd5ec9d674346f388028a1e75a0a', 'tests/test_named_and_used.py': 'bea06f3c9743e0918f943d4e0af0bfb00c9d4d1b2b57dfcb9b79264aa62fa9a1', 'tests/test_nothing_calls_is_gone.py': 'c211a3bd8b3fb367f8997130dc3b84667ddce5b8e5f869441b6f046dc198ee61', 'tests/test_palette_formats.py': '989f8682344a660218875c42b1be3468c527a1c87d72d35a7861add955d67775', 'tests/test_readme_test_counts.py': '0e1bbeed6314433901bc41b9788fc9c9bb16df39ff621179d96e062101d4582f', 'tests/test_register_wiring.py': '7e577cffefa8cac329630f5fc1ea4204ccb46f3c044bc22c9b03bb922ee4d887', 'tests/test_screen_color_picker.py': '411ed4811c4dc31fa8a4d87be205cdfbaf31496a8728e82328ec7b92e33fadc5', 'tests/test_settings_panel.py': 'ffdf33fb788dd9b1112f7d744c879415b3af79e68f1b45273b68b0dc67d7736e', 'tests/test_status_family.py': '9915f113b6c7e26a7c2c046a9ef413bdc27e1a5651bb3b18a8d69c7116b0cfb3', 'tests/test_workers.py': '3c32571f3be93c9675a9be76c375f37a2d56c31cad69c6df464d9caff6c57f35', 'tools/sync_colors.py': '80e6d14160f3148bcf512e2df1cf4e7edd69311d888533fd9a50bcdb4116391e', 'ui/about_dialog.py': 'c9546906723f5439ebeaaa542e1864f9f502045c4cded00513fc4b5e7b218021', 'ui/settings_panel.py': '723f75450d2f5832576c1b57377e5889090da453a8d46d8852f4d09b1c9b65c5', 'utils/cache.py': 'd43668da573f148311394a11bbd739387bd21906337686f7cd6678c43deb47cc', 'utils/config.py': '675c5905b6f2739f204976e4adb130b9eadf9cfbd5d221985686cdd7f7b311c1', 'tests/colour_values.py': 'cd462f11d57bfda41bf2a3fa9497e2e52b8ecd1f156975c053ba8da67cc16cbc', 'tests/test_colour_values.py': '53ca63f0c39796dbecbc378eac1657ee876209b2dd3d9e2c5aad26dc68116b1b', 'tests/test_colours_in_sync.py': 'f7d986594bdb4fc83ceed7e668ffa156c246f2dd0173a440f3c14cc0cf1e7caf'}

#: (new name, old name)
RENAMES = [('tests/color_values.py', 'tests/colour_values.py'), ('tests/test_color_values.py', 'tests/test_colour_values.py'), ('tests/test_colors_in_sync.py', 'tests/test_colours_in_sync.py')]

NEW_FILES = {}

#: The root suite's digest, where CI holds it: (file, the head's, this round's)
DIGESTS = []

#: sha256 of every file as this round writes it
WANT = {'.github/workflows/brand-sync.yml': '877edf72068e4848862fbfeb6450e667e8aab40d35e3ba050f75d7e182c6b206', 'COLORS.md': '496f0f2b22edcbb9188791c589e74f3b55a9ac1ed4f5641acbd7eb5ab12219dd', 'README.md': '6163988f58e08d172654364a3106cf3094082ad5d0b4e7269c8e8e697c6ea19d', 'brand_map.json': '8ca8fdf750f5b58d9ffcdbd947245a13c520c2c99de225395b46d9271b5c1075', 'core/accessibility.py': '41638cdc549d88222b8090a97a6accbb48e66b88218647b723902a9fb156f718', 'core/palette_formats.py': 'c267edcf445e36b66ecb50de67ca875dd0f4c31a363c2b6a498816d0437dcd08', 'test_rnv_color_picker.py': 'd84a736a8c9cefca9e173692276a8a582f000242807778bd28d06af995ef4dec', 'tests/color_values.py': '131e9cbb89b1bc291b132a9555eec86b765902244c3e66f4347321b4c432458e', 'tests/conftest.py': '806633ade2f86f9cde485a85a36dd2110d534f636ce935b0edc2415da23be6e8', 'tests/requirements-dev.txt': '7cc3682281837a2da439691270069642ab6b97e3836b03e4ad64ece3689a8ae1', 'tests/test_about_dialog.py': '1476968ff60da8d0aa0ce9e0b361ccefef6a0d3592effa8248be1fb744201855', 'tests/test_app_mirror.py': '9cd6447f577f8bf962e0e271119ee74481155c1f32d4906f624bce61d1c757bb', 'tests/test_brand_contrast.py': 'd2e2a8947347615263bc669a8729b514c8764d8e08ac313560b6140dc2261b25', 'tests/test_button_key_names.py': 'b83eb476a3d0047a8e24f03cb54e0c543b13c12b3a1aad98c68cbcdc7a38cc7c', 'tests/test_clipboard.py': '5e11a98fbc9adbf0996ae2f73ef4bcfc13f14d0fd31068e6741454a49b419c59', 'tests/test_collapse_252525.py': '116997c59cefb420c9d855a7cf3d74ded90c1eb9f86405bd700679087c564d39', 'tests/test_color_history.py': '66f3f20443c00ef3bd4194c7295f8eae513ec55c4cf8987c6dc8b8262fbd0c8f', 'tests/test_color_math.py': '62f036af838cb2df25bb41c182cf1b75a9aed4f98fd1dbfc28babc02382e043a', 'tests/test_color_swatch_widget.py': '59e33c08715e54a0322b926e56cc407842d77958827c0fd16707b7a5e37be922', 'tests/test_color_values.py': 'e523afd0781788a0255f32df2fb0d12b14089160606d46db1735f91790e7a7f7', 'tests/test_colors_in_sync.py': 'da711394c4c0fc08865d800155020ad715fde11d49d2887d7aa4ccbef8f1c4ed', 'tests/test_dependency_coherence.py': '841e21255aee937e747c7a38e7c15b87fbbff73f3c92508a53ceecf26e6b1332', 'tests/test_dependency_file_placement.py': 'ce73e781254a06a42e646fbfdcdb9dadb6e9a04d957483cf488584ecad39ac34', 'tests/test_derived_values.py': '692ef4f85c52f7818c9e76f3821046f9909c7d6495b4583439e2ef72366bbfd6', 'tests/test_fleet_floor.py': '99e8a8a1d5214d21b9b269f39ac25f6c2b79f7240f14aefa53966409300901e6', 'tests/test_gold_as_text.py': '2e4b332e1441d4a6b1c7fdfeb410c3634424b70ca6db35aa6ee571b02078f03b', 'tests/test_image_budget.py': '0dd0f85804f4194a4200a57be266cd17823aa49fabcb25cff3274d7609863eff', 'tests/test_ink_rule.py': 'cf59653a80fe9b761675a227bfddb778fbbd6a114128444728f6a4bc5487cf28', 'tests/test_ladder_and_plate.py': '414bfd8c04c471f7933799426a486afdb0a8d0f09b460056f6c6f3c9c57057ae', 'tests/test_light_rewalk.py': '1fddcd2868bf2f79041e3ba2a99f4d070829d593242e4060ab922a0ca54e4ca4', 'tests/test_light_wiring.py': '3cdd05084efb7cd71da071dc30fc115986364873dcad780d3e37fe409590f277', 'tests/test_named_and_used.py': 'cd5e49ab9a7fb40d6b42f2bba679d5dbc46775908c55c249aacf31d77df0db78', 'tests/test_nothing_calls_is_gone.py': '629a3bd6e279cbc940d5fab1e42d9c0d3d947cca6b8c87e738fa47dd73c4bc6b', 'tests/test_palette_formats.py': 'f0b6fe5204c809335d8c69b3235a7dc773ada1e4ee59cf96655af71816a6f180', 'tests/test_readme_test_counts.py': '58f6691f3f03537a1e7eed29d695f35115344f79847b0a7b1e3e866680f98f99', 'tests/test_register_wiring.py': '6ea9d883d71cd23368b5a7166d8146b3cc67bab123c6a6745f9c6a56fd6a4c5b', 'tests/test_screen_color_picker.py': '33aad1adbbc349345b14b4ba6969971de9ea9a9ef77914ecf62bbc27f62284b7', 'tests/test_settings_panel.py': '210b01f00c90d8205daf0d4ae1b3a0ecfc4a23672784b67d439a53bc61026448', 'tests/test_status_family.py': '8fb36b3716beaf2b458c02e257f99872193eb7fa3326622e9038db4892014db7', 'tests/test_workers.py': 'a75d3d5e232b3bf8937fa1713c210e8bc11c3c9a1fc690793d39d9907c3192e4', 'tools/sync_colors.py': 'b9bbd1c2785e5fbc56bd4f0e2b280a902874bd8ac27bdeca5768cf25e2c0818a', 'ui/about_dialog.py': 'a5ab2b7dc9654b7e5b65369c11e614e5c53dea7e79c7de3f3d004c9f16ad5255', 'ui/settings_panel.py': '494add9a16b774b3aa495121c88b354ae729d2f7f1ecb59b8b9056b6b7f4e088', 'utils/cache.py': '027b34c28a4553cd44c5cadff857da4e4a72b0cd0535fd343641e363aa811cbf', 'utils/config.py': '2eb546f7c1f82742258eb9a5be39a63f773429ab361896ddf24cb23e8c75ac14'}

#: Every British spelling the round leaves, {file: count}: CSS's keywords, in data (above).
KEPT = {'tests/test_named_and_used.py': 7, 'tests/test_settings_panel.py': 1}

COLOR_FILE = 'utils/config.py'


def edits(tree) -> None:
    for rel, was in BASE_SHAS.items():
        got = hashlib.sha256(tree.read(rel).encode("utf-8")).hexdigest()
        if got != was:
            raise Stop(f"{rel} is not the head's file this round was derived from ({got[:12]}). "
                       f"Nothing was written. The file moved; re-derive before trusting the script.",
                       EXIT_CANNOT_RUN)
    old_names = {old: new for new, old in RENAMES}
    for rel in BASE_SHAS:
        text = tree.read(rel)
        for a, b in PRE.get(rel, []):
            if text.count(a) != 1:
                raise Stop(f"{rel}: the hand edit's anchor is not there once", EXIT_CANNOT_RUN)
            text = text.replace(a, b)
        new = transform_text(text, rel)
        if rel in old_names:
            tree.delete(rel)
            tree.write(old_names[rel], new)
            tree.form[old_names[rel]] = tree.form[rel]   # a renamed file keeps its BOM and line endings
        else:
            tree.write(rel, new)
    for rel, was, now in DIGESTS:
        tree.sub(rel, was, now)
    for rel, body in NEW_FILES.items():
        if (tree.root / rel).exists():
            raise Stop(f"{rel} already exists here, and this round creates it. Nothing was written.",
                       EXIT_CANNOT_RUN)
        tree.write(rel, body)


#: What the rules must do, written out, so a changed rule is refused by name.
SAMPLES = {"colour": "color", "Colours": "Colors", "COLOUR_FILE": "COLOR_FILE", "grey": "gray", "GREY_44": "GRAY_44",
           "greyscale": "grayscale", "behaviour": "behavior", "centre": "center", "centred": "centered",
           "normalise": "normalize", "optimisation": "optimization", "licence": "license", "programme": "program",
           "labelled": "labeled", "honours": "honors", "judgement": "judgment", "neighbours": "neighbors",
           "maths": "math", "Maths": "Math", "quantisation": "quantization", "linearised": "linearized",
           "centralised": "centralized", "parameterised": "parameterized", "dialled": "dialed",
           "equalled": "equaled", "mathsy": "mathsy",
           "cancelled": "cancelled", "realistic": "realistic", "programmer": "programmer", "organism": "organism",
           "central": "central", "criticism": "criticism", "emphasis": "emphasis"}


#: Where the exceptions end, written out: (text, file, what this round makes of it, what that shows).
NL = chr(10)
_TREE_WAS = "\u2502   \u251c\u2500\u2500 colour_values.py   \u2190 a" + NL
_TREE_IS = "\u2502   \u251c\u2500\u2500 color_values.py    \u2190 a" + NL
_TREE_NEXT = "\u2502   \u251c\u2500\u2500 conftest.py        \u2190 b" + NL
BOUNDARY = [
    ("names = {'grey': 1, 'lightgrey': 2}" + NL, "x.py", "names = {'grey': 1, 'lightgrey': 2}" + NL,
     "CSS's own keywords, in data, are kept"),
    ("PATTERN = r'(gray|grey)'" + NL, "x.py", "PATTERN = r'(gray|grey)'" + NL, "a regex for CSS's keywords is kept"),
    ("x = 'a grey line'" + NL, "x.py", "x = 'a gray line'" + NL, "a sentence in a string is English"),
    ('\"\"\"grey\"\"\"' + NL, "x.py", '\"\"\"gray\"\"\"' + NL, "a docstring is English, whatever its words"),
    ("# grey" + NL, "x.py", "# gray" + NL, "a comment is English"),
    ("grey" + NL, "notes.md", "gray" + NL, "a file that is not Python is English"),
    ("licence, colour" + NL, "LICENSE", "licence, colour" + NL, "legal text is kept"),
    (_TREE_WAS + _TREE_NEXT, "README.md", _TREE_IS + _TREE_NEXT, "a note beside a tree diagram keeps its column"),
]


def _checkout(tree) -> list[str]:
    """Every file git tracks here, as this round leaves them: a renamed one under its new name."""
    try:
        out = subprocess.run(["git", "-C", str(tree.root), "ls-files", "-z"], capture_output=True,
                             check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as e:
        raise Stop(f"git could not list this checkout's files ({e}). This round reads every one of them, "
                   f"to see that nothing British is left. Nothing was written.", EXIT_CANNOT_RUN)
    tracked = {rel for rel in out.split(chr(0)) if rel}
    return sorted((tracked - tree.deleted) | set(tree.files))


def _plain(tree, rel: str) -> int:
    """How many British spellings a file holds, found with no exception applied."""
    if rel in tree.files:
        text = tree.files[rel]
    else:
        path = tree.root / rel
        if not path.is_file():
            return 0
        raw = path.read_bytes()
        if b"\0" in raw:
            return 0
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return 0
    if skipped(rel, text):
        return 0
    return sum(len(pattern.findall(text)) for pattern, _ in _compiled())


def checks(tree) -> None:
    # ---- the rules do what they say, and leave what they say they leave
    wrong = {b: fix(b) for b, a in SAMPLES.items() if fix(b) != a}
    assert not wrong, f"the spelling rules give {wrong}"
    for text, rel, want, shows in BOUNDARY:
        got = transform_text(text, rel)
        assert got == want, f"{shows}, and the round makes {text!r} into {got!r}"
    # ---- no value moves: every value the color file defined is what it was, under its new name
    def values(text):
        root = str(tree.root)
        added = root not in sys.path
        if added:
            sys.path.insert(0, root)
        try:
            ns = {"__file__": str(tree.root / COLOR_FILE), "__name__": COLOR_FILE[:-3].replace("/", ".")}
            exec(compile(text, COLOR_FILE, "exec"), ns)
        finally:
            if added:
                sys.path.remove(root)
        return {k: v for k, v in ns.items() if not k.startswith("__") and not callable(v)
                and type(v).__name__ not in ("TypeAliasType", "module", "Logger")
                and not (isinstance(v, str) and os.sep in v)}
    before, after = values(_original(tree, COLOR_FILE)), values(tree.read(COLOR_FILE))
    assert sorted(fix(k) for k in before) == sorted(after), \
        f"{COLOR_FILE} defines other names: {sorted(set(map(fix, before)) ^ set(after))}"
    moved_values = sorted(k for k in before if fix(repr(before[k])) != repr(after[fix(k)]))
    assert not moved_values, f"a value moved: {moved_values}"
    assert len(before) >= 40, f"only {len(before)} values compared -- the comparison is blind"
    # ---- the map: the same entries, under the new names
    was_map = json.loads(_original(tree, "brand_map.json"))
    now_map = json.loads(tree.read("brand_map.json"))
    assert json.loads(fix(json.dumps(was_map))) == now_map, "brand_map.json holds other entries"
    assert "colors" in now_map and "color_file" in now_map, "the map's keys are not in American spelling"
    # ---- nothing British is left, outside CSS's keywords and LICENSE files
    left = [(rel, b) for rel, t in tree.files.items() for b in british(t, rel)]
    assert not left, f"British spelling left: {left[:20]}"
    # ---- the whole checkout, read plainly: exactly what this round leaves (KEPT), and no more
    found = {rel: n for rel in _checkout(tree) if (n := _plain(tree, rel))}
    differ = {rel: (found.get(rel, 0), KEPT.get(rel, 0)) for rel in sorted(set(found) | set(KEPT))
              if found.get(rel, 0) != KEPT.get(rel, 0)}
    moved = sorted(rel for rel in differ if rel not in tree.files)
    if moved:
        raise Stop(f"British spelling in files this round does not write, other than it was derived with: "
                   f"{ {rel: differ[rel] for rel in moved[:10]} } as (found, expected). The checkout moved; "
                   f"re-derive before trusting the script. Nothing was written.", EXIT_CANNOT_RUN)
    assert not differ, f"British spelling left, as (found, what this round leaves): {differ}"
    # ---- every file this round writes, as it writes it
    assert sorted(tree.files) == sorted(WANT), f"this round writes {sorted(tree.files)}"
    assert sorted(tree.deleted) == sorted(old for _, old in RENAMES), f"this round removes {sorted(tree.deleted)}"
    for rel, want in WANT.items():
        got = hashlib.sha256(tree.read(rel).encode("utf-8")).hexdigest()
        assert got == want, f"{rel} is not the file this round writes: {got[:12]}"

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
