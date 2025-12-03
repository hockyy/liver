"""Utility functions for subtitle processing."""
import codecs
import re
from datetime import timedelta


def clean_srt(file_path):
    """Clean and normalize SRT subtitle file."""
    try:
        with codecs.open(file_path, 'r', encoding='utf-8-sig') as file:
            content = file.read()
    except UnicodeDecodeError:
        with codecs.open(file_path, 'r', encoding='iso-8859-1') as file:
            content = file.read()

    # Remove BOM if present
    content = content.lstrip('\ufeff')

    # Remove non-printable characters except newlines and CJK characters
    content = re.sub(
        r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u1100-\u11ff'
        r'\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\u4e00-\u9fff\x20-\x7E\n]',
        '', content
    )

    # Fix common encoding issues
    content = content.replace('â€™', "'")
    content = content.replace('â€"', "–")
    content = content.replace('â€œ', '"')
    content = content.replace('â€', '"')

    with codecs.open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

    print(f"Cleaned SRT file has been saved as {file_path}")


def format_timestamp(seconds):
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"


def format_timestamp_from_match(minutes, sec_mili):
    """Format timestamp from regex match groups."""
    total_seconds = float(minutes) * 60 + float(sec_mili)
    secint = int(total_seconds)
    milliseconds = int((total_seconds - secint) * 1000)
    hours, minutes = divmod(secint, 3600)
    minutes, seconds = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

