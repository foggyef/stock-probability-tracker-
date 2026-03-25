"""
Macro market context fetcher.
Pulls VIX (fear index), market trend, sector performance, and interest rates.
High VIX = fearful market = higher risk on all picks.
No API key required.
"""

import logging
from typing import Dict

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Key macro tickers
VIX       = "^VIX"
SPY       = "SPY"    # S&P 500 ETF
QQQ       = "QQQ"    # NASDAQ ETF
TLT       = "TLT"    # 20yr Treasury (interest rate proxy)
DXY       = "DX-Y.NYB"  # US Dollar index

# Sector ETFs
SECTORS = {
    "Technology":    "XLK",
    "Financials":    "XLF",
    "Healthcare":    "XLV",
    "Energy":        "XLE",
    "Consumer":      "XLY",
    "Industrials":   "XLI",
    "Utilities":     "XLU",
    "Materials":     "XLB",
    "Real Estate":   "XLRE",
    "Staples":       "XLP",
    "Communication": "XLC",
}


def get_market_context() -> Dict:
    """
    Returns a snapshot of current macro conditions.
    Used to adjust signal confidence and risk ratings.
    """
    context = {
        "vix":              None,
        "vix_interpretation": None,
        "spy_trend":        None,   # bullish | bearish | neutral
        "spy_5d_return":    None,
        "market_regime":    "neutral",  # bull | bear | volatile | neutral
        "risk_multiplier":  1.0,    # applied to all risk ratings
        "sectors":          {},
        "market_score":     0.0,    # -1 (bad) to +1 (good) for going long
    }

    try:
        tickers = [VIX, SPY, QQQ, TLT] + list(SECTORS.values())
        data = yf.download(tickers, period="1mo", interval="1d",
                           auto_adjust=True, progress=False, threads=True)

        closes = data["Close"] if "Close" in data else data

        # VIX
        if VIX in closes.columns:
            vix = float(closes[VIX].iloc[-1])
            context["vix"] = round(vix, 2)
            if vix < 15:
                context["vix_interpretation"] = "Very Calm — low fear"
                context["risk_multiplier"]    = 0.8
                context["market_score"]       += 0.3
            elif vix < 20:
                context["vix_interpretation"] = "Calm"
                context["market_score"]       += 0.1
            elif vix < 30:
                context["vix_interpretation"] = "Elevated Fear"
                context["risk_multiplier"]    = 1.3
                context["market_score"]       -= 0.2
            else:
                context["vix_interpretation"] = "High Fear — volatile market"
                context["risk_multiplier"]    = 1.6
                context["market_score"]       -= 0.5

        # SPY trend
        if SPY in closes.columns:
            spy = closes[SPY].dropna()
            if len(spy) >= 6:
                ret_5d = float((spy.iloc[-1] / spy.iloc[-6] - 1) * 100)
                context["spy_5d_return"] = round(ret_5d, 2)
                if ret_5d > 1.5:
                    context["spy_trend"]   = "bullish"
                    context["market_score"] += 0.3
                elif ret_5d < -1.5:
                    context["spy_trend"]   = "bearish"
                    context["market_score"] -= 0.3
                else:
                    context["spy_trend"]   = "neutral"

        # Sector performance (5-day return)
        for sector, etf in SECTORS.items():
            if etf in closes.columns:
                s = closes[etf].dropna()
                if len(s) >= 6:
                    ret = float((s.iloc[-1] / s.iloc[-6] - 1) * 100)
                    context["sectors"][sector] = round(ret, 2)

        # Overall market regime
        score = context["market_score"]
        vix   = context["vix"] or 20
        if score > 0.3 and vix < 20:
            context["market_regime"] = "bull"
        elif score < -0.3 or vix > 30:
            context["market_regime"] = "bear"
        elif vix > 25:
            context["market_regime"] = "volatile"
        else:
            context["market_regime"] = "neutral"

        context["market_score"] = round(context["market_score"], 2)

    except Exception as e:
        logger.error(f"Macro context fetch failed: {e}")

    return context


def get_sector_for_ticker(ticker: str) -> str:
    """Returns the sector for a ticker using yfinance."""
    try:
        return yf.Ticker(ticker).info.get("sector", "Unknown")
    except Exception:
        return "Unknown"
