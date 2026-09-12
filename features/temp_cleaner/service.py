"""
Service layer for the Temporary Files Cleaner.

Scan and cleanup are always two separate calls into the script (spec
section 21/11) — nothing here ever deletes as a side effect of scanning.
"""

from __future__ import annotations

from core.exceptions import ToolkitError
from core.logger import get_logger
from core.powershell import PowerShellService
from features.temp_cleaner.models import TempCleanupResult, TempScanResult

logger = get_logger("features.temp_cleaner")

SCRIPT_NAME = "CleanTempFiles.ps1"


class TempCleanerService:
    def __init__(self, powershell: PowerShellService | None = None):
        self.powershell = powershell or PowerShellService()

    def scan(
        self,
        *,
        min_age_minutes: int = 120,
        include_recycle_bin: bool = True,
        timeout: float = 60,
        progress_callback=None,
        cancel_event=None,
    ) -> TempScanResult:
        if progress_callback:
            progress_callback("Scanning temporary file locations…")

        result = self.powershell.run(
            SCRIPT_NAME,
            [
                "-ScanOnly",
                "-OutputJson",
                "-MinAgeMinutes",
                str(min_age_minutes),
                "-IncludeRecycleBin",
                "true" if include_recycle_bin else "false",
            ],
            timeout=timeout,
            parse_json=True,
            cancel_event=cancel_event,
        )

        if not isinstance(result.data, dict) or not result.data.get("success"):
            raise ToolkitError(
                user_message="The temporary files scan did not complete successfully.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        return TempScanResult.from_json(result.data)

    def cleanup(
        self,
        *,
        min_age_minutes: int = 120,
        include_recycle_bin: bool = True,
        dry_run: bool = True,
        elevated: bool = False,
        timeout: float = 120,
        progress_callback=None,
        cancel_event=None,
    ) -> TempCleanupResult:
        if progress_callback:
            progress_callback(
                "Simulating cleanup (dry run)…" if dry_run else "Cleaning temporary files…"
            )

        args = [
            "-OutputJson",
            "-MinAgeMinutes",
            str(min_age_minutes),
            "-IncludeRecycleBin",
            "true" if include_recycle_bin else "false",
        ]
        if dry_run:
            args.append("-DryRun")

        result = self.powershell.run(
            SCRIPT_NAME,
            args,
            timeout=timeout,
            parse_json=True,
            elevated=elevated,
            cancel_event=cancel_event,
        )

        if not isinstance(result.data, dict) or not result.data.get("success"):
            raise ToolkitError(
                user_message="The cleanup could not be completed.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        return TempCleanupResult.from_json(result.data)

    @staticmethod
    def read_log_tail(log_path: str, max_lines: int = 200) -> str:
        from pathlib import Path

        path = Path(log_path)
        if not path.exists():
            return "No log file found yet."
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-max_lines:])
        except OSError as exc:
            return f"Could not read log file: {exc}"
