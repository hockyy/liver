"""Speaker diarization settings panel."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QSpinBox,
)

from config import DIARIZE_METHODS, DEFAULTS
from gui.panels.helpers import make_help_label


class DiarizationPanel(QWidget):
    """Speaker separation and labeling settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        diarize_group = QGroupBox("Speaker Diarization")
        diarize_layout = QVBoxLayout()
        diarize_layout.addWidget(make_help_label(
            "Labels who is speaking (Speaker 1, Speaker 2, …) in the output. "
            "Useful for interviews or multi-speaker content."
        ))

        method_row = QHBoxLayout()
        method_label = QLabel("Diarization Method:")
        method_label.setMinimumWidth(150)
        method_label.setToolTip("Enable speaker separation/identification")
        self.diarize_combo = QComboBox()
        self.diarize_combo.addItems(DIARIZE_METHODS)
        self.diarize_combo.setCurrentText(DEFAULTS['diarize_method'])
        self.diarize_combo.currentTextChanged.connect(self._on_method_changed)
        method_row.addWidget(method_label)
        method_row.addWidget(self.diarize_combo)
        method_row.addStretch()
        diarize_layout.addLayout(method_row)

        self.diarize_options_widget = QWidget()
        options_layout = QVBoxLayout(self.diarize_options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)

        device_row = QHBoxLayout()
        device_label = QLabel("Diarization Device:")
        device_label.setMinimumWidth(150)
        self.diarize_device_combo = QComboBox()
        self.diarize_device_combo.addItems(['cuda', 'cpu'])
        self.diarize_device_combo.setCurrentText(DEFAULTS['diarize_device'])
        device_row.addWidget(device_label)
        device_row.addWidget(self.diarize_device_combo)
        device_row.addStretch()
        options_layout.addLayout(device_row)

        speakers_row = QHBoxLayout()
        num_label = QLabel("Number of Speakers:")
        num_label.setMinimumWidth(150)
        num_label.setToolTip("Set to 0 for automatic detection")
        self.num_speakers_spin = QSpinBox()
        self.num_speakers_spin.setRange(0, 20)
        self.num_speakers_spin.setValue(DEFAULTS['num_speakers'])
        self.num_speakers_spin.setSpecialValueText("Auto-detect")
        speakers_row.addWidget(num_label)
        speakers_row.addWidget(self.num_speakers_spin)
        speakers_row.addStretch()
        options_layout.addLayout(speakers_row)

        minmax_row = QHBoxLayout()
        min_label = QLabel("Min Speakers:")
        min_label.setMinimumWidth(150)
        self.min_speakers_spin = QSpinBox()
        self.min_speakers_spin.setRange(1, 20)
        self.min_speakers_spin.setValue(DEFAULTS['min_speakers'])
        max_label = QLabel("Max Speakers:")
        self.max_speakers_spin = QSpinBox()
        self.max_speakers_spin.setRange(1, 20)
        self.max_speakers_spin.setValue(DEFAULTS['max_speakers'])
        minmax_row.addWidget(min_label)
        minmax_row.addWidget(self.min_speakers_spin)
        minmax_row.addWidget(max_label)
        minmax_row.addWidget(self.max_speakers_spin)
        minmax_row.addStretch()
        options_layout.addLayout(minmax_row)

        diarize_layout.addWidget(self.diarize_options_widget)
        diarize_group.setLayout(diarize_layout)
        layout.addWidget(diarize_group)

        self._on_method_changed(self.diarize_combo.currentText())

    def _on_method_changed(self, method):
        self.diarize_options_widget.setVisible(method != 'none')

    def get_settings(self):
        return {
            'diarize_method': self.diarize_combo.currentText(),
            'diarize_device': self.diarize_device_combo.currentText(),
            'num_speakers': self.num_speakers_spin.value(),
            'min_speakers': self.min_speakers_spin.value(),
            'max_speakers': self.max_speakers_spin.value(),
        }

    def get_transcription_options(self):
        diarize_method = self.diarize_combo.currentText()
        if diarize_method == 'none':
            diarize_method = None
        return {
            'diarize_method': diarize_method,
            'diarize_device': self.diarize_device_combo.currentText(),
            'num_speakers': self.num_speakers_spin.value(),
            'min_speakers': self.min_speakers_spin.value(),
            'max_speakers': self.max_speakers_spin.value(),
        }

    def apply_settings(self, settings):
        if settings.get('diarize_method') in DIARIZE_METHODS:
            self.diarize_combo.setCurrentText(settings['diarize_method'])
        if settings.get('diarize_device') in ['cuda', 'cpu']:
            self.diarize_device_combo.setCurrentText(settings['diarize_device'])
        if 'num_speakers' in settings:
            self.num_speakers_spin.setValue(int(settings['num_speakers']))
        if 'min_speakers' in settings:
            self.min_speakers_spin.setValue(int(settings['min_speakers']))
        if 'max_speakers' in settings:
            self.max_speakers_spin.setValue(int(settings['max_speakers']))
