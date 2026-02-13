"""
ImageItem – QListWidgetItem subclass that carries metadata about one image.
"""

import os
from PIL import Image
from PyQt5.QtWidgets import QListWidgetItem


class ImageItem(QListWidgetItem):
    """List-widget item that tracks file path, dimensions, and animation info."""

    def __init__(self, file_path: str):
        super().__init__(os.path.basename(file_path))
        self.file_path = file_path
        self.original_size = self._read_size()
        self.new_size = self.original_size
        self.is_animated = self._check_animated()
        self.frame_count = self._count_frames()
        self._update_text()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _read_size(self) -> tuple:
        with Image.open(self.file_path) as img:
            return img.size

    def _check_animated(self) -> bool:
        """Return True if the image contains more than one frame."""
        try:
            with Image.open(self.file_path) as img:
                img.seek(1)
                return True
        except (EOFError, AttributeError):
            return False

    def _count_frames(self) -> int:
        if not self.is_animated:
            return 1
        try:
            with Image.open(self.file_path) as img:
                n = 0
                try:
                    while True:
                        img.seek(n)
                        n += 1
                except EOFError:
                    return n
        except Exception:
            return 1

    def _update_text(self):
        """Rebuild the display string shown in the QListWidget."""
        text = (
            f"{os.path.basename(self.file_path)} "
            f"- {self.original_size[0]}x{self.original_size[1]}"
        )
        if self.is_animated:
            text += f" ({self.frame_count} frames)"
        if self.new_size != self.original_size:
            text += f" -> {self.new_size[0]}x{self.new_size[1]}"
        self.setText(text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_new_size(self, width: int, height: int):
        self.new_size = (width, height)
        self._update_text()
