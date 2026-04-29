"""
News collection via:
  1. Yahoo Finance RSS per portfolio ticker  (stable, no auth)
  2. Reuters RSS feeds                       (stable, no auth)
"""
import logging
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

# Priority tickers for portfolio news
_PRIORITY = [
    "AMZN", "MSFT", "META", "GOOGL", "SOXX", "IBIT",
    "MCHI", "ECH",  "COPX", "SLV",  "NU",   "ASML",
    "SPY",  "QQQ",  "NVDA",
]

# Macro / general market RSS feeds (no auth)
_MACRO_FEEDS = [
    ("Reuters Business",  "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets",   "https://feeds.reuters.com/reuters/markets"),
    ("MarketWatch",       "https://feeds.marketwatch.com/marketwatch/topstories/"),
]


def _parse_rss(xml_text: str, source_override: str = "") -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        channel = root.find("channel") or root
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            src   = source_override or (item.findtext("source") or "").strip()

            if not title:
                continue

            date_str, time_str = "", ""
            if pub:
                try:
                    dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
                    date_str = dt.strftime("%d %b")
                    time_str = dt.strftime("%H:%M")
                except Exception:
                    pass

            items.append({
                "title":  title,
                "url":    link,
                "source": src,
                "date":   date_str,
                "time":   time_str,
            })
    except Exception as e:
        logger.debug(f"RSS parse error: {e}")
    return items


def _fetch_ticker_news(ticker: str, max_items: int = 4) -> list[dict]:
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []
        items = _parse_rss(resp.text, source_override="Yahoo Finance")
        return items[:max_items]
    except Exception as e:
        logger.debug(f"ticker RSS [{ticker}]: {e}")
        return []


def _fetch_macro_feeds() -> list[dict]:
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


def fetch(max_portfolio: int = 60, max_macro: int = 40) -> list[dict]:
    """
    Returns combined news list (portfolio tickers first, then macro feeds).
    The classifier in newsletter.py splits them into sections.
    """
    seen   = set()
    result = []

    # 1. Per-ticker news (portfolio + priority)
    tickers = _PRIORITY + [t for t in config.PORTFOLIO_TICKERS if t not in _PRIORITY]
    for ticker in tickers:
        if len(result) >= max_portfolio:
            break
        for item in _fetch_ticker_news(ticker):
            if item["title"] not in seen:
                seen.add(item["title"])
                result.append(item)

    # 2. Macro / general feeds
    macro_count = 0
    for item in _fetch_macro_feeds():
        if macro_count >= max_macro:
            break
        if item["title"] not in seen:
            seen.add(item["title"])
            result.append(item)
            macro_count += 1

    logger.info(f"RSS news total: {len(result)} items")
    return result
