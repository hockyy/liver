"""
MOV to WebP Converter - GUI Application
"""

import subprocess
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QFileDialog,
    QProgressBar,
    QGroupBox,
    QCheckBox,
    QLineEdit,
    QMessageBox,
    QComboBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


class ConvertThread(QThread):
    """Background thread for conversion."""
    finished = pyqtSignal(str, float, float)  # output_path, input_size, output_size
    error = pyqtSignal(str)
    
    def __init__(self, input_path, output_path, quality, fps, width, loop, speed, output_format):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.quality = quality
        self.fps = fps
        self.width = width
        self.loop = loop
        self.speed = speed
        self.output_format = output_format
    
    def run(self):
        try:
            # Build filter chain
            filters = []
            if self.speed != 1.0:
                # setpts=PTS/speed: speed > 1 = faster, speed < 1 = slower
                filters.append(f"setpts=PTS/{self.speed}")
            if self.width > 0:
                filters.append(f"scale={self.width}:-1:flags=lanczos")
            filters.append(f"fps={self.fps}")
            filter_str = ",".join(filters)
            
            # Build ffmpeg command based on format
            if self.output_format == "webp":
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.input_path,
                    "-vf", filter_str,
                    "-vcodec", "libwebp",
                    "-lossless", "0",
                    "-compression_level", "6",
                    "-q:v", str(self.quality),
                    "-loop", str(self.loop),
                    "-preset", "picture",
                    "-an",
                    self.output_path
                ]
            else:  # avif
                # Convert quality (0-100) to CRF (63-0) - lower CRF = better quality
                crf = int(63 - (self.quality / 100 * 63))
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.input_path,
                    "-vf", filter_str,
                    "-c:v", "libaom-av1",
                    "-crf", str(crf),
                    "-b:v", "0",
                    "-cpu-used", "6",
                    "-row-mt", "1",
                    "-tiles", "2x2",
                    "-an",
                    self.output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.error.emit(f"FFmpeg error: {result.stderr}")
                return
            
            input_size = Path(self.input_path).stat().st_size / 1024 / 1024
            output_size = Path(self.output_path).stat().st_size / 1024 / 1024
            
            self.finished.emit(self.output_path, input_size, output_size)
            
        except Exception as e:
            self.error.emit(str(e))


class DropArea(QLabel):
    """Drag and drop area for files."""
    file_dropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("Drag & Drop MOV file here\nor click Browse")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4CAF50;
                    border-radius: 10px;
                    padding: 40px;
                    background-color: #e8f5e9;
                    color: #666;
                    font-size: 14px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.file_dropped.emit(files[0])
        self.dragLeaveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.convert_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("MOV to WebP Converter")
        self.setMinimumSize(500, 650)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Drop area
        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self.set_input_file)
        layout.addWidget(self.drop_area)
        
        # Browse button
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        layout.addWidget(browse_btn)
        
        # Settings group
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Output format
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("WebP", "webp")
        self.format_combo.addItem("AVIF", "avif")
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        settings_layout.addLayout(format_layout)
        
        # Quality slider
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality:"))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(25)
        self.quality_slider.valueChanged.connect(self.update_quality_label)
        quality_layout.addWidget(self.quality_slider)
        self.quality_label = QLabel("25")
        self.quality_label.setMinimumWidth(30)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout)
        
        # FPS spinner
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(8)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        settings_layout.addLayout(fps_layout)
        
        # Width
        width_layout = QHBoxLayout()
        self.width_check = QCheckBox("Resize width:")
        self.width_check.setChecked(True)
        width_layout.addWidget(self.width_check)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(250)
        self.width_spin.setSuffix(" px")
        self.width_check.toggled.connect(self.width_spin.setEnabled)
        width_layout.addWidget(self.width_spin)
        width_layout.addStretch()
        settings_layout.addLayout(width_layout)
        
        # Loop
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("Loop:"))
        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(0, 100)
        self.loop_spin.setValue(0)
        self.loop_spin.setSpecialValueText("Infinite")
        loop_layout.addWidget(self.loop_spin)
        loop_layout.addStretch()
        settings_layout.addLayout(loop_layout)
        
        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.25, 4.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setSuffix("x")
        self.speed_spin.setDecimals(2)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addStretch()
        settings_layout.addLayout(speed_layout)
        
        layout.addWidget(settings_group)
        
        # Output path
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout(output_group)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Auto-generated from input filename")
        output_layout.addWidget(self.output_edit)
        output_browse_btn = QPushButton("...")
        output_browse_btn.setMaximumWidth(40)
        output_browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_browse_btn)
        layout.addWidget(output_group)
        
        # Convert button
        self.convert_btn = QPushButton("Convert to WebP")
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        layout.addWidget(self.convert_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
    
    def update_quality_label(self, value):
        self.quality_label.setText(str(value))
    
    def on_format_changed(self):
        # Update output file extension when format changes
        if self.output_edit.text():
            current_path = Path(self.output_edit.text())
            new_ext = "." + self.format_combo.currentData()
            new_path = current_path.with_suffix(new_ext)
            self.output_edit.setText(str(new_path))
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MOV file",
            "",
            "Video files (*.mov *.MOV *.mp4 *.MP4);;All files (*.*)"
        )
        if file_path:
            self.set_input_file(file_path)
    
    def set_input_file(self, file_path):
        self.input_path = file_path
        filename = Path(file_path).name
        self.drop_area.setText(f"Selected:\n{filename}")
        self.convert_btn.setEnabled(True)
        
        # Auto-set output path based on selected format
        ext = "." + self.format_combo.currentData()
        output_path = str(Path(file_path).with_suffix(ext))
        self.output_edit.setText(output_path)
        
        self.status_label.setText("")
    
    def browse_output(self):
        output_format = self.format_combo.currentData()
        if output_format == "webp":
            filter_str = "WebP files (*.webp)"
        else:
            filter_str = "AVIF files (*.avif)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save output file",
            self.output_edit.text() or "",
            filter_str
        )
        if file_path:
            ext = "." + output_format
            if not file_path.endswith(ext):
                file_path += ext
            self.output_edit.setText(file_path)
    
    def start_conversion(self):
        if not self.input_path:
            return
        
        output_format = self.format_combo.currentData()
        output_path = self.output_edit.text()
        if not output_path:
            output_path = str(Path(self.input_path).with_suffix("." + output_format))
        
        width = self.width_spin.value() if self.width_check.isChecked() else 0
        
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Converting...")
        
        self.convert_thread = ConvertThread(
            self.input_path,
            output_path,
            self.quality_slider.value(),
            self.fps_spin.value(),
            width,
            self.loop_spin.value(),
            self.speed_spin.value(),
            output_format
        )
        self.convert_thread.finished.connect(self.conversion_finished)
        self.convert_thread.error.connect(self.conversion_error)
        self.convert_thread.start()
    
    def conversion_finished(self, output_path, input_size, output_size):
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        
        reduction = (1 - output_size / input_size) * 100
        self.status_label.setText(
            f"Done! {input_size:.2f} MB → {output_size:.2f} MB ({reduction:.1f}% smaller)"
        )
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        
        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Saved to:\n{output_path}\n\n"
            f"Input: {input_size:.2f} MB\n"
            f"Output: {output_size:.2f} MB\n"
            f"Reduction: {reduction:.1f}%"
        )
    
    def conversion_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.status_label.setText("Conversion failed")
        self.status_label.setStyleSheet("color: #f44336; font-size: 12px;")
        
        QMessageBox.critical(self, "Error", f"Conversion failed:\n{error_msg}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
