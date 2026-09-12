"""
Small shared models/enums used across more than one layer. Feature-specific
models (ApplicationInfo, LeftoverItem, CleanupItem, ProjectTemplate, ...)
live in each feature's own `models.py` — this module only holds things with
no natural feature owner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Confidence(str, Enum):
    """Safety/confidence classification shown to the user before any
    destructive action. Anything other than SAFE must default to
    unselected in the UI."""

    SAFE = "Safe / Recommended"
    SUSPICIOUS = "Suspicious"
    UNKNOWN = "Unknown"


@dataclass
class PowerShellResult:
    """Structured result of a single PowerShell script invocation."""

    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    data: object | None = None
    timed_out: bool = False
    warnings: list[str] = field(default_factory=list)
