from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Node:
    path: str
    is_dir: bool = False
    size: int = 0
    status: str = "pending"
    parent: "Node | None" = field(default=None, repr=False)
    children: list = field(default_factory=list, repr=False)
    row: int = 0


@dataclass
class ScanResult:
    root: Node
    files: int = 0
    skipped: int = 0
    cancelled: bool = False
    limited: bool = False
    hardlink_entries: int = 0
    largest_files: list = field(default_factory=list)
    finished_at: datetime | None = None


@dataclass(frozen=True)
class Drive:
    path: str
    total: int
    used: int
    free: int

    @property
    def percent(self):
        return 100 * self.used / self.total if self.total else 0


def format_size(value):
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
