"""
Signal generation engine — multi-source version.

Score breakdown (total = 1.0 weight):
  40% — Technical analysis    (RSI, MACD, Bollinger, ADX, volume)
  20% — News sentiment        (Yahoo Finance, Finviz, RSS feeds)
  20% — SEC filings           (official 8-K announcements)
  10% — Analyst consensus     (ratings + price targets)
  10% — Fundamentals          (earnings surprises, insider buying)
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List

import numpy as np
import pandas as pd
import ta

from .config import HOLD_TIMES, RSI_OVERSOLD, RSI_OVERBOUGHT, VOLUME_MULTIPLIER
from .strategy_loader import get_weights, get_filters, get_hold_time_config, get_risk_thresholds

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    ticker: str
    company: str
    signal: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    probability_of_profit: float
    hold_type: str
    risk_level: str
    rationale: str
    # Source breakdown
    technical_score: float = 0.0
    news_sentiment:  float = 0.0
    sec_sentiment:   float = 0.0
    analyst_score:   float = 0.0
    fundamental_score: float = 0.0
    sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["hold_info"] = HOLD_TIMES[self.hold_type]
        d["potential_gain_pct"] = round(
            ((self.target_price - self.entry_price) / self.entry_price) * 100, 2
        )
        d["stop_loss_pct"] = round(
            abs((self.entry_price - self.stop_loss) / self.entry_price) * 100, 2
        )
        return d


def _classify_risk(atr: float, price: float) -> str:
    thresholds = get_risk_thresholds()
    ratio = atr / price
    for level, bounds in thresholds.items():
        low, high = bounds[0], bounds[1]
        if low <= ratio < high:
            return level
    return "high"


def _classify_hold_time(rsi: float, macd_hist: float, adx: float, atr_ratio: float) -> str:
    cfg = get_hold_time_config()
    if atr_ratio > cfg.get("day_trade_atr_threshold", 0.025) and abs(macd_hist) > 0.5:
        return "day_trade"
    if adx > cfg.get("swing_adx_threshold", 25) and abs(macd_hist) > 0.2:
        return "swing"
    if adx > cfg.get("short_term_adx_threshold", 20):
        return "short_term"
    return "long_term"


def _technical_score(df: pd.DataFrame) -> tuple:
    """Returns (score 0-1, direction BUY/SELL/None, reasons list, indicators dict)."""
    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

    macd_obj    = ta.trend.MACD(close)
    macd_line   = macd_obj.macd().iloc[-1]
    macd_signal = macd_obj.macd_signal().iloc[-1]
    macd_hist   = macd_obj.macd_diff().iloc[-1]

    bb          = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_pct      = bb.bollinger_pband().iloc[-1]

    atr         = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
    adx         = ta.trend.ADXIndicator(high, low, close, window=14).adx().iloc[-1]
    vol_ratio   = volume.iloc[-1] / volume.tail(20).mean()

    price       = float(close.iloc[-1])
    atr_ratio   = atr / price

    score     = 0.0
    reasons   = []
    direction = None

    if rsi < RSI_OVERSOLD:
        score += 0.25; reasons.append(f"RSI oversold ({rsi:.0f})"); direction = "BUY"
    elif rsi > RSI_OVERBOUGHT:
        score += 0.25; reasons.append(f"RSI overbought ({rsi:.0f})"); direction = "SELL"

    if macd_line > macd_signal and macd_hist > 0:
        score += 0.25; reasons.append("MACD bullish crossover")
        if direction is None: direction = "BUY"
    elif macd_line < macd_signal and macd_hist < 0:
        score += 0.25; reasons.append("MACD bearish crossover")
        if direction is None: direction = "SELL"

    if bb_pct < 0.1:
        score += 0.20; reasons.append("Near lower Bollinger Band")
        if direction is None: direction = "BUY"
    elif bb_pct > 0.9:
        score += 0.20; reasons.append("Near upper Bollinger Band")
        if direction is None: direction = "SELL"

    if vol_ratio >= VOLUME_MULTIPLIER:
        score += 0.15; reasons.append(f"Volume {vol_ratio:.1f}x above average")

    if adx > 25:
        score += 0.15; reasons.append(f"Strong trend (ADX {adx:.0f})")

    indicators = {
        "price": price, "atr": atr, "atr_ratio": atr_ratio,
        "rsi": rsi, "macd_hist": macd_hist, "adx": adx,
    }
    return score, direction, reasons, indicators


def analyze(
    ticker: str,
    company: str,
    df: pd.DataFrame,
    news_articles: Optional[List[Dict]] = None,
    sec_filings: Optional[List[Dict]] = None,
    analyst_data: Optional[Dict] = None,
    earnings_data: Optional[Dict] = None,
    insider_data: Optional[Dict] = None,
    macro_context: Optional[Dict] = None,
) -> Optional[Signal]:
    """
    Full multi-source analysis. Returns a Signal or None if below threshold.
    """
    if len(df) < 50:
        return None

    try:
        # ── 1. Technical (40%) ──────────────────────────────────────────────
        tech_score, direction, tech_reasons, indicators = _technical_score(df)
        if direction is None:
            return None

        price     = indicators["price"]
        atr       = indicators["atr"]
        atr_ratio = indicators["atr_ratio"]

        sources_used = ["Technical Analysis"]

        # ── 2. News Sentiment (20%) ──────────────────────────────────────────
        news_score_raw = 0.0
        if news_articles:
            from data.sentiment import score_articles
            raw = score_articles(news_articles)
            # Align with signal direction: positive news boosts BUY, hurts SELL
            news_score_raw = raw if direction == "BUY" else -raw
            sources_used.append(f"News ({len(news_articles)} articles)")

        # Normalize -1..+1 to 0..1
        news_contrib = (news_score_raw + 1) / 2

        # ── 3. SEC Filings (20%) ─────────────────────────────────────────────
        sec_score_raw = 0.0
        if sec_filings:
            from data.sentiment import score_filings
            raw = score_filings(sec_filings)
            sec_score_raw = raw if direction == "BUY" else -raw
            sources_used.append(f"SEC Filings ({len(sec_filings)} filings)")

        sec_contrib = (sec_score_raw + 1) / 2

        # ── 4. Analyst Consensus (10%) ──────────────────────────────────────
        analyst_contrib = 0.5  # neutral default
        analyst_score_raw = 0.0
        if analyst_data:
            analyst_score_raw = analyst_data.get("score", 0.0)
            if direction == "SELL":
                analyst_score_raw = -analyst_score_raw
            analyst_contrib = (analyst_score_raw + 1) / 2
            rec = analyst_data.get("recommendation")
            if rec:
                sources_used.append(f"Analyst: {rec}")

        # ── 5. Fundamentals (10%) ────────────────────────────────────────────
        fund_contrib = 0.5
        fund_score_raw = 0.0
        if earnings_data or insider_data:
            e_score = (earnings_data or {}).get("score", 0.0)
            i_score = (insider_data or {}).get("score", 0.0)
            fund_score_raw = (e_score + i_score) / 2
            if direction == "SELL":
                fund_score_raw = -fund_score_raw
            fund_contrib = (fund_score_raw + 1) / 2
            if earnings_data and earnings_data.get("consecutive_beats", 0) > 0:
                sources_used.append(f"{earnings_data['consecutive_beats']} consecutive earnings beats")
            if insider_data and insider_data.get("buy_transactions", 0) > 0:
                sources_used.append(f"Insider buying ({insider_data['buy_transactions']} buys)")

        # ── Weighted final score (weights loaded from active strategy) ──────
        tech_normalized = min(tech_score, 1.0)
        w = get_weights()

        confidence = (
            tech_normalized  * w.get("technical",    0.40) +
            news_contrib     * w.get("news",          0.20) +
            sec_contrib      * w.get("sec",           0.20) +
            analyst_contrib  * w.get("analyst",       0.10) +
            fund_contrib     * w.get("fundamentals",  0.10)
        )

        # Apply macro adjustment
        if macro_context:
            market_score = macro_context.get("market_score", 0.0)
            if direction == "BUY":
                confidence += market_score * 0.05
            else:
                confidence -= market_score * 0.05
            confidence = max(0.0, min(1.0, confidence))

        min_confidence = get_filters().get("min_confidence", 0.55)
        if confidence < min_confidence:
            return None

        # ── Price targets ────────────────────────────────────────────────────
        if direction == "BUY":
            target_price = round(price + (atr * 2.0), 2)
            stop_loss    = round(price - (atr * 1.0), 2)
        else:
            target_price = round(price - (atr * 2.0), 2)
            stop_loss    = round(price + (atr * 1.0), 2)

        # Historical win rate as probability proxy
        returns = df["Close"].pct_change().dropna()
        prob = float((returns > 0).sum() / len(returns)) if direction == "BUY" \
               else float((returns < 0).sum() / len(returns))
        prob = round(min(max(prob, 0.0), 1.0), 2)

        hold_type  = _classify_hold_time(
            indicators["rsi"], indicators["macd_hist"],
            indicators["adx"], atr_ratio
        )
        risk_level = _classify_risk(atr, price)

        # Boost risk if macro is volatile
        if macro_context and macro_context.get("market_regime") in ("bear", "volatile"):
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"

        # Build rationale from all sources
        all_reasons = tech_reasons[:2]
        if news_score_raw > 0.2:
            all_reasons.append("Positive news sentiment")
        elif news_score_raw < -0.2:
            all_reasons.append("Negative news sentiment")
        if sec_score_raw > 0.2:
            all_reasons.append("Positive company filings")
        if analyst_score_raw > 0.3:
            all_reasons.append(f"Analyst consensus: {analyst_data.get('recommendation', '')}")
        if fund_score_raw > 0.3:
            all_reasons.append("Strong earnings/insider activity")

        rationale = " · ".join(all_reasons[:4])

        return Signal(
            ticker=ticker,
            company=company,
            signal=direction,
            confidence=round(confidence, 3),
            entry_price=round(price, 2),
            target_price=target_price,
            stop_loss=stop_loss,
            probability_of_profit=prob,
            hold_type=hold_type,
            risk_level=risk_level,
            rationale=rationale,
            technical_score=round(tech_normalized, 3),
            news_sentiment=round(news_score_raw, 3),
            sec_sentiment=round(sec_score_raw, 3),
            analyst_score=round(analyst_score_raw, 3),
            fundamental_score=round(fund_score_raw, 3),
            sources_used=sources_used,
        )

    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {e}")
        return None


def run_full_scan(
    stock_data: Dict[str, pd.DataFrame],
    companies: Dict[str, str],
    all_news: Optional[Dict[str, List]] = None,
    all_filings: Optional[Dict[str, List]] = None,
    all_analyst: Optional[Dict[str, Dict]] = None,
    all_earnings: Optional[Dict[str, Dict]] = None,
    all_insider: Optional[Dict[str, Dict]] = None,
    macro_context: Optional[Dict] = None,
) -> List[Dict]:
    signals = []
    for ticker, df in stock_data.items():
        sig = analyze(
            ticker=ticker,
            company=companies.get(ticker, ticker),
            df=df,
            news_articles=(all_news or {}).get(ticker),
            sec_filings=(all_filings or {}).get(ticker),
            analyst_data=(all_analyst or {}).get(ticker),
            earnings_data=(all_earnings or {}).get(ticker),
            insider_data=(all_insider or {}).get(ticker),
            macro_context=macro_context,
        )
        if sig:
            signals.append(sig.to_dict())

    signals.sort(key=lambda s: s["confidence"], reverse=True)
    logger.info(f"Generated {len(signals)} signals from {len(stock_data)} stocks")
    return signals
