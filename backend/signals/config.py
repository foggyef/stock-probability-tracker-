"""
Signal generation configuration — tune thresholds here without touching logic.
"""

# Minimum confidence to include a pick in the morning briefing
MIN_CONFIDENCE = 0.55

# Risk classification thresholds (based on ATR as % of price)
RISK_THRESHOLDS = {
    "low":    (0.0, 0.015),   # ATR < 1.5% of price
    "medium": (0.015, 0.035), # ATR 1.5% - 3.5% of price
    "high":   (0.035, 999),   # ATR > 3.5% of price
}

# Hold time classification based on signal timeframe
HOLD_TIMES = {
    "day_trade":  {"label": "Day Trade",   "range": "Minutes – Hours",  "icon": "⚡"},
    "swing":      {"label": "Swing Trade", "range": "2 – 7 Days",       "icon": "📅"},
    "short_term": {"label": "Short Term",  "range": "1 – 4 Weeks",      "icon": "📆"},
    "long_term":  {"label": "Long Term",   "range": "1 – 3 Months",     "icon": "📈"},
}

# RSI thresholds
RSI_OVERSOLD  = 35
RSI_OVERBOUGHT = 65

# Volume confirmation — signal requires current volume > this multiple of 20d avg
VOLUME_MULTIPLIER = 1.3

# Minimum average daily volume to include a stock (liquidity filter)
MIN_AVG_VOLUME = 500_000

# Number of top picks to include in morning briefing
MAX_PICKS = 20

# Morning briefing schedule (ET)
BRIEFING_HOUR   = 8
BRIEFING_MINUTE = 30
