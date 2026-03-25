"""
Backtesting engine.
Used by strategy-discovery-agent to validate strategies before deployment.

Walk-forward testing is the gold standard here:
- Train on period A, validate on period B (never touched during training)
- Roll forward and repeat
- A strategy must pass ALL validation gates before being written to the registry
"""

import json
import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.stats as stats
import yfinance as yf

logger = logging.getLogger(__name__)

STRATEGIES_DIR = Path(__file__).parent / "strategies"


@dataclass
class BacktestResult:
    win_rate: float
    total_trades: int
    avg_return_per_trade: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate_ci_lower: float   # 95% confidence interval lower bound
    by_year: Dict[str, float]
    by_sector: Dict[str, float]
    by_regime: Dict[str, float]
    passed_gates: List[str]
    failed_gate: Optional[str]

    @property
    def is_valid(self) -> bool:
        return self.failed_gate is None

    def to_dict(self) -> dict:
        return asdict(self)


def _simulate_trades(
    df: pd.DataFrame,
    signals: List[Dict],
    slippage: float = 0.001
) -> List[Dict]:
    """
    Simulates trade outcomes given a list of signals and OHLCV data.
    Target = 2x ATR above entry, Stop = 1x ATR below entry.
    Returns list of trade results.
    """
    trades = []
    close = df["Close"]

    for sig in signals:
        entry_date = sig.get("date")
        entry_price = sig.get("entry_price")
        target = sig.get("target_price")
        stop = sig.get("stop_loss")
        direction = sig.get("signal")

        if not all([entry_date, entry_price, target, stop]):
            continue

        # Apply slippage to entry
        if direction == "BUY":
            actual_entry = entry_price * (1 + slippage)
        else:
            actual_entry = entry_price * (1 - slippage)

        # Walk forward from entry date to find outcome
        try:
            future = close[close.index > pd.Timestamp(entry_date)].head(60)  # max 60 days
        except Exception:
            continue

        outcome = "open"
        exit_price = float(future.iloc[-1]) if len(future) > 0 else actual_entry

        for price in future:
            if direction == "BUY":
                if price >= target:
                    outcome = "win"
                    exit_price = target * (1 - slippage)
                    break
                elif price <= stop:
                    outcome = "loss"
                    exit_price = stop * (1 - slippage)
                    break
            else:  # SELL
                if price <= target:
                    outcome = "win"
                    exit_price = target * (1 + slippage)
                    break
                elif price >= stop:
                    outcome = "loss"
                    exit_price = stop * (1 + slippage)
                    break

        if direction == "BUY":
            pct_return = (exit_price - actual_entry) / actual_entry
        else:
            pct_return = (actual_entry - exit_price) / actual_entry

        trades.append({
            "ticker":    sig.get("ticker"),
            "date":      entry_date,
            "direction": direction,
            "outcome":   outcome,
            "return":    round(pct_return, 4),
            "sector":    sig.get("sector", "Unknown"),
        })

    return trades


def _compute_metrics(trades: List[Dict], spy_return: float = 0.0) -> BacktestResult:
    """Computes all performance metrics from a list of trade results."""
    if not trades:
        return BacktestResult(
            win_rate=0, total_trades=0, avg_return_per_trade=0,
            total_return=0, sharpe_ratio=0, max_drawdown=0, calmar_ratio=0,
            win_rate_ci_lower=0, by_year={}, by_sector={}, by_regime={},
            passed_gates=[], failed_gate="no_trades"
        )

    returns = [t["return"] for t in trades]
    wins    = sum(1 for t in trades if t["outcome"] == "win")
    n       = len(trades)

    win_rate     = wins / n
    avg_return   = float(np.mean(returns))
    total_return = float(np.prod([1 + r for r in returns]) - 1)

    # Sharpe (annualized, assuming ~252 trading days, avg hold ~5 days → ~50 trades/year)
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252 / max(len(returns), 1) * 50))
    else:
        sharpe = 0.0

    # Max drawdown
    equity = np.cumprod([1 + r for r in returns])
    peak   = np.maximum.accumulate(equity)
    dd     = (equity - peak) / peak
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0

    calmar = (total_return / max_dd) if max_dd > 0 else 0.0

    # 95% confidence interval for win rate (binomial)
    ci = stats.proportion_confint(wins, n, alpha=0.05, method="wilson")
    win_rate_ci_lower = float(ci[0])

    # Breakdown by year
    by_year = {}
    for t in trades:
        year = str(t["date"])[:4]
        by_year.setdefault(year, []).append(t["outcome"] == "win")
    by_year = {y: round(sum(v) / len(v), 3) for y, v in by_year.items()}

    # Breakdown by sector
    by_sector = {}
    for t in trades:
        s = t.get("sector", "Unknown")
        by_sector.setdefault(s, []).append(t["outcome"] == "win")
    by_sector = {s: round(sum(v) / len(v), 3) for s, v in by_sector.items()}

    # Gate evaluation
    passed_gates = []
    failed_gate  = None

    # Gate 1: Statistical significance
    if n >= 100 and win_rate_ci_lower > 0.50:
        passed_gates.append("Gate 1: Statistical Significance")
    else:
        failed_gate = f"Gate 1 failed: {n} trades, CI lower={win_rate_ci_lower:.3f}"

    # Gate 2: Profitability
    if failed_gate is None:
        if win_rate > 0.58 and avg_return > 0 and total_return > spy_return:
            passed_gates.append("Gate 2: Profitability")
        else:
            failed_gate = f"Gate 2 failed: win_rate={win_rate:.3f}, avg_return={avg_return:.4f}, total_return={total_return:.3f} vs SPY {spy_return:.3f}"

    # Gate 3: Risk-adjusted
    if failed_gate is None:
        if sharpe > 1.0 and max_dd < 0.20 and calmar > 0.5:
            passed_gates.append("Gate 3: Risk-Adjusted Returns")
        else:
            failed_gate = f"Gate 3 failed: sharpe={sharpe:.2f}, max_dd={max_dd:.3f}, calmar={calmar:.2f}"

    # Gate 5: Robustness (no single year below 50%)
    if failed_gate is None:
        if by_year and min(by_year.values()) >= 0.50:
            passed_gates.append("Gate 5: Year-over-year Robustness")
        else:
            worst_year = min(by_year, key=by_year.get) if by_year else "unknown"
            failed_gate = f"Gate 5 failed: worst year {worst_year} = {by_year.get(worst_year, 0):.3f} win rate"

    return BacktestResult(
        win_rate=round(win_rate, 4),
        total_trades=n,
        avg_return_per_trade=round(avg_return, 4),
        total_return=round(total_return, 4),
        sharpe_ratio=round(sharpe, 3),
        max_drawdown=round(max_dd, 4),
        calmar_ratio=round(calmar, 3),
        win_rate_ci_lower=round(win_rate_ci_lower, 4),
        by_year=by_year,
        by_sector=by_sector,
        by_regime={},
        passed_gates=passed_gates,
        failed_gate=failed_gate,
    )


