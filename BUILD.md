# Building WinToolkit

## Running from source (development)

Requires Python 3.11+ on Windows, with PowerShell available (either
Windows PowerShell 5.1, which ships with every supported Windows
version, or PowerShell 7+).

```powershell
pip install -r requirements.txt
python main.py
```

## Running the tests

```powershell
pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM = ""   # not needed on Windows; only used for headless CI
python -m pytest tests/ -q
```

The test suite includes tests that shell out to real PowerShell (scan
scripts in read-only mode) — they are skipped automatically
(`pwsh_required` / `PWSH.is_available()` guards) on a machine with no
PowerShell on `PATH`, rather than failing.

## Building the packaged executable

```powershell
pip install -r requirements-dev.txt
pyinstaller WinToolkit.spec
```

This produces a one-directory build at `dist/WinToolkit/`, with
`WinToolkit.exe` at its root. Distribute the whole `dist/WinToolkit/`
folder — the `.exe` depends on the DLLs and the `scripts/` folder
PyInstaller places alongside it in `_internal/`.

**Why one-directory, not one-file:** WinToolkit shells out to the
bundled PowerShell scripts on every scan and cleanup operation. A
one-file build re-extracts its entire payload to a fresh temp directory
on every launch, which is slower to start and leaves a stale copy
behind each time the app exits. One-directory avoids both.

### What actually gets bundled

Only `scripts/*.ps1` is bundled as data — see the comment at the top of
`WinToolkit.spec` for the full explanation of why `templates/` and
`assets/` are *not* currently bundled (nothing in the codebase reads
from either directory at runtime: default project templates are
generated in code by `template_manager.py`, and every icon is drawn
procedurally by `ui/components/icons.py`).

### Build verification performed in this environment

This project was developed and tested in a Linux sandbox, so the
`.exe` itself could not be built or run here — PyInstaller does not
cross-compile. What *was* verified on Linux, using PyInstaller's own
Linux output as a stand-in to validate the spec file's mechanics
(`Analysis`, data-file collection, hidden imports — all
platform-independent parts of PyInstaller):

- `pyinstaller WinToolkit.spec` completes with no errors.
- The three `.ps1` scripts land in the build output exactly where
  `core/paths.py`'s frozen-mode `get_scripts_dir()` expects them.
- The frozen build launches, reaches "Application ready" in its log
  with no exceptions, and correctly writes config/logs/templates to
  the per-user data directories rather than the install folder — even
  when launched from an unrelated working directory (proving path
  resolution is based on the executable's own location, not `cwd`).

What was **not** and could not be verified here, and should be smoke
tested on a real Windows machine before wider distribution: the actual
`.exe` launching under Windows, any Windows-only API paths (elevation
via `Start-Process -Verb RunAs`, the Recycle Bin via the Shell COM
object, `WindowsIdentity`/`WindowsPrincipal` admin detection), and the
one-directory build's file associations / SmartScreen behavior on a
freshly downloaded, unsigned executable.

### Code signing

`WinToolkit.exe` is unsigned. An unsigned executable will trigger a
Windows SmartScreen warning on first run on most machines. If this
matters for your distribution channel, sign `dist/WinToolkit/WinToolkit.exe`
with a code-signing certificate after building, before distributing it.

### Adding an application icon

No `.ico` file exists yet — `WinToolkit.spec` has a commented-out
`icon=` line ready for one. Add `assets/wintoolkit.ico` and uncomment
that line to give the built `.exe` a real icon instead of the default
PyInstaller one.
