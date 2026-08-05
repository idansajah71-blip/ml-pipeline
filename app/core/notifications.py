import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def send_alert_email(
    subject: str,
    body: str,
    to: Optional[str] = None,
    alert_type: str = "info",
) -> bool:
    """
    Send an alert email via SMTP.

    Args:
        subject: Email subject line
        body: Email body (plain text)
        to: Recipient email (defaults to ALERT_EMAIL_TO)
        alert_type: 'critical', 'warning', or 'info'

    Returns:
        True if sent successfully, False otherwise
    """
    to = to or settings.ALERT_EMAIL_TO

    if not settings.SMTP_HOST or not to:
        logger.debug(f"Alert email skipped (no SMTP config): {subject}")
        return False

    severity_colors = {"critical": "#dc3545", "warning": "#ffc107", "info": "#17a2b8"}
    color = severity_colors.get(alert_type, "#17a2b8")

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="border-left: 4px solid {color}; padding: 10px; margin-bottom: 10px;">
            <h2 style="margin:0; color:{color};">{subject}</h2>
        </div>
        <pre style="background:#f5f5f5; padding:15px; border-radius:4px;">{body}</pre>
        <p style="color:#888; font-size:12px;">ML Pipeline Alert System</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[ML Pipeline {alert_type.upper()}] {subject}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to, msg.as_string())
        logger.info(f"Alert email sent: {subject}")
        return True
    except Exception as e:
        logger.warning(f"Failed to send alert email: {e}")
        return False
