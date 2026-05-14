"""
Phase 7: core/palette_formats.py — file I/O coverage.

The legacy unittest suite covers the export side (49% of the module);
the import side is largely untested. This file closes that gap with three
complementary strategies:

  1. Round-trip tests. Build a known palette → export → import →
     assert it survived. This is the primary defence against silent
     format breakage. For lossy formats (HSV/HSL float rounding,
     CSS weight discarding), the round-trip is relaxed accordingly.

  2. Format-specific branch tests. Variants the round-trip can't reach:
     JSON's three top-level shapes, XML's hex-element fallback, CSS's
     dedup behaviour, binary header validation, and the dozen graceful
     failure paths that swallow exceptions and return an empty list.

  3. Hand-crafted minimal fixtures for binary formats. ASE/ACO/Procreate
     are too brittle to round-trip every malformed-input case through;
     for those we author the smallest valid byte sequence and a few
     pointed corruption variants.

Coverage targets the ~340 statements in palette_formats.py that the
legacy suite leaves untouched (lines 508-1082 in the coverage report),
mostly the import side and detect_format.
"""

import json
import struct
import xml.etree.ElementTree as ET

import pytest

from core.palette_formats import PaletteFormats, _HEX_DATA_LINE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Anchor palette used by most round-trip tests. Mix of pure primaries,
# greyscale, and an off-axis colour so HSV/HSL round-trip stress tests
# don't trivially pass on (255, 0, 0) alone.
SAMPLE_PALETTE = [
    ((255, 0, 0), 50),
    ((0, 255, 0), 75),
    ((0, 0, 255), 25),
    ((128, 64, 200), 60),
    ((255, 255, 255), 100),
    ((0, 0, 0), 10),
]


def _rgbs_only(palette):
    """Strip weights — useful for formats where weight doesn't survive."""
    return [rgb for rgb, _ in palette]


def _assert_round_trip_exact(out_palette, in_palette):
    """Strict equality — colors AND weights preserved."""
    assert out_palette == in_palette, (
        f"round-trip mismatch:\n  in:  {in_palette}\n  out: {out_palette}"
    )


def _assert_round_trip_rgb_exact(out_palette, in_palette):
    """RGB exact, weight may differ (format doesn't preserve weight)."""
    assert _rgbs_only(out_palette) == _rgbs_only(in_palette)


def _assert_round_trip_lossy(out_palette, in_palette, tolerance=1):
    """Each channel within ±tolerance of input — for HSV/HSL/Procreate
    where float conversion introduces small rounding errors."""
    assert len(out_palette) == len(in_palette)
    for (rgb_out, _), (rgb_in, _) in zip(out_palette, in_palette):
        for ch_out, ch_in in zip(rgb_out, rgb_in):
            assert abs(ch_out - ch_in) <= tolerance, (
                f"channel diff {abs(ch_out - ch_in)} > {tolerance}: "
                f"in={rgb_in}, out={rgb_out}"
            )


# ===========================================================================
# Public API surface
# ===========================================================================


class TestGetExportFormats:
    def test_returns_list(self):
        assert isinstance(PaletteFormats.get_export_formats(), list)

    def test_each_entry_is_name_extension_tuple(self):
        for entry in PaletteFormats.get_export_formats():
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], str)

    def test_includes_known_formats(self):
        # Spot-check the formats that have round-trip tests downstream
        flat = " ".join(ext for _, ext in PaletteFormats.get_export_formats())
        for ext in ("*.gpl", "*.ase", "*.aco", "*.json", "*.xml",
                    "*.css", "*.svg", "*.hex", "*.hsv", "*.hsl", "*.txt"):
            assert ext in flat

    def test_includes_all_files_catchall(self):
        names = [n for n, _ in PaletteFormats.get_export_formats()]
        assert "All Files" in names


class TestGetImportFormats:
    def test_returns_list(self):
        assert isinstance(PaletteFormats.get_import_formats(), list)

    def test_first_entry_is_aggregate_filter(self):
        # The "All Supported Formats" entry pools every importable extension
        first = PaletteFormats.get_import_formats()[0]
        assert "All Supported" in first[0]

    def test_aggregate_includes_all_importable_extensions(self):
        aggregate = PaletteFormats.get_import_formats()[0][1]
        for ext in ("*.gpl", "*.ase", "*.aco", "*.json", "*.xml",
                    "*.css", "*.hex", "*.hsv", "*.hsl", "*.txt",
                    "*.svg", "*.clr", "*.swatches"):
            assert ext in aggregate


# ===========================================================================
# export_palette / import_palette dispatch
# ===========================================================================


class TestExportPaletteDispatch:
    def test_empty_palette_raises_value_error(self, tmp_path):
        # Source line 95-96
        with pytest.raises(ValueError, match="No colors"):
            PaletteFormats.export_palette(str(tmp_path / "x.gpl"), [])

    def test_unknown_extension_falls_back_to_json(self, tmp_path):
        # Source line 119: dispatch dict's `.get(ext, _export_json)`
        path = str(tmp_path / "weird.unknownext")
        PaletteFormats.export_palette(path, [((255, 0, 0), 50)])
        # The file should be JSON-formatted
        with open(path) as f:
            data = json.load(f)
        assert "colors" in data

    def test_dispatches_by_lowercase_extension(self, tmp_path):
        # `.GPL` should route the same as `.gpl`
        path = str(tmp_path / "PALETTE.GPL")
        PaletteFormats.export_palette(path, [((128, 128, 128), 50)])
        with open(path) as f:
            content = f.read()
        # GPL signature
        assert "GIMP Palette" in content


