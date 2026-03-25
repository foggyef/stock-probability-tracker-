"""
SEC EDGAR fetcher.
Pulls official company filings directly from the SEC:
- 8-K  : Material events, earnings announcements, press releases
- 10-K : Annual report
- 10-Q : Quarterly report

No API key required — EDGAR is a public government database.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EDGAR_BASE     = "https://data.sec.gov"
EDGAR_SEARCH   = "https://efts.sec.gov/LATEST/search-index"
HEADERS        = {"User-Agent": "stock-probability-tracker contact@example.com"}

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CIK_CACHE_FILE = CACHE_DIR / "sec_cik_map.json"


def _load_cik_map() -> Dict[str, str]:
    """Downloads the full SEC ticker→CIK mapping (cached locally)."""
    if CIK_CACHE_FILE.exists():
        age_days = (datetime.now().timestamp() - CIK_CACHE_FILE.stat().st_mtime) / 86400
        if age_days < 7:
            return json.loads(CIK_CACHE_FILE.read_text())

    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=15
        )
        raw = resp.json()
        mapping = {
            v["ticker"].upper(): str(v["cik_str"]).zfill(10)
            for v in raw.values()
        }
        CIK_CACHE_FILE.write_text(json.dumps(mapping))
        logger.info(f"Loaded SEC CIK map: {len(mapping)} tickers")
        return mapping
    except Exception as e:
        logger.error(f"Failed to load SEC CIK map: {e}")
        return {}


_CIK_MAP: Dict[str, str] = {}


def get_cik(ticker: str) -> Optional[str]:
    global _CIK_MAP
    if not _CIK_MAP:
        _CIK_MAP = _load_cik_map()
    return _CIK_MAP.get(ticker.upper())


def fetch_recent_filings(ticker: str, form_types: List[str] = None, days_back: int = 30) -> List[Dict]:
    """
    Returns recent SEC filings for a ticker.
    form_types: e.g. ["8-K", "10-Q"] — defaults to ["8-K"]
    """
    if form_types is None:
        form_types = ["8-K"]

    cik = get_cik(ticker)
    if not cik:
        return []

    try:
        url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms       = filings.get("form", [])
        dates       = filings.get("filingDate", [])
        accessions  = filings.get("accessionNumber", [])
        descriptions = filings.get("primaryDocument", [])

        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        results = []
        for form, date, acc, doc in zip(forms, dates, accessions, descriptions):
            if form not in form_types:
                continue
            if date < cutoff:
                continue

            acc_clean = acc.replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}"

            results.append({
                "ticker":      ticker,
                "form":        form,
                "date":        date,
                "accession":   acc,
                "url":         filing_url,
                "text":        None,  # lazy loaded
            })

        return results[:5]  # most recent 5 filings

    except Exception as e:
        logger.debug(f"SEC filing fetch failed for {ticker}: {e}")
        return []


def fetch_filing_text(filing: Dict, max_chars: int = 3000) -> str:
    """
    Downloads and extracts plain text from an SEC filing URL.
    Limits to max_chars to keep things fast.
    """
    try:
        resp = requests.get(filing["url"], headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove script/style tags
        for tag in soup(["script", "style", "table"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = " ".join(text.split())
        return text[:max_chars]
    except Exception as e:
        logger.debug(f"Filing text fetch failed: {e}")
        return ""


def get_company_announcements(ticker: str) -> List[Dict]:
    """
    Main entry point. Returns recent 8-K filings with extracted text.
    These are official company announcements — earnings, deals, management changes, etc.
    """
    filings = fetch_recent_filings(ticker, form_types=["8-K"], days_back=45)
    for f in filings:
        f["text"] = fetch_filing_text(f)
        time.sleep(0.1)  # be polite to SEC servers
    return filings
