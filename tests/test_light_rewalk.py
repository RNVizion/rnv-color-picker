"""RNV-STATUS-LIGHT-REWALK -- the light boundary is #e8e8e8, and it is shared.

Installed by the rev 31 follow-up. Two things it pins that the migration's own
guard does not:

  * the light text variants reach #e8e8e8, which they did not at rev 30;
  * they stop at #e0e0e0, and so does BRAND_DARK_GOLD_DEEP -- one boundary for
    every brand text family rather than one per family.

The second is the load-bearing half. A test that only asserted "these clear
#e8e8e8" would pass equally on values walked to #e0e0e0, which is the choice
the register explicitly did not make.
"""
from __future__ import annotations

import pytest

from utils import config as C

TEXT_FLOOR = 4.5

REWALKED = {'STATUS_SUCCESS_TEXT_LIGHT': '#825d79', 'STATUS_ERROR_TEXT_LIGHT': '#ae4650'}

# The rungs the register publishes, lightest first. #e0e0e0 is in the list on
# purpose: it is asserted to FAIL, which is what makes it a boundary.
REACHES = ("#ffffff", "#fbfbfb", "#f5f5f5", "#eeeeee", "#e8e8e8")
STOPS_AT = "#e0e0e0"

GOLD_DEEP = "#7e6529"   # BRAND_DARK_GOLD_DEEP, the family this shares with


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
    """Pinned by value. rev 30 held #8a6581 / #976633 / #b84e58, walked against
    #f5f5f5; rev 31 holds these, walked against #e8e8e8."""
    assert getattr(C, name) == value


@pytest.mark.parametrize("name", sorted(REWALKED))
@pytest.mark.parametrize("ground", REACHES)
def test_the_light_text_reaches_every_rung_down_to_the_ground_floor(name, ground):
    ratio = contrast(getattr(C, name), ground)
    assert ratio >= TEXT_FLOOR, f"{name} on {ground} = {ratio:.4f}"


@pytest.mark.parametrize("name", sorted(REWALKED))
def test_the_light_text_stops_where_the_gold_stops(name):
    """The half that makes #e8e8e8 a BOUNDARY rather than an arbitrary target.

    Values walked to #e0e0e0 would pass the test above and fail this one. The
    register chose #e8e8e8 because BRAND_DARK_GOLD_DEEP already stops there --
    4.53 on #e8e8e8, 4.21 on #e0e0e0 -- so below it no brand text of any
    family is carried, and an author does not have to remember which family
    they are in to know where text stops.

    If this ever goes green, either the values were re-walked deeper without
    the gold moving with them, or the gold moved. Either way the two families
    have separated and the boundary is two boundaries again.
    """
    assert contrast(GOLD_DEEP, STOPS_AT) < TEXT_FLOOR, (
        "BRAND_DARK_GOLD_DEEP now clears #e0e0e0 -- the shared boundary moved "
        "and these values should be re-walked with it")
    assert contrast(getattr(C, name), STOPS_AT) < TEXT_FLOOR, (
        f"{name} now clears {STOPS_AT}, which BRAND_DARK_GOLD_DEEP does "
        f"not. The two text families no longer share a boundary.")


def test_this_guard_is_measuring_the_right_thing():
    """Guard the guard. If contrast() ever returned a constant, every
    assertion above would pass while checking nothing."""
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0, abs=0.001)
    assert contrast(GOLD_DEEP, "#e8e8e8") == pytest.approx(4.53, abs=0.02)
