import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _build_snapshot(us_markets: list[dict]) -> list[dict]:
    """Top 4 US indices for the header bar."""
    return [r for r in us_markets if r.get("price") != "-"][:5]


def render(
    market: dict,
    finviz: dict,
) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("newsletter.html")

    now = datetime.now()

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
        # Finviz
        "sectors":         finviz.get("sectors", []),
        "gainers":         finviz.get("gainers", []),
        "losers":          finviz.get("losers", []),
        "analyst_ratings": finviz.get("analyst_ratings", []),
        "news":            finviz.get("news", []),
        "calendar":        finviz.get("calendar", []),
    }

    html = template.render(**context)
    logger.info("Newsletter HTML rendered successfully")
    return html
