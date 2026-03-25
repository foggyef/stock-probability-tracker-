"""
Sentiment analysis engine.
Uses VADER (financial-tuned lexicon) to score news articles and SEC filings.
No API key required — runs entirely locally.
"""

import logging
from typing import List, Dict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()

# Finance-specific word boosts (VADER allows custom lexicon additions)
FINANCE_LEXICON = {
    "beat":          2.0,
    "beats":         2.0,
    "exceeded":      2.0,
    "raised":        1.5,
    "upgraded":      2.0,
    "buyback":       1.5,
    "dividend":      1.2,
    "acquisition":   0.5,
    "merger":        0.5,
    "miss":         -2.0,
    "missed":       -2.0,
    "lowered":      -1.5,
    "downgraded":   -2.0,
    "recall":       -2.0,
    "lawsuit":      -1.5,
    "investigation":-2.0,
    "fraud":        -3.0,
    "bankruptcy":   -3.0,
    "layoffs":      -1.5,
    "restructuring":-1.0,
    "guidance":      0.5,
    "reaffirmed":    1.0,
    "withdrawn":    -1.5,
    "record":        1.5,
    "all-time":      1.5,
    "surge":         2.0,
    "soar":          2.0,
    "plunge":       -2.0,
    "crash":        -2.5,
    "slump":        -1.5,
}

_analyzer.lexicon.update(FINANCE_LEXICON)


def score_text(text: str) -> float:
    """
    Returns a sentiment score from -1.0 (very negative) to +1.0 (very positive).
    Uses VADER compound score.
    """
    if not text or not text.strip():
        return 0.0
    scores = _analyzer.polarity_scores(text)
    return round(scores["compound"], 3)


def score_articles(articles: List[Dict]) -> float:
    """
    Scores a list of news articles and returns a weighted average sentiment.
    Titles are weighted more than summaries.
    """
    if not articles:
        return 0.0

    scores = []
    for article in articles:
        title_score   = score_text(article.get("title", ""))
        summary_score = score_text(article.get("summary", ""))
        # Title has more impact (0.6/0.4 weighting)
        combined = (title_score * 0.6) + (summary_score * 0.4)
        scores.append(combined)

    if not scores:
        return 0.0

    avg = sum(scores) / len(scores)
    return round(avg, 3)


def score_filings(filings: List[Dict]) -> float:
    """
    Scores SEC filings. More recent filings get higher weight.
    """
    if not filings:
        return 0.0

    scores = []
    for i, filing in enumerate(filings):
        text = filing.get("text", "") or ""
        if not text:
            continue
        # More recent = higher weight (index 0 is most recent)
        weight = 1.0 / (i + 1)
        scores.append((score_text(text), weight))

    if not scores:
        return 0.0

    total_weight = sum(w for _, w in scores)
    weighted = sum(s * w for s, w in scores) / total_weight
    return round(weighted, 3)


def interpret(score: float) -> str:
    """Human-readable interpretation of a sentiment score."""
    if score >= 0.5:
        return "Very Positive"
    if score >= 0.2:
        return "Positive"
    if score >= -0.2:
        return "Neutral"
    if score >= -0.5:
        return "Negative"
    return "Very Negative"
