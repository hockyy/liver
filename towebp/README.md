# MOV to WebP Converter

Convert MOV video files to animated WebP with optimized file size.

## Requirements

- Python 3.10+
- FFmpeg installed on your system

### Install FFmpeg

```bash
# Windows
winget install FFmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

## Usage

```bash
# Basic conversion
python convert.py video.mov

# Lower quality and fps for smaller file size
python convert.py video.mov -q 60 -f 12

# Scale to specific width (height auto-calculated)
python convert.py video.mov -w 480

# Specify output filename
python convert.py video.mov -o output.webp

# Extract a clip (10 seconds starting at 5s mark)
python convert.py video.mov -s 5 -d 10

# Combine options for maximum compression
python convert.py video.mov -q 50 -f 10 -w 320
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output file path | Same name with .webp |
| `-q, --quality` | Quality 0-100 (lower = smaller) | 75 |
| `-f, --fps` | Frame rate (lower = smaller) | 15 |
| `-w, --width` | Output width in pixels | Original |
| `-l, --loop` | Loop count (0 = infinite) | 0 |
| `-s, --start` | Start time in seconds | Beginning |
| `-d, --duration` | Duration in seconds | Full length |

## Tips for Good File Size

1. **Lower FPS**: Most animations look fine at 10-15 fps
2. **Reduce width**: Scale down to 480px or less for web use
3. **Adjust quality**: 50-75 is usually a good balance
4. **Trim duration**: Shorter clips = smaller files
