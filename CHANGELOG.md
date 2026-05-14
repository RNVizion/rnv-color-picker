# Changelog

All notable changes to RNV Color Picker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Mutation testing harness (`mutmut`) against `core/` modules.
- GitHub Actions CI with a "tests passing" badge.
- PyInstaller spec for downloadable `.exe` releases.

---

## [3.0.3] — 2026-01

This release closes out a multi-phase test-coverage and code-hygiene campaign. Three latent production bugs were caught by the new test suite and fixed. Cross-project copy-paste residue was cleaned up. Application metadata is now sourced from a single file.

### Fixed
- **HSL palette importer tuple-order bug.** Importing an `.hsl` palette containing pure red (`H=0.0, S=100.0, L=50.0`) yielded white instead of red. Root cause: `palette_formats.py` passed `(h, s, l)` to `ColorMath.hsl_to_rgb` but the underlying `colorsys.hls_to_rgb` expects `(h, l, s)`. Fixed at `palette_formats.py` line 793.
- **Image viewer drag from origin.** Drag-to-select region extraction silently failed when the user's drag began at scene origin `(0, 0)`. Root cause: `if self.selection_start:` is falsy for `QPointF(0, 0)` because `__bool__` returns `not isNull()`. Replaced with explicit `is not None` checks at both occurrences.
- **Pixmap cache keyword-argument mismatch.** `ImagePixmapCache(max_size_mb=15)` would `TypeError` on construction; the class signature was `max_size`, and a call site passed an unsupported `max_size_mb`. Standardized on `max_size` with default 15 entries.

### Changed
- `__init__.py` (project root) — `__version__`, `__author__`, and `__app_name__` now import from `utils.config` instead of being hardcoded. Single source of truth for application metadata.
- `utils/session_manager.py` — `AUTOSAVE_INTERVAL` set to its production value of 360 seconds (6 minutes). Was 60 seconds with a "for testing" comment.
- `utils/font_loader.py` — simplified to file-only loading. The unused embedded-base64 path containing a `<BASE64 FONT STRING HERE>` placeholder was removed. Net –13 lines.
- `utils/config.py` — `APP_TAGLINE` constant added alongside `APP_NAME`/`APP_VERSION`/`APP_AUTHOR`. Centralizes a tagline that was previously duplicated locally.

### Removed
- `utils/utils_imports.py` — 189 lines of dead dynamic-import shims with lambda fallbacks. Confirmed zero production imports anywhere in the project. Net –189 lines.
- Dead duplicate `APP_NAME`/`APP_VERSION`/`APP_AUTHOR`/`APP_WEBSITE` constants in `ui/settings_panel.py` (lines 49–53). Defined but never referenced; pure dead weight. Net –7 lines.
- Dead duplicate `APP_AUTHOR`/`APP_YEAR` constants in `ui/about_dialog.py` (lines 26–27). `APP_TAGLINE` was retained but moved to `utils/config.py`. Net –6 lines.

### Internal
- Renamed all "Color Mixer" copy-paste residue to "Color Picker" in `utils/logger.py`: module docstring, class docstring, default `LOG_FILE_PATH` value, demo-block log messages. Six replacements.
- Fixed broken import in `utils/logger.py` `__main__` demo block: `from utils.config import VERSION, APP_NAME` → `APP_VERSION, APP_NAME`. The original would always `ImportError` because `config.py` exports `APP_VERSION`, not `VERSION`.
- Hardcoded fallback version in `logger.py` demo block synced from `3.3.3` to `3.0.3`.
- Fixed broken import in root `__init__.py`: `from .logger import Logger` → `from utils.logger import Logger`. The original referenced a module that doesn't exist at the project root.

### Testing
- Test coverage campaign concluded at **87% TOTAL** with branch coverage enabled, **1,641 tests** across two harnesses (400 `unittest` + 1,241 `pytest`).
- Thirteen modules now at ≥90% coverage including `error_handler.py` at 100%.
- Three production bugs (listed above under **Fixed**) were caught by tests written during the campaign.
- See [TESTING.md](TESTING.md) for the full architecture, phase-by-phase progression, and reusable patterns banked.

### Documentation
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
