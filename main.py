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
from collectors import finviz_collector, market_data, portfolio_tracker, stock_analysis
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

    # 3. Track portfolio positions (live prices)
    logger.info("Rastreando posiciones del portfolio...")
    portfolio = portfolio_tracker.track()

    # 4. Analyze stock ideas with yfinance fundamentals
    logger.info("Analizando ideas de inversión...")
    finviz["stock_ideas"] = stock_analysis.analyze(finviz.get("stock_idea_tickers", []))

    # 5. Render newsletter HTML
    logger.info("Generando HTML del newsletter...")
    html = newsletter.render(market=market, finviz=finviz, portfolio=portfolio)

    # Save local HTML copy for debugging
    output_path = Path(__file__).parent / "output_latest.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML guardado en: {output_path}")

    # 6. Send email
    logger.info(f"Enviando newsletter a: {config.EMAIL_RECIPIENTS}")
    success = email_sender.send(
        html_content=html,
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
