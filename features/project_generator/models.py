"""Data models for the Project Generator feature."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectPreview:
    project_name: str
    template_name: str
    folders: list[Path] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    tree_text: str = ""

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def folder_count(self) -> int:
        return len(self.folders)


@dataclass
class ConflictInfo:
    project_path: Path
    conflicting_files: list[Path] = field(default_factory=list)


@dataclass
class ProjectGenerationResult:
    project_path: Path
    template_name: str
    files_created: list[Path] = field(default_factory=list)
    folders_created: list[Path] = field(default_factory=list)
    overwritten_files: list[Path] = field(default_factory=list)
