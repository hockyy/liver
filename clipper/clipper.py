import os
import sys
import time
import subprocess
import tempfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTextEdit, QGroupBox,
    QMessageBox, QSpinBox, QCheckBox, QProgressBar, QComboBox
)
from PyQt5.QtCore import Qt, QRect, QProcess
from PyQt5.QtGui import QPixmap, QColor

from widgets import VideoPreviewWidget, VerticalPreviewWidget
from utils import parse_timestamp_line, TIMESTAMP_PATTERN


class ClipperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stream Clip Editor - 9:16 Vertical Mode")
        self.setGeometry(100, 100, 1400, 900)
        
        self.selected_file = None
        self.video_width = 1920
        self.video_height = 1080
        self.video_duration = 0
        self.temp_frame_path = None
        
        # Clipping queue state
        self.clip_queue = []  # List of (cmd, output_file, clip_info) tuples
        self.current_clip_index = 0
        self.total_clips = 0
        self.output_dir = None
        self.ffmpeg_process = None
        self.is_clipping = False
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        # File selection
        file_group = QGroupBox("Video File")
        file_layout = QVBoxLayout(file_group)
        self.file_label = QLabel("No video selected")
        self.file_label.setWordWrap(True)
        self.browse_btn = QPushButton("Browse Video")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_btn)
        left_layout.addWidget(file_group)
        
        # Video info
        info_group = QGroupBox("Video Info")
        info_layout = QVBoxLayout(info_group)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        info_layout.addWidget(self.info_text)
        left_layout.addWidget(info_group)
        
        # Frame selection for preview
        frame_group = QGroupBox("Preview Frame")
        frame_layout = QHBoxLayout(frame_group)
        frame_layout.addWidget(QLabel("Time (sec):"))
        self.frame_time_spin = QSpinBox()
        self.frame_time_spin.setRange(0, 99999)
        self.frame_time_spin.setValue(30)
        frame_layout.addWidget(self.frame_time_spin)
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.clicked.connect(self.capture_frame)
        frame_layout.addWidget(self.capture_btn)
        left_layout.addWidget(frame_group)
        
        # Timestamp input
        timestamp_group = QGroupBox("Clip Timestamps")
        timestamp_layout = QVBoxLayout(timestamp_group)
        timestamp_layout.addWidget(QLabel("Format: HH:MM:SS[,mmm] --> HH:MM:SS[,mmm]"))
        self.timestamp_text = QTextEdit()
        self.timestamp_text.setPlaceholderText("00:01:30,000 --> 00:02:00,000\n00:05:00 --> 00:05:30")
        self.timestamp_text.textChanged.connect(self.update_clip_count)
        timestamp_layout.addWidget(self.timestamp_text)
        self.clip_count_label = QLabel("Clips: 0")
        timestamp_layout.addWidget(self.clip_count_label)
        left_layout.addWidget(timestamp_group)
        
        # 9:16 mode checkbox
        self.vertical_mode_check = QCheckBox("Enable 9:16 Vertical Mode")
        self.vertical_mode_check.setChecked(True)
        self.vertical_mode_check.stateChanged.connect(self.toggle_vertical_mode)
        left_layout.addWidget(self.vertical_mode_check)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        left_layout.addWidget(self.progress_bar)
        
        # Start/Cancel buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Clipping")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_clipping)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(self.cancel_clipping)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setStyleSheet("background-color: #8B0000;")
        btn_layout.addWidget(self.cancel_btn)
        
        left_layout.addLayout(btn_layout)
        
        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group)
        
        main_layout.addWidget(left_panel)
        
        # Center panel - video preview with crop boxes
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        self.preview_label = QLabel("Source Video - Drag to move, drag corners/edges to resize")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #aaa; font-size: 11px;")
        center_layout.addWidget(self.preview_label)
        
        self.video_preview = VideoPreviewWidget()
        self.video_preview.on_boxes_changed = self.update_vertical_preview
        center_layout.addWidget(self.video_preview)
        
        main_layout.addWidget(center_panel, stretch=1)
        
        # Right panel - 9:16 preview with integrated slider
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        self.right_panel.setMaximumWidth(280)
        
        preview_label = QLabel("9:16 Output Preview")
        preview_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(preview_label)
        
        slider_hint = QLabel("Drag the split line to adjust ratio")
        slider_hint.setAlignment(Qt.AlignCenter)
        slider_hint.setStyleSheet("color: #888; font-size: 10px;")
        right_layout.addWidget(slider_hint)
        
        self.vertical_preview = VerticalPreviewWidget()
        self.vertical_preview.ratio_changed.connect(self.on_ratio_changed)
        right_layout.addWidget(self.vertical_preview, stretch=1)
        
        self.ratio_label = QLabel("Top: 50% | Bottom: 50%")
        self.ratio_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.ratio_label)
        
        # Output resolution
        res_group = QGroupBox("Output Settings")
        res_layout = QVBoxLayout(res_group)
        
        # Aspect ratio picker
        aspect_layout = QHBoxLayout()
        aspect_layout.addWidget(QLabel("Aspect:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItem("9:16 (TikTok/Reels)", (9, 16))
        self.aspect_combo.addItem("3:4 (Instagram)", (3, 4))
        self.aspect_combo.addItem("4:3 (Classic)", (4, 3))
        self.aspect_combo.addItem("1:1 (Square)", (1, 1))
        self.aspect_combo.currentIndexChanged.connect(self.on_aspect_changed)
        aspect_layout.addWidget(self.aspect_combo, stretch=1)
        res_layout.addLayout(aspect_layout)
        
        res_h_layout = QHBoxLayout()
        res_h_layout.addWidget(QLabel("W:"))
        self.output_width_spin = QSpinBox()
        self.output_width_spin.setRange(360, 2160)
        self.output_width_spin.setValue(1080)
        self.output_width_spin.setSingleStep(10)
        res_h_layout.addWidget(self.output_width_spin)
        res_h_layout.addWidget(QLabel("H:"))
        self.output_height_spin = QSpinBox()
        self.output_height_spin.setRange(640, 3840)
        self.output_height_spin.setValue(1920)
        self.output_height_spin.setSingleStep(10)
        res_h_layout.addWidget(self.output_height_spin)
        res_layout.addLayout(res_h_layout)
        
        # GPU encoding checkbox
        self.gpu_encode_check = QCheckBox("Use NVIDIA GPU (NVENC)")
        self.gpu_encode_check.setChecked(True)
        self.gpu_encode_check.setToolTip("Use NVIDIA CUDA for faster encoding.\nDisable if you don't have an NVIDIA GPU.")
        res_layout.addWidget(self.gpu_encode_check)
        
        right_layout.addWidget(res_group)
        
        main_layout.addWidget(self.right_panel)
    
    def set_ui_enabled(self, enabled):
        """Enable or disable UI elements during clipping"""
        self.browse_btn.setEnabled(enabled)
        self.capture_btn.setEnabled(enabled)
        self.timestamp_text.setEnabled(enabled)
        self.vertical_mode_check.setEnabled(enabled)
        self.aspect_combo.setEnabled(enabled)
        self.output_width_spin.setEnabled(enabled)
        self.output_height_spin.setEnabled(enabled)
        self.start_btn.setVisible(enabled)
        self.cancel_btn.setVisible(not enabled)
        self.progress_bar.setVisible(not enabled)
    
    def browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video files (*.mp4 *.mkv *.ts *.avi *.mov);;All files (*.*)"
        )
        if filename:
            self.selected_file = filename
            self.file_label.setText(os.path.basename(filename))
            self.get_video_info(filename)
            self.capture_frame()
    
    def get_video_info(self, filename):
        """Get video information using ffprobe"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                filename
            ], capture_output=True, text=True)
            
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(',')
                if len(parts) >= 2:
                    self.video_width = int(parts[0])
                    self.video_height = int(parts[1])
                
                if len(lines) > 1 and lines[1]:
                    self.video_duration = float(lines[1])
                elif len(parts) >= 3 and parts[2]:
                    self.video_duration = float(parts[2])
                
                self.frame_time_spin.setMaximum(int(self.video_duration) if self.video_duration > 0 else 99999)
                
                mid_time = int(self.video_duration / 2) if self.video_duration > 0 else 30
                self.frame_time_spin.setValue(min(mid_time, int(self.video_duration)))
            
            result2 = subprocess.run(
                ["ffmpeg", "-hide_banner", "-i", filename],
                capture_output=True, text=True
            )
            self.info_text.setText(result2.stderr)
            
        except Exception as e:
            self.log_text.append(f"Error getting video info: {e}")
    
    def capture_frame(self):
        """Capture a frame from the video for preview"""
        if not self.selected_file:
            return
        
        time_sec = self.frame_time_spin.value()
        
        if self.temp_frame_path and os.path.exists(self.temp_frame_path):
            os.remove(self.temp_frame_path)
        
        self.temp_frame_path = os.path.join(tempfile.gettempdir(), "clipper_preview.jpg")
        
        try:
            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", str(time_sec),
                "-i", self.selected_file,
                "-vframes", "1",
                "-q:v", "2",
                self.temp_frame_path
            ], capture_output=True)
            
            if os.path.exists(self.temp_frame_path):
                self.video_preview.split_ratio = self.vertical_preview.ratio
                self.video_preview.set_image(self.temp_frame_path, 
                                             self.video_width, self.video_height)
                self.vertical_preview.set_source(QPixmap(self.temp_frame_path))
                self.update_vertical_preview()
                self.log_text.append(f"Captured frame at {time_sec}s")
        except Exception as e:
            self.log_text.append(f"Error capturing frame: {e}")
    
    def update_vertical_preview(self):
        """Update the 9:16 preview based on current crop boxes"""
        top_params, bottom_params = self.video_preview.get_crop_params()
        
        top_rect = QRect(top_params['x'], top_params['y'], 
                        top_params['w'], top_params['h'])
        bottom_rect = QRect(bottom_params['x'], bottom_params['y'],
                           bottom_params['w'], bottom_params['h'])
        
        self.vertical_preview.set_crops(top_rect, bottom_rect)
    
    def on_ratio_changed(self, ratio):
        """Handle ratio change from the vertical preview slider"""
        top_pct = int(ratio * 100)
        self.ratio_label.setText(f"Top: {top_pct}% | Bottom: {100-top_pct}%")
        self.video_preview.set_split_ratio(ratio)
    
    def on_aspect_changed(self, index):
        """Handle aspect ratio selection change"""
        aspect_data = self.aspect_combo.currentData()
        if aspect_data:
            w, h = aspect_data
            # Update preview widgets
            self.vertical_preview.set_aspect_ratio(w, h)
            self.video_preview.set_output_aspect(w, h)
            
            # Update output resolution to match aspect ratio
            # Keep width, adjust height
            current_width = self.output_width_spin.value()
            new_height = int(current_width * h / w)
            # Ensure even number for ffmpeg
            new_height = new_height if new_height % 2 == 0 else new_height + 1
            self.output_height_spin.setValue(new_height)
            
            # Update preview label
            aspect_text = self.aspect_combo.currentText().split(" ")[0]  # Get "9:16" part
            for label in self.right_panel.findChildren(QLabel):
                if "Output Preview" in label.text():
                    label.setText(f"{aspect_text} Output Preview")
                    break
            
            # Refresh the preview
            self.update_vertical_preview()
    
    def toggle_vertical_mode(self, state):
        """Toggle 9:16 mode UI visibility"""
        is_vertical = state == Qt.Checked
        self.right_panel.setVisible(is_vertical)
        self.video_preview.set_boxes_visible(is_vertical)
        
        if is_vertical:
            self.preview_label.setText("Source Video - Drag to move, drag corners/edges to resize")
        else:
            self.preview_label.setText("Source Video Preview")
    
    def update_clip_count(self):
        """Update clip count label"""
        content = self.timestamp_text.toPlainText()
        lines = content.strip().splitlines()
        valid_lines = [
            line for line in lines
            if line.strip() and TIMESTAMP_PATTERN.match(line.strip())
        ]
        self.clip_count_label.setText(f"Clips: {len(valid_lines)}")
    
    def build_clip_queue(self):
        """Build the queue of clips to process"""
        content = self.timestamp_text.toPlainText().strip()
        lines = content.splitlines()
        timestamps = []
        
        for line in lines:
            result = parse_timestamp_line(line)
            if result is None and line.strip():
                QMessageBox.critical(self, "Error", f"Invalid timestamp format:\n{line}")
                return False
            if result:
                timestamps.append(result)
        
        if not timestamps:
            QMessageBox.critical(self, "Error", "No valid timestamps found!")
            return False
        
        # Create output directory
        input_dir = os.path.dirname(self.selected_file)
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        current_epoch = int(time.time())
        self.output_dir = os.path.join(input_dir, f"{base_name}-{current_epoch}")
        
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create output directory:\n{e}")
            return False
        
        vertical_mode = self.vertical_mode_check.isChecked()
        self.clip_queue = []
        
        for i, (start_str, end_str, duration) in enumerate(timestamps, 1):
            start_ffmpeg = start_str.replace(",", ".")
            duration_str = f"{duration:.3f}"
            
            if vertical_mode:
                aspect_data = self.aspect_combo.currentData()
                suffix = f"_{aspect_data[0]}x{aspect_data[1]}" if aspect_data else "_9x16"
            else:
                suffix = ""
            output_file = os.path.join(self.output_dir, f"clip-{i:03}{suffix}.mp4")
            clip_info = f"{start_str} --> {end_str}"
            
            if vertical_mode:
                top_params, bottom_params = self.video_preview.get_crop_params()
                ratio = self.vertical_preview.ratio
                
                out_width = self.output_width_spin.value()
                out_height = self.output_height_spin.value()
                
                out_width = out_width if out_width % 2 == 0 else out_width - 1
                out_height = out_height if out_height % 2 == 0 else out_height - 1
                
                top_out_height = int(out_height * ratio)
                top_out_height = top_out_height if top_out_height % 2 == 0 else top_out_height - 1
                bottom_out_height = out_height - top_out_height
                
                filter_complex = (
                    f"[0:v]crop={top_params['w']}:{top_params['h']}:{top_params['x']}:{top_params['y']},"
                    f"scale={out_width}:{top_out_height}[top];"
                    f"[0:v]crop={bottom_params['w']}:{bottom_params['h']}:{bottom_params['x']}:{bottom_params['y']},"
                    f"scale={out_width}:{bottom_out_height}[bottom];"
                    f"[top][bottom]vstack=inputs=2[out]"
                )
                
                # Build encoding options based on GPU/CPU choice
                use_gpu = self.gpu_encode_check.isChecked()
                
                if use_gpu:
                    cmd = [
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-hwaccel", "cuda",  # Use CUDA for decoding
                        "-ss", start_ffmpeg,
                        "-i", self.selected_file,
                        "-t", duration_str,
                        "-filter_complex", filter_complex,
                        "-map", "[out]",
                        "-map", "0:a?",
                        "-c:v", "h264_nvenc",  # NVIDIA GPU encoding
                        "-preset", "p4",  # p1(fastest) to p7(slowest/best quality)
                        "-cq", "23",  # Constant quality (like CRF)
                        "-c:a", "aac",
                        output_file
                    ]
                else:
                    cmd = [
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", start_ffmpeg,
                        "-i", self.selected_file,
                        "-t", duration_str,
                        "-filter_complex", filter_complex,
                        "-map", "[out]",
                        "-map", "0:a?",
                        "-c:v", "libx264",  # CPU encoding
                        "-preset", "fast",
                        "-crf", "23",
                        "-c:a", "aac",
                        output_file
                    ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", start_ffmpeg,
                    "-i", self.selected_file,
                    "-t", duration_str,
                    "-c", "copy",
                    output_file
                ]
            
            self.clip_queue.append((cmd, output_file, clip_info))
        
        self.total_clips = len(self.clip_queue)
        return True
    
    def start_clipping(self):
        """Start the clipping process"""
        if not self.selected_file:
            QMessageBox.critical(self, "Error", "No video file selected!")
            return
        
        content = self.timestamp_text.toPlainText().strip()
        if not content:
            QMessageBox.critical(self, "Error", "No timestamp data provided!")
            return
        
        if not self.build_clip_queue():
            return
        
        self.log_text.clear()
        self.log_text.append(f"Output directory: {self.output_dir}")
        self.log_text.append(f"Processing {self.total_clips} clips...\n")
        
        self.current_clip_index = 0
        self.is_clipping = True
        self.set_ui_enabled(False)
        
        self.progress_bar.setRange(0, self.total_clips)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Clip %v / {self.total_clips}")
        
        # Start processing first clip
        self.process_next_clip()
    
    def process_next_clip(self):
        """Process the next clip in the queue"""
        if self.current_clip_index >= len(self.clip_queue):
            # All done
            self.clipping_finished()
            return
        
        cmd, output_file, clip_info = self.clip_queue[self.current_clip_index]
        clip_num = self.current_clip_index + 1
        
        self.log_text.append(f"[{clip_num}/{self.total_clips}] Processing: {clip_info}")
        
        # Create QProcess for non-blocking execution
        self.ffmpeg_process = QProcess(self)
        self.ffmpeg_process.setProcessChannelMode(QProcess.MergedChannels)
        self.ffmpeg_process.finished.connect(self.on_clip_finished)
        self.ffmpeg_process.errorOccurred.connect(self.on_clip_error)
        
        # Store output file for reference in callback
        self.ffmpeg_process.setProperty("output_file", output_file)
        self.ffmpeg_process.setProperty("clip_info", clip_info)
        
        # Start the process
        program = cmd[0]
        arguments = cmd[1:]
        self.ffmpeg_process.start(program, arguments)
    
    def on_clip_finished(self, exit_code, exit_status):
        """Called when a clip finishes processing"""
        output_file = self.ffmpeg_process.property("output_file")
        
        if exit_code == 0:
            self.log_text.append(f"  -> Created: {os.path.basename(output_file)}")
        else:
            stderr = self.ffmpeg_process.readAllStandardOutput().data().decode()
            self.log_text.append(f"  -> Error (code {exit_code}): {stderr[:200] if stderr else 'Unknown error'}")
        
        self.current_clip_index += 1
        self.progress_bar.setValue(self.current_clip_index)
        
        # Process next clip
        if self.is_clipping:
            self.process_next_clip()
    
    def on_clip_error(self, error):
        """Called when there's an error starting the process"""
        error_msg = {
            QProcess.FailedToStart: "FFmpeg failed to start. Is it installed?",
            QProcess.Crashed: "FFmpeg crashed",
            QProcess.Timedout: "Process timed out",
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
            QProcess.UnknownError: "Unknown error"
        }.get(error, f"Error code: {error}")
        
        self.log_text.append(f"  -> Process error: {error_msg}")
        
        self.current_clip_index += 1
        self.progress_bar.setValue(self.current_clip_index)
        
        if self.is_clipping:
            self.process_next_clip()
    
    def clipping_finished(self):
        """Called when all clips are done"""
        self.is_clipping = False
        self.set_ui_enabled(True)
        self.ffmpeg_process = None
        
        self.log_text.append(f"\nClipping completed! {self.current_clip_index} clips processed.")
        self.log_text.append(f"Saved to: {self.output_dir}")
        
        QMessageBox.information(self, "Done", 
            f"Clipping completed!\n{self.current_clip_index} clips saved to:\n{self.output_dir}")
    
    def cancel_clipping(self):
        """Cancel the clipping process"""
        if self.ffmpeg_process and self.ffmpeg_process.state() != QProcess.NotRunning:
            self.ffmpeg_process.kill()
            self.ffmpeg_process.waitForFinished(1000)
        
        self.is_clipping = False
        self.set_ui_enabled(True)
        
        self.log_text.append(f"\nClipping cancelled. {self.current_clip_index} clips were completed.")
        QMessageBox.warning(self, "Cancelled", 
            f"Clipping cancelled.\n{self.current_clip_index} of {self.total_clips} clips were completed.")
    
    def closeEvent(self, event):
        """Cleanup on close"""
        # Cancel any running process
        if self.ffmpeg_process and self.ffmpeg_process.state() != QProcess.NotRunning:
            self.ffmpeg_process.kill()
            self.ffmpeg_process.waitForFinished(1000)
        
        if self.temp_frame_path and os.path.exists(self.temp_frame_path):
            try:
                os.remove(self.temp_frame_path)
            except:
                pass
        event.accept()


def apply_dark_theme(app):
    """Apply dark theme to the application"""
    app.setStyle('Fusion')
    palette = app.palette()
    palette.setColor(palette.Window, QColor(53, 53, 53))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(25, 25, 25))
    palette.setColor(palette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ToolTipBase, Qt.white)
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(53, 53, 53))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, Qt.red)
    palette.setColor(palette.Link, QColor(42, 130, 218))
    palette.setColor(palette.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    window = ClipperApp()
    window.show()
    sys.exit(app.exec_())
