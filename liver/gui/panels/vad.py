"""VAD settings panel."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox

from config import VAD_METHODS, DEFAULTS
from gui.panels.helpers import make_help_label


class VadPanel(QWidget):
    """Voice activity detection method selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        vad_group = QGroupBox("Voice Activity Detection (VAD)")
        vad_layout = QVBoxLayout()
        vad_layout.addWidget(make_help_label(
            "Detects speech vs silence before transcribing. Skips quiet parts so Whisper "
            "doesn't hallucinate text in background noise. Use 'none' to disable."
        ))

        vad_row = QHBoxLayout()
        vad_label = QLabel("VAD Method:")
        vad_label.setMinimumWidth(150)
        self.vad_combo = QComboBox()
        self.vad_combo.addItems(VAD_METHODS)
        self.vad_combo.setCurrentText(DEFAULTS['vad_method'])
        vad_row.addWidget(vad_label)
        vad_row.addWidget(self.vad_combo)
        vad_row.addStretch()
        vad_layout.addLayout(vad_row)

        vad_group.setLayout(vad_layout)
        layout.addWidget(vad_group)

    def get_settings(self):
        return {'vad_method': self.vad_combo.currentText()}

    def get_transcription_options(self):
        return self.get_settings()

    def apply_settings(self, settings):
        if settings.get('vad_method') in VAD_METHODS:
            self.vad_combo.setCurrentText(settings['vad_method'])
