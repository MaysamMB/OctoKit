from .scanner import scan
from .windows_api import list_drives


class StorageService:
    list_drives = staticmethod(list_drives)
    scan = staticmethod(scan)
