# Testing

> **Summary:** over 1,900 tests across two harnesses · branch coverage measured on every run · a set of guard tests for rules that span the repository · 3 production bugs caught and fixed during the campaign · 26 reusable testing patterns banked.

This document describes the test architecture, the guard tests, the seven-phase campaign that built the suite, the coverage profile, and the three production bugs that the suite caught before they reached users.

---

## Quick stats

| Metric | Value |
|---|---|
| Total tests | **over 1,900** |
| `unittest` harness | over 300 tests |
| `pytest` harness | over 1,500 tests |
| Coverage (TOTAL, branch enabled) | measured on every full run; `python run_tests.py --report` prints it |
| Production bugs caught by the suite | 3 |

Run the full combined suite, after installing `tests/requirements-dev.txt` (see *Setting up for development* in the [README](README.md)):

```bash
python run_tests.py
```

This runs `unittest` first, then `pytest`, and merges coverage data into a single report. It runs coverage with the same Python that runs it (`python -m coverage`), never a `coverage` found first on PATH.

---

## Architecture

The suite uses **two parallel harnesses** rather than a single test runner. This is deliberate — each harness covers what the other can't easily reach.

### `unittest` harness (`test_rnv_color_picker.py`)

A single file of over 300 tests, using Python's standard `unittest.TestCase`. Older portion of the suite, retained because:

- It catches regressions that depend on real Python startup paths (top-level import side effects, module-level cache initialization) which `pytest`'s collection mechanism can mask.
- It runs with zero plugin dependencies — useful as a smoke check on a fresh machine before installing the dev requirements.
- Its cumulative tests cover end-to-end module coupling that the more focused `pytest` files don't.

### `pytest` harness (`tests/`)

Over 1,500 pytest tests in `tests/`. Some files test one module (`tests/test_session_manager.py`, `tests/test_palette_formats.py`); others test one topic across modules (`tests/test_picker_features.py` drives the main window through drag and drop, the gestures, palette import, the restore offer, and the settings Maximum Colors, Auto-load, Default Export Format and Remember window size and position) or hold a guard (below). Not every module has a file of its own. Uses:

- **`pytest-qt`** for real Qt event loop and signal verification (no mocking of widget signals).
- **`hypothesis`** for property-based testing of color math and color history invariants — round-trip identity, monotonicity, max-size invariants, etc.
- **`qtbot.waitUntil(predicate, timeout)`** for callback-driven manager tests where signals fire asynchronously.

Each harness patches `ColorHistoryManager.__init__/_setup/_load` itself, so tests don't write to the user's history file: the `unittest` file at its top, the `pytest` suite in `tests/conftest.py`. The root `conftest.py` only puts the project root on `sys.path`.

---

## Guard tests

Besides the tests of the app's behavior, a set of guard tests holds rules that span the
repository:

| Test | Holds |
|---|---|
| `tests/test_colors_in_sync.py` | the color file and `COLORS.md` are what `brand_map.json` and the pinned brand say |
| `tests/test_register_pin.py` | the installed rnv-brand is the pinned commit |
| `tests/test_atomic_state_writes.py` | every file the app keeps is written atomically |
| `tests/test_status_carried_by_a_word.py` | a status is never shown by color alone: each one has a word or a mark beside it |
| `tests/test_accent_images.py` | `ACCENT_IMAGES.md` matches the images |
| `tests/test_setup_scripts.py` | `in.sh` and `in.ps1` install the same files |
| `tests/test_readme_test_counts.py` | every test count the docs state is a floor that holds |
| `tests/test_install_resources.py` | an installed copy (`pip install .`) carries every file under `resources/` |

---

## Coverage profile

Coverage is measured with **branch coverage enabled** (stricter than line coverage alone).

Coverage is measured on every full run. `python run_tests.py --report` prints the current
figure for every module; it differs a little between Windows and Linux. CI prints the
combined report after every run; this repository's workflow sets no floor (`--fail-under`).
`python run_tests.py --summary` prints only the modules that are not fully covered.

### Where the gaps are — and why

The modules with the most uncovered lines are not under-tested by accident; their uncovered lines fall into well-defined buckets that are uneconomical to test in isolation.

| Module | Why the gap |
|---|---|
| `utils/font_loader.py` | OS-specific file-discovery branches and the system-fallback path require platform-specific test fixtures. |
| `utils/file_utils.py` | Defensive branches around `OSError` / `PermissionError` for unwritable paths — would require platform-specific permission setup. |
| `utils/logger.py` | ANSI rendering branches and file-logging path are touched by manual smoke tests rather than automated tests. |
| `utils/config.py` | The `detect_image_resources()` filesystem walk — covered indirectly by integration runs. |
| `utils/settings_manager.py` | Settings export/import paths and settings-file-corruption recovery branches. |
| `utils/cache.py` | Some cache-eviction edge cases and unused convenience helpers. |
| `core/screen_color_picker.py` | Fullscreen overlay paint branches that depend on real cursor/screen geometry. |
| `ui/image_button.py` | Image-mode painting paths that depend on actual loaded button images. |
| `utils/dialog_helper.py` | The themed `get_text` / `get_int` instance-based dialog bodies are intentionally mocked at the call site in `settings_panel` tests to avoid modal `.exec()` blocking — a deliberate trade-off for test reliability. |
| `utils/clipboard.py` | Some `QApplication`-not-yet-initialized defensive branches. |

