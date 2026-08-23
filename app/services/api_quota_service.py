from datetime import datetime, timezone, timedelta
from sqlalchemy import select


class APIQuotaService:
    def __init__(self, session):
        self.session = session

    TIER_LIMITS = {
        "free": {"rpm": 60, "daily": 10000, "monthly": 300000, "training_daily": 5, "training_monthly": 100},
        "starter": {"rpm": 300, "daily": 100000, "monthly": 3000000, "training_daily": 20, "training_monthly": 500},
        "pro": {"rpm": 1000, "daily": 500000, "monthly": 15000000, "training_daily": 100, "training_monthly": 3000},
        "enterprise": {"rpm": 5000, "daily": 5000000, "monthly": 150000000, "training_daily": 500, "training_monthly": 15000},
    }

    def _fallback_quota(self):
        """Return a free-tier usage dict when DB table is missing."""
        limits = self.TIER_LIMITS["free"]
        return {
            "tier": "free",
            "rpm": {"current": 0, "limit": limits["rpm"]},
            "daily": {"current": 0, "limit": limits["daily"]},
            "monthly": {"current": 0, "limit": limits["monthly"]},
            "training": {
                "daily": {"current": 0, "limit": limits["training_daily"]},
                "monthly": {"current": 0, "limit": limits["training_monthly"]},
            },
        }

    async def get_or_create_quota(self, user_id):
        from app.models.api_quota import APIQuota
        from sqlalchemy import select

        try:
            result = await self.session.execute(
                select(APIQuota).where(APIQuota.user_id == user_id)
            )
            quota = result.scalar_one_or_none()
        except Exception:
            await self.session.rollback()
            return self._fallback_quota()

        if not quota:
            try:
                quota = APIQuota(user_id=user_id, tier="free")
                self.session.add(quota)
                await self.session.flush()
            except Exception:
                await self.session.rollback()
                return self._fallback_quota()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
        from app.models.api_quota import APIQuota
        quota = await self.get_or_create_quota(user_id)
        limits = self.TIER_LIMITS.get(quota.tier, self.TIER_LIMITS["free"])

        if quota.current_rpm >= limits["rpm"]:
            return {"allowed": False, "reason": "RPM limit exceeded", "retry_after": 60}
        if quota.current_daily >= limits["daily"]:
            return {"allowed": False, "reason": "Daily limit exceeded", "retry_after": 3600}
        if quota.current_monthly >= limits["monthly"]:
            return {"allowed": False, "reason": "Monthly limit exceeded", "retry_after": 86400}

        rpm = quota.current_rpm + 1
        daily = quota.current_daily + 1
        monthly = quota.current_monthly + 1
        await self.session.execute(
            select(APIQuota).where(APIQuota.id == quota.id).with_for_update()
        )
        quota.current_rpm = rpm
        quota.current_daily = daily
        quota.current_monthly = monthly
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
        from app.models.experiment import Experiment
        from sqlalchemy import func

        quota = await self.get_or_create_quota(user_id)

        # Fallback when DB table is missing
        if isinstance(quota, dict):
            return quota

        limits = self.TIER_LIMITS.get(quota.tier, self.TIER_LIMITS["free"])

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        training_today = 0
        training_month = 0
        try:
            result = await self.session.execute(
                select(func.count(Experiment.id)).where(
                    Experiment.owner_id == user_id,
                    Experiment.created_at >= today_start,
                )
            )
            training_today = result.scalar() or 0

            result = await self.session.execute(
                select(func.count(Experiment.id)).where(
                    Experiment.owner_id == user_id,
                    Experiment.created_at >= month_start,
                )
            )
            training_month = result.scalar() or 0
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Quota training count failed: %s", exc)

        return {
            "tier": quota.tier,
            "rpm": {"current": quota.current_rpm, "limit": limits["rpm"]},
            "daily": {"current": quota.current_daily, "limit": limits["daily"]},
            "monthly": {"current": quota.current_monthly, "limit": limits["monthly"]},
            "training": {
                "daily": {"current": training_today, "limit": limits["training_daily"]},
                "monthly": {"current": training_month, "limit": limits["training_monthly"]},
            },
        }
