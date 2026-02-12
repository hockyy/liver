#!/usr/bin/env python3
"""
Image to AVIF Converter for Typora
Converts images to AVIF format, scales to max 640x320, and saves in the same directory
"""

import sys
import os
from PIL import Image
from pathlib import Path
import time
from urllib.request import pathname2url


def convert_to_avif(image_path):
    """
    Convert image to AVIF format with max dimensions of 640x320

    Args:
        image_path: Path to the input image

    Returns:
        Path to the converted AVIF image in file:// format
    """
    try:
        img = Image.open(image_path)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        # Calculate new dimensions maintaining aspect ratio
        max_width = 640
        max_height = 320

        width, height = img.size
        aspect_ratio = width / height

        if width > max_width or height > max_height:
            if aspect_ratio > max_width / max_height:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * aspect_ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Get the original file path and directory
        original_path = Path(image_path)
        output_dir = original_path.parent

        # Use the same filename but with .avif extension
        original_stem = original_path.stem
        output_path = output_dir / f"{original_stem}.avif"

        # If file already exists, append timestamp to avoid overwriting
        if output_path.exists():
            epoch_ms = int(time.time() * 1000)
            output_path = output_dir / f"{original_stem}_{epoch_ms}.avif"

        # Save as AVIF
        # quality: 0-100 (higher = better quality, larger file)
        # speed: 0-10 (lower = slower but better compression; 6 is a good balance)
        print("here")
        img.save(output_path, 'AVIF', quality=65, speed=6)

        # Convert to file:// URL format for Typora
        absolute_path = output_path.absolute()
        file_url = pathname2url(str(absolute_path))
        if not file_url.startswith('/'):
            file_url = '/' + file_url
        file_url = 'file://' + file_url

        print(file_url)

    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python typora_avif_converter.py <image_path>\n")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        sys.stderr.write(f"Error: Image file not found: {image_path}\n")
        sys.exit(1)

    convert_to_avif(image_path)