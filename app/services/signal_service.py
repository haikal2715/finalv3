# -*- coding: utf-8 -*-
"""
Zenith Bot — Signal Service
Analisa cache management + signal generation pipeline
"""

from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from app.database import vps_execute, vps_fetch, vps_fetchrow, get_supabase
from app.services.hermes_service import hermes_analyze_stock, hermes_chat
from app.services.market_service import fetch_ohlcv, get_latest_ohlcv, calculate_indicators, generate_chart
from app.services.news_service import get_market_news_context


async def get_cached_analisa(ticker: str) -> Optional[dict]:
    """Ambil analisa dari cache VPS jika masih valid"""
    try:
        row = await vps_fetchrow("""
            SELECT * FROM analisa_cache
            WHERE saham = $1 AND expired_at > NOW()
            ORDER BY created_at DESC LIMIT 1
        """, ticker.upper())
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"get_cached_analisa error: {e}")
        return None


async def save_analisa_cache(ticker: str, result: dict, chart_path: str = None):
    """Simpan hasil analisa ke cache VPS (TTL 2 hari)"""
    try:
        expired_at = datetime.utcnow() + timedelta(days=2)
        await vps_execute("""
            INSERT INTO analisa_cache (saham, fase, entry, tp, sl, reason, chart_path, expired_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            ticker.upper(),
            result.get("fase"),
            result.get("entry"),
            result.get("tp"),
            result.get("sl"),
            result.get("alasan"),
            chart_path,
            expired_at,
        )
    except Exception as e:
        logger.error(f"save_analisa_cache error: {e}")


async def run_full_analysis(
    ticker: str,
    tier: str = "silver",
    skill_context: str = "",
    admin_context: str = "",
    force_refresh: bool = False,
) -> Optional[dict]:
    """
    Pipeline analisa lengkap:
    1. Cek cache
    2. Fetch data
    3. Hitung indikator
    4. Fetch berita
    5. Hermes analisa
    6. Simpan cache
    7. Return result
    """
    ticker = ticker.upper().strip()

    # Cek cache dulu
    if not force_refresh:
        cached = await get_cached_analisa(ticker)
        if cached:
            logger.info(f"Cache hit for {ticker}")
            return {
                "ticker": ticker,
                "fase": cached["fase"],
                "entry": cached["entry"],
                "tp": cached.get("tp"),
                "sl": cached.get("sl"),
                "alasan": cached.get("reason"),
                "chart_path": cached.get("chart_path"),
                "provider": "cache",
                "from_cache": True,
            }

    # Fetch data market
    df = await fetch_ohlcv(ticker)
    if df is None:
        logger.error(f"No data for {ticker}")
        return None

    ohlcv = get_latest_ohlcv(df)
    indicators = calculate_indicators(df)
    news_context = await get_market_news_context(ticker)

    # Generate chart
    chart_path = await generate_chart(ticker, df)

    # Hermes analisa
    result, provider = await hermes_analyze_stock(
        ticker=ticker,
        ohlcv_data=ohlcv,
        indicators=indicators,
        news_context=news_context,
        skill_context=skill_context,
        tier=tier,
        admin_context=admin_context,
    )

    if not result:
        return None

    # Simpan ke cache
    await save_analisa_cache(ticker, result, chart_path)

    # Simpan ke history Supabase
    try:
        sb = get_supabase()
        sb.table("analisa_history").insert({
            "saham": ticker,
            "tier_target": tier,
            "fase": result.get("fase"),
            "entry": result.get("entry"),
            "tp": result.get("tp"),
            "sl": result.get("sl"),
            "reason": result.get("alasan"),
            "provider_used": provider,
            "status": "open",
        }).execute()
    except Exception as e:
        logger.error(f"Save analisa history error: {e}")

    return {
        "ticker": ticker,
        "fase": result.get("fase"),
        "entry": result.get("entry"),
        "tp": result.get("tp"),
        "sl": result.get("sl"),
        "alasan": result.get("alasan"),
        "confidence": result.get("confidence"),
        "chart_path": chart_path,
        "provider": provider,
        "from_cache": False,
    }


def format_signal_message(result: dict, tier: str) -> str:
    """Format pesan sinyal sesuai tier"""
    ticker = result.get("ticker", "")
    fase = result.get("fase", "")
    entry = result.get("entry", 0)
    alasan = result.get("alasan", "")

    if tier == "bronze":
        return (
            f"{ticker} {fase}\n"
            f"Entry: Rp {int(entry):,}\n"
            f"Alasan: {alasan}"
        ).replace(",", ".")
    else:
        tp = result.get("tp", 0)
        sl = result.get("sl", 0)
        return (
            f"{ticker} {fase}\n"
            f"Entry : Rp {int(entry):,}\n"
            f"TP    : Rp {int(tp):,}\n"
            f"SL    : Rp {int(sl):,}\n"
            f"Alasan: {alasan}"
        ).replace(",", ".")
