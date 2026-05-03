# -*- coding: utf-8 -*-
"""
Zenith Bot — Database Connections
Supabase (permanen) + VPS PostgreSQL (cache rolling)
"""

import asyncpg
from supabase import create_client, Client
from loguru import logger
from app.config import settings

# =====================================================
# SUPABASE CLIENT (data permanen)
# =====================================================

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _supabase_client


# =====================================================
# VPS POSTGRESQL (cache rolling 2 hari)
# =====================================================

_vps_pool: asyncpg.Pool | None = None


async def get_vps_pool() -> asyncpg.Pool:
    global _vps_pool
    if _vps_pool is None:
        try:
            _vps_pool = await asyncpg.create_pool(
                host=settings.vps_db_host,
                port=settings.vps_db_port,
                database=settings.vps_db_name,
                user=settings.vps_db_user,
                password=settings.vps_db_pass,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("VPS PostgreSQL pool created")
        except Exception as e:
            logger.error(f"Failed to create VPS pool: {e}")
            raise
    return _vps_pool


async def close_vps_pool():
    global _vps_pool
    if _vps_pool:
        await _vps_pool.close()
        _vps_pool = None
        logger.info("VPS PostgreSQL pool closed")


async def vps_execute(query: str, *args):
    """Execute query di VPS PostgreSQL"""
    try:
        pool = await get_vps_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    except Exception as e:
        logger.error(f"VPS execute error: {e} | Query: {query}")
        raise


async def vps_fetch(query: str, *args) -> list:
    """Fetch rows dari VPS PostgreSQL"""
    try:
        pool = await get_vps_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
    except Exception as e:
        logger.error(f"VPS fetch error: {e} | Query: {query}")
        return []


async def vps_fetchrow(query: str, *args):
    """Fetch single row dari VPS PostgreSQL"""
    try:
        pool = await get_vps_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    except Exception as e:
        logger.error(f"VPS fetchrow error: {e} | Query: {query}")
        return None
