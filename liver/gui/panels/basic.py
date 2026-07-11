"""Model and decoder settings panel."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QSpinBox,
)

from config import MODELS, LANGUAGES, DEFAULTS
from gui.panels.helpers import make_help_label


class BasicSettingsPanel(QWidget):
    """Whisper model, language, beam size, and best-of settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._build_model_group())
        layout.addLayout(self._build_parameters_group())

    def _build_model_group(self):
        layout = QVBoxLayout()
        model_group = QGroupBox("Model Configuration")
        model_layout = QVBoxLayout()

        model_row = QHBoxLayout()
        model_label = QLabel("Whisper Model:")
        model_label.setMinimumWidth(150)
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setCurrentText(DEFAULTS['model'])
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_row.addWidget(model_label)
        model_row.addWidget(self.model_combo)
        model_row.addStretch()
        model_layout.addLayout(model_row)

        lang_row = QHBoxLayout()
        self.lang_label = QLabel("Source Language:")
        self.lang_label.setMinimumWidth(150)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setCurrentText(DEFAULTS['language'])
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        model_layout.addLayout(lang_row)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        return layout

    def _build_parameters_group(self):
        layout = QVBoxLayout()
        param_group = QGroupBox("Transcription Parameters")
        param_layout = QVBoxLayout()
        param_layout.addWidget(make_help_label(
            "Decoder search settings. Higher beam / best-of can improve accuracy on "
            "difficult audio but take longer."
        ))

        beam_row = QHBoxLayout()
        beam_label = QLabel("Beam Size:")
        beam_label.setMinimumWidth(150)
        beam_label.setToolTip("Higher values may improve accuracy but slow down transcription")
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 20)
        self.beam_spin.setValue(int(DEFAULTS['beam_size']))
        beam_row.addWidget(beam_label)
        beam_row.addWidget(self.beam_spin)
        beam_row.addStretch()
        param_layout.addLayout(beam_row)

        best_row = QHBoxLayout()
        best_label = QLabel("Best of:")
        best_label.setMinimumWidth(150)
        best_label.setToolTip("Number of candidates to consider when sampling")
        self.best_spin = QSpinBox()
        self.best_spin.setRange(1, 10)
        self.best_spin.setValue(int(DEFAULTS['best_of']))
        best_row.addWidget(best_label)
        best_row.addWidget(self.best_spin)
        best_row.addStretch()
        param_layout.addLayout(best_row)

        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        return layout

    def _on_model_changed(self, model):
        is_cantonese = model == 'cantonese'
        self.lang_label.setVisible(not is_cantonese)
        self.lang_combo.setVisible(not is_cantonese)

    def get_settings(self):
        return {
            'model': self.model_combo.currentText(),
            'language': self.lang_combo.currentText(),
            'beam_size': self.beam_spin.value(),
            'best_of': self.best_spin.value(),
        }

    def get_transcription_options(self):
        lang = '' if self.model_combo.currentText() == 'cantonese' else self.lang_combo.currentText()
        return {
            'lang': lang,
            'beam_size': self.beam_spin.value(),
            'best_of': self.best_spin.value(),
        }

    def apply_settings(self, settings):
        if settings.get('model') in MODELS:
            self.model_combo.setCurrentText(settings['model'])
        if settings.get('language') in LANGUAGES:
            self.lang_combo.setCurrentText(settings['language'])
        if 'beam_size' in settings:
            self.beam_spin.setValue(int(settings['beam_size']))
        if 'best_of' in settings:
            self.best_spin.setValue(int(settings['best_of']))