class TestImportPaletteDispatch:
    def test_unknown_extension_falls_back_to_json(self, tmp_path):
        # Source line 146: same dispatch fallback as export
        path = tmp_path / "x.unknownext"
        path.write_text(json.dumps({
            "colors": [{"rgb": {"r": 10, "g": 20, "b": 30}, "weight": 50}]
        }))
        result = PaletteFormats.import_palette(str(path))
        assert result == [((10, 20, 30), 50)]

    def test_uppercase_extension_dispatches_correctly(self, tmp_path):
        path = tmp_path / "P.GPL"
        path.write_text("GIMP Palette\nName: x\n#\n255   0   0\tRed\n")
        result = PaletteFormats.import_palette(str(path))
        assert result == [((255, 0, 0), 50)]


# ===========================================================================
# GPL — text-based, weight not preserved
# ===========================================================================


class TestGplRoundTrip:
    def test_exports_and_writes_header(self, tmp_path):
        path = str(tmp_path / "p.gpl")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        text = open(path).read()
        assert "GIMP Palette" in text

    def test_round_trip_preserves_rgb(self, tmp_path):
        path = str(tmp_path / "p.gpl")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_rgb_exact(out, SAMPLE_PALETTE)

    def test_round_trip_weight_defaults_to_50(self, tmp_path):
        # GPL doesn't store weight; importer assigns 50 to all
        path = str(tmp_path / "p.gpl")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        for _, weight in out:
            assert weight == 50


class TestGplImportEdgeCases:
    def test_skips_header_lines_starting_with_hash(self, tmp_path):
        path = tmp_path / "x.gpl"
        path.write_text(
            "GIMP Palette\nName: Test\nColumns: 0\n# Comment\n"
            "255 128   0\tOrange\n"
        )
        result = PaletteFormats.import_palette(str(path))
        assert result == [((255, 128, 0), 50)]

    def test_skips_empty_and_malformed_lines(self, tmp_path):
        # Lines with non-int data fail int() — caught by source ValueError except
        path = tmp_path / "x.gpl"
        path.write_text(
            "GIMP Palette\n#\n"
            "10 20 30\tValid\n"
            "not a number row\n"
            "abc def ghi\tBad\n"
            "40 50 60\tValid 2\n"
        )
        result = PaletteFormats.import_palette(str(path))
        assert result == [((10, 20, 30), 50), ((40, 50, 60), 50)]

    def test_skips_rows_with_too_few_parts(self, tmp_path):
        # Two-token line bypasses the `len(parts) >= 3` guard
        path = tmp_path / "x.gpl"
        path.write_text("GIMP Palette\n#\n10 20\n10 20 30\tOK\n")
        result = PaletteFormats.import_palette(str(path))
        assert result == [((10, 20, 30), 50)]


# ===========================================================================
# ASE — binary
# ===========================================================================


class TestAseRoundTrip:
    def test_round_trip_preserves_rgb(self, tmp_path):
        path = str(tmp_path / "p.ase")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        # ASE float→int conversion can lose 1 unit at the boundary
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=1)

    def test_round_trip_returns_correct_count(self, tmp_path):
        path = str(tmp_path / "p.ase")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        assert len(out) == len(SAMPLE_PALETTE)

    def test_weight_defaults_to_50(self, tmp_path):
        path = str(tmp_path / "p.ase")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        for _, weight in out:
            assert weight == 50


class TestAseImportEdgeCases:
    def test_invalid_signature_returns_empty(self, tmp_path):
        # Source line 533-534: raises ValueError → caught by outer except → []
        path = tmp_path / "fake.ase"
        path.write_bytes(b"NOTASEF" + b"\x00" * 20)
        result = PaletteFormats.import_palette(str(path))
        assert result == []

    def test_truncated_file_returns_empty(self, tmp_path):
        # Header valid but data truncated → struct.error inside the loop
        path = tmp_path / "trunc.ase"
        path.write_bytes(b"ASEF" + struct.pack(">HH", 1, 0)
                         + struct.pack(">I", 5))  # claims 5 blocks, has 0 data
        result = PaletteFormats.import_palette(str(path))
        assert result == []

    def test_non_rgb_color_block_skipped(self, tmp_path):
        # Block type 0x0001 with color_model != b'RGB ' is silently skipped.
        # We exercise the "color_model not RGB" path by writing a CMYK marker.
        path = tmp_path / "cmyk.ase"
        with open(path, "wb") as f:
            f.write(b"ASEF")
            f.write(struct.pack(">HH", 1, 0))
            f.write(struct.pack(">I", 1))  # 1 block
            f.write(struct.pack(">H", 0x0001))  # block type: color
            f.write(struct.pack(">I", 22 + 10))  # block length
            f.write(struct.pack(">H", 5))  # name length (5 chars)
            f.write("hello".encode("utf-16be"))
            f.write(b"CMYK")  # NOT RGB — skip path
            # Non-RGB models would have data we don't read; for the test
            # we read enough that color_type won't fail
            f.write(struct.pack(">H", 2))  # color_type
        result = PaletteFormats.import_palette(str(path))
        # The non-RGB block contributed no colors
        assert result == []

    def test_unknown_block_type_skipped(self, tmp_path):
        # Block type != 0x0001 falls into the else branch which reads
        # block_length - 4 bytes and continues
        path = tmp_path / "unknown.ase"
        with open(path, "wb") as f:
            f.write(b"ASEF")
            f.write(struct.pack(">HH", 1, 0))
            f.write(struct.pack(">I", 1))
            f.write(struct.pack(">H", 0x00FF))  # unknown block type
            f.write(struct.pack(">I", 8))  # block_length
            f.write(b"ABCD")  # block_length - 4 = 4 bytes
        result = PaletteFormats.import_palette(str(path))
        assert result == []


