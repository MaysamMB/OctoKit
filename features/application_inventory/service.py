"""
Service layer for the Application Inventory feature.

This feature is, and must remain, strictly READ-ONLY. This module never
imports anything capable of writing to the registry or filesystem, and the
underlying script (`OldApplicationsInventory.ps1`) is used completely
unmodified — it was already a correct fit for GUI consumption (JSON output,
no destructive calls of any kind, confirmed by full source inspection).
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from core.exceptions import ToolkitError
from core.logger import get_logger
from core.powershell import PowerShellService
from features.application_inventory.models import InventoryResult

logger = get_logger("features.application_inventory")

SCRIPT_NAME = "OldApplicationsInventory.ps1"


class InventoryService:
    def __init__(self, powershell: PowerShellService | None = None):
        self.powershell = powershell or PowerShellService()

    def scan(self, *, timeout: float = 60, progress_callback=None, cancel_event=None) -> InventoryResult:
        if progress_callback:
            progress_callback("Reading installed application registrations…")

        result = self.powershell.run(
            SCRIPT_NAME,
            ["-OutputJson"],
            timeout=timeout,
            parse_json=True,
            cancel_event=cancel_event,
        )

        if not isinstance(result.data, dict) or not result.data.get("success"):
            raise ToolkitError(
                user_message="The application inventory scan did not complete successfully.",
                technical_details=result.stdout + "\n" + result.stderr,
            )

        if not result.data.get("readOnly", True):
            # Defensive check: if the script's own contract ever changes to
            # claim it is no longer read-only, refuse to trust the result
            # rather than silently presenting it as safe.
            raise ToolkitError(
                user_message="The inventory script no longer reports itself as read-only; "
                "refusing to display results until this is verified.",
            )

        inventory = InventoryResult.from_json(result.data)

        if result.stderr.strip():
            inventory.warnings.append(
                "PowerShell reported diagnostic output during the scan. Some registry "
                "locations may not have been fully readable. See technical details in "
                "the logs for the raw message."
            )
            logger.warning("Inventory scan produced stderr output: %s", result.stderr[:500])

        return inventory

    @staticmethod
    def export_json(result: InventoryResult, path: Path) -> None:
        payload = {
            "summary": {
                "totalApplications": result.total_applications,
                "brokenRegistrations": result.broken_registrations_count,
                "orphanedRegistryEntries": result.orphaned_registry_count,
                "possibleOldFolders": result.old_folders_count,
                "scanCompletedAt": result.scan_completed_at,
            },
            "applications": [asdict(a) for a in result.applications],
            "brokenRegistrations": [asdict(a) for a in result.broken_registrations],
            "orphanedRegistry": [asdict(a) for a in result.orphaned_registry],
            "possibleOldFolders": [asdict(a) for a in result.possible_old_folders],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def export_csv(result: InventoryResult, path: Path) -> None:
        fieldnames = [
            "name",
            "publisher",
            "install_date",
            "install_location",
            "install_location_exists",
            "status",
            "type",
            "uninstaller_exists",
        ]
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for app in result.applications:
                writer.writerow(asdict(app))
