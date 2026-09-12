"""Application Inventory page — strictly read-only (spec section 19)."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.app_state import AppState
from core.config import ConfigManager
from core.exceptions import ToolkitError
from core.paths import get_exports_dir
from core.workers import FunctionWorker
from features.application_inventory.models import InventoryResult
from features.application_inventory.service import InventoryService
from ui.components.cards import InfoBanner, PageHeader, StatCard
from ui.dialogs.error_dialog import ErrorDialog

ONBOARDING_KEY = "inventory"


class InventoryView(QWidget):
    def __init__(self, service: InventoryService, app_state: AppState, config: ConfigManager):
        super().__init__()
        self.service = service
        self.app_state = app_state
        self.config = config
        self._result: InventoryResult | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = PageHeader(
            "Application Inventory",
            "Scans installed application registrations and highlights unusual or "
            "potentially broken entries. This feature never deletes, uninstalls, "
            "or modifies anything.",
            read_only=True,
        )
        self.scan_btn = QPushButton("  Scan")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self._start_scan)
        header.add_action(self.scan_btn)

        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.clicked.connect(lambda: self._export("json"))
        self.export_json_btn.setEnabled(False)
        header.add_action(self.export_json_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))
        self.export_csv_btn.setEnabled(False)
        header.add_action(self.export_csv_btn)

        layout.addWidget(header)

        if not self.config.config.onboarding_dismissed.get(ONBOARDING_KEY):
            banner = InfoBanner(
                "Application Inventory scans installed-program registrations and folder "
                "evidence to spot broken or orphaned entries. It is completely read-only "
                "— nothing is ever uninstalled, deleted, or changed.",
                kind="info",
                dismissible=True,
            )
            banner.dismissed.connect(lambda: self.config.set_onboarding_dismissed(ONBOARDING_KEY))
            layout.addWidget(banner)

        stats_row = QHBoxLayout()
        self.total_card = StatCard("Total Applications", icon_name="apps")
        self.broken_card = StatCard("Broken Registrations", icon_name="warning", accent="#b3730a")
        self.orphan_card = StatCard("Possible Orphaned Registry Entries", icon_name="warning", accent="#b3730a")
        self.folders_card = StatCard("Possible Old Folders", icon_name="folder")
        for card in (self.total_card, self.broken_card, self.orphan_card, self.folders_card):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("No scan yet. Click Scan to inspect installed applications.")
        self.status_label.setObjectName("mutedText")
        layout.addWidget(self.status_label)

        filter_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name or publisher…")
        self.search_box.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_box, 1)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses")
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.status_filter)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All types", "Application", "System/Runtime Component"])
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.type_filter)
        layout.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Application", "Publisher", "Install Location", "Status", "Type", "Uninstaller"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        self.scan_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Scanning installed applications…")

        worker = FunctionWorker(self.service.scan, timeout=90)
        worker.signals.finished.connect(self._on_scan_finished)
        worker.signals.error.connect(self._on_scan_error)
        QThreadPool.globalInstance().start(worker)

    def _on_scan_finished(self, result: InventoryResult) -> None:
        self._result = result
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)

        self.total_card.set_value(str(result.total_applications))
        self.broken_card.set_value(str(result.broken_registrations_count))
        self.orphan_card.set_value(str(result.orphaned_registry_count))
        self.folders_card.set_value(str(result.old_folders_count))

        status_text = f"Scan completed at {result.scan_completed_at}. No files, folders, or registry entries were modified."
        if result.warnings:
            status_text += " " + " ".join(result.warnings)
        self.status_label.setText(status_text)

        statuses = sorted({app.status for app in result.applications})
        self.status_filter.blockSignals(True)
        self.status_filter.clear()
        self.status_filter.addItem("All statuses")
        self.status_filter.addItems(statuses)
        self.status_filter.blockSignals(False)

        self._populate_table(result.applications)
        self.app_state.record_inventory_scan(
            total=result.total_applications,
            broken=result.broken_registrations_count,
            orphans=result.orphaned_registry_count,
        )

    def _on_scan_error(self, error: Exception) -> None:
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.status_label.setText("The scan could not be completed.")
        ErrorDialog(
            self,
            error,
            next_step="You can try scanning again. If this keeps happening, check "
            "the Troubleshooting guide under Help.",
        ).exec()

    def _populate_table(self, applications) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for app in applications:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(app.name))
            self.table.setItem(row, 1, QTableWidgetItem(app.publisher))
            self.table.setItem(row, 2, QTableWidgetItem(app.install_location or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(app.status))
            self.table.setItem(row, 4, QTableWidgetItem(app.type))
            self.table.setItem(
                row, 5, QTableWidgetItem("Yes" if app.uninstaller_exists else "No")
            )
        self.table.setSortingEnabled(True)
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = self.search_box.text().strip().lower()
        status_filter = self.status_filter.currentText()
        type_filter = self.type_filter.currentText()

        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            publisher = self.table.item(row, 1).text().lower()
            status = self.table.item(row, 3).text()
            app_type = self.table.item(row, 4).text()

            matches_query = query in name or query in publisher
            matches_status = status_filter == "All statuses" or status == status_filter
            matches_type = type_filter == "All types" or app_type == type_filter

            self.table.setRowHidden(row, not (matches_query and matches_status and matches_type))

    def _export(self, fmt: str) -> None:
        if not self._result:
            return
        default_name = f"inventory_export.{fmt}"
        default_path = str(get_exports_dir() / default_name)
        path_str, _ = QFileDialog.getSaveFileName(
            self, f"Export as {fmt.upper()}", default_path, f"*.{fmt}"
        )
        if not path_str:
            return
        try:
            from pathlib import Path

            if fmt == "json":
                self.service.export_json(self._result, Path(path_str))
            else:
                self.service.export_csv(self._result, Path(path_str))
        except (OSError, ToolkitError) as exc:
            ErrorDialog(self, exc, next_step="Choose a different location and try again.").exec()
