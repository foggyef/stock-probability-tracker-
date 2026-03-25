"""
Daily report model and storage.
Each day the pipeline writes a structured report that the site displays.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent
REPORTS_DIR.mkdir(exist_ok=True)


def get_report_path(target_date: str) -> Path:
    return REPORTS_DIR / f"{target_date}.json"


def load_report(target_date: str) -> Optional[dict]:
    path = get_report_path(target_date)
    if path.exists():
        return json.loads(path.read_text())
    return None


def load_latest_report() -> Optional[dict]:
    paths = sorted(REPORTS_DIR.glob("????-??-??.json"), reverse=True)
    if paths:
        return json.loads(paths[0].read_text())
    return None


def list_report_dates() -> list:
    paths = sorted(REPORTS_DIR.glob("????-??-??.json"), reverse=True)
    return [p.stem for p in paths[:30]]  # last 30 days


def save_report(report: dict) -> None:
    target_date = report.get("date", date.today().isoformat())
    path = get_report_path(target_date)
    path.write_text(json.dumps(report, indent=2))
    logger.info(f"Report saved: {path}")


def empty_report(target_date: str = None) -> dict:
    """Returns a blank report structure for the pipeline to fill in."""
    return {
        "date": target_date or date.today().isoformat(),
        "generated_at": datetime.now().isoformat(),
        "pipeline_run_count": 0,
        "team_reports": {
            "research": {
                "hypotheses_generated": 0,
                "hypotheses": [],
                "new_sources": [],
                "summary": None,
                "status": "pending"
            },
            "discovery": {
                "hypothesis_tested": None,
                "result": None,
                "gate_failed": None,
                "gate_passed_count": 0,
                "metrics": {},
                "summary": None,
                "status": "pending"
            },
            "deployment": {
                "action": None,
                "strategy_name": None,
                "win_rate": None,
                "sharpe": None,
                "reason": None,
                "summary": None,
                "status": "pending"
            }
        },
        "ceo_response": {
            "grade": None,
            "headline": None,
            "summary": None,
            "commendations": [],
            "criticisms": [],
            "directives_issued": [],
            "outlook": None,
            "heat": None  # "cold" | "warm" | "hot" — CEO mood
        },
        "stats": {
            "total_experiments_all_time": 0,
            "total_proven_strategies": 0,
            "active_strategy_name": None,
            "active_strategy_win_rate": None,
            "active_strategy_sharpe": None,
            "days_since_last_deployment": None
        }
    }
