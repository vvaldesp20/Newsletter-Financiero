import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import config

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

MACRO_KEYWORDS = [
    "fed", "federal reserve", "interest rate", "inflation", "cpi", "pce",
    "gdp", "unemployment", "jobs report", "nonfarm", "powell", "ecb",
    "recession", "tariff", "trade war", "treasury", "yield curve", "fomc",
    "monetary policy", "fiscal", "rate hike", "rate cut", "bank of england",
    "bank of japan", "boj", "bce", "debt ceiling", "budget", "earnings season",
]


def _classify_news(news: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split news into portfolio-relevant and macro/general categories (10 each)."""
    tickers_lower = {t.lower() for t in config.PORTFOLIO_TICKERS}
    name_keywords = {
        "amazon", "microsoft", "alphabet", "google", "meta", "nvidia",
        "semiconductor", "copper", "bitcoin", "ethereum", "latam", "airlines",
        "chile", "china", "japan", "europe", "emerging", "s&p", "nasdaq",
        "silver", "nu holdings", "asml", "vanguard", "ishares", "etf",
    }

    portfolio_news, macro_news, other_news = [], [], []
    for item in news:
        combined = (item.get("title", "") + " " + item.get("source", "")).lower()

        if any(t in combined for t in tickers_lower) or any(kw in combined for kw in name_keywords):
            portfolio_news.append(item)
        elif any(kw in combined for kw in MACRO_KEYWORDS):
            macro_news.append(item)
        else:
            other_news.append(item)

    # Fill macro to 10 with general financial news if needed
    macro_news += other_news[:max(0, 10 - len(macro_news))]

    return portfolio_news[:10], macro_news[:10]


def _build_snapshot(us_markets: list[dict]) -> list[dict]:
    """Top 4 US indices for the header bar."""
    return [r for r in us_markets if r.get("price") != "-"][:5]


def render(
    market: dict,
    finviz: dict,
    portfolio: dict,
) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("newsletter.html")

    now = datetime.now()

    news_portfolio, news_macro = _classify_news(finviz.get("news", []))

    context = {
        "date":     now.strftime("%A, %d de %B de %Y"),
        "time":     now.strftime("%H:%M"),
        "snapshot": _build_snapshot(market.get("us_markets", [])),
        # Equity
        "us_markets":    market.get("us_markets", []),
        "eu_markets":    market.get("eu_markets", []),
        "latam_markets": market.get("latam_markets", []),
        # Fixed income
        "yields":      market.get("yields", []),
        "yield_curve": market.get("yield_curve"),
        "vix":         market.get("vix", {}),
        # FX & Commodities
        "fx_rates":    market.get("fx_rates", []),
        "commodities": market.get("commodities", []),
        # Sectors (yfinance ETFs)
        "sectors":         market.get("sectors", []),
        # Portfolio
        "portfolio_desarrollado": portfolio.get("desarrollado", []),
        "portfolio_emergente":    portfolio.get("emergente", []),
        "portfolio_megatrend":    portfolio.get("megatrend", []),
        # Movers (Finviz gainers/losers; fallback to portfolio movers)
        "gainers":            finviz.get("gainers", []),
        "losers":             finviz.get("losers", []),
        "portfolio_gainers":  finviz.get("portfolio_gainers", []),
        "portfolio_losers":   finviz.get("portfolio_losers", []),
        "analyst_ratings":    finviz.get("analyst_ratings", []),
        "news_portfolio":  news_portfolio,
        "news_macro":      news_macro,
        "calendar":        finviz.get("calendar", []),
        "stock_ideas":     finviz.get("stock_ideas", []),
    }

    html = template.render(**context)
    logger.info("Newsletter HTML rendered successfully")
    return html
