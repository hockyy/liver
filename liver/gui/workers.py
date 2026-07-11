"""Background workers for the GUI."""
from PyQt5.QtCore import QThread, pyqtSignal


class TranscriptionWorker(QThread):
    """Worker thread for transcription to avoid blocking the UI."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, transcriber, file_path, options):
        super().__init__()
        self.transcriber = transcriber
        self.file_path = file_path
        self.options = options

    def run(self):
        """Run transcription in background thread."""
        self.transcriber.transcribe_and_write_srt_live(
            self.file_path,
            self.log_callback,
            self.options,
        )
        self.finished_signal.emit()

    def log_callback(self, message):
        """Thread-safe logging callback."""
        self.log_signal.emit(message)
