"""
Built-in Help / User Guide content (spec section 36).

This documents the ACTUAL implemented behavior of this application - not
the aspirational spec. Where the two differ (e.g. the Leftovers Cleaner's
error-suppression limitation, or that Windows\\Temp cleanup requires
elevation), that limitation is stated here plainly rather than glossed
over. If you change what a feature does, update the matching section here.
"""

from __future__ import annotations

GETTING_STARTED = """
# Getting Started

WinToolkit is a small suite of Windows maintenance and developer tools in
one application: an application inventory scanner, a leftover-files
cleaner, a temporary-files cleaner, and a project scaffolding tool.

**Read-only features:** Application Inventory. Scanning, in every feature,
is always read-only — it never deletes or changes anything by itself.

**Features that can change your system:** Application Leftovers Cleaner
(deletes files, folders, and registry keys you select) and Temporary Files
Cleaner (deletes temp files and can empty the Recycle Bin). Both always
show you exactly what they found and wait for your explicit confirmation
before deleting anything.

**Project Generator** creates new files and folders on disk (it does not
delete existing ones, except when you explicitly choose to overwrite an
existing project).

## Recommended workflow

```
Open a feature
      ↓
Scan / Analyze
      ↓
Review results
      ↓
Select what you want to act on (destructive features only)
      ↓
Confirm if required
      ↓
View results / logs
```

Scanning never means deleting or modifying anything. You always take a
separate, explicit action before anything changes.
"""

DASHBOARD_GUIDE = """
# Dashboard Guide

The Dashboard shows a summary of your last scans in this session: how many
applications were found, how many looked broken, how much temp space is
recoverable, and how many projects you've generated. Every card reads "—"
until you've actually run that scan at least once — nothing here is
estimated or made up.

Quick Actions on the Dashboard take you to a feature; they do not scan or
delete anything by themselves.
"""

APPLICATION_INVENTORY_GUIDE = """
# Application Inventory — User Guide

**This feature is READ-ONLY.** It never uninstalls, deletes, or modifies
anything on your system.

## What it scans

Three Windows registry locations where installed programs register
themselves: `HKLM\\...\\Uninstall`, its WOW6432Node counterpart (32-bit
apps on a 64-bit system), and the equivalent under `HKCU`. For every
registered entry it also checks whether the claimed install folder, the
uninstaller, and the display icon actually still exist on disk.

## What the statuses mean

- **Installed** — the registered install folder exists on disk.
- **Registered - Uninstaller Found** — the install folder is gone, but
  its uninstaller program still exists.
- **Registered - Application Evidence Found** — only its icon file could
  be confirmed to still exist.
- **Possible Broken Registration** — an install location is registered but
  nothing at that path exists anymore. This usually means the program was
  removed by hand instead of through its uninstaller, or an uninstall
  didn't fully clean up its own registry entry.
- **Registered - Location Not Specified** — the registry entry never
  recorded an install location at all; this is normal for some
  installers and does not by itself indicate a problem.

Entries recognized as system or runtime components (for example, Visual
C++ Redistributables or .NET runtimes) are labeled **System/Runtime
Component** rather than **Application**, since removing them can be risky
and they're not what most people mean by "an old application."

A "Possible Broken Registration" or an orphaned registry entry is a
**candidate for cleanup**, not a diagnosis that something is actually
broken — some legitimate applications intentionally leave a registry
marker without a traditional install folder. Verify before acting.

## Known limitation

Scanning suppresses non-fatal PowerShell errors so a single unreadable
registry key doesn't stop the whole scan. If that happens, a note appears
in the scan status; the counts you see are still accurate for whatever
could be read.

## Workflow

Scan → Review → Search/Filter → Export (JSON or CSV) if you want a record.
There is no delete button anywhere on this screen, by design.
"""

