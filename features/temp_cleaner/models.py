"""Data models for the Temporary Files Cleaner feature."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TargetScanInfo:
    path: str
    requires_admin: bool
    skipped_admin: bool
    processed: bool
    files_eligible: int
    folders_eligible: int
    bytes_eligible: int
    too_new: int
    error: str | None

    @classmethod
    def from_json(cls, raw: dict) -> "TargetScanInfo":
        return cls(
            path=raw.get("path", ""),
            requires_admin=bool(raw.get("requiresAdmin")),
            skipped_admin=bool(raw.get("skippedAdmin")),
            processed=bool(raw.get("processed")),
            files_eligible=raw.get("filesEligible", 0),
            folders_eligible=raw.get("foldersEligible", 0),
            bytes_eligible=raw.get("bytesEligible", 0),
            too_new=raw.get("tooNew", 0),
            error=raw.get("error"),
        )


@dataclass
class TargetCleanupInfo:
    path: str
    requires_admin: bool
    skipped_admin: bool
    processed: bool
    files_deleted: int
    folders_deleted: int
    bytes_deleted: int
    skipped_locked: int
    too_new: int
    error: str | None

    @classmethod
    def from_json(cls, raw: dict) -> "TargetCleanupInfo":
        return cls(
            path=raw.get("path", ""),
            requires_admin=bool(raw.get("requiresAdmin")),
            skipped_admin=bool(raw.get("skippedAdmin")),
            processed=bool(raw.get("processed")),
            files_deleted=raw.get("filesDeleted", 0),
            folders_deleted=raw.get("foldersDeleted", 0),
            bytes_deleted=raw.get("bytesDeleted", 0),
            skipped_locked=raw.get("skippedLocked", 0),
            too_new=raw.get("tooNew", 0),
            error=raw.get("error"),
        )


@dataclass
class RecycleBinScanInfo:
    included: bool
    item_count: int | None
    estimated_bytes: int | None
    estimate_available: bool

    @classmethod
    def from_json(cls, raw: dict) -> "RecycleBinScanInfo":
        return cls(
            included=bool(raw.get("included")),
            item_count=raw.get("itemCount"),
            estimated_bytes=raw.get("estimatedBytes"),
            estimate_available=bool(raw.get("estimateAvailable")),
        )


@dataclass
class RecycleBinCleanupInfo:
    included: bool
    emptied: bool
    estimated_bytes_before: int | None
    error: str | None

    @classmethod
    def from_json(cls, raw: dict) -> "RecycleBinCleanupInfo":
        return cls(
            included=bool(raw.get("included")),
            emptied=bool(raw.get("emptied")),
            estimated_bytes_before=raw.get("estimatedBytesBefore"),
            error=raw.get("error"),
        )


@dataclass
class TempScanResult:
    is_admin: bool
    min_age_minutes: int
    include_recycle_bin: bool
    targets: list[TargetScanInfo]
    recycle_bin: RecycleBinScanInfo
    total_files: int
    total_folders: int
    total_bytes: int
    total_too_new: int
    log_file: str
    scan_completed_at: str

    @classmethod
    def from_json(cls, raw: dict) -> "TempScanResult":
        totals = raw.get("totals") or {}
        return cls(
            is_admin=bool(raw.get("isAdmin")),
            min_age_minutes=raw.get("minAgeMinutes", 0),
            include_recycle_bin=bool(raw.get("includeRecycleBin")),
            targets=[TargetScanInfo.from_json(t) for t in raw.get("targets") or []],
            recycle_bin=RecycleBinScanInfo.from_json(raw.get("recycleBin") or {}),
            total_files=totals.get("filesEligible", 0),
            total_folders=totals.get("foldersEligible", 0),
            total_bytes=totals.get("bytesEligible", 0),
            total_too_new=totals.get("tooNew", 0),
            log_file=raw.get("logFile", ""),
            scan_completed_at=raw.get("scanCompletedAt", ""),
        )


@dataclass
class TempCleanupResult:
    dry_run: bool
    is_admin: bool
    min_age_minutes: int
    include_recycle_bin: bool
    targets: list[TargetCleanupInfo]
    recycle_bin: RecycleBinCleanupInfo
    total_files: int
    total_folders: int
    total_bytes: int
    total_skipped_locked: int
    total_too_new: int
    log_file: str
    cleanup_completed_at: str

    @classmethod
    def from_json(cls, raw: dict) -> "TempCleanupResult":
        totals = raw.get("totals") or {}
        return cls(
            dry_run=bool(raw.get("dryRun")),
            is_admin=bool(raw.get("isAdmin")),
            min_age_minutes=raw.get("minAgeMinutes", 0),
            include_recycle_bin=bool(raw.get("includeRecycleBin")),
            targets=[TargetCleanupInfo.from_json(t) for t in raw.get("targets") or []],
            recycle_bin=RecycleBinCleanupInfo.from_json(raw.get("recycleBin") or {}),
            total_files=totals.get("filesDeleted", 0),
            total_folders=totals.get("foldersDeleted", 0),
            total_bytes=totals.get("bytesDeleted", 0),
            total_skipped_locked=totals.get("skippedLocked", 0),
            total_too_new=totals.get("tooNew", 0),
            log_file=raw.get("logFile", ""),
            cleanup_completed_at=raw.get("cleanupCompletedAt", ""),
        )
