from datetime import datetime, timedelta
from typing import Optional


class APIQuotaService:
    def __init__(self, session):
        self.session = session

    TIER_LIMITS = {
        "free": {"rpm": 60, "daily": 10000, "monthly": 300000},
        "starter": {"rpm": 300, "daily": 100000, "monthly": 3000000},
        "pro": {"rpm": 1000, "daily": 500000, "monthly": 15000000},
        "enterprise": {"rpm": 5000, "daily": 5000000, "monthly": 150000000},
    }

    async def get_or_create_quota(self, user_id):
        from app.models.api_quota import APIQuota
        from sqlalchemy import select

        result = await self.session.execute(
            select(APIQuota).where(APIQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()

        if not quota:
            quota = APIQuota(user_id=user_id, tier="free")
            self.session.add(quota)
            await self.session.flush()

        now = datetime.utcnow()
        if quota.rpm_reset_at and quota.rpm_reset_at < now:
            quota.current_rpm = 0
            quota.rpm_reset_at = now + timedelta(minutes=1)
        elif not quota.rpm_reset_at:
            quota.rpm_reset_at = now + timedelta(minutes=1)

        if quota.daily_reset_at and quota.daily_reset_at < now:
            quota.current_daily = 0
            quota.daily_reset_at = now + timedelta(days=1)
        elif not quota.daily_reset_at:
            quota.daily_reset_at = now + timedelta(days=1)

        if quota.monthly_reset_at and quota.monthly_reset_at < now:
            quota.current_monthly = 0
            quota.monthly_reset_at = now + timedelta(days=30)
        elif not quota.monthly_reset_at:
            quota.monthly_reset_at = now + timedelta(days=30)

        await self.session.flush()
        return quota

    async def check_and_increment(self, user_id) -> dict:
        quota = await self.get_or_create_quota(user_id)
        limits = self.TIER_LIMITS.get(quota.tier, self.TIER_LIMITS["free"])

        if quota.current_rpm >= limits["rpm"]:
            return {"allowed": False, "reason": "RPM limit exceeded", "retry_after": 60}
        if quota.current_daily >= limits["daily"]:
            return {"allowed": False, "reason": "Daily limit exceeded", "retry_after": 3600}
        if quota.current_monthly >= limits["monthly"]:
            return {"allowed": False, "reason": "Monthly limit exceeded", "retry_after": 86400}

        quota.current_rpm += 1
        quota.current_daily += 1
        quota.current_monthly += 1
        await self.session.flush()

        return {
            "allowed": True,
            "rpm_remaining": limits["rpm"] - quota.current_rpm,
            "daily_remaining": limits["daily"] - quota.current_daily,
            "monthly_remaining": limits["monthly"] - quota.current_monthly,
        }

    async def set_tier(self, user_id, tier: str):
        from app.models.api_quota import APIQuota
        from sqlalchemy import select

        if tier not in self.TIER_LIMITS:
            return {"error": f"Invalid tier: {tier}"}

        result = await self.session.execute(
            select(APIQuota).where(APIQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()
        if not quota:
            quota = APIQuota(user_id=user_id, tier=tier)
            self.session.add(quota)
        else:
            quota.tier = tier

        await self.session.flush()
        limits = self.TIER_LIMITS[tier]
        return {"tier": tier, "limits": limits}

    async def get_usage(self, user_id):
        quota = await self.get_or_create_quota(user_id)
        limits = self.TIER_LIMITS.get(quota.tier, self.TIER_LIMITS["free"])
        return {
            "tier": quota.tier,
            "rpm": {"current": quota.current_rpm, "limit": limits["rpm"]},
            "daily": {"current": quota.current_daily, "limit": limits["daily"]},
            "monthly": {"current": quota.current_monthly, "limit": limits["monthly"]},
        }
