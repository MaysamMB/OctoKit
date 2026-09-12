# WinToolkit

A unified Windows desktop utility toolkit (PySide6) combining four
previously-standalone tools into one modular application:

- **Application Inventory** — read-only. Lists installed applications,
  broken uninstall registrations, orphaned registry entries, and
  possible leftover application folders. Never modifies anything.
- **Application Leftovers Cleaner** — destructive. Finds leftover
  folders and registry keys for a named application and deletes only
  the items you explicitly select and confirm.
- **Temporary Files Cleaner** — destructive. Scans standard temp
  locations (and optionally the Recycle Bin) and deletes only what you
  choose to clean, after a separate read-only scan step.
- **Project & File Generator** — creates new project scaffolds
  (Python, React, Flutter, and any custom templates you add) from
  templates, with itemized conflict detection before anything is
  written.

## Safety model

Every destructive action in this app follows the same pipeline:
**Detect → Analyze → Review → Select → Validate → Confirm → Execute →
Report → Log.** Nothing is deleted without an item being scanned,
shown to you, explicitly selected, re-validated immediately before
deletion (a stale scan result is never trusted), and confirmed — with
an additional typed confirmation phrase required specifically for any
deletion that includes registry keys. Items the safety checks can't
classify with confidence default to **unselected**.

All PowerShell execution goes through a single, allow-listed service
(`core/powershell.py`) — the UI never runs arbitrary PowerShell, and
arguments are always passed as a list, never concatenated into a
string.

See the in-app **Help / User Guide** page for full, implementation-accurate
documentation of exactly what each feature does and does not do.

## Getting started

```powershell
pip install -r requirements.txt
python main.py
```

See [BUILD.md](BUILD.md) for running the test suite and building a
packaged `.exe` with PyInstaller.

## Project layout

```
core/        Infrastructure shared by every feature: config, logging,
             paths, the PowerShell execution service, background
             worker helper, exceptions, domain models.
features/    One package per feature (application_inventory,
             leftovers_cleaner, temp_cleaner, project_generator), each
             with models.py / service.py / view.py.
scripts/     The three PowerShell scripts the app shells out to.
settings/    The Settings page.
help/        Help / User Guide content and view.
ui/          App shell: main window, sidebar, dashboard, theming,
             shared dialogs and components.
tests/       pytest suite (unit tests for services/models/scripts,
             headless Qt tests for views, and end-to-end integration
             tests that exercise real PowerShell + real background
             worker threads).
```

## Known limitations

This project was built and tested in a Linux sandbox with real
PowerShell 7 installed for functional testing, since no Windows
machine was available. That testing caught and fixed several real
PowerShell bugs (parameter binding, JSON serialization edge cases —
see git history / inline comments in `scripts/*.ps1` for details), but
a few Windows-only code paths could not be exercised end-to-end and
should be smoke tested on a real Windows machine before wider use:
elevation via `Start-Process -Verb RunAs`, Recycle Bin access via the
Shell COM object, and admin-status detection via
`WindowsPrincipal`/`WindowsIdentity`. The packaged `.exe` itself was
also not run on real Windows — see BUILD.md's "Build verification
performed in this environment" section for exactly what was and
wasn't verified.
