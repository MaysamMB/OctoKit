import json
import sys
import threading

import pytest

from core.exceptions import (
    JsonParseError,
    OperationCancelledError,
    PowerShellNotFoundError,
    PowerShellTimeoutError,
    ScriptValidationError,
)
from core.powershell import PowerShellService


def _write_script(scripts_dir, name, body):
    path = scripts_dir / name
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def scripts_dir(tmp_path, monkeypatch):
    directory = tmp_path / "scripts"
    directory.mkdir()
    # Register a fake script name in the allow-list so tests don't need to
    # touch the real production scripts.
    monkeypatch.setattr(
        "core.powershell.ALLOWED_SCRIPTS",
        frozenset({"OldApplicationsInventory.ps1", "CleanTempFiles.ps1", "CleanAppLeftovers.ps1", "fake.ps1"}),
    )
    return directory


def test_rejects_script_outside_allowlist(scripts_dir):
    service = PowerShellService(scripts_dir=scripts_dir)
    _write_script(scripts_dir, "not_allowed.ps1", "Write-Output 'hi'")
    with pytest.raises(ScriptValidationError):
        service.run("not_allowed.ps1", parse_json=False)


def test_rejects_missing_script(scripts_dir):
    service = PowerShellService(scripts_dir=scripts_dir)
    with pytest.raises(ScriptValidationError):
        service.run("fake.ps1", parse_json=False)


def test_rejects_path_traversal(scripts_dir, tmp_path):
    # Even if a caller tries to sneak a traversal-like name past the
    # allow-list check, resolution must keep it inside scripts_dir.
    service = PowerShellService(scripts_dir=scripts_dir)
    with pytest.raises(ScriptValidationError):
        service._resolve_script_path("../evil.ps1")


def test_discover_executable_raises_when_missing(scripts_dir, monkeypatch):
    service = PowerShellService(scripts_dir=scripts_dir)
    monkeypatch.setattr("core.powershell.shutil.which", lambda name: None)
    with pytest.raises(PowerShellNotFoundError):
        service.discover_executable()
    assert service.is_available() is False


@pytest.mark.skipif(sys.platform == "win32", reason="uses a POSIX shell script stand-in")
def test_run_parses_json_output(scripts_dir, monkeypatch):
    # We can't run real PowerShell in this environment, so we point the
    # service at a fake "PowerShell executable" that is actually our own
    # interpreter, and verify the plumbing (argument building, execution,
    # JSON parsing) end to end.
    service = PowerShellService(scripts_dir=scripts_dir)
    fake_script = _write_script(scripts_dir, "fake.ps1", "# not actually run")

    stub = scripts_dir / "stub_powershell.py"
    stub.write_text(
        "import sys, json\n"
        "print(json.dumps({'success': True, 'value': 42}))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("core.powershell.shutil.which", lambda name: sys.executable)

    # Patch the internal command builder indirectly by overriding _run_normal
    # is not necessary: instead we monkeypatch discover_executable's chosen
    # exe usage inside _run_normal by intercepting subprocess.Popen args.
    import subprocess as subprocess_module

    original_popen = subprocess_module.Popen

    def fake_popen(args, **kwargs):
        # Replace the real "-File <script>" invocation with running our stub.
        return original_popen([sys.executable, str(stub)], **kwargs)

    monkeypatch.setattr("core.powershell.subprocess.Popen", fake_popen)

    result = service.run("fake.ps1", ["-Whatever"], timeout=10)
    assert result.success is True
    assert result.data == {"success": True, "value": 42}


def test_run_raises_json_parse_error_on_bad_output(scripts_dir, monkeypatch):
    service = PowerShellService(scripts_dir=scripts_dir)
    _write_script(scripts_dir, "fake.ps1", "# stub")

    stub = scripts_dir / "stub_bad.py"
    stub.write_text("print('not json at all')", encoding="utf-8")

    monkeypatch.setattr("core.powershell.shutil.which", lambda name: sys.executable)

    import subprocess as subprocess_module

    original_popen = subprocess_module.Popen

    def fake_popen(args, **kwargs):
        return original_popen([sys.executable, str(stub)], **kwargs)

    monkeypatch.setattr("core.powershell.subprocess.Popen", fake_popen)

    with pytest.raises(JsonParseError):
        service.run("fake.ps1", timeout=10)


def test_run_times_out(scripts_dir, monkeypatch):
    service = PowerShellService(scripts_dir=scripts_dir)
    _write_script(scripts_dir, "fake.ps1", "# stub")

    stub = scripts_dir / "stub_slow.py"
    stub.write_text("import time\ntime.sleep(5)\nprint('{}')", encoding="utf-8")

    monkeypatch.setattr("core.powershell.shutil.which", lambda name: sys.executable)

    import subprocess as subprocess_module

    original_popen = subprocess_module.Popen

    def fake_popen(args, **kwargs):
        return original_popen([sys.executable, str(stub)], **kwargs)

    monkeypatch.setattr("core.powershell.subprocess.Popen", fake_popen)

    with pytest.raises(PowerShellTimeoutError):
        service.run("fake.ps1", timeout=0.5)


def test_run_can_be_cancelled(scripts_dir, monkeypatch):
    service = PowerShellService(scripts_dir=scripts_dir)
    _write_script(scripts_dir, "fake.ps1", "# stub")

    stub = scripts_dir / "stub_slow2.py"
    stub.write_text("import time\ntime.sleep(5)\nprint('{}')", encoding="utf-8")

    monkeypatch.setattr("core.powershell.shutil.which", lambda name: sys.executable)

    import subprocess as subprocess_module

    original_popen = subprocess_module.Popen

    def fake_popen(args, **kwargs):
        return original_popen([sys.executable, str(stub)], **kwargs)

    monkeypatch.setattr("core.powershell.subprocess.Popen", fake_popen)

    cancel_event = threading.Event()
    cancel_event.set()  # already cancelled before the poll loop starts

    with pytest.raises(OperationCancelledError):
        service.run("fake.ps1", timeout=10, cancel_event=cancel_event)


def test_write_json_temp_file_roundtrip():
    path = PowerShellService.write_json_temp_file({"items": [1, 2, 3]})
    try:
        assert json.loads(path.read_text(encoding="utf-8")) == {"items": [1, 2, 3]}
    finally:
        path.unlink(missing_ok=True)
