"""
Service layer for the Application Leftovers Cleaner - the highest-risk
feature in the application. See scripts/CleanAppLeftovers.ps1 for the full
rationale behind forking the original interactive script into non-
interactive Scan/Delete modes.

This service NEVER deletes anything on its own initiative: `delete()` only
ever runs with the exact, explicit item list the caller (the UI, after the
user has selected items and confirmed) passes in, and the script itself
re-validates every item again before touching it.
"""

from __future__ import annotations

from core.exceptions import ToolkitError
from core.logger import get_logger
from core.powershell import PowerShellService
from features.leftovers_cleaner.models import LeftoverDeleteResult, LeftoverScanResult

logger = get_logger("features.leftovers_cleaner")

SCRIPT_NAME = "CleanAppLeftovers.ps1"


class LeftoversService:
    def __init__(self, powershell: PowerShellService | None = None):
        self.powershell = powershell or PowerShellService()

    def scan(
        self, target_app_name: str, *, timeout: float = 60, progress_callback=None, cancel_event=None
    ) -> LeftoverScanResult:
        if not target_app_name or not target_app_name.strip():
            raise ToolkitError(user_message="Enter an application name to search for.")

        if progress_callback:
            progress_callback(f"Searching for leftovers of '{target_app_name}'…")

        result = self.powershell.run(
            SCRIPT_NAME,
            ["-TargetAppName", target_app_name, "-Mode", "Scan"],
            timeout=timeout,
            parse_json=True,
            cancel_event=cancel_event,
        )

        if not isinstance(result.data, dict) or not result.data.get("success"):
            raise ToolkitError(
                user_message="The leftovers scan did not complete successfully.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        return LeftoverScanResult.from_json(result.data)

    def delete(
        self,
        target_app_name: str,
        *,
        approved_folders: list[str] | None = None,
        approved_registry: list[str] | None = None,
        elevated: bool = False,
        timeout: float = 90,
        progress_callback=None,
        cancel_event=None,
    ) -> LeftoverDeleteResult:
        approved_folders = approved_folders or []
        approved_registry = approved_registry or []

        if not approved_folders and not approved_registry:
            raise ToolkitError(user_message="No items were selected for deletion.")

        if progress_callback:
            progress_callback("Deleting selected leftovers…")

        items_path = self.powershell.write_json_temp_file(
            {"folders": approved_folders, "registry": approved_registry}
        )
        try:
            result = self.powershell.run(
                SCRIPT_NAME,
                [
                    "-TargetAppName",
                    target_app_name,
                    "-Mode",
                    "Delete",
                    "-ItemsFile",
                    str(items_path),
                ],
                timeout=timeout,
                parse_json=True,
                elevated=elevated,
                cancel_event=cancel_event,
            )
        finally:
            items_path.unlink(missing_ok=True)

        if not isinstance(result.data, dict):
            raise ToolkitError(
                user_message="The deletion could not be completed.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        if not result.data.get("success") and not result.data.get("aborted"):
            raise ToolkitError(
                user_message="The deletion could not be completed.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        return LeftoverDeleteResult.from_json(result.data)
