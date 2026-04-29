import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_LINK_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0F1923;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0F1923;min-height:100vh;">
    <tr><td align="center" style="padding:60px 20px;">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#162030;border-radius:16px;overflow:hidden;border:1px solid #1E3048;">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1A3A5C 0%,#0F2A45 100%);padding:36px 40px 28px;text-align:center;">
            <div style="font-size:11px;font-weight:700;letter-spacing:3px;color:#4A9EDB;text-transform:uppercase;margin-bottom:10px;">Financial Daily</div>
            <div style="font-size:26px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">{date}</div>
            <div style="font-size:13px;color:#7FB3D3;margin-top:6px;">{weekday} &nbsp;·&nbsp; Newsletter listo a las {time}</div>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 32px;text-align:center;">
            <p style="margin:0 0 10px;font-size:15px;color:#A8BFD0;line-height:1.6;">
              Tu resumen diario de mercados está listo.<br>
              Haz clic para verlo en tu navegador.
            </p>
            <a href="{url}" style="display:inline-block;margin-top:24px;padding:16px 44px;background:linear-gradient(135deg,#2B7FC1,#1A5FA0);color:#FFFFFF;font-size:15px;font-weight:700;text-decoration:none;border-radius:10px;letter-spacing:0.3px;">
              Ver Newsletter &rarr;
            </a>
            <p style="margin:24px 0 0;font-size:11px;color:#4A6278;">
              También puedes copiar este enlace:<br>
              <span style="color:#4A9EDB;">{url}</span>
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#0F1923;padding:18px 40px;text-align:center;border-top:1px solid #1E3048;">
            <span style="font-size:10px;color:#2E4860;letter-spacing:1px;text-transform:uppercase;">Financial Daily Newsletter · Automatizado</span>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_link(
    page_url: str,
    recipients: list[str],
    sender: str,
    password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> bool:
    if not recipients:
        logger.error("No recipients configured")
        return False

    now     = datetime.now()
    subject = f"Financial Daily – {now.strftime('%d %b %Y')}"

    html = _LINK_EMAIL_TEMPLATE.format(
        date    = now.strftime("%d de %B de %Y"),
        weekday = now.strftime("%A"),
        time    = now.strftime("%H:%M"),
        url     = page_url,
    )
    plain = f"Tu newsletter diario está listo: {page_url}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    return _smtp_send(msg, sender, password, recipients, smtp_host, smtp_port)


def _smtp_send(msg, sender, password, recipients, smtp_host, smtp_port) -> bool:
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"Email sent to: {recipients}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check EMAIL_SENDER and EMAIL_PASSWORD")
        return False
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False
