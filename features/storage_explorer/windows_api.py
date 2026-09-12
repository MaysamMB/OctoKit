"""Read-only fixed-drive discovery. No elevation, shells or network drives."""
import ctypes
import os
import shutil
from .models import Drive


def list_drives():
    if os.name != "nt":
        paths = [os.path.abspath(os.sep)]
    else:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetLogicalDrives.restype = ctypes.c_uint32
        kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        kernel.GetDriveTypeW.restype = ctypes.c_uint32
        mask = kernel.GetLogicalDrives()
        if not mask:
            raise ctypes.WinError(ctypes.get_last_error())
        paths = [f"{chr(65+i)}:\\" for i in range(26)
                 if mask & (1 << i) and kernel.GetDriveTypeW(f"{chr(65+i)}:\\") == 3]
    drives, unavailable = [], []
    for path in paths:
        try:
            usage = shutil.disk_usage(path)
            drives.append(Drive(path, usage.total, usage.used, usage.free))
        except OSError:
            unavailable.append(path)
    return sorted(drives, key=lambda d: (-d.used, d.path)), unavailable
