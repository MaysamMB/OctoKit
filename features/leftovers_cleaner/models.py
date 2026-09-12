"""Data models for the Application Leftovers Cleaner feature."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import Confidence


def _confidence_from_classification(classification: str) -> Confidence:
    return {
        "Safe": Confidence.SAFE,
        "Suspicious": Confidence.SUSPICIOUS,
    }.get(classification, Confidence.UNKNOWN)


@dataclass
class InstalledMatch:
    display_name: str
    publisher: str
    install_location: str | None

    @classmethod
    def from_json(cls, raw: dict) -> "InstalledMatch":
        return cls(
            display_name=raw.get("DisplayName") or "(unnamed)",
            publisher=raw.get("Publisher") or "",
            install_location=raw.get("InstallLocation") or None,
        )


@dataclass
class LeftoverCandidate:
    kind: str  # "Folder" | "Registry"
    path: str
    reason: str
    classification: Confidence
    name: str | None = None

    @classmethod
    def from_json(cls, raw: dict, kind: str) -> "LeftoverCandidate":
        return cls(
            kind=kind,
            path=raw.get("path", ""),
            reason=raw.get("reason", ""),
            classification=_confidence_from_classification(raw.get("classification", "")),
            name=raw.get("name"),
        )


@dataclass
class LeftoverScanResult:
    target_app_name: str
    still_installed: bool
    installed_matches: list[InstalledMatch] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    folders: list[LeftoverCandidate] = field(default_factory=list)
    registry: list[LeftoverCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scan_completed_at: str = ""

    @classmethod
    def from_json(cls, raw: dict) -> "LeftoverScanResult":
        candidates = raw.get("candidates") or {}
        return cls(
            target_app_name=raw.get("targetAppName", ""),
            still_installed=bool(raw.get("stillInstalled")),
            installed_matches=[InstalledMatch.from_json(m) for m in raw.get("installedMatches") or []],
            search_terms=list(raw.get("searchTerms") or []),
            folders=[LeftoverCandidate.from_json(c, "Folder") for c in candidates.get("folders") or []],
            registry=[LeftoverCandidate.from_json(c, "Registry") for c in candidates.get("registry") or []],
            warnings=list(raw.get("warnings") or []),
            scan_completed_at=raw.get("scanCompletedAt", ""),
        )

    @property
    def total_candidates(self) -> int:
        return len(self.folders) + len(self.registry)


@dataclass
class RejectedItem:
    kind: str
    path: str
    reason: str

    @classmethod
    def from_json(cls, raw: dict) -> "RejectedItem":
        return cls(kind=raw.get("type", ""), path=raw.get("path", ""), reason=raw.get("reason", ""))


@dataclass
class FailedItem:
    kind: str
    path: str
    reason: str

    @classmethod
    def from_json(cls, raw: dict) -> "FailedItem":
        return cls(kind=raw.get("type", ""), path=raw.get("path", ""), reason=raw.get("reason", ""))


@dataclass
class LeftoverDeleteResult:
    target_app_name: str
    aborted: bool
    abort_reason: str | None
    deleted_folders: list[str] = field(default_factory=list)
    deleted_registry: list[str] = field(default_factory=list)
    rejected: list[RejectedItem] = field(default_factory=list)
    failed: list[FailedItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    delete_completed_at: str = ""

    @classmethod
    def from_json(cls, raw: dict) -> "LeftoverDeleteResult":
        deleted = raw.get("deleted") or {}
        return cls(
            target_app_name=raw.get("targetAppName", ""),
            aborted=bool(raw.get("aborted")),
            abort_reason=raw.get("reason"),
            deleted_folders=list(deleted.get("folders") or []),
            deleted_registry=list(deleted.get("registry") or []),
            rejected=[RejectedItem.from_json(r) for r in raw.get("rejected") or []],
            failed=[FailedItem.from_json(f) for f in raw.get("failed") or []],
            warnings=list(raw.get("warnings") or []),
            delete_completed_at=raw.get("deleteCompletedAt", ""),
        )
