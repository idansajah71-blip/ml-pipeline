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


def send_training_notification_email(
    to_email: str,
    model_name: str,
    status: str,
    metrics: Optional[dict] = None,
    error: Optional[str] = None,
    experiment_id: Optional[str] = None,
) -> bool:
    """
    Send a user-facing training completion/failure email.

    Args:
        to_email: Recipient email address
        model_name: Name of the model that was trained
        status: 'completed' or 'failed'
        metrics: Training metrics dict (if completed)
        error: Error message (if failed)
        experiment_id: Experiment ID for linking

    Returns:
        True if sent successfully, False otherwise
    """
    if not settings.SMTP_HOST or not to_email:
        logger.debug(f"Training notification email skipped (no SMTP config): {model_name}")
        return False

    if status == "completed":
        subject = f"Training Selesai: {model_name}"
        color = "#28a745"
        metrics_text = ""
        if metrics:
            acc = metrics.get("accuracy", metrics.get("r2", metrics.get("f1", None)))
            if acc is not None:
                metrics_text = f"\nMetrik utama: {acc:.2%}" if isinstance(acc, float) and acc <= 1 else f"\nMetrik utama: {acc}"
            rmse = metrics.get("rmse")
            if rmse:
                metrics_text += f"\nRMSE: {rmse:.2f}"
        body = f"""Training model '{model_name}' telah selesai.

Status: Berhasil{metrics_text}

Buka ML Pipeline untuk melihat hasil lengkap.
"""
        detail_line = f"Model <strong>{model_name}</strong> telah selesai dilatih dan siap digunakan."
    else:
        subject = f"Training Gagal: {model_name}"
        color = "#dc3545"
        body = f"""Training model '{model_name}' gagal.

Error: {error or 'Unknown error'}

Silakan periksa log atau coba训练 ulang.
"""
        detail_line = f"Training model <strong>{model_name}</strong> gagal."

    link = f"/experiments" if not experiment_id else f"/experiments?id={experiment_id}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
        <div style="border-left: 4px solid {color}; padding: 12px 16px; margin-bottom: 20px;">
            <h2 style="margin:0; color:{color}; font-size: 18px;">{subject}</h2>
        </div>
        <p style="color: #333; font-size: 14px;">{detail_line}</p>
        {"<pre style='background:#f5f5f5; padding:12px; border-radius:6px; font-size:13px; white-space:pre-wrap;'>" + (error or '') + "</pre>" if status == "failed" else ""}
        <p style="color:#888; font-size: 12px; margin-top: 30px;">
            Email ini dikirim otomatis oleh ML Pipeline. Jangan membalas email ini.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[ML Pipeline] {subject}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        logger.info(f"Training notification email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.warning(f"Failed to send training notification email: {e}")
        return False
