"""
Stock data fetching and universe management.
Uses yfinance for OHLCV data. Caches results locally as JSON.
"""

import json
import os
import time
import logging
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

UNIVERSE_CACHE = CACHE_DIR / "universe.json"
UNIVERSE_MAX_AGE_DAYS = 7


def get_stock_universe() -> list[str]:
    """
    Returns a list of liquid US stock tickers.
    Combines S&P 500 + NASDAQ 100. Refreshes weekly.
    """
    if UNIVERSE_CACHE.exists():
        age = (datetime.now().timestamp() - UNIVERSE_CACHE.stat().st_mtime) / 86400
        if age < UNIVERSE_MAX_AGE_DAYS:
            return json.loads(UNIVERSE_CACHE.read_text())

    tickers = set()

    # S&P 500
    try:
        sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        tickers.update(sp500["Symbol"].str.replace(".", "-").tolist())
        logger.info(f"Loaded {len(sp500)} S&P 500 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500: {e}")

    # NASDAQ 100
    try:
        nasdaq = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[4]
        tickers.update(nasdaq["Ticker"].tolist())
        logger.info(f"Loaded NASDAQ 100 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ 100: {e}")

    result = sorted(tickers)
    UNIVERSE_CACHE.write_text(json.dumps(result))
    logger.info(f"Stock universe: {len(result)} tickers")
    return result


def fetch_ohlcv(tickers: list[str], period: str = "6mo", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """
    Downloads OHLCV data for a list of tickers using yfinance batch download.
    Returns a dict of {ticker: DataFrame}.
    """
    results = {}

    # yfinance batch download — much faster than individual calls
    batch_size = 100
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            raw = yf.download(
                batch,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        df = raw.copy()
                    else:
                        df = raw[ticker].copy()

                    df.dropna(inplace=True)
                    if len(df) < 30:
                        continue

                    results[ticker] = df
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Batch download failed for batch {i}: {e}")

        time.sleep(0.5)  # be polite to yfinance

    logger.info(f"Fetched data for {len(results)}/{len(tickers)} tickers")
    return results


def filter_by_liquidity(data: dict[str, pd.DataFrame], min_avg_volume: int = 500_000) -> dict[str, pd.DataFrame]:
    """
    Removes tickers with insufficient average daily volume.
    """
    filtered = {
        ticker: df
        for ticker, df in data.items()
        if df["Volume"].tail(20).mean() >= min_avg_volume
    }
    logger.info(f"After liquidity filter: {len(filtered)} tickers (was {len(data)})")
    return filtered


def get_company_name(ticker: str) -> str:
    """Returns the company long name for a ticker, or the ticker itself on failure."""
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker
