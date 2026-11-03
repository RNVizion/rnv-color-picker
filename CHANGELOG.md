# Changelog

All notable changes to RNV Color Picker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

Changes since the May 2026 patches: June to October 2026.

### Added
- **Drag and drop.** Dropping a PNG, JPG or JPEG file on the window or the image view loads it as Upload Image (`Ctrl+O`) does. Anything else (another file type, a file that is not really an image, several files, text) is refused with a message.
- **SCSS export and import** (`.scss`), beside CSS: `$color-1: #rrggbb;` and `$color-1-rgb: r, g, b;`, named as the CSS export names its variables. That makes 17 export formats and 16 import formats.
- **Palette import is reachable**: `Ctrl+I`, or right-click an empty part of the palette and choose Import Palette.
- **The restore offer.** After a run that did not close properly, the next launch offers to restore the colors it auto-saved. A normal close is never followed by the offer, and the auto-save is kept whatever the answer.
- **Setup scripts**: `in.sh` (Linux and Codespaces, with the Qt system libraries) and `in.ps1` (Windows) install `requirements.txt` and `tests/requirements-dev.txt`.
- **Color sync**: `brand_map.json` says where each color comes from; `tools/sync_colors.py` writes the values in `utils/colors.py` and the chart `COLORS.md`; the daily `brand-sync` workflow opens a pull request when a brand color this app uses moves.
- **`ACCENT_IMAGES.md`**, written by `tools/accent_images.py`: every image with the gold drawn into its pixels.
- **Guard tests**: colors in sync with the brand, the brand pin, atomic state writes, status carried by a word, the accent-image list, the setup scripts, the test-count floors in the docs, and an installed copy carrying `resources/`; also the Python floor, dependency coherence, the image budget and the shared test-tool ranges.
- `tests/test_picker_features.py` drives the main window through the features and settings above.

### Changed
- **Five grays are the brand's.** rnv-brand rev 49 (`63a0235`, now the pin in `tests/requirements-dev.txt`) names five steps of its ink grid, `GRAY.gray-4`, `gray-5`, `gray-6`, `gray-8` and `gray-12`, and `brand_map.json` takes the app's 5 colors at those values from them instead of owning them. No value moved; `COLORS.md` lists them under the brand. The tests read the register as `rnv_brand.brand`, the name it installs under.
- **The README's badges take the brand's colors**: each static badge has a dark label and a gold message. The CI status badges keep shields.io's colors, which change with the run, and say passing or failing in words.
- **The brand register is read as `rnv_brand.brand`.** rnv-brand 48.1.0 (`108213b`) installs it under that name, which no other package's `engine` can hide. `tools/sync_colors.py` imports it so, the daily brand-sync checks that name, and `tests/requirements-dev.txt` pins `108213b`. No color moved.
- **The interface fonts are the brand's.** Inter, for interface text, and JetBrains Mono, for fixed-width text, replace Arial, Segoe UI, Consolas and Courier wherever the app used them; the mark stays Montserrat Black. `python tools/sync_fonts.py` makes them from rnv-brand's files at the pin, one TrueType file per weight (Qt on Windows loads no woff2), into `resources/fonts/`, with `fonts.json`, and `utils/brand_fonts.py` registers them at startup, by file. `tests/test_fonts_in_sync.py` holds the copy to the pin. Exported files (SVG, HTML) keep the fonts they name.
- **Each font's license travels with it.** `resources/fonts/` holds `OFL-Montserrat.txt`, `OFL-Inter.txt` and `OFL-JetBrains-Mono.txt`; Montserrat Black had been committed and bundled without its license. `tests/test_font_license.py` holds it, and the README's License section says so.
- **Gestures in the image view**: Shift+drag selects a region and extracts its colors, as the README said; a plain drag now pans the image instead of selecting. Double-click still picks one color, and the wheel still zooms.
- **Maximum Colors** (Settings, 1 to 1000) now sets the palette limit, at launch too; it was 333 whatever the setting said. Lowering it below the palette's size keeps every color and says so.
- **Auto-load last session on startup** now loads, at launch, the session saved, auto-saved or loaded most recently.
- **Default Export Format** now sets the format Export Palette opens on (GPL, ASE, JSON, CSS), or Save As Image (PNG, JPEG).
- **Remember window size** and **Remember window position** now keep the window's size and place from one close to the next launch, in the settings file; a place no longer on any screen is not used.
- **Python 3.13** is the floor, declared and run.
- **Colors**: the theme colors follow rnv-brand, pinned at a commit in `tests/requirements-dev.txt`; light-mode text and the contrast-rating colors were reworked to clear WCAG contrast; hovers take the mode's gold; colors written at an alpha are derived from their base color.
- **Files the app keeps** (settings, sessions, the recent list, history) are written atomically through `utils/atomic_write.py`.
- **A status is never shown by color alone**, and a guard now holds it; in this app the WCAG results read PASS or FAIL beside their color.
- The background, settings-gear and icon images were re-encoded much smaller, with the same pictures.
- The dev requirements moved from `requirements-test.txt` to `tests/requirements-dev.txt`, with rnv-brand pinned and the test tools in ranges shared by the RNV apps.
- `run_tests.py` runs coverage with its own Python (`python -m coverage`), not a `coverage` found first on PATH.
- Help text in the app: the About dialog and the Settings shortcut list name `Ctrl+I`, `Ctrl+0`, the drop and the right-click menus, the gestures as they are, and `Ctrl+S` as saving the palette sheet; the History tab says double-click.
- The documentation was corrected against the code: README, TESTING and this file.

