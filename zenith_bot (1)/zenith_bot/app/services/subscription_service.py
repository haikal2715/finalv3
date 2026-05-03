# -*- coding: utf-8 -*-
"""
Zenith Bot — Subscription Service
Manajemen subscription, tier, dan expiry
"""

from datetime import date, timedelta
from typing import Optional
from loguru import logger

from app.database import get_supabase
from app.config import TIER_LIMITS


async def get_active_subscription(user_id: str) -> Optional[dict]:
    try:
        sb = get_supabase()
        today = date.today().isoformat()
        result = (
            sb.table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "active")
            .gte("end_date", today)
            .order("end_date", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"get_active_subscription error: {e}")
        return None


async def get_user_tier(user_id: str) -> Optional[str]:
    sub = await get_active_subscription(user_id)
    if sub:
        return sub["tier"]
    return None


async def get_tier_limits(user_id: str) -> dict:
    tier = await get_user_tier(user_id)
    if tier and tier in TIER_LIMITS:
        return TIER_LIMITS[tier]
    return {}


async def activate_subscription(user_id: str, tier: str, days: int = 30) -> bool:
    try:
        sb = get_supabase()
        today = date.today()
        existing = await get_active_subscription(user_id)

        if existing and existing["tier"] == tier:
            # Perpanjang: tambah hari ke sisa
            current_end = date.fromisoformat(existing["end_date"])
            new_end = current_end + timedelta(days=days)
            sb.table("subscriptions").update({
                "end_date": new_end.isoformat()
            }).eq("id", existing["id"]).execute()
        else:
            # Plan baru atau ganti plan
            if existing:
                sb.table("subscriptions").update({"status": "cancelled"}).eq("id", existing["id"]).execute()
            new_end = today + timedelta(days=days)
            sb.table("subscriptions").insert({
                "user_id": user_id,
                "tier": tier,
                "start_date": today.isoformat(),
                "end_date": new_end.isoformat(),
                "status": "active",
            }).execute()

        logger.info(f"Subscription activated: user={user_id} tier={tier} days={days}")
        return True
    except Exception as e:
        logger.error(f"activate_subscription error: {e}")
        return False


async def get_days_remaining(user_id: str) -> int:
    sub = await get_active_subscription(user_id)
    if not sub:
        return 0
    end_date = date.fromisoformat(sub["end_date"])
    delta = end_date - date.today()
    return max(0, delta.days)


async def is_subscription_active(user_id: str) -> bool:
    sub = await get_active_subscription(user_id)
    return sub is not None


async def expire_old_subscriptions():
    """Jalankan via scheduler untuk update status expired"""
    try:
        sb = get_supabase()
        today = date.today().isoformat()
        sb.table("subscriptions").update({"status": "expired"}).lt("end_date", today).eq("status", "active").execute()
        logger.info("Expired subscriptions updated")
    except Exception as e:
        logger.error(f"expire_old_subscriptions error: {e}")
