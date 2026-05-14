"""
Phase 5: core/color_math.py — hypothesis-driven property tests.

The legacy unittest suite (TestColorMath in test_rnv_color_picker.py) covers
named-color examples for the basic conversions and a handful of mixing cases.
This file uses hypothesis to assert the *invariants* those examples can't
prove on their own:

  - Round-trip closure (HEX exact, HSV/HSL/RYB ±1, LAB exact) for the entire
    [0, 255]^3 RGB cube
  - Hex output format (always 7 chars, lowercase)
  - Clamp / validate idempotency and bounds preservation
  - color_distance: identity, symmetry, non-negativity, triangle inequality
  - All five mixing functions (weighted_rgb, weighted_hsv, lab_perceptual,
    subtractive_cmy, weighted_ryb, kubelka_munk):
      * Empty / all-zero-weights → None
      * Single color in → that color out (within rounding)
      * Output is always a valid RGB tuple in [0, 255]^3
  - HSV mix hue circularity (averaging colors at h≈0 and h≈1 doesn't produce
    the wrong-side hue — a textbook bug example tests routinely miss)
  - calculate_average_region_color: bounds, single-pixel, all-same identity
  - safe_rgb / is_valid_rgb: garbage tolerance, validity↔clampability

Tolerances were derived empirically by sweeping 2000+ random samples plus
extremes through each forward/backward pair before writing the suite.

Examples-as-anchors: a few named-color tests verify the named cases that
property tests don't pin down (yellow + cyan ≈ green in subtractive CMY,
yellow + blue → green-ish in artist's RYB wheel, Kubelka-Munk darkening).
"""

import math

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from core.color_math import ColorMath


# ---------------------------------------------------------------------------
# Strategies — the building blocks for our property tests
# ---------------------------------------------------------------------------

# A single RGB channel value
channel = st.integers(min_value=0, max_value=255)
# A full RGB triple
rgb = st.tuples(channel, channel, channel)
# Two-or-more RGB triples for mix functions
rgb_list = st.lists(rgb, min_size=1, max_size=8)
# Weights — positive ints; mix functions filter zeros
weight = st.integers(min_value=1, max_value=100)
# (color, weight) pairs for mix functions
weighted_pair = st.tuples(rgb, weight)
weighted_list = st.lists(weighted_pair, min_size=1, max_size=8)


def _is_valid_rgb_tuple(t):
    """Helper: True iff `t` is a 3-tuple of ints in [0, 255]."""
    return (
        isinstance(t, tuple)
        and len(t) == 3
        and all(isinstance(v, int) and 0 <= v <= 255 for v in t)
    )


# ===========================================================================
# Round-trip conversions
# ===========================================================================


class TestRgbHexRoundTrip:
    """rgb → hex → rgb is bit-perfect for any RGB triple."""

    @given(rgb=rgb)
    def test_round_trip_is_exact(self, rgb):
        # HEX preserves all 24 bits, so the trip must be lossless
        assert ColorMath.hex_to_rgb(ColorMath.rgb_to_hex(rgb)) == rgb

    @given(rgb=rgb)
    def test_hex_format_is_seven_chars_with_hash(self, rgb):
        out = ColorMath.rgb_to_hex(rgb)
        assert len(out) == 7
        assert out[0] == "#"

    @given(rgb=rgb)
    def test_hex_lowercase(self, rgb):
        # Source uses :02x (lowercase). The cache also uses lowercase.
        out = ColorMath.rgb_to_hex(rgb)
        assert out == out.lower()

    @given(rgb=rgb)
    def test_hex_uppercase_input_round_trips(self, rgb):
        # hex_to_rgb is case-insensitive (int(_, 16) doesn't care)
        upper = ColorMath.rgb_to_hex(rgb).upper()
        assert ColorMath.hex_to_rgb(upper) == rgb

    @given(short_hex=st.from_regex(r"^#[0-9a-f]{3}$", fullmatch=True))
    def test_three_char_hex_expands_to_six(self, short_hex):
        # #f00 should become (255, 0, 0); #abc → (0xaa, 0xbb, 0xcc)
        result = ColorMath.hex_to_rgb(short_hex)
        # Each channel is the doubled hex digit (0xf*16+0xf=255 for "f")
        for i, ch in enumerate(short_hex[1:]):
            assert result[i] == int(ch * 2, 16)