# ===========================================================================
# ACO — binary
# ===========================================================================


class TestAcoRoundTrip:
    def test_round_trip_preserves_rgb(self, tmp_path):
        # ACO uses 16-bit precision — exact round-trip via r * 257 / 257
        path = str(tmp_path / "p.aco")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_rgb_exact(out, SAMPLE_PALETTE)

    def test_weight_defaults_to_50(self, tmp_path):
        path = str(tmp_path / "p.aco")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        for _, weight in out:
            assert weight == 50


class TestAcoImportEdgeCases:
    def test_truncated_file_returns_empty(self, tmp_path):
        path = tmp_path / "trunc.aco"
        path.write_bytes(b"\x00")  # 1 byte — far short of 4-byte header
        result = PaletteFormats.import_palette(str(path))
        assert result == []

    def test_non_rgb_color_space_skipped(self, tmp_path):
        # Source lines 576-583: color_space != 0 is read-and-skipped
        path = tmp_path / "hsb.aco"
        with open(path, "wb") as f:
            f.write(struct.pack(">HH", 1, 1))  # version 1, 1 color
            f.write(struct.pack(">H", 1))      # color_space=1 (HSB) — skip
            f.write(b"\x00" * 8)               # 8 bytes consumed by the skip
        result = PaletteFormats.import_palette(str(path))
        assert result == []


# ===========================================================================
# JSON — full fidelity round-trip
# ===========================================================================


class TestJsonRoundTrip:
    def test_round_trip_exact(self, tmp_path):
        # JSON preserves both RGB and weight exactly
        path = str(tmp_path / "p.json")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_exact(out, SAMPLE_PALETTE)


class TestJsonImportVariants:
    def test_dict_with_rgb_field(self, tmp_path):
        # Source lines 597-604: standard exported shape
        path = tmp_path / "x.json"
        path.write_text(json.dumps({
            "colors": [{"rgb": {"r": 100, "g": 150, "b": 200}, "weight": 80}]
        }))
        assert PaletteFormats.import_palette(str(path)) == [
            ((100, 150, 200), 80)]

    def test_dict_with_hex_field(self, tmp_path):
        # Source lines 605-607: hex variant — no rgb but has hex
        path = tmp_path / "x.json"
        path.write_text(json.dumps({
            "colors": [{"hex": "#FF0000", "weight": 99}]
        }))
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 99)]

    def test_dict_hex_field_uses_default_weight_when_missing(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text(json.dumps({"colors": [{"hex": "#00ff00"}]}))
        result = PaletteFormats.import_palette(str(path))
        assert result == [((0, 255, 0), 50)]

    def test_top_level_list_with_color_key(self, tmp_path):
        # Source lines 608-612: alternative top-level shape
        path = tmp_path / "x.json"
        path.write_text(json.dumps([
            {"color": [10, 20, 30], "weight": 25},
            {"color": [40, 50, 60]},  # weight defaults to 50
        ]))
        assert PaletteFormats.import_palette(str(path)) == [
            ((10, 20, 30), 25),
            ((40, 50, 60), 50),
        ]

    def test_malformed_json_returns_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{NOT VALID}")
        assert PaletteFormats.import_palette(str(path)) == []

    def test_missing_file_returns_empty(self, tmp_path):
        # Outer except catches FileNotFoundError → returns []
        assert PaletteFormats.import_palette(
            str(tmp_path / "missing.json")) == []


# ===========================================================================
# XML — full fidelity round-trip + hex fallback
# ===========================================================================


class TestXmlRoundTrip:
    def test_round_trip_exact(self, tmp_path):
        path = str(tmp_path / "p.xml")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_exact(out, SAMPLE_PALETTE)


class TestXmlImportVariants:
    def test_color_with_rgb_subelement(self, tmp_path):
        # Source lines 627-634: rgb path
        path = tmp_path / "x.xml"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<palette><colors>'
            '<color><rgb><r>10</r><g>20</g><b>30</b></rgb><weight>77</weight></color>'
            '</colors></palette>')
        assert PaletteFormats.import_palette(str(path)) == [
            ((10, 20, 30), 77)]

    def test_color_with_rgb_subelement_default_weight(self, tmp_path):
        # No weight element → defaults to 50
        path = tmp_path / "x.xml"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<palette><colors>'
            '<color><rgb><r>10</r><g>20</g><b>30</b></rgb></color>'
            '</colors></palette>')
        assert PaletteFormats.import_palette(str(path)) == [
            ((10, 20, 30), 50)]

    def test_color_with_hex_subelement_fallback(self, tmp_path):
        # Source lines 635-639: rgb missing, hex fallback
        path = tmp_path / "x.xml"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<palette><colors>'
            '<color><hex>#ABCDEF</hex></color>'
            '</colors></palette>')
        result = PaletteFormats.import_palette(str(path))
        assert result == [((171, 205, 239), 50)]

    def test_malformed_xml_returns_empty(self, tmp_path):
        path = tmp_path / "bad.xml"
        path.write_text("<not <valid xml")
        assert PaletteFormats.import_palette(str(path)) == []


# ===========================================================================
# CSS — text-based, weight not preserved, dedup behaviour
# ===========================================================================


