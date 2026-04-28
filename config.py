import os
from dotenv import load_dotenv

load_dotenv()

FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL", "")
FINVIZ_PASSWORD = os.getenv("FINVIZ_PASSWORD", "")

FRED_API_KEY = os.getenv("FRED_API_KEY", "")

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = [r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()]
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

NEWSLETTER_TIME = os.getenv("NEWSLETTER_TIME", "07:30")
