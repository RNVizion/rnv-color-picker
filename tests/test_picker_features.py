"""THE FEATURES THE README DESCRIBED, BUILT (#93 B, #95 A, #96 A, 2026-10-24).

Driven through the real main window, offscreen, in a home folder of its own.

  1. Drag and drop. An image file dropped on the window or the image view
     loads as Upload Image (Ctrl+O) does, through the same code and with the
     same types (PNG, JPG, JPEG). Anything else is refused with a message.
  2. Gestures. Shift+drag selects a region and extracts its colors (5 px
     each way at least); a plain drag pans; double-click picks one color;
     the wheel zooms.
  3. Palette import. Ctrl+I and the palette area's right-click menu reach
     ColorPickerApp.import_palette, which nothing called.
  4. The restore offer. A launch after a run that did not close cleanly
     offers that run's auto-save; a launch after a clean close does not.
  5. Maximum Colors. The palette limit follows the setting (1-1000, 333 by
     default); lowering it below the palette's size keeps every color.
  6. Auto-load last session. With it on, the last session recorded (the
     first in the recent-sessions list) loads at startup.
  7. Default Export Format. Export Palette (palette formats) and Save As
     Image (PNG, JPEG) open on it.
  8. Remember window size / position. Kept in the settings file from one
     close to the next launch; a position off every screen is not used.

Each test here fails against the code before this round.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QFileDialog

import utils.session_manager as session_manager_module
import utils.settings_manager as settings_manager_module
from utils.dialog_helper import DialogHelper
from utils.session_manager import SessionManager
from utils.settings_manager import get_settings_manager

#: How long the startup check needs: it runs 500 ms after the window is built.
STARTUP_WAIT_MS = 800


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A home folder of the test's own: settings, sessions and the recovery
    flag land in it, on Windows too."""
    folder = tmp_path / "home"
    folder.mkdir()
    for var in ("HOME", "USERPROFILE", "APPDATA"):
        monkeypatch.setenv(var, str(folder))
    monkeypatch.setattr(settings_manager_module, "_settings_instance", None)
    monkeypatch.setattr(session_manager_module, "_session_instance", None)
    return folder


@pytest.fixture
def dialogs(monkeypatch):
    """Record every message the app shows, without showing it. confirm()
    answers `dialogs.answer` (Yes by default)."""
    class Recorder(list):
        answer = True

    shown = Recorder()

    def record(kind):
        def show(parent, message, title=None, *args, **kwargs):
            shown.append((kind, title, message))
            return shown.answer if kind == "confirm" else None
        return staticmethod(show)

    for kind in ("show_info", "show_warning", "show_error", "confirm"):
        monkeypatch.setattr(DialogHelper, kind, record(kind))
    return shown


@pytest.fixture
def launch(home, qtbot, dialogs, monkeypatch):
    """Start the app as main() does. Settings given are saved first, as a
    previous run would have left them. Every window is closed at the end.

    Image mode is left out: finding it re-encodes the shipped background,
    which takes seconds per window, and nothing here depends on the mode."""
    import RNV_Color_Picker as main_module
    from utils.config import ThemeManager
    monkeypatch.setattr(ThemeManager, "detect_image_resources", lambda self: False)

    def start(wait_for_startup: bool = False, **settings):
        manager = get_settings_manager()
        for key, value in settings.items():
            manager.set(key, value)
        manager.save_settings()
        win = main_module.ColorPickerApp()
        qtbot.addWidget(win)
        if wait_for_startup:
            qtbot.wait(STARTUP_WAIT_MS)
        return win

    return start


@pytest.fixture
def sample_png(tmp_path):
    """A 120 x 80 image: left half red, right half blue, with a green block."""
    img = Image.new("RGB", (120, 80), (255, 0, 0))
    img.paste((0, 0, 255), (60, 0, 120, 80))
    img.paste((0, 255, 0), (40, 20, 80, 60))
    path = tmp_path / "sample.png"
    img.save(path)
    return path


