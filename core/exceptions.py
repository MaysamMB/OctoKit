"""
Centralized exception hierarchy.

Every exception carries a short, non-technical `user_message` suitable for
direct display, plus an optional `technical_details` string that the UI can
place behind an expandable "Show Technical Details" section. Callers should
never need to show a raw traceback as the only explanation.
"""

from __future__ import annotations


class ToolkitError(Exception):
    """Base class for all application-raised errors."""

    default_message = "Something went wrong."

    def __init__(self, user_message: str | None = None, technical_details: str | None = None):
        self.user_message = user_message or self.default_message
        self.technical_details = technical_details
        super().__init__(self.user_message)


class PowerShellNotFoundError(ToolkitError):
    default_message = (
        "PowerShell could not be found on this system. Features that rely on "
        "PowerShell (Application Inventory, Leftovers Cleaner, Temp Files "
        "Cleaner) are unavailable until PowerShell is installed."
    )


class ScriptValidationError(ToolkitError):
    default_message = (
        "An internal script could not be verified and was not executed, "
        "for your safety."
    )


class PowerShellExecutionError(ToolkitError):
    default_message = "The requested operation could not be completed."


class PowerShellTimeoutError(ToolkitError):
    default_message = "The operation took too long and was cancelled."


class JsonParseError(ToolkitError):
    default_message = (
        "The scan returned unexpected output and could not be read. "
        "Nothing was changed on your system."
    )


class PermissionDeniedError(ToolkitError):
    default_message = (
        "Windows denied access to a protected location. This operation may "
        "require administrator privileges."
    )


class PathSafetyError(ToolkitError):
    default_message = (
        "This item was rejected by a safety check and will not be modified."
    )


class InvalidProjectNameError(ToolkitError):
    default_message = "That project name is not valid."


class ProjectAlreadyExistsError(ToolkitError):
    default_message = "A project with that name already exists at this location."


class TemplateNotFoundError(ToolkitError):
    default_message = "The selected template could not be found."


class OperationCancelledError(ToolkitError):
    default_message = "The operation was cancelled."
