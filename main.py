"""
Financial Daily Newsletter
Ejecutar directamente: python main.py
Programado:           python scheduler.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from collectors import finviz_collector, market_data, market_news, portfolio_ratings, portfolio_tracker, stock_analysis
from generators import newsletter
from sender import email_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "newsletter.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)


def validate_config() -> list[str]:
    errors = []
    if not config.FINVIZ_EMAIL:
        errors.append("FINVIZ_EMAIL no configurado")
    if not config.FINVIZ_PASSWORD:
        errors.append("FINVIZ_PASSWORD no configurado")
    if not config.EMAIL_SENDER:
        errors.append("EMAIL_SENDER no configurado")
    if not config.EMAIL_PASSWORD:
        errors.append("EMAIL_PASSWORD no configurado")
    if not config.EMAIL_RECIPIENTS:
        errors.append("EMAIL_RECIPIENTS no configurado")
    return errors


def run() -> bool:
    logger.info("=" * 60)
    logger.info(f"Financial Daily Newsletter — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 60)

    # Validate configuration
    errors = validate_config()
    if errors:
        for e in errors:
            logger.error(f"Config error: {e}")
        logger.error("Revisa el archivo .env y vuelve a intentarlo.")
        return False

    # 1. Collect market data (Yahoo Finance)
    logger.info("Recopilando datos de mercado (Yahoo Finance)...")
    market = market_data.collect()

    # 2. Collect Finviz Elite data
    logger.info("Recopilando datos de Finviz Elite...")
    finviz = finviz_collector.collect(config.FINVIZ_EMAIL, config.FINVIZ_PASSWORD)

    # 2b. Collect Yahoo Finance news (reliable fallback, no login required)
    logger.info("Recopilando noticias de Yahoo Finance...")
    yf_news = market_news.fetch()
    # Merge: Finviz news first (deduped by title), then Yahoo Finance
    finviz_titles = {n["title"] for n in finviz.get("news", [])}
    merged_news = finviz.get("news", []) + [n for n in yf_news if n["title"] not in finviz_titles]
    finviz["news"] = merged_news
    logger.info(f"Total noticias combinadas: {len(merged_news)}")

    # 3. Track portfolio positions (live prices)
    logger.info("Rastreando posiciones del portfolio...")
    portfolio = portfolio_tracker.track()

    # 4. Analyze stock ideas with yfinance fundamentals
    logger.info("Analizando ideas de inversión...")
    # Use Finviz screener tickers when available; always fallback to curated watchlist
    idea_tickers = finviz.get("stock_idea_tickers") or config.STOCK_WATCHLIST
    finviz["stock_ideas"] = stock_analysis.analyze(idea_tickers[:8])

    # 4b. Analyst ratings: Finviz first, yfinance as fallback
    if not finviz.get("analyst_ratings"):
        logger.info("Finviz ratings vacíos — usando yfinance upgrades/downgrades...")
        finviz["analyst_ratings"] = portfolio_ratings.fetch()

    # 4c. Compute portfolio movers (top gainers/losers from the user's own portfolio)
    all_positions = (
        portfolio.get("desarrollado", [])
        + portfolio.get("emergente", [])
        + portfolio.get("megatrend", [])
    )
    with_change = [p for p in all_positions if p.get("change_pct") is not None]
    with_change.sort(key=lambda x: x["change_pct"], reverse=True)
    finviz["portfolio_gainers"] = with_change[:5]
    finviz["portfolio_losers"]  = with_change[-5:][::-1] if len(with_change) >= 5 else []

    # 5. Render newsletter HTML
    logger.info("Generando HTML del newsletter...")
    html = newsletter.render(market=market, finviz=finviz, portfolio=portfolio)

    # Save local HTML copy for debugging
    output_path = Path(__file__).parent / "output_latest.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML guardado en: {output_path}")

    # 6. Send link email (newsletter is published to GitHub Pages by the workflow)
    page_url = "https://vvaldesp20.github.io/Newsletter-Financiero/"
    logger.info(f"Enviando link del newsletter a: {config.EMAIL_RECIPIENTS}")
    success = email_sender.send_link(
        page_url=page_url,
        recipients=config.EMAIL_RECIPIENTS,
        sender=config.EMAIL_SENDER,
        password=config.EMAIL_PASSWORD,
        smtp_host=config.EMAIL_SMTP_HOST,
        smtp_port=config.EMAIL_SMTP_PORT,
    )

    if success:
        logger.info("Newsletter enviado correctamente.")
    else:
        logger.error("Error al enviar el newsletter. Revisa el log para más detalles.")

    return success


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
