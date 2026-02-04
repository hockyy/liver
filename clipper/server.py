"""
FastAPI Web GUI for SRT Preprocessor
"""

import os
import re
import json
import asyncio
import queue
import threading
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from srt_preprocessor import (
    load_env_file,
    parse_srt,
    chunk_subtitles,
    estimate_tokens,
    seconds_to_time_str,
    time_str_to_seconds,
    format_chunk_for_ai,
    query_ai_openrouter_stream,
    merge_clip_suggestions,
    build_entry_mapping,
    ClipSuggestion,
    MergedEntry,
)

# Load environment variables
load_env_file()

# Setup paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"

# Create directories if they don't exist
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Initialize FastAPI
app = FastAPI(title="SRT Clip Preprocessor", description="AI-powered video clip finder")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    # Get default values from environment
    default_model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
    has_api_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "default_model": default_model,
        "has_api_key": has_api_key,
    })


@app.post("/upload")
async def upload_srt(file: UploadFile = File(...)):
    """Upload an SRT file and return basic info."""
    if not file.filename.endswith(('.srt', '.SRT')):
        raise HTTPException(status_code=400, detail="File must be an SRT file")
    
    # Save the uploaded file
    file_path = UPLOADS_DIR / file.filename
    content = await file.read()
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Parse and get basic info
    try:
        entries = parse_srt(str(file_path))
        if not entries:
            raise HTTPException(status_code=400, detail="No subtitle entries found in file")
        
        total_duration = entries[-1].end_seconds - entries[0].start_seconds
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "filepath": str(file_path),
            "entries_count": len(entries),
            "duration": seconds_to_time_str(total_duration),
            "duration_seconds": total_duration,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse SRT: {str(e)}")


@app.post("/dry-run")
async def dry_run(
    filepath: str = Form(...),
    provider: str = Form("openrouter"),
    model: str = Form(None),
    max_tokens: int = Form(6000),
):
    """Perform a dry run to show chunk breakdown."""
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    entries = parse_srt(filepath)
    if not entries:
        raise HTTPException(status_code=400, detail="No entries in SRT file")
    
    # This now returns merged entries
    chunks = chunk_subtitles(entries, max_tokens=max_tokens)
    
    # Count unique merged entries
    all_merged = []
    for chunk_entries, _, _ in chunks:
        for entry in chunk_entries:
            if entry not in all_merged:
                all_merged.append(entry)
    
    # Calculate stats with new compact format
    total_tokens = sum(
        sum(estimate_tokens(f"{e.merged_index} | {e.text}\n") for e in chunk_entries)
        for chunk_entries, _, _ in chunks
    )
    
    # Resolve model name
    if provider == "openrouter":
        display_model = model or os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-sonnet-4-20250514"
    elif provider == "openai":
        display_model = model or "gpt-4o"
    elif provider == "anthropic":
        display_model = model or "claude-sonnet-4-20250514"
    else:
        display_model = model or "llama3.2"
    
    # Build chunk details
    chunk_details = []
    for i, (chunk_entries, chunk_start, chunk_end) in enumerate(chunks):
        chunk_tokens = sum(estimate_tokens(f"{e.merged_index} | {e.text}\n") for e in chunk_entries)
        entry_range = f"{chunk_entries[0].merged_index}-{chunk_entries[-1].merged_index}"
        chunk_details.append({
            "index": i + 1,
            "start": seconds_to_time_str(chunk_start),
            "end": seconds_to_time_str(chunk_end),
            "tokens": chunk_tokens,
            "entries": len(chunk_entries),
            "entry_range": entry_range,
        })
    
    compression = len(entries) / len(all_merged) if all_merged else 1
    
    return JSONResponse({
        "provider": provider,
        "model": display_model,
        "total_chunks": len(chunks),
        "total_tokens": total_tokens,
        "api_queries": len(chunks),
        "original_entries": len(entries),
        "merged_entries": len(all_merged),
        "compression": round(compression, 1),
        "chunks": chunk_details,
    })


