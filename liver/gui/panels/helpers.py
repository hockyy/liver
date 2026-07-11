"""Shared UI helpers for settings panels."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QFrame, QVBoxLayout, QToolButton, QWidget


def make_help_label(text):
    """Small wrapped description label for a setting."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 6px;")
    return label


class CollapsibleSection(QFrame):
    """Click-to-expand/collapse wrapper for a settings panel or group."""

    def __init__(self, title, expanded=True, parent=None):
        super().__init__(parent)
        self.setObjectName("CollapsibleSection")
        self.setFrameShape(QFrame.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 8)
        outer.setSpacing(0)

        self.toggle = QToolButton()
        self.toggle.setObjectName("CollapsibleToggle")
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setAutoRaise(False)
        self.toggle.clicked.connect(self._sync_visibility)
        outer.addWidget(self.toggle)

        self.content = QWidget()
        self.content.setObjectName("CollapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 0, 0)
        self.content_layout.setSpacing(0)
        outer.addWidget(self.content)

        self._sync_visibility()

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def set_expanded(self, expanded):
        self.toggle.setChecked(expanded)
        self._sync_visibility()

    def _sync_visibility(self):
        expanded = self.toggle.isChecked()
        self.content.setVisible(expanded)
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
