"""
Centralized, cwd-independent path resolution.

Two distinct concerns live here, deliberately kept apart:

1. "Bundle" resources — files shipped WITH the application (PowerShell
   scripts, default project templates, icons). These are read-only at
   runtime and must resolve correctly whether the app is run from source
   or packaged as a frozen PyInstaller executable.

2. "User data" locations — config, logs, and the user's own editable
   template copies. These must live under a proper per-user Windows data
   directory (%LOCALAPPDATA% / %APPDATA%), never inside the installation
   folder (which may not be writable) and never derived from the current
   working directory.

Nothing in this module ever hardcodes a user-specific path such as
``C:\\Users\\SomeUser\\...``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Retain the legacy on-disk data namespace so upgrades preserve settings,
# logs and custom templates. The public application name is OctoKit.
APP_NAME = "WinToolkit"
APP_AUTHOR = "WinToolkit"


def is_frozen() -> bool:
    """True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def get_bundle_root() -> Path:
    """
    Root directory containing files shipped with the application
    (scripts/, templates/, assets/).

    - Source checkout: the directory containing this package (one level
      above `core/`).
    - PyInstaller onefile: `sys._MEIPASS`, the temporary extraction dir.
    - PyInstaller onedir: the directory containing the executable.
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_scripts_dir() -> Path:
    """Read-only directory containing the application's own .ps1 scripts."""
    return get_bundle_root() / "scripts"


def get_bundled_templates_dir() -> Path:
    """Read-only directory containing the shipped default project templates."""
    return get_bundle_root() / "templates"


def get_assets_dir() -> Path:
    return get_bundle_root() / "assets"


def _windows_env_dir(var_name: str, fallback_subdir: str) -> Path:
    """
    Resolve a Windows special-folder environment variable, with a safe
    fallback for non-Windows development/test environments. Never returns
    a hardcoded absolute user path.
    """
    value = os.environ.get(var_name)
    if value:
        return Path(value)
    # Non-Windows dev/test fallback — still derived from the environment,
    # never a literal path.
    return Path.home() / f".{fallback_subdir.lower()}"


def get_app_data_dir() -> Path:
    """
    Per-user, writable application data root.
    Windows: %LOCALAPPDATA%\\WinToolkit
    """
    base = _windows_env_dir("LOCALAPPDATA", APP_NAME)
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    """
    Per-user configuration root.
    Windows: %APPDATA%\\WinToolkit
    """
    base = _windows_env_dir("APPDATA", APP_NAME)
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "Logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_user_templates_dir() -> Path:
    """
    Writable per-user copy of project templates. Users can add their own
    templates here without touching the (potentially read-only) install
    location. Default templates are copied here on first run only, and
    never overwritten afterwards (see TemplateManager).
    """
    path = get_app_data_dir() / "Templates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_exports_dir() -> Path:
    path = get_app_data_dir() / "Exports"
    path.mkdir(parents=True, exist_ok=True)
    return path
