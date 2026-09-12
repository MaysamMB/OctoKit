"""
Functional tests that execute CleanAppLeftovers.ps1 with real PowerShell.
Registry operations can't be exercised end-to-end on this (non-Windows)
test environment (no HKLM:/HKCU: provider), so the registry-specific safety
logic (Test-SafeRegistryLeaf, and matching quality) is verified by
dot-sourcing just the function definitions and calling them directly with
crafted PSPath-shaped strings - the same technique used to validate
Clear-FolderContents' helpers in test_temp_cleaner_script.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "CleanAppLeftovers.ps1"
PWSH = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(PWSH is None, reason="pwsh/powershell not available in this environment")


def _run(target_app: str, mode: str, env: dict, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    args = [
        PWSH,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-TargetAppName",
        target_app,
        "-Mode",
        mode,
        *(extra_args or []),
    ]
    full_env = dict(os.environ)
    full_env.update(env)
    result = subprocess.run(args, env=full_env, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout.strip(), result.stderr


@pytest.fixture
def fake_app_dirs(tmp_path):
    localappdata = tmp_path / "localappdata"
    localappdata.mkdir()
    (localappdata / "TestApp").mkdir()
    (localappdata / "MyTestAppBackup").mkdir()
    (localappdata / "Unrelated").mkdir()

    env = {
        "LOCALAPPDATA": str(localappdata),
        "APPDATA": str(tmp_path / "no_appdata"),
        "PROGRAMDATA": str(tmp_path / "no_programdata"),
    }
    return localappdata, env


def test_scan_classifies_exact_and_containment_matches(fake_app_dirs):
    localappdata, env = fake_app_dirs
    code, stdout, stderr = _run("TestApp", "Scan", env)
    assert code == 0, stderr
    data = json.loads(stdout)

    assert data["success"] is True
    assert data["stillInstalled"] is False

    by_path = {c["path"]: c for c in data["candidates"]["folders"]}
    exact = by_path[str(localappdata / "TestApp")]
    containment = by_path[str(localappdata / "MyTestAppBackup")]

    assert exact["classification"] == "Safe"
    assert containment["classification"] == "Suspicious"
    assert str(localappdata / "Unrelated") not in by_path


def test_scan_never_deletes_anything(fake_app_dirs):
    localappdata, env = fake_app_dirs
    _run("TestApp", "Scan", env)
    assert (localappdata / "TestApp").exists()
    assert (localappdata / "MyTestAppBackup").exists()
    assert (localappdata / "Unrelated").exists()


def test_delete_only_removes_approved_and_revalidated_items(fake_app_dirs, tmp_path):
    localappdata, env = fake_app_dirs
    items_file = tmp_path / "approved.json"
    items_file.write_text(
        json.dumps(
            {
                "folders": [
                    str(localappdata / "TestApp"),  # matches -> should be deleted
                    str(localappdata / "Unrelated"),  # does not match -> must be rejected
                ],
                "registry": [],
            }
        )
    )

    code, stdout, stderr = _run("TestApp", "Delete", env, ["-ItemsFile", str(items_file)])
    assert code == 0, stderr
    data = json.loads(stdout)

    assert data["success"] is True
    assert data["deleted"]["folders"] == [str(localappdata / "TestApp")]
    assert not (localappdata / "TestApp").exists()

    assert (localappdata / "Unrelated").exists()  # must survive
    rejected_paths = {r["path"]: r["reason"] for r in data["rejected"]}
    assert str(localappdata / "Unrelated") in rejected_paths


def test_delete_rejects_paths_that_fail_safe_path_check(fake_app_dirs, tmp_path, monkeypatch):
    localappdata, env = fake_app_dirs
    # Point APPDATA itself at a folder literally named to match the app,
    # then try to get the script to delete APPDATA outright - Test-SafePath
    # must refuse this regardless of any name match.
    dangerous_appdata = tmp_path / "TestApp"
    dangerous_appdata.mkdir()
    env_with_dangerous_appdata = dict(env)
    env_with_dangerous_appdata["APPDATA"] = str(dangerous_appdata)

    items_file = tmp_path / "approved_dangerous.json"
    items_file.write_text(json.dumps({"folders": [str(dangerous_appdata)], "registry": []}))

    code, stdout, stderr = _run("TestApp", "Delete", env_with_dangerous_appdata, ["-ItemsFile", str(items_file)])
    assert code == 0, stderr
    data = json.loads(stdout)

    assert data["deleted"]["folders"] == []
    assert dangerous_appdata.exists()  # must NOT have been deleted
    reasons = [r["reason"] for r in data["rejected"]]
    assert any("safety check" in r for r in reasons)


def test_scan_aborts_when_items_file_missing_for_delete(fake_app_dirs):
    _, env = fake_app_dirs
    code, stdout, stderr = _run("TestApp", "Delete", env)
    assert code == 1
    error = json.loads(stdout)
    assert error["success"] is False


def test_empty_app_name_fails_cleanly(fake_app_dirs):
    _, env = fake_app_dirs
    code, stdout, stderr = _run(" ", "Scan", env)
    # Whitespace-only name should be rejected by the script's own check
    # (mandatory-parameter binding only rejects a truly empty string).
    data = json.loads(stdout) if stdout.startswith("{") else None
    assert code != 0 or (data and data.get("success") is False)


# ---------------------------------------------------------------------------
# Isolated function-level tests for the NEW registry safety check, which
# can't be exercised end-to-end without a real Windows registry.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def funcs_only(tmp_path_factory):
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    marker = next(i for i, line in enumerate(lines) if line.strip() == "# MODE: Scan")
    # back up past the "# ====" banner line and the section title above it
    truncated = lines[: marker - 2]

    out_dir = tmp_path_factory.mktemp("funcs")
    out_path = out_dir / "funcs_only.ps1"
    out_path.write_text("\n".join(truncated), encoding="utf-8")
    return out_path


def test_registry_safety_check_accepts_direct_child(funcs_only):
    result = subprocess.run(
        [
            PWSH,
            "-NoProfile",
            "-Command",
            f". '{funcs_only}' -TargetAppName x -Mode Scan 2>$null; "
            "Test-SafeRegistryLeaf "
            "-RegistryPath 'Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software\\TestApp' "
            "-AllowedRootPSPaths @('Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software')",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.stdout.strip() == "True"


def test_registry_safety_check_rejects_nested_key(funcs_only):
    result = subprocess.run(
        [
            PWSH,
            "-NoProfile",
            "-Command",
            f". '{funcs_only}' -TargetAppName x -Mode Scan 2>$null; "
            "Test-SafeRegistryLeaf "
            "-RegistryPath 'Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software\\TestApp\\Nested' "
            "-AllowedRootPSPaths @('Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software')",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.stdout.strip() == "False"


def test_registry_safety_check_rejects_unrelated_root(funcs_only):
    result = subprocess.run(
        [
            PWSH,
            "-NoProfile",
            "-Command",
            f". '{funcs_only}' -TargetAppName x -Mode Scan 2>$null; "
            "Test-SafeRegistryLeaf "
            "-RegistryPath 'Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet' "
            "-AllowedRootPSPaths @('Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software')",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.stdout.strip() == "False"


def test_match_quality_exact_vs_containment_vs_none(funcs_only):
    result = subprocess.run(
        [
            PWSH,
            "-NoProfile",
            "-Command",
            f". '{funcs_only}' -TargetAppName x -Mode Scan 2>$null; "
            "$terms = @('TestApp','testapp'); "
            "Write-Output (Get-ApplicationNameMatchQuality -Name 'TestApp' -SearchTerms $terms); "
            "Write-Output (Get-ApplicationNameMatchQuality -Name 'MyTestAppBackup' -SearchTerms $terms); "
            "Write-Output (Get-ApplicationNameMatchQuality -Name 'Unrelated' -SearchTerms $terms)",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    lines = result.stdout.strip().splitlines()
    assert lines == ["Exact", "Containment", "None"]
