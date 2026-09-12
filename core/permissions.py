"""
Administrator-privilege detection.

The application runs as a normal user by default and never requests
elevation for itself at startup (spec section 16). Elevation, when needed,
is requested per-operation by core.powershell.PowerShellService, which
launches only the single required script elevated rather than relaunching
the whole application.
"""

from __future__ import annotations

import sys

from core.logger import get_logger

logger = get_logger("core.permissions")


def is_admin() -> bool:
    """
    True if the current process is running with Administrator privileges.
    Always False on non-Windows platforms (used during development/tests).
    """
    if sys.platform != "win32":
        return False

    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - never let a permissions check crash the app
        logger.warning("Could not determine administrator status; assuming non-admin.")
        return False


def platform_supports_elevation() -> bool:
    return sys.platform == "win32"
