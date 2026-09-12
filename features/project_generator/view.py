"""Project Generator page (spec section 18)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_state import AppState
from core.config import ConfigManager
from core.exceptions import ProjectAlreadyExistsError, ToolkitError
from core.workers import FunctionWorker
from features.project_generator.models import ProjectGenerationResult
from features.project_generator.service import ProjectGeneratorService
from ui.components.cards import PageHeader
from ui.dialogs.error_dialog import ErrorDialog


class ProjectGeneratorView(QWidget):
    def __init__(self, service: ProjectGeneratorService, app_state: AppState, config: ConfigManager):
        super().__init__()
        self.service = service
        self.app_state = app_state
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = PageHeader(
            "Project Generator",
            "Scaffolds a new project from a template: folders, starter files, "
            "and a config.json, with the project name filled in automatically.",
        )
        layout.addWidget(header)

        form_row = QHBoxLayout()

        name_col = QVBoxLayout()
        name_col.addWidget(QLabel("Project Name"))
        self.name_input = QLineEdit("MyProject")
        self.name_input.textChanged.connect(self._update_preview)
        name_col.addWidget(self.name_input)
        form_row.addLayout(name_col, 1)

        template_col = QVBoxLayout()
        template_col.addWidget(QLabel("Template"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(self.service.template_manager.get_templates())
        self.template_combo.currentIndexChanged.connect(self._update_preview)
        template_col.addWidget(self.template_combo)
        form_row.addLayout(template_col, 1)

        layout.addLayout(form_row)

        location_col = QVBoxLayout()
        location_col.addWidget(QLabel("Create Project In"))
        location_row = QHBoxLayout()
        self.location_input = QLineEdit(self.config.config.default_project_location)
        location_row.addWidget(self.location_input, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._choose_location)
        location_row.addWidget(browse_btn)
        location_col.addLayout(location_row)
        layout.addLayout(location_col)

        preview_label = QLabel("Preview")
        layout.addWidget(preview_label)
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(220)
        layout.addWidget(self.preview_text)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("mutedText")
        layout.addWidget(self.stats_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.create_btn = QPushButton("  Create Project")
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.clicked.connect(self._create_project)
        button_row.addWidget(self.create_btn)
        layout.addLayout(button_row)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch(1)

        self._update_preview()

    def _choose_location(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose Project Location")
        if folder:
            self.location_input.setText(folder)

    def _update_preview(self) -> None:
        template_name = self.template_combo.currentText()
        if not template_name:
            self.preview_text.setPlainText("")
            self.stats_label.setText("")
            return
        try:
            preview = self.service.preview(template_name, self.name_input.text())
        except ToolkitError:
            self.preview_text.setPlainText("")
            self.stats_label.setText("")
            return

        self.preview_text.setPlainText(preview.tree_text)
        self.stats_label.setText(
            f"Template: {template_name}    Files: {preview.file_count}    Folders: {preview.folder_count}"
        )

    def _create_project(self, force_overwrite: bool = False) -> None:
        project_name = self.name_input.text().strip()
        template_name = self.template_combo.currentText()
        location_text = self.location_input.text().strip()

        try:
            self.service.validate_project_name(project_name)
            self.service.validate_location(Path(location_text) if location_text else Path())
        except ToolkitError as exc:
            ErrorDialog(self, exc).exec()
            return

        self.create_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Creating project…")

        worker = FunctionWorker(
            self.service.generate,
            template_name,
            project_name,
            Path(location_text),
            force_overwrite=force_overwrite,
        )
        worker.signals.finished.connect(self._on_generated)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_generated(self, result: ProjectGenerationResult) -> None:
        self.progress_bar.hide()
        self.create_btn.setEnabled(True)
        self.status_label.setText(
            f"Project created successfully.\nLocation: {result.project_path}\n"
            f"Files created: {len(result.files_created)}    Folders created: {len(result.folders_created)}"
        )
        self.app_state.record_project_generated(str(result.project_path))

    def _on_error(self, error: Exception) -> None:
        self.progress_bar.hide()
        self.create_btn.setEnabled(True)

        if isinstance(error, ProjectAlreadyExistsError):
            answer = QMessageBox.question(
                self,
                "Project Already Exists",
                f"{error.user_message}\n\n{error.technical_details}\n\n"
                "Do you want to overwrite the conflicting files?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._create_project(force_overwrite=True)
            return

        ErrorDialog(self, error, next_step="Check the project name and location, then try again.").exec()
