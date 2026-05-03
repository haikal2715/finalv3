# -*- coding: utf-8 -*-
"""
Zenith Bot — Scheduler
APScheduler jobs:
- Pre-analisa malam (tiap hari 20:00 WIB)
- Alert checker (tiap 5 menit saat market buka)
- Weekend learning (Jumat 15:30-17:30 WIB)
- Cleanup cache (Sabtu 00:00 WIB)
- Expire subscription check (tiap hari 00:05 WIB)
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import pytz

from app.config import settings

WIB = pytz.timezone("Asia/Jakarta")


async def job_pre_analisa_malam(bot):
    """
    Scan malam hari — simpan ke cache VPS.
    Dijalankan tiap hari 20:00 WIB (termasuk Minggu untuk Senin pagi).
    """
    try:
        logger.info("Scheduler: pre-analisa malam dimulai")
        from app.services.market_service import IDX_SCAN_LISTS
        from app.services.signal_service import run_full_analysis
        from app.config import settings

        scan_list = IDX_SCAN_LISTS["idxsmc30"] + IDX_SCAN_LISTS["lq45"]
        seen = set()
        unique_tickers = [t for t in scan_list if not (t in seen or seen.add(t))]

        success_count = 0
        for ticker in unique_tickers[:30]:  # Batasi 30 ticker per run
            try:
                result = await run_full_analysis(ticker, tier="silver", force_refresh=True)
                if result:
                    success_count += 1
            except Exception as e:
                logger.warning(f"Pre-analisa error for {ticker}: {e}")

        logger.info(f"Pre-analisa selesai: {success_count}/{len(unique_tickers[:30])} berhasil")
    except Exception as e:
        logger.error(f"job_pre_analisa_malam error: {e}")


async def job_alert_checker(bot):
    """Cek price alert tiap 5 menit saat market buka (09:00-15:30 WIB)"""
    try:
        from datetime import datetime
        now = datetime.now(WIB)
        # Market buka Senin-Jumat 09:00-15:30
        if now.weekday() >= 5:  # Sabtu-Minggu
            return
        hour = now.hour
        minute = now.minute
        if not (9 <= hour < 15 or (hour == 15 and minute <= 30)):
            return

        from app.handlers.alert_handler import check_and_fire_alerts
        await check_and_fire_alerts(bot)
    except Exception as e:
        logger.error(f"job_alert_checker error: {e}")


async def job_weekend_learning(bot):
    """
    Weekend learning — Jumat 15:30 WIB
    Hermes review semua SL hit minggu ini dan generate lesson learned
    """
    try:
        logger.info("Scheduler: weekend learning dimulai")
        from app.database import get_supabase
        from app.services.hermes_service import hermes_chat
        from datetime import date, timedelta

        sb = get_supabase()
        week_start = (date.today() - timedelta(days=7)).isoformat()

        # Ambil semua SL hit minggu ini
        sl_hits = sb.table("analisa_history").select("*").eq("status", "sl_hit").gte("created_at", week_start).execute()
        signals = sl_hits.data or []

        if not signals:
            logger.info("Weekend learning: tidak ada SL hit minggu ini")
            return

        lessons_generated = 0
        for signal in signals:
            try:
                prompt = (
                    f"Analisa kegagalan sinyal berikut:\n"
                    f"Saham : {signal.get('saham')}\n"
                    f"Entry : {signal.get('entry')}\n"
                    f"SL    : {signal.get('sl')}\n"
                    f"Alasan original: {signal.get('reason', '-')}\n"
                    f"Skill digunakan: {signal.get('skill_used', '-')}\n\n"
                    "Identifikasi penyebab SL hit dan buat lesson learned singkat (1-2 kalimat) "
                    "yang bisa digunakan untuk memperbaiki analisa serupa di masa depan. "
                    "Format output: LESSON: <lesson learned>"
                )
                response, provider = await hermes_chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_extra="MODE: SELF-IMPROVEMENT LEARNING",
                )

                if response and "LESSON:" in response:
                    lesson = response.split("LESSON:")[-1].strip()[:500]
                    sb.table("hermes_improvements").insert({
                        "saham": signal.get("saham"),
                        "entry": signal.get("entry"),
                        "sl": signal.get("sl"),
                        "skill_active": signal.get("skill_used"),
                        "original_reason": signal.get("reason"),
                        "lesson_learned": lesson,
                        "week_date": date.today().isoformat(),
                    }).execute()
                    lessons_generated += 1
            except Exception as e:
                logger.warning(f"Weekend learning error for signal {signal.get('id')}: {e}")

        logger.info(f"Weekend learning selesai: {lessons_generated} lesson generated")

        # Kirim ringkasan ke admin
        try:
            summary = (
                f"WEEKLY LEARNING SUMMARY\n\n"
                f"SL hit minggu ini : {len(signals)}\n"
                f"Lesson generated  : {lessons_generated}\n"
                f"Semua lesson disimpan ke RAG global Hermes."
            )
            await bot.send_message(settings.admin_telegram_id, summary)
        except Exception as e:
            logger.warning(f"Kirim summary ke admin gagal: {e}")

    except Exception as e:
        logger.error(f"job_weekend_learning error: {e}")


async def job_cleanup_cache(bot):
    """Bersihkan cache VPS yang expired — Sabtu 00:00 WIB"""
    try:
        from app.database import vps_execute
        await vps_execute("DELETE FROM analisa_cache WHERE expired_at < NOW()")
        await vps_execute("DELETE FROM alerts WHERE is_triggered = TRUE AND created_at < NOW() - INTERVAL '7 days'")
        logger.info("Scheduler: cache cleanup selesai")
    except Exception as e:
        logger.error(f"job_cleanup_cache error: {e}")


async def job_expire_subscriptions(bot):
    """Update status subscription expired — tiap hari 00:05 WIB"""
    try:
        from app.services.subscription_service import expire_old_subscriptions
        await expire_old_subscriptions()

        # Hapus RAG Diamond yang sudah expired > 7 hari
        from app.database import get_supabase
        from datetime import date, timedelta
        sb = get_supabase()
        cutoff = (date.today() - timedelta(days=7)).isoformat()

        # Ambil user yang subscriptionnya expired > 7 hari lalu
        expired_subs = sb.table("subscriptions").select("user_id").eq("status", "expired").lt("end_date", cutoff).execute()
        if expired_subs.data:
            for sub in expired_subs.data:
                sb.table("rag_user_skills").delete().eq("user_id", sub["user_id"]).execute()
            logger.info(f"RAG personal dihapus untuk {len(expired_subs.data)} user expired")
    except Exception as e:
        logger.error(f"job_expire_subscriptions error: {e}")


async def job_distribute_daily_signals(bot):
    """
    Distribusi sinyal harian ke semua subscriber aktif — 09:15 WIB
    Bronze: sinyal tanpa TP/SL dari cache
    Silver/Diamond: sinyal lengkap
    """
    try:
        logger.info("Scheduler: distribusi sinyal harian dimulai")
        from app.database import get_supabase
        from app.services.signal_service import run_full_analysis, format_signal_message
        from app.services.market_service import IDX_SCAN_LISTS
        from aiogram.types import FSInputFile
        import asyncio

        sb = get_supabase()
        from datetime import date
        today = date.today().isoformat()

        # Ambil semua subscriber aktif
        subs = sb.table("subscriptions").select("user_id, tier").eq("status", "active").gte("end_date", today).execute()
        if not subs.data:
            return

        # Pilih saham untuk sinyal hari ini (top 3 dari IDX30)
        signal_tickers = IDX_SCAN_LISTS["idxsmc30"][:5]
        signals_by_tier = {"bronze": [], "silver": [], "diamond": []}

        for ticker in signal_tickers:
            for tier in ("bronze", "silver", "diamond"):
                result = await run_full_analysis(ticker, tier=tier)
                if result and result.get("fase") in ("BUY", "SELL"):
                    signals_by_tier[tier].append(result)
                    break  # 1 ticker = 1 tier target

        # Distribusi per user
        for sub in subs.data:
            try:
                tier = sub["tier"]
                user_signals = signals_by_tier.get(tier, [])
                if not user_signals:
                    continue

                # Ambil telegram_id
                user = sb.table("users").select("telegram_id").eq("id", sub["user_id"]).execute()
                if not user.data:
                    continue

                tg_id = user.data[0]["telegram_id"]
                header = f"SINYAL HERMES - {date.today().strftime('%d/%m/%Y')}\n\n"

                for sig in user_signals[:2]:  # Max 2 sinyal per hari untuk Silver/Diamond
                    msg = format_signal_message(sig, tier)
                    chart_path = sig.get("chart_path")
                    try:
                        if chart_path:
                            await bot.send_photo(
                                tg_id,
                                photo=FSInputFile(chart_path),
                                caption=header + msg,
                            )
                        else:
                            await bot.send_message(tg_id, header + msg)
                    except Exception as e:
                        logger.warning(f"Kirim sinyal ke {tg_id} gagal: {e}")

                    await asyncio.sleep(0.05)  # Rate limit protection

            except Exception as e:
                logger.warning(f"Distribusi sinyal user {sub['user_id']} error: {e}")

        logger.info("Scheduler: distribusi sinyal selesai")
    except Exception as e:
        logger.error(f"job_distribute_daily_signals error: {e}")


def setup_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=WIB)

    # Pre-analisa malam — tiap hari 20:00 WIB
    scheduler.add_job(
        job_pre_analisa_malam,
        CronTrigger(hour=20, minute=0, timezone=WIB),
        args=[bot],
        id="pre_analisa",
        replace_existing=True,
    )

    # Alert checker — tiap 5 menit
    scheduler.add_job(
        job_alert_checker,
        CronTrigger(minute="*/5", timezone=WIB),
        args=[bot],
        id="alert_checker",
        replace_existing=True,
    )

    # Distribusi sinyal harian — 09:15 WIB Senin-Jumat
    scheduler.add_job(
        job_distribute_daily_signals,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=15, timezone=WIB),
        args=[bot],
        id="daily_signals",
        replace_existing=True,
    )

    # Weekend learning — Jumat 15:30 WIB
    scheduler.add_job(
        job_weekend_learning,
        CronTrigger(day_of_week="fri", hour=15, minute=30, timezone=WIB),
        args=[bot],
        id="weekend_learning",
        replace_existing=True,
    )

    # Cleanup cache — Sabtu 00:00 WIB
    scheduler.add_job(
        job_cleanup_cache,
        CronTrigger(day_of_week="sat", hour=0, minute=0, timezone=WIB),
        args=[bot],
        id="cleanup_cache",
        replace_existing=True,
    )

    # Expire subscription check — tiap hari 00:05 WIB
    scheduler.add_job(
        job_expire_subscriptions,
        CronTrigger(hour=0, minute=5, timezone=WIB),
        args=[bot],
        id="expire_subs",
        replace_existing=True,
    )

    return scheduler
