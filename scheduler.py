"""
Programador diario del newsletter.
Ejecutar en background: python scheduler.py

El horario se configura con NEWSLETTER_TIME en el .env (formato HH:MM).
Por defecto: 07:30 hora local.
"""

import logging
import sys
import time

import schedule

import config
from main import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def job():
    logger.info("Iniciando envío programado del newsletter...")
    run()


def main():
    send_time = config.NEWSLETTER_TIME
    schedule.every().monday.at(send_time).do(job)
    schedule.every().tuesday.at(send_time).do(job)
    schedule.every().wednesday.at(send_time).do(job)
    schedule.every().thursday.at(send_time).do(job)
    schedule.every().friday.at(send_time).do(job)

    logger.info(f"Scheduler activo — newsletter de lunes a viernes a las {send_time}")
    logger.info("Presiona Ctrl+C para detener.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