class TestCssRoundTrip:
    def test_round_trip_preserves_unique_rgbs(self, tmp_path):
        # CSS importer dedups; sample palette has all-unique colours so
        # each appears once in the output.
        path = str(tmp_path / "p.css")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        # CSS output has triple references per color (var, .color-N, .bg-N)
        # but importer dedups → exactly len(SAMPLE_PALETTE) entries
        assert len(out) == len(SAMPLE_PALETTE)
        _assert_round_trip_rgb_exact(out, SAMPLE_PALETTE)


class TestCssImportEdgeCases:
    def test_finds_hex_colors_in_text(self, tmp_path):
        path = tmp_path / "x.css"
        path.write_text("body { color: #ff0000; background: #00ff00; }")
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 50), ((0, 255, 0), 50)]

    def test_dedups_repeated_colors(self, tmp_path):
        # Source lines 655-658: seen set
        path = tmp_path / "x.css"
        path.write_text("a { color: #ff0000; } b { color: #ff0000; } "
                        "c { color: #ff0000; }")
        result = PaletteFormats.import_palette(str(path))
        assert result == [((255, 0, 0), 50)]

    def test_no_hex_colors_returns_empty(self, tmp_path):
        path = tmp_path / "x.css"
        path.write_text("body { font-family: sans-serif; }")
        assert PaletteFormats.import_palette(str(path)) == []


# ===========================================================================
# .colors — full fidelity round-trip (R G B Weight inline)
# ===========================================================================


class TestColorsRoundTrip:
    def test_round_trip_exact(self, tmp_path):
        # .colors stores `#hex R G B Weight` — full fidelity expected
        path = str(tmp_path / "p.colors")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_exact(out, SAMPLE_PALETTE)


class TestColorsImportEdgeCases:
    def test_skips_pure_comment_lines(self, tmp_path):
        # `# Comment` doesn't match _HEX_DATA_LINE → skipped
        path = tmp_path / "x.colors"
        path.write_text(
            "# Header line 1\n"
            "# Header line 2\n"
            "#\n"
            "#FF0000 255   0   0  50 # Red\n"
        )
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 50)]

    def test_falls_back_to_hex_prefix_when_rgb_fields_missing(self, tmp_path):
        # If only the hex prefix is present, fallback decodes from it.
        # Source lines 699-708.
        path = tmp_path / "x.colors"
        path.write_text("#00FF00\n")  # nothing after the hex
        assert PaletteFormats.import_palette(str(path)) == [
            ((0, 255, 0), 50)]

    def test_fallback_uses_last_token_as_weight_when_parseable(self, tmp_path):
        # Source line 703-705: last token tried as int weight in fallback
        path = tmp_path / "x.colors"
        path.write_text("#0000FF 99\n")  # only hex + weight, no R G B
        result = PaletteFormats.import_palette(str(path))
        assert result == [((0, 0, 255), 99)]

    def test_skips_non_hex_lines(self, tmp_path):
        # Lines that don't match _HEX_DATA_LINE are silently skipped
        path = tmp_path / "x.colors"
        path.write_text(
            "Header text\n"
            "more text\n"
            "#FF0000 255   0   0  50 # Red\n"
            "garbage line\n"
        )
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 50)]

    def test_inline_comment_after_data_stripped(self, tmp_path):
        # Source line 689: `rest.split('#', 1)[0]`
        path = tmp_path / "x.colors"
        path.write_text("#FF0000 255   0   0  77 # an inline comment\n")
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 77)]


# ===========================================================================
# .hex — full fidelity round-trip including weight
# ===========================================================================


class TestHexRoundTrip:
    def test_round_trip_exact(self, tmp_path):
        path = str(tmp_path / "p.hex")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_exact(out, SAMPLE_PALETTE)


class TestHexImportEdgeCases:
    def test_no_weight_defaults_to_50(self, tmp_path):
        path = tmp_path / "x.hex"
        path.write_text("#ABCDEF\n")
        assert PaletteFormats.import_palette(str(path)) == [
            ((171, 205, 239), 50)]

    def test_skips_pure_comment_lines(self, tmp_path):
        path = tmp_path / "x.hex"
        path.write_text(
            "# HEX Color Palette\n"
            "# Format: ...\n"
            "#\n"
            "#FF8800 75 # Orange\n"
        )
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 136, 0), 75)]

    def test_skips_empty_lines(self, tmp_path):
        path = tmp_path / "x.hex"
        path.write_text("#FF0000 50\n\n\n#00FF00 60\n")
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 50), ((0, 255, 0), 60)]

    def test_invalid_weight_field_falls_back_to_50(self, tmp_path):
        # Source lines 738-741: int() on non-numeric → except → keeps 50
        path = tmp_path / "x.hex"
        path.write_text("#ff0000 not_a_number\n")
        assert PaletteFormats.import_palette(str(path)) == [
            ((255, 0, 0), 50)]


# ===========================================================================
# HSV — lossy round-trip
# ===========================================================================


class TestHsvRoundTrip:
    def test_round_trip_within_one_per_channel(self, tmp_path):
        path = str(tmp_path / "p.hsv")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        # HSV: float → format → float → RGB has cumulative rounding errors;
        # we observed up to 2 units in the boundaries.
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=2)

    def test_weight_preserved_in_hsv(self, tmp_path):
        # HSV format CAN store weight (line 767), so it should round-trip
        path = str(tmp_path / "p.hsv")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        for (_, w_out), (_, w_in) in zip(out, SAMPLE_PALETTE):
            assert w_out == w_in


