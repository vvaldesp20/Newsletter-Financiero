import logging
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)

YIELD_TICKERS = [
    ("^IRX", "T-Bill 3M"),
    ("^FVX", "Treasury 5Y"),
    ("^TNX", "Treasury 10Y"),
    ("^TYX", "Treasury 30Y"),
]

US_INDICES = [
    ("^GSPC",    "S&P 500"),
    ("^IXIC",    "NASDAQ Composite"),
    ("^DJI",     "Dow Jones"),
    ("^RUT",     "Russell 2000"),
]

EU_INDICES = [
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^GDAXI",    "DAX (Alemania)"),
    ("^FTSE",     "FTSE 100 (UK)"),
    ("^FCHI",     "CAC 40 (Francia)"),
    ("^IBEX",     "IBEX 35 (España)"),
    ("FTSEMIB.MI","FTSE MIB (Italia)"),
]

LATAM_INDICES = [
    ("^BVSP",  "Bovespa (Brasil)"),
    ("^MXX",   "IPC (México)"),
    ("^MERV",  "Merval (Argentina)"),
    ("^IPSA",  "IPSA (Chile)"),
]

COMMODITIES = [
    ("GC=F",  "Oro",           "USD/oz"),
    ("SI=F",  "Plata",         "USD/oz"),
    ("CL=F",  "WTI Crude",     "USD/bbl"),
    ("BZ=F",  "Brent Crude",   "USD/bbl"),
    ("NG=F",  "Gas Natural",   "USD/MMBtu"),
    ("HG=F",  "Cobre",         "USD/lb"),
]

FX_PAIRS = [
    ("EURUSD=X", "EUR/USD"),
    ("GBPUSD=X", "GBP/USD"),
    ("JPY=X",    "USD/JPY"),
    ("CHF=X",    "USD/CHF"),
    ("DX-Y.NYB", "DXY (Índice Dólar)"),
    ("BRL=X",    "USD/BRL"),
    ("MXN=X",    "USD/MXN"),
    ("CLP=X",    "USD/CLP"),
]


def _fetch_quote(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d")
        if hist.empty or len(hist) < 2:
            return None
        close_today = hist["Close"].iloc[-1]
        close_prev  = hist["Close"].iloc[-2]
        change_pct  = ((close_today - close_prev) / close_prev) * 100
        return {
            "price":      close_today,
            "prev":       close_prev,
            "change_pct": round(change_pct, 2),
            "date":       hist.index[-1].strftime("%d %b"),
        }
    except Exception as e:
        logger.warning(f"yfinance error [{ticker}]: {e}")
        return None


def _ytd_change(ticker: str) -> float | None:
    try:
        t = yf.Ticker(ticker)
        start = f"{datetime.now().year}-01-01"
        hist = t.history(start=start)
        if len(hist) < 2:
            return None
        return round(((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100, 2)
    except Exception:
        return None


def _format_price(price: float, ticker: str) -> str:
    if price is None:
        return "-"
    if price >= 1000:
        return f"{price:,.0f}"
    if price >= 10:
        return f"{price:,.2f}"
    return f"{price:.4f}"


def _build_row(ticker: str, name: str, unit: str = "") -> dict:
    q = _fetch_quote(ticker)
    if q is None:
        return {"name": name, "ticker": ticker, "price": "-", "change_pct": None, "ytd": None, "unit": unit}
    ytd = _ytd_change(ticker)
    return {
        "name":       name,
        "ticker":     ticker,
        "price":      _format_price(q["price"], ticker),
        "change_pct": q["change_pct"],
        "ytd":        ytd,
        "unit":       unit,
        "date":       q["date"],
    }


def _fetch_yield(ticker: str, label: str) -> dict:
    try:
        closes = yf.Ticker(ticker).history(period="5d")["Close"].dropna()
        if len(closes) < 2:
            return {"name": label, "value": "-", "change": "-", "change_positive": None, "date": "-"}
        current = round(float(closes.iloc[-1]), 2)
        prev    = round(float(closes.iloc[-2]), 2)
        bps     = round((current - prev) * 100, 1)
        return {
            "name":            label,
            "value":           f"{current:.2f}%",
            "change":          f"{bps:+.0f} bps",
            "change_positive": bps <= 0,
            "date":            closes.index[-1].strftime("%d %b"),
        }
    except Exception as e:
        logger.warning(f"Yield fetch error [{ticker}]: {e}")
        return {"name": label, "value": "-", "change": "-", "change_positive": None, "date": "-"}


def _fetch_vix() -> dict:
    try:
        closes = yf.Ticker("^VIX").history(period="5d")["Close"].dropna()
        if len(closes) < 2:
            return {}
        current = round(float(closes.iloc[-1]), 1)
        chg     = round(current - float(closes.iloc[-2]), 2)
        return {
            "value":           f"{current:.1f}",
            "change":          f"{chg:+.2f}",
            "change_positive": chg <= 0,
            "date":            closes.index[-1].strftime("%d %b"),
        }
    except Exception as e:
        logger.warning(f"VIX fetch error: {e}")
        return {}


def collect() -> dict:
    logger.info("Collecting market data from Yahoo Finance...")

    us_markets    = [_build_row(t, n) for t, n in US_INDICES]
    eu_markets    = [_build_row(t, n) for t, n in EU_INDICES]
    latam_markets = [_build_row(t, n) for t, n in LATAM_INDICES]
    commodities   = [_build_row(t, n, u) for t, n, u in COMMODITIES]
    fx_rates      = [_build_row(t, n) for t, n in FX_PAIRS]
    yields        = [_fetch_yield(t, l) for t, l in YIELD_TICKERS]
    vix           = _fetch_vix()

    # Yield curve: 10Y minus 3M
    yield_curve = None
    try:
        tnx = yf.Ticker("^TNX").history(period="5d")["Close"].dropna()
        irx = yf.Ticker("^IRX").history(period="5d")["Close"].dropna()
        if not tnx.empty and not irx.empty:
            spread_bps = round((float(tnx.iloc[-1]) - float(irx.iloc[-1])) * 100)
            yield_curve = {"value": f"{spread_bps:+d} bps", "change_positive": spread_bps >= 0}
    except Exception as e:
        logger.warning(f"Yield curve calc error: {e}")

    logger.info("Market data collected.")
    return {
        "us_markets":    us_markets,
        "eu_markets":    eu_markets,
        "latam_markets": latam_markets,
        "commodities":   commodities,
        "fx_rates":      fx_rates,
        "yields":        yields,
        "vix":           vix,
        "yield_curve":   yield_curve,
    }
