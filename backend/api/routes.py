"""
FastAPI routes for the stock probability tracker.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from scheduler.morning_job import run_morning_briefing, load_latest_briefing, load_briefing_for_date

router = APIRouter()


@router.get("/briefing/today")
def get_today_briefing():
    """Returns today's morning briefing. Triggers a fresh scan if not yet generated."""
    briefing = load_latest_briefing()
    if not briefing:
        raise HTTPException(
            status_code=404,
            detail="Morning briefing not yet generated. Check back after 8:30am ET or trigger manually."
        )
    return briefing


@router.get("/briefing/{date}")
def get_briefing_by_date(date: str):
    """Returns the briefing for a specific date (YYYY-MM-DD)."""
    briefing = load_briefing_for_date(date)
    if not briefing:
        raise HTTPException(status_code=404, detail=f"No briefing found for {date}")
    return briefing


@router.post("/briefing/run")
def trigger_briefing(background_tasks: BackgroundTasks):
    """Manually triggers a fresh morning briefing scan (runs in background)."""
    background_tasks.add_task(run_morning_briefing)
    return {"status": "scan started", "message": "Morning briefing is being generated. Refresh /briefing/today in a few minutes."}


@router.get("/health")
def health():
    return {"status": "ok"}
