# -*- coding: utf-8 -*-
"""
Tests for utils/pixmap_cache.py.

Phase 3-aux-4 covers QPixmapCache (LRU cache base class) and the
ImagePixmapCache subclass with image-aware helpers, plus the module-level
helpers `create_cache_key_for_image`, `get_pixmap_cache`, and
`reset_pixmap_cache`.

Coverage targets:
  - QPixmapCache.__init__              (defaults + custom max_size)
  - QPixmapCache.get                   (hit + miss + LRU move-to-end)
  - QPixmapCache.put                   (add + replace + LRU eviction)
  - QPixmapCache.get_or_create         (hit returns cached + miss invokes
                                        creator + None-creator skipped)
  - QPixmapCache.clear                 (returns prior count)
  - QPixmapCache.remove                (present/absent)
  - QPixmapCache.resize                (larger no-op + smaller evicts)
  - QPixmapCache.get_size/get_max_size (basic readers)
  - QPixmapCache.get_stats             (empty + populated + hit_rate)
  - QPixmapCache.print_stats           (smoke)
  - QPixmapCache.reset_stats           (zeroes counters, keeps cache)
  - QPixmapCache.get_keys              (empty + LRU order)
  - QPixmapCache.contains              (preserves LRU)
  - ImagePixmapCache.__init__          (current_image_path=None)
  - ImagePixmapCache.set_current_image (same path noop + new path clears)
  - ImagePixmapCache.get_for_zoom      (composite key passed to get_or_create)
  - ImagePixmapCache.invalidate_image  (removes only matching path's keys)
  - create_cache_key_for_image         (without and with additional_params)
  - get_pixmap_cache / reset_pixmap_cache (constructor-kwarg fix verified)

Out of scope:
  - None. The constructor-kwarg mismatch originally surfaced in Phase
    3-aux-4 has been patched. This file now verifies the singleton works
    end-to-end and produces a fresh instance after reset.
"""

import pytest

from PyQt6.QtGui import QPixmap

from utils.pixmap_cache import (
    QPixmapCache,
    ImagePixmapCache,
    create_cache_key_for_image,
    get_pixmap_cache,
    reset_pixmap_cache,
)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def cache():
    """Fresh QPixmapCache with default max_size=15."""
    return QPixmapCache()


@pytest.fixture
def small_cache():
    """QPixmapCache with max_size=3 — for testing eviction."""
    return QPixmapCache(max_size=3)


@pytest.fixture
def image_cache():
    """Fresh ImagePixmapCache."""
    return ImagePixmapCache()


@pytest.fixture(autouse=True)
def _reset_singleton(qtbot):
    """Reset the module-level singleton between tests so mutations don't
    leak. qtbot ensures a QApplication is alive for QPixmap creation."""
    yield
    try:
        reset_pixmap_cache()
    except Exception:
        # In case the bug-logged path fires during teardown, swallow
        pass


def _make_pixmap(size: int = 32) -> QPixmap:
    """Build a small QPixmap for cache testing."""
    return QPixmap(size, size)


# =============================================================================
# 1.  QPixmapCache.__init__
# =============================================================================

class TestInit:
    """Init starts with empty cache and zero counters."""

    def test_default_max_size_15(self, cache):
        assert cache.get_max_size() == 15

    def test_custom_max_size(self):
        c = QPixmapCache(max_size=42)
        assert c.get_max_size() == 42

    def test_starts_empty(self, cache):
        assert cache.get_size() == 0

    def test_counters_start_zero(self, cache):
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['evictions'] == 0


# =============================================================================
# 2.  QPixmapCache.get
# =============================================================================