The `RNV_Color_Picker.py` main module itself is **excluded from the coverage figures** by design. `tests/test_picker_features.py` drives the main window through its features all the same.

---

## The seven-phase campaign

The suite did not appear all at once. It was built across seven focused phases, each with a verification gate before the next began. This is the engineering log:

| Phase | Focus | Tests | TOTAL coverage |
|---|---|---|---|
| 0 | `unittest` baseline | 400 | 40% |
| 3a–3f, aux 1–5 | Per-module unit tests across `utils/` and `core/` | 878 | 71% |
| Bugfix pause | Fix bugs caught during 3a–3f before continuing | 774* | 69% |
| 5 | `hypothesis` property tests on `color_math` + `color_history` | 990 | 75% |
| 6 | Real Qt threading on `workers` + `async_file_ops` (no mocking signals) | 1,110 | 79% |
| 7 | `palette_formats` round-trip tests + HSL importer bugfix | 1,241 | **86%** |

\* Bugfix pause reduced the test count temporarily because flaky tests from earlier phases were removed and rewritten before continuing.

Each phase had an explicit definition of done before the next phase started. No phase was allowed to land with failing tests, and every phase ended with a clean combined run logged for posterity.

---

## Bugs caught by the suite

Three real production bugs were discovered by tests written during the campaign — bugs that had been latent in the codebase, not introduced by recent changes. All three are now fixed and have regression tests.

### Bug 1 — `pixmap_cache.py` keyword-argument mismatch

**Symptom:** constructing the cache with a `max_size_mb` keyword would `TypeError` immediately, which masked itself behind a fallback path that constructed an oversized cache.

