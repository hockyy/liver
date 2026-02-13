"""
GPU detection and CUDA-accelerated image processing.

Checks for available GPU acceleration backends and provides
accelerated resize/conversion when possible. Falls back to
CPU (Pillow) transparently.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Backend flags
# ---------------------------------------------------------------------------
CUDA_AVAILABLE = False
OPENCV_CUDA = False
TORCH_AVAILABLE = False

_backend = "cpu"  # "torch_cuda", "opencv_cuda", or "cpu"

# --- 1. Try PyTorch + CUDA (best general-purpose GPU path) ----------------
_gpu_name = "N/A"
_vram_mb = 0

try:
    import torch
    TORCH_AVAILABLE = True
    if torch.cuda.is_available():
        CUDA_AVAILABLE = True
        _backend = "torch_cuda"
        _device = torch.device("cuda")
        _gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        # Attribute was renamed from total_mem → total_memory in newer PyTorch
        _vram_mb = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) / (1024 * 1024)
except Exception as e:
    import traceback
    _gpu_init_error = f"PyTorch CUDA init failed: {e}\n{traceback.format_exc()}"
    print(f"[gpu.py] {_gpu_init_error}", file=sys.stderr)

# --- 2. Try OpenCV with CUDA (only if PyTorch CUDA not available) ----------
if not CUDA_AVAILABLE:
    try:
        import cv2
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            OPENCV_CUDA = True
            CUDA_AVAILABLE = True
            _backend = "opencv_cuda"
            _gpu_name = f"OpenCV CUDA device (count={cv2.cuda.getCudaEnabledDeviceCount()})"
            _vram_mb = 0  # OpenCV doesn't expose VRAM easily
    except Exception:
        pass  # OpenCV is optional, no need to report


def get_backend() -> str:
    """Return the active acceleration backend name."""
    return _backend


def get_gpu_info() -> dict:
    """Return a dict describing the GPU state for the UI status bar."""
    if _backend == "torch_cuda":
        return {
            "available": True,
            "backend": "PyTorch CUDA",
            "name": _gpu_name,
            "vram_mb": int(_vram_mb),
        }
    elif _backend == "opencv_cuda":
        return {
            "available": True,
            "backend": "OpenCV CUDA",
            "name": _gpu_name,
            "vram_mb": 0,
        }
    else:
        return {
            "available": False,
            "backend": "CPU (Pillow)",
            "name": "N/A",
            "vram_mb": 0,
        }


# ---------------------------------------------------------------------------
# Accelerated helpers
# ---------------------------------------------------------------------------
from PIL import Image
import numpy as np


def resize_image(img: Image.Image, target_size: tuple, resample=Image.LANCZOS) -> Image.Image:
    """
    Resize a PIL Image, using GPU when available.
    
    Parameters
    ----------
    img : PIL.Image.Image
    target_size : (width, height)
    resample : Pillow resampling filter (used for CPU fallback)
    
    Returns
    -------
    PIL.Image.Image  – resized image (always returned as PIL)
    """
    if img.size == target_size:
        return img

    if _backend == "torch_cuda":
        return _resize_torch(img, target_size)
    elif _backend == "opencv_cuda":
        return _resize_opencv_cuda(img, target_size)
    else:
        return img.resize(target_size, resample)


def _resize_torch(img: Image.Image, target_size: tuple) -> Image.Image:
    """Resize using PyTorch on CUDA."""
    try:
        import torch
        import torch.nn.functional as F

        mode = img.mode
        arr = np.array(img)

        # Handle different channel arrangements
        if arr.ndim == 2:
            # Grayscale
            tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).float().to(_device)
        else:
            # HWC -> NCHW
            tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float().to(_device)

        # target_size is (width, height) but F.interpolate expects (height, width)
        h, w = target_size[1], target_size[0]
        resized = F.interpolate(tensor, size=(h, w), mode="bilinear", align_corners=False)

        # Back to numpy
        if arr.ndim == 2:
            result_arr = resized.squeeze().cpu().numpy().clip(0, 255).astype(np.uint8)
        else:
            result_arr = (
                resized.squeeze(0).permute(1, 2, 0).cpu().numpy().clip(0, 255).astype(np.uint8)
            )

        return Image.fromarray(result_arr, mode=mode)

    except Exception:
        # Fallback on any error
        return img.resize(target_size, Image.LANCZOS)


def _resize_opencv_cuda(img: Image.Image, target_size: tuple) -> Image.Image:
    """Resize using OpenCV CUDA."""
    try:
        import cv2

        mode = img.mode
        arr = np.array(img)

        # Convert RGB(A) -> BGR(A) for OpenCV
        if mode == "RGB":
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        elif mode == "RGBA":
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)

        # Upload to GPU, resize, download
        gpu_mat = cv2.cuda_GpuMat()
        gpu_mat.upload(arr)
        gpu_resized = cv2.cuda.resize(gpu_mat, target_size, interpolation=cv2.INTER_LINEAR)
        result = gpu_resized.download()

        # Convert back
        if mode == "RGB":
            result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        elif mode == "RGBA":
            result = cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA)

        return Image.fromarray(result, mode=mode)

    except Exception:
        return img.resize(target_size, Image.LANCZOS)


# ---------------------------------------------------------------------------
# Batch processing helper (for future threaded conversion)
# ---------------------------------------------------------------------------
def process_image_for_save(img: Image.Image, target_size=None, should_trim=False, trim_func=None):
    """
    Apply resize + optional trim on the GPU path.
    Returns a processed PIL.Image ready for .save().
    """
    if should_trim and trim_func:
        img = trim_func(img)

    if target_size and img.size != target_size:
        img = resize_image(img, target_size)

    # Ensure compatible mode
    if img.mode not in ("RGB", "RGBA"):
        if img.mode == "P" and "transparency" in img.info:
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

    return img
