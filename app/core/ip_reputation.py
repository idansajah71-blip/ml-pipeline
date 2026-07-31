import ipaddress
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


class IPReputationService:
    def __init__(self):
        self.RATE_LIMIT_THRESHOLD = 1000
        self.SUSPICIOUS_THRESHOLD = 100
        self.BLOCK_DURATION_HOURS = 24

        self.BLOCKED_RANGES = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        ]

    async def check_ip(self, ip_address: str) -> Dict:
        if await self._is_ip_blocked(ip_address):
            return {
                "allowed": False,
                "reason": "IP is blocked",
                "severity": "high",
            }

        if self._is_private_ip(ip_address):
            return {
                "allowed": True,
                "reason": "Private IP",
                "severity": "none",
            }

        threat_level = await self._assess_threat_level(ip_address)

        return {
            "allowed": threat_level != "critical",
            "reason": f"Threat level: {threat_level}",
            "severity": threat_level,
        }

    async def _is_ip_blocked(self, ip_address: str) -> bool:
        redis_client = await get_redis()
        if redis_client is None:
            return False

        try:
            block_time = await redis_client.get(f"ip_block:{ip_address}")
            if block_time:
                return True
            return False
        except Exception as e:
            logger.warning(f"Redis IP block check error: {e}")
            return False

    def _is_private_ip(self, ip_address: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private
        except ValueError:
            return False

    async def _assess_threat_level(self, ip_address: str) -> str:
        redis_client = await get_redis()
        if redis_client is None:
            return "none"

        try:
            suspicious_count = await redis_client.get(f"ip_suspicious:{ip_address}")
            count = int(suspicious_count) if suspicious_count else 0

            if count > self.SUSPICIOUS_THRESHOLD:
                return "critical"
            if count > 50:
                return "high"
            if count > 10:
                return "medium"
            if count > 0:
                return "low"
            return "none"
        except Exception as e:
            logger.warning(f"Redis threat assessment error: {e}")
            return "none"

    async def record_request(self, ip_address: str):
        redis_client = await get_redis()
        if redis_client is None:
            return

        try:
            key = f"ip_requests:{ip_address}"
            await redis_client.incr(key)
            await redis_client.expire(key, 3600)
        except Exception as e:
            logger.warning(f"Redis record_request error: {e}")

    async def record_suspicious_activity(self, ip_address: str, activity_type: str):
        redis_client = await get_redis()
        if redis_client is None:
            return

        try:
            key = f"ip_suspicious:{ip_address}"
            await redis_client.incr(key)
            await redis_client.expire(key, 86400)

            logger.warning(
                f"Suspicious activity recorded from {ip_address}",
                ip_address=ip_address,
                activity_type=activity_type,
            )

            count = await redis_client.get(key)
            if count and int(count) > self.SUSPICIOUS_THRESHOLD:
                await self.block_ip(ip_address, "Too many suspicious activities")
        except Exception as e:
            logger.warning(f"Redis record_suspicious error: {e}")

    async def block_ip(self, ip_address: str, reason: str):
        redis_client = await get_redis()
        if redis_client is None:
            return

        try:
            key = f"ip_block:{ip_address}"
            await redis_client.set(key, datetime.utcnow().isoformat(), ex=self.BLOCK_DURATION_HOURS * 3600)

            logger.warning(
                f"IP blocked: {ip_address}",
                ip_address=ip_address,
                reason=reason,
            )
        except Exception as e:
            logger.warning(f"Redis block_ip error: {e}")

    async def unblock_ip(self, ip_address: str) -> bool:
        redis_client = await get_redis()
        if redis_client is None:
            return False

        try:
            key = f"ip_block:{ip_address}"
            result = await redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis unblock_ip error: {e}")
            return False

    async def get_blocked_ips(self) -> List[Dict]:
        redis_client = await get_redis()
        if redis_client is None:
            return []

        try:
            blocked = []
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match="ip_block:*", count=100)
                for key in keys:
                    ip = key.replace("ip_block:", "")
                    block_time = await redis_client.get(key)
                    if block_time:
                        remaining = self.BLOCK_DURATION_HOURS - (datetime.utcnow() - datetime.fromisoformat(block_time)).total_seconds() / 3600
                        if remaining > 0:
                            blocked.append({
                                "ip": ip,
                                "blocked_at": block_time,
                                "remaining_hours": round(remaining, 2),
                            })
                if cursor == 0:
                    break
            return blocked
        except Exception as e:
            logger.warning(f"Redis get_blocked_ips error: {e}")
            return []

    async def get_ip_stats(self, ip_address: str) -> Dict:
        redis_client = await get_redis()
        if redis_client is None:
            return {
                "ip": ip_address,
                "total_requests": 0,
                "suspicious_activities": 0,
                "is_blocked": False,
                "threat_level": "none",
            }

        try:
            requests = await redis_client.get(f"ip_requests:{ip_address}")
            suspicious = await redis_client.get(f"ip_suspicious:{ip_address}")
            is_blocked = await self._is_ip_blocked(ip_address)

            return {
                "ip": ip_address,
                "total_requests": int(requests) if requests else 0,
                "suspicious_activities": int(suspicious) if suspicious else 0,
                "is_blocked": is_blocked,
                "threat_level": await self._assess_threat_level(ip_address),
            }
        except Exception as e:
            logger.warning(f"Redis get_ip_stats error: {e}")
            return {
                "ip": ip_address,
                "total_requests": 0,
                "suspicious_activities": 0,
                "is_blocked": False,
                "threat_level": "none",
            }


ip_reputation_service = IPReputationService()