class TestGet:
    """`get` returns cached pixmap on hit (moving it to LRU end) and None
    on miss; counters increment accordingly."""

    def test_miss_returns_none(self, cache):
        assert cache.get(("nope",)) is None

    def test_miss_increments_misses_counter(self, cache):
        cache.get(("a",))
        cache.get(("b",))
        assert cache.get_stats()['misses'] == 2

    def test_hit_returns_pixmap(self, cache):
        pix = _make_pixmap()
        cache.put(("k",), pix)
        result = cache.get(("k",))
        assert result is pix

    def test_hit_increments_hits_counter(self, cache):
        cache.put(("k",), _make_pixmap())
        cache.get(("k",))
        cache.get(("k",))
        assert cache.get_stats()['hits'] == 2

    def test_hit_moves_to_end_lru(self, cache):
        # Insert 3 keys, access first → it should move to most-recent
        cache.put(("a",), _make_pixmap())
        cache.put(("b",), _make_pixmap())
        cache.put(("c",), _make_pixmap())
        # Access 'a' → moved to end
        cache.get(("a",))
        keys = cache.get_keys()
        # Order is oldest-to-newest, so 'a' should be last now
        assert keys[-1] == ("a",)


# =============================================================================
# 3.  QPixmapCache.put
# =============================================================================

class TestPut:
    """`put` adds an entry, replaces an existing one (refreshing LRU), and
    evicts the oldest entry when over capacity."""

    def test_adds_entry(self, cache):
        cache.put(("k",), _make_pixmap())
        assert cache.get_size() == 1

    def test_replaces_existing_key_with_new_pixmap(self, cache):
        first = _make_pixmap(16)
        second = _make_pixmap(64)
        cache.put(("k",), first)
        cache.put(("k",), second)
        assert cache.get(("k",)) is second
        assert cache.get_size() == 1

    def test_evicts_oldest_when_over_capacity(self, small_cache):
        # max_size=3: insert 4 → oldest evicted
        small_cache.put(("a",), _make_pixmap())
        small_cache.put(("b",), _make_pixmap())
        small_cache.put(("c",), _make_pixmap())
        small_cache.put(("d",), _make_pixmap())  # evicts 'a'
        assert small_cache.get_size() == 3
        assert ("a",) not in small_cache.get_keys()

    def test_eviction_increments_counter(self, small_cache):
        for k in ["a", "b", "c", "d", "e"]:
            small_cache.put((k,), _make_pixmap())
        # 5 inserted into 3-slot cache → 2 evictions
        assert small_cache.get_stats()['evictions'] == 2

    def test_evicts_in_lru_order(self, small_cache):
        small_cache.put(("a",), _make_pixmap())
        small_cache.put(("b",), _make_pixmap())
        small_cache.put(("c",), _make_pixmap())
        # Touch 'a' so 'b' becomes oldest
        small_cache.get(("a",))
        # Add new key — should evict 'b' (now oldest)
        small_cache.put(("d",), _make_pixmap())
        keys = small_cache.get_keys()
        assert ("b",) not in keys
        assert ("a",) in keys


# =============================================================================
# 4.  QPixmapCache.get_or_create
# =============================================================================

class TestGetOrCreate:
    """`get_or_create` returns cached value on hit; otherwise calls creator
    and caches the result. None-result from creator is NOT cached."""

    def test_returns_cached_on_hit(self, cache):
        pix = _make_pixmap()
        cache.put(("k",), pix)
        creator_calls = []
        result = cache.get_or_create(
            ("k",), lambda: creator_calls.append(1) or _make_pixmap(),
        )
        assert result is pix
        assert creator_calls == []  # creator NOT called on hit

    def test_creates_and_caches_on_miss(self, cache):
        new_pix = _make_pixmap()
        result = cache.get_or_create(("k",), lambda: new_pix)
        assert result is new_pix
        # Should be in cache now
        assert cache.contains(("k",))

    def test_none_creator_result_not_cached(self, cache):
        result = cache.get_or_create(("k",), lambda: None)
        assert result is None
        assert not cache.contains(("k",))

    def test_creator_called_only_once_for_miss_then_hit(self, cache):
        creator_calls = []
        def creator():
            creator_calls.append(1)
            return _make_pixmap()
        cache.get_or_create(("k",), creator)
        cache.get_or_create(("k",), creator)
        # Second call hits cache
        assert creator_calls == [1]


