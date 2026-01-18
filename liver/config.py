"""Configuration and constants for Subtitle Transcriber PRO."""
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regular expression to match subtitle lines
SUBTITLE_REGEX = re.compile(r'^\[(\d+):(\d{2}\.\d{3}) --> (\d+):(\d{2}\.\d{3})\] (.+)$')

# Supported models
MODELS = ['large-v3', 'large-v3-turbo', 'large-v3-turbo-cantonese-16', 'cantonese', 'distil-large-v3']

# Supported languages
LANGUAGES = ['en', 'ja', 'zh', 'yue', 'id']

# Asian languages requiring special formatting
ASIAN_LANGUAGES = ['ja', 'zh', 'yue']

# VAD methods (Pro feature)
VAD_METHODS = ['ten', 'silero_v6', 'silero_v6_fw', 'nemo_v2', 'pyannote_v3']

# Voice extraction methods (Pro feature)
VOCAL_EXTRACT_METHODS = ['none', 'mdx1_kim2', 'mdx2_kim2', 'mb-roformer']

# Realignment devices (Pro feature)
REALIGN_DEVICES = ['automatic', 'cuda', 'cpu']

# Diarization methods (Pro feature - speaker separation)
DIARIZE_METHODS = ['none', 'pyannote_v3.0', 'pyannote_v3.1', 'reverb_v1', 'reverb_v2']

# One word per line options
ONE_WORD_OPTIONS = ['0 - Disabled', '1 - One word/line', '2 - One word + min 50ms']

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
}