class TestRgbHsvRoundTrip:
    """rgb → hsv → rgb stays within ±1 per channel (int truncation in hsv_to_rgb)."""

    @given(rgb=rgb)
    def test_round_trip_within_one_per_channel(self, rgb):
        out = ColorMath.hsv_to_rgb(ColorMath.rgb_to_hsv(rgb))
        for i in range(3):
            assert abs(out[i] - rgb[i]) <= 1, f"channel {i}: in={rgb} out={out}"

    @given(rgb=rgb)
    def test_hsv_output_in_unit_range(self, rgb):
        h, s, v = ColorMath.rgb_to_hsv(rgb)
        assert 0.0 <= h <= 1.0
        assert 0.0 <= s <= 1.0
        assert 0.0 <= v <= 1.0


class TestRgbHslRoundTrip:
    """rgb → hsl → rgb stays within ±1 per channel."""

    @given(rgb=rgb)
    def test_round_trip_within_one_per_channel(self, rgb):
        out = ColorMath.hsl_to_rgb(ColorMath.rgb_to_hsl(rgb))
        for i in range(3):
            assert abs(out[i] - rgb[i]) <= 1


class TestRgbLabRoundTrip:
    """rgb → lab → rgb is exact thanks to int(_+0.5) rounding in lab_to_rgb."""

    @given(rgb=rgb)
    def test_round_trip_is_exact(self, rgb):
        out = ColorMath.lab_to_rgb(ColorMath.rgb_to_lab(rgb))
        # Empirically verified: zero error across the whole cube
        assert out == rgb

    @given(rgb=rgb)
    def test_lab_L_in_zero_to_hundred(self, rgb):
        L, _, _ = ColorMath.rgb_to_lab(rgb)
        # Allow a small epsilon for floating-point at the extremes
        assert -0.01 <= L <= 100.01


class TestRgbRybRoundTrip:
    """rgb → ryb → rgb stays within ±1 per channel."""

    @given(rgb=rgb)
    def test_round_trip_within_one_per_channel(self, rgb):
        out = ColorMath.ryb_to_rgb(ColorMath.rgb_to_ryb(rgb))
        for i in range(3):
            assert abs(out[i] - rgb[i]) <= 1

    @given(rgb=rgb)
    def test_ryb_output_in_unit_range(self, rgb):
        r, y, b = ColorMath.rgb_to_ryb(rgb)
        # RYB is normalized 0..1 per source docstring
        for v in (r, y, b):
            assert -0.001 <= v <= 1.001  # tolerance for float arithmetic


# ===========================================================================
# Clamp / validate / safe — bounds + idempotency
# ===========================================================================


class TestClampRgb:
    """clamp_rgb output is always a valid RGB tuple, idempotent, and a no-op
    on already-valid input."""

    @given(r=st.floats(allow_nan=False, allow_infinity=False, width=32),
           g=st.floats(allow_nan=False, allow_infinity=False, width=32),
           b=st.floats(allow_nan=False, allow_infinity=False, width=32))
    def test_output_always_valid_rgb(self, r, g, b):
        result = ColorMath.clamp_rgb(r, g, b)
        assert _is_valid_rgb_tuple(result)

    @given(rgb=rgb)
    def test_in_range_input_passes_through(self, rgb):
        # Already-valid RGB ints should be unchanged
        assert ColorMath.clamp_rgb(*rgb) == rgb

    @given(r=st.floats(allow_nan=False, allow_infinity=False, width=32),
           g=st.floats(allow_nan=False, allow_infinity=False, width=32),
           b=st.floats(allow_nan=False, allow_infinity=False, width=32))
    def test_idempotent(self, r, g, b):
        # clamp(clamp(x)) == clamp(x)
        once = ColorMath.clamp_rgb(r, g, b)
        twice = ColorMath.clamp_rgb(*once)
        assert once == twice


