"""
Image conversion logic for static and animated images.

All heavy lifting lives here so the UI module stays lean.
Uses gpu.resize_image() automatically when a CUDA backend is available.
"""

import os
from PIL import Image

from gpu import resize_image, process_image_for_save

# Re-export AVIF flag so callers can check without extra imports
try:
    import pillow_avif
    AVIF_SUPPORTED = True
except ImportError:
    AVIF_SUPPORTED = False

# Supported input extensions
VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.webp'}
if AVIF_SUPPORTED:
    VALID_EXTENSIONS.add('.avif')

# File dialog filter string
FILE_FILTER = 'Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.gif *.webp'
if AVIF_SUPPORTED:
    FILE_FILTER += ' *.avif'
FILE_FILTER += ')'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_image_file(file_path: str) -> bool:
    """Return True if *file_path* is a file with a supported image extension."""
    if not os.path.isfile(file_path):
        return False
    _, ext = os.path.splitext(file_path.lower())
    return ext in VALID_EXTENSIONS


def trim_transparent_edges(img: Image.Image) -> Image.Image:
    """Crop away fully-transparent borders (RGBA / LA images only)."""
    if img.mode in ('RGBA', 'LA'):
        bbox = img.getbbox()
        if bbox:
            return img.crop(bbox)
    return img


def build_save_kwargs(format_text: str, quality: int, quality_preset: str, animated: bool = False) -> dict:
    """
    Build the keyword arguments dict for ``Image.save()``.

    Parameters
    ----------
    format_text : "WebP" or "AVIF"
    quality : 1-100
    quality_preset : e.g. "Best (Lossless)", "Custom", etc.
    animated : if True, include ``save_all`` / ``loop`` keys

    Returns
    -------
    dict  – ready to be unpacked into ``img.save(path, **kwargs)``
    """
    kwargs: dict = {}

    if format_text == 'AVIF':
        kwargs['format'] = 'AVIF'
        if quality_preset == 'Best (Lossless)':
            kwargs['lossless'] = True
            kwargs['speed'] = 0
        else:
            kwargs['quality'] = quality
            kwargs['speed'] = 4
    else:  # WebP
        kwargs['format'] = 'WEBP'
        if quality_preset == 'Best (Lossless)':
            kwargs['lossless'] = True
            kwargs['method'] = 6
        else:
            kwargs['quality'] = quality
            kwargs['method'] = 4

    if animated:
        kwargs['loop'] = 0  # infinite loop

    return kwargs


def _ensure_mode(img: Image.Image) -> Image.Image:
    """Convert to RGB/RGBA if the current mode is unsupported for saving."""
    if img.mode not in ('RGB', 'RGBA'):
        if img.mode == 'P' and 'transparency' in img.info:
            return img.convert('RGBA')
        return img.convert('RGB')
    return img


# ---------------------------------------------------------------------------
# Conversion entry-points
# ---------------------------------------------------------------------------

def _scaled_trim_size(trimmed_size: tuple, original_size: tuple, new_size: tuple) -> tuple:
    """
    After trimming, calculate the correct resize target that preserves
    the trim crop rather than stretching back to the full dimensions.

    If the user requested a resize (new_size != original_size), we apply
    the same scale factor to the trimmed dimensions. Otherwise we keep
    the trimmed size as-is.
    """
    if new_size == original_size:
        return trimmed_size  # No resize requested → keep trimmed size

    # Calculate the scale the user intended relative to the original
    scale_w = new_size[0] / original_size[0]
    scale_h = new_size[1] / original_size[1]
    return (
        max(1, int(trimmed_size[0] * scale_w)),
        max(1, int(trimmed_size[1] * scale_h)),
    )


def convert_static(
    input_path: str,
    output_path: str,
    new_size: tuple,
    original_size: tuple,
    format_text: str,
    quality: int,
    quality_preset: str,
    should_trim: bool,
):
    """Convert a single static image (or the first frame of an animated one)."""
    with Image.open(input_path) as img:
        if should_trim:
            img = trim_transparent_edges(img)

        # Determine the correct target size after trimming
        target = _scaled_trim_size(img.size, original_size, new_size) if should_trim else new_size

        if target != img.size:
            img = resize_image(img, target)

        img = _ensure_mode(img)

        save_kwargs = build_save_kwargs(format_text, quality, quality_preset)
        img.save(output_path, **save_kwargs)


def convert_animated(
    input_path: str,
    output_path: str,
    new_size: tuple,
    original_size: tuple,
    frame_count: int,
    format_text: str,
    quality: int,
    quality_preset: str,
    should_trim: bool,
):
    """
    Convert an animated image preserving all frames.

    Falls back to ``convert_static`` on error.
    """
    with Image.open(input_path) as img:
        frames = []
        durations = []

        try:
            for idx in range(frame_count):
                img.seek(idx)
                frame = img.copy()

                # Palette → RGBA / RGB
                if frame.mode == 'P':
                    frame = frame.convert('RGBA' if 'transparency' in frame.info else 'RGB')

                if should_trim and frame.mode in ('RGBA', 'LA'):
                    frame = trim_transparent_edges(frame)

                # Determine the correct target size after trimming
                target = _scaled_trim_size(frame.size, original_size, new_size) if should_trim else new_size

                if target != frame.size:
                    frame = resize_image(frame, target)

                frame = _ensure_mode(frame)
                frames.append(frame)
                durations.append(frame.info.get('duration', 100))

            if frames:
                save_kwargs = build_save_kwargs(format_text, quality, quality_preset, animated=True)
                save_kwargs['save_all'] = True
                save_kwargs['append_images'] = frames[1:]
                save_kwargs['duration'] = durations
                frames[0].save(output_path, **save_kwargs)

        except Exception:
            # Fallback to first-frame conversion
            convert_static(
                input_path, output_path,
                new_size, original_size,
                format_text, quality, quality_preset, should_trim,
            )


def get_output_path(input_path: str, format_text: str) -> str:
    """Return the output file path with the correct extension."""
    ext = '.avif' if format_text == 'AVIF' else '.webp'
    return os.path.splitext(input_path)[0] + ext
