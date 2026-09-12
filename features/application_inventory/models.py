"""Data models for the (read-only) Application Inventory feature."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApplicationInfo:
    name: str
    publisher: str
    install_date: str | None
    install_location: str | None
    install_location_exists: bool
    uninstall_string: str | None
    uninstaller_exists: bool
    display_icon: str | None
    icon_exists: bool
    status: str
    type: str
    registry_path: str

    @classmethod
    def from_json(cls, raw: dict) -> "ApplicationInfo":
        return cls(
            name=raw.get("Name") or "(unnamed)",
            publisher=raw.get("Publisher") or "",
            install_date=raw.get("InstallDate"),
            install_location=raw.get("InstallLocation") or None,
            install_location_exists=bool(raw.get("InstallLocationExists")),
            uninstall_string=raw.get("UninstallString") or None,
            uninstaller_exists=bool(raw.get("UninstallerExists")),
            display_icon=raw.get("DisplayIcon") or None,
            icon_exists=bool(raw.get("IconExists")),
            status=raw.get("Status") or "Unknown",
            type=raw.get("Type") or "Application",
            registry_path=raw.get("RegistryPath") or "",
        )


@dataclass
class BrokenRegistration:
    name: str
    publisher: str
    install_location: str | None

    @classmethod
    def from_json(cls, raw: dict) -> "BrokenRegistration":
        return cls(
            name=raw.get("Name") or "(unnamed)",
            publisher=raw.get("Publisher") or "",
            install_location=raw.get("InstallLocation") or None,
        )


@dataclass
class OrphanedRegistryEntry:
    application: str
    publisher: str
    installed: str | None
    confidence: str
    reason: str
    registry: str

    @classmethod
    def from_json(cls, raw: dict) -> "OrphanedRegistryEntry":
        return cls(
            application=raw.get("Application") or "(unnamed)",
            publisher=raw.get("Publisher") or "",
            installed=raw.get("Installed"),
            confidence=raw.get("Confidence") or "MEDIUM",
            reason=raw.get("Reason") or "",
            registry=raw.get("Registry") or "",
        )


@dataclass
class PossibleOldFolder:
    application: str
    folder: str
    path: str
    modified: str | None
    confidence: str
    reason: str

    @classmethod
    def from_json(cls, raw: dict) -> "PossibleOldFolder":
        return cls(
            application=raw.get("Application") or "(unnamed)",
            folder=raw.get("Folder") or "",
            path=raw.get("Path") or "",
            modified=raw.get("Modified"),
            confidence=raw.get("Confidence") or "LOW",
            reason=raw.get("Reason") or "",
        )


@dataclass
class InventoryResult:
    total_applications: int
    broken_registrations_count: int
    orphaned_registry_count: int
    old_folders_count: int
    scan_completed_at: str
    applications: list[ApplicationInfo] = field(default_factory=list)
    broken_registrations: list[BrokenRegistration] = field(default_factory=list)
    orphaned_registry: list[OrphanedRegistryEntry] = field(default_factory=list)
    possible_old_folders: list[PossibleOldFolder] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, raw: dict) -> "InventoryResult":
        summary = raw.get("summary") or {}
        return cls(
            total_applications=summary.get("TotalApplications", 0),
            broken_registrations_count=summary.get("BrokenRegistrations", 0),
            orphaned_registry_count=summary.get("PossibleOrphanedRegistryEntries", 0),
            old_folders_count=summary.get("PossibleOldApplicationFolders", 0),
            scan_completed_at=summary.get("ScanCompletedAt", ""),
            applications=[ApplicationInfo.from_json(a) for a in raw.get("applications") or []],
            broken_registrations=[
                BrokenRegistration.from_json(a) for a in raw.get("brokenRegistrations") or []
            ],
            orphaned_registry=[
                OrphanedRegistryEntry.from_json(a) for a in raw.get("orphanedRegistry") or []
            ],
            possible_old_folders=[
                PossibleOldFolder.from_json(a) for a in raw.get("possibleOldFolders") or []
            ],
        )
