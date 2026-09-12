"""
Phase 11 integration test — proves the background-thread path is real.

Every other test exercises the *services* synchronously (direct method
calls) or the *views* structurally (widgets exist, wiring is present).
None of them actually pushed work through `core.workers.FunctionWorker`
on a `QThreadPool` and observed the UI update from the resulting Qt
signal — which is the exact mechanism spec sections 11/12 require for
every long-running operation. This file closes that gap by driving the
real `_start_scan()` button handlers on the real views, backed by a real
`PowerShellService` invoking the real scripts, and waiting for the
worker thread to finish via a local `QEventLoop` (no sleep-polling loops,
no faked signals).

Each test captures the genuine `FunctionWorker` instance created inside
the view (by subclassing it to record itself on construction) purely so
the test can `connect` to its real signal — the worker's behavior is
never modified or mocked.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from core.app_state import AppState
from core.config import ConfigManager
from core.powershell import PowerShellService
from core.workers import FunctionWorker as RealFunctionWorker

PWSH = PowerShellService()
pwsh_required = pytest.mark.skipif(
    not PWSH.is_available(), reason="Real PowerShell is required for worker integration tests."
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


class _CapturingWorker(RealFunctionWorker):
    """Same as FunctionWorker, but remembers every instance created.

    Used only so the test can grab a handle to the real worker object and
    wait on its real `finished`/`error` signal — it changes no behavior.
    """

    captured: list = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _CapturingWorker.captured.append(self)


@pytest.fixture
def capture_worker(monkeypatch):
    _CapturingWorker.captured.clear()

    def _patch(module):
        monkeypatch.setattr(module, "FunctionWorker", _CapturingWorker)

    yield _patch
    _CapturingWorker.captured.clear()


def _wait_for_worker(timeout_ms: int = 15000):
    """Block (while pumping Qt events) until the most recently captured
    worker's finished or error signal fires, or fail on timeout."""
    assert _CapturingWorker.captured, "No FunctionWorker was constructed — scan did not start."
    worker = _CapturingWorker.captured[-1]

    loop = QEventLoop()
    worker.signals.finished.connect(loop.quit)
    worker.signals.error.connect(loop.quit)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timed_out = not timer.isActive()
    timer.stop()
    if timed_out:
        pytest.fail("Worker thread did not finish within the timeout — it may have hung.")
    return worker


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return ConfigManager()


@pwsh_required
def test_inventory_scan_runs_off_ui_thread_and_updates_ui(qapp, config, capture_worker):
    import features.application_inventory.view as inv_view_module
    from features.application_inventory.service import InventoryService

    capture_worker(inv_view_module)
    view = inv_view_module.InventoryView(InventoryService(PWSH), AppState(), config)

    view._start_scan()
    # Disabled synchronously, before the background thread has had a chance to run —
    # proves the scan button click did not block the calling (UI) thread.
    assert view.scan_btn.isEnabled() is False

    worker = _wait_for_worker()
    assert worker.signals is not None

    # `_on_scan_finished` (or `_on_scan_error`) must have run as a queued slot
    # on the main thread by the time the event loop above returns.
    assert view.scan_btn.isEnabled() is True
    assert view._result is not None
    assert "Scan completed" in view.status_label.text()


@pwsh_required
def test_temp_cleaner_scan_runs_off_ui_thread_and_updates_ui(qapp, config, capture_worker):
    import features.temp_cleaner.view as temp_view_module
    from features.temp_cleaner.service import TempCleanerService

    capture_worker(temp_view_module)
    view = temp_view_module.TempCleanerView(TempCleanerService(PWSH), AppState(), config)

    view._start_scan()
    assert view.scan_btn.isEnabled() is False

    _wait_for_worker()

    assert view.scan_btn.isEnabled() is True
    assert view._last_scan is not None


@pwsh_required
def test_leftovers_scan_runs_off_ui_thread_and_updates_ui(qapp, config, capture_worker):
    import features.leftovers_cleaner.view as left_view_module
    from features.leftovers_cleaner.service import LeftoversService

    capture_worker(left_view_module)
    view = left_view_module.LeftoversView(LeftoversService(PWSH), AppState(), config)
    view.app_name_input.setText("NoSuchAppXYZ123")

    view._start_scan()
    assert view.scan_btn.isEnabled() is False

    _wait_for_worker()

    assert view.scan_btn.isEnabled() is True
    assert view._last_scan is not None
    assert view._last_scan.target_app_name == "NoSuchAppXYZ123"
