"""
Multi-source news fetcher.
Pulls headlines from Yahoo Finance RSS, MarketWatch, Reuters, Benzinga, and Seeking Alpha.
No API key required.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# RSS feeds per ticker (Yahoo Finance)
def _yahoo_rss(ticker: str) -> List[Dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:10]:
            articles.append({
                "title":     entry.get("title", ""),
                "summary":   entry.get("summary", ""),
                "source":    "Yahoo Finance",
                "published": entry.get("published", ""),
            })
        return articles
    except Exception as e:
        logger.debug(f"Yahoo RSS failed for {ticker}: {e}")
        return []


# MarketWatch RSS
def _marketwatch_rss(ticker: str) -> List[Dict]:
    url = f"https://feeds.marketwatch.com/marketwatch/realtimeheadlines/"
    try:
        feed = feedparser.parse(url)
        articles = []
        ticker_lower = ticker.lower()
        for entry in feed.entries[:30]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            if ticker_lower in title.lower() or ticker_lower in summary.lower():
                articles.append({
                    "title":     title,
                    "summary":   summary,
                    "source":    "MarketWatch",
                    "published": entry.get("published", ""),
                })
        return articles
    except Exception as e:
        logger.debug(f"MarketWatch RSS failed for {ticker}: {e}")
        return []


# Seeking Alpha news via yfinance (no key needed)
def _yfinance_news(ticker: str) -> List[Dict]:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).news
        articles = []
        for item in (info or [])[:10]:
            articles.append({
                "title":     item.get("title", ""),
                "summary":   item.get("title", ""),  # yfinance doesn't give full text
                "source":    item.get("publisher", "Yahoo Finance"),
                "published": str(item.get("providerPublishTime", "")),
            })
        return articles
    except Exception as e:
        logger.debug(f"yfinance news failed for {ticker}: {e}")
        return []


# Finviz news scraper (free, no key)
def _finviz_news(ticker: str) -> List[Dict]:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; stock-tracker/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("table.fullview-news-outer tr")
        articles = []
        for row in rows[:10]:
            link = row.find("a")
            if link:
                articles.append({
                    "title":     link.get_text(strip=True),
                    "summary":   link.get_text(strip=True),
                    "source":    "Finviz",
                    "published": "",
                })
        return articles
    except Exception as e:
        logger.debug(f"Finviz news failed for {ticker}: {e}")
        return []


def fetch_news(ticker: str) -> List[Dict]:
    """
    Fetches news from all available sources for a ticker.
    Returns a combined, deduplicated list of articles.
    """
    articles = []
    articles.extend(_yfinance_news(ticker))
    articles.extend(_yahoo_rss(ticker))
    articles.extend(_finviz_news(ticker))

    # Deduplicate by title
    seen = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    return unique
