"""Queue and log panel."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTextEdit,
)

from gui.widgets import FileListWidget


class QueuePanel(QWidget):
    """File queue, processing log, and queue action buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        queue_group = QGroupBox("Processing Queue (Drag & Drop Files Here)")
        queue_layout = QVBoxLayout()

        self.queue_list = FileListWidget()
        self.queue_list.setMinimumHeight(120)
        queue_layout.addWidget(self.queue_list)

        queue_btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Files")
        self.remove_btn = QPushButton("Remove Selected")
        self.clear_btn = QPushButton("Clear Queue")
        queue_btn_layout.addWidget(self.add_btn)
        queue_btn_layout.addWidget(self.remove_btn)
        queue_btn_layout.addWidget(self.clear_btn)
        queue_btn_layout.addStretch()
        queue_layout.addLayout(queue_btn_layout)

        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)

        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)

        log_btn_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_btn_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def append_log(self, message):
        self.log_text.append(message.rstrip())
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def clear_log(self):
        self.log_text.clear()
