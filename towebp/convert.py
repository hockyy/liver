"""
MOV to WebP Converter
Converts MOV video files to animated WebP with optimized file size.
"""

import subprocess
import argparse
import sys
from pathlib import Path


def get_video_duration(input_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def convert_mov_to_webp(
    input_path: str,
    output_path: str | None = None,
    quality: int = 75,
    fps: int = 15,
    width: int | None = None,
    loop: int = 0,
    start_time: float | None = None,
    duration: float | None = None,
) -> str:
    """
    Convert MOV file to animated WebP.

    Args:
        input_path: Path to input MOV file
        output_path: Path for output WebP file (default: same name with .webp)
        quality: WebP quality 0-100 (lower = smaller file, default: 75)
        fps: Output frame rate (lower = smaller file, default: 15)
        width: Output width in pixels (height auto-scaled, default: original)
        loop: Number of loops, 0 = infinite (default: 0)
        start_time: Start time in seconds for trimming
        duration: Duration in seconds for trimming

    Returns:
        Path to the output file
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not input_file.suffix.lower() == ".mov":
        print(f"Warning: Input file is not a .mov file: {input_path}")
    
    # Set output path
    if output_path is None:
        output_path = str(input_file.with_suffix(".webp"))
    
    # Build filter chain
    filters = []
    
    # Scale filter (if width specified)
    if width:
        filters.append(f"scale={width}:-1:flags=lanczos")
    
    # FPS filter
    filters.append(f"fps={fps}")
    
    # Combine filters
    filter_str = ",".join(filters)
    
    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"]
    
    # Input options
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    
    cmd.extend(["-i", input_path])
    
    if duration is not None:
        cmd.extend(["-t", str(duration)])
    
    # Output options
    cmd.extend([
        "-vf", filter_str,
        "-vcodec", "libwebp",
        "-lossless", "0",
        "-compression_level", "6",
        "-q:v", str(quality),
        "-loop", str(loop),
        "-preset", "picture",
        "-an",  # No audio
        output_path
    ])
    
    print(f"Converting: {input_path} -> {output_path}")
    print(f"Settings: quality={quality}, fps={fps}, width={width or 'original'}")
    
    # Run conversion
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Conversion failed")
    
    # Report file sizes
    input_size = input_file.stat().st_size / 1024 / 1024
    output_size = Path(output_path).stat().st_size / 1024 / 1024
    reduction = (1 - output_size / input_size) * 100
    
    print(f"Input size:  {input_size:.2f} MB")
    print(f"Output size: {output_size:.2f} MB")
    print(f"Reduction:   {reduction:.1f}%")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert MOV files to animated WebP with optimized file size",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mov                      # Basic conversion
  %(prog)s video.mov -q 60 -f 12          # Lower quality and fps for smaller size
  %(prog)s video.mov -w 480               # Scale to 480px width
  %(prog)s video.mov -o output.webp       # Specify output filename
  %(prog)s video.mov -s 5 -d 10           # Extract 10 seconds starting at 5s
        """
    )
    
    parser.add_argument("input", help="Input MOV file path")
    parser.add_argument("-o", "--output", help="Output WebP file path")
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=75,
        help="Quality 0-100, lower = smaller file (default: 75)"
    )
    parser.add_argument(
        "-f", "--fps",
        type=int,
        default=15,
        help="Frame rate, lower = smaller file (default: 15)"
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        help="Output width in pixels (height auto-scaled)"
    )
    parser.add_argument(
        "-l", "--loop",
        type=int,
        default=0,
        help="Loop count, 0 = infinite (default: 0)"
    )
    parser.add_argument(
        "-s", "--start",
        type=float,
        help="Start time in seconds"
    )
    parser.add_argument(
        "-d", "--duration",
        type=float,
        help="Duration in seconds"
    )
    
    args = parser.parse_args()
    
    try:
        output = convert_mov_to_webp(
            input_path=args.input,
            output_path=args.output,
            quality=args.quality,
            fps=args.fps,
            width=args.width,
            loop=args.loop,
            start_time=args.start,
            duration=args.duration,
        )
        print(f"\nSuccess! Output: {output}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