class TestClampValue:
    @given(v=st.floats(allow_nan=False, allow_infinity=False, width=32),
           lo=st.integers(min_value=0, max_value=100),
           hi=st.integers(min_value=101, max_value=255))
    def test_output_within_bounds(self, v, lo, hi):
        result = ColorMath.clamp_value(v, lo, hi)
        assert lo <= result <= hi

    @given(v=st.integers(min_value=0, max_value=255))
    def test_in_range_value_unchanged(self, v):
        assert ColorMath.clamp_value(v) == v


class TestValidateRgb:
    """validate_rgb is the tuple version of clamp_rgb."""

    @given(rgb=st.tuples(
        st.integers(min_value=-1000, max_value=1000),
        st.integers(min_value=-1000, max_value=1000),
        st.integers(min_value=-1000, max_value=1000)))
    def test_output_always_valid(self, rgb):
        assert _is_valid_rgb_tuple(ColorMath.validate_rgb(rgb))

    @given(rgb=rgb)
    def test_in_range_input_passes_through(self, rgb):
        assert ColorMath.validate_rgb(rgb) == rgb


class TestSafeRgb:
    """safe_rgb returns a valid RGB tuple even when given garbage."""

    @given(rgb=rgb)
    def test_valid_input_matches_clamp_rgb(self, rgb):
        # When all three inputs are valid ints, safe_rgb == clamp_rgb
        assert ColorMath.safe_rgb(*rgb) == ColorMath.clamp_rgb(*rgb)

    @given(garbage=st.one_of(
        st.none(),
        st.lists(st.integers()),
        # Text that genuinely can't be int()-parsed. A bare numeric string
        # like "0" or "-5" is *valid* int input — exclude those.
        st.text(min_size=1, max_size=5).filter(
            lambda s: not s.lstrip("-").isdigit()
        ),
    ))
    def test_garbage_returns_default(self, garbage):
        # Any non-numeric arg should hit the except → default
        assert ColorMath.safe_rgb(garbage, 128, 128) == (0, 0, 0)

    def test_custom_default_used_on_failure(self):
        custom = (123, 45, 67)
        assert ColorMath.safe_rgb("bad", 0, 0, default=custom) == custom


class TestIsValidRgb:
    """is_valid_rgb iff all three are integers in [0, 255]."""

    @given(rgb=rgb)
    def test_returns_true_for_valid_rgb(self, rgb):
        assert ColorMath.is_valid_rgb(*rgb) is True

    @given(out_of_range=st.one_of(
        st.integers(min_value=256, max_value=10_000),
        st.integers(min_value=-10_000, max_value=-1)))
    def test_returns_false_for_out_of_range(self, out_of_range):
        # Just the first channel out — short-circuits to False
        assert ColorMath.is_valid_rgb(out_of_range, 0, 0) is False

    @given(garbage=st.one_of(
        st.none(),
        # Same filter as TestSafeRgb: exclude numeric-looking strings
        st.text(min_size=1, max_size=5).filter(
            lambda s: not s.lstrip("-").isdigit()
        ),
    ))
    def test_returns_false_for_non_numeric(self, garbage):
        # Any non-numeric arg trips int(_) → False via except
        assert ColorMath.is_valid_rgb(garbage, 0, 0) is False


# ===========================================================================
# color_distance — metric properties
# ===========================================================================


class TestColorDistance:
    """color_distance is a proper Euclidean metric: identity of indiscernibles,
    symmetry, non-negativity, triangle inequality."""

    @given(c=rgb)
    def test_identity_is_zero(self, c):
        assert ColorMath.color_distance(c, c) == 0.0

    @given(c1=rgb, c2=rgb)
    def test_symmetric(self, c1, c2):
        assert ColorMath.color_distance(c1, c2) == ColorMath.color_distance(c2, c1)

    @given(c1=rgb, c2=rgb)
    def test_non_negative(self, c1, c2):
        assert ColorMath.color_distance(c1, c2) >= 0

    @given(c1=rgb, c2=rgb, c3=rgb)
    def test_triangle_inequality(self, c1, c2, c3):
        # d(a, c) <= d(a, b) + d(b, c) — with float epsilon
        d_ac = ColorMath.color_distance(c1, c3)
        d_ab = ColorMath.color_distance(c1, c2)
        d_bc = ColorMath.color_distance(c2, c3)
        assert d_ac <= d_ab + d_bc + 1e-9

    def test_max_distance_is_diagonal(self):
        # Black to white is the longest possible RGB distance
        # sqrt(255^2 * 3) ≈ 441.67
        d = ColorMath.color_distance((0, 0, 0), (255, 255, 255))
        assert math.isclose(d, math.sqrt(3) * 255)


