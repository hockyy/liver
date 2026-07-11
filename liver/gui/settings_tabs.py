"""Settings area composing all configuration panels."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame

from gui.panels.basic import BasicSettingsPanel
from gui.panels.vad import VadPanel
from gui.panels.voice_extraction import VoiceExtractionPanel
from gui.panels.subtitle_output import SubtitleOutputPanel
from gui.panels.diarization import DiarizationPanel
from gui.panels.helpers import CollapsibleSection


class SettingsTabs(QWidget):
    """All transcription settings in one scrollable panel."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.basic = BasicSettingsPanel()
        self.vad = VadPanel()
        self.voice = VoiceExtractionPanel()
        self.subtitle = SubtitleOutputPanel()
        self.diarization = DiarizationPanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(4)

        sections = (
            ("Model & Language", self.basic, True),
            ("Voice Activity Detection", self.vad, False),
            ("Voice Extraction", self.voice, False),
            ("Subtitle Output", self.subtitle, True),
            ("Speaker Diarization", self.diarization, False),
        )
        for title, panel, expanded in sections:
            section = CollapsibleSection(title, expanded=expanded)
            section.add_widget(panel)
            content_layout.addWidget(section)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def build_transcription_options(self):
        """Merge panel options for the transcriber."""
        options = {}
        options.update(self.basic.get_transcription_options())
        options.update(self.vad.get_transcription_options())
        options.update(self.voice.get_transcription_options())
        options.update(self.subtitle.get_transcription_options())
        options.update(self.diarization.get_transcription_options())
        return options

    def initialize_after_load(self):
        """Sync derived UI state after settings are restored."""
        self.subtitle.initialize_after_load()
