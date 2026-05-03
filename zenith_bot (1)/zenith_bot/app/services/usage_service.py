# -*- coding: utf-8 -*-
"""
Zenith Bot — Usage Limits Service
Tracking request/alert harian per user di VPS cache
"""

from datetime import date
from loguru import logger

from app.database import vps_execute, vps_fetchrow
from app.config import TIER_LIMITS


async def get_usage_today(user_id: str) -> dict:
    try:
        today = date.today()
        row = await vps_fetchrow(
            "SELECT request_count, alert_count FROM usage_limits WHERE user_id = $1 AND usage_date = $2",
            user_id, today
        )
        if row:
            return {"request_count": row["request_count"], "alert_count": row["alert_count"]}
        return {"request_count": 0, "alert_count": 0}
    except Exception as e:
        logger.error(f"get_usage_today error: {e}")
        return {"request_count": 0, "alert_count": 0}


async def increment_request(user_id: str) -> bool:
    try:
        today = date.today()
        await vps_execute("""
            INSERT INTO usage_limits (user_id, usage_date, request_count, alert_count)
            VALUES ($1, $2, 1, 0)
            ON CONFLICT (user_id, usage_date)
            DO UPDATE SET request_count = usage_limits.request_count + 1
        """, user_id, today)
        return True
    except Exception as e:
        logger.error(f"increment_request error: {e}")
        return False


async def increment_alert(user_id: str) -> bool:
    try:
        today = date.today()
        await vps_execute("""
            INSERT INTO usage_limits (user_id, usage_date, request_count, alert_count)
            VALUES ($1, $2, 0, 1)
            ON CONFLICT (user_id, usage_date)
            DO UPDATE SET alert_count = usage_limits.alert_count + 1
        """, user_id, today)
        return True
    except Exception as e:
        logger.error(f"increment_alert error: {e}")
        return False


async def check_request_limit(user_id: str, tier: str) -> bool:
    """Return True jika masih dalam batas"""
    if tier not in TIER_LIMITS:
        return False
    limit = TIER_LIMITS[tier]["request_per_day"]
    usage = await get_usage_today(user_id)
    return usage["request_count"] < limit


async def check_alert_limit(user_id: str, tier: str) -> bool:
    """Return True jika masih dalam batas"""
    if tier not in TIER_LIMITS:
        return False
    limit = TIER_LIMITS[tier]["alert_per_day"]
    usage = await get_usage_today(user_id)
    return usage["alert_count"] < limit
