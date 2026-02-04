"""
SRT Preprocessor for Video Clipping
Analyzes subtitle files using AI to identify clip-worthy moments.

Handles long transcripts by chunking with overlap to avoid missing
moments at chunk boundaries.
"""

import re
import os
import sys
import json
import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def load_env_file():
    """Load environment variables from .env file in the script's directory."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value and key not in os.environ:  # Don't override existing env vars
                        os.environ[key] = value


# Load .env file on import
load_env_file()


@dataclass
class SubtitleEntry:
    """A single subtitle entry from an SRT file."""
    index: int
    start_time: str  # HH:MM:SS,mmm format
    end_time: str
    text: str
    start_seconds: float
    end_seconds: float


@dataclass
class MergedEntry:
    """
    A merged entry combining multiple short subtitle entries.
    Tracks the original entries for timestamp mapping.
    """
    merged_index: int  # The display index (1, 2, 3...)
    text: str  # Combined text with " - " separators
    original_entries: list[SubtitleEntry]  # Original entries that were merged
    
    @property
    def start_time(self) -> str:
        return self.original_entries[0].start_time
    
    @property
    def end_time(self) -> str:
        return self.original_entries[-1].end_time
    
    @property
    def start_seconds(self) -> float:
        return self.original_entries[0].start_seconds
    
    @property
    def end_seconds(self) -> float:
        return self.original_entries[-1].end_seconds


@dataclass
class ClipSuggestion:
    """A suggested clip from AI analysis."""
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    reason: str
    category: str  # e.g., "funny", "dramatic", "educational", "highlight"
    confidence: float  # 0.0 to 1.0


def time_str_to_seconds(timestr: str) -> float:
    """Convert SRT timestamp 'HH:MM:SS,mmm' to seconds."""
    try:
        parts = timestr.split(':')
        hours = int(parts[0].strip())
        minutes = int(parts[1].strip())
        sec_parts = parts[2].strip().replace('.', ',').split(',')
        seconds = int(sec_parts[0])
        milliseconds = int(sec_parts[1]) if len(sec_parts) > 1 else 0
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    except Exception:
        return 0.0


def seconds_to_time_str(seconds: float) -> str:
    """Convert seconds to SRT timestamp 'HH:MM:SS,mmm'."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt(srt_path: str) -> list[SubtitleEntry]:
    """Parse an SRT file into a list of SubtitleEntry objects."""
    with open(srt_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # SRT format: index\ntimestamp --> timestamp\ntext\n\n
    pattern = re.compile(
        r'(\d+)\s*\n'
        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n'
        r'((?:(?!\n\n|\n\d+\s*\n).)+)',
        re.DOTALL
    )
    
    entries = []
    for match in pattern.finditer(content):
        index = int(match.group(1))
        start_time = match.group(2).replace('.', ',')
        end_time = match.group(3).replace('.', ',')
        text = match.group(4).strip().replace('\n', ' ')
        
        entries.append(SubtitleEntry(
            index=index,
            start_time=start_time,
            end_time=end_time,
            text=text,
            start_seconds=time_str_to_seconds(start_time),
            end_seconds=time_str_to_seconds(end_time)
        ))
    
    return sorted(entries, key=lambda e: e.start_seconds)


def estimate_tokens(text: str) -> int:
    """Rough token estimation (avg 4 chars per token for English)."""
    return len(text) // 4


def merge_short_entries(
    entries: list[SubtitleEntry],
    min_duration_seconds: float = 3.0,
    max_merge_gap_seconds: float = 1.0,
    max_merged_duration_seconds: float = 15.0,
) -> list[MergedEntry]:
    """
    Merge short consecutive subtitle entries into combined entries.
    
    Short entries (like quick dialogue exchanges) are combined using " - " separator.
    This significantly reduces token count while preserving content.
    
    Args:
        entries: List of subtitle entries to merge
        min_duration_seconds: Entries shorter than this may be merged
        max_merge_gap_seconds: Maximum gap between entries to merge them
        max_merged_duration_seconds: Maximum total duration for a merged entry
    
    Returns:
        List of MergedEntry objects with mapping to original entries
    """
    if not entries:
        return []
    
    merged_entries = []
    current_group = [entries[0]]
    
    for entry in entries[1:]:
        last_entry = current_group[-1]
        
        # Calculate gap between entries
        gap = entry.start_seconds - last_entry.end_seconds
        
        # Calculate total duration if we merge
        total_duration = entry.end_seconds - current_group[0].start_seconds
        
        # Decide whether to merge
        should_merge = (
            gap <= max_merge_gap_seconds and
            total_duration <= max_merged_duration_seconds and
            (last_entry.end_seconds - last_entry.start_seconds) < min_duration_seconds
        )
        
        if should_merge:
            current_group.append(entry)
        else:
            # Save current group and start new one
            merged_index = len(merged_entries) + 1
            merged_text = " - ".join(e.text for e in current_group)
            merged_entries.append(MergedEntry(
                merged_index=merged_index,
                text=merged_text,
                original_entries=current_group.copy()
            ))
            current_group = [entry]
    
    # Don't forget the last group
    if current_group:
        merged_index = len(merged_entries) + 1
        merged_text = " - ".join(e.text for e in current_group)
        merged_entries.append(MergedEntry(
            merged_index=merged_index,
            text=merged_text,
            original_entries=current_group.copy()
        ))
    
    return merged_entries


def build_entry_mapping(merged_entries: list[MergedEntry]) -> dict[int, MergedEntry]:
    """Build a mapping from merged index to MergedEntry for quick lookup."""
    return {entry.merged_index: entry for entry in merged_entries}


def chunk_subtitles(
    entries: list[SubtitleEntry], 
    max_tokens: int = 6000,
    overlap_seconds: float = 60.0
) -> list[tuple[list[MergedEntry], float, float]]:
    """
    Merge short entries and split into chunks that fit within token limits.
    Returns list of (merged_entries, chunk_start_seconds, chunk_end_seconds).
    
    Overlap ensures we don't miss clip-worthy moments at chunk boundaries.
    """
    if not entries:
        return []
    
    # First, merge short entries to reduce token count
    merged = merge_short_entries(entries)
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    chunk_start = merged[0].start_seconds
    
    for entry in merged:
        # New compact format: "N | text"
        entry_text = f"{entry.merged_index} | {entry.text}\n"
        entry_tokens = estimate_tokens(entry_text)
        
        if current_tokens + entry_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunk_end = current_chunk[-1].end_seconds
            chunks.append((current_chunk.copy(), chunk_start, chunk_end))
            
            # Start new chunk with overlap
            overlap_start = chunk_end - overlap_seconds
            current_chunk = [e for e in current_chunk if e.start_seconds >= overlap_start]
            current_tokens = sum(estimate_tokens(f"{e.merged_index} | {e.text}\n") for e in current_chunk)
            chunk_start = current_chunk[0].start_seconds if current_chunk else entry.start_seconds
        
        current_chunk.append(entry)
        current_tokens += entry_tokens
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_end = current_chunk[-1].end_seconds
        chunks.append((current_chunk, chunk_start, chunk_end))
    
    return chunks


def format_chunk_for_ai(
    entries: list[MergedEntry], 
    chunk_index: int, 
    total_chunks: int,
    video_context: str = ""
) -> str:
    """
    Format a subtitle chunk into a compact prompt for AI analysis.
    
    Uses numbered entries instead of timestamps to save tokens.
    The " - " in text indicates speaker changes or quick exchanges.
    """
    
    # Build the transcript text with entry numbers (much more compact!)
    transcript_lines = []
    for entry in entries:
        transcript_lines.append(f"{entry.merged_index} | {entry.text}")
    
    transcript = "\n".join(transcript_lines)
    
    entry_range = f"entries {entries[0].merged_index}-{entries[-1].merged_index}" if entries else "N/A"
    
    prompt = f"""Analyze this video transcript to find clip-worthy moments.

TRANSCRIPT FORMAT:
- Each line: "NUMBER | text"
- " - " within text indicates speaker changes or quick dialogue exchanges
{f'- Video context: {video_context}' if video_context else ''}
- This is chunk {chunk_index + 1}/{total_chunks} ({entry_range})

TRANSCRIPT:
{transcript}

TASK:
Find 3-10 clip-worthy moments. Look for:
- Funny/entertaining moments
- Dramatic or emotional moments  
- Key insights or educational content
- Memorable quotes or highlights

For each clip, give the entry range that captures full context (a few entries before/after the key moment).

RESPONSE FORMAT (JSON only):
{{
  "clips": [
    {{
      "start_entry": <number>,
      "end_entry": <number>,
      "reason": "Why this is clip-worthy",
      "category": "funny|dramatic|educational|highlight|quote",
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "Brief summary of this section"
}}

Return valid JSON only. If nothing clip-worthy, return {{"clips": [], "summary": "..."}}.
"""
    return prompt


def query_ai_openai(prompt: str, api_key: str, model: str = "gpt-4o") -> dict:
    """Query OpenAI API for clip suggestions."""
    import urllib.request
    import urllib.error
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a video editor assistant. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"OpenAI API error: {e.code} - {e.read().decode()}")
        return {"clips": [], "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        return {"clips": [], "error": str(e)}


def query_ai_anthropic(prompt: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> dict:
    """Query Anthropic API for clip suggestions."""
    import urllib.request
    import urllib.error
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    data = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt + "\n\nRespond with valid JSON only, no markdown code blocks."}
        ]
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result['content'][0]['text']
            # Try to extract JSON if wrapped in markdown
            if '```' in content:
                json_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"Anthropic API error: {e.code} - {e.read().decode()}")
        return {"clips": [], "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        return {"clips": [], "error": str(e)}


def query_ai_ollama(prompt: str, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> dict:
    """Query local Ollama for clip suggestions."""
    import urllib.request
    import urllib.error
    
    url = f"{base_url}/api/generate"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({
        "model": model,
        "prompt": prompt + "\n\nRespond with valid JSON only, no markdown code blocks.",
        "stream": False,
        "format": "json"
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result.get('response', '{}')
            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"Ollama API error: {e.code}")
        return {"clips": [], "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        return {"clips": [], "error": str(e)}


def query_ai_openrouter(prompt: str, api_key: str, model: str = "anthropic/claude-sonnet-4-20250514") -> dict:
    """Query OpenRouter API for clip suggestions (non-streaming)."""
    import urllib.request
    import urllib.error
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/user/srt-preprocessor",
    }
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a video editor assistant. Always respond with valid JSON only, no markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            # Try to extract JSON if wrapped in markdown
            if '```' in content:
                json_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            return json.loads(content)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print(f"OpenRouter API error: {e.code} - {error_body}")
        return {"clips": [], "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        return {"clips": [], "error": str(e)}


def query_ai_openrouter_stream(
    prompt: str, 
    api_key: str, 
    model: str = "anthropic/claude-sonnet-4-20250514",
    on_token: callable = None,
    verbose: bool = True
) -> dict:
    """
    Query OpenRouter API with streaming support.
    
    Args:
        prompt: The prompt to send
        api_key: OpenRouter API key
        model: Model name
        on_token: Callback function called with each token (for GUI updates)
        verbose: Whether to print to terminal
    
    Returns:
        Parsed JSON response
    """
    import urllib.request
    import urllib.error
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/user/srt-preprocessor",
    }
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a video editor assistant. Always respond with valid JSON only, no markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": True,
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    full_content = ""
    
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            for line in response:
                line = line.decode('utf-8').strip()
                if not line or not line.startswith('data: '):
                    continue
                
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str == '[DONE]':
                    break
                
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    token = delta.get('content', '')
                    
                    if token:
                        full_content += token
                        
                        # Print to terminal
                        if verbose:
                            print(token, end='', flush=True)
                        
                        # Call callback for GUI updates
                        if on_token:
                            on_token(token)
                            
                except json.JSONDecodeError:
                    continue
        
        if verbose:
            print()  # Newline after streaming
        
        # Parse the complete response as JSON
        content = full_content
        if '```' in content:
            json_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
        
        return json.loads(content)
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print(f"\nOpenRouter API error: {e.code} - {error_body}")
        return {"clips": [], "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"\nFailed to parse AI response as JSON: {e}")
        print(f"Raw content: {full_content[:500]}...")
        return {"clips": [], "error": str(e)}


def merge_clip_suggestions(
    all_suggestions: list[ClipSuggestion],
    merge_threshold_seconds: float = 5.0
) -> list[ClipSuggestion]:
    """
    Merge overlapping or adjacent clip suggestions.
    Keeps the one with highest confidence if they overlap significantly.
    """
    if not all_suggestions:
        return []
    
    # Sort by start time
    sorted_clips = sorted(all_suggestions, key=lambda c: c.start_seconds)
    
    merged = []
    current = sorted_clips[0]
    
    for clip in sorted_clips[1:]:
        # Check if clips overlap or are very close
        if clip.start_seconds <= current.end_seconds + merge_threshold_seconds:
            # Merge: extend the range, keep higher confidence one's metadata
            if clip.confidence > current.confidence:
                current = ClipSuggestion(
                    start_time=current.start_time,
                    end_time=max(current.end_time, clip.end_time, key=time_str_to_seconds),
                    start_seconds=current.start_seconds,
                    end_seconds=max(current.end_seconds, clip.end_seconds),
                    reason=clip.reason,
                    category=clip.category,
                    confidence=clip.confidence
                )
            else:
                current = ClipSuggestion(
                    start_time=current.start_time,
                    end_time=max(current.end_time, clip.end_time, key=time_str_to_seconds),
                    start_seconds=current.start_seconds,
                    end_seconds=max(current.end_seconds, clip.end_seconds),
                    reason=current.reason,
                    category=current.category,
                    confidence=current.confidence
                )
        else:
            merged.append(current)
            current = clip
    
    merged.append(current)
    return merged


def analyze_srt(
    srt_path: str,
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    video_context: str = "",
    max_tokens_per_chunk: int = 6000,
    min_confidence: float = 0.5,
    verbose: bool = True,
    dry_run: bool = False,
    stream: bool = False,
    on_token: callable = None,
    on_chunk_start: callable = None,
    on_chunk_complete: callable = None,
) -> list[ClipSuggestion]:
    """
    Main function to analyze an SRT file and return clip suggestions.
    
    Args:
        srt_path: Path to the SRT file
        provider: AI provider (openrouter, openai, anthropic, ollama)
        api_key: API key for the provider
        model: Model name to use
        video_context: Additional context about the video
        max_tokens_per_chunk: Maximum tokens per chunk
        min_confidence: Minimum confidence threshold for clips
        verbose: Whether to print progress to terminal
        dry_run: Only show what would be done without making API calls
        stream: Use streaming API (OpenRouter only)
        on_token: Callback for each streamed token (for GUI)
        on_chunk_start: Callback when starting a chunk analysis
        on_chunk_complete: Callback when a chunk is complete with its clips
    """
    # Parse SRT
    if verbose:
        print(f"Parsing SRT file: {srt_path}")
    entries = parse_srt(srt_path)
    
    if not entries:
        print("No subtitle entries found in file.")
        return []
    
    total_duration = entries[-1].end_seconds - entries[0].start_seconds
    if verbose:
        print(f"Found {len(entries)} subtitle entries")
        print(f"Total duration: {seconds_to_time_str(total_duration)}")
    
    # Chunk the subtitles (this also merges short entries)
    chunks = chunk_subtitles(entries, max_tokens=max_tokens_per_chunk)
    
    # Build global entry mapping for converting entry numbers back to timestamps
    all_merged_entries = []
    for chunk_entries, _, _ in chunks:
        for entry in chunk_entries:
            if entry not in all_merged_entries:
                all_merged_entries.append(entry)
    entry_mapping = build_entry_mapping(all_merged_entries)
    
    # Calculate total tokens for estimation (now with compact format)
    total_tokens = sum(
        sum(estimate_tokens(f"{e.merged_index} | {e.text}\n") for e in chunk_entries)
        for chunk_entries, _, _ in chunks
    )
    
    # Calculate merged entry stats
    total_original = len(entries)
    total_merged = len(all_merged_entries)
    compression_ratio = total_original / total_merged if total_merged > 0 else 1
    
    if verbose:
        print(f"Merged into {total_merged} entries (from {total_original}, {compression_ratio:.1f}x compression)")
    
    # Resolve provider and model for display
    display_provider = provider
    display_model = model
    if provider == "openrouter":
        display_model = model or os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-sonnet-4-20250514"
    elif provider == "openai":
        display_model = model or "gpt-4o"
    elif provider == "anthropic":
        display_model = model or "claude-sonnet-4-20250514"
    elif provider == "ollama":
        display_model = model or "llama3.2"
    
    # Show dry run info
    print(f"\n{'='*60}")
    print("DRY RUN SUMMARY" if dry_run else "ANALYSIS PLAN")
    print("="*60)
    print(f"Provider:        {display_provider}")
    print(f"Model:           {display_model}")
    print(f"Chunks:          {len(chunks)}")
    print(f"API queries:     {len(chunks)}")
    print(f"Est. tokens:     ~{total_tokens:,} tokens total")
    print(f"Video duration:  {seconds_to_time_str(total_duration)}")
    print("="*60)
    
    # Show chunk breakdown
    print("\nChunk breakdown:")
    for i, (chunk_entries, chunk_start, chunk_end) in enumerate(chunks):
        chunk_tokens = sum(estimate_tokens(f"{e.merged_index} | {e.text}\n") for e in chunk_entries)
        entry_range = f"entries {chunk_entries[0].merged_index}-{chunk_entries[-1].merged_index}"
        print(f"  {i+1}. {seconds_to_time_str(chunk_start)} - {seconds_to_time_str(chunk_end)} ({entry_range}, ~{chunk_tokens:,} tokens)")
    
    if dry_run:
        print(f"\n[DRY RUN] Would make {len(chunks)} API request(s) to {display_provider}")
        print("Run without --dry-run to execute.")
        return []
    
    print()  # Blank line before starting
    
    # Resolve API key early
    if provider == "openrouter":
        if not api_key:
            api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY in .env or pass --api-key")
    elif provider == "openai":
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass --api-key")
    elif provider == "anthropic":
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass --api-key")
    
    # Analyze each chunk
    all_suggestions = []
    
    for i, (chunk_entries, chunk_start, chunk_end) in enumerate(chunks):
        chunk_info = {
            "index": i + 1,
            "total": len(chunks),
            "start": seconds_to_time_str(chunk_start),
            "end": seconds_to_time_str(chunk_end),
        }
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"CHUNK {i+1}/{len(chunks)} ({seconds_to_time_str(chunk_start)} - {seconds_to_time_str(chunk_end)})")
            print("="*60)
        
        # Notify chunk start
        if on_chunk_start:
            on_chunk_start(chunk_info)
        
        prompt = format_chunk_for_ai(chunk_entries, i, len(chunks), video_context)
        
        # Query the appropriate AI provider
        if provider == "openrouter":
            if stream:
                if verbose:
                    print("AI Response:\n")
                result = query_ai_openrouter_stream(
                    prompt, api_key, display_model,
                    on_token=on_token,
                    verbose=verbose
                )
            else:
                result = query_ai_openrouter(prompt, api_key, display_model)
        
        elif provider == "openai":
            result = query_ai_openai(prompt, api_key, model or "gpt-4o")
        
        elif provider == "anthropic":
            result = query_ai_anthropic(prompt, api_key, model or "claude-sonnet-4-20250514")
        
        elif provider == "ollama":
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            result = query_ai_ollama(prompt, model or "llama3.2", base_url)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Parse clip suggestions from result (now using entry ranges)
        clips = result.get("clips", [])
        chunk_suggestions = []
        
        if verbose:
            print(f"\n  => Found {len(clips)} clip suggestions")
            if result.get("summary"):
                print(f"  => Summary: {result['summary'][:100]}...")
        
        for clip in clips:
            try:
                start_entry = int(clip["start_entry"])
                end_entry = int(clip["end_entry"])
                
                # Look up the merged entries to get timestamps
                if start_entry not in entry_mapping or end_entry not in entry_mapping:
                    if verbose:
                        print(f"  Skipping clip with invalid entry range: {start_entry}-{end_entry}")
                    continue
                
                start_merged = entry_mapping[start_entry]
                end_merged = entry_mapping[end_entry]
                
                suggestion = ClipSuggestion(
                    start_time=start_merged.start_time,
                    end_time=end_merged.end_time,
                    start_seconds=start_merged.start_seconds,
                    end_seconds=end_merged.end_seconds,
                    reason=clip.get("reason", ""),
                    category=clip.get("category", "highlight"),
                    confidence=float(clip.get("confidence", 0.7))
                )
                all_suggestions.append(suggestion)
                chunk_suggestions.append(suggestion)
                
                if verbose:
                    print(f"    - Entries {start_entry}-{end_entry} -> {suggestion.start_time} - {suggestion.end_time}")
                    
            except (KeyError, ValueError, TypeError) as e:
                if verbose:
                    print(f"  Skipping invalid clip: {e}")
        
        # Notify chunk complete
        if on_chunk_complete:
            on_chunk_complete(chunk_info, chunk_suggestions, result.get("summary", ""))
    
    # Merge overlapping suggestions
    if verbose:
        print(f"\nMerging {len(all_suggestions)} total suggestions...")
    
    merged = merge_clip_suggestions(all_suggestions)
    
    # Filter by confidence
    filtered = [c for c in merged if c.confidence >= min_confidence]
    
    if verbose:
        print(f"Final: {len(filtered)} clips (after merge and confidence filter)")
    
    return filtered


def output_for_clipper(clips: list[ClipSuggestion], output_path: Optional[str] = None) -> str:
    """
    Format clips as timestamps for clipper.py.
    Returns the formatted string and optionally writes to file.
    """
    lines = []
    for clip in clips:
        lines.append(f"{clip.start_time} --> {clip.end_time}")
    
    output = "\n".join(lines)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
    
    return output


def output_detailed_json(clips: list[ClipSuggestion], output_path: Optional[str] = None) -> str:
    """Output clips as detailed JSON with reasons and categories."""
    data = {
        "clips": [
            {
                "start_time": c.start_time,
                "end_time": c.end_time,
                "duration_seconds": c.end_seconds - c.start_seconds,
                "reason": c.reason,
                "category": c.category,
                "confidence": c.confidence
            }
            for c in clips
        ],
        "total_clips": len(clips)
    }
    
    output = json.dumps(data, indent=2)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
    
    return output


def run_clipper(video_path: str, clips: list[ClipSuggestion], output_dir: Optional[str] = None):
    """
    Directly clip the video using ffmpeg (bypass GUI).
    """
    if not clips:
        print("No clips to process.")
        return
    
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return
    
    # Create output directory
    if not output_dir:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        import time
        output_dir = os.path.join(os.path.dirname(video_path), f"{base_name}-clips-{int(time.time())}")
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nClipping to: {output_dir}")
    
    for i, clip in enumerate(clips, 1):
        start_ffmpeg = clip.start_time.replace(",", ".")
        duration = clip.end_seconds - clip.start_seconds
        
        # Create descriptive filename
        safe_reason = re.sub(r'[^\w\s-]', '', clip.reason[:30]).strip().replace(' ', '_')
        output_file = os.path.join(output_dir, f"clip-{i:03d}-{clip.category}-{safe_reason}.mp4")
        
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-ss", start_ffmpeg,
            "-i", video_path,
            "-t", f"{duration:.3f}",
            "-c", "copy",
            output_file
        ]
        
        print(f"  [{i}/{len(clips)}] {clip.start_time} --> {clip.end_time} ({clip.category})")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr}")
        else:
            print(f"    Created: {os.path.basename(output_file)}")
    
    print(f"\nDone! {len(clips)} clips saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze SRT subtitles with AI to find clip-worthy moments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see how many API queries will be made
  python srt_preprocessor.py video.srt --dry-run

  # Analyze SRT and output timestamps for clipper.py (uses OpenRouter by default)
  python srt_preprocessor.py video.srt --output clips.txt

  # Use a specific model via OpenRouter
  python srt_preprocessor.py video.srt --model openai/gpt-4o
  
  # Use local Ollama (free, no API key)
  python srt_preprocessor.py video.srt --provider ollama --model llama3.2

  # Analyze and immediately clip the video
  python srt_preprocessor.py video.srt --video video.mp4 --clip

  # Add context about the video
  python srt_preprocessor.py video.srt --context "Gaming stream of Elden Ring"

  # Output detailed JSON with reasons
  python srt_preprocessor.py video.srt --format json --output clips.json
"""
    )
    
    parser.add_argument("srt_file", help="Path to the SRT subtitle file")
    parser.add_argument("--video", "-v", help="Path to the video file (for clipping)")
    parser.add_argument("--output", "-o", help="Output file path for timestamps/JSON")
    parser.add_argument("--format", "-f", choices=["timestamps", "json"], default="timestamps",
                       help="Output format (default: timestamps)")
    parser.add_argument("--clip", "-c", action="store_true", 
                       help="Automatically clip the video (requires --video)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Show how many API queries would be made without executing them")
    parser.add_argument("--provider", "-p", choices=["openrouter", "openai", "anthropic", "ollama"], 
                       default="openrouter", help="AI provider (default: openrouter)")
    parser.add_argument("--api-key", "-k", help="API key (or set via .env file)")
    parser.add_argument("--model", "-m", help="Model name to use (default from .env or provider default)")
    parser.add_argument("--context", help="Additional context about the video content")
    parser.add_argument("--max-tokens", type=int, default=6000,
                       help="Max tokens per chunk (default: 6000)")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                       help="Minimum confidence threshold (default: 0.5)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    parser.add_argument("--stream", "-s", action="store_true", 
                       help="Use streaming API to show AI output in real-time (OpenRouter only)")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.srt_file):
        print(f"Error: SRT file not found: {args.srt_file}")
        sys.exit(1)
    
    if args.clip and not args.video:
        print("Error: --clip requires --video to be specified")
        sys.exit(1)
    
    if args.video and not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)
    
    # Run analysis
    try:
        clips = analyze_srt(
            srt_path=args.srt_file,
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
            video_context=args.context or "",
            max_tokens_per_chunk=args.max_tokens,
            min_confidence=args.min_confidence,
            verbose=not args.quiet,
            dry_run=args.dry_run,
            stream=args.stream and args.provider == "openrouter",
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Exit early if dry run
    if args.dry_run:
        sys.exit(0)
    
    if not clips:
        print("\nNo clip-worthy moments found.")
        sys.exit(0)
    
    # Output results
    print("\n" + "="*60)
    print("SUGGESTED CLIPS")
    print("="*60)
    
    for i, clip in enumerate(clips, 1):
        duration = clip.end_seconds - clip.start_seconds
        print(f"\n{i}. [{clip.category.upper()}] {clip.start_time} --> {clip.end_time} ({duration:.1f}s)")
        print(f"   Confidence: {clip.confidence:.0%}")
        print(f"   Reason: {clip.reason}")
    
    # Write output file
    if args.format == "json":
        output = output_detailed_json(clips, args.output)
    else:
        output = output_for_clipper(clips, args.output)
    
    if args.output:
        print(f"\nSaved to: {args.output}")
    else:
        print(f"\n--- Timestamps for clipper.py ---")
        print(output)
    
    # Auto-clip if requested
    if args.clip and args.video:
        run_clipper(args.video, clips)


if __name__ == "__main__":
    main()
