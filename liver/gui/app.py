"""Main application window."""
import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QSplitter, QFileDialog,
)

from config import SETTINGS_FILE
from transcriber import SubtitleTranscriber
from gui.settings_tabs import SettingsTabs
from gui.settings_store import SettingsStore
from gui.panels.queue_panel import QueuePanel
from gui.workers import TranscriptionWorker
from gui.styles import apply_modern_style


class ModernTranscriptionApp(QMainWindow):
    """Modern PyQt5 main window for Subtitle Transcriber PRO."""

    def __init__(self):
        super().__init__()
        self.transcriber = SubtitleTranscriber()
        self.settings_store = SettingsStore()
        self.queue = []
        self.is_processing = False
        self.current_worker = None

        self._build_ui()
        apply_modern_style(self)
        self._load_settings()
        self.settings_tabs.initialize_after_load()

    def _build_ui(self):
        self.setWindowTitle("Subtitle Transcriber PRO - PyQt5")
        self.setGeometry(100, 100, 1150, 920)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        splitter = QSplitter(Qt.Vertical)
        self.settings_tabs = SettingsTabs()
        splitter.addWidget(self.settings_tabs)

        self.queue_panel = QueuePanel()
        splitter.addWidget(self.queue_panel)
        splitter.setSizes([450, 400])
        main_layout.addWidget(splitter)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        main_layout.addLayout(controls)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        main_layout.addWidget(self.progress_bar)

        self.queue_panel.queue_list.files_dropped.connect(self.on_files_dropped)
        self.queue_panel.add_btn.clicked.connect(self.browse_and_add_files)
        self.queue_panel.remove_btn.clicked.connect(self.remove_selected_files)
        self.queue_panel.clear_btn.clicked.connect(self.clear_queue)
        self.queue_panel.clear_log_btn.clicked.connect(self.queue_panel.clear_log)

    def log(self, message):
        self.queue_panel.append_log(message)

    def _load_settings(self):
        settings = self.settings_store.load()
        if not settings:
            return
        try:
            self.settings_store.apply(settings, self.settings_tabs)
            last_saved = settings.get('last_saved', 'unknown')
            self.log(f"Loaded settings from {SETTINGS_FILE} (last saved: {last_saved})\n")
        except Exception as exc:
            self.log(f"Error loading settings: {exc}\n")

    def save_settings(self):
        try:
            settings = self.settings_store.collect(self.settings_tabs)
            self.settings_store.save(settings)
            self.log(f"Settings saved to {SETTINGS_FILE}\n")
        except Exception as exc:
            self.log(f"Error saving settings: {exc}\n")

    def on_files_dropped(self, files):
        added = 0
        for file_path in files:
            if file_path not in self.queue:
                self.queue.append(file_path)
                self.queue_panel.queue_list.addItem(file_path)
                added += 1
        if added:
            self.log(f"Added {added} file(s) via drag and drop\n")

    def browse_and_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio/Video Files",
            os.path.expanduser("~"),
            "Media Files (*.mkv *.mp4 *.wav *.mp3 *.aac *.opus *.ts *.avi *.mov *.flac *.m4a *.webm);;All Files (*.*)",
        )
        added = 0
        for file_path in files:
            if file_path not in self.queue:
                self.queue.append(file_path)
                self.queue_panel.queue_list.addItem(file_path)
                added += 1
        if added:
            self.log(f"Added {added} file(s) to queue\n")

    def remove_selected_files(self):
        selected = self.queue_panel.queue_list.selectedItems()
        if not selected:
            self.log("No files selected to remove\n")
            return
        for item in selected:
            file_path = item.text()
            if file_path in self.queue:
                self.queue.remove(file_path)
            self.queue_panel.queue_list.takeItem(self.queue_panel.queue_list.row(item))
        self.log(f"Removed {len(selected)} file(s) from queue\n")

    def clear_queue(self):
        if self.queue:
            count = len(self.queue)
            self.queue.clear()
            self.queue_panel.queue_list.clear()
            self.log(f"Cleared {count} file(s) from queue\n")

    def start_processing(self):
        if self.is_processing:
            self.log("Processing is already in progress\n")
            return
        if not self.queue:
            self.log("No files in queue. Please add files first\n")
            return

        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.process_next_file()

    def process_next_file(self):
        if not self.queue or not self.is_processing:
            self.finish_processing()
            return

        file_path = self.queue[0]
        self.log(f"Processing: {file_path}\n")
        self.progress_bar.setFormat(f"Processing: {os.path.basename(file_path)}")

        self.transcriber.model = self.settings_tabs.basic.model_combo.currentText()
        options = self.settings_tabs.build_transcription_options()

        self.current_worker = TranscriptionWorker(self.transcriber, file_path, options)
        self.current_worker.log_signal.connect(self.log, Qt.QueuedConnection)
        self.current_worker.finished_signal.connect(self.on_file_finished, Qt.QueuedConnection)
        self.current_worker.start()

    def on_file_finished(self):
        if self.queue:
            finished_file = self.queue.pop(0)
            self.queue_panel.queue_list.takeItem(0)
            self.log(f"Finished: {finished_file}\n\n")
        QTimer.singleShot(100, self.process_next_file)

    def finish_processing(self):
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        self.log("All files processed!\n")

    def stop_processing(self):
        self.is_processing = False
        self.transcriber.stop_transcription()
        if self.current_worker:
            self.current_worker.terminate()
            self.current_worker.wait()
        self.finish_processing()
        self.log("Processing stopped by user\n")

    def closeEvent(self, event):
        self.save_settings()
        event.accept()


def run_app():
    """Run the PyQt5 application."""
    app = QApplication(sys.argv)
    window = ModernTranscriptionApp()
    window.show()
    sys.exit(app.exec_())
