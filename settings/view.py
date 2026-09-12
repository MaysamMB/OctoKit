"""Settings page (spec section 23). Every control here is wired to a real
ConfigManager field — nothing is decorative."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.config import ConfigManager
from core.permissions import is_admin
from core.powershell import PowerShellService
from ui.components.cards import PageHeader


class SettingsView(QWidget):
    def __init__(self, config: ConfigManager, powershell: PowerShellService, theme_manager=None):
        super().__init__()
        self.config = config
        self.powershell = powershell
        self.theme_manager = theme_manager

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        header = PageHeader("Settings", "Preferences for the whole application.")
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        layout.addWidget(self._build_general_group())
        layout.addWidget(self._build_project_generator_group())
        layout.addWidget(self._build_cleaning_group())
        layout.addWidget(self._build_logging_group())
        layout.addWidget(self._build_powershell_group())
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # ------------------------------------------------------------------

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox("General")
        form = QFormLayout(group)

        theme_combo = QComboBox()
        theme_combo.addItems(["system", "light", "dark"])
        theme_combo.setCurrentText(self.config.config.theme)
        theme_combo.currentTextChanged.connect(self._on_theme_changed)
        form.addRow("Theme", theme_combo)

        confirm_check = QCheckBox("Ask for confirmation before destructive actions")
        confirm_check.setChecked(self.config.config.confirm_destructive_actions)
        confirm_check.toggled.connect(lambda v: self.config.update(confirm_destructive_actions=v))
        form.addRow(confirm_check)

        maximized_check = QCheckBox("Start maximized")
        maximized_check.setChecked(self.config.config.start_maximized)
        maximized_check.toggled.connect(lambda v: self.config.update(start_maximized=v))
        form.addRow(maximized_check)

        reset_btn = QPushButton("Reset all onboarding tips")
        reset_btn.clicked.connect(self.config.reset_onboarding)
        form.addRow(reset_btn)

        return group

    def _on_theme_changed(self, value: str) -> None:
        self.config.update(theme=value)
        if self.theme_manager:
            self.theme_manager.apply(value)

    def _build_project_generator_group(self) -> QGroupBox:
        group = QGroupBox("Project Generator")
        form = QFormLayout(group)

        location_row = QHBoxLayout()
        location_edit = QLineEdit(self.config.config.default_project_location)
        location_edit.editingFinished.connect(
            lambda: self.config.update(default_project_location=location_edit.text())
        )
        location_row.addWidget(location_edit)
        browse_btn = QPushButton("Browse…")

        def browse():
            folder = QFileDialog.getExistingDirectory(self, "Default Project Location")
            if folder:
                location_edit.setText(folder)
                self.config.update(default_project_location=folder)

        browse_btn.clicked.connect(browse)
        location_row.addWidget(browse_btn)
        form.addRow("Default project location", location_row)

        template_dir_label = QLabel(str(self.config.config.resolved_template_directory()))
        template_dir_label.setObjectName("mutedText")
        form.addRow("Template directory", template_dir_label)

        return group

    def _build_cleaning_group(self) -> QGroupBox:
        group = QGroupBox("Cleaning")
        form = QFormLayout(group)

        age_spin = QSpinBox()
        age_spin.setRange(0, 100000)
        age_spin.setValue(self.config.config.default_min_age_minutes)
        age_spin.valueChanged.connect(lambda v: self.config.update(default_min_age_minutes=v))
        form.addRow("Default minimum file age (minutes)", age_spin)

        dry_run_check = QCheckBox("Default to Dry Run")
        dry_run_check.setChecked(self.config.config.dry_run_by_default)
        dry_run_check.toggled.connect(lambda v: self.config.update(dry_run_by_default=v))
        form.addRow(dry_run_check)

        recycle_check = QCheckBox("Include Recycle Bin by default")
        recycle_check.setChecked(self.config.config.include_recycle_bin_by_default)
        recycle_check.toggled.connect(lambda v: self.config.update(include_recycle_bin_by_default=v))
        form.addRow(recycle_check)

        registry_confirm_check = QCheckBox("Require typed confirmation for Registry deletions")
        registry_confirm_check.setChecked(self.config.config.require_typed_confirmation_for_registry)
        registry_confirm_check.toggled.connect(
            lambda v: self.config.update(require_typed_confirmation_for_registry=v)
        )
        form.addRow(registry_confirm_check)

        return group

    def _build_logging_group(self) -> QGroupBox:
        from core.paths import get_logs_dir

        group = QGroupBox("Logging")
        form = QFormLayout(group)

        level_combo = QComboBox()
        level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        level_combo.setCurrentText(self.config.config.log_level)

        def on_level_changed(value: str) -> None:
            from core.logger import configure_logging

            self.config.update(log_level=value)
            configure_logging(level=value)

        level_combo.currentTextChanged.connect(on_level_changed)
        form.addRow("Log level", level_combo)

        log_dir_label = QLabel(str(get_logs_dir()))
        log_dir_label.setObjectName("mutedText")
        form.addRow("Log directory", log_dir_label)

        return group

    def _build_powershell_group(self) -> QGroupBox:
        group = QGroupBox("PowerShell")
        form = QFormLayout(group)

        if self.powershell.is_available():
            exe_label = QLabel(self.powershell.discover_executable())
        else:
            exe_label = QLabel("Not found — PowerShell-dependent features are unavailable.")
        exe_label.setObjectName("mutedText")
        form.addRow("Detected executable", exe_label)

        scripts_label = QLabel(str(self.powershell.scripts_dir))
        scripts_label.setObjectName("mutedText")
        form.addRow("Script directory", scripts_label)

        admin_label = QLabel("Yes" if is_admin() else "No (elevation requested per-operation when needed)")
        admin_label.setObjectName("mutedText")
        form.addRow("Running as Administrator", admin_label)

        return group