### Fixed
- `pip install .` now installs `resources/` (fonts, icons, button images, background, screenshots); the wheel had none of them.
- Settings: Apply now reaches the Preserve Colors checkbox; Save Settings applies the settings as Apply does; the Settings panel and the About dialog follow a theme switch made while they are open; the Sessions tab's divider is drawn in the theme's color.
- Two runs started within the same second no longer share one auto-save file.
- The 3.0.3 entry below describes an ASE `metadata` parameter fix that never was: no such parameter existed. The fixes of that day (2026-05-19, with the line endings on 2026-05-20, not 2026-05-21) were: ASE color names gained their UTF-16 terminator and each color block its correct length (20 bytes plus the name, not 22); ACO export writes the name length as 4 bytes; ACO import rounds 16-bit channels instead of truncating them.

### Planned
- Mutation testing harness (`mutmut`) against `core/` modules.
- Snapshot test suite (mirroring Color Mixer) for byte-level export verification.

---

## [3.0.3] — 2026-01

### 2026-05-21 — Post-release patches (no version bump)

#### Fixed

- **Cross-platform line-ending consistency in palette text-format exports.**
  All text-format palette export methods now produce byte-identical output
  across Windows, macOS, and Linux. Previously, Python's text-mode `open()`
  substituted `\r\n` for `\n` on Windows only, creating inconsistent
  palette files when users shared exports across platforms. The files
  still parsed correctly and round-tripped through text editors, but
  byte-level comparison (signed manifests, content hashes, snapshot tests
  in downstream consumers) would diverge.

  Fix applied across three patterns: simple text writes (added
  `newline='\n'` to `open(...)`), JSON writes (same fix), and
  ElementTree XML / CLR exports (switched to binary mode with explicit
  file objects so the writer controls byte content directly).

- **ASE (Adobe Swatch Exchange) export signature mismatch** that caused
  a `TypeError` whenever a user attempted to export to `.ase` format.
  The exporter was missing the `metadata` parameter that the
  `export_palette` dispatcher passes to every format method. Bug existed
  since the metadata-propagation refactor and was caught during the
  cross-project audit.

#### Added

- **GitHub Actions CI** running the full test suite on Ubuntu and Windows
  on every push and PR. Live status badges in the README. Achieves the
  cross-platform verification that was previously self-reported.
- **Engineering Notes section in README** documenting the cross-project
  bug discovery methodology and the specific shape of bugs it surfaces
  (silent in functional tests, visible only at byte level).

#### Engineering notes

