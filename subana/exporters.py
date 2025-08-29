"""Export functionality for Subana application"""

import csv
from typing import List, Optional
from pathlib import Path

from models import Cue, Track, SubanaProject
from utils import (
    milliseconds_to_time,
    milliseconds_to_srt_time,
    milliseconds_to_vtt_time,
    get_timestamp,
    ensure_extension
)


class BaseExporter:
    """Base class for all exporters"""
    
    def __init__(self, project: SubanaProject):
        self.project = project
    
    def export(self, file_path: str, track_id: Optional[str] = None):
        """Export data to file. If track_id is provided, export only that track."""
        raise NotImplementedError


class TextExporter(BaseExporter):
    """Export to human-readable text format"""
    
    def export(self, file_path: str, track_id: Optional[str] = None):
        file_path = ensure_extension(file_path, '.txt')
        
        # Get cues to export
        if track_id:
            track = self.project.get_track_by_id(track_id)
            if not track:
                raise ValueError(f"Track not found: {track_id}")
            cues = track.cues
            export_title = f"Track: {track.get_display_name()}"
        else:
            cues = self.project.get_all_cues()
            export_title = "All Tracks"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"Project: {self.project.info.name}\n")
            f.write(f"Export: {export_title}\n")
            f.write(f"Generated: {get_timestamp()}\n")
            f.write(f"Total Cues: {len(cues)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write cues
            for i, cue in enumerate(cues, 1):
                f.write(f"[{i}] {milliseconds_to_time(cue.start_ms)} --> {milliseconds_to_time(cue.end_ms)}\n")
                f.write(f"Speaker: {cue.speaker}\n")
                f.write(f"Text: {cue.text}\n")
                if cue.original_text and cue.original_text != cue.text:
                    f.write(f"Original: {cue.original_text}\n")
                f.write("\n")


class CSVExporter(BaseExporter):
    """Export to CSV format"""
    
    def export(self, file_path: str, track_id: Optional[str] = None):
        file_path = ensure_extension(file_path, '.csv')
        
        # Get cues to export
        if track_id:
            track = self.project.get_track_by_id(track_id)
            if not track:
                raise ValueError(f"Track not found: {track_id}")
            cues = track.cues
        else:
            cues = self.project.get_all_cues()
        
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Index', 'Track ID', 'Speaker', 'Start Time', 'End Time', 
                'Duration (s)', 'Text', 'Original Text'
            ])
            
            # Write cues
            for i, cue in enumerate(cues, 1):
                writer.writerow([
                    i,
                    cue.track_id,
                    cue.speaker,
                    milliseconds_to_time(cue.start_ms),
                    milliseconds_to_time(cue.end_ms),
                    f"{cue.duration_seconds:.2f}",
                    cue.text,
                    cue.original_text
                ])


class SRTExporter(BaseExporter):
    """Export to SRT subtitle format"""
    
    def export(self, file_path: str, track_id: Optional[str] = None):
        file_path = ensure_extension(file_path, '.srt')
        
        # Get cues to export
        if track_id:
            track = self.project.get_track_by_id(track_id)
            if not track:
                raise ValueError(f"Track not found: {track_id}")
            cues = track.cues
        else:
            cues = self.project.get_all_cues()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for i, cue in enumerate(cues, 1):
                f.write(f"{i}\n")
                f.write(f"{milliseconds_to_srt_time(cue.start_ms)} --> {milliseconds_to_srt_time(cue.end_ms)}\n")
                
                # Use text if available, otherwise use original_text
                text = cue.text if cue.text else cue.original_text
                f.write(f"{text}\n\n")


class VTTExporter(BaseExporter):
    """Export to WebVTT subtitle format"""
    
    def export(self, file_path: str, track_id: Optional[str] = None):
        file_path = ensure_extension(file_path, '.vtt')
        
        # Get cues to export
        if track_id:
            track = self.project.get_track_by_id(track_id)
            if not track:
                raise ValueError(f"Track not found: {track_id}")
            cues = track.cues
        else:
            cues = self.project.get_all_cues()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write VTT header
            f.write("WEBVTT\n\n")
            
            # Write cues
            for i, cue in enumerate(cues, 1):
                f.write(f"{i}\n")
                f.write(f"{milliseconds_to_vtt_time(cue.start_ms)} --> {milliseconds_to_vtt_time(cue.end_ms)}\n")
                
                # Use text if available, otherwise use original_text
                text = cue.text if cue.text else cue.original_text
                f.write(f"{text}\n\n")


class ExporterFactory:
    """Factory class to create appropriate exporter"""
    
    EXPORTERS = {
        'txt': TextExporter,
        'csv': CSVExporter,
        'srt': SRTExporter,
        'vtt': VTTExporter
    }
    
    @classmethod
    def create_exporter(cls, format: str, project: SubanaProject) -> BaseExporter:
        """Create an exporter for the specified format"""
        format = format.lower()
        if format not in cls.EXPORTERS:
            raise ValueError(f"Unsupported export format: {format}")
        
        exporter_class = cls.EXPORTERS[format]
        return exporter_class(project)
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported export formats"""
        return list(cls.EXPORTERS.keys())
