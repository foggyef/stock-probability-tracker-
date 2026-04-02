"""
FastAPI entry point.
Schedules:
  - Morning briefing: weekdays 8:30am ET
  - Intraday scan:    every 10 min, Mon-Fri 9:30am-4:00pm ET
  - Trade monitor:    every 10 min, Mon-Fri 9:30am-4:00pm ET
"""

import logging
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router
from scheduler.morning_job import run_morning_briefing
from scheduler.intraday_job import run_intraday_scan
from alerts.trade_tracker import check_open_trades
from signals.config import BRIEFING_HOUR, BRIEFING_MINUTE

REPO_DIR = Path(__file__).parent.parent


def git_pull():
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        if "Already up to date" not in result.stdout:
            logger.info(f"Git pull: {result.stdout.strip()}")
    except Exception as e:
        logger.warning(f"Git pull failed: {e}")

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

scheduler = BackgroundScheduler(timezone="America/New_York")


@app.on_event("startup")
def start_scheduler():
    # Morning briefing — 8:30am ET weekdays
    scheduler.add_job(
        run_morning_briefing,
        CronTrigger(day_of_week="mon-fri", hour=BRIEFING_HOUR,
                    minute=BRIEFING_MINUTE, timezone="America/New_York"),
        id="morning_briefing",
        replace_existing=True,
    )

    # Intraday scan — every 10 min during market hours (9:30am-4pm ET)
    scheduler.add_job(
        run_intraday_scan,
        CronTrigger(day_of_week="mon-fri", hour="9-15",
                    minute="*/10", timezone="America/New_York"),
        id="intraday_scan",
        replace_existing=True,
    )

    # Trade monitor — every 10 min during market hours
    scheduler.add_job(
        check_open_trades,
        CronTrigger(day_of_week="mon-fri", hour="9-15",
                    minute="*/10", timezone="America/New_York"),
        id="trade_monitor",
        replace_existing=True,
    )

    # Auto-pull from GitHub every 15 minutes
    scheduler.add_job(
        git_pull,
        IntervalTrigger(minutes=15),
        id="git_pull",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started:")
    logger.info(f"  Morning briefing  — weekdays {BRIEFING_HOUR}:{BRIEFING_MINUTE:02d} ET")
    logger.info(f"  Intraday scan     — every 10 min, 9:30am-4pm ET")
    logger.info(f"  Trade monitor     — every 10 min, 9:30am-4pm ET")


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()