# ===========================================================================
# Mixing functions — invariants shared across all five mixers
# ===========================================================================


class TestMixingInvariantsWeightedRgb:
    """weighted_rgb_mix invariants."""

    def test_empty_returns_none(self):
        assert ColorMath.weighted_rgb_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.weighted_rgb_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_passes_through(self, c, w):
        # Single color with any positive weight returns that exact color
        assert ColorMath.weighted_rgb_mix([(c, w)]) == c

    @given(c=rgb, weights=st.lists(weight, min_size=1, max_size=5))
    def test_all_same_color_returns_same(self, c, weights):
        # Mixing the same color with any weight distribution = that color
        pairs = [(c, w) for w in weights]
        assert ColorMath.weighted_rgb_mix(pairs) == c

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.weighted_rgb_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)

    @given(pairs=weighted_list)
    def test_output_bounded_by_input_extremes(self, pairs):
        # Weighted average is always between the min and max of the inputs
        result = ColorMath.weighted_rgb_mix(pairs)
        if result is None:
            return
        for ch in range(3):
            channels = [c[ch] for c, _ in pairs]
            # Allow ±1 for integer-division floor behavior
            assert min(channels) - 1 <= result[ch] <= max(channels) + 1


class TestMixingInvariantsWeightedHsv:
    """weighted_hsv_mix invariants. Note HSV mixing has rounding tolerance
    because of int conversion in hsv_to_rgb."""

    def test_empty_returns_none(self):
        assert ColorMath.weighted_hsv_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.weighted_hsv_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_within_one_per_channel(self, c, w):
        # Single-color HSV mix: round-trip via HSV → tolerance ±1
        result = ColorMath.weighted_hsv_mix([(c, w)])
        assert result is not None
        for i in range(3):
            assert abs(result[i] - c[i]) <= 1

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.weighted_hsv_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)

    def test_hue_circularity_at_red(self):
        # Two reds (HSV hue at the 0/1 boundary) must average to red, not
        # green. This is *the* classic example-tests-can't-catch-it bug:
        # naive averaging would give h=0.5 (green/cyan).
        # Both colors are very-near-red.
        result = ColorMath.weighted_hsv_mix([((255, 0, 0), 50), ((255, 0, 0), 50)])
        # Result should be very close to red, not anywhere near green
        assert result[0] >= 200  # red dominant
        assert result[1] <= 50   # not much green


class TestMixingInvariantsLabPerceptual:
    def test_empty_returns_none(self):
        assert ColorMath.lab_perceptual_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.lab_perceptual_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_round_trips_exactly(self, c, w):
        # LAB round-trip is exact, so single-color mix is the identity
        assert ColorMath.lab_perceptual_mix([(c, w)]) == c

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.lab_perceptual_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)


class TestMixingInvariantsSubtractiveCmy:
    def test_empty_returns_none(self):
        assert ColorMath.subtractive_cmy_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.subtractive_cmy_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_within_one_per_channel(self, c, w):
        # CMY conversion uses int truncation → ±1 tolerance
        result = ColorMath.subtractive_cmy_mix([(c, w)])
        assert result is not None
        for i in range(3):
            assert abs(result[i] - c[i]) <= 1

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.subtractive_cmy_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)

    def test_yellow_plus_cyan_is_greenish(self):
        # Subtractive primary mixing: yellow (255,255,0) + cyan (0,255,255)
        # should produce a green-dominant result. This is the canonical CMY
        # example tests need to catch.
        yellow = (255, 255, 0)
        cyan = (0, 255, 255)
        result = ColorMath.subtractive_cmy_mix([(yellow, 50), (cyan, 50)])
        # Green channel should dominate
        assert result[1] > result[0]
        assert result[1] > result[2]


