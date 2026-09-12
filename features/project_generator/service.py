"""
Service layer for the Project Generator - the non-UI logic extracted from
the original Tkinter `ProjectGeneratorApp` (validate_project_name,
validate, generate_project, replace_variables), made independent of any
GUI framework so it can be driven by the new PySide6 view.

Two safe, additive fixes were made on top of the original logic (see
inline comments): stricter Windows name validation, and itemized
conflict detection before overwriting an existing project directory,
instead of a single blanket yes/no gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.exceptions import (
    InvalidProjectNameError,
    ProjectAlreadyExistsError,
    TemplateNotFoundError,
    ToolkitError,
)
from core.logger import get_logger
from features.project_generator.models import ProjectGenerationResult, ProjectPreview
from features.project_generator.template_manager import TemplateManager

logger = get_logger("features.project_generator")

_INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')

# Windows reserved device names - invalid as a file/folder name with or
# without an extension. Not checked by the original script (a gap
# identified during source inspection); added here as a safe, additive
# strengthening of validation, not a behavior change to anything that
# previously worked.
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class ProjectGeneratorService:
    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_project_name(self, project_name: str) -> None:
        if not project_name:
            raise InvalidProjectNameError(user_message="Please enter a project name.")

        if _INVALID_CHARS_PATTERN.search(project_name):
            raise InvalidProjectNameError(
                user_message='Project name contains invalid characters. Avoid: < > : " / \\ | ? *'
            )

        if project_name in {".", ".."}:
            raise InvalidProjectNameError(user_message="Please enter a valid project name.")

        # ADDED: trailing dot/space is invalid on Windows even though the
        # original character-class check did not catch it.
        if project_name != project_name.rstrip(" ."):
            raise InvalidProjectNameError(
                user_message="Windows does not allow project names ending in a space or a period."
            )

        # ADDED: Windows reserved device names (with or without an
        # extension) were not checked by the original validation.
        base_name = project_name.split(".")[0].upper()
        if base_name in _RESERVED_NAMES:
            raise InvalidProjectNameError(
                user_message=f"'{project_name}' is a reserved Windows name and can't be used."
            )

    def validate_location(self, location: Path) -> None:
        if not location or not str(location).strip():
            raise ToolkitError(user_message="Please choose where the project should be created.")
        if not location.exists():
            raise ToolkitError(user_message="The selected location does not exist.")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview(self, template_name: str, project_name: str) -> ProjectPreview:
        if not self.template_manager.exists(template_name):
            raise TemplateNotFoundError()

        display_name = project_name.strip() or "MyProject"
        folders = self.template_manager.get_folders(template_name)
        files = self.template_manager.get_files(template_name)

        lines = [f"{display_name}/"]
        for folder in folders:
            depth = len(folder.parts) - 1
            lines.append(f"{'    ' * depth}├── {folder.name}/")
        for file in files:
            depth = len(file.parts) - 1
            lines.append(f"{'    ' * depth}├── {file}")

        return ProjectPreview(
            project_name=display_name,
            template_name=template_name,
            folders=folders,
            files=files,
            tree_text="\n".join(lines),
        )

    # ------------------------------------------------------------------
    # Conflict detection (ADDED - see module docstring)
    # ------------------------------------------------------------------

    def find_conflicts(self, template_name: str, project_path: Path) -> list[Path]:
        """Relative paths of template files that would be overwritten if
        generation proceeds into an already-existing project_path."""
        if not project_path.exists():
            return []

        files = self.template_manager.get_files(template_name)
        return [f for f in files if (project_path / f).exists()]

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        template_name: str,
        project_name: str,
        location: Path,
        *,
        force_overwrite: bool = False,
        progress_callback=None,
    ) -> ProjectGenerationResult:
        self.validate_project_name(project_name)
        self.validate_location(location)

        if not self.template_manager.exists(template_name):
            raise TemplateNotFoundError()

        project_path = location / project_name

        if project_path.exists() and not force_overwrite:
            conflicts = self.find_conflicts(template_name, project_path)
            raise ProjectAlreadyExistsError(
                user_message=f"A folder named '{project_name}' already exists at this location.",
                technical_details=(
                    f"{len(conflicts)} file(s) would be overwritten: "
                    + ", ".join(str(c) for c in conflicts)
                    if conflicts
                    else "The folder exists but no template files would be overwritten."
                ),
            )

        template_path = self.template_manager.get_template_path(template_name)
        files = self.template_manager.get_files(template_name)
        folders = self.template_manager.get_folders(template_name)

        conflicts_before = set(self.find_conflicts(template_name, project_path))

        try:
            project_path.mkdir(parents=True, exist_ok=True)

            created_folders: list[Path] = []
            for folder in folders:
                dest = project_path / folder
                dest.mkdir(parents=True, exist_ok=True)
                created_folders.append(folder)

            created_files: list[Path] = []
            for index, relative_file in enumerate(files):
                if progress_callback:
                    progress_callback(f"Writing {relative_file} ({index + 1}/{len(files)})…")

                source_file = template_path / relative_file
                destination_file = project_path / relative_file
                destination_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    content = source_file.read_text(encoding="utf-8")
                    content = self.replace_variables(content, project_name, template_name)
                    destination_file.write_text(content, encoding="utf-8")
                except UnicodeDecodeError:
                    destination_file.write_bytes(source_file.read_bytes())

                created_files.append(relative_file)

            config_path = project_path / "config.json"
            config_data = {
                "project_name": project_name,
                "template": template_name,
                "version": "1.0.0",
            }
            config_path.write_text(json.dumps(config_data, indent=4), encoding="utf-8")
            if Path("config.json") not in created_files:
                created_files.append(Path("config.json"))

        except OSError as exc:
            raise ToolkitError(
                user_message="Could not create the project.",
                technical_details=str(exc),
            ) from exc

        logger.info("Generated project '%s' from template '%s' at %s", project_name, template_name, project_path)

        return ProjectGenerationResult(
            project_path=project_path,
            template_name=template_name,
            files_created=created_files,
            folders_created=created_folders,
            overwritten_files=sorted(conflicts_before),
        )

    @staticmethod
    def replace_variables(content: str, project_name: str, template_name: str) -> str:
        content = content.replace("{{PROJECT_NAME}}", project_name)
        content = content.replace("{{TEMPLATE}}", template_name)
        return content
