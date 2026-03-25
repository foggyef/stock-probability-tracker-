"""
FastAPI entry point.
Starts the APScheduler morning briefing job on startup.
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Add backend root to path so imports resolve cleanly
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router
from scheduler.morning_job import run_morning_briefing
from signals.config import BRIEFING_HOUR, BRIEFING_MINUTE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stock Probability Tracker",
    description="Daily stock briefings with buy/sell signals, hold times, and risk ratings.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

scheduler = BackgroundScheduler(timezone="America/New_York")


@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        run_morning_briefing,
        CronTrigger(
            day_of_week="mon-fri",
            hour=BRIEFING_HOUR,
            minute=BRIEFING_MINUTE,
            timezone="America/New_York",
        ),
        id="morning_briefing",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — morning briefing runs weekdays at {BRIEFING_HOUR}:{BRIEFING_MINUTE:02d} ET")


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()
