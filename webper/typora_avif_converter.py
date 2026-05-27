#!/usr/bin/env python3
"""
Typora AVIF converter (size-target via bisection)

- Keeps AVIF quality fixed (default: 80)
- Binary-searches image scale until output size is within target range (default: 80-100 KB)
- Saves .avif in same directory as source image
- Prints Typora-friendly path to stdout:
    - ./assets/...  (if output path contains assets/)
    - file://...    (fallback)
"""

import argparse
import io
import sys
from pathlib import Path
from PIL import Image
import pillow_avif  # noqa: F401 (registers AVIF plugin)
from urllib.request import pathname2url


def prepare_rgb(img: Image.Image) -> Image.Image:
    """Convert image to RGB, flatten alpha onto white background when needed."""
    if img.mode in ("RGBA", "LA", "P"):
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode == "LA":
            # Convert LA -> RGBA so alpha handling is consistent
            img = img.convert("RGBA")

        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        background.paste(img, mask=alpha)
        return background.copy()

    if img.mode != "RGB":
        return img.convert("RGB").copy()

    return img.copy()  # IMPORTANT: detach from file handle

def encode_avif_bytes(base_img: Image.Image, scale: float, quality: int, speed: int):
    """Return (bytes, size_bytes, (w, h)) for AVIF encoded resized image."""
    w0, h0 = base_img.size
    w = max(1, int(round(w0 * scale)))
    h = max(1, int(round(h0 * scale)))

    img = base_img if (w, h) == base_img.size else base_img.resize((w, h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="AVIF", quality=quality, speed=speed)
    data = buf.getvalue()
    return data, len(data), (w, h)


def unique_output_path(src: Path, suffix: str = ".avif") -> Path:
    """Avoid overwriting existing files."""
    out = src.with_suffix(suffix)
    if not out.exists():
        return out

    i = 1
    while True:
        candidate = src.with_name(f"{src.stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def choose_better(candidate, best, min_b, max_b, target_mid):
    """
    candidate/best = (data, size_bytes, (w,h), scale)
    Prefer in-range candidates; otherwise closest to midpoint.
    """
    if best is None:
        return candidate

    _, c_size, _, _ = candidate
    _, b_size, _, _ = best

    c_in = min_b <= c_size <= max_b
    b_in = min_b <= b_size <= max_b

    if c_in and not b_in:
        return candidate
    if b_in and not c_in:
        return best

    return candidate if abs(c_size - target_mid) < abs(b_size - target_mid) else best


def bisect_scale_to_size(
    img: Image.Image,
    min_kb: int = 80,
    max_kb: int = 100,
    quality: int = 80,
    speed: int = 0,
    max_iter: int = 5,
    min_scale: float = 0.05,
    max_upscale: float = 1.0,
):
    """Binary-search scale so encoded AVIF size lands in [min_kb, max_kb]."""
    min_b = min_kb * 1024
    max_b = max_kb * 1024
    target_mid = (min_b + max_b) // 2

    d1, s1, wh1 = encode_avif_bytes(img, 1.0, quality, speed)
    best = (d1, s1, wh1, 1.0)
    if min_b <= s1 <= max_b:
        return best

    if s1 > max_b:
        # Need downscale
        low, high = min_scale, 1.0
    else:
        # Need upscale
        low, high = 1.0, 2.0
        d_hi, s_hi, wh_hi = encode_avif_bytes(img, high, quality, speed)
        best = choose_better((d_hi, s_hi, wh_hi, high), best, min_b, max_b, target_mid)

        while s_hi < min_b and high < max_upscale:
            low = high
            high = min(high * 2.0, max_upscale)
            d_hi, s_hi, wh_hi = encode_avif_bytes(img, high, quality, speed)
            best = choose_better((d_hi, s_hi, wh_hi, high), best, min_b, max_b, target_mid)

        if s_hi < min_b and high >= max_upscale:
            return best

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        d, s, wh = encode_avif_bytes(img, mid, quality, speed)
        cand = (d, s, wh, mid)
        best = choose_better(cand, best, min_b, max_b, target_mid)

        if min_b <= s <= max_b:
            return cand

        if s < min_b:
            low = mid
        else:
            high = mid

        if abs(high - low) < 1e-4:
            break

    return best


def to_typora_path(output_path: Path) -> str:
    """
    Return Typora-friendly path:
      - './assets/...' if path contains assets/
      - otherwise file:// URL
    """
    abs_path = str(output_path.resolve())
    posix_abs = abs_path.replace("\\", "/")
    marker = "/assets/"

    idx = posix_abs.lower().find(marker)
    if idx != -1:
        return "." + posix_abs[idx:]  # -> ./assets/...

    # Fallback to file:// URL
    file_url = pathname2url(abs_path)
    if not file_url.startswith("/"):
        file_url = "/" + file_url
    return "file://" + file_url


def main():
    parser = argparse.ArgumentParser(description="Convert image to AVIF with size-target bisection for Typora.")
    parser.add_argument("image_path", help="Input image path")
    parser.add_argument("--min-kb", type=int, default=80, help="Minimum target KB (default: 80)")
    parser.add_argument("--max-kb", type=int, default=100, help="Maximum target KB (default: 100)")
    parser.add_argument("--quality", type=int, default=80, help="AVIF quality (default: 80)")
    parser.add_argument("--speed", type=int, default=0, help="AVIF speed (default: 0)")
    parser.add_argument("--max-iter", type=int, default=24, help="Bisection iterations (default: 24)")
    parser.add_argument("--verbose", action="store_true", help="Print debug info to stderr")
    args = parser.parse_args()

    src = Path(args.image_path)
    if not src.exists():
        sys.stderr.write(f"Error: Image file not found: {src}\n")
        sys.exit(1)

    if args.min_kb <= 0 or args.max_kb <= 0 or args.min_kb > args.max_kb:
        sys.stderr.write("Error: invalid size range. Use 0 < min-kb <= max-kb.\n")
        sys.exit(1)

    try:
        with Image.open(src) as im:
            base_img = prepare_rgb(im)

        data, size_bytes, (w, h), scale = bisect_scale_to_size(
            base_img,
            min_kb=args.min_kb,
            max_kb=args.max_kb,
            quality=args.quality,
            speed=args.speed,
            max_iter=args.max_iter,
        )

        out_path = unique_output_path(src, ".avif")
        out_path.write_bytes(data)

        typora_path = to_typora_path(out_path)

        # IMPORTANT: Typora generally expects path on stdout
        print(typora_path)

        if args.verbose:
            sys.stderr.write(
                f"[info] saved={out_path}\n"
                f"[info] size={size_bytes/1024:.2f}KB, dims={w}x{h}, scale={scale:.4f}, "
                f"quality={args.quality}, speed={args.speed}\n"
            )

    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
