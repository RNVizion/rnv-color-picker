# Testing

> **Summary:** 1,641 tests across two harnesses · 86% TOTAL coverage with branch coverage enabled · 3 production bugs caught and fixed during the campaign · 26 reusable testing patterns banked.

This document describes the test architecture, the seven-phase campaign that built the suite, the coverage profile, and the three production bugs that the suite caught before they reached users.

---

## Quick stats

| Metric | Value |
|---|---|
| Total tests | **1,641** |
| `unittest` harness | 400 tests |
| `pytest` harness | 1,241 tests |
| Coverage (TOTAL, branch enabled) | **86%** |
| Modules at ≥90% coverage | 12 |
| Production bugs caught by the suite | 3 |
| Suite runtime | ~85 seconds (full combined run) |

Run the full combined suite:

```bash
python run_tests.py
```

This runs `unittest` first, then `pytest`, and merges coverage data into a single report.

---

## Architecture

The suite uses **two parallel harnesses** rather than a single test runner. This is deliberate — each harness covers what the other can't easily reach.

### `unittest` harness (`test_rnv_color_picker.py`)

A single 400-test file using Python's standard `unittest.TestCase`. Older portion of the suite, retained because:

- It catches regressions that depend on real Python startup paths (top-level import side effects, module-level cache initialization) which `pytest`'s collection mechanism can mask.
- It runs with zero plugin dependencies — useful as a smoke check on a fresh machine before installing the dev requirements.
- Its cumulative tests cover end-to-end module coupling that the more focused `pytest` files don't.

### `pytest` harness (`tests/`)

1,241 tests spread across one file per production module (`tests/test_<module>.py`). Uses:

- **`pytest-qt`** for real Qt event loop and signal verification (no mocking of widget signals).
- **`hypothesis`** for property-based testing of color math and color history invariants — round-trip identity, monotonicity, max-size invariants, etc.
- **`qtbot.waitUntil(predicate, timeout)`** for callback-driven manager tests where signals fire asynchronously.

The two harnesses share a `conftest.py` that globally patches `ColorHistoryManager.__init__/_setup/_load` so tests don't write to user `AppData` directories.

---

## Coverage profile

Coverage is measured with **branch coverage enabled** (stricter than line coverage alone). All numbers below are from the post-Phase-7 verified clean run.

### Modules at 90%+

| Module | Coverage | Notes |
|---|---|---|
| `utils/error_handler.py` | 100% | Every branch of every safe-execute path |
| `utils/pixmap_cache.py` | 99% | LRU eviction, resize, hit-rate stats |
| `ui/progress_dialog.py` | 97% | All three theme paths, cancel handling |
| `ui/about_dialog.py` | 96% | All four tabs, theme fallbacks |
| `core/accessibility.py` | 96% | WCAG ratios, color-blindness simulation |
| `core/color_math.py` | 95% | RGB/HSV/HSL/Lab/RYB round-trips, mixing modes |
| `core/palette_formats.py` | 94% | 17 file formats, round-trip preservation |
| `utils/async_file_ops.py` | 94% | Real QThread file I/O with progress callbacks |
| `utils/session_manager.py` | 93% | Save, load, autosave, recent sessions, cleanup |
| `core/color_history.py` | 91% | OS-specific path resolution, max-size invariant |
| `core/color_harmony.py` | 91% | All 7 harmony types |
| `utils/signal_manager.py` | 91% | Connection tracking, leak detection |

### Modules below 90% — and why

The remaining modules are not under-tested by accident; their uncovered lines fall into well-defined buckets that are uneconomical to test in isolation.

| Module | Coverage | Why the gap |
|---|---|---|
| `utils/font_loader.py` | 51% | OS-specific file-discovery branches and the system-fallback path require platform-specific test fixtures. |
| `utils/file_utils.py` | 55% | Defensive branches around `OSError` / `PermissionError` for unwritable paths — would require platform-specific permission setup. |
| `utils/logger.py` | 63% | ANSI rendering branches and file-logging path are touched by manual smoke tests rather than automated tests. |
| `utils/config.py` | 66% | Module-level constants and the `detect_image_resources()` filesystem walk — covered indirectly by integration runs. |
| `utils/settings_manager.py` | 69% | Settings export/import paths and settings-file-corruption recovery branches. |
| `utils/cache.py` | 71% | Some cache-eviction edge cases and unused convenience helpers. |
| `core/screen_color_picker.py` | 77% | Fullscreen overlay paint branches that depend on real cursor/screen geometry. |
| `ui/image_button.py` | 81% | Image-mode painting paths that depend on actual loaded button images. |
| `utils/dialog_helper.py` | 85% | The themed `get_text` / `get_int` instance-based dialog bodies are intentionally mocked at the call site in `settings_panel` tests to avoid modal `.exec()` blocking — a deliberate trade-off for test reliability. |
| `utils/clipboard.py` | 87% | Some `QApplication`-not-yet-initialized defensive branches. |

