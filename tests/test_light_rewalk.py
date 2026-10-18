"""RNV-STATUS-LIGHT-REWALK -- the light boundary is the gold text floor,
REGISTER_GOLD_TEXT_GROUND_FLOOR, and it is shared.

Installed by the rev 31 follow-up. Two things it pins that the migration's own
guard does not:

  * the light text variants reach REGISTER_GOLD_TEXT_GROUND_FLOOR, which they
    did not at rev 30;
  * they stop at APP_PRESSED_LIGHT, and so does BRAND_DARK_GOLD_DEEP -- one boundary for
    every brand text family rather than one per family.

The second is the load-bearing half. A test that only asserted "these clear
REGISTER_GOLD_TEXT_GROUND_FLOOR" would pass equally on values walked to
APP_PRESSED_LIGHT, which is the choice
the register explicitly did not make.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from utils import config as C
from tests.colour_values import (
    EXAMPLE_BLACK, EXAMPLE_WHITE, REGISTER_APP_SURFACE_LIGHT_2,
    REGISTER_GOLD_TEXT_GROUND_FLOOR)

#: RNV-COLOUR-SYNC, 2026-10-16. Where each colour comes from, as brand_map.json
#: says. The values are held by tests/test_colours_in_sync.py, against the
#: register at the pin; what this file holds is the name each one takes.
BRAND_MAP = json.loads((pathlib.Path(__file__).resolve().parents[1] / "brand_map.json").read_text(encoding="utf-8"))["colours"]

TEXT_FLOOR = 4.5

#: Each re-walked value, by the register name it is written from.
REWALKED = {'STATUS_SUCCESS_TEXT_LIGHT': 'STATUS.success-text-light',
            'STATUS_ERROR_TEXT_LIGHT': 'STATUS.error-text-light'}

# The rungs the register publishes, lightest first. APP_PRESSED_LIGHT is in the list on
# purpose: it is asserted to FAIL, which is what makes it a boundary.
REACHES = (C.WHITE, REGISTER_APP_SURFACE_LIGHT_2, C.APP_SURFACE_LIGHT_3, C.APP_HOVER_LIGHT,
           REGISTER_GOLD_TEXT_GROUND_FLOOR)
STOPS_AT = C.APP_PRESSED_LIGHT

GOLD_DEEP = C.BRAND_DARK_GOLD_DEEP   # the family this shares with


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(value: str) -> float:
    h = value.lstrip("#")
    t = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return 0.2126 * _lin(t[0]) + 0.7152 * _lin(t[1]) + 0.0722 * _lin(t[2])


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name,value", sorted(REWALKED.items()))
def test_the_light_values_are_the_re_walked_ones(name, value):
    """Pinned by value. rev 30 held RETIRED_REV30_SUCCESS_TEXT_LIGHT,
    RETIRED_REV30_WARNING_TEXT_LIGHT and RETIRED_REV30_ERROR_TEXT_LIGHT, walked
    against APP_SURFACE_LIGHT_3; rev 31 holds these, walked against
    REGISTER_GOLD_TEXT_GROUND_FLOOR.

    RNV-COLOUR-SYNC, 2026-10-16: pinned by the register name brand_map.json
    writes it from; tests/test_colours_in_sync.py holds the value."""
    assert BRAND_MAP[name] == value


@pytest.mark.parametrize("name", sorted(REWALKED))
@pytest.mark.parametrize("ground", REACHES)
def test_the_light_text_reaches_every_rung_down_to_the_ground_floor(name, ground):
    ratio = contrast(getattr(C, name), ground)
    assert ratio >= TEXT_FLOOR, f"{name} on {ground} = {ratio:.4f}"


@pytest.mark.parametrize("name", sorted(REWALKED))
def test_the_light_text_stops_where_the_gold_stops(name):
    """The half that makes REGISTER_GOLD_TEXT_GROUND_FLOOR a BOUNDARY rather
    than an arbitrary target.

    Values walked to APP_PRESSED_LIGHT would pass the test above and fail this
    one. The register chose REGISTER_GOLD_TEXT_GROUND_FLOOR because
    BRAND_DARK_GOLD_DEEP already stops there -- 4.53 on
    REGISTER_GOLD_TEXT_GROUND_FLOOR, 4.21 on APP_PRESSED_LIGHT -- so below it no
    brand text of any family is carried, and an author does not have to
    remember which family they are in to know where text stops.

    If this ever goes green, either the values were re-walked deeper without
    the gold moving with them, or the gold moved. Either way the two families
    have separated and the boundary is two boundaries again.
    """
    assert contrast(GOLD_DEEP, STOPS_AT) < TEXT_FLOOR, (
        f"BRAND_DARK_GOLD_DEEP now clears {STOPS_AT} -- the shared boundary moved "
        "and these values should be re-walked with it")
    assert contrast(getattr(C, name), STOPS_AT) < TEXT_FLOOR, (
        f"{name} now clears {STOPS_AT}, which BRAND_DARK_GOLD_DEEP does "
        f"not. The two text families no longer share a boundary.")


def test_this_guard_is_measuring_the_right_thing():
    """Guard the guard. If contrast() ever returned a constant, every
    assertion above would pass while checking nothing."""
    assert contrast(EXAMPLE_BLACK, EXAMPLE_WHITE) == pytest.approx(21.0, abs=0.01)
    assert contrast(EXAMPLE_WHITE, EXAMPLE_WHITE) == pytest.approx(1.0, abs=0.001)
    assert contrast(GOLD_DEEP, REGISTER_GOLD_TEXT_GROUND_FLOOR) == pytest.approx(4.53, abs=0.02)
