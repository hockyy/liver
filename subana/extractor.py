"""JSON extraction logic for Subana application"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from models import Cue, Track, ProjectInfo, SubanaProject


class SubanaExtractor:
    """Handles extraction of data from Subana JSON files"""
    
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """Load and parse JSON file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.suffix.lower() == '.json':
            raise ValueError(f"File must be a JSON file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def extract_project_info(data: Dict[str, Any]) -> ProjectInfo:
        """Extract project information from JSON data"""
        info = ProjectInfo()
        
        # Extract basic info
        info.id = data.get('id', '')
        info.name = data.get('name', 'Untitled Project')
        
        # Extract video information
        if 'video' in data:
            video = data['video']
            info.youtube_id = video.get('youtubeId', '')
            info.video_filename = video.get('fileName', '')
            
            # Calculate duration
            if 'duration' in video:
                duration = video['duration']
                seconds = duration.get('seconds', 0)
                nanos = duration.get('nanos', 0)
                info.duration_seconds = seconds + (nanos / 1000000000)
        
        return info
    
    @staticmethod
    def extract_cue(cue_data: Dict[str, Any], track_id: str, speaker: str) -> Cue:
        """Extract a single cue from JSON data"""
        return Cue(
            id=cue_data.get('id', ''),
            track_id=track_id,
            speaker=speaker,
            start_ms=cue_data.get('startMillisecond', 0),
            end_ms=cue_data.get('endMillisecond', 0),
            text=cue_data.get('text', ''),
            original_text=cue_data.get('originalText', '')
        )
    
    @staticmethod
    def extract_track(track_data: Dict[str, Any]) -> Track:
        """Extract a single track from JSON data"""
        track_id = track_data.get('id', 'unknown')
        group_id = track_data.get('groupId', None)
        script = track_data.get('script', None)
        
        # Extract speaker name
        speaker_name = 'Unknown'
        if 'speaker' in track_data and 'name' in track_data['speaker']:
            speaker_name = track_data['speaker']['name']
        
        # Create track
        track = Track(
            id=track_id,
            group_id=group_id,
            script=script,
            speaker_name=speaker_name
        )
        
        # Extract cues
        if 'cuesList' in track_data:
            for cue_data in track_data['cuesList']:
                cue = SubanaExtractor.extract_cue(cue_data, track_id, speaker_name)
                track.cues.append(cue)
        
        return track
    
    @staticmethod
    def extract_project(file_path: str) -> SubanaProject:
        """Extract complete project from JSON file"""
        # Load JSON data
        data = SubanaExtractor.load_json_file(file_path)
        
        # Extract project info
        info = SubanaExtractor.extract_project_info(data)
        
        # Extract tracks
        tracks = []
        if 'tracksList' in data:
            for track_data in data['tracksList']:
                track = SubanaExtractor.extract_track(track_data)
                if track.cues:  # Only add tracks that have cues
                    tracks.append(track)
        
        # Create and return project
        return SubanaProject(
            info=info,
            tracks=tracks,
            raw_data=data
        )
    
    @staticmethod
    def get_track_summary(track: Track) -> Dict[str, Any]:
        """Get summary information for a track"""
        return {
            'id': track.id,
            'speaker': track.speaker_name,
            'cue_count': track.cue_count,
            'duration_ms': track.total_duration_ms,
            'first_cue_start': track.cues[0].start_ms if track.cues else 0,
            'last_cue_end': track.cues[-1].end_ms if track.cues else 0
        }
