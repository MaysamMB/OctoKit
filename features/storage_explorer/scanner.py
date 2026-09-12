"""Bounded, iterative metadata-only scanner; never opens file contents.

Logical bytes are counted per directory entry, NOT reclaimable physical bytes.
Reparse/cloud entries and cross-device directory mounts are excluded. Results
are a best-effort observation, not an atomic filesystem snapshot.
"""
import heapq
import os
import stat
import time
from datetime import datetime
from pathlib import Path
from .models import Node, ScanResult, format_size

# REPARSE_POINT, OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS.
EXCLUDED_ATTRIBUTES = 0x400 | 0x1000 | 0x40000 | 0x400000


def excluded(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & EXCLUDED_ATTRIBUTES)


def validate_root(path):
    path = os.path.abspath(os.fspath(path))
    if os.name == "nt" and path.startswith("\\\\"):
        raise ValueError("Network and device paths are not supported.")
    # Reject links/cloud placeholders anywhere in the selected path.
    for part in reversed((Path(path), *Path(path).parents)):
        if excluded(os.lstat(part)):
            raise ValueError("Linked or cloud-placeholder paths are not scanned.")
    return path


def scan(path, *, progress_callback=None, cancel_event=None, max_nodes=300_000):
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    path = validate_root(path)
    root = Node(path)
    result = ScanResult(root)
    nodes = [root]
    pending = [root]
    biggest = []
    root_device = os.lstat(path).st_dev
    last_update = 0.0
    discovered_bytes = 0
    while pending:
        if cancel_event and cancel_event.is_set():
            result.cancelled = True
            break
        node = pending.pop()
        now = time.monotonic()
        if progress_callback and now - last_update >= .2:
            progress_callback(f"Scanning {node.path} | {result.files:,} files | "
                              f"{format_size(discovered_bytes)} discovered (provisional)")
            last_update = now
        try:
            info = os.lstat(node.path)
            if excluded(info) or info.st_dev != root_device:
                node.status = "excluded link/cloud/mount"
                result.skipped += 1
                continue
            node.is_dir = stat.S_ISDIR(info.st_mode)
            if node.is_dir:
                with os.scandir(node.path) as entries:
                    for entry in entries:
                        if cancel_event and cancel_event.is_set():
                            result.cancelled = True
                            break
                        if len(nodes) >= max_nodes:
                            result.limited = True
                            break
                        child = Node(entry.path, parent=node)
                        node.children.append(child)
                        nodes.append(child)
                        pending.append(child)
                node.status = "partial" if result.cancelled or result.limited else "complete"
                if result.cancelled or result.limited:
                    break
            elif stat.S_ISREG(info.st_mode):
                node.size = info.st_size
                discovered_bytes += node.size
                result.files += 1
                result.hardlink_entries += int(info.st_nlink > 1)
                node.status = "complete"
                candidate = (node.size, node.path, node)
                if len(biggest) < 100:
                    heapq.heappush(biggest, candidate)
                elif candidate[:2] > biggest[0][:2]:
                    heapq.heapreplace(biggest, candidate)
            else:
                node.status = "excluded special file"
                result.skipped += 1
        except OSError as exc:
            node.status = f"unavailable ({type(exc).__name__})"
            result.skipped += 1
    # Parents always precede descendants in nodes: aggregate bottom-up.
    for node in reversed(nodes):
        if node.children:
            node.children.sort(key=lambda item: (-item.size, item.path.casefold()))
            for row, child in enumerate(node.children):
                child.row = row
            node.size = sum(child.size for child in node.children)
            if any(child.status != "complete" for child in node.children):
                node.status = "partial"
        if node.status == "pending":
            node.status = "not scanned"
    if result.cancelled or result.limited:
        root.status = "partial"
    result.largest_files = [item[2] for item in sorted(biggest, reverse=True)]
    result.finished_at = datetime.now()
    if progress_callback:
        progress_callback(f"Scan ended: {root.status}; {result.files:,} files; "
                          f"{result.skipped:,} excluded/unavailable.")
    return result