# =============================================================================
# 5.  QPixmapCache.clear
# =============================================================================

class TestClear:
    """`clear` empties the dict and returns the prior count."""

    def test_returns_zero_when_empty(self, cache):
        assert cache.clear() == 0

    def test_returns_count_when_populated(self, cache):
        for k in ["a", "b", "c"]:
            cache.put((k,), _make_pixmap())
        assert cache.clear() == 3

    def test_size_zero_after_clear(self, cache):
        cache.put(("k",), _make_pixmap())
        cache.clear()
        assert cache.get_size() == 0


# =============================================================================
# 6.  QPixmapCache.remove
# =============================================================================

class TestRemove:
    """`remove` deletes a specific key, returns True/False."""

    def test_returns_false_for_unknown_key(self, cache):
        assert cache.remove(("missing",)) is False

    def test_returns_true_when_removed(self, cache):
        cache.put(("k",), _make_pixmap())
        assert cache.remove(("k",)) is True
        assert not cache.contains(("k",))


# =============================================================================
# 7.  QPixmapCache.resize
# =============================================================================

class TestResize:
    """`resize` updates max_size and evicts oldest entries if shrinking."""

    def test_grow_does_not_evict(self, small_cache):
        for k in ["a", "b", "c"]:
            small_cache.put((k,), _make_pixmap())
        small_cache.resize(10)
        assert small_cache.get_max_size() == 10
        assert small_cache.get_size() == 3
        assert small_cache.get_stats()['evictions'] == 0

    def test_shrink_evicts_oldest(self, small_cache):
        for k in ["a", "b", "c"]:
            small_cache.put((k,), _make_pixmap())
        small_cache.resize(1)
        assert small_cache.get_size() == 1
        # 'c' is most recent → kept
        assert small_cache.contains(("c",))
        assert small_cache.get_stats()['evictions'] == 2

    def test_shrink_to_zero_clears_all(self, small_cache):
        for k in ["a", "b", "c"]:
            small_cache.put((k,), _make_pixmap())
        small_cache.resize(0)
        assert small_cache.get_size() == 0


# =============================================================================
# 8.  Stats accessors
# =============================================================================

class TestStats:
    """`get_stats` returns a dict with size/max_size/hits/misses/hit_rate/
    evictions; `print_stats` is a smoke test; `reset_stats` zeroes counters
    without touching the cache itself."""

    def test_empty_stats_has_zero_hit_rate(self, cache):
        s = cache.get_stats()
        assert s['hit_rate'] == 0
        assert s['size'] == 0

    def test_hit_rate_computed_correctly(self, cache):
        # 3 hits, 1 miss → 75%
        cache.put(("k",), _make_pixmap())
        cache.get(("k",))    # hit
        cache.get(("k",))    # hit
        cache.get(("k",))    # hit
        cache.get(("missing",))  # miss
        assert cache.get_stats()['hit_rate'] == 75.0

    def test_get_stats_includes_max_size(self, cache):
        assert cache.get_stats()['max_size'] == 15

    def test_print_stats_does_not_crash_empty(self, cache):
        cache.print_stats()  # must not raise

    def test_print_stats_does_not_crash_populated(self, cache):
        cache.put(("k",), _make_pixmap())
        cache.get(("k",))
        cache.print_stats()

    def test_reset_stats_zeroes_counters(self, cache):
        cache.put(("k",), _make_pixmap())
        cache.get(("k",))
        cache.get(("nope",))
        cache.reset_stats()
        s = cache.get_stats()
        assert s['hits'] == 0
        assert s['misses'] == 0
        assert s['evictions'] == 0

    def test_reset_stats_keeps_cache_contents(self, cache):
        cache.put(("k",), _make_pixmap())
        cache.reset_stats()
        # Cache still has the entry
        assert cache.contains(("k",))


