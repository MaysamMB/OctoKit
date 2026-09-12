import json
import shutil
from unittest.mock import MagicMock

import pytest

from core.exceptions import ToolkitError
from core.models import PowerShellResult
from core.powershell import PowerShellService
from features.leftovers_cleaner.service import LeftoversService

SCAN_JSON = {
    "success": True,
    "targetAppName": "TestApp",
    "stillInstalled": False,
    "installedMatches": [],
    "searchTerms": ["TestApp", "testapp"],
    "candidates": {
        "folders": [
            {"path": r"C:\Users\x\AppData\Local\TestApp", "classification": "Safe", "reason": "exact"},
            {"path": r"C:\Users\x\AppData\Local\MyTestAppBackup", "classification": "Suspicious", "reason": "contains"},
        ],
        "registry": [],
    },
    "warnings": [],
    "scanCompletedAt": "2026-08-22 10:00:00",
}

STILL_INSTALLED_JSON = {
    "success": True,
    "targetAppName": "TestApp",
    "stillInstalled": True,
    "installedMatches": [{"DisplayName": "TestApp", "Publisher": "Acme", "InstallLocation": r"C:\Program Files\TestApp"}],
    "candidates": {"folders": [], "registry": []},
    "warnings": [],
    "scanCompletedAt": "2026-08-22 10:00:00",
}


def _mock_ps(data):
    ps = MagicMock()
    ps.run.return_value = PowerShellResult(success=True, exit_code=0, stdout="", stderr="", data=data)
    ps.write_json_temp_file.side_effect = PowerShellService.write_json_temp_file
    return ps


def test_scan_requires_nonempty_name():
    service = LeftoversService(powershell=_mock_ps(SCAN_JSON))
    with pytest.raises(ToolkitError):
        service.scan("   ")


def test_scan_parses_candidates_with_classification():
    service = LeftoversService(powershell=_mock_ps(SCAN_JSON))
    result = service.scan("TestApp")
    assert result.still_installed is False
    assert len(result.folders) == 2
    safe = [f for f in result.folders if f.classification.value == "Safe / Recommended"]
    assert len(safe) == 1


def test_scan_surfaces_still_installed_without_raising():
    service = LeftoversService(powershell=_mock_ps(STILL_INSTALLED_JSON))
    result = service.scan("TestApp")
    assert result.still_installed is True
    assert result.installed_matches[0].display_name == "TestApp"
    assert result.folders == []


def test_delete_requires_at_least_one_item():
    service = LeftoversService(powershell=_mock_ps(SCAN_JSON))
    with pytest.raises(ToolkitError):
        service.delete("TestApp")


def test_delete_writes_items_file_and_cleans_up():
    ps = _mock_ps(
        {
            "success": True,
            "targetAppName": "TestApp",
            "aborted": False,
            "deleted": {"folders": [r"C:\x\TestApp"], "registry": []},
            "rejected": [],
            "failed": [],
            "warnings": [],
            "deleteCompletedAt": "2026-08-22 10:05:00",
        }
    )
    service = LeftoversService(powershell=ps)
    result = service.delete("TestApp", approved_folders=[r"C:\x\TestApp"])

    assert result.deleted_folders == [r"C:\x\TestApp"]

    # The temp items file passed to run() must have been written with the
    # right content, and cleaned up afterward.
    args, kwargs = ps.run.call_args
    items_file_index = args[1].index("-ItemsFile") + 1
    items_file_path = args[1][items_file_index]
    from pathlib import Path

    assert not Path(items_file_path).exists()  # cleaned up


def test_delete_surfaces_abort_without_raising():
    ps = _mock_ps(
        {
            "success": False,
            "targetAppName": "TestApp",
            "aborted": True,
            "reason": "The application now appears to be installed.",
            "installedMatches": [],
        }
    )
    service = LeftoversService(powershell=ps)
    result = service.delete("TestApp", approved_folders=[r"C:\x\TestApp"])
    assert result.aborted is True


def test_delete_passes_elevated_flag():
    ps = _mock_ps(
        {
            "success": True,
            "targetAppName": "TestApp",
            "aborted": False,
            "deleted": {"folders": [], "registry": [r"HK...\TestApp"]},
            "rejected": [],
            "failed": [],
            "warnings": [],
            "deleteCompletedAt": "x",
        }
    )
    service = LeftoversService(powershell=ps)
    service.delete("TestApp", approved_registry=[r"HK...\TestApp"], elevated=True)
    _, kwargs = ps.run.call_args
    assert kwargs["elevated"] is True


# ---------------------------------------------------------------------------
# Real end-to-end integration through the actual PowerShellService + script.
# ---------------------------------------------------------------------------

PWSH = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(PWSH is None, reason="pwsh not available")
def test_real_scan_and_delete_end_to_end(tmp_path, monkeypatch):
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    localappdata = tmp_path / "localappdata"
    localappdata.mkdir()
    (localappdata / "RealTestApp").mkdir()

    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("APPDATA", str(tmp_path / "nope"))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "nope2"))

    ps_service = PowerShellService(scripts_dir=scripts_dir)
    service = LeftoversService(powershell=ps_service)

    scan_result = service.scan("RealTestApp")
    assert scan_result.still_installed is False
    assert len(scan_result.folders) == 1

    delete_result = service.delete(
        "RealTestApp", approved_folders=[scan_result.folders[0].path]
    )
    assert delete_result.deleted_folders == [scan_result.folders[0].path]
    assert not (localappdata / "RealTestApp").exists()