LEFTOVERS_CLEANER_GUIDE = """
# Application Leftovers Cleaner — User Guide

**This feature can delete files, folders, and registry keys.** Deletions
are permanent — they bypass the Recycle Bin and cannot be undone by this
application.

## Before you start

Uninstall the application normally first (Windows Settings, or its own
uninstaller). This tool only looks for what an uninstaller left behind —
it refuses to run if the application still appears to be installed.

## What "leftovers" are

Many uninstallers don't remove every file or registry key they created —
save-data folders, cached settings, or a registry key documenting that the
program was once installed. These leftovers are usually harmless but can
accumulate over time.

## Why detected items are only candidates

Matching is done by name: does a folder or registry key name match the
application name you searched for? An **exact** name match is marked
**Safe / Recommended**. A **partial** match (the folder/key name contains
your search term, and the term is specific enough — at least 5 characters
— to reduce false positives) is marked **Suspicious** and is *never*
pre-selected for you. Review Suspicious items carefully — a folder called
"MyToolBackup" partially matching a search for "Tool" is exactly the kind
of coincidence this classification exists to flag.

Every item is re-checked immediately before deletion, independent of the
scan: it must still exist, still pass a safety-path check (folders) or a
registry-location check (registry keys), and still match the application
name. Nothing is deleted just because it was shown on screen earlier.

## Workflow

```
Search for the application
        ↓
Scan
        ↓
Review Folders and Registry results separately
        ↓
Select the items you want removed (Select Safe Items, or choose your own)
        ↓
Click Delete Selected
        ↓
Review the confirmation dialog carefully
        ↓
Confirm (Registry deletions require typing a confirmation phrase, by default)
        ↓
Review the result: deleted / rejected / failed
```

Items that fail re-validation at delete time are reported as **rejected**,
with a reason, rather than silently skipped.
"""

TEMP_CLEANER_GUIDE = """
# Temporary Files Cleaner — User Guide

## What it cleans

The *contents* of your user Temp folder (`%TEMP%`) and, if you're running
as Administrator, `C:\\Windows\\Temp`. The folders themselves are never
removed, only what's inside them. It can also empty the Recycle Bin.
`C:\\Windows\\Prefetch` is intentionally never touched — Windows manages it
itself, and clearing it provides no real benefit.

## Scan vs. Cleanup

**Scan** is completely read-only: it reports how many files and folders
are old enough to be eligible, and an estimate of the space you'd recover.
Nothing is deleted. **Cleanup** is the separate, explicit action that
actually deletes — and even then, only files older than the minimum age
you set, so anything currently in use is left alone.

## Minimum Age

Only items whose last-modified time is older than this many minutes are
considered. The default (120 minutes) exists so a file created moments ago
— possibly still in use by another program — is never touched.

## Dry Run

Simulates a real cleanup and reports exactly what it would do, without
deleting anything. Useful for checking a lower minimum-age setting before
committing to it.

## Locked files

Files currently open in another program can't be deleted; the cleanup
simply skips them and reports the count rather than stopping or erroring.

## Administrator privileges

Cleaning `C:\\Windows\\Temp` requires elevation. If you're not running as
Administrator, that location is skipped and clearly marked in the
results — your user Temp folder and the Recycle Bin are still cleaned
normally. You can choose to run just that part elevated; Windows will show
the standard UAC prompt for it.

## Workflow

```
Set Minimum Age and Recycle Bin option
        ↓
Scan
        ↓
Review estimated space / file / folder counts
        ↓
(Optional) enable Dry Run to double-check
        ↓
Click Clean Selected
        ↓
Confirm
        ↓
Review the cleanup summary and, if needed, the log
```
"""

PROJECT_GENERATOR_GUIDE = """
# Project Generator — User Guide

Creates a new project folder from a template: predefined folders, starter
files, and a `config.json` recording the project name and template used.

## Templates

Templates live as folders on disk, each containing the files/folders to
copy. Ten templates are created automatically the first time you use this
feature (Basic, Python, Web, Node.js, React, Flutter, Java, Spring Boot,
C++, and C). If you ever delete or modify one of these, it is **not**
automatically restored to its original content — only genuinely *missing*
default templates are recreated, and any template you've customized is
left exactly as you left it. You can also add your own custom template
folders; they show up in the Template list alongside the built-in ones.

## Variables

Any file in a template can use `{{PROJECT_NAME}}` and `{{TEMPLATE}}` —
both are replaced with your actual values when the project is generated.

## Validation

A project name can't contain `< > : " / \\ | ? *`, can't be `.` or `..`,
can't end in a space or a period, and can't be a Windows-reserved name
like `CON` or `COM1` (with or without a file extension) — Windows itself
rejects these as file/folder names.

## If a project with that name already exists

Generation stops and shows you exactly which template files would be
overwritten before anything happens. You can then choose to proceed
(overwriting only those specific files) or cancel and pick a different
name or location.

## Workflow

```
Enter Project Name
        ↓
Select Template
        ↓
Select Location
        ↓
Review Preview and Statistics
        ↓
Create Project
        ↓
Review the confirmation (files/folders actually created)
```
"""

