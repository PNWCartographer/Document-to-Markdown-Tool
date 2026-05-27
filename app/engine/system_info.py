"""
System hardware detection for performance auto-configuration.

Detects CPU, RAM, GPU, and available ONNX Runtime execution providers
to automatically configure parallel workers and chunk sizes.

All detection is local. No data is transmitted externally.
"""

import os
import sys
import platform
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SystemInfo:
    """Detected system hardware capabilities."""
    cpu_name: str = "Unknown"
    cpu_cores: int = 1
    ram_gb: float = 0.0
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    gpu_provider: str = "cpu"       # "cuda", "directml", "coreml", "cpu"
    onnx_providers: list[str] = field(default_factory=list)
    recommended_workers: int = 1
    recommended_chunk_size: int = 20


# ---------------------------------------------------------------------------
# Cached result — detect once per process
# ---------------------------------------------------------------------------

_cached_info: Optional[SystemInfo] = None


def detect_system() -> SystemInfo:
    """Detect system hardware. Results are cached after first call."""
    global _cached_info
    if _cached_info is not None:
        return _cached_info

    info = SystemInfo()

    # CPU
    info.cpu_cores = os.cpu_count() or 1
    info.cpu_name = _detect_cpu_name()

    # RAM
    info.ram_gb = _detect_ram_gb()

    # GPU (NVIDIA via pynvml, AMD/Intel via OS query)
    gpu_name, gpu_vram = _detect_gpu()
    if gpu_name:
        info.gpu_name = gpu_name
        info.gpu_vram_gb = gpu_vram

    # ONNX Runtime execution providers
    info.onnx_providers = _detect_onnx_providers()

    # Determine best GPU acceleration provider
    info.gpu_provider = _select_gpu_provider(info.onnx_providers)

    # Auto-configure performance
    info.recommended_workers = _calc_workers(info.cpu_cores, info.ram_gb)
    info.recommended_chunk_size = _calc_chunk_size(info.ram_gb)

    _cached_info = info
    return info


# ---------------------------------------------------------------------------
# CPU detection
# ---------------------------------------------------------------------------

def _detect_cpu_name() -> str:
    """Get CPU model name from the OS."""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return name.strip()
        elif sys.platform == "darwin":
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        else:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"


# ---------------------------------------------------------------------------
# RAM detection
# ---------------------------------------------------------------------------

def _detect_ram_gb() -> float:
    """Get total system RAM in GB."""
    # Try psutil first (cross-platform, most reliable)
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        pass

    # Windows fallback via ctypes
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass

    # Linux fallback
    if sys.platform == "linux":
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 ** 2), 1)
        except Exception:
            pass

    # macOS fallback
    if sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return round(int(result.stdout.strip()) / (1024 ** 3), 1)
        except Exception:
            pass

    return 0.0


# ---------------------------------------------------------------------------
# GPU detection
# ---------------------------------------------------------------------------

def _detect_gpu() -> tuple[Optional[str], Optional[float]]:
    """Detect GPU name and VRAM.

    Tries NVIDIA via pynvml first (provides VRAM info), then falls back
    to platform-specific queries for AMD/Intel GPUs (name only, no VRAM).
    """
    # Try NVIDIA first (gives us VRAM)
    name, vram = _detect_nvidia_gpu()
    if name:
        return name, vram

    # Fallback: detect any GPU via OS queries (AMD, Intel, etc.)
    name = _detect_gpu_platform()
    if name:
        return name, None

    return None, None


def _detect_nvidia_gpu() -> tuple[Optional[str], Optional[float]]:
    """Detect NVIDIA GPU name and VRAM via nvidia-ml-py (pynvml)."""
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*pynvml.*deprecated.*")
            import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_gb = round(mem.total / (1024 ** 3), 1)
        pynvml.nvmlShutdown()
        return name, vram_gb
    except Exception:
        return None, None


def _detect_gpu_platform() -> Optional[str]:
    """Detect GPU name via platform-specific OS queries (AMD, Intel, etc.)."""
    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                lines = [ln.strip() for ln in result.stdout.splitlines()
                         if ln.strip() and ln.strip().lower() != "name"]
                if lines:
                    return lines[0]
        except Exception:
            pass
    elif sys.platform == "linux":
        try:
            import subprocess
            result = subprocess.run(
                ["lspci"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "VGA" in line or "3D" in line or "Display" in line:
                        # Extract device name after the colon
                        parts = line.split(": ", 1)
                        if len(parts) > 1:
                            return parts[1].strip()
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Chipset Model:"):
                        return stripped.split(":", 1)[1].strip()
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# ONNX Runtime provider detection
# ---------------------------------------------------------------------------

def _detect_onnx_providers() -> list[str]:
    """Get available ONNX Runtime execution providers."""
    try:
        import onnxruntime
        return onnxruntime.get_available_providers()
    except ImportError:
        return ["CPUExecutionProvider"]
    except Exception:
        return ["CPUExecutionProvider"]


def _select_gpu_provider(providers: list[str]) -> str:
    """Select the best GPU provider. Priority: CUDA > DirectML > CoreML > CPU."""
    if "CUDAExecutionProvider" in providers:
        return "cuda"
    if "DmlExecutionProvider" in providers:
        return "directml"
    if "CoreMLExecutionProvider" in providers:
        return "coreml"
    return "cpu"


# ---------------------------------------------------------------------------
# Auto-configuration
# ---------------------------------------------------------------------------

def _calc_workers(cpu_cores: int, ram_gb: float) -> int:
    """Calculate recommended parallel workers based on hardware."""
    if ram_gb <= 0:
        return 1
    workers = min(cpu_cores - 1, int((ram_gb - 2) / 1.5))
    return max(1, min(workers, 8))


def _calc_chunk_size(ram_gb: float) -> int:
    """Calculate recommended pages per chunk for auto-chunking large documents."""
    if ram_gb >= 16:
        return 30
    if ram_gb >= 8:
        return 25
    return 20


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_summary(info: SystemInfo) -> str:
    """Format system info as a multi-line human-readable summary."""
    lines = [
        f"CPU: {info.cpu_name} ({info.cpu_cores} cores)",
        f"RAM: {info.ram_gb} GB",
    ]
    if info.gpu_name:
        vram = f" ({info.gpu_vram_gb} GB VRAM)" if info.gpu_vram_gb else ""
        lines.append(f"GPU: {info.gpu_name}{vram}")
    else:
        lines.append("GPU: None detected")

    provider_labels = {
        "cuda": "CUDA",
        "directml": "DirectML",
        "coreml": "CoreML",
        "cpu": "CPU only",
    }
    lines.append(f"Accelerator: {provider_labels.get(info.gpu_provider, info.gpu_provider)}")
    lines.append(f"Recommended workers: {info.recommended_workers}")
    return "\n".join(lines)


def format_oneline(info: SystemInfo) -> str:
    """Format system info as a short single-line summary for the About window."""
    gpu = info.gpu_name or "No GPU"
    provider_labels = {
        "cuda": "CUDA",
        "directml": "DirectML",
        "coreml": "CoreML",
        "cpu": "CPU",
    }
    accel = provider_labels.get(info.gpu_provider, info.gpu_provider)
    return f"{info.cpu_cores} cores, {info.ram_gb} GB RAM, {gpu} ({accel})"
