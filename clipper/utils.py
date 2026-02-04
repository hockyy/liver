"""Utility functions for the clipper application"""

import re


def time_str_to_seconds(timestr):
    """Convert a time string in the format 'HH:MM:SS,mmm' to seconds (float)."""
    try:
        parts = timestr.split(':')
        hours = int(parts[0].strip())
        minutes = int(parts[1].strip())
        sec, milli = parts[2].strip().split(',')
        seconds = int(sec)
        milliseconds = int(milli)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    except Exception:
        return None


def seconds_to_ffmpeg_time(secs):
    """Convert seconds to ffmpeg time format HH:MM:SS.mmm"""
    hours = int(secs // 3600)
    minutes = int((secs % 3600) // 60)
    seconds = secs % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


# Regex pattern for parsing timestamps
TIMESTAMP_PATTERN = re.compile(
    r'(\d{2}):(\d{2}):(\d{2})(?:,(\d{3}))?\s*-->\s*'
    r'(\d{2}):(\d{2}):(\d{2})(?:,(\d{3}))?\s*'
)


def parse_timestamp_line(line):
    """
    Parse a timestamp line and return (start_str, end_str, duration) or None if invalid.
    """
    line = line.strip()
    if not line:
        return None
    
    match = TIMESTAMP_PATTERN.match(line)
    if not match:
        return None
    
    # Extract times
    start_hours, start_minutes, start_seconds = match.group(1), match.group(2), match.group(3)
    start_millis = match.group(4) or "000"
    start_str = f"{start_hours}:{start_minutes}:{start_seconds},{start_millis}"
    
    end_hours, end_minutes, end_seconds = match.group(5), match.group(6), match.group(7)
    end_millis = match.group(8) or "000"
    end_str = f"{end_hours}:{end_minutes}:{end_seconds},{end_millis}"
    
    start_secs = time_str_to_seconds(start_str)
    end_secs = time_str_to_seconds(end_str)
    
    if start_secs is None or end_secs is None or start_secs >= end_secs:
        return None
    
    return (start_str, end_str, end_secs - start_secs)
