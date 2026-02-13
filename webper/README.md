# WebPer – Batch Image Converter (WebP / AVIF)

A powerful batch image converter with optional **CUDA GPU acceleration**, supporting WebP and AVIF output formats, animated GIF conversion, transparent-edge trimming, and live size-estimation preview.

## Features

- **WebP & AVIF** output (including animated AVIF from GIF)
- **GPU acceleration** – auto-detects PyTorch CUDA or OpenCV CUDA for fast resizing
- **Drag & drop** images into the window
- **Right-click** to remove an image from the queue
- **Live preview** with estimated output file size and compression ratio (toggleable for performance)
- **Trim transparent edges** for PNG/GIF with alpha
- **Preserve animation** from animated GIFs
- **Quality presets** – Best (Lossless, speed=0), High, Medium, Low, Custom
- **Batch resize** – presets, custom max dimensions, or percentage slider

## Project Structure

```
webper/
├── webper.py        # Main entry-point & PyQt5 UI
├── gpu.py           # GPU/CUDA detection & accelerated resize
├── converter.py     # Static & animated image conversion logic
├── preview.py       # Thumbnail generation & size estimation cache
├── image_item.py    # QListWidgetItem subclass with image metadata
├── requirements.txt
├── .gitignore
└── README.md
```

| Module | Responsibility |
|--------|---------------|
| `webper.py` | Application window, layout, event wiring |
| `gpu.py` | Detect PyTorch CUDA / OpenCV CUDA, provide `resize_image()` that falls back to Pillow |
| `converter.py` | `convert_static()`, `convert_animated()`, save-kwarg builder, extension helpers |
| `preview.py` | `SizeEstimator` (cached), `make_thumbnail()`, file-size formatting |
| `image_item.py` | `ImageItem` – stores path, dimensions, frame count, animation flag |

## Installation

```bash
pip install -r requirements.txt
```

### Optional: GPU Acceleration

For CUDA-accelerated image resizing, install **one** of:

```bash
# Option A – PyTorch (recommended, best general-purpose GPU path)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Option B – OpenCV with CUDA support
pip install opencv-python  # must be built with CUDA
```

The app auto-detects available backends at startup and shows the status in the title bar and a coloured status label.

## Usage

```bash
python webper.py
```

1. **Add images** – drag & drop or click "Add Images"
2. **Configure** – pick output format, quality preset, resize, trim, animation options
3. **Preview** – select an image to see its thumbnail and estimated output size
4. **Convert** – click the convert button

## GPU Acceleration Details

The app checks for GPU support in this order:

1. **PyTorch CUDA** – uses `torch.nn.functional.interpolate` on GPU for resizing
2. **OpenCV CUDA** – uses `cv2.cuda.resize` for resizing
3. **CPU fallback** – standard Pillow `Image.resize(LANCZOS)`

GPU acceleration primarily speeds up **resizing** operations. Encoding (WebP/AVIF) is still handled by Pillow/pillow-avif on CPU.

## Performance Tips

| Scenario | Recommendation |
|----------|---------------|
| Large batch (100+ images) | Disable "Enable live preview" checkbox |
| Big images with resize | Install PyTorch CUDA for GPU-accelerated resize |
| Animated GIFs | Expect longer conversion times; lossless AVIF + speed=0 is slowest |
| Quick quality check | Keep preview enabled, select individual images |

## Quality Presets

| Preset | Quality | Speed/Method | Notes |
|--------|---------|-------------|-------|
| Best (Lossless) | lossless | AVIF speed=0, WebP method=6 | Perfect quality, largest files |
| High (95) | 95 | AVIF speed=4, WebP method=4 | Near-lossless |
| Medium (80) | 80 | AVIF speed=4, WebP method=4 | Good balance (default) |
| Low (60) | 60 | AVIF speed=4, WebP method=4 | Smaller files |
| Custom | slider | balanced | Full manual control |

## Requirements

- Python 3.8+
- PyQt5 >= 5.15
- Pillow >= 9.0
- pillow-avif >= 1.4 (for AVIF support)
- numpy >= 1.21 (for GPU path)
- Optional: PyTorch with CUDA or OpenCV with CUDA