def run_backtest(
    experiment: Dict,
    stock_data: Dict[str, pd.DataFrame],
    train: bool = True,
) -> BacktestResult:
    """
    Runs a full backtest for an experiment config.
    train=True uses train_period, train=False uses test_period (OOS).
    """
    period_key = "train_period" if train else "test_period"
    period     = experiment.get(period_key, "")

    logger.info(f"Running backtest: {experiment.get('experiment_id')} | {'IN-SAMPLE' if train else 'OUT-OF-SAMPLE'} | {period}")

    # Would generate signals here using the experiment's weights/filters
    # and then simulate trades — full implementation added by strategy-discovery-agent
    # This scaffold gives the agent the structure to work with
    raise NotImplementedError(
        "strategy-discovery-agent should implement the full signal generation "
        "loop here using the experiment weights and the stock_data provided."
    )


def log_experiment(experiment: Dict, in_sample: BacktestResult, oos: Optional[BacktestResult] = None) -> None:
    """Logs an experiment result to experiments_log.json."""
    log_path = STRATEGIES_DIR / "experiments_log.json"
    log = json.loads(log_path.read_text())

    entry = {
        "experiment_id":   experiment.get("experiment_id", str(uuid.uuid4())[:8]),
        "hypothesis":      experiment.get("hypothesis", ""),
        "timestamp":       datetime.now().isoformat(),
        "weights":         experiment.get("weights", {}),
        "filters":         experiment.get("filters", {}),
        "in_sample":       in_sample.to_dict(),
        "oos":             oos.to_dict() if oos else None,
        "overall_result":  "PASSED" if (oos and oos.is_valid) else "FAILED",
        "failure_reason":  (oos or in_sample).failed_gate,
    }

    log["experiments"].append(entry)
    log_path.write_text(json.dumps(log, indent=2))
    logger.info(f"Experiment logged: {entry['experiment_id']} — {entry['overall_result']}")


def submit_proven_strategy(experiment: Dict, in_sample: BacktestResult, oos: BacktestResult) -> bool:
    """
    Writes a fully validated strategy to the registry for deployment.
    Only call this after ALL 6 gates have passed.
    """
    if not oos.is_valid:
        logger.error("Cannot submit strategy — OOS validation failed")
        return False

    # Gate 4: OOS vs in-sample drift check
    drift = abs(in_sample.win_rate - oos.win_rate)
    if drift > 0.08:
        logger.error(f"Gate 4 failed: OOS drift too high ({drift:.3f})")
        return False

    # Gate 5 for OOS too
    if oos.sharpe_ratio < 0.7:
        logger.error(f"Gate 4 failed: OOS Sharpe too low ({oos.sharpe_ratio:.2f})")
        return False

    registry_path = STRATEGIES_DIR / "registry.json"
    registry = json.loads(registry_path.read_text())

    strategy = {
        "strategy_id":   str(uuid.uuid4()),
        "name":          experiment.get("name", experiment.get("experiment_id")),
        "status":        "proven",
        "hypothesis":    experiment.get("hypothesis", ""),
        "weights":       experiment.get("weights", {}),
        "filters":       experiment.get("filters", {}),
        "hold_time_config": experiment.get("hold_time_config", {}),
        "validation": {
            "train_period": experiment.get("train_period"),
            "oos_period":   experiment.get("test_period"),
            "in_sample":    in_sample.to_dict(),
            "out_of_sample": oos.to_dict(),
        },
        "created_at":    datetime.now().isoformat(),
        "created_by":    "strategy-discovery-agent",
    }

    registry["strategies"].append(strategy)
    registry["last_updated"] = strategy["created_at"]
    registry_path.write_text(json.dumps(registry, indent=2))

    logger.info(f"Strategy submitted to registry: {strategy['name']} (id={strategy['strategy_id']})")
    return True
