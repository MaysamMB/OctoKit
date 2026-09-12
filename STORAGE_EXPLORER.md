# Storage Explorer — local trial

This is a read-only feature. No files are deleted, file contents
read, privileges changed or scan results uploaded by this feature.

## Windows trial (PowerShell, inside this separate extracted project)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
.\.venv\Scripts\python.exe -m pytest tests/test_storage_explorer.py -q
.\.venv\Scripts\python.exe main.py
```

Open SYSTEM TOOLS > Storage Explorer. Choose a small test folder first.
Then List drives, review the used/free space, and Scan selected drive.
The most-used fixed local drive by bytes is preselected; highest percentage
is reported separately. Drive discovery does not start a recursive scan.

After one metadata pass, the tree is sorted by logical bytes. Timed summaries
follow the largest observed child at each level. Select any tree item to read
its exact path, byte count, coverage and conservative advice. Re-scan selected
item replaces the current tree with a fresh scan of that file/folder.
Choose folder starts a different scope. Largest files lists up to 100 paths
from across the scan, including files outside the largest-folder chain.

## Required Windows checks before publishing

- Small folder: compare byte counts with known files, test Arabic names.
- Drive list: compare total/free/used with Windows.
- Cancel a scan, check partial status, then start again.
- Expand folders, select files, re-scan, open containing folder.
- Test inaccessible folders, junctions, cloud placeholders and hard links.
- Try a large folder and verify UI responsiveness and memory use.
- Run the whole suite: `.\.venv\Scripts\python.exe -m pytest tests -q`.
- Build and launch an EXE on Windows before a release. See BUILD.md and the
  included OctoKit.spec. A separate preview can also be built using:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onedir --windowed --name OctoKit-StoragePreview --add-data "scripts;scripts" main.py
```

Distribute the entire generated folder, not just the executable. Build from
this trial folder so an existing release build is not overwritten.

## Honest limits

- Logical size per directory entry, not allocated or recoverable disk space.
  Hard-linked data can appear multiple times and is explicitly counted as such.
- No file contents, NTFS metadata tables, alternate data streams, restore points
  or complete physical-allocation accounting. No promise to match Windows used
  space; compressed/sparse/cloud data and inaccessible items cause differences.
- Links/reparse points, offline/recall placeholders and cross-device mounts
  are excluded; excluded entries propagate partial coverage to parents.
- At 300,000 discovered nodes the scan stops with partial results. Select a
  smaller folder to continue. Tree rendering is virtualized, not item-per-widget.
- A changing filesystem is not an atomic snapshot. Ordinary metadata calls can
  block; cancellation is cooperative, not a forced thread termination. Do not
  use against an adversarial process actively replacing paths with links.
- Advice is a conservative name-based hint, never proof that data is unused or
  safe to delete. There is no deletion button or automatic cleanup integration.
- Results live in memory for this session only. No background scheduled scans.

## Development

Verification on Linux with Python 3.12.14, PySide6 6.11.2 and pytest 9.1.1:
105 passed, 19 skipped in the full suite. Skipped tests require unavailable
PowerShell capabilities. A real Qt background scan/re-scan and offscreen UI
render were exercised. Windows APIs, junction/cloud behavior on Windows,
whole-drive performance and the Windows executable have NOT been verified.
The new tests include mocked Windows file attribute exclusions, not a substitute
for the Windows checklist above.

Feature code: `features/storage_explorer/`; integration: `main.py`,
`ui/sidebar.py`, `ui/dashboard.py`, `core/app_state.py`, and `help/content.py`.
Tests: `tests/test_storage_explorer.py`, plus existing application wiring tests.
Development branch: `feature/storage-explorer`.