The line-ending bug was discovered while debugging snapshot test failures
in [RNV Color Mixer](https://github.com/RNVizion/rnv-color-mixer), where
byte-level comparison surfaced the platform-dependent output. RNV Color
Picker had no snapshot tests at the time, so the same latent bug existed
here undetected — palette files shared between Windows and Linux users
would have inconsistent byte content. A cross-project audit applied the
same systematic fix to all three repositories in the RNVizion suite.

The Color Mixer investment in snapshot testing paid for itself directly:
a class of bug that was invisible in functional tests (the files still
"worked" — they parsed back into the same palette) became immediately
visible at the byte level. The Color Picker fix is verified by code
review against the audit pattern; adding equivalent snapshot tests here
is tracked above under [Unreleased] → Planned.

---

### 2026-01 — Initial release

This release closes out a multi-phase test-coverage and code-hygiene campaign. Three latent production bugs were caught by the new test suite and fixed. Cross-project copy-paste residue was cleaned up. Application metadata is now sourced from a single file.

#### Fixed
- **HSL palette importer tuple-order bug.** Importing an `.hsl` palette containing pure red (`H=0.0, S=100.0, L=50.0`) yielded white instead of red. Root cause: `palette_formats.py` passed `(h, s, l)` to `ColorMath.hsl_to_rgb` but the underlying `colorsys.hls_to_rgb` expects `(h, l, s)`. Fixed at `palette_formats.py` line 793.
- **Image viewer drag from origin.** Drag-to-select region extraction silently failed when the user's drag began at scene origin `(0, 0)`. Root cause: `if self.selection_start:` is falsy for `QPointF(0, 0)` because `__bool__` returns `not isNull()`. Replaced with explicit `is not None` checks at both occurrences.
- **Pixmap cache keyword-argument mismatch.** `ImagePixmapCache(max_size_mb=15)` would `TypeError` on construction; the class signature was `max_size`, and a call site passed an unsupported `max_size_mb`. Standardized on `max_size` with default 15 entries.

#### Changed
- `__init__.py` (project root) — `__version__`, `__author__`, and `__app_name__` now import from `utils.config` instead of being hardcoded. Single source of truth for application metadata.
- `utils/session_manager.py` — `AUTOSAVE_INTERVAL` set to its production value of 360 seconds (6 minutes). Was 60 seconds with a "for testing" comment.
- `utils/font_loader.py` — simplified to file-only loading. The unused embedded-base64 path containing a `<BASE64 FONT STRING HERE>` placeholder was removed. Net –13 lines.
- `utils/config.py` — `APP_TAGLINE` constant added alongside `APP_NAME`/`APP_VERSION`/`APP_AUTHOR`. Centralizes a tagline that was previously duplicated locally.

#### Removed
- `utils/utils_imports.py` — 189 lines of dead dynamic-import shims with lambda fallbacks. Confirmed zero production imports anywhere in the project. Net –189 lines.
- Dead duplicate `APP_NAME`/`APP_VERSION`/`APP_AUTHOR`/`APP_WEBSITE` constants in `ui/settings_panel.py` (lines 49–53). Defined but never referenced; pure dead weight. Net –7 lines.
- Dead duplicate `APP_AUTHOR`/`APP_YEAR` constants in `ui/about_dialog.py` (lines 26–27). `APP_TAGLINE` was retained but moved to `utils/config.py`. Net –6 lines.

#### Internal
- Renamed all "Color Mixer" copy-paste residue to "Color Picker" in `utils/logger.py`: module docstring, class docstring, default `LOG_FILE_PATH` value, demo-block log messages. Six replacements.
- Fixed broken import in `utils/logger.py` `__main__` demo block: `from utils.config import VERSION, APP_NAME` → `APP_VERSION, APP_NAME`. The original would always `ImportError` because `config.py` exports `APP_VERSION`, not `VERSION`.
- Hardcoded fallback version in `logger.py` demo block synced from `3.3.3` to `3.0.3`.
- Fixed broken import in root `__init__.py`: `from .logger import Logger` → `from utils.logger import Logger`. The original referenced a module that doesn't exist at the project root.

#### Testing
- Test coverage campaign concluded at **86% TOTAL** with branch coverage enabled, **1,641 tests** across two harnesses (400 `unittest` + 1,241 `pytest`).
- Thirteen modules now at ≥90% coverage including `error_handler.py` at 100%.
- Three production bugs (listed above under **Fixed**) were caught by tests written during the campaign.
- See [TESTING.md](TESTING.md) for the full architecture, phase-by-phase progression, and reusable patterns banked.

#### Documentation
- New `README.md` with hero image, feature list, install/quick-start, project structure, testing summary, and architecture highlights.
- New `LICENSE` (MIT).
- New `requirements.txt` and `requirements-test.txt` (split runtime/dev dependencies).
- New `TESTING.md` documenting the test campaign.
- New `pyproject.toml` enabling `pip install .` and `pip install -e .` workflows alongside the existing Visual Studio `.pyproj` file.

---

## [3.0.0] — 2025

> Earlier version history is summarized below at high level. Detailed entries can be backfilled from the project's commit history.

### Added
- Image-mode theme with translucent overlays and custom backgrounds.
- Six-tab settings panel covering color history, sessions, harmony, accessibility, shortcuts, and general settings.
- Hilbert-curve perceptual color sorting alongside the existing HSL sort.
- WCAG contrast checker and color-blindness simulator.
- Color harmony generator (complementary, triadic, tetradic, analogous, split-complementary, monochromatic, compound).
- 15+ palette export formats including Adobe `.ase`/`.aco`/`.acb`, GIMP `.gpl`, Procreate `.swatches`, Apple `.clr`, Affinity, JSON, XML, CSS, and SVG.
- Auto-save with crash recovery on next launch.

### Changed
- Major refactor splitting the monolithic main file into `core/`, `ui/`, and `utils/` packages.
- All colors moved to `utils/config.py` as the single source of truth (no hardcoded color literals elsewhere in the codebase).
- Performance work: paint events 500ms → 65ms via `StylesheetCache` and `QColorCache`; color-grid refresh 1.7s → 65ms via `WidgetPool` recycling.

---

## [2.x] — 2025

> Pre-modular versions. See git history for detail.

---

## [1.0.0] — 2025

Initial public release.
