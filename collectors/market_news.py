"""
News via RSS feeds:
  1. Yahoo Finance per-ticker RSS  (portfolio news)
  2. Reuters + MarketWatch RSS     (macro / general)
"""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

import config

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
_TIMEOUT = 10

_PRIORITY = [
    "AMZN", "MSFT", "META", "GOOGL", "SOXX", "IBIT",
    "MCHI", "ECH",  "COPX", "SLV",  "NU",   "ASML",
    "SPY",  "QQQ",  "NVDA",
]

_MACRO_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets",  "https://feeds.reuters.com/reuters/markets"),
    ("MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",     "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
]


# ── text helpers ──────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;",  "&", text)
    text = re.sub(r"&lt;",   "<", text)
    text = re.sub(r"&gt;",   ">", text)
    text = re.sub(r"&quot;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def _trim(text: str, max_sentences: int = 3) -> str:
    """Keep first max_sentences sentences, max ~300 chars."""
    if not text:
        return ""
    text = _strip_html(text)
    # Split on sentence-ending punctuation followed by a space
    parts = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(parts[:max_sentences])
    if len(summary) > 320:
        summary = summary[:317].rsplit(" ", 1)[0] + "…"
    return summary


def _parse_dt(pub: str) -> datetime | None:
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc)
    except Exception:
        return None


# ── RSS parsing ───────────────────────────────────────────────────────────────

def _parse_rss(xml_text: str, source_override: str = "") -> list[dict]:
    items = []
    try:
        root    = ET.fromstring(xml_text)
        channel = root.find("channel") or root
        for item in channel.findall("item"):
            title = _strip_html(item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            desc  = _trim(item.findtext("description") or "", max_sentences=3)
            src   = source_override or _strip_html(item.findtext("source") or "")

            if not title:
                continue

            dt       = _parse_dt(pub)
            date_str = dt.strftime("%d %b") if dt else ""
            time_str = dt.strftime("%H:%M") if dt else ""

            items.append({
                "title":   title,
                "summary": desc,
                "url":     link,
                "source":  src,
                "date":    date_str,
                "time":    time_str,
                "_dt":     dt,          # kept for sorting, not exposed to template
            })
    except Exception as e:
        logger.debug(f"RSS parse error: {e}")
    return items


# ── fetchers ──────────────────────────────────────────────────────────────────

def _fetch_ticker_rss(ticker: str, max_items: int = 5) -> list[dict]:
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []
        return _parse_rss(resp.text, source_override="Yahoo Finance")[:max_items]
    except Exception as e:
        logger.debug(f"ticker RSS [{ticker}]: {e}")
        return []


def _fetch_macro_rss() -> list[dict]:
    items = []
    for source, url in _MACRO_FEEDS:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if resp.status_code != 200:
                continue
            items.extend(_parse_rss(resp.text, source_override=source))
        except Exception as e:
            logger.debug(f"macro RSS [{source}]: {e}")
    return items


# ── public API ────────────────────────────────────────────────────────────────

def fetch(max_portfolio: int = 80, max_macro: int = 60) -> list[dict]:
    """
    Returns combined & deduplicated news sorted newest-first.
    Items include a 'summary' field (≤3 sentences).
    The classifier in newsletter.py splits them into portfolio / macro buckets.
    """
    seen   = set()
    result = []

    tickers = _PRIORITY + [t for t in config.PORTFOLIO_TICKERS if t not in _PRIORITY]
    for ticker in tickers:
        if len(result) >= max_portfolio:
            break
        for item in _fetch_ticker_rss(ticker):
            if item["title"] not in seen:
                seen.add(item["title"])
                result.append(item)

    macro_added = 0
    for item in _fetch_macro_rss():
        if macro_added >= max_macro:
            break
        if item["title"] not in seen:
            seen.add(item["title"])
            result.append(item)
            macro_added += 1

    # Sort newest-first (items without a date go to the end)
    result.sort(key=lambda x: x.get("_dt") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Strip internal sort key before handing to template
    for item in result:
        item.pop("_dt", None)

    logger.info(f"RSS news total: {len(result)} items")
    return result