# =============================================================================
# 9.  get_keys and contains
# =============================================================================

class TestKeysAndContains:
    """`get_keys` returns LRU-ordered list (oldest first). `contains`
    must NOT change LRU order."""

    def test_get_keys_empty(self, cache):
        assert cache.get_keys() == []

    def test_get_keys_in_insertion_order(self, cache):
        for k in ["x", "y", "z"]:
            cache.put((k,), _make_pixmap())
        keys = cache.get_keys()
        assert keys == [("x",), ("y",), ("z",)]

    def test_contains_returns_true_for_present_key(self, cache):
        cache.put(("k",), _make_pixmap())
        assert cache.contains(("k",)) is True

    def test_contains_returns_false_for_absent_key(self, cache):
        assert cache.contains(("missing",)) is False

    def test_contains_does_not_affect_lru(self, cache):
        cache.put(("a",), _make_pixmap())
        cache.put(("b",), _make_pixmap())
        cache.contains(("a",))  # check 'a' — should NOT promote
        keys = cache.get_keys()
        # 'a' should still be first (oldest)
        assert keys == [("a",), ("b",)]


# =============================================================================
# 10.  ImagePixmapCache
# =============================================================================

class TestImagePixmapCacheConstruction:
    """`ImagePixmapCache.__init__` adds `current_image_path=None`."""

    def test_inherits_from_qpixmap_cache(self, image_cache):
        assert isinstance(image_cache, QPixmapCache)

    def test_default_image_path_is_none(self, image_cache):
        assert image_cache.current_image_path is None

    def test_custom_max_size_passed_to_parent(self):
        c = ImagePixmapCache(max_size=7)
        assert c.get_max_size() == 7


class TestSetCurrentImage:
    """`set_current_image` clears cache and updates path on path change."""

    def test_first_call_clears_zero(self, image_cache):
        # No prior path; cache empty → nothing to clear; but path differs
        # from None, so clear() is called returning 0
        cleared = image_cache.set_current_image("/img1.jpg")
        assert cleared == 0
        assert image_cache.current_image_path == "/img1.jpg"

    def test_same_path_returns_zero_and_keeps_cache(self, image_cache):
        image_cache.set_current_image("/img1.jpg")
        image_cache.put(("/img1.jpg", 1.0, (100, 100)), _make_pixmap())
        cleared = image_cache.set_current_image("/img1.jpg")  # same
        assert cleared == 0
        # Cache should still have the entry
        assert image_cache.get_size() == 1

    def test_different_path_clears_cache_and_returns_count(self, image_cache):
        image_cache.set_current_image("/img1.jpg")
        image_cache.put(("/img1.jpg", 1.0, (100, 100)), _make_pixmap())
        image_cache.put(("/img1.jpg", 2.0, (100, 100)), _make_pixmap())
        cleared = image_cache.set_current_image("/img2.jpg")
        assert cleared == 2
        assert image_cache.get_size() == 0
        assert image_cache.current_image_path == "/img2.jpg"


class TestGetForZoom:
    """`get_for_zoom` builds a (path, zoom, size) cache key and delegates
    to `get_or_create`."""

    def test_builds_composite_key_and_caches(self, image_cache):
        new_pix = _make_pixmap()
        result = image_cache.get_for_zoom(
            "/img.jpg", 1.5, (800, 600), creator=lambda: new_pix,
        )
        assert result is new_pix
        # Verify the composite key was stored
        assert image_cache.contains(("/img.jpg", 1.5, (800, 600)))

    def test_subsequent_call_hits_cache(self, image_cache):
        creator_calls = []
        def creator():
            creator_calls.append(1)
            return _make_pixmap()
        image_cache.get_for_zoom("/img.jpg", 1.0, (10, 10), creator)
        image_cache.get_for_zoom("/img.jpg", 1.0, (10, 10), creator)
        assert creator_calls == [1]  # only called once


