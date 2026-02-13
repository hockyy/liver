"""
Preview helpers – image thumbnail generation and converted-size estimation.

Keeps the expensive IO / encoding work out of the main UI module and
makes caching easy to reason about.
"""

import os
from io import BytesIO
from typing import Dict, Optional

from PIL import Image

from converter import (
    AVIF_SUPPORTED,
    build_save_kwargs,
    trim_transparent_edges,
    _scaled_trim_size,
)
from gpu import resize_image


# ---------------------------------------------------------------------------
# File-size formatting
# ---------------------------------------------------------------------------

def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_file_size_formatted(file_path: str) -> str:
    try:
        return format_file_size(os.path.getsize(file_path))
    except OSError:
        return "Unknown size"


# ---------------------------------------------------------------------------
# Size-estimation cache
# ---------------------------------------------------------------------------

class SizeEstimator:
    """
    Caches converted-size estimates keyed on
    (path, format, quality_preset, quality, target_size, trim, animated).
    """

    def __init__(self):
        self._cache: Dict[str, int] = {}

    def clear(self):
        self._cache.clear()

    # ---- public entry point ----------------------------------------------
    def estimate(
        self,
        file_path: str,
        format_text: str,
        quality: int,
        quality_preset: str,
        target_size: Optional[tuple],
        should_trim: bool,
        is_animated: bool,
        frame_count: int,
    ) -> Optional[int]:
        """
        Return the estimated size in bytes of the converted file, or None on
        error.  Results are cached.
        """
        trim_key = "_trim" if should_trim else ""
        anim_key = f"_anim_{frame_count}" if is_animated else ""
        sz = f"{target_size[0]}x{target_size[1]}" if target_size else "original"
        cache_key = f"{file_path}_{format_text}_{quality_preset}_{quality}_{sz}{trim_key}{anim_key}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            if is_animated:
                result = self._estimate_animated(
                    file_path, format_text, quality, quality_preset,
                    target_size, should_trim, frame_count,
                )
            else:
                result = self._estimate_static(
                    file_path, format_text, quality, quality_preset,
                    target_size, should_trim,
                )

            if result and result > 0:
                self._cache[cache_key] = result
            return result

        except Exception:
            return None

    # ---- internals -------------------------------------------------------
    def _estimate_static(self, file_path, format_text, quality, quality_preset,
                         target_size, should_trim) -> Optional[int]:
        with Image.open(file_path) as img:
            original_size = img.size
            if should_trim:
                img = trim_transparent_edges(img)

            # After trimming, scale proportionally instead of stretching
            if target_size:
                actual_target = _scaled_trim_size(img.size, original_size, target_size) if should_trim else target_size
                if actual_target != img.size:
                    img = resize_image(img, actual_target)

            if img.mode not in ('RGB', 'RGBA'):
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

            buf = BytesIO()
            kwargs = build_save_kwargs(format_text, quality, quality_preset)
            img.save(buf, **kwargs)
            return buf.tell()

    def _estimate_animated(self, file_path, format_text, quality, quality_preset,
                           target_size, should_trim, frame_count) -> Optional[int]:
        with Image.open(file_path) as img:
            sample_count = min(3, frame_count)
            total = 0
            sampled = 0

            for i in range(0, frame_count, max(1, frame_count // sample_count)):
                try:
                    img.seek(i)
                    frame = img.copy()

                    if frame.mode == 'P' and 'transparency' in frame.info:
                        frame = frame.convert('RGBA')
                    elif frame.mode not in ('RGB', 'RGBA'):
                        frame = frame.convert('RGB')

                    original_frame_size = frame.size
                    if should_trim and frame.mode in ('RGBA', 'LA'):
                        frame = trim_transparent_edges(frame)

                    # After trimming, scale proportionally instead of stretching
                    if target_size:
                        actual_target = _scaled_trim_size(frame.size, original_frame_size, target_size) if should_trim else target_size
                        if actual_target != frame.size:
                            frame = resize_image(frame, actual_target)

                    buf = BytesIO()
                    kwargs = build_save_kwargs(format_text, quality, quality_preset)
                    frame.save(buf, **kwargs)
                    total += buf.tell()
                    sampled += 1
                except (EOFError, OSError):
                    break

            if sampled > 0:
                avg = total / sampled
                estimated = int(avg * frame_count * 0.85)
                return max(estimated, total)

        return None


# ---------------------------------------------------------------------------
# Thumbnail for the preview pane
# ---------------------------------------------------------------------------

def make_thumbnail(file_path: str, max_w: int = 400, max_h: int = 300) -> Optional[Image.Image]:
    """
    Return a PIL Image scaled to fit inside (max_w, max_h) without up-scaling.
    Returns None on error.
    """
    try:
        with Image.open(file_path) as img:
            if img.mode not in ('RGB', 'RGBA'):
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

            w, h = img.size
            scale = min(max_w / w, max_h / h, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)

            return resize_image(img, (new_w, new_h))
    except Exception:
        return None