def _shown(win, qtbot):
    win.resize(1280, 850)
    win.show()
    qtbot.waitExposed(win)
    return win


def _drop(target, paths=None, text=None):
    """Drag enter, then drop, as Qt delivers them, on `target`."""
    mime = QMimeData()
    if paths is not None:
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    if text is not None:
        mime.setText(text)
    pos = QPointF(target.width() / 2, target.height() / 2)
    enter = QDragEnterEvent(pos.toPoint(), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    enter.ignore()
    QApplication.sendEvent(target, enter)
    drop = QDropEvent(pos, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier)
    drop.ignore()
    QApplication.sendEvent(target, drop)
    return enter, drop


def _mouse(win, kind, pos, mods=Qt.KeyboardModifier.NoModifier):
    vp = win.graphics_view.viewport()
    pressed = kind != QEvent.Type.MouseMove
    event = QMouseEvent(kind, QPointF(pos), vp.mapToGlobal(QPointF(pos)),
                        Qt.MouseButton.LeftButton if pressed else Qt.MouseButton.NoButton,
                        Qt.MouseButton.LeftButton, mods)
    QApplication.sendEvent(vp, event)


def _drag(win, start, end, mods=Qt.KeyboardModifier.NoModifier):
    _mouse(win, QEvent.Type.MouseButtonPress, start, mods)
    mid = QPoint((start.x() + end.x()) // 2, (start.y() + end.y()) // 2)
    _mouse(win, QEvent.Type.MouseMove, mid, mods)
    _mouse(win, QEvent.Type.MouseMove, end, mods)
    _mouse(win, QEvent.Type.MouseButtonRelease, end, mods)


def _session_colors(rgbs):
    return [{"rgb": list(rgb), "hsl": [0, 0, 0], "hilbert": i, "locked": False}
            for i, rgb in enumerate(rgbs)]


# ---------------------------------------------------------------------------
# 1. Drag and drop
# ---------------------------------------------------------------------------


class TestDragAndDrop:
    def test_an_image_dropped_on_the_view_loads(self, launch, qtbot, sample_png, dialogs):
        win = _shown(launch(), qtbot)
        enter, drop = _drop(win.graphics_view.viewport(), [sample_png])
        assert enter.isAccepted() and drop.isAccepted()
        assert win.image is not None and win.image.size == (120, 80)
        assert win.pixmap_item is not None
        assert dialogs == []

    def test_an_image_dropped_on_the_window_loads(self, launch, qtbot, sample_png):
        win = _shown(launch(), qtbot)
        _drop(win, [sample_png])
        assert win.image is not None and win.image.size == (120, 80)

    @pytest.mark.parametrize("name", ["photo.JPG", "photo.jpeg"])
    def test_jpg_and_jpeg_load_whatever_the_case(self, launch, qtbot, tmp_path, name):
        path = tmp_path / name
        Image.new("RGB", (10, 10), (10, 20, 30)).save(path, "JPEG")
        win = _shown(launch(), qtbot)
        _drop(win.graphics_view.viewport(), [path])
        assert win.image is not None and win.image.size == (10, 10)

    def test_another_file_type_is_refused_with_a_message(self, launch, qtbot, tmp_path, dialogs):
        notes = tmp_path / "notes.txt"
        notes.write_text("not an image")
        win = _shown(launch(), qtbot)
        _drop(win.graphics_view.viewport(), [notes])
        assert win.image is None
        assert [(k, t) for k, t, _ in dialogs] == [("show_warning", "Image Not Loaded")]
        assert "notes.txt" in dialogs[0][2] and "PNG, JPG or JPEG" in dialogs[0][2]

    def test_a_file_that_is_not_really_an_image_is_refused(self, launch, qtbot, tmp_path, dialogs):
        fake = tmp_path / "fake.png"
        fake.write_text("not a PNG")
        win = _shown(launch(), qtbot)
        _drop(win, [fake])
        assert win.image is None
        assert [(k, t) for k, t, _ in dialogs] == [("show_warning", "Image Not Loaded")]

    def test_several_files_are_refused_with_a_message(self, launch, qtbot, sample_png, dialogs):
        win = _shown(launch(), qtbot)
        _drop(win, [sample_png, sample_png])
        assert win.image is None
        assert len(dialogs) == 1 and "2 files" in dialogs[0][2]

    def test_text_is_refused_with_a_message(self, launch, qtbot, dialogs):
        win = _shown(launch(), qtbot)
        enter, _ = _drop(win, text="hello")
        assert enter.isAccepted(), "taken, so the refusal is said rather than shown by the cursor alone"
        assert win.image is None
        assert len(dialogs) == 1 and "not a file" in dialogs[0][2]

    def test_upload_image_takes_the_same_path_and_types(self, launch, qtbot, sample_png, monkeypatch):
        win = launch()
        asked = []

        def pick(parent, caption, folder, filters):
            asked.append(filters)
            return str(sample_png), ""

        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(pick))
        loaded = []
        monkeypatch.setattr(win, "load_image_file", lambda p: loaded.append(p))
        win.upload_image()
        assert asked == ["Image files (*.png *.jpg *.jpeg)"]
        assert loaded == [str(sample_png)]


# ---------------------------------------------------------------------------
# 2. Gestures
# ---------------------------------------------------------------------------


class TestGestures:
    @pytest.fixture
    def win(self, launch, qtbot, sample_png):
        win = _shown(launch(), qtbot)
        win.load_image_file(str(sample_png))
        qtbot.wait(50)
        return win

    def test_shift_drag_selects_a_region_and_extracts_its_colors(self, win, dialogs):
        # the view fits the 120 x 80 image; a drag across the middle covers red, green and blue
        vp = win.graphics_view.viewport()
        left = win.graphics_view.mapFromScene(QPointF(5, 5))
        right = win.graphics_view.mapFromScene(QPointF(115, 75))
        _drag(win, left, right, Qt.KeyboardModifier.ShiftModifier)
        assert {c[0] for c in win.colors} == {(255, 0, 0), (0, 0, 255), (0, 255, 0)}
        assert vp.cursor().shape() != Qt.CursorShape.ClosedHandCursor

    def test_a_plain_drag_pans_and_extracts_nothing(self, win, qtbot):
        view = win.graphics_view
        view.scale(8, 8)                      # zoomed in: the image is bigger than the view
        qtbot.wait(50)
        h0, v0 = view.horizontalScrollBar().value(), view.verticalScrollBar().value()
        assert view.horizontalScrollBar().maximum() > 0
        _drag(win, QPoint(400, 200), QPoint(300, 150))
        assert win.colors == []
        assert view.selection_rect_item is None
        assert view.horizontalScrollBar().value() == h0 + 100
        assert view.verticalScrollBar().value() == v0 + 50

    def test_a_shift_drag_under_5_px_extracts_nothing(self, win):
        start = win.graphics_view.mapFromScene(QPointF(50, 40))
        end = win.graphics_view.mapFromScene(QPointF(54, 44))
        _drag(win, start, end, Qt.KeyboardModifier.ShiftModifier)
        assert win.colors == []

    def test_double_click_still_picks_one_color(self, win):
        at = win.graphics_view.mapFromScene(QPointF(10, 10))
        _mouse(win, QEvent.Type.MouseButtonDblClick, at)
        assert [c[0] for c in win.colors] == [(255, 0, 0)]

    def test_the_wheel_still_zooms(self, win):
        vp = win.graphics_view.viewport()
        before = win.scale_factor
        wheel = QWheelEvent(QPointF(100, 100), vp.mapToGlobal(QPointF(100, 100)), QPoint(0, 0),
                            QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(vp, wheel)
        assert win.scale_factor == pytest.approx(before * 1.1)


# ---------------------------------------------------------------------------
# 3. Palette import, reachable
# ---------------------------------------------------------------------------


class TestImportReachable:
    @pytest.fixture
    def scss(self, tmp_path):
        from core.palette_formats import PaletteFormats
        path = tmp_path / "brand.scss"
        PaletteFormats.export_palette(str(path), [((212, 175, 55), 50), ((30, 60, 140), 50)])
        return path

    @pytest.fixture
    def picks(self, monkeypatch, scss):
        asked = []

        def pick(parent, caption, folder, filters):
            asked.append(caption)
            return str(scss), ""

        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(pick))
        return asked

    def test_ctrl_i_imports_a_palette(self, launch, picks):
        win = launch()
        shortcut = [s for s in win._shortcuts if s.key().toString() == "Ctrl+I"]
        assert len(shortcut) == 1
        shortcut[0].activated.emit()
        assert picks == ["Import Palette"]
        assert {c[0] for c in win.colors} == {(212, 175, 55), (30, 60, 140)}

    def test_the_palette_menu_imports_a_palette(self, launch, picks):
        win = launch()
        actions = win.palette_menu().actions()
        assert [a.text().split("\t")[0] for a in actions] == ["Import Palette..."]
        assert actions[0].text().endswith("\tCtrl+I")
        actions[0].trigger()
        assert picks == ["Import Palette"]
        assert {c[0] for c in win.colors} == {(212, 175, 55), (30, 60, 140)}

    def test_right_click_on_the_palette_opens_that_menu(self, launch):
        win = launch()
        frame = win.scrollable_frame
        assert frame.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
        assert frame.receivers(frame.customContextMenuRequested) == 1


# ---------------------------------------------------------------------------
# 4. The restore offer
# ---------------------------------------------------------------------------


class TestRestoreOffer:
    def _run_that_autosaved(self, launch, rgbs):
        """A run that auto-saved these colors (what its 6-minute timer does)."""
        first = launch()
        for rgb in rgbs:
            first.add_color(rgb)
        first.session_manager._autosave()
        return first

    def test_no_offer_after_a_clean_close(self, launch, dialogs):
        first = self._run_that_autosaved(launch, [(1, 2, 3), (4, 5, 6)])
        first.close()                                      # a clean close
        assert list(first.session_manager.sessions_dir.glob("autosave_*")), \
            "the auto-saves are kept after a clean close"
        second = launch(wait_for_startup=True)
        assert [d for d in dialogs if d[0] == "confirm"] == []
        assert second.colors == []
        assert second.session_manager.check_for_autosave() is None

    def test_offer_after_a_run_that_did_not_close(self, launch, dialogs):
        first = self._run_that_autosaved(launch, [(1, 2, 3), (4, 5, 6)])
        written = str(first.session_manager.autosave_path)
        first.session_manager.autosave_timer.stop()        # the process dies: no closeEvent
        second = launch(wait_for_startup=True)
        offers = [d for d in dialogs if d[0] == "confirm"]
        assert [t for _, t, _ in offers] == ["Restore Previous Session?"]
        assert "2 colors" in offers[0][2]
        assert {c[0] for c in second.colors} == {(1, 2, 3), (4, 5, 6)}
        assert second.session_manager.check_for_autosave() == written

    def test_declining_leaves_the_palette_empty_and_keeps_the_autosave(self, launch, dialogs):
        first = self._run_that_autosaved(launch, [(1, 2, 3)])
        written = first.session_manager.autosave_path
        first.session_manager.autosave_timer.stop()
        dialogs.answer = False
        second = launch(wait_for_startup=True, auto_load_session=True)
        assert len([d for d in dialogs if d[0] == "confirm"]) == 1
        assert second.colors == [], "nothing is auto-loaded after an offer is declined"
        assert written.exists()

    def test_no_offer_when_the_flag_is_older_than_every_autosave(self, launch, dialogs, home):
        """An auto-save from before the run that did not close is not offered:
        that run wrote nothing."""
        old = SessionManager()
        old.save_session(str(old.autosave_path), colors_data=_session_colors([(9, 9, 9)]))
        os.utime(old.autosave_path, (1_000_000, 1_000_000))
        old._set_recovery_flag()
        launch(wait_for_startup=True)
        assert [d for d in dialogs if d[0] == "confirm"] == []


# ---------------------------------------------------------------------------
# 5. Maximum Colors
# ---------------------------------------------------------------------------


class TestMaximumColors:
    def test_the_limit_follows_the_saved_setting(self, launch):
        win = launch(max_colors=3)
        assert win.MAX_COLORS == 3
        for rgb in ((1, 1, 1), (2, 2, 2), (3, 3, 3)):
            assert win.add_color(rgb)
        assert not win.add_color((4, 4, 4))
        assert win.get_remaining_slots() == 0

    def test_the_default_is_333(self, launch):
        assert launch().MAX_COLORS == 333

    @pytest.mark.parametrize("saved, used", [(5000, 1000), (0, 1), ("abc", 333)])
    def test_a_saved_value_out_of_range_is_brought_in(self, launch, saved, used):
        assert launch(max_colors=saved).MAX_COLORS == used

    def test_lowering_it_below_the_palette_keeps_every_color(self, launch, dialogs):
        win = launch()
        for i in range(6):
            win.add_color((i, i, i))
        win._on_setting_changed("max_colors", 4)            # Apply in the Settings tab
        assert win.MAX_COLORS == 4
        assert len(win.colors) == 6, "no color is removed"
        assert win.get_remaining_slots() == 0
        assert not win.add_color((99, 99, 99))
        assert [(k, t) for k, t, _ in dialogs] == [("show_info", "Over the Maximum")]
        assert "6 colors" in dialogs[0][2] and "All 6 colors are kept" in dialogs[0][2]

    def test_raising_it_makes_room_again(self, launch, dialogs):
        win = launch(max_colors=2)
        win.add_color((1, 1, 1))
        win.add_color((2, 2, 2))
        win._on_setting_changed("max_colors", 3)
        assert win.add_color((3, 3, 3))
        assert dialogs == []


# ---------------------------------------------------------------------------
# 6. Auto-load last session
# ---------------------------------------------------------------------------


class TestAutoLoad:
    def _save_two_sessions(self):
        sessions = SessionManager()
        sessions.save_session("older", {"colors": _session_colors([(1, 1, 1)])})
        sessions.save_session("newer", {"colors": _session_colors([(2, 2, 2), (3, 3, 3)])})

    def test_on_loads_the_last_session_recorded(self, launch, dialogs):
        self._save_two_sessions()
        win = launch(wait_for_startup=True, auto_load_session=True)
        assert [c[0] for c in win.colors] == [(2, 2, 2), (3, 3, 3)]
        assert dialogs == []

    def test_off_loads_nothing(self, launch):
        self._save_two_sessions()
        win = launch(wait_for_startup=True, auto_load_session=False)
        assert win.colors == []

    def test_on_with_no_session_loads_nothing(self, launch, dialogs):
        win = launch(wait_for_startup=True, auto_load_session=True)
        assert win.colors == []
        assert dialogs == []

    def test_last_means_last_saved_or_loaded(self, launch, home):
        """Loading a session moves it to the front of the recent list, so it is
        the one Auto-load picks next time."""
        self._save_two_sessions()
        sessions = SessionManager()
        sessions.load_session("older")
        recent = json.loads((sessions.recent_file).read_text(encoding="utf-8"))
        assert Path(recent[0]).stem == "older"
        win = launch(wait_for_startup=True, auto_load_session=True)
        assert [c[0] for c in win.colors] == [(1, 1, 1)]


# ---------------------------------------------------------------------------
# 7. Default Export Format (#95 A): the save dialogs open on it
# ---------------------------------------------------------------------------


class TestDefaultExportFormat:
    """Settings > Default Export Format was saved and never read. Palette
    formats (GPL, ASE, JSON, CSS) are where Export Palette opens; PNG and
    JPEG are image formats, where Save As Image opens."""

    @pytest.fixture
    def asked(self, monkeypatch, tmp_path):
        """Record each save dialog's filters and the filter it opens on, and
        answer with a name typed without an extension, in the filter it
        opened on."""
        calls = []

        def ask(parent, caption, folder, filters, initial=None, *rest):
            calls.append((caption, filters.split(";;"), initial))
            return str(tmp_path / "palette"), initial or filters.split(";;")[0]

        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(ask))
        return calls

    @staticmethod
    def _with_colors(win):
        for rgb in ((10, 20, 30), (200, 100, 50)):
            win.add_color(rgb)
        return win

    @pytest.mark.parametrize("key, opens_on", [("gpl", "GIMP Palette (*.gpl)"),
                                               ("json", "JSON (*.json)"),
                                               ("css", "CSS Variables (*.css)")])
    def test_export_palette_opens_on_it(self, launch, asked, tmp_path, key, opens_on):
        win = self._with_colors(launch(export_format=key))
        win.export_palette()
        assert [(c, i) for c, _, i in asked] == [("Export Palette", opens_on)]
        assert (tmp_path / f"palette.{key}").exists(), \
            "a name typed without an extension takes the chosen format's"

    def test_save_as_image_opens_on_jpeg(self, launch, asked, tmp_path):
        win = self._with_colors(launch(export_format="jpeg"))
        win.save_colors_as_image()
        assert [(c, i) for c, _, i in asked] == [("Save Colors As Image", "JPEG Files (*.jpg *.jpeg)")]
        assert (tmp_path / "palette.jpg").exists()

    def test_an_image_format_leaves_export_palette_on_its_first_filter(self, launch, asked):
        win = self._with_colors(launch(export_format="jpeg"))
        win.export_palette()
        assert asked[0][2] is None

    def test_the_default_png_is_the_first_filter_already(self, launch, asked):
        win = self._with_colors(launch())
        win.save_colors_as_image()
        assert asked[0][1][0] == "PNG Files (*.png)" and asked[0][2] is None


