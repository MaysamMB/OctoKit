"""Temporary Files Cleaner page (spec section 21)."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.app_state import AppState
from core.config import ConfigManager
from core.permissions import platform_supports_elevation
from core.workers import FunctionWorker
from features.temp_cleaner.models import TempCleanupResult, TempScanResult
from features.temp_cleaner.service import TempCleanerService
from ui.components.cards import InfoBanner, PageHeader, StatCard
from ui.dialogs.confirm_dialog import ConfirmItem, DestructiveConfirmDialog
from ui.dialogs.error_dialog import ErrorDialog
from core.models import Confidence

ONBOARDING_KEY = "tempcleaner"


def _fmt_bytes(num: int | None) -> str:
    if num is None:
        return "—"
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


class TempCleanerView(QWidget):
    def __init__(self, service: TempCleanerService, app_state: AppState, config: ConfigManager):
        super().__init__()
        self.service = service
        self.app_state = app_state
        self.config = config
        self._last_scan: TempScanResult | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = PageHeader(
            "Temporary Files Cleaner",
            "Finds and removes old temporary files, Windows Temp contents, and "
            "the Recycle Bin. Scanning never deletes anything — cleanup is a "
            "separate step that always asks for confirmation first.",
            read_only=None,
        )
        layout.addWidget(header)

        if not self.config.config.onboarding_dismissed.get(ONBOARDING_KEY):
            banner = InfoBanner(
                "Scan shows what CAN be cleaned and how much space you'd recover. "
                "Nothing is deleted until you review the results and confirm Cleanup.",
                kind="info",
                dismissible=True,
            )
            banner.dismissed.connect(lambda: self.config.set_onboarding_dismissed(ONBOARDING_KEY))
            layout.addWidget(banner)

        controls_row = QHBoxLayout()

        age_label = QLabel("Minimum file age (minutes):")
        controls_row.addWidget(age_label)
        self.min_age_spin = QSpinBox()
        self.min_age_spin.setRange(0, 100000)
        self.min_age_spin.setValue(self.config.config.default_min_age_minutes)
        self.min_age_spin.setToolTip(
            "Only files older than this are considered. Anything newer is left "
            "alone even if it's sitting in a temp folder, in case it's still in use."
        )
        controls_row.addWidget(self.min_age_spin)

        self.recycle_bin_check = QCheckBox("Include Recycle Bin")
        self.recycle_bin_check.setChecked(self.config.config.include_recycle_bin_by_default)
        controls_row.addWidget(self.recycle_bin_check)

        self.dry_run_check = QCheckBox("Dry Run (simulate cleanup, delete nothing)")
        self.dry_run_check.setChecked(self.config.config.dry_run_by_default)
        self.dry_run_check.setToolTip(
            "Simulates the cleanup and reports what would happen, without "
            "actually deleting anything."
        )
        controls_row.addWidget(self.dry_run_check)
        controls_row.addStretch(1)
        layout.addLayout(controls_row)

        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("  Scan")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self._start_scan)
        action_row.addWidget(self.scan_btn)

        self.clean_btn = QPushButton("Clean Selected")
        self.clean_btn.setObjectName("dangerButton")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._start_cleanup)
        action_row.addWidget(self.clean_btn)

        self.view_log_btn = QPushButton("View Log")
        self.view_log_btn.clicked.connect(self._show_log)
        action_row.addWidget(self.view_log_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("No scan yet. Click Scan to see what can be cleaned.")
        self.status_label.setObjectName("mutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        stats_row = QHBoxLayout()
        self.space_card = StatCard("Estimated Recoverable Space", icon_name="trash")
        self.files_card = StatCard("Files", icon_name="folder")
        self.folders_card = StatCard("Folders", icon_name="folder")
        self.locked_card = StatCard("Skipped (Locked/In Use)", icon_name="warning", accent="#b3730a")
        for c in (self.space_card, self.files_card, self.folders_card, self.locked_card):
            stats_row.addWidget(c)
        layout.addLayout(stats_row)

        self.admin_banner_container = QVBoxLayout()
        layout.addLayout(self.admin_banner_container)

        layout.addStretch(1)

    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Scanning…")

        worker = FunctionWorker(
            self.service.scan,
            min_age_minutes=self.min_age_spin.value(),
            include_recycle_bin=self.recycle_bin_check.isChecked(),
            timeout=60,
        )
        worker.signals.finished.connect(self._on_scan_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_scan_finished(self, result: TempScanResult) -> None:
        self._last_scan = result
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)

        recoverable = result.total_bytes
        self.space_card.set_value(_fmt_bytes(recoverable))
        self.files_card.set_value(str(result.total_files))
        self.folders_card.set_value(str(result.total_folders))
        self.locked_card.set_value("—")  # only known after an actual cleanup attempt

        self.status_label.setText(
            f"Scan completed at {result.scan_completed_at}. Nothing has been deleted."
        )

        self._clear_admin_banner()
        skipped_targets = [t for t in result.targets if t.skipped_admin]
        if skipped_targets and platform_supports_elevation():
            paths = ", ".join(t.path for t in skipped_targets)
            banner = InfoBanner(
                f"{paths} requires administrator privileges and was not scanned. "
                "You can run Cleanup elevated for just this operation if you want it included.",
                kind="warning",
            )
            self.admin_banner_container.addWidget(banner)

        self.app_state.record_temp_scan(files=result.total_files, recoverable_bytes=recoverable)

    def _clear_admin_banner(self) -> None:
        while self.admin_banner_container.count():
            item = self.admin_banner_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _start_cleanup(self) -> None:
        if not self._last_scan:
            return

        dry_run = self.dry_run_check.isChecked()
        min_age = self.min_age_spin.value()
        include_bin = self.recycle_bin_check.isChecked()

        items = [
            ConfirmItem(
                kind="Files/Folders",
                path=t.path,
                reason=f"{t.files_eligible} file(s), {t.folders_eligible} folder(s) older than {min_age} minutes",
                classification=Confidence.SAFE,
            )
            for t in self._last_scan.targets
            if t.processed and (t.files_eligible or t.folders_eligible)
        ]
        if include_bin and self._last_scan.recycle_bin.included:
            items.append(
                ConfirmItem(
                    kind="Recycle Bin",
                    path="Recycle Bin",
                    reason="All items in the Recycle Bin will be permanently removed",
                    classification=Confidence.SAFE,
                )
            )

        if not items:
            self.status_label.setText("Nothing eligible to clean based on the last scan.")
            return

        if not dry_run and self.config.config.confirm_destructive_actions:
            dialog = DestructiveConfirmDialog(
                self,
                title="Confirm Cleanup",
                summary="The following will be permanently deleted:",
                items=items,
                reversible=False,
                confirm_label="Clean Now",
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

        self.clean_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Simulating cleanup…" if dry_run else "Cleaning…")

        worker = FunctionWorker(
            self.service.cleanup,
            min_age_minutes=min_age,
            include_recycle_bin=include_bin,
            dry_run=dry_run,
            timeout=120,
        )
        worker.signals.finished.connect(self._on_cleanup_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_cleanup_finished(self, result: TempCleanupResult) -> None:
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)

        self.space_card.set_value(_fmt_bytes(result.total_bytes))
        self.files_card.set_value(str(result.total_files))
        self.folders_card.set_value(str(result.total_folders))
        self.locked_card.set_value(str(result.total_skipped_locked))

        verb = "Dry run finished" if result.dry_run else "Cleanup finished"
        self.status_label.setText(
            f"{verb} at {result.cleanup_completed_at}. "
            f"{result.total_files} file(s) and {result.total_folders} folder(s) "
            f"{'would be' if result.dry_run else 'were'} removed, "
            f"{result.total_skipped_locked} skipped because they were locked or in use."
        )

        if not result.dry_run:
            self.app_state.record_temp_cleanup()

    def _on_error(self, error: Exception) -> None:
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        ErrorDialog(self, error, next_step="Try again, or check the log for details.").exec()

    def _show_log(self) -> None:
        log_path = self._last_scan.log_file if self._last_scan else r"C:\ProgramData\AutoTempCleaner\cleanup.log"
        content = self.service.read_log_tail(log_path)

        dialog = QDialog(self)
        dialog.setWindowTitle("Cleanup Log")
        dialog.resize(640, 420)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit(content)
        text.setReadOnly(True)
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()
