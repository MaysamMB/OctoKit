"""
Generic background-execution helper so no long-running call (PowerShell
scan/cleanup, inventory scan, project generation) ever runs on the UI
thread (spec section 11/12).

Usage:
    worker = FunctionWorker(my_service.scan, arg1, arg2)
    worker.signals.finished.connect(on_finished)
    worker.signals.error.connect(on_error)
    worker.signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(worker)

A callable that wants to report progress or support cancellation should
accept optional `progress_callback` and/or `cancel_event` keyword
arguments; `FunctionWorker` supplies them automatically when the target
callable declares them.
"""

from __future__ import annotations

import inspect
import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    started = Signal()
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(object)  # ToolkitError or Exception


class FunctionWorker(QRunnable):
    """Runs `fn(*args, **kwargs)` on a Qt thread-pool thread."""

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = dict(kwargs)
        self.signals = WorkerSignals()
        self.cancel_event = threading.Event()

        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            params = {}

        if "cancel_event" in params:
            self.kwargs["cancel_event"] = self.cancel_event
        if "progress_callback" in params:
            self.kwargs["progress_callback"] = self.signals.progress.emit

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:  # noqa: D102 - QRunnable override
        self.signals.started.emit()
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - must never crash the thread pool
            traceback.print_exc()
            self.signals.error.emit(exc)
        else:
            self.signals.finished.emit(result)