# ---------------------------------------------------------------------------
# 8. Remember window size / position (#95 A)
# ---------------------------------------------------------------------------


def _wh(size):
    return size.width(), size.height()


def _xy(point):
    return point.x(), point.y()


class TestRememberWindow:
    """Both were saved by the Settings tab and never read: every launch
    opened at 1059 x 850, at (100, 100)."""

    def test_size_is_kept_from_one_close_to_the_next_launch(self, launch):
        first = launch()
        first.resize(1200, 900)
        first.close()
        assert _wh(launch().size()) == (1200, 900)

    def test_size_is_not_restored_when_off(self, launch):
        first = launch(remember_window_size=True)
        first.resize(1200, 900)
        first.close()
        get_settings_manager().set("remember_window_size", False)
        assert _wh(launch().size()) == (1059, 850)

    def test_position_is_kept_when_on(self, launch):
        first = launch(remember_window_position=True)
        first.move(150, 120)
        first.close()
        assert _xy(launch().pos()) == (150, 120)

    def test_position_is_not_restored_by_default(self, launch):
        first = launch()
        first.move(150, 120)
        first.close()
        assert _xy(launch().pos()) == (100, 100)

    def test_a_position_off_every_screen_is_not_used(self, launch):
        manager = get_settings_manager()
        manager.set("window_position", [-5000, -5000])
        win = launch(remember_window_position=True)
        assert _xy(win.pos()) == (100, 100), "the window stays where a user can see it"

    def test_the_settings_file_holds_them(self, launch, home):
        first = launch(remember_window_position=True)
        first.resize(1100, 870)
        first.move(30, 40)
        first.close()
        saved = json.loads(Path(get_settings_manager().settings_file).read_text(encoding="utf-8"))
        assert Path(get_settings_manager().settings_file).is_relative_to(home)
        assert saved["window_size"] == [1100, 870]
        assert saved["window_position"] == [30, 40]
