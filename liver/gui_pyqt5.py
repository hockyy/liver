"""Modern PyQt5 GUI for Subtitle Transcriber PRO."""
import os
import sys
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGroupBox, QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton,
    QListWidget, QTextEdit, QProgressBar, QFileDialog, QSpinBox,
    QDoubleSpinBox, QTabWidget, QFrame, QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMimeData, QUrl
from PyQt5.QtGui import QFont, QPalette, QColor, QDragEnterEvent, QDropEvent, QIcon

from config import (
    MODELS, LANGUAGES, VAD_METHODS, VOCAL_EXTRACT_METHODS,
    REALIGN_DEVICES, VALID_MEDIA_EXTENSIONS, DEFAULTS,
    DIARIZE_METHODS, ONE_WORD_OPTIONS, SUBTITLE_PRESETS, MAX_COMMA_CENT_OPTIONS,
    SETTINGS_FILE
)
from transcriber import SubtitleTranscriber


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
            self.options
        )
        self.finished_signal.emit()
        
    def log_callback(self, message):
        """Thread-safe logging callback."""
        self.log_signal.emit(message)


class FileListWidget(QListWidget):
    """Custom list widget with drag and drop support."""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext in VALID_MEDIA_EXTENSIONS:
                    files.append(file_path)
            elif os.path.isdir(file_path):
                # Scan directory for media files
                for root, dirs, filenames in os.walk(file_path):
                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in VALID_MEDIA_EXTENSIONS:
                            files.append(os.path.join(root, filename))
        
        if files:
            self.files_dropped.emit(files)
        event.acceptProposedAction()


