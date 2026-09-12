"""
OctoKit — entry point.

Wires together core services, feature services, and the UI shell. No
business logic lives here — this module only constructs objects and
connects signals.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from core.app_state import AppState
from core.config import ConfigManager
from core.logger import configure_logging, get_logger
from core.powershell import PowerShellService
from features.application_inventory.service import InventoryService
from features.application_inventory.view import InventoryView
from features.leftovers_cleaner.service import LeftoversService
from features.leftovers_cleaner.view import LeftoversView
from features.project_generator.service import ProjectGeneratorService
from features.project_generator.template_manager import TemplateManager
from features.project_generator.view import ProjectGeneratorView
from features.temp_cleaner.service import TempCleanerService
from features.temp_cleaner.view import TempCleanerView
from features.storage_explorer.service import StorageService
from features.storage_explorer.view import StorageView
from help.view import HelpView
from settings.view import SettingsView
from ui.about_view import AboutView
from ui.main_window import MainWindow
from ui.theme import ThemeManager


def build_application() -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("OctoKit")
    app.setApplicationVersion("0.2.0")

    config = ConfigManager()
    configure_logging(level=config.config.log_level)
    logger = get_logger("main")
    logger.info("Application starting up.")

    theme_manager = ThemeManager(app, initial_mode=config.config.theme)
    theme_manager.apply()

    powershell = PowerShellService()
    if not powershell.is_available():
        logger.warning(
            "PowerShell was not found. Application Inventory, Leftovers Cleaner, "
            "and Temp Files Cleaner will be unavailable until it is installed."
        )

    app_state = AppState()
    window = MainWindow(app_state)

    template_manager = TemplateManager(config.config.resolved_template_directory())
    template_manager.create_default_templates()

    inventory_view = InventoryView(InventoryService(powershell), app_state, config)
    window.register_page("inventory", inventory_view)

    leftovers_view = LeftoversView(LeftoversService(powershell), app_state, config)
    window.register_page("leftovers", leftovers_view)

    temp_view = TempCleanerView(TempCleanerService(powershell), app_state, config)
    window.register_page("tempcleaner", temp_view)
    window.register_page("storage", StorageView(StorageService(), app_state))

    project_gen_view = ProjectGeneratorView(
        ProjectGeneratorService(template_manager), app_state, config
    )
    window.register_page("projectgen", project_gen_view)

    settings_view = SettingsView(config, powershell, theme_manager)
    window.register_page("settings", settings_view)

    help_view = HelpView()
    window.register_page("help", help_view)

    about_view = AboutView(open_help_callback=lambda: window.go_to("help"))
    window.register_page("about", about_view)

    if config.config.start_maximized:
        window.showMaximized()

    logger.info("Application ready.")
    return app, window


def main() -> int:
    app, window = build_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
