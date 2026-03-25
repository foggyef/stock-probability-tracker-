"""
Morning briefing job — multi-source edition.
Runs every weekday at 8:30am ET.

Data sources pulled every morning:
  1. Yahoo Finance      — OHLCV price data (all liquid US stocks)
  2. Yahoo Finance      — Analyst ratings, price targets, earnings, insider trades
  3. Finviz + RSS feeds — News headlines
  4. SEC EDGAR          — Official 8-K company announcements (direct from the SEC)
  5. VADER NLP          — Sentiment scoring on all text
  6. VIX + SPY + Sectors — Macro market context
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Optional

from data.fetcher import get_stock_universe, fetch_ohlcv, filter_by_liquidity, get_company_name
from data.news_fetcher import fetch_news
from data.sec_fetcher import get_company_announcements
from data.fundamentals import get_analyst_data, get_earnings_data, get_insider_activity
from data.macro import get_market_context
from signals.analyzer import run_full_scan
from signals.config import MIN_AVG_VOLUME, MAX_PICKS

logger = logging.getLogger(__name__)

BRIEFING_DIR = Path(__file__).parent.parent / "data" / "briefings"
BRIEFING_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_enrichment(ticker: str) -> tuple:
    """Fetches all non-price data for a single ticker. Run in thread pool."""
    try:
        news     = fetch_news(ticker)
        filings  = get_company_announcements(ticker)
        analyst  = get_analyst_data(ticker)
        earnings = get_earnings_data(ticker)
        insider  = get_insider_activity(ticker)
        return ticker, news, filings, analyst, earnings, insider
    except Exception as e:
        logger.debug(f"Enrichment failed for {ticker}: {e}")
        return ticker, [], [], {}, {}, {}


def run_morning_briefing() -> dict:
    today = date.today().isoformat()
    logger.info(f"═══ Morning briefing starting: {today} ═══")

    # ── Step 1: Get stock universe and price data ──────────────────────────
    tickers    = get_stock_universe()
    raw_data   = fetch_ohlcv(tickers, period="6mo", interval="1d")
    liquid     = filter_by_liquidity(raw_data, min_avg_volume=MIN_AVG_VOLUME)
    liquid_tickers = list(liquid.keys())
    logger.info(f"Liquid stocks to analyze: {len(liquid_tickers)}")

    # Company names
    companies = {t: get_company_name(t) for t in liquid_tickers}

    # ── Step 2: Macro context (one call for everything) ────────────────────
    logger.info("Fetching macro context (VIX, SPY, sectors)...")
    macro = get_market_context()
    logger.info(f"Market regime: {macro['market_regime']} | VIX: {macro['vix']} | SPY 5d: {macro.get('spy_5d_return')}%")

    # ── Step 3: Enrich each ticker in parallel ─────────────────────────────
    logger.info(f"Fetching news, SEC filings, and fundamentals for {len(liquid_tickers)} tickers...")

    all_news, all_filings, all_analyst, all_earnings, all_insider = {}, {}, {}, {}, {}

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_enrichment, t): t for t in liquid_tickers}
        for future in as_completed(futures):
            ticker, news, filings, analyst, earnings, insider = future.result()
            all_news[ticker]     = news
            all_filings[ticker]  = filings
            all_analyst[ticker]  = analyst
            all_earnings[ticker] = earnings
            all_insider[ticker]  = insider

    logger.info("Enrichment complete. Running signal analysis...")

    # ── Step 4: Run signal analysis ────────────────────────────────────────
    signals = run_full_scan(
        stock_data=liquid,
        companies=companies,
        all_news=all_news,
        all_filings=all_filings,
        all_analyst=all_analyst,
        all_earnings=all_earnings,
        all_insider=all_insider,
        macro_context=macro,
    )

    top_picks = signals[:MAX_PICKS]

    # ── Step 5: Save briefing ──────────────────────────────────────────────
    briefing = {
        "date": today,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "total_scanned": len(tickers),
        "liquid_scanned": len(liquid_tickers),
        "total_signals": len(signals),
        "macro": macro,
        "picks": top_picks,
        "summary": {
            "buy_count":  sum(1 for p in top_picks if p["signal"] == "BUY"),
            "sell_count": sum(1 for p in top_picks if p["signal"] == "SELL"),
            "high_risk":  sum(1 for p in top_picks if p["risk_level"] == "high"),
            "medium_risk":sum(1 for p in top_picks if p["risk_level"] == "medium"),
            "low_risk":   sum(1 for p in top_picks if p["risk_level"] == "low"),
        },
        "sources": [
            "Yahoo Finance (price data)",
            "Yahoo Finance (analyst ratings)",
            "Yahoo Finance (earnings history)",
            "Yahoo Finance (insider trades)",
            "Finviz (news headlines)",
            "RSS feeds (Yahoo Finance, MarketWatch)",
            "SEC EDGAR (official 8-K filings)",
            "VADER NLP (sentiment analysis)",
            "VIX / SPY / Sector ETFs (macro context)",
        ],
    }

    path = BRIEFING_DIR / f"{today}.json"
    path.write_text(json.dumps(briefing, indent=2))
    logger.info(f"═══ Briefing saved: {len(top_picks)} picks from {len(signals)} signals ═══")

    return briefing


def load_latest_briefing() -> Optional[dict]:
    today = date.today().isoformat()
    path  = BRIEFING_DIR / f"{today}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def load_briefing_for_date(target_date: str) -> Optional[dict]:
    path = BRIEFING_DIR / f"{target_date}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None
