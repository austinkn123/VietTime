"""Background sampling of GPU memory (via nvidia-smi) and system RAM, keeping the peaks."""

import shutil
import subprocess
import threading


def gpu_memory_mb() -> tuple[int, int] | None:
    """(used, total) MB for the first GPU, or None without nvidia-smi."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        used, total = (int(x) for x in out.splitlines()[0].split(","))
        return used, total
    except (subprocess.SubprocessError, ValueError, IndexError):
        return None


def ram_mb() -> tuple[int, int]:
    import psutil

    vm = psutil.virtual_memory()
    return (vm.total - vm.available) // 2**20, vm.total // 2**20


class ResourceMonitor:
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.gpu_total_mb = None
        self.gpu_peak_mb = 0
        self.ram_total_mb = None
        self.ram_peak_mb = 0
        self.snapshots: list[dict] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _sample(self) -> dict:
        row = {}
        gpu = gpu_memory_mb()
        if gpu:
            row["gpu_used_mb"], self.gpu_total_mb = gpu
            self.gpu_peak_mb = max(self.gpu_peak_mb, gpu[0])
        row["ram_used_mb"], self.ram_total_mb = ram_mb()
        self.ram_peak_mb = max(self.ram_peak_mb, row["ram_used_mb"])
        return row

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self._sample()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def snapshot(self, label: str) -> dict:
        row = {"label": label, **self._sample()}
        self.snapshots.append(row)
        return row
