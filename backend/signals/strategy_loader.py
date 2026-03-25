"""
Strategy loader — reads the active strategy from strategy_state.json
and provides it to the signal analyzer at runtime.

This is how strategy-deployment-agent communicates with the live site:
it writes a new strategy_state.json, and the next morning scan
automatically picks up the new weights and filters.
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

STRATEGY_STATE_PATH = Path(__file__).parent / "strategy_state.json"
REGISTRY_PATH       = Path(__file__).parent / "strategies" / "registry.json"

_cached_state: Dict = {}


def load_active_strategy() -> Dict:
    """
    Loads the current active strategy config from strategy_state.json.
    Falls back to hardcoded defaults if the file is missing or corrupt.
    """
    global _cached_state
    try:
        state = json.loads(STRATEGY_STATE_PATH.read_text())
        _cached_state = state
        logger.info(f"Active strategy: {state['active_strategy_name']}")
        return state
    except Exception as e:
        logger.warning(f"Could not load strategy_state.json ({e}), using defaults")
        return _get_defaults()


def get_weights() -> Dict[str, float]:
    state = load_active_strategy()
    return state.get("weights", _get_defaults()["weights"])


def get_filters() -> Dict:
    state = load_active_strategy()
    return state.get("filters", _get_defaults()["filters"])


def get_hold_time_config() -> Dict:
    state = load_active_strategy()
    return state.get("hold_time_config", _get_defaults()["hold_time_config"])


def get_risk_thresholds() -> Dict:
    state = load_active_strategy()
    return state.get("risk_thresholds", _get_defaults()["risk_thresholds"])


def get_active_strategy_name() -> str:
    state = load_active_strategy()
    return state.get("active_strategy_name", "Default")


def record_trade_outcome(ticker: str, signal: str, hit_target: bool) -> None:
    """
    Records a live trade outcome for performance tracking.
    Called by the end-of-day monitoring job.
    """
    try:
        state = json.loads(STRATEGY_STATE_PATH.read_text())
        perf = state.setdefault("performance", {})
        tracked = perf.get("live_trades_tracked", 0)
        win_rate = perf.get("live_win_rate") or 0.0

        # Rolling win rate update
        new_tracked = tracked + 1
        new_win_rate = ((win_rate * tracked) + (1 if hit_target else 0)) / new_tracked

        perf["live_trades_tracked"]    = new_tracked
        perf["live_win_rate"]          = round(new_win_rate, 4)
        perf["last_performance_check"] = __import__("datetime").datetime.now().isoformat()

        STRATEGY_STATE_PATH.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logger.error(f"Failed to record trade outcome: {e}")


def deploy_strategy(strategy: Dict) -> bool:
    """
    Deploys a strategy from the registry to the live site.
    Called by strategy-deployment-agent.
    Returns True on success.
    """
    try:
        import datetime, uuid

        # Archive current state
        current = json.loads(STRATEGY_STATE_PATH.read_text())
        archive_path = Path(__file__).parent / "strategies" / f"archived_{current.get('active_strategy_id', 'unknown')}_{datetime.date.today()}.json"
        archive_path.write_text(json.dumps(current, indent=2))

        # Build new state from proven strategy
        new_state = {
            "active_strategy_id":   strategy["strategy_id"],
            "active_strategy_name": strategy["name"],
            "deployed_at":          datetime.datetime.now().isoformat(),
            "weights":              strategy["weights"],
            "filters":              strategy.get("filters", current.get("filters", {})),
            "hold_time_config":     strategy.get("hold_time_config", current.get("hold_time_config", {})),
            "risk_thresholds":      strategy.get("risk_thresholds", current.get("risk_thresholds", {})),
            "performance": {
                "backtested_win_rate":    strategy["validation"]["out_of_sample"]["win_rate"],
                "backtested_sharpe":      strategy["validation"]["out_of_sample"]["sharpe"],
                "live_win_rate":          None,
                "live_trades_tracked":    0,
                "last_performance_check": None,
            }
        }

        STRATEGY_STATE_PATH.write_text(json.dumps(new_state, indent=2))

        # Mark as deployed in registry
        registry = json.loads(REGISTRY_PATH.read_text())
        for s in registry["strategies"]:
            if s["strategy_id"] == strategy["strategy_id"]:
                s["status"] = "deployed"
                s["deployed_at"] = new_state["deployed_at"]
            elif s.get("status") == "deployed":
                s["status"] = "retired"
        registry["last_updated"] = new_state["deployed_at"]
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2))

        logger.info(f"Strategy deployed: {strategy['name']}")
        return True

    except Exception as e:
        logger.error(f"Strategy deployment failed: {e}")
        return False


def _get_defaults() -> Dict:
    return {
        "weights": {
            "technical": 0.40, "news": 0.20, "sec": 0.20,
            "analyst": 0.10, "fundamentals": 0.10
        },
        "filters": {
            "min_confidence": 0.55, "min_volume_ratio": 1.3,
            "rsi_oversold": 35, "rsi_overbought": 65
        },
        "hold_time_config": {
            "day_trade_atr_threshold": 0.025,
            "swing_adx_threshold": 25,
            "short_term_adx_threshold": 20
        },
        "risk_thresholds": {
            "low": [0.0, 0.015], "medium": [0.015, 0.035], "high": [0.035, 999]
        }
    }
