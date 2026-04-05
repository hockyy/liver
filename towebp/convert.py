"""
Video to animated WebP / AVIF converter
Converts common video formats to animated WebP or AVIF with optimized file size.
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Extensions we treat as video input (case-insensitive)
VIDEO_EXTENSIONS = frozenset(
    ".mov .mp4 .m4v .webm .mkv .avi .wmv .flv .ogv .mpeg .mpg".split()
)


def quality_to_avif_crf(quality: int) -> int:
    """Map 0–100 quality to libaom CRF 63–0 (lower CRF = better quality)."""
    return max(0, min(63, int(63 - (quality / 100 * 63))))


def convert_video(
    input_path: str,
    output_path: str | None = None,
    quality: int = 75,
    fps: int = 15,
    width: int | None = None,
    loop: int = 0,
    start_time: float | None = None,
    duration: float | None = None,
    output_format: str = "webp",
    speed: float = 1.0,
) -> str:
    """
    Convert a video file to animated WebP or AVIF.

    Args:
        input_path: Path to input video
        output_path: Path for output (default: same basename with .webp / .avif)
        quality: WebP: qscale 0–100. AVIF: mapped to libaom CRF (default: 75)
        fps: Output frame rate (lower = smaller file)
        width: Output width in pixels (height auto-scaled)
        loop: Loop count for WebP only; 0 = infinite (ignored for AVIF)
        start_time: Start time in seconds for trimming
        duration: Duration in seconds for trimming
        output_format: "webp" or "avif"
        speed: Playback speed multiplier (1.0 = original)

    Returns:
        Path to the output file
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = input_file.suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        print(
            f"Warning: Unrecognized video extension {ext!r}; "
            f"FFmpeg may still decode it.",
            file=sys.stderr,
        )

    fmt = output_format.lower()
    if fmt not in ("webp", "avif"):
        raise ValueError(f"output_format must be 'webp' or 'avif', got {output_format!r}")

    if output_path is None:
        output_path = str(input_file.with_suffix(f".{fmt}"))

    filters: list[str] = []
    if speed != 1.0:
        filters.append(f"setpts=PTS/{speed}")
    if width:
        filters.append(f"scale={width}:-1:flags=lanczos")
    filters.append(f"fps={fps}")
    filter_str = ",".join(filters)

    cmd: list[str] = ["ffmpeg", "-y"]

    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])

    cmd.extend(["-i", input_path])

    if duration is not None:
        cmd.extend(["-t", str(duration)])

    if fmt == "webp":
        cmd.extend(
            [
                "-vf",
                filter_str,
                "-vcodec",
                "libwebp",
                "-lossless",
                "0",
                "-compression_level",
                "6",
                "-q:v",
                str(quality),
                "-loop",
                str(loop),
                "-preset",
                "picture",
                "-an",
                output_path,
            ]
        )
    else:
        crf = quality_to_avif_crf(quality)
        cmd.extend(
            [
                "-vf",
                filter_str,
                "-c:v",
                "libaom-av1",
                "-still-picture",
                "0",
                "-crf",
                str(crf),
                "-b:v",
                "0",
                "-cpu-used",
                "6",
                "-row-mt",
                "1",
                "-tiles",
                "2x2",
                "-an",
                output_path,
            ]
        )

    print(f"Converting: {input_path} -> {output_path}")
    print(
        f"Settings: format={fmt}, quality={quality}, fps={fps}, "
        f"width={width or 'original'}, speed={speed}"
    )

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Conversion failed")

    input_size = input_file.stat().st_size / 1024 / 1024
    output_size = Path(output_path).stat().st_size / 1024 / 1024
    reduction = (1 - output_size / input_size) * 100 if input_size > 0 else 0.0

    print(f"Input size:  {input_size:.2f} MB")
    print(f"Output size: {output_size:.2f} MB")
    print(f"Reduction:   {reduction:.1f}%")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert video files to animated WebP or AVIF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                         # WebP (default)
  %(prog)s clip.mov --format avif            # Animated AVIF
  %(prog)s video.mov -q 60 -f 12             # Lower quality and fps
  %(prog)s video.mov -w 480                  # Scale to 480px width
  %(prog)s video.mov -o output.webp          # Explicit output path
  %(prog)s video.mov -s 5 -d 10              # 10s clip from 5s
  %(prog)s video.mov --format avif --speed 2 # AVIF at 2x speed
        """,
    )

    parser.add_argument("input", help="Input video file path")
    parser.add_argument("-o", "--output", help="Output file path (default: input basename + format extension)")
    parser.add_argument(
        "--format",
        choices=("webp", "avif"),
        default="webp",
        help="Output format (default: webp)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=75,
        help="Quality 0–100 (lower = smaller file for WebP; mapped to CRF for AVIF) (default: 75)",
    )
    parser.add_argument(
        "-f",
        "--fps",
        type=int,
        default=15,
        help="Frame rate (default: 15)",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        help="Output width in pixels (height auto-scaled)",
    )
    parser.add_argument(
        "-l",
        "--loop",
        type=int,
        default=0,
        help="Loop count for WebP only; 0 = infinite (default: 0)",
    )
    parser.add_argument(
        "-s",
        "--start",
        type=float,
        help="Start time in seconds",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        help="Duration in seconds",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed (1.0 = original, 2.0 = 2x faster) (default: 1.0)",
    )

    args = parser.parse_args()

    try:
        output = convert_video(
            input_path=args.input,
            output_path=args.output,
            quality=args.quality,
            fps=args.fps,
            width=args.width,
            loop=args.loop,
            start_time=args.start,
            duration=args.duration,
            output_format=args.format,
            speed=args.speed,
        )
        print(f"\nSuccess! Output: {output}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
