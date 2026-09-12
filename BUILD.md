# Building OctoKit 0.2.0

Build Windows executables on Windows 10/11 x64 using Python 3.11+.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m PyInstaller OctoKit.spec
.\dist\OctoKit\OctoKit.exe
```

Verify the title and sidebar say OctoKit, About says 0.2.0, Storage Explorer
scans a test folder, cancellation works, and the other tools still open.
See STORAGE_EXPLORER.md for detailed storage checks.

The onedir build produces dist/OctoKit/OctoKit.exe and its _internal
dependencies, including the three PowerShell scripts. Keep the complete folder.

After the Windows executable passes the checks:

```powershell
Compress-Archive -Path .\dist\OctoKit -DestinationPath .\OctoKit-v0.2.0-win64.zip
```

Attach that ZIP to release v0.2.0 using RELEASE-v0.2.0.md for release notes.
Do not upload build/, .venv/, or the executable without its dependencies.

The program is unsigned and Windows may display a SmartScreen warning.
The public name is OctoKit. Existing WinToolkit application-data directories
remain in use so upgrades preserve configuration, logs and custom templates.

Validation performed here: Linux source tests and Qt rendering. The maintainer
reported a successful Windows source trial of Storage Explorer. The newly
branded Windows executable has not yet been built or smoke-tested here.
