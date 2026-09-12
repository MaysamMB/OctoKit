import os
import stat
import threading
from types import SimpleNamespace
import pytest
from features.storage_explorer.scanner import scan, excluded
from features.storage_explorer.analyzer import advice, largest_path
from features.storage_explorer.models import Node, Drive


def test_totals_hierarchy_and_global_largest(tmp_path):
    folder = tmp_path / "أعمال"
    folder.mkdir()
    for name in ("a", "b"):
        (folder / name).write_bytes(b"x" * 60)
    (tmp_path / "large file").write_bytes(b"z" * 100)
    result = scan(tmp_path)
    assert result.root.size == 220
    assert result.files == 3
    assert result.root.status == "complete"
    assert result.root.children[0].path == str(folder)
    assert result.largest_files[0].size == 100
    assert next(largest_path(result.root))[0].path == str(folder)
    assert (folder / "a").read_bytes() == b"x" * 60


def test_empty_and_single_file(tmp_path):
    assert scan(tmp_path).root.size == 0
    file = tmp_path / "file"
    file.write_bytes(b"123")
    assert scan(file).root.size == 3


def test_cancel_before_scan(tmp_path):
    event = threading.Event()
    event.set()
    result = scan(tmp_path, cancel_event=event)
    assert result.cancelled and result.root.status == "partial"


def test_cancel_during_scan(tmp_path):
    (tmp_path / "file").touch()
    event = threading.Event()
    result = scan(tmp_path, cancel_event=event,
                  progress_callback=lambda _: event.set())
    assert result.cancelled
    assert result.root.status == "partial"


def test_resource_limit(tmp_path):
    for i in range(10):
        (tmp_path / str(i)).touch()
    result = scan(tmp_path, max_nodes=4)
    assert result.limited and result.root.status == "partial"
    assert len(result.root.children) == 3


def test_symlink_loop_and_root_rejection(tmp_path):
    link = tmp_path / "loop"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable")
    result = scan(tmp_path)
    assert result.skipped == 1 and result.root.status == "partial"
    with pytest.raises(ValueError):
        scan(link)


def test_unavailable_directory(tmp_path, monkeypatch):
    folder = tmp_path / "denied"
    folder.mkdir()
    original = os.scandir
    def guarded(path):
        if str(path) == str(folder):
            raise PermissionError("test")
        return original(path)
    monkeypatch.setattr(os, "scandir", guarded)
    result = scan(tmp_path)
    assert result.skipped == 1 and result.root.status == "partial"


@pytest.mark.parametrize("flag", [0x400, 0x1000, 0x40000, 0x400000])
def test_windows_cloud_and_reparse_exclusions(flag):
    assert excluded(SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=flag))


def test_hard_links_are_explicit_logical_entries(tmp_path):
    first = tmp_path / "a"
    first.write_bytes(b"1234")
    try:
        os.link(first, tmp_path / "b")
    except OSError:
        pytest.skip("Hard links unavailable")
    result = scan(tmp_path)
    assert result.root.size == 8 and result.hardlink_entries == 2


@pytest.mark.parametrize("path, phrase", [
    (r"C:\Windows\test", "Do not delete"),
    (r"C:\Program Files\app", "uninstaller"),
    (r"C:\Users\x\.android\avd", "dependencies"),
    (r"C:\Users\x\cache", "Not certified safe"),
    (r"C:\Users\x\photos", "unknown"),
])
def test_conservative_advice(path, phrase):
    assert phrase in advice(Node(path, status="complete"))


def test_incomplete_advice_and_zero_drive():
    assert "Incomplete" in advice(Node("x"))
    assert Drive("x", 0, 0, 0).percent == 0


def test_progress_and_top_100(tmp_path):
    for i in range(120):
        (tmp_path / str(i)).write_bytes(b"x" * i)
    messages = []
    result = scan(tmp_path, progress_callback=messages.append)
    assert len(result.largest_files) == 100
    assert result.largest_files[0].size == 119
    assert messages[0].startswith("Scanning")
    assert messages[-1].startswith("Scan ended")


def test_qt_model_and_view(tmp_path):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QModelIndex
    from core.app_state import AppState
    from features.storage_explorer.service import StorageService
    from features.storage_explorer.view import StorageView
    app = QApplication.instance() or QApplication([])
    (tmp_path / "file").write_bytes(b"test")
    view = StorageView(StorageService(), AppState())
    result = scan(tmp_path)
    view._finished(result)
    view.timer.stop()
    model = view.model
    root = model.index(0, 0)
    child = model.index(0, 0, root)
    assert model.rowCount(QModelIndex()) == 1
    assert model.parent(child) == root
    assert not model.parent(root).isValid()
    assert model.rowCount(model.index(0, 1)) == 0
    assert view.rescan.isEnabled()
    view._largest()
    assert "file" in view.log.toPlainText()
    view.close()


def test_vanishing_file_marks_parent_partial(tmp_path, monkeypatch):
    file = tmp_path / "gone"
    file.touch()
    original = os.lstat
    def changing(path, *args, **kwargs):
        if str(path) == str(file):
            raise FileNotFoundError("Disappeared during scan")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(os, "lstat", changing)
    result = scan(tmp_path)
    assert result.skipped == 1
    assert result.root.status == "partial"


def test_actual_background_worker_and_rescan(tmp_path):
    import time
    from PySide6.QtWidgets import QApplication
    from core.app_state import AppState
    from features.storage_explorer.service import StorageService
    from features.storage_explorer.view import StorageView
    app = QApplication.instance() or QApplication([])
    state = AppState()
    view = StorageView(StorageService(), state)
    (tmp_path / "file").write_bytes(b"123")
    def run():
        view.start_scan(str(tmp_path))
        assert view.worker is not None
        assert not view.choose.isEnabled()
        deadline = time.monotonic() + 5
        while view.worker and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.001)
        assert view.worker is None
        view.timer.stop()
    run()
    assert view.result.root.size == 3
    (tmp_path / "file").write_bytes(b"12345")
    run()
    assert view.result.root.size == 5
    assert state.storage_summary is not None
    assert view.choose.isEnabled()
    view.close()
