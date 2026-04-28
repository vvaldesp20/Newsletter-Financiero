import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send(
    html_content: str,
    recipients: list[str],
    sender: str,
    password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> bool:
    if not recipients:
        logger.error("No recipients configured")
        return False

    subject = f"Financial Daily – {datetime.now().strftime('%d %b %Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)

    plain_text = (
        "Este email requiere un cliente de correo compatible con HTML.\n"
        f"Newsletter generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"Newsletter sent to: {recipients}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check EMAIL_SENDER and EMAIL_PASSWORD")
        return False
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False
