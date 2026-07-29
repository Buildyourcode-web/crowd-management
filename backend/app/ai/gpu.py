"""
GPU Detection — Task 2.

Detects CUDA availability, GPU name, memory, Torch version.
Provides a single get_gpu_info() function used at startup and in the AI status API.
"""
from typing import Any, Dict, Optional

from loguru import logger


def get_gpu_info() -> Dict[str, Any]:
    """
    Probe the runtime for GPU / CUDA availability.

    Returns a dict with:
        device         — "cuda" or "cpu"
        gpu_name       — GPU display name, or None if CPU-only
        gpu_memory_mb  — Total VRAM in MB, or None if CPU-only
        cuda_available — bool
        torch_version  — installed PyTorch version string
        cuda_version   — CUDA toolkit version string, or None
    """
    try:
        import torch  # lazy import — avoids hard crash if torch is missing

        cuda_available: bool = torch.cuda.is_available()
        device: str = "cuda" if cuda_available else "cpu"

        gpu_name: Optional[str] = None
        gpu_memory_mb: Optional[int] = None
        cuda_version: Optional[str] = None

        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            gpu_memory_mb = props.total_memory // (1024 * 1024)
            cuda_version = torch.version.cuda

        return {
            "device": device,
            "gpu_name": gpu_name,
            "gpu_memory_mb": gpu_memory_mb,
            "cuda_available": cuda_available,
            "torch_version": torch.__version__,
            "cuda_version": cuda_version,
        }

    except ImportError:
        logger.warning("PyTorch not installed — GPU detection skipped, using CPU")
        return {
            "device": "cpu",
            "gpu_name": None,
            "gpu_memory_mb": None,
            "cuda_available": False,
            "torch_version": "not installed",
            "cuda_version": None,
        }
    except Exception as exc:
        logger.error("GPU detection failed | error={err}", err=str(exc))
        return {
            "device": "cpu",
            "gpu_name": None,
            "gpu_memory_mb": None,
            "cuda_available": False,
            "torch_version": "unknown",
            "cuda_version": None,
        }


def log_gpu_info() -> Dict[str, Any]:
    """
    Run get_gpu_info() and log a structured summary.
    Returns the same dict for further use.
    """
    info = get_gpu_info()

    if info["cuda_available"]:
        logger.info(
            "GPU detected | name={name} | memory={mem}MB | "
            "CUDA={cuda} | torch={torch}",
            name=info["gpu_name"],
            mem=info["gpu_memory_mb"],
            cuda=info["cuda_version"],
            torch=info["torch_version"],
        )
    else:
        logger.warning(
            "No GPU detected — running on CPU | torch={torch}",
            torch=info["torch_version"],
        )

    return info