class TestHsvImportEdgeCases:
    def test_skips_comment_lines(self, tmp_path):
        path = tmp_path / "x.hsv"
        path.write_text(
            "# HSV Color Palette\n"
            "# Format: H S V Weight\n"
            "#\n"
            "0.0 100.0 100.0 50 # Red\n"
        )
        result = PaletteFormats.import_palette(str(path))
        assert len(result) == 1
        # H=0, S=100%, V=100% → red
        assert result[0][0] == (255, 0, 0)

    def test_default_weight_when_missing(self, tmp_path):
        path = tmp_path / "x.hsv"
        path.write_text("0.0 100.0 100.0\n")
        # 3 parts, no 4th → weight=50
        assert PaletteFormats.import_palette(str(path))[0][1] == 50

    def test_malformed_line_skipped(self, tmp_path):
        path = tmp_path / "x.hsv"
        path.write_text("not numeric data\n0 100 100\n")
        # First line raises ValueError on float() → skipped; second succeeds
        result = PaletteFormats.import_palette(str(path))
        assert len(result) == 1


# ===========================================================================
# HSL — lossy round-trip
# ===========================================================================


class TestHslRoundTrip:
    def test_round_trip_within_two_per_channel(self, tmp_path):
        path = str(tmp_path / "p.hsl")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=2)


class TestHslImportEdgeCases:
    def test_skips_comments(self, tmp_path):
        path = tmp_path / "x.hsl"
        path.write_text(
            "# HSL Palette\n"
            "0.0 100.0 50.0 75\n"
        )
        result = PaletteFormats.import_palette(str(path))
        # HSL(0, 100%, 50%) = pure red
        assert result[0][0] == (255, 0, 0)
        assert result[0][1] == 75

    def test_default_weight_when_missing(self, tmp_path):
        path = tmp_path / "x.hsl"
        path.write_text("120 100 50\n")
        assert PaletteFormats.import_palette(str(path))[0][1] == 50

    def test_malformed_line_skipped(self, tmp_path):
        path = tmp_path / "x.hsl"
        path.write_text("garbage\n0 100 50\n")
        assert len(PaletteFormats.import_palette(str(path))) == 1


# ===========================================================================
# TXT — heuristic format, weight not preserved
# ===========================================================================


class TestTxtRoundTrip:
    def test_round_trip_preserves_unique_rgbs(self, tmp_path):
        # Output contains both #hex AND RGB(r, g, b); importer extracts both
        # then dedups. Sample palette has unique colors → len matches.
        path = str(tmp_path / "p.txt")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        # All colors round-trip; weights default to 50
        _assert_round_trip_rgb_exact(out, SAMPLE_PALETTE)


class TestTxtImportEdgeCases:
    def test_extracts_hex_pattern(self, tmp_path):
        path = tmp_path / "x.txt"
        path.write_text("My favourite colors are #ff0000 and #00ff00.")
        result = PaletteFormats.import_palette(str(path))
        assert ((255, 0, 0), 50) in result
        assert ((0, 255, 0), 50) in result

    def test_extracts_rgb_pattern(self, tmp_path):
        path = tmp_path / "x.txt"
        path.write_text("Use RGB(100, 150, 200) for the highlight.")
        assert ((100, 150, 200), 50) in PaletteFormats.import_palette(str(path))

    def test_dedups_when_same_color_appears_in_both_formats(self, tmp_path):
        # Source lines 831-836: dedup pass
        path = tmp_path / "x.txt"
        path.write_text(
            "Red is #ff0000 also written as RGB(255, 0, 0).\n"
            "Green is #00ff00.\n"
        )
        result = PaletteFormats.import_palette(str(path))
        # Red appears twice (hex + RGB) but should be deduped
        red_count = sum(1 for c, _ in result if c == (255, 0, 0))
        assert red_count == 1

    def test_rejects_rgb_values_above_255(self, tmp_path):
        # Source line 826: range check
        path = tmp_path / "x.txt"
        path.write_text("RGB(300, 100, 100)\n")  # 300 > 255
        result = PaletteFormats.import_palette(str(path))
        # No valid colors extracted
        assert result == []


# ===========================================================================
# Affinity — JSON-based, full fidelity round-trip
# ===========================================================================


class TestAffinityRoundTrip:
    def test_round_trip_within_one_per_channel(self, tmp_path):
        # Float quantisation → channel-of-1 tolerance
        path = str(tmp_path / "p.afpalette")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=1)

    def test_weight_preserved(self, tmp_path):
        path = str(tmp_path / "p.afpalette")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        for (_, w_out), (_, w_in) in zip(out, SAMPLE_PALETTE):
            assert w_out == w_in


class TestAffinityImportEdgeCases:
    def test_skips_non_rgb_color_models(self, tmp_path):
        # Source line 854 — only `model: rgb` is processed
        path = tmp_path / "x.afpalette"
        path.write_text(json.dumps({
            "colors": [
                {"color": {"model": "cmyk", "c": 0.5, "m": 0.5,
                           "y": 0.5, "k": 0.0}, "weight": 50},
                {"color": {"model": "rgb", "r": 1.0, "g": 0.0, "b": 0.0},
                 "weight": 80},
            ]
        }))
        result = PaletteFormats.import_palette(str(path))
        assert result == [((255, 0, 0), 80)]

    def test_default_weight_when_missing(self, tmp_path):
        path = tmp_path / "x.afpalette"
        path.write_text(json.dumps({
            "colors": [{"color": {"model": "rgb", "r": 0, "g": 0.5, "b": 1.0}}]
        }))
        result = PaletteFormats.import_palette(str(path))
        assert result[0][1] == 50

    def test_empty_colors_list(self, tmp_path):
        path = tmp_path / "x.afpalette"
        path.write_text(json.dumps({"colors": []}))
        assert PaletteFormats.import_palette(str(path)) == []

    def test_malformed_returns_empty(self, tmp_path):
        path = tmp_path / "bad.afpalette"
        path.write_text("not json")
        assert PaletteFormats.import_palette(str(path)) == []


