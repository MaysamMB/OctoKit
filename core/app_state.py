"""
Small shared, in-memory session state that the Dashboard reads from and the
feature pages write to after a REAL scan/operation completes.

This deliberately holds no fake/placeholder numbers: every field starts as
`None` and the Dashboard renders that as "No scan yet" rather than a zero
or a made-up value, so the home screen never implies work has happened
when it hasn't (spec sections 5, 8).
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, Signal


class AppState(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.inventory_total_apps: int | None = None
        self.storage_summary: str | None = None
        self.inventory_broken: int | None = None
        self.inventory_orphans: int | None = None
        self.inventory_last_scan: datetime | None = None

        self.temp_scan_files: int | None = None
        self.temp_scan_bytes: int | None = None
        self.temp_last_scan: datetime | None = None
        self.temp_last_cleanup: datetime | None = None

        self.leftovers_last_app_scanned: str | None = None
        self.leftovers_candidates_found: int | None = None
        self.leftovers_last_scan: datetime | None = None

        self.projects_generated_count: int = 0
        self.projects_last_generated_path: str | None = None
        self.projects_last_generated_at: datetime | None = None

    def record_inventory_scan(self, total: int, broken: int, orphans: int) -> None:
        self.inventory_total_apps = total
        self.inventory_broken = broken
        self.inventory_orphans = orphans
        self.inventory_last_scan = datetime.now()
        self.changed.emit()

    def record_temp_scan(self, files: int, recoverable_bytes: int) -> None:
        self.temp_scan_files = files
        self.temp_scan_bytes = recoverable_bytes
        self.temp_last_scan = datetime.now()
        self.changed.emit()

    def record_temp_cleanup(self) -> None:
        self.temp_last_cleanup = datetime.now()
        self.changed.emit()

    def record_leftovers_scan(self, app_name: str, candidates: int) -> None:
        self.leftovers_last_app_scanned = app_name
        self.leftovers_candidates_found = candidates
        self.leftovers_last_scan = datetime.now()
        self.changed.emit()

    def record_project_generated(self, path: str) -> None:
        self.projects_generated_count += 1
        self.projects_last_generated_path = path
        self.projects_last_generated_at = datetime.now()
        self.changed.emit()