The `RNV_Color_Picker.py` main module itself is **excluded from the coverage spec** by design — the entry point is exercised by the application starting up, and coverage tooling for `if __name__ == "__main__"` blocks adds noise without insight.

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

**Symptom:** `ImagePixmapCache(max_size_mb=15)` would `TypeError` immediately on construction, which masked itself behind a fallback path that constructed an oversized cache.

**Root cause:** The class signature accepted `max_size` (entry count, default 15) but a call site passed `max_size_mb=256` (a megabyte budget that didn't exist as an argument). The call site had been written assuming a different cache abstraction that was never implemented.

**Fix:** Standardized on `max_size` with a default of 15 entries. Tests now construct the cache with both default and explicit `max_size` to lock the contract.

**Test that caught it:** `tests/test_pixmap_cache.py::TestInit::test_default_max_size_15`

### Bug 2 — `image_viewer.py` `QPointF(0,0)` truthiness

**Symptom:** Drag-to-select region extraction silently failed when the user's drag began at the absolute scene origin `(0, 0)`. No selection rectangle was created, no error logged. The user saw nothing happen.

**Root cause:** Two lines used `if self.selection_start:` to test whether a selection was in progress. `QPointF(0, 0)` is falsy in PyQt6 because `__bool__` returns `not self.isNull()`. The fix is `if self.selection_start is not None:`.

**Fix:** Both occurrences (lines 226 and 251) corrected to use explicit `is not None` checks. Two regression tests pin the `(0, 0)` case specifically.

**Tests that caught it:**
- `tests/test_image_widgets.py::TestMouseMoveEvent::test_drag_with_qpointf_zero_zero_start_now_creates_rect`
- `tests/test_image_widgets.py::TestMouseReleaseEvent::test_release_with_qpointf_zero_zero_start_now_fires`

### Bug 3 — `palette_formats.py` HSL importer tuple-order

**Symptom:** Importing an HSL `.hsl` palette file containing pure red (`H=0.0, S=100.0, L=50.0`) yielded white `(255, 255, 255)` instead of red `(255, 0, 0)`. Other colors were similarly wrong in non-obvious ways.

**Root cause:** `palette_formats.py` line 793 called `ColorMath.hsl_to_rgb((h, s, l))`, but `ColorMath.hsl_to_rgb` internally uses `colorsys.hls_to_rgb` which expects **(hue, lightness, saturation)** ordering — the standard Python stdlib convention. The fix swaps the tuple argument to `(h, l, s)`.

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

For each of the 17 supported palette formats, the test pattern is:
1. Construct a fixed input palette.
2. Export it to a temp file.
3. Re-import from the temp file.
4. Assert the imported colors match the input within a documented tolerance.

Three tolerance tiers were used:
- **Exact** — JSON, XML, GPL, hex text formats.
- **RGB-only** — formats that drop or default the weight metadata (CSS, SVG, ASE, ACO).
- **Lossy ±N per channel** — HSV/HSL/Lab formats that round-trip through floating-point conversion.

Documenting the tolerance per format makes the contract explicit.

---

## What's *not* tested

Honesty matters here. The suite does not currently cover:

- **Visual rendering correctness.** The custom theme stylesheets, image-mode translucent overlays, and tooltip rendering are exercised structurally (the right CSS strings get applied) but not visually verified. Doing this well requires a screenshot-diff harness — out of scope for v1.
- **Cross-platform clipboard edge cases.** macOS and Linux clipboard behavior is exercised on Windows CI; platform-specific quirks may exist.
- **Multi-monitor screen picker geometry.** The fullscreen overlay assumes a single primary screen. Multi-monitor cursor mapping has been smoke-tested but not unit-tested.
- **The main entry-point module (`RNV_Color_Picker.py`).** Excluded from the coverage spec by design — the entry point is exercised by application startup, and adding tests for `if __name__ == "__main__"` adds noise without insight.

---

## Future work

- **Mutation testing** with `mutmut` against `core/` modules. Coverage measures *what code ran*; mutation testing measures *whether the tests would notice if the code was wrong*. A natural next step.
- **GitHub Actions CI** running the suite on every push, with a coverage badge in the README. Tracked under portfolio Phase 5.
- **Property-based tests for `palette_formats`** edge cases — currently uses fixed inputs; hypothesis could surface format-specific malformations.

---

## Running tests

**Full combined suite:**

```bash
python run_tests.py
```

**Just `pytest` with verbose output:**

```bash
pytest tests/ -v
```

**Coverage report only:**

```bash
coverage run --source=core,utils,ui --branch -m pytest tests/
coverage report -m
```

**Single test file:**

```bash
pytest tests/test_palette_formats.py -v
```

**Single test:**

```bash
pytest tests/test_palette_formats.py::TestHslRoundTrip::test_round_trip_within_two_per_channel -v
```
