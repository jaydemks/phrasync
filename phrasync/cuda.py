from __future__ import annotations

import ctypes
import os
import site
import sys
from pathlib import Path

_DLL_HANDLES: list[object] = []
_CONFIGURED_PATHS: list[str] = []


def _existing(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if resolved.is_dir() and key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def windows_cuda_directories() -> list[Path]:
    """Discover CUDA/cuDNN DLL folders without machine-specific paths."""
    if os.name != "nt":
        return []

    candidates: list[Path] = []
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidates.append(Path(cuda_path) / "bin")

    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    cuda_root = program_files / "NVIDIA GPU Computing Toolkit" / "CUDA"
    if cuda_root.is_dir():
        candidates.extend(path / "bin" for path in sorted(cuda_root.glob("v*"), reverse=True))

    cudnn_root = program_files / "NVIDIA" / "CUDNN"
    if cudnn_root.is_dir():
        for version in sorted(cudnn_root.glob("v*"), reverse=True):
            bin_dir = version / "bin"
            candidates.append(bin_dir)
            if bin_dir.is_dir():
                candidates.extend(sorted((path for path in bin_dir.iterdir() if path.is_dir()), reverse=True))

    site_roots = [Path(sys.prefix) / "Lib" / "site-packages"]
    try:
        site_roots.extend(Path(path) for path in site.getsitepackages())
    except AttributeError:
        pass
    for root in site_roots:
        candidates.extend((root / "nvidia" / package / "bin" for package in ("cublas", "cudnn")))

    return _existing(candidates)


def configure_cuda_paths() -> list[str]:
    """Expose discovered DLL folders to this Python process on Windows."""
    global _CONFIGURED_PATHS
    if os.name != "nt" or _CONFIGURED_PATHS:
        return list(_CONFIGURED_PATHS)

    directories = windows_cuda_directories()
    for directory in directories:
        try:
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
        except (AttributeError, OSError):
            pass

    if directories:
        current = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join([*(str(path) for path in directories), current])
    _CONFIGURED_PATHS = [str(path) for path in directories]
    return list(_CONFIGURED_PATHS)


def cuda_runtime_available() -> bool:
    """Check the runtime libraries CTranslate2 needs before selecting CUDA."""
    configure_cuda_paths()
    libraries = (
        ("cublas64_12.dll", "cudnn_ops64_9.dll")
        if os.name == "nt"
        else ("libcublas.so.12", "libcudnn_ops.so.9")
    )
    try:
        for library in libraries:
            ctypes.CDLL(library)
    except OSError:
        return False
    return True
