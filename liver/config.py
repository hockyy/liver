"""Configuration and constants for Subtitle Transcriber PRO."""
import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Settings file path (saved in same directory as the script)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

# Regular expression to match subtitle lines
SUBTITLE_REGEX = re.compile(r'^\[(\d+):(\d{2}\.\d{3}) --> (\d+):(\d{2}\.\d{3})\] (.+)$')

# Supported models
MODELS = ['large-v3', 'large-v3-turbo', 'large-v3-turbo-cantonese-16', 'cantonese', 'distil-large-v3']

# Supported languages
LANGUAGES = ['en', 'ja', 'zh', 'yue', 'id']

# Asian languages requiring special formatting
ASIAN_LANGUAGES = ['ja', 'zh', 'yue']

# VAD methods (Pro feature) - 'none' disables VAD filtering
VAD_METHODS = ['none', 'ten', 'silero_v6', 'silero_v6_fw', 'nemo_v2', 'pyannote_v3']

# Voice extraction methods (Pro feature)
VOCAL_EXTRACT_METHODS = ['none', 'mdx1_kim2', 'mdx2_kim2', 'mb-roformer']

# Realignment devices (Pro feature)
REALIGN_DEVICES = ['automatic', 'cuda', 'cpu']

# Diarization methods (Pro feature - speaker separation)
DIARIZE_METHODS = ['none', 'pyannote_v3.0', 'pyannote_v3.1', 'reverb_v1', 'reverb_v2']

# One word per line options
ONE_WORD_OPTIONS = ['0 - Disabled', '1 - One word/line', '2 - One word + min 50ms']

# Subtitle length presets for different content types
SUBTITLE_PRESETS = ['Default', 'Brainrot (Short)', 'YouTube Shorts', 'TikTok', 'Custom']

# Max comma cent options (percentage of line width to break at comma)
MAX_COMMA_CENT_OPTIONS = ['100 - Disabled', '90', '80', '70', '60', '50', '40', '30', '20']

# Supported media file extensions
VALID_MEDIA_EXTENSIONS = {
    '.mkv', '.mp4', '.wav', '.mp3', '.aac', '.opus', '.ts',
    '.avi', '.mov', '.flac', '.m4a', '.webm'
}

# Default values (PRO settings optimized for Japanese content)
DEFAULTS = {
    'model': 'large-v3',
    'language': 'ja',
    'beam_size': '10',
    'best_of': '5',
    'vad_method': 'ten',
    'vocal_extract': 'mb-roformer',
    'realign': True,
    'realign_device': 'automatic',
    'roformer_overlap': '0.25',
    'roformer_vram': '4',
    # Diarization settings
    'diarize_method': 'none',
    'diarize_device': 'cuda',
    'num_speakers': 0,  # 0 = auto-detect
    'min_speakers': 1,
    'max_speakers': 10,
    # Word-level timestamp settings
    'word_timestamps': True,
    'highlight_words': False,
    'one_word': '0 - Disabled',
    # Subtitle format settings (for brainrot/short-form content)
    'sentence_split': False,   # Enable sentence splitting (--sentence flag)
    'max_line_width': 1000,    # Max characters per line (1000 = essentially no limit)
    'max_line_count': 1,       # Max lines per subtitle (1-4)
    'max_comma_cent': '100 - Disabled',  # Break at comma after this % of line width
    'subtitle_preset': 'Default',
}