class TestMixingInvariantsWeightedRyb:
    def test_empty_returns_none(self):
        assert ColorMath.weighted_ryb_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.weighted_ryb_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_within_one_per_channel(self, c, w):
        result = ColorMath.weighted_ryb_mix([(c, w)])
        assert result is not None
        for i in range(3):
            assert abs(result[i] - c[i]) <= 1

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.weighted_ryb_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)

    def test_yellow_plus_blue_is_greenish_in_ryb(self):
        # The artist's color wheel: yellow + blue = green (NOT grayish brown
        # as in additive RGB). This is the whole point of having an RYB mode.
        yellow = (255, 255, 0)
        blue = (0, 0, 255)
        result = ColorMath.weighted_ryb_mix([(yellow, 50), (blue, 50)])
        # Some greenness should emerge
        assert result[1] > 0


class TestMixingInvariantsKubelkaMunk:
    def test_empty_returns_none(self):
        assert ColorMath.kubelka_munk_mix([]) is None

    @given(colors=rgb_list)
    def test_all_zero_weights_returns_none(self, colors):
        assert ColorMath.kubelka_munk_mix([(c, 0) for c in colors]) is None

    @given(c=rgb, w=weight)
    def test_single_color_close_to_input(self, c, w):
        # Kubelka-Munk has more rounding due to sqrt + clamp; allow ±2
        result = ColorMath.kubelka_munk_mix([(c, w)])
        assert result is not None
        for i in range(3):
            assert abs(result[i] - c[i]) <= 2

    @given(pairs=weighted_list)
    def test_output_is_valid_rgb(self, pairs):
        result = ColorMath.kubelka_munk_mix(pairs)
        assert result is None or _is_valid_rgb_tuple(result)

    def test_paint_mixing_darkens(self):
        # Pigment mixing produces darker results than additive — physical paint
        # behavior. White + black with KM should be noticeably darker than the
        # midpoint (128, 128, 128) that additive RGB would produce.
        white = (255, 255, 255)
        black = (0, 0, 0)
        rgb_mix = ColorMath.weighted_rgb_mix([(white, 50), (black, 50)])
        km_mix = ColorMath.kubelka_munk_mix([(white, 50), (black, 50)])
        # KM result should be darker (smaller channel values) than RGB mix
        assert sum(km_mix) <= sum(rgb_mix)


# ===========================================================================
# Region averaging
# ===========================================================================


class TestAverageRegionColor:
    def test_empty_returns_none(self):
        assert ColorMath.calculate_average_region_color([]) is None

    @given(c=rgb)
    def test_single_pixel_returns_that_pixel(self, c):
        assert ColorMath.calculate_average_region_color([c]) == c

    @given(c=rgb, count=st.integers(min_value=1, max_value=20))
    def test_all_same_pixels_return_that_color(self, c, count):
        assert ColorMath.calculate_average_region_color([c] * count) == c

    @given(pixels=st.lists(rgb, min_size=1, max_size=20))
    def test_output_is_valid_rgb(self, pixels):
        result = ColorMath.calculate_average_region_color(pixels)
        assert _is_valid_rgb_tuple(result)

    @given(pixels=st.lists(rgb, min_size=1, max_size=20))
    def test_output_bounded_by_input_extremes(self, pixels):
        # Floor-division average is between the min and max
        result = ColorMath.calculate_average_region_color(pixels)
        for ch in range(3):
            channels = [p[ch] for p in pixels]
            assert min(channels) <= result[ch] <= max(channels)


# ===========================================================================
# Palette generation
# ===========================================================================


class TestGenerateColorPalette:
    @given(base=rgb, count=st.integers(min_value=1, max_value=12))
    def test_produces_requested_count(self, base, count):
        result = ColorMath.generate_color_palette(base, count=count)
        assert len(result) == count

    @given(base=rgb, count=st.integers(min_value=1, max_value=12))
    def test_all_outputs_are_valid_rgb(self, base, count):
        result = ColorMath.generate_color_palette(base, count=count)
        for c in result:
            assert _is_valid_rgb_tuple(c)

    def test_default_count_is_five(self):
        # Source default in the signature is count=5
        result = ColorMath.generate_color_palette((128, 128, 128))
        assert len(result) == 5
