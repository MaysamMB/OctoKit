from unittest.mock import MagicMock

import pytest

from core.exceptions import ToolkitError
from core.models import PowerShellResult
from features.application_inventory.service import InventoryService

SAMPLE_JSON = {
    "success": True,
    "readOnly": True,
    "summary": {
        "TotalApplications": 2,
        "BrokenRegistrations": 1,
        "PossibleOrphanedRegistryEntries": 1,
        "PossibleOldApplicationFolders": 0,
        "ScanCompletedAt": "2026-08-22 10:00:00",
    },
    "applications": [
        {
            "Name": "Good App",
            "Publisher": "Acme",
            "InstallLocation": r"C:\Program Files\GoodApp",
            "InstallLocationExists": True,
            "Status": "Installed",
            "Type": "Application",
            "UninstallerExists": True,
            "RegistryPath": "HKLM:\\...\\GoodApp",
        },
        {
            "Name": "Ghost App",
            "Publisher": "Acme",
            "InstallLocation": r"C:\Program Files\GhostApp",
            "InstallLocationExists": False,
            "Status": "Possible Broken Registration",
            "Type": "Application",
            "UninstallerExists": False,
            "RegistryPath": "HKLM:\\...\\GhostApp",
        },
    ],
    "brokenRegistrations": [{"Name": "Ghost App", "Publisher": "Acme", "InstallLocation": r"C:\Program Files\GhostApp"}],
    "orphanedRegistry": [
        {
            "Application": "Ghost App",
            "Publisher": "Acme",
            "Confidence": "MEDIUM",
            "Reason": "Registered installation location does not exist",
            "Registry": "HKLM:\\...\\GhostApp",
        }
    ],
    "possibleOldFolders": [],
}


def _mock_powershell(data, stderr=""):
    ps = MagicMock()
    ps.run.return_value = PowerShellResult(success=True, exit_code=0, stdout="", stderr=stderr, data=data)
    return ps


def test_scan_parses_result_correctly():
    service = InventoryService(powershell=_mock_powershell(SAMPLE_JSON))
    result = service.scan()

    assert result.total_applications == 2
    assert result.broken_registrations_count == 1
    assert len(result.applications) == 2
    assert result.applications[1].status == "Possible Broken Registration"
    assert result.warnings == []


def test_scan_calls_script_with_output_json_flag():
    ps = _mock_powershell(SAMPLE_JSON)
    service = InventoryService(powershell=ps)
    service.scan()
    args, kwargs = ps.run.call_args
    assert args[0] == "OldApplicationsInventory.ps1"
    assert "-OutputJson" in args[1]


def test_scan_raises_on_success_false():
    service = InventoryService(powershell=_mock_powershell({"success": False}))
    with pytest.raises(ToolkitError):
        service.scan()


def test_scan_raises_if_not_read_only():
    payload = dict(SAMPLE_JSON)
    payload["readOnly"] = False
    service = InventoryService(powershell=_mock_powershell(payload))
    with pytest.raises(ToolkitError):
        service.scan()


def test_scan_surfaces_stderr_as_warning():
    service = InventoryService(powershell=_mock_powershell(SAMPLE_JSON, stderr="Access denied to some key"))
    result = service.scan()
    assert result.warnings  # a warning must be surfaced, not silently dropped


def test_export_json_and_csv(tmp_path):
    service = InventoryService(powershell=_mock_powershell(SAMPLE_JSON))
    result = service.scan()

    json_path = tmp_path / "out.json"
    csv_path = tmp_path / "out.csv"
    InventoryService.export_json(result, json_path)
    InventoryService.export_csv(result, csv_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert "Ghost App" in csv_path.read_text(encoding="utf-8")