SAFETY_GUIDE = """
# Safety Guide

## Read-only, always
- Application Inventory
- Every "Scan" button, in every feature
- The Project Generator's Preview

## Can modify your system
- Application Leftovers Cleaner (file, folder, and registry deletion)
- Temporary Files Cleaner (file deletion, Recycle Bin emptying)
- Project Generator (creates new files; can overwrite files in an existing
  project folder only if you explicitly confirm it)

## The sequence every destructive action follows

```
Detect → Review → Select → Confirm → Execute → Report → Log
```

Nothing is ever deleted or changed automatically. Items your the app is
uncertain about (marked Suspicious) are never pre-selected for you.

## What is NOT reversible

Deletions performed by the Leftovers Cleaner and the Temp Files Cleaner
bypass the Recycle Bin and **cannot** be recovered by this application.
This app does not implement a backup/undo mechanism for any destructive
operation — if a confirmation dialog says an action cannot be undone,
that is a literal statement, not caution for its own sake.
"""

PERMISSIONS_GUIDE = """
# Permissions / Administrator Guide

WinToolkit runs as a normal user by default and does not request
Administrator privileges at startup. Some individual operations do need
elevation:

- Cleaning `C:\\Windows\\Temp` (a system-owned location).
- Deleting certain Registry keys, depending on how your system's
  permissions are configured.

When one of these is needed, the app asks you at that moment — you'll see
a standard Windows UAC prompt scoped to just that operation, not the whole
application. If you decline, or aren't running as an account that can
elevate, that specific operation is skipped and clearly marked; everything
else you asked for still runs.

There's no reason to run the whole application as Administrator all the
time — doing so doesn't unlock anything extra beyond what per-operation
elevation already covers, and it's safer to keep the app itself running
with standard privileges.
"""

TROUBLESHOOTING_GUIDE = """
# Troubleshooting

**PowerShell unavailable** — Application Inventory, Leftovers Cleaner, and
Temp Files Cleaner all require PowerShell (Windows PowerShell 5.1 or
PowerShell 7+). If neither can be found, those features are disabled and
Settings will say so under PowerShell → Detected executable.

**Access Denied** — Windows blocked access to a protected location. This
usually means the operation needs Administrator privileges; the app will
say so rather than failing silently.

**A file is locked / in use** — the file is currently open elsewhere.
Cleanup skips it and reports the count; it does not stop the rest of the
operation.

**The scan returned unexpected output** — rare, and usually means a
script produced something that couldn't be parsed as the expected data.
Nothing is changed when this happens; check "Show Technical Details" on
the error dialog, and the application log, for specifics.

**Project Already Exists** — the generator never silently overwrites an
existing project. It shows you exactly which files would be affected and
asks first.

**Template Missing** — if a *default* template folder is missing, it's
recreated automatically the next time you open Project Generator. Custom
templates you created yourself are never auto-recreated if you delete
them, since the app has no way to know what they should contain.

**I cancelled an operation midway** — cancelling stops before further
changes are made; whatever had already completed up to that point stays
as it is (this mirrors how the underlying scripts report partial
progress — there is no automatic rollback of steps already taken).
"""

ABOUT_TEXT = """

# About WinToolkit

A unified Windows desktop utility suite built around four tools:

- Application Inventory
- Application Leftovers Cleaner
- Temporary Files Cleaner
- Project Generator

Built with Python and PySide6.

PowerShell scripts under the hood are executed only through a centralized,

allow-listed execution layer — the UI never runs arbitrary PowerShell.

## Developer

**Developed by Maysam Baradiya**

[LinkedIn](https://www.linkedin.com/in/maysam-baradiya-589757347/)

**Version:** 1.0.0

"""

SECTIONS: dict[str, tuple[str, str]] = {
    "getting_started": ("Getting Started", GETTING_STARTED),
    "dashboard": ("Dashboard Guide", DASHBOARD_GUIDE),
    "inventory": ("Application Inventory Guide", APPLICATION_INVENTORY_GUIDE),
    "leftovers": ("Application Leftovers Cleaner Guide", LEFTOVERS_CLEANER_GUIDE),
    "tempcleaner": ("Temporary Files Cleaner Guide", TEMP_CLEANER_GUIDE),
    "projectgen": ("Project Generator Guide", PROJECT_GENERATOR_GUIDE),
    "safety": ("Safety Guide", SAFETY_GUIDE),
    "permissions": ("Permissions / Administrator Guide", PERMISSIONS_GUIDE),
    "troubleshooting": ("Troubleshooting", TROUBLESHOOTING_GUIDE),
    "about": ("About the Application", ABOUT_TEXT),
}