@app.get("/analyze-stream")
async def analyze_stream(
    filepath: str,
    provider: str = "openrouter",
    model: str = None,
    context: str = "",
    max_tokens: int = 6000,
    min_confidence: float = 0.5,
):
    """
    Run analysis with Server-Sent Events for real-time streaming.
    Processes chunks one by one and streams AI output.
    Uses compact entry-based format for efficiency.
    """
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Parse SRT and get chunks (now with merged entries)
    entries = parse_srt(filepath)
    if not entries:
        raise HTTPException(status_code=400, detail="No entries in SRT file")
    
    chunks = chunk_subtitles(entries, max_tokens=max_tokens)
    
    # Build global entry mapping for converting entry numbers back to timestamps
    all_merged_entries = []
    for chunk_entries, _, _ in chunks:
        for entry in chunk_entries:
            if entry not in all_merged_entries:
                all_merged_entries.append(entry)
    entry_mapping = build_entry_mapping(all_merged_entries)
    
    # Resolve model and API key
    if provider == "openrouter":
        display_model = model or os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-sonnet-4-20250514"
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured")
    else:
        raise HTTPException(status_code=400, detail="Streaming only supported for OpenRouter")
    
    async def event_generator():
        all_suggestions = []
        
        for i, (chunk_entries, chunk_start, chunk_end) in enumerate(chunks):
            entry_range = f"{chunk_entries[0].merged_index}-{chunk_entries[-1].merged_index}"
            chunk_info = {
                "index": i + 1,
                "total": len(chunks),
                "start": seconds_to_time_str(chunk_start),
                "end": seconds_to_time_str(chunk_end),
                "entry_range": entry_range,
            }
            
            # Send chunk start event
            yield f"event: chunk_start\ndata: {json.dumps(chunk_info)}\n\n"
            
            # Create a queue for tokens
            token_queue = queue.Queue()
            result_holder = [None]
            error_holder = [None]
            
            def on_token(token):
                token_queue.put(token)
            
            def run_query():
                try:
                    prompt = format_chunk_for_ai(chunk_entries, i, len(chunks), context)
                    result = query_ai_openrouter_stream(
                        prompt, api_key, display_model,
                        on_token=on_token,
                        verbose=True  # Also print to terminal
                    )
                    result_holder[0] = result
                except Exception as e:
                    error_holder[0] = e
                finally:
                    token_queue.put(None)  # Signal completion
            
            # Run the query in a background thread
            thread = threading.Thread(target=run_query)
            thread.start()
            
            # Stream tokens as they arrive
            while True:
                try:
                    token = token_queue.get(timeout=0.1)
                    if token is None:
                        break
                    # Send token event
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                except queue.Empty:
                    # Check if thread is still running
                    if not thread.is_alive():
                        break
                    await asyncio.sleep(0.05)
            
            thread.join()
            
            if error_holder[0]:
                yield f"event: error\ndata: {json.dumps({'error': str(error_holder[0])})}\n\n"
                continue
            
            result = result_holder[0]
            if not result:
                continue
            
            # Parse clips from this chunk (now using entry ranges)
            clips = result.get("clips", [])
            chunk_clips = []
            
            for clip in clips:
                try:
                    start_entry = int(clip["start_entry"])
                    end_entry = int(clip["end_entry"])
                    
                    # Look up the merged entries to get timestamps
                    if start_entry not in entry_mapping or end_entry not in entry_mapping:
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
                    chunk_clips.append({
                        "start_time": suggestion.start_time,
                        "end_time": suggestion.end_time,
                        "start_seconds": suggestion.start_seconds,
                        "end_seconds": suggestion.end_seconds,
                        "duration": round(suggestion.end_seconds - suggestion.start_seconds, 1),
                        "reason": suggestion.reason,
                        "category": suggestion.category,
                        "confidence": suggestion.confidence,
                        "entry_range": f"{start_entry}-{end_entry}",
                    })
                except (KeyError, ValueError, TypeError):
                    continue
            
            # Send chunk complete event
            chunk_complete = {
                "chunk": chunk_info,
                "clips": chunk_clips,
                "summary": result.get("summary", ""),
            }
            yield f"event: chunk_complete\ndata: {json.dumps(chunk_complete)}\n\n"
        
        # Merge all suggestions
        merged = merge_clip_suggestions(all_suggestions)
        filtered = [c for c in merged if c.confidence >= min_confidence]
        
        # Send final results
        final_clips = [
            {
                "start_time": c.start_time,
                "end_time": c.end_time,
                "start_seconds": c.start_seconds,
                "end_seconds": c.end_seconds,
                "duration": round(c.end_seconds - c.start_seconds, 1),
                "reason": c.reason,
                "category": c.category,
                "confidence": c.confidence,
            }
            for c in filtered
        ]
        
        timestamps = "\n".join(f"{c['start_time']} --> {c['end_time']}" for c in final_clips)
        
        final_result = {
            "success": True,
            "clips": final_clips,
            "total": len(final_clips),
            "timestamps": timestamps,
        }
        yield f"event: complete\ndata: {json.dumps(final_result)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/config")
async def get_config():
    """Get current configuration from environment."""
    return JSONResponse({
        "has_openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY")),
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY")),
        "has_anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "default_model": os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514"),
    })


if __name__ == "__main__":
    import uvicorn
    print("Starting SRT Preprocessor Web GUI...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
