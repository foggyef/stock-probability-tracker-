"""
FastAPI routes for the stock probability tracker.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from scheduler.morning_job import run_morning_briefing, load_latest_briefing, load_briefing_for_date
from reports.report_model import load_latest_report, load_report, list_report_dates

router = APIRouter()


# ── Morning Briefing ────────────────────────────────────────────────────────

@router.get("/briefing/today")
def get_today_briefing():
    briefing = load_latest_briefing()
    if not briefing:
        raise HTTPException(
            status_code=404,
            detail="Morning briefing not yet generated. Check back after 8:30am ET or trigger manually."
        )
    return briefing


@router.get("/briefing/{date}")
def get_briefing_by_date(date: str):
    briefing = load_briefing_for_date(date)
    if not briefing:
        raise HTTPException(status_code=404, detail=f"No briefing found for {date}")
    return briefing


@router.post("/briefing/run")
def trigger_briefing(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_morning_briefing)
    return {"status": "scan started", "message": "Morning briefing is being generated. Refresh in a few minutes."}


# ── CEO Reports ─────────────────────────────────────────────────────────────

@router.get("/reports/latest")
def get_latest_report():
    report = load_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No reports yet. The strategy team hasn't run yet.")
    return report


@router.get("/reports/dates")
def get_report_dates():
    return {"dates": list_report_dates()}


@router.get("/reports/{date}")
def get_report_by_date(date: str):
    report = load_report(date)
    if not report:
        raise HTTPException(status_code=404, detail=f"No report found for {date}")
    return report


# ── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}