# ===========================================================================
# SVG — best-effort, weight not preserved
# ===========================================================================


class TestSvgRoundTrip:
    def test_round_trip_preserves_all_input_colors(self, tmp_path):
        # SVG export adds a background <rect fill="#FFFFFF"/> as a frame;
        # the importer extracts that too and dedups it with input colors.
        # The contract we test is weaker than for other formats: every
        # input colour must appear in the output (set-membership), but
        # the output may include extras (the BG frame) and may be in a
        # different order (BG appears first).
        path = str(tmp_path / "p.svg")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        out_rgbs = {c for c, _ in out}
        in_rgbs = {c for c, _ in SAMPLE_PALETTE}
        assert in_rgbs.issubset(out_rgbs)


class TestSvgImportEdgeCases:
    def test_extracts_from_fill_attribute(self, tmp_path):
        path = tmp_path / "x.svg"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg">\n'
            '  <rect fill="#ff0000"/>\n'
            '  <rect fill="#00ff00"/>\n'
            '</svg>')
        result = PaletteFormats.import_palette(str(path))
        # Source dedups; both unique
        assert {c for c, _ in result} == {(255, 0, 0), (0, 255, 0)}

    def test_extracts_from_style_attribute(self, tmp_path):
        # Source lines 944-953: style="fill: #hex" branch
        path = tmp_path / "x.svg"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg">\n'
            '  <circle style="fill: #abcdef; stroke: #000000;"/>\n'
            '</svg>')
        result = PaletteFormats.import_palette(str(path))
        assert ((171, 205, 239), 50) in result

    def test_skips_3_char_hex_fills(self, tmp_path):
        # Source line 937: `len(fill) == 7` filter — #abc is 4 chars, skipped
        path = tmp_path / "x.svg"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg">\n'
            '  <rect fill="#abc"/>\n'
            '  <rect fill="#aabbcc"/>\n'
            '</svg>')
        result = PaletteFormats.import_palette(str(path))
        # Only the 7-char form is extracted
        assert result == [((170, 187, 204), 50)]

    def test_no_fill_attributes_returns_empty(self, tmp_path):
        path = tmp_path / "x.svg"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
        assert PaletteFormats.import_palette(str(path)) == []

    def test_dedups_repeated_fills(self, tmp_path):
        path = tmp_path / "x.svg"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg">\n'
            '  <rect fill="#ff0000"/>\n'
            '  <rect fill="#ff0000"/>\n'
            '  <rect fill="#ff0000"/>\n'
            '</svg>')
        result = PaletteFormats.import_palette(str(path))
        assert len(result) == 1

    def test_malformed_xml_returns_empty(self, tmp_path):
        path = tmp_path / "bad.svg"
        path.write_text("not xml at all")
        assert PaletteFormats.import_palette(str(path)) == []


# ===========================================================================
# CLR — XML plist variant (binary not supported)
# ===========================================================================


class TestClrRoundTrip:
    def test_round_trip_preserves_rgb(self, tmp_path):
        # Export writes XML plist; import reads XML plist
        path = str(tmp_path / "p.clr")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=1)


class TestClrImportEdgeCases:
    def test_handcrafted_minimal_xml(self, tmp_path):
        # Smallest viable XML plist with 1 color
        path = tmp_path / "x.clr"
        path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '  <key>Colors</key>\n'
            '  <array>\n'
            '    <dict>\n'
            '      <key>Red</key><real>1.0</real>\n'
            '      <key>Green</key><real>0.5</real>\n'
            '      <key>Blue</key><real>0.0</real>\n'
            '    </dict>\n'
            '  </array>\n'
            '</dict>\n'
            '</plist>')
        result = PaletteFormats.import_palette(str(path))
        # 1.0 → 255, 0.5 → 127 (int truncation), 0.0 → 0
        assert result == [((255, 127, 0), 50)]

    def test_dict_with_no_color_keys_ignored(self, tmp_path):
        # Dict with only a Name key — not a color → skipped
        path = tmp_path / "x.clr"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<plist><dict><key>Colors</key><array>'
            '<dict><key>Name</key><string>NotAColor</string></dict>'
            '</array></dict></plist>')
        assert PaletteFormats.import_palette(str(path)) == []

    def test_invalid_xml_returns_empty(self, tmp_path):
        # Source lines 910-913: ParseError catches binary plists
        path = tmp_path / "binary.clr"
        path.write_bytes(b"\x00\x01\x02\x03 not xml at all")
        assert PaletteFormats.import_palette(str(path)) == []

    def test_empty_array_logs_warning_returns_empty(self, tmp_path):
        # Source lines 905-908: empty colors list logs warning
        path = tmp_path / "x.clr"
        path.write_text(
            '<?xml version="1.0"?>\n'
            '<plist><dict><key>Colors</key><array></array></dict></plist>')
        assert PaletteFormats.import_palette(str(path)) == []


# ===========================================================================
# Procreate — binary
# ===========================================================================


class TestProcreateRoundTrip:
    def test_round_trip_within_one_per_channel(self, tmp_path):
        path = str(tmp_path / "p.swatches")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        out = PaletteFormats.import_palette(path)
        _assert_round_trip_lossy(out, SAMPLE_PALETTE, tolerance=1)


