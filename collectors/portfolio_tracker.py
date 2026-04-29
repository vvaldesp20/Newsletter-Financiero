import logging
from datetime import datetime

import yfinance as yf

import config

logger = logging.getLogger(__name__)


def _fetch_quote(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = getattr(fi, "last_price", None)
        prev  = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)
        if price and prev and float(price) > 0 and float(prev) > 0:
            return {"price": float(price), "prev": float(prev)}
    except Exception:
        pass
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if len(hist) >= 2:
            return {"price": float(hist["Close"].iloc[-1]), "prev": float(hist["Close"].iloc[-2])}
    except Exception:
        pass
    return None


def _ytd(ticker: str) -> float | None:
    try:
        start = f"{datetime.now().year}-01-01"
        hist = yf.Ticker(ticker).history(start=start)
        if len(hist) >= 2:
            return round(((float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[0])) / float(hist["Close"].iloc[0])) * 100, 2)
    except Exception:
        pass
    return None


def _fmt(price: float) -> str:
    if price >= 1000:
        return f"{price:,.2f}"
    if price >= 10:
        return f"{price:.2f}"
    return f"{price:.4f}"


def _build_row(ticker: str, name: str) -> dict:
    q = _fetch_quote(ticker)
    if q is None:
        return {"ticker": ticker, "name": name, "price": "-", "change_pct": None, "ytd": None}
    price, prev = q["price"], q["prev"]
    chg = round(((price - prev) / prev) * 100, 2)
    ytd = _ytd(ticker)
    return {"ticker": ticker, "name": name, "price": _fmt(price), "change_pct": chg, "ytd": ytd}


def track() -> dict:
    """Returns portfolio positions grouped by category with live prices."""
    result = {}
    for category, holdings in config.PORTFOLIO.items():
        rows = []
        for ticker, name in holdings:
            row = _build_row(ticker, name)
            rows.append(row)
            logger.info(f"Portfolio [{category}] {ticker}: {row['price']} ({row['change_pct']}%)")
        result[category] = rows
    return result
