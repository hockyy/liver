"""Reusable PyQt5 widgets."""
import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QListWidget

from config import VALID_MEDIA_EXTENSIONS


class FileListWidget(QListWidget):
    """Custom list widget with drag and drop support."""

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext in VALID_MEDIA_EXTENSIONS:
                    files.append(file_path)
            elif os.path.isdir(file_path):
                for root, _dirs, filenames in os.walk(file_path):
                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in VALID_MEDIA_EXTENSIONS:
                            files.append(os.path.join(root, filename))

        if files:
            self.files_dropped.emit(files)
        event.acceptProposedAction()
