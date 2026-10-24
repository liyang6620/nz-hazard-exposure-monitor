from __future__ import annotations

import ctypes
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


class ResourceLimitExceeded(RuntimeError):
    """Raised before local processing can exhaust memory or the workspace drive."""


def _rss_bytes() -> int:
    if os.name == "nt":

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        get_current_process = ctypes.windll.kernel32.GetCurrentProcess  # type: ignore[attr-defined]
        get_current_process.restype = ctypes.c_void_p
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined]
        get_process_memory_info.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        get_process_memory_info.restype = ctypes.c_int
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = get_current_process()
        success = get_process_memory_info(handle, ctypes.byref(counters), counters.cb)
        if success:
            return int(counters.WorkingSetSize)

    status = Path("/proc/self/status")
    if status.exists():
        for line in status.read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    return 0


@dataclass
class ResourceGuard:
    path: Path
    min_free_disk_gb: float = 20.0
    max_rss_mb: int = 768
    minimum_free_disk_gb: float = field(default=float("inf"), init=False)
    peak_rss_mb: float = field(default=0.0, init=False)

    def check(self, *, required_free_bytes: int = 0) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        free_bytes = shutil.disk_usage(self.path).free
        free_gb = free_bytes / (1024**3)
        rss_mb = _rss_bytes() / (1024**2)
        self.minimum_free_disk_gb = min(self.minimum_free_disk_gb, free_gb)
        self.peak_rss_mb = max(self.peak_rss_mb, rss_mb)
        if free_gb < self.min_free_disk_gb:
            raise ResourceLimitExceeded(
                f"Free disk is {free_gb:.2f} GB; stopping before the "
                f"{self.min_free_disk_gb:.2f} GB floor"
            )
        remaining_gb = (free_bytes - required_free_bytes) / (1024**3)
        if remaining_gb < self.min_free_disk_gb:
            required_gb = required_free_bytes / (1024**3)
            raise ResourceLimitExceeded(
                f"Operation needs {required_gb:.2f} GB; projected free disk is "
                f"{remaining_gb:.2f} GB, below the {self.min_free_disk_gb:.2f} GB floor"
            )
        if rss_mb > self.max_rss_mb:
            raise ResourceLimitExceeded(
                f"Process RSS is {rss_mb:.1f} MB; stopping above the {self.max_rss_mb} MB ceiling"
            )
