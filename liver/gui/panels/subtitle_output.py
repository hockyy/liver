"""Subtitle timing, layout, and preview panel."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QCheckBox,
    QSpinBox, QFrame, QTextEdit,
)
from PyQt5.QtGui import QFont

from config import (
    DEFAULTS, REALIGN_DEVICES, MAX_COMMA_CENT_OPTIONS, HIGHLIGHT_SILENCE_OPTIONS,
    TIKTOK_LAYOUT_DEFAULTS,
)
from gui.panels.helpers import make_help_label


TIKTOK_HELP = (
    'One timed word per line from Whisper, then local wrap + <u>underline</u> '
    'highlights. Captions disappear during silence.'
)
STANDARD_HELP = (
    'Normal subtitles — word-level timing plus a second pass that nudges each '
    'line to match speech more closely.'
)

# Clip from sample recording used in the live preview (2026-07-12 02-47-48.webm)
PREVIEW_SAMPLE = {
    'start': '00:00:00,000',
    'end': '00:00:09,220',
    'end_realign': '00:00:09,180',
    'line1': 'hello hello everyone why the fuck is it',
    'line2': "lagging I don't know why turn off the low",
    'short_wrap': "hello hello everyone\nwhy the fuck is it\nlagging I don't know",
    'karaoke_preview': [
        (5.22, 5.54, "I don't know <u>why</u>"),
        (5.54, 6.39, "<u>turn</u> off the"),
        (8.66, 8.88, "turn <u>off</u> the"),
        (8.88, 9.00, "turn off <u>the</u>"),
        (9.00, 9.22, "<u>low</u> power mode okay now"),
    ],
    'karaoke_silence_gap': (6.39, 8.66),
}


class SubtitleOutputPanel(QWidget):
    """Subtitle output: Standard (default) or TikTok highlight mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applying_mode_defaults = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Subtitle Output")
        group_layout = QVBoxLayout()

        self.tiktok_mode_check = QCheckBox("TikTok mode (word highlights)")
        self.tiktok_mode_check.setChecked(DEFAULTS.get('tiktok_mode', False))
        self.tiktok_mode_check.setToolTip(
            "Short highlighted caption lines for TikTok / Shorts. "
            "Off = standard precise subtitles."
        )
        self.tiktok_mode_check.stateChanged.connect(self._on_tiktok_mode_changed)
        group_layout.addWidget(self.tiktok_mode_check)

        self.mode_help = QLabel()
        self.mode_help.setWordWrap(True)
        self.mode_help.setStyleSheet("color: #7ec8c8; font-size: 12px; padding: 2px 0 8px 0;")
        group_layout.addWidget(self.mode_help)

        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.StyledPanel)
        preview_frame.setStyleSheet(
            "QFrame { background-color: #1e1e1e; border: 1px solid #3a3a3a; border-radius: 4px; }"
        )
        preview_layout = QVBoxLayout(preview_frame)
        preview_title = QLabel("Preview (example .srt)")
        preview_title.setStyleSheet("font-weight: bold; color: #bbb;")
        self.subtitle_preview = QTextEdit()
        self.subtitle_preview.setReadOnly(True)
        self.subtitle_preview.setMaximumHeight(240)
        self.subtitle_preview.setFont(QFont("Consolas", 9))
        self.subtitle_preview.setStyleSheet(
            "QTextEdit { background-color: #141414; color: #e8e8e8; border: none; }"
        )
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.subtitle_preview)
        group_layout.addWidget(preview_frame)

        self.layout_subgroup = QGroupBox("Line layout")
        format_layout = QVBoxLayout()

        self.standard_only_widget = QWidget()
        standard_only_layout = QVBoxLayout(self.standard_only_widget)
        standard_only_layout.setContentsMargins(0, 0, 0, 0)

        self.sentence_split_check = QCheckBox("Split at sentence boundaries")
        self.sentence_split_check.setChecked(DEFAULTS['sentence_split'])
        self.sentence_split_check.setToolTip(
            "Start a new subtitle block at each sentence."
        )
        self.sentence_split_check.stateChanged.connect(self.update_state)
        standard_only_layout.addWidget(self.sentence_split_check)

        comma_row = QHBoxLayout()
        comma_label = QLabel("Break at comma:")
        comma_label.setMinimumWidth(120)
        self.max_comma_cent_combo = QComboBox()
        self.max_comma_cent_combo.addItems(MAX_COMMA_CENT_OPTIONS)
        self.max_comma_cent_combo.setCurrentText(DEFAULTS['max_comma_cent'])
        self.max_comma_cent_combo.setToolTip(
            "When a line is this full (percent of max width), prefer breaking at a comma."
        )
        self.max_comma_cent_combo.currentTextChanged.connect(self.update_state)
        comma_row.addWidget(comma_label)
        comma_row.addWidget(self.max_comma_cent_combo, 1)
        standard_only_layout.addLayout(comma_row)

        format_layout.addWidget(self.standard_only_widget)

        width_row = QHBoxLayout()
        width_label = QLabel("Max chars / line:")
        width_label.setMinimumWidth(120)
        self.max_line_width_spin = QSpinBox()
        self.max_line_width_spin.setRange(10, 1000)
        self.max_line_width_spin.setValue(DEFAULTS['max_line_width'])
        self.max_line_width_spin.setToolTip("Wrap text after this many characters.")
        self.max_line_width_spin.valueChanged.connect(self.update_state)
        width_row.addWidget(width_label)
        width_row.addWidget(self.max_line_width_spin)
        width_row.addStretch()
        format_layout.addLayout(width_row)

        count_row = QHBoxLayout()
        count_label = QLabel("Max lines:")
        count_label.setMinimumWidth(120)
        self.max_line_count_spin = QSpinBox()
        self.max_line_count_spin.setRange(1, 4)
        self.max_line_count_spin.setValue(DEFAULTS['max_line_count'])
        self.max_line_count_spin.setToolTip("Maximum stacked lines in one subtitle block.")
        self.max_line_count_spin.valueChanged.connect(self.update_state)
        count_row.addWidget(count_label)
        count_row.addWidget(self.max_line_count_spin)
        count_row.addStretch()
        format_layout.addLayout(count_row)

        self.layout_subgroup.setLayout(format_layout)
        group_layout.addWidget(self.layout_subgroup)

        self.realign_device_widget = QWidget()
        realign_device_row = QHBoxLayout(self.realign_device_widget)
        realign_device_row.setContentsMargins(0, 0, 0, 0)
        device_label = QLabel("Refine timing on:")
        device_label.setMinimumWidth(120)
        device_label.setToolTip("GPU is faster; CPU works if CUDA is unavailable.")
        self.realign_device_combo = QComboBox()
        self.realign_device_combo.addItems(REALIGN_DEVICES)
        self.realign_device_combo.setCurrentText(DEFAULTS['realign_device'])
        self.realign_device_combo.currentTextChanged.connect(self.update_state)
        realign_device_row.addWidget(device_label)
        realign_device_row.addWidget(self.realign_device_combo, 1)
        realign_device_row.addStretch()
        group_layout.addWidget(self.realign_device_widget)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _on_tiktok_mode_changed(self, *_args):
        if self._applying_mode_defaults:
            return

        if self.tiktok_mode_check.isChecked():
            self._applying_mode_defaults = True
            self.max_line_width_spin.setValue(TIKTOK_LAYOUT_DEFAULTS['max_line_width'])
            self.max_line_count_spin.setValue(TIKTOK_LAYOUT_DEFAULTS['max_line_count'])
            self._applying_mode_defaults = False

        self.update_state()

    def _format_preview_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        secs_int = int(secs)
        millis = int(round((secs - secs_int) * 1000))
        return f"{hours:02}:{minutes:02}:{secs_int:02},{millis:03}"

    def _build_preview_text(self):
        sample = PREVIEW_SAMPLE
        tiktok = self.tiktok_mode_check.isChecked()
        max_width = self.max_line_width_spin.value()
        max_lines = self.max_line_count_spin.value()

        if tiktok:
            blocks = []
            for index, (start_sec, end_sec, text) in enumerate(
                sample['karaoke_preview'], start=1
            ):
                blocks.append(
                    f"{index}\n"
                    f"{self._format_preview_time(start_sec)} --> "
                    f"{self._format_preview_time(end_sec)}\n{text}"
                )
            gap_start, gap_end = sample['karaoke_silence_gap']
            gap_secs = gap_end - gap_start
            note = (
                f"# TikTok — ~{max_width} chars/line, one <u>word</u> highlighted per cue\n"
                f"# … no captions from {self._format_preview_time(gap_start)} "
                f"to {self._format_preview_time(gap_end)} ({gap_secs:.1f}s silence)"
            )
            return '\n\n'.join(blocks) + '\n\n' + note

        sentence = self.sentence_split_check.isChecked()
        block_body = f"{sample['line1']}\n{sample['line2']}"

        if sentence and max_width < 80:
            wrapped = sample['short_wrap']
            if max_lines == 1:
                wrapped = sample['line1'][:max_width]
            return (
                f"1\n{sample['start']} --> {sample['end_realign']}\n"
                f"{wrapped}\n\n"
                f"# Standard — ~{max_width} chars/line, sentence split"
            )

        return (
            f"1\n{sample['start']} --> {sample['end_realign']}\n"
            f"{block_body}\n\n"
            "# Standard — realignment adjusts lines to match speech"
        )

    def update_state(self):
        tiktok = self.tiktok_mode_check.isChecked()

        self.mode_help.setText(TIKTOK_HELP if tiktok else STANDARD_HELP)
        self.standard_only_widget.setVisible(not tiktok)
        self.realign_device_widget.setVisible(not tiktok)

        if tiktok:
            self.max_line_width_spin.setRange(10, 80)
            if self.max_line_width_spin.value() > 80:
                self.max_line_width_spin.setValue(TIKTOK_LAYOUT_DEFAULTS['max_line_width'])
            self.max_line_count_spin.setRange(1, 2)
        else:
            self.max_line_width_spin.setRange(10, 1000)
            self.max_line_count_spin.setRange(1, 4)

        self.subtitle_preview.setPlainText(self._build_preview_text())

    def initialize_after_load(self):
        self.update_state()

    def get_settings(self):
        return {
            'tiktok_mode': self.tiktok_mode_check.isChecked(),
            'realign_device': self.realign_device_combo.currentText(),
            'sentence_split': self.sentence_split_check.isChecked(),
            'max_line_width': self.max_line_width_spin.value(),
            'max_line_count': self.max_line_count_spin.value(),
            'max_comma_cent': self.max_comma_cent_combo.currentText(),
        }

    def get_transcription_options(self):
        tiktok = self.tiktok_mode_check.isChecked()
        options = {
            'realign': not tiktok,
            'realign_device': self.realign_device_combo.currentText(),
            'word_timestamps': True,
            'highlight_words': tiktok,
            'one_word': '0 - Disabled',
            'sentence_split': False if tiktok else self.sentence_split_check.isChecked(),
            'max_line_width': self.max_line_width_spin.value(),
            'max_line_count': self.max_line_count_spin.value(),
            'max_comma_cent': (
                '100 - Disabled' if tiktok else self.max_comma_cent_combo.currentText()
            ),
        }
        if tiktok:
            options.update(HIGHLIGHT_SILENCE_OPTIONS)
        return options

    def apply_settings(self, settings):
        if 'tiktok_mode' in settings:
            tiktok = bool(settings['tiktok_mode'])
        elif settings.get('highlight_words') and not settings.get('realign', True):
            tiktok = True
        else:
            tiktok = False

        self._applying_mode_defaults = True
        self.tiktok_mode_check.setChecked(tiktok)

        if settings.get('realign_device') in REALIGN_DEVICES:
            self.realign_device_combo.setCurrentText(settings['realign_device'])
        if 'sentence_split' in settings:
            self.sentence_split_check.setChecked(bool(settings['sentence_split']))
        if 'max_line_width' in settings:
            self.max_line_width_spin.setValue(int(settings['max_line_width']))
        if 'max_line_count' in settings:
            self.max_line_count_spin.setValue(int(settings['max_line_count']))
        if settings.get('max_comma_cent') in MAX_COMMA_CENT_OPTIONS:
            self.max_comma_cent_combo.setCurrentText(settings['max_comma_cent'])

        self._applying_mode_defaults = False
        self.update_state()