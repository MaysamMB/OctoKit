"""
Centralized PowerShell execution layer.

This is the ONLY place in the application that is allowed to build and run
a PowerShell command line. UI and feature-service code must call
`PowerShellService.run(...)` rather than touching `subprocess` directly.

Guarantees provided here (spec section 7 / 11):
  * Only application-owned scripts, resolved strictly inside the app's own
    `scripts/` directory and matched against an explicit allow-list, can be
    executed. Arbitrary paths are rejected before anything runs.
  * Arguments are always passed as a list to `subprocess` — never
    interpolated into a command string — so there is no shell-injection
    surface. `-Command` is used only for the small, fully-internal elevation
    bootstrap below, and every value placed into it is produced by this
    module itself (never raw user text) and safely quoted.
  * `Invoke-Expression` is never used anywhere in this codebase.
  * Every invocation is logged (script + argument names, not raw file
    contents); failures are logged at ERROR.
  * Long-running calls support both a timeout and cooperative cancellation
    via a `threading.Event`.
  * JSON output is parsed centrally; a malformed response becomes a
    `JsonParseError` carrying the raw output for the UI's "Show Technical
    Details" panel — it is never silently swallowed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from core.exceptions import (
    JsonParseError,
    OperationCancelledError,
    PermissionDeniedError,
    PowerShellExecutionError,
    PowerShellNotFoundError,
    PowerShellTimeoutError,
    ScriptValidationError,
)
from core.logger import get_logger
from core.models import PowerShellResult
from core.paths import get_scripts_dir
from core.permissions import platform_supports_elevation

logger = get_logger("core.powershell")

# Explicit allow-list of scripts this application is permitted to execute.
# Anything not in this set is refused by `_resolve_script_path`, regardless
# of what a caller passes in.
ALLOWED_SCRIPTS = frozenset(
    {
        "OldApplicationsInventory.ps1",
        "CleanTempFiles.ps1",
        "CleanAppLeftovers.ps1",
    }
)

_DEFAULT_TIMEOUT_SECONDS = 120
_POLL_INTERVAL_SECONDS = 0.25


class PowerShellService:
    def __init__(self, scripts_dir: Path | None = None):
        self.scripts_dir = (scripts_dir or get_scripts_dir()).resolve()
        self._executable: str | None = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_executable(self) -> str:
        """Locate PowerShell 7+ (`pwsh`) or fall back to Windows PowerShell
        (`powershell`). Result is cached for the lifetime of the service."""
        if self._executable:
            return self._executable

        for candidate in ("pwsh", "pwsh.exe", "powershell", "powershell.exe"):
            found = shutil.which(candidate)
            if found:
                self._executable = found
                logger.info("Using PowerShell executable: %s", found)
                return found

        raise PowerShellNotFoundError()

    def is_available(self) -> bool:
        try:
            self.discover_executable()
            return True
        except PowerShellNotFoundError:
            return False

    # ------------------------------------------------------------------
    # Script path validation
    # ------------------------------------------------------------------

    def _resolve_script_path(self, script_name: str) -> Path:
        if script_name not in ALLOWED_SCRIPTS:
            raise ScriptValidationError(
                technical_details=f"'{script_name}' is not in the application's script allow-list."
            )

        candidate = (self.scripts_dir / script_name).resolve()

        if candidate.parent != self.scripts_dir:
            # Defeats path traversal such as "..\\..\\evil.ps1".
            raise ScriptValidationError(
                technical_details=f"Resolved path '{candidate}' escapes the scripts directory."
            )

        if not candidate.is_file():
            raise ScriptValidationError(
                user_message=f"Required script '{script_name}' is missing from the installation.",
                technical_details=f"Expected file at {candidate}",
            )

        return candidate

    # ------------------------------------------------------------------
    # Helpers for passing complex data safely
    # ------------------------------------------------------------------

    @staticmethod
    def write_json_temp_file(data: object) -> Path:
        """
        Write a JSON payload (e.g. a user-approved deletion list) to a
        private temp file and return its path, so it can be passed to a
        script as a single `-ItemsFile <path>` argument instead of being
        serialized inline on the command line.
        """
        fd, path_str = tempfile.mkstemp(prefix="wintoolkit_", suffix=".json")
        path = Path(path_str)
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def _quote_ps(value: str) -> str:
        """Safely quote a value for embedding in a PowerShell single-quoted
        string. Only used for the internal elevation bootstrap; every value
        passed through here originates from this module, never free-form
        user input."""
        return "'" + str(value).replace("'", "''") + "'"

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        script_name: str,
        args: list[str] | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        parse_json: bool = True,
        elevated: bool = False,
        cancel_event: threading.Event | None = None,
    ) -> PowerShellResult:
        args = args or []
        script_path = self._resolve_script_path(script_name)
        exe = self.discover_executable()

        logger.info(
            "Running script=%s elevated=%s args=%s", script_name, elevated, _redact_args(args)
        )

        try:
            if elevated:
                stdout, stderr, exit_code = self._run_elevated(exe, script_path, args, timeout)
            else:
                stdout, stderr, exit_code = self._run_normal(
                    exe, script_path, args, timeout, cancel_event
                )
        except OperationCancelledError:
            logger.warning("Script %s cancelled by user.", script_name)
            raise
        except PowerShellTimeoutError:
            logger.error("Script %s timed out after %ss.", script_name, timeout)
            raise

        success = exit_code == 0
        if not success:
            logger.warning(
                "Script %s exited with code %s. stderr=%s", script_name, exit_code, stderr[:500]
            )

        result = PowerShellResult(
            success=success, exit_code=exit_code, stdout=stdout, stderr=stderr
        )

        if parse_json:
            result.data = self._parse_json(stdout, script_name)

        return result

    def _run_normal(
        self,
        exe: str,
        script_path: Path,
        args: list[str],
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> tuple[str, str, int]:
        full_args = [
            exe,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *args,
        ]

        try:
            process = subprocess.Popen(
                full_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise PowerShellExecutionError(technical_details=str(exc)) from exc

        start = time.monotonic()
        stdout, stderr = "", ""
        while True:
            if cancel_event is not None and cancel_event.is_set():
                process.kill()
                process.communicate()
                raise OperationCancelledError()
            try:
                stdout, stderr = process.communicate(timeout=_POLL_INTERVAL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() - start > timeout:
                    process.kill()
                    process.communicate()
                    raise PowerShellTimeoutError()
                continue

        return stdout, stderr, process.returncode

    def _run_elevated(
        self, exe: str, script_path: Path, args: list[str], timeout: float
    ) -> tuple[str, str, int]:
        if not platform_supports_elevation():
            raise PermissionDeniedError(
                user_message="Elevated execution is only supported on Windows."
            )

        with tempfile.TemporaryDirectory(prefix="wintoolkit_elev_") as tmp:
            out_file = Path(tmp) / "out.txt"
            err_file = Path(tmp) / "err.txt"
            exit_file = Path(tmp) / "exit.txt"

            inner_args_str = " ".join(self._quote_ps(a) for a in args)
            inner_command = (
                f"try {{ & {self._quote_ps(str(script_path))} {inner_args_str} "
                f"*> {self._quote_ps(str(out_file))}; "
                f"$LASTEXITCODE | Out-File -FilePath {self._quote_ps(str(exit_file))} "
                f"-Encoding utf8 -NoNewline }} "
                f"catch {{ $_.Exception.Message | Out-File -FilePath "
                f"{self._quote_ps(str(err_file))} -Encoding utf8 }}"
            )

            start_process_command = (
                f"$p = Start-Process -FilePath {self._quote_ps(exe)} -Verb RunAs -Wait "
                f"-PassThru -WindowStyle Hidden -ArgumentList @("
                f"'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',"
                f"{self._quote_ps(inner_command)})"
            )

            outer_args = [
                exe,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                start_process_command,
            ]

            try:
                subprocess.run(outer_args, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise PowerShellTimeoutError() from exc
            except OSError as exc:
                raise PowerShellExecutionError(technical_details=str(exc)) from exc

            stdout = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""
            stderr = err_file.read_text(encoding="utf-8", errors="replace") if err_file.exists() else ""
            exit_code_text = (
                exit_file.read_text(encoding="utf-8", errors="replace").strip()
                if exit_file.exists()
                else ""
            )

            if stderr and not stdout:
                raise PermissionDeniedError(technical_details=stderr)

            try:
                exit_code = int(exit_code_text) if exit_code_text else 0
            except ValueError:
                exit_code = 1

            return stdout, stderr, exit_code

    @staticmethod
    def _parse_json(stdout: str, script_name: str) -> object:
        text = stdout.strip()
        if not text:
            raise JsonParseError(
                technical_details=f"'{script_name}' produced no output to parse."
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise JsonParseError(
                technical_details=f"Raw output from '{script_name}':\n{text[:2000]}"
            ) from exc


def _redact_args(args: list[str]) -> list[str]:
    """Argument values are generally not sensitive (paths, flags, app
    names), but this keeps a single choke point in case that changes."""
    return list(args)
