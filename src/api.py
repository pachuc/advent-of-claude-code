"""FastAPI application for the Race Against Claude web interface.

This module provides the REST API endpoints for the race functionality
and serves the static frontend files.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from src.race_manager import race_manager

# Get the directory where this file is located
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Race Against Claude",
    description="Race against Claude to solve Advent of Code puzzles",
    version="1.0.0"
)


# Request/Response models
class RaceStartRequest(BaseModel):
    year: int
    day: int
    aoc_session: str
    fast_mode: bool = False  # Use one-shot solver instead of multi-agent


class RaceStartResponse(BaseModel):
    success: bool
    puzzle_part1: Optional[str] = None
    puzzle_title: Optional[str] = None
    input_url: Optional[str] = None
    error: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    part: int
    answer: str


class SubmitAnswerResponse(BaseModel):
    success: bool
    correct: Optional[bool] = None
    message: Optional[str] = None
    hint: Optional[str] = None
    rate_limited: bool = False


class ConfigResponse(BaseModel):
    has_session: bool
    current_year: int


# API Endpoints

@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get configuration info including whether AOC_SESSION is set."""
    has_session = bool(os.getenv("AOC_SESSION"))
    current_year = datetime.now().year
    return ConfigResponse(has_session=has_session, current_year=current_year)


@app.post("/api/race/start", response_model=RaceStartResponse)
async def start_race(request: RaceStartRequest):
    """Start a new race against Claude."""
    try:
        # Use provided session or fall back to environment
        session = request.aoc_session or os.getenv("AOC_SESSION")
        if not session:
            raise HTTPException(status_code=400, detail="AOC session token required")

        # Determine solver strategy based on fast_mode
        strategy = "one-shot" if request.fast_mode else "default"

        result = race_manager.start_race(
            year=request.year,
            day=request.day,
            aoc_session=session,
            strategy=strategy
        )
        return RaceStartResponse(**result)

    except ValueError as e:
        return RaceStartResponse(success=False, error=str(e))
    except Exception as e:
        return RaceStartResponse(success=False, error=f"Failed to start race: {e}")


@app.get("/api/race/status")
async def get_race_status():
    """Get the current race status (poll this endpoint)."""
    return race_manager.get_status()


@app.get("/api/race/progress")
async def get_progress(cursor: int = 0):
    """Get progress updates since a cursor position."""
    return race_manager.get_progress_updates(cursor)


@app.post("/api/race/submit", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """Submit the user's answer for a part."""
    if request.part not in [1, 2]:
        raise HTTPException(status_code=400, detail="Part must be 1 or 2")

    result = race_manager.submit_user_answer(
        part=request.part,
        answer=request.answer
    )
    return SubmitAnswerResponse(**result)


@app.post("/api/race/reset")
async def reset_race():
    """Reset the race to idle state."""
    race_manager.reset()
    return {"success": True}


# Static file serving

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main index.html page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return HTMLResponse(
            content="<h1>Race Against Claude</h1><p>Frontend not found. Please ensure static/index.html exists.</p>",
            status_code=200
        )


# Mount static files directory (CSS, JS, etc.)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
