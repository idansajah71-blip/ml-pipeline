"""Webhook Notifier — Send notifications via webhook/Slack/Discord/Email."""
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    webhook_urls: list[str] = field(default_factory=list)
    slack_webhook: str = ""
    discord_webhook: str = ""
    email_config: dict = field(default_factory=dict)
    enabled: bool = True
    events: list[str] = field(default_factory=lambda: ["completed", "failed"])
    include_data: bool = False
    max_retries: int = 3

    def to_dict(self) -> dict:
        return {
            "webhook_count": len(self.webhook_urls),
            "has_slack": bool(self.slack_webhook),
            "has_discord": bool(self.discord_webhook),
            "has_email": bool(self.email_config),
            "enabled": self.enabled,
            "events": self.events,
        }


@dataclass
class NotificationResult:
    success: bool = True
    sent_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "sent_count": self.sent_count,
            "failed_count": self.failed_count,
            "errors": self.errors,
        }


class WebhookNotifier:

    def __init__(self):
        self._configs: Dict[str, NotificationConfig] = {}
        self._history: list[dict] = []

    def configure(self, name: str, config: NotificationConfig):
        self._configs[name] = config

    async def notify(self, event: str, data: dict, config_name: str = None) -> NotificationResult:
        result = NotificationResult()
        if config_name:
            config = self._configs.get(config_name)
            if not config:
                result.success = False
                result.errors.append(f"Config '{config_name}' not found")
                return result
            configs = [config]
        else:
            configs = list(self._configs.values())

        for config in configs:
            if not config.enabled:
                continue
            if event not in config.events:
                continue

            for url in config.webhook_urls:
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        payload = {
                            "event": event,
                            "timestamp": datetime.now().isoformat(),
                            "data": data if config.include_data else {
                                "status": data.get("status", ""),
                                "summary": data.get("summary", ""),
                                "url": data.get("url", ""),
                            },
                        }
                        resp = await client.post(url, json=payload)
                        if resp.status_code < 300:
                            result.sent_count += 1
                            result.results.append({"url": url, "status": "sent"})
                        else:
                            result.failed_count += 1
                            result.errors.append(f"{url}: HTTP {resp.status_code}")
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"{url}: {str(e)}")

            if config.slack_webhook:
                try:
                    await self._send_slack(config.slack_webhook, event, data)
                    result.sent_count += 1
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"Slack: {str(e)}")

            if config.discord_webhook:
                try:
                    await self._send_discord(config.discord_webhook, event, data)
                    result.sent_count += 1
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"Discord: {str(e)}")

        result.success = result.failed_count == 0
        self._history.append({
            "event": event, "timestamp": datetime.now().isoformat(),
            "result": result.to_dict(),
        })
        return result

    async def _send_slack(self, webhook_url: str, event: str, data: dict):
        color_map = {"completed": "good", "failed": "danger", "started": "#439FE0"}
        emoji_map = {"completed": "✅", "failed": "❌", "started": "🚀"}
        emoji = emoji_map.get(event, "📢")
        color = color_map.get(event, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} Scrape {event.title()}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*URL:*\n{data.get('url', 'N/A')[:100]}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{data.get('status', event)}"},
                    {"type": "mrkdwn", "text": f"*Rows:*\n{data.get('clean_row_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Quality:*\n{data.get('quality_score', 0)}%"},
                ]
            }
        ]

        payload = {"blocks": blocks}
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(webhook_url, json=payload)

    async def _send_discord(self, webhook_url: str, event: str, data: dict):
        color_map = {"completed": 0x00FF00, "failed": 0xFF0000, "started": 0x0099FF}
        emoji_map = {"completed": "✅", "failed": "❌", "started": "🚀"}
        emoji = emoji_map.get(event, "📢")
        color = color_map.get(event, 0x808080)

        embed = {
            "title": f"{emoji} Scrape {event.title()}",
            "color": color,
            "fields": [
                {"name": "URL", "value": data.get("url", "N/A")[:100], "inline": True},
                {"name": "Status", "value": data.get("status", event), "inline": True},
                {"name": "Rows", "value": str(data.get("clean_row_count", 0)), "inline": True},
                {"name": "Quality", "value": f"{data.get('quality_score', 0)}%", "inline": True},
            ],
            "timestamp": datetime.now().isoformat(),
        }

        payload = {"embeds": [embed]}
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(webhook_url, json=payload)

    async def send_email(self, config: dict, subject: str, body: str):
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = config.get("from", "")
            msg["To"] = config.get("to", "")
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            host = config.get("host", "")
            port = config.get("port", 587)
            user = config.get("user", "")
            password = config.get("password", "")
            
            if not host:
                logger.error("Email send failed: SMTP host not configured")
                return False
            
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if port != 25:
                    server.starttls()
                    server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
            return True
        except smtplib.SMTPConnectError as e:
            logger.error(f"Email send failed - connection error: {e}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Email send failed - authentication error: {e}")
            return False
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def get_history(self, limit: int = 20) -> list[dict]:
        return self._history[-limit:]
