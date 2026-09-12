"""Application Leftovers Cleaner page (spec section 20)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_state import AppState
from core.config import ConfigManager
from core.models import Confidence
from core.workers import FunctionWorker
from features.leftovers_cleaner.models import LeftoverCandidate, LeftoverDeleteResult, LeftoverScanResult
from features.leftovers_cleaner.service import LeftoversService
from ui.components.cards import ClassificationBadge, InfoBanner, PageHeader
from ui.dialogs.confirm_dialog import ConfirmItem, DestructiveConfirmDialog
from ui.dialogs.error_dialog import ErrorDialog

ONBOARDING_KEY = "leftovers"


class CandidateRow(QWidget):
    def __init__(self, candidate: LeftoverCandidate):
        super().__init__()
        self.candidate = candidate

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(candidate.classification == Confidence.SAFE)
        layout.addWidget(self.checkbox)

        text_col = QVBoxLayout()
        path_label = QLabel(candidate.path)
        path_label.setWordWrap(True)
        text_col.addWidget(path_label)
        reason_label = QLabel(candidate.reason)
        reason_label.setObjectName("mutedText")
        text_col.addWidget(reason_label)
        layout.addLayout(text_col, 1)

        layout.addWidget(ClassificationBadge(candidate.classification))

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()


class LeftoversView(QWidget):
    def __init__(self, service: LeftoversService, app_state: AppState, config: ConfigManager):
        super().__init__()
        self.service = service
        self.app_state = app_state
        self.config = config
        self._last_scan: LeftoverScanResult | None = None
        self._folder_rows: list[CandidateRow] = []
        self._registry_rows: list[CandidateRow] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = PageHeader(
            "Application Leftovers Cleaner",
            "Finds files, folders, and registry entries left behind by an "
            "application you've already uninstalled. Nothing is deleted "
            "until you review and select items yourself.",
            read_only=False,
        )
        layout.addWidget(header)

        if not self.config.config.onboarding_dismissed.get(ONBOARDING_KEY):
            banner = InfoBanner(
                "Uninstall the application normally first. This tool only looks for "
                "what an uninstaller left behind — it never uninstalls anything itself. "
                "Items are never auto-selected unless they're an exact name match.",
                kind="warning",
                dismissible=True,
            )
            banner.dismissed.connect(lambda: self.config.set_onboarding_dismissed(ONBOARDING_KEY))
            layout.addWidget(banner)

        search_row = QHBoxLayout()
        self.app_name_input = QLineEdit()
        self.app_name_input.setPlaceholderText("Application name (as it appeared in Programs and Features)…")
        self.app_name_input.returnPressed.connect(self._start_scan)
        search_row.addWidget(self.app_name_input, 1)

        self.scan_btn = QPushButton("  Scan for Leftovers")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self._start_scan)
        search_row.addWidget(self.scan_btn)
        layout.addLayout(search_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Enter an application name and click Scan.")
        self.status_label.setObjectName("mutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.still_installed_container = QVBoxLayout()
        layout.addLayout(self.still_installed_container)

        selection_row = QHBoxLayout()
        select_safe_btn = QPushButton("Select Safe Items")
        select_safe_btn.clicked.connect(self._select_safe_only)
        selection_row.addWidget(select_safe_btn)

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        selection_row.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        selection_row.addWidget(deselect_all_btn)
        selection_row.addStretch(1)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._start_delete)
        selection_row.addWidget(self.delete_btn)
        layout.addLayout(selection_row)

        groups_row = QHBoxLayout()

        folders_group = QGroupBox("Folders")
        folders_layout = QVBoxLayout(folders_group)
        self.folders_list = QListWidget()
        folders_layout.addWidget(self.folders_list)
        groups_row.addWidget(folders_group)

        registry_group = QGroupBox("Registry")
        registry_layout = QVBoxLayout(registry_group)
        self.registry_list = QListWidget()
        registry_layout.addWidget(self.registry_list)
        groups_row.addWidget(registry_group)

        layout.addLayout(groups_row, 1)

    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        app_name = self.app_name_input.text().strip()
        if not app_name:
            self.status_label.setText("Enter an application name first.")
            return

        self.scan_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.progress_bar.show()
        self._clear_still_installed_banner()
        self.status_label.setText(f"Searching for leftovers of '{app_name}'…")

        worker = FunctionWorker(self.service.scan, app_name, timeout=60)
        worker.signals.finished.connect(self._on_scan_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_scan_finished(self, result: LeftoverScanResult) -> None:
        self._last_scan = result
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)

        if result.still_installed:
            self.folders_list.clear()
            self.registry_list.clear()
            self._folder_rows = []
            self._registry_rows = []
            self.status_label.setText(
                f"'{result.target_app_name}' still appears to be installed."
            )
            names = ", ".join(m.display_name for m in result.installed_matches)
            banner = InfoBanner(
                f"{names} is still registered as installed. Please uninstall it "
                "normally first, then scan again for leftovers.",
                kind="warning",
            )
            self.still_installed_container.addWidget(banner)
            return

        self._populate_lists(result)
        self.status_label.setText(
            f"Scan completed at {result.scan_completed_at}. "
            f"{result.total_candidates} candidate item(s) found. Nothing has been deleted."
        )
        self.app_state.record_leftovers_scan(result.target_app_name, result.total_candidates)

    def _clear_still_installed_banner(self) -> None:
        while self.still_installed_container.count():
            item = self.still_installed_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _populate_lists(self, result: LeftoverScanResult) -> None:
        self.folders_list.clear()
        self.registry_list.clear()
        self._folder_rows = []
        self._registry_rows = []

        for candidate in result.folders:
            row = CandidateRow(candidate)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.folders_list.addItem(item)
            self.folders_list.setItemWidget(item, row)
            self._folder_rows.append(row)

        for candidate in result.registry:
            row = CandidateRow(candidate)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.registry_list.addItem(item)
            self.registry_list.setItemWidget(item, row)
            self._registry_rows.append(row)

        self.delete_btn.setEnabled(bool(self._folder_rows or self._registry_rows))

    def _select_safe_only(self) -> None:
        for row in self._folder_rows + self._registry_rows:
            row.checkbox.setChecked(row.candidate.classification == Confidence.SAFE)

    def _set_all_checked(self, checked: bool) -> None:
        for row in self._folder_rows + self._registry_rows:
            row.checkbox.setChecked(checked)

    def _start_delete(self) -> None:
        if not self._last_scan:
            return

        selected_folders = [r.candidate for r in self._folder_rows if r.is_checked()]
        selected_registry = [r.candidate for r in self._registry_rows if r.is_checked()]

        if not selected_folders and not selected_registry:
            self.status_label.setText("Select at least one item to delete.")
            return

        confirm_items = [
            ConfirmItem(kind="Folder", path=c.path, reason=c.reason, classification=c.classification)
            for c in selected_folders
        ] + [
            ConfirmItem(kind="Registry", path=c.path, reason=c.reason, classification=c.classification)
            for c in selected_registry
        ]

        has_registry = bool(selected_registry)
        required_phrase = (
            "DELETE REGISTRY"
            if has_registry and self.config.config.require_typed_confirmation_for_registry
            else None
        )

        if self.config.config.confirm_destructive_actions:
            dialog = DestructiveConfirmDialog(
                self,
                title="Confirm Deletion",
                summary=f"The following {len(confirm_items)} item(s) related to "
                f"'{self._last_scan.target_app_name}' will be permanently deleted:",
                items=confirm_items,
                reversible=False,
                required_phrase=required_phrase,
                confirm_label="Delete Selected",
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

        self.delete_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Deleting selected items…")

        worker = FunctionWorker(
            self.service.delete,
            self._last_scan.target_app_name,
            approved_folders=[c.path for c in selected_folders],
            approved_registry=[c.path for c in selected_registry],
            timeout=90,
        )
        worker.signals.finished.connect(self._on_delete_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_delete_finished(self, result: LeftoverDeleteResult) -> None:
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)

        if result.aborted:
            self.status_label.setText(
                f"Nothing was deleted: {result.abort_reason or 'the application now appears to be installed.'}"
            )
            return

        deleted_count = len(result.deleted_folders) + len(result.deleted_registry)
        rejected_count = len(result.rejected)
        failed_count = len(result.failed)

        message = (
            f"Deletion finished at {result.delete_completed_at}. "
            f"{deleted_count} item(s) deleted."
        )
        if rejected_count:
            message += f" {rejected_count} item(s) were rejected on re-validation and left untouched."
        if failed_count:
            message += f" {failed_count} item(s) could not be deleted (see details)."
        self.status_label.setText(message)

        # Re-scan to reflect the new state of the system.
        self._start_scan()

    def _on_error(self, error: Exception) -> None:
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.delete_btn.setEnabled(bool(self._folder_rows or self._registry_rows))
        ErrorDialog(self, error, next_step="Try scanning again.").exec()
