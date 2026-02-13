"""
webper – Batch Image Converter (WebP / AVIF) with optional CUDA acceleration.

This is the main entry-point and UI module.  Heavy logic lives in:
    gpu.py        – GPU detection & accelerated resize
    converter.py  – static / animated image conversion
    preview.py    – thumbnail generation & size estimation
    image_item.py – QListWidgetItem subclass with image metadata
"""

import sys
import os
from io import BytesIO

# -- project modules (import BEFORE PyQt5 to avoid DLL conflicts on Windows) -
from gpu import get_gpu_info, get_backend
from converter import (
    AVIF_SUPPORTED, VALID_EXTENSIONS, FILE_FILTER,
    is_image_file, convert_static, convert_animated, get_output_path,
)
from preview import (
    format_file_size, get_file_size_formatted,
    SizeEstimator, make_thumbnail,
)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QMessageBox, QSlider, QComboBox, QListWidget,
    QGridLayout, QMenu, QAction, QScrollArea, QSplitter, QCheckBox,
)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt5.QtCore import Qt

from image_item import ImageItem  # Depends on PyQt5, must come after


class ImageConverterApp(QWidget):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.size_estimator = SizeEstimator()
        self._init_ui()

    # ==================================================================
    # UI setup
    # ==================================================================
    def _init_ui(self):
        gpu = get_gpu_info()
        title = 'Batch Image Converter (WebP/AVIF)' if AVIF_SUPPORTED else 'Batch Image to WebP Converter'
        if gpu['available']:
            title += f"  [GPU: {gpu['name']}]"
        self.setWindowTitle(title)
        self.setGeometry(300, 300, 950, 650)
        self.setAcceptDrops(True)

        root = QVBoxLayout()

        # --- GPU status bar ------------------------------------------------
        if gpu['available']:
            gpu_label = QLabel(
                f"🟢 GPU Acceleration: {gpu['backend']} — {gpu['name']}"
                + (f" ({gpu['vram_mb']} MB VRAM)" if gpu['vram_mb'] else "")
            )
        else:
            gpu_label = QLabel("⚪ GPU Acceleration: Not available (using CPU)")
        gpu_label.setStyleSheet(
            "QLabel { background-color: #dff0d8; border: 1px solid #b2d8a2; padding: 4px; border-radius: 3px; }"
            if gpu['available'] else
            "QLabel { background-color: #f5f5f5; border: 1px solid #ddd; padding: 4px; border-radius: 3px; }"
        )
        root.addWidget(gpu_label)

        # --- Splitter: image list | preview --------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # left – file list
        left = QWidget()
        ll = QVBoxLayout()
        ll.addWidget(QLabel('Selected Images (drag & drop or use button below):'))
        self.image_list = QListWidget()
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_list.customContextMenuRequested.connect(self._ctx_menu)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        ll.addWidget(self.image_list)
        left.setLayout(ll)

        # right – preview
        right = QWidget()
        rl = QVBoxLayout()
        rl.addWidget(QLabel('Image Preview:'))
        self.info_label = QLabel("No image selected")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "QLabel { background-color: #e8e8e8; border: 1px solid #ccc; padding: 5px; }"
        )
        rl.addWidget(self.info_label)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        self.preview_label = QLabel("Select an image to preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; border: 1px solid #ccc; }"
        )
        self.preview_label.setMinimumSize(300, 200)
        self.preview_scroll.setWidget(self.preview_label)
        rl.addWidget(self.preview_scroll)
        right.setLayout(rl)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 300])
        root.addWidget(splitter)

        # --- Add / Clear buttons ----------------------------------------------
        btn_row = QHBoxLayout()
        btn_add = QPushButton('Add Images')
        btn_add.clicked.connect(self._add_images)
        btn_row.addWidget(btn_add)

        btn_clear = QPushButton('Remove All')
        btn_clear.clicked.connect(self._clear_queue)
        btn_row.addWidget(btn_clear)
        root.addLayout(btn_row)

        # --- Resize options ------------------------------------------------
        grid = QGridLayout()
        grid.addWidget(QLabel('Resize options:'), 0, 0)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(['Custom', '1920x1080', '1280x720', '800x600', '640x480'])
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        grid.addWidget(self.preset_combo, 0, 1)

        self.width_edit = QLineEdit()
        self.width_edit.setPlaceholderText('Max Width')
        self.height_edit = QLineEdit()
        self.height_edit.setPlaceholderText('Max Height')
        grid.addWidget(self.width_edit, 1, 0)
        grid.addWidget(QLabel('x'), 1, 1)
        grid.addWidget(self.height_edit, 1, 2)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(10, 100)
        self.size_slider.setValue(100)
        self.size_slider.valueChanged.connect(self._slider_resize)
        grid.addWidget(QLabel('Scale:'), 2, 0)
        grid.addWidget(self.size_slider, 2, 1, 1, 2)
        root.addLayout(grid)

        btn_resize = QPushButton('Apply Resize to All')
        btn_resize.clicked.connect(self._apply_resize)
        root.addWidget(btn_resize)

        # --- Format selection ----------------------------------------------
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel('Output Format:'))
        self.format_combo = QComboBox()
        self.format_combo.addItem('WebP')
        if AVIF_SUPPORTED:
            self.format_combo.addItem('AVIF')
        self.format_combo.currentTextChanged.connect(self._format_changed)
        fmt_row.addWidget(self.format_combo)
        root.addLayout(fmt_row)

        # --- Quality preset ------------------------------------------------
        qp_row = QHBoxLayout()
        qp_row.addWidget(QLabel('Quality Preset:'))
        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItems([
            'Custom', 'Best (Lossless)', 'High (95)', 'Medium (80)', 'Low (60)',
        ])
        self.quality_preset_combo.currentTextChanged.connect(self._quality_preset_changed)
        qp_row.addWidget(self.quality_preset_combo)
        root.addLayout(qp_row)

        # --- Options checkboxes --------------------------------------------
        opts = QVBoxLayout()

        self.chk_preview = QCheckBox(
            'Enable live preview with size estimates (disable for better performance with many images)'
        )
        self.chk_preview.setChecked(True)
        self.chk_preview.stateChanged.connect(self._preview_toggled)
        opts.addWidget(self.chk_preview)

        self.chk_trim = QCheckBox('Trim transparent edges (for images with transparency)')
        self.chk_trim.stateChanged.connect(self._option_changed)
        opts.addWidget(self.chk_trim)

        self.chk_animation = QCheckBox('Preserve animation (for animated GIFs)')
        self.chk_animation.setChecked(True)
        self.chk_animation.stateChanged.connect(self._option_changed)
        opts.addWidget(self.chk_animation)

        root.addLayout(opts)

        # --- Quality slider ------------------------------------------------
        q_row = QHBoxLayout()
        q_row.addWidget(QLabel('Quality:'))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(10)
        q_row.addWidget(self.quality_slider)
        self.quality_value = QLabel('80')
        q_row.addWidget(self.quality_value)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_value.setText(str(v)))
        self.quality_slider.valueChanged.connect(self._update_preview_if_enabled)
        root.addLayout(q_row)

        # --- Convert button ------------------------------------------------
        self.btn_convert = QPushButton('Convert All to WebP')
        self.btn_convert.clicked.connect(self._convert)
        root.addWidget(self.btn_convert)

        self.setLayout(root)

    # ==================================================================
    # Adding images
    # ==================================================================
    def _add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select Input Images', '', FILE_FILTER)
        for p in paths:
            self.image_list.addItem(ImageItem(p))

    def _clear_queue(self):
        if self.image_list.count() == 0:
            return
        self.image_list.clear()
        self.size_estimator.clear()
        self._clear_preview()

    def _add_dropped(self, file_paths):
        existing = {
            self.image_list.item(i).file_path
            for i in range(self.image_list.count())
        }
        added = 0
        for fp in file_paths:
            if fp not in existing:
                try:
                    self.image_list.addItem(ImageItem(fp))
                    added += 1
                except Exception as e:
                    QMessageBox.warning(self, 'Error', f'Failed to add {os.path.basename(fp)}: {e}')
        if added:
            QMessageBox.information(self, 'Success', f'Added {added} image(s) to the list.')

    # ==================================================================
    # Drag & drop
    # ==================================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if is_image_file(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if is_image_file(url.toLocalFile())
            ]
            if files:
                self._add_dropped(files)
                event.acceptProposedAction()
            else:
                QMessageBox.warning(self, 'Warning', 'No valid image files were dropped.')
                event.ignore()
        else:
            event.ignore()

    # ==================================================================
    # Context menu (right-click)
    # ==================================================================
    def _ctx_menu(self, pos):
        item = self.image_list.itemAt(pos)
        if item is None:
            return
        menu = QMenu()
        act = QAction("Remove from queue", self)
        act.triggered.connect(lambda: self._remove_item(item))
        menu.addAction(act)
        menu.exec_(self.image_list.mapToGlobal(pos))

    def _remove_item(self, item):
        row = self.image_list.row(item)
        if row >= 0:
            removed = self.image_list.takeItem(row)
            if removed:
                if self.image_list.currentItem() is None:
                    self._clear_preview()
                QMessageBox.information(
                    self, 'Removed',
                    f'Removed {os.path.basename(removed.file_path)} from queue.',
                )

    # ==================================================================
    # Resize helpers
    # ==================================================================
    @staticmethod
    def _calc_new_size(original, max_w, max_h):
        ow, oh = original
        ratio = ow / oh
        if ow <= max_w and oh <= max_h:
            return original
        nw = max_w
        nh = int(nw / ratio)
        if nh > max_h:
            nh = max_h
            nw = int(nh * ratio)
        return (nw, nh)

    def _preset_changed(self, index):
        if index == 0:
            return
        w, h = map(int, self.preset_combo.currentText().split('x'))
        self.width_edit.setText(str(w))
        self.height_edit.setText(str(h))
        self._apply_resize()

    def _slider_resize(self):
        scale = self.size_slider.value() / 100
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            nw = int(item.original_size[0] * scale)
            nh = int(item.original_size[1] * scale)
            item.update_new_size(nw, nh)
        self._update_preview_if_enabled()

    def _apply_resize(self):
        try:
            mw = int(self.width_edit.text())
            mh = int(self.height_edit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Please enter valid width and height values.')
            return
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            item.update_new_size(*self._calc_new_size(item.original_size, mw, mh))
        self._update_preview_if_enabled()

    # ==================================================================
    # Option / combo handlers
    # ==================================================================
    def _format_changed(self, text):
        self.btn_convert.setText(f'Convert All to {text}')
        self.size_estimator.clear()
        self._update_preview_if_enabled()

    def _quality_preset_changed(self, text):
        presets = {'Best (Lossless)': 100, 'High (95)': 95, 'Medium (80)': 80, 'Low (60)': 60}
        if text in presets:
            self.quality_slider.setValue(presets[text])
            self.quality_slider.setEnabled(text != 'Best (Lossless)')
        else:
            self.quality_slider.setEnabled(True)
        self.size_estimator.clear()
        self._update_preview_if_enabled()

    def _option_changed(self):
        self.size_estimator.clear()
        self._update_preview_if_enabled()

    def _preview_toggled(self):
        if self.chk_preview.isChecked():
            self._on_selection_changed()
        else:
            self.size_estimator.clear()
            cur = self.image_list.currentItem()
            if cur and hasattr(cur, 'file_path'):
                self.info_label.setText(
                    f"{os.path.basename(cur.file_path)}\n"
                    "Live preview disabled for performance\n"
                    "Enable checkbox above to see size estimates"
                )
                self._show_thumbnail(cur.file_path)
            else:
                self.info_label.setText(
                    "Live preview disabled\nEnable checkbox above for size estimates"
                )

    # ==================================================================
    # Preview
    # ==================================================================
    def _on_selection_changed(self):
        cur = self.image_list.currentItem()
        if not cur or not hasattr(cur, 'file_path'):
            self._clear_preview()
            return
        if self.chk_preview.isChecked():
            self._load_full_preview(cur)
        else:
            self.info_label.setText(
                f"{os.path.basename(cur.file_path)}\n"
                "Live preview disabled for performance\n"
                "Enable checkbox above to see size estimates"
            )
            self._show_thumbnail(cur.file_path)

    def _update_preview_if_enabled(self):
        if self.chk_preview.isChecked():
            self._on_selection_changed()

    def _show_thumbnail(self, file_path: str):
        """Display a thumbnail without any size calculations."""
        thumb = make_thumbnail(file_path)
        if thumb is None:
            self.preview_label.setText("Error loading image")
            return
        # PIL → QPixmap via in-memory PNG
        buf = BytesIO()
        thumb.save(buf, 'PNG')
        buf.seek(0)
        pm = QPixmap()
        pm.loadFromData(buf.getvalue())
        self.preview_label.setPixmap(pm)
        self.preview_label.setText("")

    def _load_full_preview(self, item: ImageItem):
        """Show thumbnail + size estimate info."""
        fp = item.file_path
        try:
            from PIL import Image as _Img
            with _Img.open(fp) as img:
                img_w, img_h = img.size

            original_size_str = get_file_size_formatted(fp)
            fmt = self.format_combo.currentText()
            preserve_anim = self.chk_animation.isChecked()
            is_anim = item.is_animated
            will_anim = is_anim and preserve_anim
            frames = item.frame_count if is_anim else 1

            target = item.new_size if item.new_size != (img_w, img_h) else None

            # Size estimate
            est = self.size_estimator.estimate(
                fp, fmt,
                self.quality_slider.value(),
                self.quality_preset_combo.currentText(),
                target,
                self.chk_trim.isChecked(),
                will_anim,
                frames,
            )

            # -- Build info text --
            filename = os.path.basename(fp)
            dim = f"{img_w} x {img_h} px"
            if is_anim:
                dim += f" ({frames} frames, {'will preserve animation' if will_anim else 'first frame only'})"
            if target:
                dim += f" -> {target[0]} x {target[1]} px"

            if est:
                est_str = format_file_size(est)
                orig_bytes = os.path.getsize(fp)
                ratio = (1 - est / orig_bytes) * 100
                size_line = f"{original_size_str} -> {est_str} (-{ratio:.1f}%)"
                if will_anim:
                    size_line += f"\nAnimated {fmt}"
                elif is_anim:
                    size_line += f"\nStatic {fmt} (first frame)"
                self.info_label.setText(f"{filename}\n{dim}\n{size_line}")
            else:
                calc = f"{original_size_str} -> {fmt} (calculating...)"
                if will_anim:
                    calc = f"{original_size_str} -> Animated {fmt} (calculating...)"
                elif is_anim:
                    calc = f"{original_size_str} -> Static {fmt} (calculating...)"
                self.info_label.setText(f"{filename}\n{dim}\n{calc}")

            self._show_thumbnail(fp)

        except Exception as e:
            self._clear_preview()
            self.preview_label.setText(f"Error loading image:\n{e}")
            self.info_label.setText(f"Error: {e}")

    def _clear_preview(self):
        self.preview_label.clear()
        self.preview_label.setText("Select an image to preview")
        self.info_label.setText("No image selected")

    # ==================================================================
    # Conversion
    # ==================================================================
    def _convert(self):
        count = self.image_list.count()
        if count == 0:
            QMessageBox.warning(self, 'Error', 'Please add images to convert.')
            return

        fmt = self.format_combo.currentText()
        quality = self.quality_slider.value()
        preset = self.quality_preset_combo.currentText()
        trim = self.chk_trim.isChecked()
        keep_anim = self.chk_animation.isChecked()

        if fmt == 'AVIF' and not AVIF_SUPPORTED:
            QMessageBox.warning(
                self, 'Error',
                'AVIF support is not available.\npip install pillow-avif',
            )
            return

        anim_count = sum(
            1 for i in range(count) if self.image_list.item(i).is_animated
        )
        if anim_count and keep_anim:
            reply = QMessageBox.question(
                self, 'Animated Images Detected',
                f'Found {anim_count} animated image(s).  '
                f'Converting to animated {fmt} may take longer.\n\nContinue?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return

        for i in range(count):
            item = self.image_list.item(i)
            out = get_output_path(item.file_path, fmt)
            try:
                if item.is_animated and keep_anim:
                    convert_animated(
                        item.file_path, out,
                        item.new_size, item.original_size, item.frame_count,
                        fmt, quality, preset, trim,
                    )
                else:
                    convert_static(
                        item.file_path, out,
                        item.new_size, item.original_size,
                        fmt, quality, preset, trim,
                    )
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to convert {item.text()}: {e}')

        QMessageBox.information(self, 'Success', f'All images have been converted to {fmt} format.')


# ======================================================================
# Entry point
# ======================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ImageConverterApp()
    win.show()
    sys.exit(app.exec_())