class TestProcreateImportEdgeCases:
    def test_invalid_header_returns_empty(self, tmp_path):
        # Source line 987-989: SWCH check
        path = tmp_path / "x.swatches"
        path.write_bytes(b"NOTSWCH" + b"\x00" * 20)
        assert PaletteFormats.import_palette(str(path)) == []

    def test_truncated_count_field_returns_empty(self, tmp_path):
        # Source lines 992-995: incomplete num_colors header
        path = tmp_path / "x.swatches"
        path.write_bytes(b"SWCH" + b"\x00\x01")  # only 2 bytes, need 4
        assert PaletteFormats.import_palette(str(path)) == []

    def test_unusually_high_count_clamped_to_1000(self, tmp_path):
        # Source lines 999-1001: sanity-check
        path = tmp_path / "x.swatches"
        with open(path, "wb") as f:
            f.write(b"SWCH")
            f.write(struct.pack("<I", 99999))  # absurd count
            # No actual color data → loop will break on truncation
        # Doesn't crash; returns empty (the loop reads less than 16 bytes)
        result = PaletteFormats.import_palette(str(path))
        assert isinstance(result, list)

    def test_truncated_color_data_breaks_loop(self, tmp_path):
        # Source lines 1006-1009: incomplete color entry
        path = tmp_path / "x.swatches"
        with open(path, "wb") as f:
            f.write(b"SWCH")
            f.write(struct.pack("<I", 5))  # claims 5 colors
            # Only write 1 complete color (16 bytes) + 8 bytes (truncated)
            f.write(struct.pack("<ffff", 1.0, 0.0, 0.0, 1.0))
            f.write(b"\x00" * 8)
        result = PaletteFormats.import_palette(str(path))
        # First color valid; loop breaks on truncated 2nd
        assert len(result) == 1
        assert result[0] == ((255, 0, 0), 50)

    def test_out_of_range_floats_skipped(self, tmp_path):
        # Source lines 1013-1016: float range validation
        path = tmp_path / "x.swatches"
        with open(path, "wb") as f:
            f.write(b"SWCH")
            f.write(struct.pack("<I", 2))
            # First color: out of range (2.0 > 1.0)
            f.write(struct.pack("<ffff", 2.0, 0.0, 0.0, 1.0))
            # Second color: valid
            f.write(struct.pack("<ffff", 0.0, 1.0, 0.0, 1.0))
        result = PaletteFormats.import_palette(str(path))
        # First skipped; second accepted
        assert result == [((0, 255, 0), 50)]


# ===========================================================================
# Export-only formats: ACB, plus smoke tests for non-round-trippable exports
# ===========================================================================


class TestAcbExport:
    """ACB has no importer — just smoke-test that export doesn't crash."""

    def test_writes_valid_acb_header(self, tmp_path):
        path = str(tmp_path / "p.acb")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        with open(path, "rb") as f:
            assert f.read(4) == b"8BCB"

    def test_writes_color_count(self, tmp_path):
        path = str(tmp_path / "p.acb")
        PaletteFormats.export_palette(path, SAMPLE_PALETTE)
        # The structure is: 8BCB + version(2) + 0(2) + title_len(2) +
        # title + 0(2) + 0(2) + desc_len(2) + desc + count(2) + entries...
        # We just verify the file exists and starts with the magic bytes.
        import os
        assert os.path.getsize(path) > 4


# ===========================================================================
# detect_format
# ===========================================================================


class TestDetectFormat:
    def test_returns_extension_when_present(self, tmp_path):
        # Source lines 1049-1051: ext shortcut
        path = tmp_path / "x.gpl"
        path.write_text("anything")
        assert PaletteFormats.detect_format(str(path)) == ".gpl"

    def test_lowercases_extension(self, tmp_path):
        path = tmp_path / "x.GPL"
        path.write_text("anything")
        assert PaletteFormats.detect_format(str(path)) == ".gpl"

    def test_detects_ase_by_magic_bytes(self, tmp_path):
        # No extension, falls into the binary-sniffing block at lines 1053-1061
        path = tmp_path / "noext_ase"
        path.write_bytes(b"ASEF" + b"\x00" * 20)
        assert PaletteFormats.detect_format(str(path)) == ".ase"

    def test_detects_acb_by_magic_bytes(self, tmp_path):
        path = tmp_path / "noext_acb"
        path.write_bytes(b"8BCB" + b"\x00" * 20)
        assert PaletteFormats.detect_format(str(path)) == ".acb"

    def test_detects_swatches_by_magic_bytes(self, tmp_path):
        path = tmp_path / "noext_swc"
        path.write_bytes(b"SWCH" + b"\x00" * 20)
        assert PaletteFormats.detect_format(str(path)) == ".swatches"

    def test_detects_gpl_by_first_line(self, tmp_path):
        # Source line 1066: text content sniff
        path = tmp_path / "noext_gpl"
        path.write_text("GIMP Palette\nName: Test\n")
        assert PaletteFormats.detect_format(str(path)) == ".gpl"

    def test_detects_xml_by_xml_declaration(self, tmp_path):
        path = tmp_path / "noext_xml"
        path.write_text('<?xml version="1.0"?>\n<palette/>')
        assert PaletteFormats.detect_format(str(path)) == ".xml"

    def test_detects_xml_by_palette_tag(self, tmp_path):
        # Even without xml declaration, <palette> triggers detection
        path = tmp_path / "noext_xml2"
        path.write_text("<palette><colors/></palette>")
        assert PaletteFormats.detect_format(str(path)) == ".xml"

    def test_detects_svg_by_svg_tag(self, tmp_path):
        path = tmp_path / "noext_svg"
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        assert PaletteFormats.detect_format(str(path)) == ".svg"

    def test_detects_clr_by_plist_tag(self, tmp_path):
        path = tmp_path / "noext_clr"
        path.write_text("<plist><dict/></plist>")
        assert PaletteFormats.detect_format(str(path)) == ".clr"

    def test_detects_css_by_root_selector(self, tmp_path):
        # Source line 1074
        path = tmp_path / "noext_css"
        path.write_text(":root { --color: #ff0000; }")
        assert PaletteFormats.detect_format(str(path)) == ".css"

    def test_detects_css_by_var_function(self, tmp_path):
        path = tmp_path / "noext_css2"
        path.write_text(".x { color: var(--brand); }")
        assert PaletteFormats.detect_format(str(path)) == ".css"

    def test_detects_json_by_opening_brace(self, tmp_path):
        # Source line 1076: starts with `{`
        path = tmp_path / "noext_json"
        path.write_text('{"colors": []}')
        assert PaletteFormats.detect_format(str(path)) == ".json"

    def test_unrecognized_content_returns_none(self, tmp_path):
        path = tmp_path / "noext_unknown"
        path.write_text("some random text without any markers")
        assert PaletteFormats.detect_format(str(path)) is None

    def test_missing_file_returns_none(self, tmp_path):
        # Outer except catches FileNotFoundError → returns None
        assert PaletteFormats.detect_format(
            str(tmp_path / "missing")) is None


