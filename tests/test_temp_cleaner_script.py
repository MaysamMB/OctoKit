"""
Functional tests that actually execute CleanTempFiles.ps1 with real
PowerShell (skipped if pwsh/powershell isn't available in this
environment). Windows-only APIs used by the script (WindowsIdentity for
admin detection, Clear-RecycleBin, the Shell.Application COM object for
Recycle Bin size estimation) are already wrapped in try/catch in the
script itself and degrade gracefully off-Windows, so the core added logic
(age-cutoff scanning, safe-root validation, file/folder/byte counting,
dry-run behavior) can be exercised end-to-end here even outside Windows.

This does NOT substitute for running the script on a real Windows machine
before shipping — only for verifying the logic this project added.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "CleanTempFiles.ps1"


def _find_powershell() -> str | None:
    for candidate in ("pwsh", "powershell"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


PWSH = _find_powershell()
pytestmark = pytest.mark.skipif(PWSH is None, reason="pwsh/powershell not available in this environment")


def _age_file(path: Path, minutes_old: int) -> None:
    past = time.time() - minutes_old * 60
    os.utime(path, (past, past))


@pytest.fixture
def temp_area(tmp_path):
    temp_root = tmp_path / "fake_temp"
    temp_root.mkdir()

    old_file = temp_root / "old_file.txt"
    old_file.write_text("stale data")
    _age_file(old_file, minutes_old=300)

    new_file = temp_root / "new_file.txt"
    new_file.write_text("fresh data")
    # leave at current mtime (too new to touch)

    old_folder = temp_root / "old_folder"
    old_folder.mkdir()
    (old_folder / "nested.txt").write_text("x" * 1024)
    _age_file(old_folder / "nested.txt", minutes_old=300)
    _age_file(old_folder, minutes_old=300)

    cwd = tmp_path / "run_cwd"
    cwd.mkdir()

    return temp_root, cwd


def _run(temp_root: Path, cwd: Path, extra_args: list[str]) -> dict:
    env = dict(os.environ)
    env["TEMP"] = str(temp_root)
    env["TMP"] = str(temp_root)

    args = [
        PWSH,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        *extra_args,
    ]
    result = subprocess.run(
        args, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    return json.loads(result.stdout.strip())


def test_scan_only_never_deletes(temp_area):
    temp_root, cwd = temp_area
    data = _run(
        temp_root,
        cwd,
        ["-ScanOnly", "-OutputJson", "-MinAgeMinutes", "60", "-IncludeRecycleBin", "false"],
    )

    assert data["mode"] == "scan"
    assert data["readOnly"] is True

    user_target = next(t for t in data["targets"] if not t["requiresAdmin"])
    assert user_target["filesEligible"] == 1  # old_file.txt only
    assert user_target["foldersEligible"] == 1  # old_folder
    assert user_target["tooNew"] == 1  # new_file.txt
    assert user_target["bytesEligible"] >= 1024

    # Nothing should have been touched.
    assert (temp_root / "old_file.txt").exists()
    assert (temp_root / "old_folder").exists()
    assert (temp_root / "new_file.txt").exists()


def test_cleanup_deletes_only_old_items(temp_area):
    temp_root, cwd = temp_area
    data = _run(
        temp_root,
        cwd,
        ["-OutputJson", "-MinAgeMinutes", "60", "-IncludeRecycleBin", "false"],
    )

    assert data["mode"] == "cleanup"
    assert data["dryRun"] is False

    assert not (temp_root / "old_file.txt").exists()
    assert not (temp_root / "old_folder").exists()
    assert (temp_root / "new_file.txt").exists()  # too new, must survive

    user_target = next(t for t in data["targets"] if not t["requiresAdmin"])
    assert user_target["filesDeleted"] == 1
    assert user_target["foldersDeleted"] == 1
    assert user_target["tooNew"] == 1


def test_dry_run_deletes_nothing(temp_area):
    temp_root, cwd = temp_area
    data = _run(
        temp_root,
        cwd,
        ["-DryRun", "-OutputJson", "-MinAgeMinutes", "60", "-IncludeRecycleBin", "false"],
    )

    assert data["dryRun"] is True
    # DryRun cleanup path still reports what WOULD be deleted...
    user_target = next(t for t in data["targets"] if not t["requiresAdmin"])
    assert user_target["filesDeleted"] == 1
    assert user_target["foldersDeleted"] == 1
    # ...but nothing is actually removed.
    assert (temp_root / "old_file.txt").exists()
    assert (temp_root / "old_folder").exists()


def test_admin_required_target_is_skipped_gracefully(temp_area):
    temp_root, cwd = temp_area
    data = _run(
        temp_root,
        cwd,
        ["-ScanOnly", "-OutputJson", "-MinAgeMinutes", "60", "-IncludeRecycleBin", "false"],
    )
    admin_target = next(t for t in data["targets"] if t["requiresAdmin"])
    assert admin_target["skippedAdmin"] is True