**Root cause:** The class signature accepted `max_size` (entry count, default 15) but a call site passed `max_size_mb` (a megabyte budget that didn't exist as an argument). The call site had been written assuming a different cache abstraction that was never implemented.

**Fix:** Standardized on `max_size` with a default of 15 entries. Tests now construct the cache with both default and explicit `max_size` to lock the contract.

**Test that caught it:** `tests/test_pixmap_cache.py::TestInit::test_default_max_size_15`

### Bug 2 — `image_viewer.py` `QPointF(0,0)` truthiness

**Symptom:** Drag-to-select region extraction (Shift+drag today) silently failed when the user's drag began at the absolute scene origin `(0, 0)`. No selection rectangle was created, no error logged. The user saw nothing happen.

**Root cause:** Two checks, in the mouse-move and mouse-release handlers, used `if self.selection_start:` to test whether a selection was in progress. `QPointF(0, 0)` is falsy in PyQt6 because `__bool__` returns `not self.isNull()`. The fix is `if self.selection_start is not None:`.

**Fix:** Both occurrences corrected to use explicit `is not None` checks. Two regression tests pin the `(0, 0)` case specifically.

**Tests that caught it:**
- `tests/test_image_widgets.py::TestMouseMoveEvent::test_drag_with_qpointf_zero_zero_start_now_creates_rect`
- `tests/test_image_widgets.py::TestMouseReleaseEvent::test_release_with_qpointf_zero_zero_start_now_fires`

### Bug 3 — `palette_formats.py` HSL importer tuple-order

**Symptom:** Importing an HSL `.hsl` palette file containing pure red (`H=0.0, S=100.0, L=50.0`) yielded white `(255, 255, 255)` instead of red `(255, 0, 0)`. Other colors were similarly wrong in non-obvious ways.

**Root cause:** the HSL importer in `palette_formats.py` called `ColorMath.hsl_to_rgb((h, s, l))`, but `ColorMath.hsl_to_rgb` internally uses `colorsys.hls_to_rgb` which expects **(hue, lightness, saturation)** ordering — the standard Python stdlib convention. The fix swaps the tuple argument to `(h, l, s)`.

This bug was discovered by the round-trip test `test_round_trip_within_two_per_channel`: exporting then re-importing the same HSL palette should preserve the colors within ±2 per channel. It didn't, and the diff pointed straight at the conversion call.

**Fix:** Swapped the tuple ordering at the call site. Round-trip test now passes.

**Test that caught it:** `tests/test_palette_formats.py::TestHslRoundTrip::test_round_trip_within_two_per_channel`

---

## Banked test patterns

Twenty-six reusable techniques crystallized during the campaign. The most useful for future testing of PyQt6 applications:

### Modal dialog bypass

PyQt6 dialogs that call `.exec()` block test execution. Patching `QDialog.exec` to return immediately while still running the dialog's `__init__` lets you assert on the dialog's final state without ever rendering a window.

### `captured_exec` fixture

A pytest fixture that captures the most recently constructed `QMessageBox`/`QDialog` instance and exposes its title, text, icon, and button choice for assertion. Keeps test code declarative.

### `importlib.reload` bypass for `conftest` patches

When a `conftest.py` globally patches a class's `__init__`, you can temporarily reload the production module to get a *real* class for the small subset of tests that need it. Pattern lets you have your global patch *and* targeted unpatched tests in the same suite.

### `raising=False` for OS-conditional attributes

`monkeypatch.setattr(target, "name", value, raising=False)` lets you patch attributes that may not exist on this platform (e.g., `os.uname` on Windows) without the test failing on the wrong platform.

### Hybrid sync-run + real-start strategy (Phase 6)

For QThread workers, the cleanest pattern is:
- Test the worker's logic by calling `.run()` synchronously in the test thread (no event loop needed).
- Test the threading itself by calling `.start()` and using `qtbot.waitSignal(worker.finished, timeout=2000)`.

This separates "does the algorithm work" from "does the threading machinery work" cleanly.

### `FakeSlowWorker` fixture (Phase 6)

A purpose-built `QThread` subclass that sleeps for a controllable duration before emitting `finished`. Lets `WorkerManager` cancellation, cleanup, and concurrency tests run deterministically without actually doing slow work.

### `qtbot.waitUntil(predicate, timeout)` for callback-driven managers

When a manager's behavior is "after `cancel_all()`, the active count should eventually drop to zero," neither `waitSignal` nor sleep loops work cleanly. `qtbot.waitUntil(lambda: manager.get_active_count() == 0, timeout=1000)` polls the predicate until it's true or the timeout expires.

### Round-trip tests for file format I/O (Phase 7)

For each of the 16 palette formats that import (the 17 export formats less `.acb`, which is export-only and checked by its header), the test pattern is:
1. Construct a fixed input palette.
2. Export it to a temp file.
3. Re-import from the temp file.
4. Assert the imported colors match the input within a documented tolerance.

Three tolerance tiers are used:
- **Exact** — JSON, XML, `.colors`, `.hex`: colors and weights.
- **RGB-only** — formats that drop or default the weight (GPL, ASE, ACO, CLR, CSS, SCSS, SVG, TXT).
- **Lossy ±N per channel** — HSV (±1), HSL (±2), Affinity (±1) and Procreate (±1), which round-trip through floating-point conversion.

Documenting the tolerance per format makes the contract explicit.

---

## What's *not* tested

Honesty matters here. The suite does not currently cover:

- **Visual rendering correctness.** The custom theme stylesheets, image-mode translucent overlays, and tooltip rendering are exercised structurally (the right CSS strings get applied) but not visually verified. Doing this well requires a screenshot-diff harness — out of scope for v1.
- **Cross-platform clipboard edge cases.** CI runs the suite on Ubuntu and Windows; macOS is not exercised, and platform-specific quirks may exist.
- **Multi-monitor screen picker geometry.** The fullscreen overlay assumes a single primary screen. Multi-monitor cursor mapping has been smoke-tested but not unit-tested.
- **The main entry-point module (`RNV_Color_Picker.py`) in the coverage figures.** It is left out of them by design; `tests/test_picker_features.py` exercises its features, and `main()` itself runs only when the app starts.

---

## Future work

- **Mutation testing** with `mutmut` against `core/` modules. Coverage measures *what code ran*; mutation testing measures *whether the tests would notice if the code was wrong*. A natural next step.
- **Property-based tests for `palette_formats`** edge cases — currently uses fixed inputs; hypothesis could surface format-specific malformations.

---

## Running tests

**Full combined suite:**

```bash
python run_tests.py
```

**Just `pytest` with verbose output:**

```bash
python -m pytest tests/ -v
```

**Coverage report only:**

```bash
python -m coverage run --source=core,utils,ui --branch -m pytest tests/
python -m coverage report -m
```

**Single test file:**

```bash
python -m pytest tests/test_palette_formats.py -v
```

**Single test:**

```bash
python -m pytest tests/test_palette_formats.py::TestHslRoundTrip::test_round_trip_within_two_per_channel -v
```

Use `python -m pytest` and `python -m coverage` rather than a bare `pytest` or `coverage`: a copy on PATH from another Python has another rnv-brand, and the register-pin tests fail falsely under it.

**CI** (`.github/workflows/tests.yml`) runs both suites on Ubuntu and Windows with Python 3.13 on every push and pull request.
