"""
Fundamental data fetcher.
Pulls analyst ratings, earnings surprises, short interest, and insider activity
directly from Yahoo Finance via yfinance — no API key required.
"""

import logging
from typing import Dict, Optional
from datetime import datetime

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


def get_analyst_data(ticker: str) -> Dict:
    """
    Returns analyst consensus, price targets, and recommendation trend.
    Source: Yahoo Finance (via yfinance)
    """
    result = {
        "recommendation":    None,   # strongBuy, buy, hold, underperform, sell
        "mean_target":       None,   # analyst mean price target
        "current_price":     None,
        "upside_pct":        None,   # % upside to mean target
        "num_analysts":      None,
        "score":             0.0,    # -1 (sell) to +1 (strong buy)
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info

        result["recommendation"] = info.get("recommendationKey")
        result["mean_target"]    = info.get("targetMeanPrice")
        result["current_price"]  = info.get("currentPrice") or info.get("regularMarketPrice")
        result["num_analysts"]   = info.get("numberOfAnalystOpinions")

        if result["mean_target"] and result["current_price"]:
            result["upside_pct"] = round(
                ((result["mean_target"] - result["current_price"]) / result["current_price"]) * 100, 1
            )

        # Convert recommendation to score
        rec_scores = {
            "strongBuy":    1.0,
            "buy":          0.6,
            "hold":         0.0,
            "underperform": -0.6,
            "sell":        -1.0,
        }
        result["score"] = rec_scores.get(result["recommendation"], 0.0)

        # Boost score based on upside to target
        if result["upside_pct"]:
            if result["upside_pct"] > 20:
                result["score"] = min(result["score"] + 0.2, 1.0)
            elif result["upside_pct"] < -10:
                result["score"] = max(result["score"] - 0.2, -1.0)

    except Exception as e:
        logger.debug(f"Analyst data failed for {ticker}: {e}")

    return result


def get_earnings_data(ticker: str) -> Dict:
    """
    Returns earnings surprise history and upcoming earnings date.
    A positive earnings surprise (beat) is a strong BUY signal.
    """
    result = {
        "next_earnings_date": None,
        "last_surprise_pct":  None,   # % beat or miss vs estimate
        "consecutive_beats":  0,
        "score":              0.0,    # -1 to +1
    }
    try:
        t = yf.Ticker(ticker)

        # Upcoming earnings
        cal = t.calendar
        if cal is not None and not cal.empty:
            if "Earnings Date" in cal.index:
                result["next_earnings_date"] = str(cal.loc["Earnings Date"].iloc[0])

        # Historical earnings surprises
        history = t.earnings_history
        if history is not None and not history.empty:
            history = history.sort_index(ascending=False)

            surprises = history.get("surprisePercent", pd.Series())
            if len(surprises) > 0:
                result["last_surprise_pct"] = round(float(surprises.iloc[0]) * 100, 1)

                # Count consecutive beats
                beats = 0
                for s in surprises:
                    if s > 0:
                        beats += 1
                    else:
                        break
                result["consecutive_beats"] = beats

                # Score based on recent performance
                avg_surprise = float(surprises.head(4).mean()) * 100
                if avg_surprise > 5:
                    result["score"] = 0.8
                elif avg_surprise > 0:
                    result["score"] = 0.4
                elif avg_surprise > -5:
                    result["score"] = -0.2
                else:
                    result["score"] = -0.8

    except Exception as e:
        logger.debug(f"Earnings data failed for {ticker}: {e}")

    return result


def get_insider_activity(ticker: str) -> Dict:
    """
    Returns recent insider trading activity.
    Insider buying is a strong signal — executives buying their own stock
    means they expect it to go up.
    """
    result = {
        "net_shares_bought": 0,
        "buy_transactions":  0,
        "sell_transactions": 0,
        "score":             0.0,   # -1 to +1
    }
    try:
        t = yf.Ticker(ticker)
        trades = t.insider_transactions

        if trades is None or trades.empty:
            return result

        # Filter to last 90 days
        trades = trades.copy()
        if "Start Date" in trades.columns:
            trades["Start Date"] = pd.to_datetime(trades["Start Date"], errors="coerce")
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
            trades = trades[trades["Start Date"] >= cutoff]

        if trades.empty:
            return result

        buys  = trades[trades.get("Transaction", pd.Series()).str.contains("Buy|Purchase", na=False, case=False)]
        sells = trades[trades.get("Transaction", pd.Series()).str.contains("Sell|Sale", na=False, case=False)]

        result["buy_transactions"]  = len(buys)
        result["sell_transactions"] = len(sells)

        buy_shares  = buys["Shares"].sum()  if "Shares" in buys.columns  else 0
        sell_shares = sells["Shares"].sum() if "Shares" in sells.columns else 0
        result["net_shares_bought"] = int(buy_shares - sell_shares)

        # Score: more buys than sells = positive signal
        total = result["buy_transactions"] + result["sell_transactions"]
        if total > 0:
            buy_ratio = result["buy_transactions"] / total
            result["score"] = round((buy_ratio - 0.5) * 2, 2)  # -1 to +1

    except Exception as e:
        logger.debug(f"Insider data failed for {ticker}: {e}")

    return result


def get_short_interest(ticker: str) -> Dict:
    """
    Returns short interest data.
    Very high short interest can mean squeeze potential (BUY) or justified pessimism (SELL).
    """
    result = {
        "short_ratio":   None,   # days to cover
        "short_pct_float": None, # % of float sold short
        "score":         0.0,
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info

        result["short_ratio"]      = info.get("shortRatio")
        result["short_pct_float"]  = info.get("shortPercentOfFloat")

        if result["short_pct_float"]:
            pct = result["short_pct_float"] * 100
            # High short interest (>15%) with rising price = squeeze potential
            if pct > 20:
                result["score"] = 0.3   # potential squeeze
            elif pct > 10:
                result["score"] = 0.1
            else:
                result["score"] = 0.0

    except Exception as e:
        logger.debug(f"Short interest failed for {ticker}: {e}")

    return result