class ModernTranscriptionApp(QMainWindow):
    """Modern PyQt5 main window for Subtitle Transcriber PRO."""
    
    def __init__(self):
        super().__init__()
        self.transcriber = SubtitleTranscriber()
        self.queue = []
        self.is_processing = False
        self.current_worker = None
        
        self.init_ui()
        self.apply_modern_style()
        self.load_settings()  # Load saved settings on startup
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Subtitle Transcriber PRO - PyQt5")
        self.setGeometry(100, 100, 1100, 850)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section: Settings
        settings_widget = self.create_settings_section()
        splitter.addWidget(settings_widget)
        
        # Bottom section: Queue and logs
        bottom_widget = self.create_bottom_section()
        splitter.addWidget(bottom_widget)
        
        # Set initial sizes
        splitter.setSizes([450, 400])
        
        main_layout.addWidget(splitter)
        
        # Control buttons at the very bottom
        control_layout = self.create_control_buttons()
        main_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        main_layout.addWidget(self.progress_bar)
        
    def create_settings_section(self):
        """Create the settings section with tabs."""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tabs for better organization
        tabs = QTabWidget()
        
        # Basic Settings Tab (with scroll area)
        basic_scroll = QScrollArea()
        basic_scroll.setWidgetResizable(True)
        basic_scroll.setFrameShape(QFrame.NoFrame)
        basic_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.addLayout(self.create_model_settings())
        basic_layout.addLayout(self.create_basic_parameters())
        basic_layout.addStretch()
        
        basic_scroll.setWidget(basic_tab)
        tabs.addTab(basic_scroll, "Basic Settings")
        
        # PRO Features Tab (with scroll area for many settings)
        pro_scroll = QScrollArea()
        pro_scroll.setWidgetResizable(True)
        pro_scroll.setFrameShape(QFrame.NoFrame)
        pro_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        pro_tab = QWidget()
        pro_layout = QVBoxLayout(pro_tab)
        pro_layout.addLayout(self.create_vad_settings())
        pro_layout.addLayout(self.create_voice_extraction_settings())
        pro_layout.addLayout(self.create_realignment_settings())
        pro_layout.addLayout(self.create_word_timestamp_settings())
        pro_layout.addLayout(self.create_subtitle_format_settings())
        pro_layout.addLayout(self.create_diarization_settings())
        pro_layout.addStretch()
        
        pro_scroll.setWidget(pro_tab)
        tabs.addTab(pro_scroll, "PRO Features")
        
        settings_layout.addWidget(tabs)
        return settings_widget
        
    def create_model_settings(self):
        """Create model and language settings."""
        layout = QVBoxLayout()
        
        # Model selection group
        model_group = QGroupBox("Model Configuration")
        model_layout = QVBoxLayout()
        
        # Model selection
        model_row = QHBoxLayout()
        model_label = QLabel("Whisper Model:")
        model_label.setMinimumWidth(150)
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setCurrentText(DEFAULTS['model'])
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_row.addWidget(model_label)
        model_row.addWidget(self.model_combo)
        model_row.addStretch()
        model_layout.addLayout(model_row)
        
        # Language selection
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
        
    def create_basic_parameters(self):
        """Create basic transcription parameters."""
        layout = QVBoxLayout()
        
        param_group = QGroupBox("Transcription Parameters")
        param_layout = QVBoxLayout()
        
        # Beam size
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
        
        # Best of
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
        
    def create_vad_settings(self):
        """Create VAD method settings."""
        layout = QVBoxLayout()
        
        vad_group = QGroupBox("Voice Activity Detection (VAD)")
        vad_layout = QHBoxLayout()
        
        vad_label = QLabel("VAD Method:")
        vad_label.setMinimumWidth(150)
        self.vad_combo = QComboBox()
        self.vad_combo.addItems(VAD_METHODS)
        self.vad_combo.setCurrentText(DEFAULTS['vad_method'])
        
        vad_layout.addWidget(vad_label)
        vad_layout.addWidget(self.vad_combo)
        vad_layout.addStretch()
        
        vad_group.setLayout(vad_layout)
        layout.addWidget(vad_group)
        
        return layout
        
    def create_voice_extraction_settings(self):
        """Create voice extraction settings."""
        layout = QVBoxLayout()
        
        vocal_group = QGroupBox("Voice Extraction [PRO]")
        vocal_layout = QVBoxLayout()
        
        # Method selection
        method_row = QHBoxLayout()
        method_label = QLabel("Extraction Method:")
        method_label.setMinimumWidth(150)
        self.vocal_combo = QComboBox()
        self.vocal_combo.addItems(VOCAL_EXTRACT_METHODS)
        self.vocal_combo.setCurrentText(DEFAULTS['vocal_extract'])
        self.vocal_combo.currentTextChanged.connect(self.on_vocal_extract_changed)
        method_row.addWidget(method_label)
        method_row.addWidget(self.vocal_combo)
        method_row.addStretch()
        vocal_layout.addLayout(method_row)
        
        # Roformer settings (hidden by default)
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
        
        # Show by default since mb-roformer is the default setting
        self.roformer_widget.show()
        vocal_layout.addWidget(self.roformer_widget)
        
        vocal_group.setLayout(vocal_layout)
        layout.addWidget(vocal_group)
        
        return layout
        
    def create_realignment_settings(self):
        """Create realignment settings."""
        layout = QVBoxLayout()
        
        realign_group = QGroupBox("Word-Level Realignment [PRO]")
        realign_layout = QVBoxLayout()
        
        # Enable checkbox
        self.realign_check = QCheckBox("Enable Realignment")
        self.realign_check.setChecked(DEFAULTS['realign'])
        realign_layout.addWidget(self.realign_check)
        
        # Device selection
        device_row = QHBoxLayout()
        device_label = QLabel("Realignment Device:")
        device_label.setMinimumWidth(150)
        self.realign_device_combo = QComboBox()
        self.realign_device_combo.addItems(REALIGN_DEVICES)
        self.realign_device_combo.setCurrentText(DEFAULTS['realign_device'])
        device_row.addWidget(device_label)
        device_row.addWidget(self.realign_device_combo)
        device_row.addStretch()
        realign_layout.addLayout(device_row)
        
        realign_group.setLayout(realign_layout)
        layout.addWidget(realign_group)
        
        return layout
    
    def create_word_timestamp_settings(self):
        """Create word-level timestamp settings."""
        layout = QVBoxLayout()
        
        word_group = QGroupBox("Word Timestamps [PRO]")
        word_layout = QVBoxLayout()
        
        # Word timestamps checkbox
        self.word_timestamps_check = QCheckBox("Enable Word Timestamps")
        self.word_timestamps_check.setChecked(DEFAULTS['word_timestamps'])
        self.word_timestamps_check.setToolTip("Extract word-level timestamps for more accurate timing")
        word_layout.addWidget(self.word_timestamps_check)
        
        # Highlight words (karaoke) checkbox
        self.highlight_words_check = QCheckBox("Highlight Words (Karaoke Style)")
        self.highlight_words_check.setChecked(DEFAULTS['highlight_words'])
        self.highlight_words_check.setToolTip("Underline each word as it is spoken in SRT/VTT output")
        word_layout.addWidget(self.highlight_words_check)
        
        # One word per line setting
        one_word_row = QHBoxLayout()
        one_word_label = QLabel("One Word Per Line:")
        one_word_label.setMinimumWidth(150)
        one_word_label.setToolTip("Output one word per subtitle line")
        self.one_word_combo = QComboBox()
        self.one_word_combo.addItems(ONE_WORD_OPTIONS)
        self.one_word_combo.setCurrentText(DEFAULTS['one_word'])
        one_word_row.addWidget(one_word_label)
        one_word_row.addWidget(self.one_word_combo)
        one_word_row.addStretch()
        word_layout.addLayout(one_word_row)
        
        word_group.setLayout(word_layout)
        layout.addWidget(word_group)
        
        return layout
    
    def create_subtitle_format_settings(self):
        """Create subtitle format settings for brainrot/short-form content."""
        layout = QVBoxLayout()
        
        format_group = QGroupBox("Subtitle Format [Brainrot/Shorts]")
        format_layout = QVBoxLayout()
        
        # Preset selection
        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setMinimumWidth(150)
        preset_label.setToolTip("Quick presets for different content types")
        self.subtitle_preset_combo = QComboBox()
        self.subtitle_preset_combo.addItems(SUBTITLE_PRESETS)
        self.subtitle_preset_combo.setCurrentText(DEFAULTS['subtitle_preset'])
        self.subtitle_preset_combo.currentTextChanged.connect(self.on_subtitle_preset_changed)
        preset_row.addWidget(preset_label)
        preset_row.addWidget(self.subtitle_preset_combo)
        preset_row.addStretch()
        format_layout.addLayout(preset_row)
        
        # Sentence split checkbox
        self.sentence_split_check = QCheckBox("Enable Sentence Splitting")
        self.sentence_split_check.setChecked(DEFAULTS['sentence_split'])
        self.sentence_split_check.setToolTip("Split subtitles at sentence boundaries (required for line width/count to work properly)")
        self.sentence_split_check.stateChanged.connect(self.on_subtitle_format_changed)
        format_layout.addWidget(self.sentence_split_check)
        
        # Max line width (characters)
        width_row = QHBoxLayout()
        width_label = QLabel("Max Chars/Line:")
        width_label.setMinimumWidth(150)
        width_label.setToolTip("Maximum characters per subtitle line")
        self.max_line_width_spin = QSpinBox()
        self.max_line_width_spin.setRange(10, 1000)
        self.max_line_width_spin.setValue(DEFAULTS['max_line_width'])
        self.max_line_width_spin.valueChanged.connect(self.on_subtitle_format_changed)
        width_row.addWidget(width_label)
        width_row.addWidget(self.max_line_width_spin)
        width_row.addStretch()
        format_layout.addLayout(width_row)
        
        # Max line count
        count_row = QHBoxLayout()
        count_label = QLabel("Max Lines:")
        count_label.setMinimumWidth(150)
        count_label.setToolTip("Maximum number of lines per subtitle entry")
        self.max_line_count_spin = QSpinBox()
        self.max_line_count_spin.setRange(1, 4)
        self.max_line_count_spin.setValue(DEFAULTS['max_line_count'])
        self.max_line_count_spin.valueChanged.connect(self.on_subtitle_format_changed)
        count_row.addWidget(count_label)
        count_row.addWidget(self.max_line_count_spin)
        count_row.addStretch()
        format_layout.addLayout(count_row)
        
        # Max comma cent (break at comma)
        comma_row = QHBoxLayout()
        comma_label = QLabel("Break at Comma:")
        comma_label.setMinimumWidth(150)
        comma_label.setToolTip("Break line at comma after this percentage of max line width (requires sentence splitting)")
        self.max_comma_cent_combo = QComboBox()
        self.max_comma_cent_combo.addItems(MAX_COMMA_CENT_OPTIONS)
        self.max_comma_cent_combo.setCurrentText(DEFAULTS['max_comma_cent'])
        self.max_comma_cent_combo.currentTextChanged.connect(self.on_subtitle_format_changed)
        comma_row.addWidget(comma_label)
        comma_row.addWidget(self.max_comma_cent_combo)
        comma_row.addStretch()
        format_layout.addLayout(comma_row)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        return layout
    
    def on_subtitle_preset_changed(self, preset):
        """Apply subtitle format preset."""
        # Presets: sentence_split, width, count, comma_cent
        presets = {
            'Default': {'sentence': False, 'width': 1000, 'count': 1, 'comma': '100 - Disabled'},
            'Brainrot (Short)': {'sentence': True, 'width': 20, 'count': 1, 'comma': '50'},
            'YouTube Shorts': {'sentence': True, 'width': 30, 'count': 2, 'comma': '70'},
            'TikTok': {'sentence': True, 'width': 25, 'count': 1, 'comma': '60'},
            'Custom': None  # Don't change values
        }
        
        if preset in presets and presets[preset] is not None:
            values = presets[preset]
            # Block signals to prevent recursive calls
            self.sentence_split_check.blockSignals(True)
            self.max_line_width_spin.blockSignals(True)
            self.max_line_count_spin.blockSignals(True)
            self.max_comma_cent_combo.blockSignals(True)
            
            self.sentence_split_check.setChecked(values['sentence'])
            self.max_line_width_spin.setValue(values['width'])
            self.max_line_count_spin.setValue(values['count'])
            self.max_comma_cent_combo.setCurrentText(values['comma'])
            
            self.sentence_split_check.blockSignals(False)
            self.max_line_width_spin.blockSignals(False)
            self.max_line_count_spin.blockSignals(False)
            self.max_comma_cent_combo.blockSignals(False)
    
    def on_subtitle_format_changed(self):
        """Handle manual change to subtitle format - switch to Custom preset."""
        self.subtitle_preset_combo.blockSignals(True)
        self.subtitle_preset_combo.setCurrentText('Custom')
        self.subtitle_preset_combo.blockSignals(False)
    
    def create_diarization_settings(self):
        """Create speaker diarization settings."""
        layout = QVBoxLayout()
        
        diarize_group = QGroupBox("Speaker Diarization [PRO]")
        diarize_layout = QVBoxLayout()
        
        # Diarization method selection
        method_row = QHBoxLayout()
        method_label = QLabel("Diarization Method:")
        method_label.setMinimumWidth(150)
        method_label.setToolTip("Enable speaker separation/identification")
        self.diarize_combo = QComboBox()
        self.diarize_combo.addItems(DIARIZE_METHODS)
        self.diarize_combo.setCurrentText(DEFAULTS['diarize_method'])
        self.diarize_combo.currentTextChanged.connect(self.on_diarize_changed)
        method_row.addWidget(method_label)
        method_row.addWidget(self.diarize_combo)
        method_row.addStretch()
        diarize_layout.addLayout(method_row)
        
        # Diarization options (hidden by default)
        self.diarize_options_widget = QWidget()
        diarize_options_layout = QVBoxLayout(self.diarize_options_widget)
        diarize_options_layout.setContentsMargins(0, 0, 0, 0)
        
        # Device selection
        device_row = QHBoxLayout()
        device_label = QLabel("Diarization Device:")
        device_label.setMinimumWidth(150)
        self.diarize_device_combo = QComboBox()
        self.diarize_device_combo.addItems(['cuda', 'cpu'])
        self.diarize_device_combo.setCurrentText(DEFAULTS['diarize_device'])
        device_row.addWidget(device_label)
        device_row.addWidget(self.diarize_device_combo)
        device_row.addStretch()
        diarize_options_layout.addLayout(device_row)
        
        # Number of speakers (0 = auto)
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
        diarize_options_layout.addLayout(speakers_row)
        
        # Min/Max speakers row
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
        diarize_options_layout.addLayout(minmax_row)
        
        # Hide by default since 'none' is default
        self.diarize_options_widget.hide()
        diarize_layout.addWidget(self.diarize_options_widget)
        
        diarize_group.setLayout(diarize_layout)
        layout.addWidget(diarize_group)
        
        return layout
    
    def on_diarize_changed(self, method):
        """Handle diarization method change."""
        is_enabled = method != 'none'
        self.diarize_options_widget.setVisible(is_enabled)
        
    def create_bottom_section(self):
        """Create bottom section with queue and logs."""
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # File queue
        queue_group = QGroupBox("Processing Queue (Drag & Drop Files Here)")
        queue_layout = QVBoxLayout()
        
        self.queue_list = FileListWidget()
        self.queue_list.setMinimumHeight(120)
        self.queue_list.files_dropped.connect(self.on_files_dropped)
        queue_layout.addWidget(self.queue_list)
        
        # Queue buttons
        queue_btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Files")
        add_btn.clicked.connect(self.browse_and_add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_files)
        clear_btn = QPushButton("Clear Queue")
        clear_btn.clicked.connect(self.clear_queue)
        
        queue_btn_layout.addWidget(add_btn)
        queue_btn_layout.addWidget(remove_btn)
        queue_btn_layout.addWidget(clear_btn)
        queue_btn_layout.addStretch()
        queue_layout.addLayout(queue_btn_layout)
        
        queue_group.setLayout(queue_layout)
        bottom_layout.addWidget(queue_group)
        
        # Logs
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)
        
        # Log control buttons
        log_btn_layout = QHBoxLayout()
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(clear_log_btn)
        log_layout.addLayout(log_btn_layout)
        
        log_group.setLayout(log_layout)
        bottom_layout.addWidget(log_group)
        
        return bottom_widget
        
    def create_control_buttons(self):
        """Create main control buttons."""
        layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_processing)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        
        return layout
        
    def apply_modern_style(self):
        """Apply modern dark theme styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px;
                min-width: 120px;
                color: #e0e0e0;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #0d7377;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #3a3a3a;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid #e0e0e0;
                width: 6px;
                height: 6px;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
            QPushButton:pressed {
                background-color: #0a5f63;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666666;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 2px dashed #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }
            QListWidget::item:selected {
                background-color: #0d7377;
                color: white;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
                color: #e0e0e0;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #0d7377;
                border-radius: 3px;
            }
            QCheckBox {
                spacing: 5px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border: 1px solid #0d7377;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
            }
            QSplitter::handle {
                background-color: #3a3a3a;
                height: 2px;
            }
            QSplitter::handle:hover {
                background-color: #0d7377;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0d7377;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
    def on_model_changed(self, model):
        """Handle model selection change."""
        # Hide language selection for Cantonese model
        is_cantonese = model == 'cantonese'
        self.lang_label.setVisible(not is_cantonese)
        self.lang_combo.setVisible(not is_cantonese)
        
    def on_vocal_extract_changed(self, method):
        """Handle vocal extraction method change."""
        # Show roformer settings only for mb-roformer
        is_roformer = method == 'mb-roformer'
        self.roformer_widget.setVisible(is_roformer)
        
    def on_files_dropped(self, files):
        """Handle files dropped onto the queue."""
        added_count = 0
        for file_path in files:
            if file_path not in self.queue:
                self.queue.append(file_path)
                self.queue_list.addItem(file_path)
                added_count += 1
        
        if added_count > 0:
            self.log(f"Added {added_count} file(s) via drag and drop\n")
            
    def browse_and_add_files(self):
        """Browse and add files to queue."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio/Video Files",
            os.path.expanduser("~"),
            "Media Files (*.mkv *.mp4 *.wav *.mp3 *.aac *.opus *.ts *.avi *.mov *.flac *.m4a *.webm);;All Files (*.*)"
        )
        
        added_count = 0
        for file_path in files:
            if file_path not in self.queue:
                self.queue.append(file_path)
                self.queue_list.addItem(file_path)
                added_count += 1
                
        if added_count > 0:
            self.log(f"Added {added_count} file(s) to queue\n")
            
    def remove_selected_files(self):
        """Remove selected files from queue."""
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            self.log("No files selected to remove\n")
            return
            
        for item in selected_items:
            file_path = item.text()
            if file_path in self.queue:
                self.queue.remove(file_path)
            row = self.queue_list.row(item)
            self.queue_list.takeItem(row)
            
        self.log(f"Removed {len(selected_items)} file(s) from queue\n")
        
    def clear_queue(self):
        """Clear the entire queue."""
        if self.queue:
            count = len(self.queue)
            self.queue.clear()
            self.queue_list.clear()
            self.log(f"Cleared {count} file(s) from queue\n")
            
    def clear_log(self):
        """Clear the log."""
        self.log_text.clear()
        
    def build_options(self):
        """Build transcription options from GUI settings."""
        lang = '' if self.model_combo.currentText() == 'cantonese' else self.lang_combo.currentText()
        
        vocal_extract = self.vocal_combo.currentText()
        if vocal_extract == 'none':
            vocal_extract = None
        
        diarize_method = self.diarize_combo.currentText()
        if diarize_method == 'none':
            diarize_method = None
            
        return {
            'lang': lang,
            'beam_size': self.beam_spin.value(),
            'best_of': self.best_spin.value(),
            'vad_method': self.vad_combo.currentText(),
            'vocal_extract': vocal_extract,
            'realign': self.realign_check.isChecked(),
            'realign_device': self.realign_device_combo.currentText(),
            'roformer_overlap': self.roformer_overlap_spin.value(),
            'roformer_vram': self.roformer_vram_spin.value(),
            # Word timestamp options
            'word_timestamps': self.word_timestamps_check.isChecked(),
            'highlight_words': self.highlight_words_check.isChecked(),
            'one_word': self.one_word_combo.currentText(),
            # Subtitle format options (brainrot/shorts)
            'sentence_split': self.sentence_split_check.isChecked(),
            'max_line_width': self.max_line_width_spin.value(),
            'max_line_count': self.max_line_count_spin.value(),
            'max_comma_cent': self.max_comma_cent_combo.currentText(),
            # Diarization options
            'diarize_method': diarize_method,
            'diarize_device': self.diarize_device_combo.currentText(),
            'num_speakers': self.num_speakers_spin.value(),
            'min_speakers': self.min_speakers_spin.value(),
            'max_speakers': self.max_speakers_spin.value(),
        }
        
    def start_processing(self):
        """Start processing the queue."""
        if self.is_processing:
            self.log("Processing is already in progress\n")
            return
            
        if not self.queue:
            self.log("No files in queue. Please add files first\n")
            return
            
        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.process_next_file()
        
    def process_next_file(self):
        """Process the next file in the queue."""
        if not self.queue or not self.is_processing:
            self.finish_processing()
            return
            
        file_path = self.queue[0]
        self.log(f"Processing: {file_path}\n")
        self.progress_bar.setFormat(f"Processing: {os.path.basename(file_path)}")
        
        # Update transcriber model
        self.transcriber.model = self.model_combo.currentText()
        
        # Build options
        options = self.build_options()
        
        # Create worker thread
        self.current_worker = TranscriptionWorker(self.transcriber, file_path, options)
        self.current_worker.log_signal.connect(self.log, Qt.QueuedConnection)
        self.current_worker.finished_signal.connect(self.on_file_finished, Qt.QueuedConnection)
        self.current_worker.start()
        
    def on_file_finished(self):
        """Handle completion of a file."""
        if self.queue:
            finished_file = self.queue.pop(0)
            self.queue_list.takeItem(0)
            self.log(f"Finished: {finished_file}\n\n")
            
        # Process next file
        QTimer.singleShot(100, self.process_next_file)
        
    def finish_processing(self):
        """Finish processing and clean up."""
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        self.log("All files processed!\n")
        
    def stop_processing(self):
        """Stop current processing."""
        self.is_processing = False
        self.transcriber.stop_transcription()
        
        if self.current_worker:
            self.current_worker.terminate()
            self.current_worker.wait()
            
        self.finish_processing()
        self.log("Processing stopped by user\n")
        
    def log(self, message):
        """Log a message to the log area."""
        self.log_text.append(message.rstrip())
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def get_all_settings(self):
        """Get all current settings as a dictionary."""
        return {
            'model': self.model_combo.currentText(),
            'language': self.lang_combo.currentText(),
            'beam_size': self.beam_spin.value(),
            'best_of': self.best_spin.value(),
            'vad_method': self.vad_combo.currentText(),
            'vocal_extract': self.vocal_combo.currentText(),
            'realign': self.realign_check.isChecked(),
            'realign_device': self.realign_device_combo.currentText(),
            'roformer_overlap': self.roformer_overlap_spin.value(),
            'roformer_vram': self.roformer_vram_spin.value(),
            'word_timestamps': self.word_timestamps_check.isChecked(),
            'highlight_words': self.highlight_words_check.isChecked(),
            'one_word': self.one_word_combo.currentText(),
            'sentence_split': self.sentence_split_check.isChecked(),
            'max_line_width': self.max_line_width_spin.value(),
            'max_line_count': self.max_line_count_spin.value(),
            'max_comma_cent': self.max_comma_cent_combo.currentText(),
            'subtitle_preset': self.subtitle_preset_combo.currentText(),
            'diarize_method': self.diarize_combo.currentText(),
            'diarize_device': self.diarize_device_combo.currentText(),
            'num_speakers': self.num_speakers_spin.value(),
            'min_speakers': self.min_speakers_spin.value(),
            'max_speakers': self.max_speakers_spin.value(),
            'last_saved': datetime.now().isoformat(),
        }
    
    def save_settings(self):
        """Save current settings to JSON file."""
        try:
            settings = self.get_all_settings()
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            self.log(f"Settings saved to {SETTINGS_FILE}\n")
        except Exception as e:
            self.log(f"Error saving settings: {e}\n")
    
    def load_settings(self):
        """Load settings from JSON file if it exists."""
        if not os.path.exists(SETTINGS_FILE):
            return
        
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Apply settings to UI components (with validation)
            if settings.get('model') in MODELS:
                self.model_combo.setCurrentText(settings['model'])
            if settings.get('language') in LANGUAGES:
                self.lang_combo.setCurrentText(settings['language'])
            if 'beam_size' in settings:
                self.beam_spin.setValue(int(settings['beam_size']))
            if 'best_of' in settings:
                self.best_spin.setValue(int(settings['best_of']))
            if settings.get('vad_method') in VAD_METHODS:
                self.vad_combo.setCurrentText(settings['vad_method'])
            if settings.get('vocal_extract') in VOCAL_EXTRACT_METHODS:
                self.vocal_combo.setCurrentText(settings['vocal_extract'])
            if 'realign' in settings:
                self.realign_check.setChecked(bool(settings['realign']))
            if settings.get('realign_device') in REALIGN_DEVICES:
                self.realign_device_combo.setCurrentText(settings['realign_device'])
            if 'roformer_overlap' in settings:
                self.roformer_overlap_spin.setValue(float(settings['roformer_overlap']))
            if 'roformer_vram' in settings:
                self.roformer_vram_spin.setValue(int(settings['roformer_vram']))
            if 'word_timestamps' in settings:
                self.word_timestamps_check.setChecked(bool(settings['word_timestamps']))
            if 'highlight_words' in settings:
                self.highlight_words_check.setChecked(bool(settings['highlight_words']))
            if settings.get('one_word') in ONE_WORD_OPTIONS:
                self.one_word_combo.setCurrentText(settings['one_word'])
            if 'sentence_split' in settings:
                self.sentence_split_check.setChecked(bool(settings['sentence_split']))
            if 'max_line_width' in settings:
                self.max_line_width_spin.setValue(int(settings['max_line_width']))
            if 'max_line_count' in settings:
                self.max_line_count_spin.setValue(int(settings['max_line_count']))
            if settings.get('max_comma_cent') in MAX_COMMA_CENT_OPTIONS:
                self.max_comma_cent_combo.setCurrentText(settings['max_comma_cent'])
            if settings.get('subtitle_preset') in SUBTITLE_PRESETS:
                self.subtitle_preset_combo.setCurrentText(settings['subtitle_preset'])
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
            
            last_saved = settings.get('last_saved', 'unknown')
            self.log(f"Loaded settings from {SETTINGS_FILE} (last saved: {last_saved})\n")
            
        except Exception as e:
            self.log(f"Error loading settings: {e}\n")
    
    def closeEvent(self, event):
        """Save settings when the application is closed."""
        self.save_settings()
        event.accept()


def run_app():
    """Run the PyQt5 application."""
    app = QApplication(sys.argv)
    window = ModernTranscriptionApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run_app()

