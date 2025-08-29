"""Utility functions for Subana application"""

from datetime import datetime
import os


def milliseconds_to_time(ms: int) -> str:
    """Convert milliseconds to readable time format (HH:MM:SS.mmm)"""
    seconds = ms / 1000
    minutes = int(seconds // 60)
    seconds = seconds % 60
    hours = int(minutes // 60)
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def milliseconds_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format (HH:MM:SS,mmm)"""
    seconds = ms / 1000
    minutes = int(seconds // 60)
    seconds = seconds % 60
    hours = int(minutes // 60)
    minutes = minutes % 60
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def milliseconds_to_vtt_time(ms: int) -> str:
    """Convert milliseconds to WebVTT time format (HH:MM:SS.mmm)"""
    # VTT uses period instead of comma
    return milliseconds_to_srt_time(ms).replace(',', '.')


def seconds_to_duration(seconds: float) -> str:
    """Convert seconds to duration string (MM:SS or HH:MM:SS)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def get_timestamp() -> str:
    """Get current timestamp for exports"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def ensure_extension(filename: str, extension: str) -> str:
    """Ensure filename has the correct extension"""
    if not extension.startswith('.'):
        extension = '.' + extension
    
    if not filename.lower().endswith(extension.lower()):
        return filename + extension
    return filename
