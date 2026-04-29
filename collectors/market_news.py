import logging
from datetime import datetime, timezone

import yfinance as yf

import config

logger = logging.getLogger(__name__)

# Priority tickers for news (most likely to yield relevant stories)
_PRIORITY = [
    "SPY", "QQQ", "AMZN", "MSFT", "META", "GOOGL",
    "SOXX", "IBIT", "MCHI", "ECH", "COPX", "SLV", "NU",
]


def fetch(max_per_ticker: int = 5, max_total: int = 80) -> list[dict]:
    """Fetch recent news from Yahoo Finance for portfolio tickers."""
    tickers = _PRIORITY + [t for t in config.PORTFOLIO_TICKERS if t not in _PRIORITY]
    seen = set()
    items = []

    for ticker in tickers:
        if len(items) >= max_total:
            break
        try:
            news = yf.Ticker(ticker).news or []
            count = 0
            for n in news:
                if count >= max_per_ticker:
                    break
                title = (n.get("title") or "").strip()
                if not title or title in seen:
                    continue
                seen.add(title)

                ts = n.get("providerPublishTime") or 0
                if ts:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    date_str = dt.strftime("%d %b")
                    time_str = dt.strftime("%H:%M")
                else:
                    date_str = ""
                    time_str = ""

                items.append({
                    "title":  title,
                    "url":    n.get("link", ""),
                    "source": n.get("publisher", ""),
                    "date":   date_str,
                    "time":   time_str,
                })
                count += 1
        except Exception as e:
            logger.debug(f"yfinance news [{ticker}]: {e}")

    logger.info(f"Yahoo Finance news: {len(items)} items fetched")
    return items