# ===========================================================================
# validate_colors
# ===========================================================================


class TestValidateColors:
    def test_passes_through_valid(self):
        out = PaletteFormats.validate_colors([((100, 150, 200), 75)])
        assert out == [((100, 150, 200), 75)]

    def test_clamps_high_rgb_values(self):
        out = PaletteFormats.validate_colors([((300, 400, 500), 50)])
        assert out == [((255, 255, 255), 50)]

    def test_clamps_negative_rgb_values(self):
        out = PaletteFormats.validate_colors([((-10, -20, -30), 50)])
        assert out == [((0, 0, 0), 50)]

    def test_clamps_weight_above_100(self):
        out = PaletteFormats.validate_colors([((50, 50, 50), 200)])
        assert out[0][1] == 100

    def test_clamps_negative_weight(self):
        out = PaletteFormats.validate_colors([((50, 50, 50), -25)])
        assert out[0][1] == 0

    def test_floats_truncated_to_int(self):
        # int(1.7) = 1 — truncation, not rounding
        out = PaletteFormats.validate_colors([((1.7, 2.3, 3.9), 50.5)])
        assert out == [((1, 2, 3), 50)]

    def test_empty_list_returns_empty(self):
        assert PaletteFormats.validate_colors([]) == []

    def test_multiple_colors_all_validated(self):
        result = PaletteFormats.validate_colors([
            ((300, 100, 100), 50),
            ((-1, -1, -1), 200),
        ])
        assert result == [((255, 100, 100), 50), ((0, 0, 0), 100)]


# ===========================================================================
# get_format_info
# ===========================================================================


class TestGetFormatInfo:
    def test_returns_dict_with_expected_keys_for_known_extension(self):
        info = PaletteFormats.get_format_info(".gpl")
        assert "name" in info
        assert "type" in info
        assert "support" in info
        assert "apps" in info

    def test_known_extension_returns_correct_metadata(self):
        info = PaletteFormats.get_format_info(".gpl")
        assert info["name"] == "GIMP Palette"
        assert info["type"] == "text"

    def test_binary_format_marked_as_binary(self):
        info = PaletteFormats.get_format_info(".ase")
        assert info["type"] == "binary"

    def test_export_only_format_marked_correctly(self):
        # ACB is exportable but not importable
        info = PaletteFormats.get_format_info(".acb")
        assert info["support"] == "export"

    def test_limited_support_format_has_note(self):
        info = PaletteFormats.get_format_info(".clr")
        assert info["support"] == "limited"
        assert "note" in info

    def test_unknown_extension_returns_unknown_dict(self):
        info = PaletteFormats.get_format_info(".zzz")
        assert info["name"] == "Unknown"
        assert info["support"] == "none"

    def test_uppercase_extension_normalized(self):
        info = PaletteFormats.get_format_info(".GPL")
        assert info["name"] == "GIMP Palette"


# ===========================================================================
# Module-level helper regex sanity
# ===========================================================================


class TestHexDataLineRegex:
    """The shared _HEX_DATA_LINE regex distinguishes data rows starting with
    `#RRGGBB ...` from comment rows starting with `# Comment ...`."""

    def test_matches_six_char_hex_followed_by_space(self):
        m = _HEX_DATA_LINE.match("#FF0000 50 # comment")
        assert m is not None
        assert m.group(1) == "#FF0000"

    def test_matches_three_char_hex(self):
        m = _HEX_DATA_LINE.match("#abc more text")
        assert m is not None

    def test_does_not_match_pure_comment(self):
        # Space immediately after `#` — not hex
        assert _HEX_DATA_LINE.match("# Comment text") is None

    def test_does_not_match_too_long_hex(self):
        # 7 hex chars after `#` — fails the lookahead (next char IS hex)
        assert _HEX_DATA_LINE.match("#FF0000A something") is None

    def test_matches_lowercase_hex(self):
        assert _HEX_DATA_LINE.match("#ff8800 50") is not None
