"""Conservative explanations, never deletion authorization."""
from pathlib import PureWindowsPath
from .models import format_size


def advice(node):
    parts = {part.casefold() for part in PureWindowsPath(node.path).parts}
    if node.status != "complete":
        return "Incomplete or excluded result. Size is a lower bound; deletion safety is unknown."
    if parts & {"windows", "system volume information", "$recycle.bin"} or parts & {
        "pagefile.sys", "hiberfil.sys", "swapfile.sys"}:
        return "System-managed data. Do not delete manually; use Windows storage settings."
    if parts & {"program files", "program files (x86)", "programdata"}:
        return "Application-managed data. Use the application's settings or uninstaller."
    if parts & {"sdk", ".android", "avd", "system-images"}:
        return "Possible development SDK/emulator data. Check project dependencies and use SDK/Device Manager. Size does not prove it is unused."
    if parts & {"cache", "caches", "temp", "tmp", "node_modules"}:
        return "Possible cache, temporary or generated data (name-based hint). Verify ownership and dependencies; prefer the owning tool's cleanup. Not certified safe to delete."
    return "Usage is unknown. Review the file and keep a backup if needed. Size and age alone cannot establish deletion safety."


def largest_path(root):
    node = root
    while node.children:
        child = node.children[0]
        percentage = child.size * 100 / node.size if node.size else 0
        qualifier = "Largest observed" if node.status != "complete" else "Largest"
        yield child, (f"{qualifier} in {node.path}: {child.path} — "
                      f"{format_size(child.size)} ({percentage:.1f}% of observed parent size).")
        node = child
