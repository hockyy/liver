"""Voice extraction settings panel."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QDoubleSpinBox, QSpinBox,
)

from config import VOCAL_EXTRACT_METHODS, DEFAULTS
from gui.panels.helpers import make_help_label


class VoiceExtractionPanel(QWidget):
    """Vocal isolation settings before transcription."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        vocal_group = QGroupBox("Voice Extraction")
        vocal_layout = QVBoxLayout()
        vocal_layout.addWidget(make_help_label(
            "Optional step that tries to isolate vocals from music / noise before "
            "transcription. Helpful for songs or busy background audio."
        ))

        method_row = QHBoxLayout()
        method_label = QLabel("Extraction Method:")
        method_label.setMinimumWidth(150)
        self.vocal_combo = QComboBox()
        self.vocal_combo.addItems(VOCAL_EXTRACT_METHODS)
        self.vocal_combo.setCurrentText(DEFAULTS['vocal_extract'])
        self.vocal_combo.currentTextChanged.connect(self._on_method_changed)
        method_row.addWidget(method_label)
        method_row.addWidget(self.vocal_combo)
        method_row.addStretch()
        vocal_layout.addLayout(method_row)

        self.roformer_widget = QWidget()
        roformer_layout = QHBoxLayout(self.roformer_widget)
        roformer_layout.setContentsMargins(0, 0, 0, 0)

        overlap_label = QLabel("Roformer Overlap:")
        overlap_label.setMinimumWidth(150)
        self.roformer_overlap_spin = QDoubleSpinBox()
        self.roformer_overlap_spin.setRange(0.0, 1.0)
        self.roformer_overlap_spin.setSingleStep(0.05)
        self.roformer_overlap_spin.setValue(float(DEFAULTS['roformer_overlap']))

        vram_label = QLabel("VRAM (GB):")
        self.roformer_vram_spin = QSpinBox()
        self.roformer_vram_spin.setRange(1, 24)
        self.roformer_vram_spin.setValue(int(DEFAULTS['roformer_vram']))

        roformer_layout.addWidget(overlap_label)
        roformer_layout.addWidget(self.roformer_overlap_spin)
        roformer_layout.addWidget(vram_label)
        roformer_layout.addWidget(self.roformer_vram_spin)
        roformer_layout.addStretch()
        vocal_layout.addWidget(self.roformer_widget)

        vocal_group.setLayout(vocal_layout)
        layout.addWidget(vocal_group)

        self._on_method_changed(self.vocal_combo.currentText())

    def _on_method_changed(self, method):
        self.roformer_widget.setVisible(method == 'mb-roformer')

    def get_settings(self):
        return {
            'vocal_extract': self.vocal_combo.currentText(),
            'roformer_overlap': self.roformer_overlap_spin.value(),
            'roformer_vram': self.roformer_vram_spin.value(),
        }

    def get_transcription_options(self):
        vocal_extract = self.vocal_combo.currentText()
        if vocal_extract == 'none':
            vocal_extract = None
        return {
            'vocal_extract': vocal_extract,
            'roformer_overlap': self.roformer_overlap_spin.value(),
            'roformer_vram': self.roformer_vram_spin.value(),
        }

    def apply_settings(self, settings):
        if settings.get('vocal_extract') in VOCAL_EXTRACT_METHODS:
            self.vocal_combo.setCurrentText(settings['vocal_extract'])
        if 'roformer_overlap' in settings:
            self.roformer_overlap_spin.setValue(float(settings['roformer_overlap']))
        if 'roformer_vram' in settings:
            self.roformer_vram_spin.setValue(int(settings['roformer_vram']))