class TestInvalidateImage:
    """`invalidate_image` removes only the keys whose first element matches."""

    def test_removes_only_matching_path(self, image_cache):
        image_cache.put(("/a.jpg", 1.0, (10, 10)), _make_pixmap())
        image_cache.put(("/a.jpg", 2.0, (10, 10)), _make_pixmap())
        image_cache.put(("/b.jpg", 1.0, (10, 10)), _make_pixmap())
        removed = image_cache.invalidate_image("/a.jpg")
        assert removed == 2
        assert image_cache.get_size() == 1
        # /b.jpg's entry should still be there
        assert image_cache.contains(("/b.jpg", 1.0, (10, 10)))

    def test_returns_zero_when_no_match(self, image_cache):
        image_cache.put(("/a.jpg", 1.0, (10, 10)), _make_pixmap())
        removed = image_cache.invalidate_image("/nonexistent.jpg")
        assert removed == 0


# =============================================================================
# 11.  create_cache_key_for_image (helper function)
# =============================================================================

class TestCreateCacheKeyForImage:
    """`create_cache_key_for_image` builds a hashable tuple key."""

    def test_without_additional_params(self):
        key = create_cache_key_for_image("/img.jpg", 1.5, (800, 600))
        assert key == ("/img.jpg", 1.5, (800, 600))

    def test_with_additional_params_appended(self):
        key = create_cache_key_for_image(
            "/img.jpg", 1.5, (800, 600),
            additional_params={"quality": "high", "sharpen": True},
        )
        # Should be 4 elements; last is sorted tuple of items
        assert len(key) == 4
        assert key[0] == "/img.jpg"
        assert key[3] == (("quality", "high"), ("sharpen", True))

    def test_keys_hashable_for_use_in_dict(self):
        key = create_cache_key_for_image(
            "/img.jpg", 1.0, (10, 10), {"k": "v"},
        )
        # If unhashable, this would raise
        d = {key: "value"}
        assert d[key] == "value"

    def test_empty_additional_params_dict_treated_as_falsy(self):
        # Empty dict → falsy → no extra tuple element appended
        key = create_cache_key_for_image(
            "/img.jpg", 1.0, (10, 10), additional_params={},
        )
        assert len(key) == 3


# =============================================================================
# 12.  Module-level singleton helpers
# =============================================================================

class TestSingletonHelpers:
    """`get_pixmap_cache` and `reset_pixmap_cache` provide a module-level
    cache instance. The constructor-kwarg mismatch (originally documented
    as a bug in Phase 3-aux-4) has since been fixed: the wrapper's
    parameter is now `max_size` and is forwarded to the constructor with
    the matching name.
    """

    def test_get_pixmap_cache_returns_image_pixmap_cache(self):
        # First call constructs the singleton; type must be ImagePixmapCache
        cache = get_pixmap_cache()
        assert isinstance(cache, ImagePixmapCache)

    def test_get_pixmap_cache_returns_same_instance_on_subsequent_calls(self):
        first = get_pixmap_cache()
        second = get_pixmap_cache()
        assert first is second

    def test_get_pixmap_cache_with_custom_max_size(self):
        # Custom max_size should be honored on first construction
        cache = get_pixmap_cache(max_size=42)
        assert cache.get_max_size() == 42

    def test_reset_when_no_instance_is_safe(self):
        # If singleton was never created, reset must be a no-op
        # (autouse fixture may have already done this, but call explicitly)
        reset_pixmap_cache()
        # Calling again must also be safe
        reset_pixmap_cache()

    def test_reset_then_recreate_yields_fresh_instance(self):
        first = get_pixmap_cache()
        reset_pixmap_cache()
        second = get_pixmap_cache()
        # After reset, a new instance is constructed
        assert first is not second
