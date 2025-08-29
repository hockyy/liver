"""Data models for Subana application"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Cue:
    """Represents a single subtitle cue"""
    id: str
    track_id: str
    speaker: str
    start_ms: int
    end_ms: int
    text: str
    original_text: str
    
    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms
    
    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000


@dataclass
class Track:
    """Represents a track containing multiple cues"""
    id: str
    group_id: Optional[str] = None
    script: Optional[int] = None
    speaker_name: str = "Unknown"
    cues: List[Cue] = field(default_factory=list)
    
    @property
    def cue_count(self) -> int:
        return len(self.cues)
    
    @property
    def total_duration_ms(self) -> int:
        if not self.cues:
            return 0
        return max(cue.end_ms for cue in self.cues) - min(cue.start_ms for cue in self.cues)
    
    def get_display_name(self) -> str:
        """Get a display name for the track"""
        return f"{self.speaker_name} ({self.id[:8]}...)" if len(self.id) > 8 else f"{self.speaker_name} ({self.id})"


@dataclass
class ProjectInfo:
    """Contains project metadata"""
    id: str = ""
    name: str = ""
    duration_seconds: float = 0
    youtube_id: str = ""
    video_filename: str = ""
    
    @property
    def duration_formatted(self) -> str:
        if self.duration_seconds > 0:
            minutes = int(self.duration_seconds // 60)
            seconds = int(self.duration_seconds % 60)
            return f"{minutes}:{seconds:02d}"
        return "Unknown"


@dataclass
class SubanaProject:
    """Complete project data"""
    info: ProjectInfo
    tracks: List[Track]
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_cues(self) -> int:
        return sum(track.cue_count for track in self.tracks)
    
    @property
    def track_count(self) -> int:
        return len(self.tracks)
    
    def get_all_cues(self) -> List[Cue]:
        """Get all cues from all tracks"""
        all_cues = []
        for track in self.tracks:
            all_cues.extend(track.cues)
        return all_cues
    
    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID"""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None
