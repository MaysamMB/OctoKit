import os
import shutil
import time
from unittest.mock import MagicMock

import pytest

from core.exceptions import ToolkitError
from core.models import PowerShellResult
from core.powershell import PowerShellService
from features.temp_cleaner.service import TempCleanerService

SAMPLE_SCAN_JSON = {
    "success": True,
    "mode": "scan",
    "readOnly": True,
    "isAdmin": False,
    "minAgeMinutes": 120,
    "includeRecycleBin": True,
    "targets": [
        {
            "path": "/tmp/x",
            "requiresAdmin": False,
            "skippedAdmin": False,
            "processed": True,
            "filesEligible": 3,
            "foldersEligible": 1,
            "bytesEligible": 4096,
            "tooNew": 2,
            "error": None,
        }
    ],
    "recycleBin": {"included": True, "itemCount": 5, "estimatedBytes": 2048, "estimateAvailable": True},
    "totals": {"filesEligible": 3, "foldersEligible": 1, "bytesEligible": 6144, "tooNew": 2},
    "logFile": "C:\\ProgramData\\AutoTempCleaner\\cleanup.log",
    "scanCompletedAt": "2026-08-22 10:00:00",
}


def _mock_powershell(data):
    ps = MagicMock()
    ps.run.return_value = PowerShellResult(success=True, exit_code=0, stdout="", stderr="", data=data)
    return ps


def test_scan_builds_correct_arguments():
    ps = _mock_powershell(SAMPLE_SCAN_JSON)
    service = TempCleanerService(powershell=ps)
    service.scan(min_age_minutes=30, include_recycle_bin=False)

    args, kwargs = ps.run.call_args
    assert args[0] == "CleanTempFiles.ps1"
    call_args = args[1]
    assert "-ScanOnly" in call_args
    assert "-OutputJson" in call_args
    assert "30" in call_args
    assert "false" in call_args  # IncludeRecycleBin value, not "$false"


def test_scan_parses_result():
    service = TempCleanerService(powershell=_mock_powershell(SAMPLE_SCAN_JSON))
    result = service.scan()
    assert result.total_files == 3
    assert result.total_bytes == 6144
    assert result.recycle_bin.item_count == 5


def test_scan_raises_on_failure():
    service = TempCleanerService(powershell=_mock_powershell({"success": False}))
    with pytest.raises(ToolkitError):
        service.scan()


def test_cleanup_passes_dry_run_flag():
    ps = _mock_powershell({**SAMPLE_SCAN_JSON, "mode": "cleanup", "dryRun": True})
    service = TempCleanerService(powershell=ps)
    service.cleanup(dry_run=True)
    args, kwargs = ps.run.call_args
    assert "-DryRun" in args[1]


def test_cleanup_omits_dry_run_flag_when_false():
    ps = _mock_powershell({**SAMPLE_SCAN_JSON, "mode": "cleanup", "dryRun": False})
    service = TempCleanerService(powershell=ps)
    service.cleanup(dry_run=False)
    args, kwargs = ps.run.call_args
    assert "-DryRun" not in args[1]


def test_cleanup_requests_elevation_when_asked():
    ps = _mock_powershell({**SAMPLE_SCAN_JSON, "mode": "cleanup", "dryRun": False})
    service = TempCleanerService(powershell=ps)
    service.cleanup(dry_run=False, elevated=True)
    _, kwargs = ps.run.call_args
    assert kwargs["elevated"] is True


def test_read_log_tail_handles_missing_file(tmp_path):
    missing = tmp_path / "nope.log"
    text = TempCleanerService.read_log_tail(str(missing))
    assert "No log file" in text


def test_read_log_tail_returns_last_lines(tmp_path):
    log = tmp_path / "cleanup.log"
    log.write_text("\n".join(f"line {i}" for i in range(500)), encoding="utf-8")
    text = TempCleanerService.read_log_tail(str(log), max_lines=10)
    assert text.splitlines() == [f"line {i}" for i in range(490, 500)]


# ---------------------------------------------------------------------------
# Real end-to-end integration through the actual PowerShellService + script,
# skipped when pwsh/powershell is unavailable.
# ---------------------------------------------------------------------------

PWSH = shutil.which("pwsh") or shutil.which("powershell")
pytestmark_integration = pytest.mark.skipif(PWSH is None, reason="pwsh not available")


@pytest.mark.skipif(PWSH is None, reason="pwsh not available")
def test_real_scan_end_to_end(tmp_path, monkeypatch):
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    fake_temp = tmp_path / "temp"
    fake_temp.mkdir()
    old_file = fake_temp / "old.txt"
    old_file.write_text("data")
    past = time.time() - 300 * 60
    os.utime(old_file, (past, past))

    monkeypatch.setenv("TEMP", str(fake_temp))
    monkeypatch.setenv("TMP", str(fake_temp))

    ps_service = PowerShellService(scripts_dir=scripts_dir)
    service = TempCleanerService(powershell=ps_service)
    result = service.scan(min_age_minutes=60, include_recycle_bin=False)

    user_target = next(t for t in result.targets if not t.requires_admin)
    assert user_target.files_eligible == 1
