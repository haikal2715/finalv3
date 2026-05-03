# -*- coding: utf-8 -*-
"""
Zenith Bot — Alert Harga Handler
Set & monitor price alerts per user
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.utils.keyboards import kb_main_menu
from app.utils.states import AlertStates
from app.utils.helpers import sanitize_ticker, is_valid_price, format_rupiah
from app.services.usage_service import check_alert_limit, increment_alert
from app.database import vps_execute, vps_fetch, get_supabase
from app.config import TIER_LIMITS

router = Router()


@router.callback_query(F.data == "menu:alert")
async def cb_alert_menu(callback: CallbackQuery, state: FSMContext, user: dict = None, tier: str = None):
    try:
        if not user or not tier:
            await callback.answer("Langganan diperlukan.", show_alert=True)
            return

        can_set = await check_alert_limit(user["id"], tier)
        if not can_set:
            limit = TIER_LIMITS[tier]["alert_per_day"]
            await callback.answer(
                f"Batas alert harian ({limit}x) sudah tercapai.",
                show_alert=True
            )
            return

        await state.set_state(AlertStates.waiting_ticker)
        await state.update_data(user_id=user["id"], tier=tier)
        await callback.message.edit_text(
            "Alert Harga\n\nMasukkan kode saham (contoh: BBCA):"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_alert_menu error: {e}")


@router.message(AlertStates.waiting_ticker)
async def process_alert_ticker(message: Message, state: FSMContext):
    try:
        ticker = sanitize_ticker(message.text)
        if not ticker or len(ticker) < 2:
            await message.answer("Kode saham tidak valid. Contoh: BBCA")
            return
        await state.update_data(alert_ticker=ticker)
        await state.set_state(AlertStates.waiting_price)
        await message.answer(f"Saham: {ticker}\n\nMasukkan harga target (contoh: 9500):")
    except Exception as e:
        logger.error(f"process_alert_ticker error: {e}")


@router.message(AlertStates.waiting_price)
async def process_alert_price(message: Message, state: FSMContext):
    try:
        valid, price = is_valid_price(message.text)
        if not valid:
            await message.answer("Format harga tidak valid. Contoh: 9500 atau 9.500")
            return
        await state.update_data(alert_price=price)
        await state.set_state(AlertStates.waiting_direction)
        await message.answer(
            f"Harga target: {format_rupiah(price)}\n\n"
            "Alert saat harga:\n"
            "1. Di atas harga target (breakout)\n"
            "2. Di bawah harga target (support tercapai)\n\n"
            "Ketik 1 atau 2:"
        )
    except Exception as e:
        logger.error(f"process_alert_price error: {e}")


@router.message(AlertStates.waiting_direction)
async def process_alert_direction(message: Message, state: FSMContext, user: dict = None, tier: str = None):
    try:
        choice = message.text.strip()
        if choice not in ("1", "2"):
            await message.answer("Pilih 1 (di atas) atau 2 (di bawah):")
            return

        direction = "above" if choice == "1" else "below"
        data = await state.get_data()
        ticker = data.get("alert_ticker")
        price = data.get("alert_price")
        uid = user["id"] if user else data.get("user_id")

        await state.clear()

        # Simpan alert ke VPS cache
        await vps_execute("""
            INSERT INTO alerts (user_id, saham, target_price, direction)
            VALUES ($1, $2, $3, $4)
        """, uid, ticker, price, direction)

        await increment_alert(uid)

        direction_text = "di atas" if direction == "above" else "di bawah"
        await message.answer(
            f"Alert aktif!\n\n"
            f"Saham : {ticker}\n"
            f"Target: {format_rupiah(price)}\n"
            f"Notif : Saat harga {direction_text} target",
            reply_markup=kb_main_menu(tier),
        )
    except Exception as e:
        logger.error(f"process_alert_direction error: {e}")


async def check_and_fire_alerts(bot):
    """
    Dipanggil oleh scheduler setiap 5 menit saat market buka.
    Cek semua alert aktif dan kirim notifikasi jika triggered.
    """
    try:
        alerts = await vps_fetch(
            "SELECT * FROM alerts WHERE is_triggered = FALSE"
        )
        if not alerts:
            return

        from app.services.market_service import fetch_ohlcv, get_latest_ohlcv

        checked_tickers = {}
        for alert in alerts:
            ticker = alert["saham"]
            if ticker not in checked_tickers:
                df = await fetch_ohlcv(ticker, n_bars=2)
                if df is not None:
                    ohlcv = get_latest_ohlcv(df)
                    checked_tickers[ticker] = ohlcv.get("close", 0)

            current_price = checked_tickers.get(ticker, 0)
            if not current_price:
                continue

            triggered = False
            if alert["direction"] == "above" and current_price >= alert["target_price"]:
                triggered = True
            elif alert["direction"] == "below" and current_price <= alert["target_price"]:
                triggered = True

            if triggered:
                # Ambil telegram_id user
                sb = get_supabase()
                user_result = sb.table("users").select("telegram_id").eq("id", str(alert["user_id"])).execute()
                if user_result.data:
                    tg_id = user_result.data[0]["telegram_id"]
                    direction_text = "di atas" if alert["direction"] == "above" else "di bawah"
                    await bot.send_message(
                        tg_id,
                        f"ALERT TERAMBIL\n\n"
                        f"{ticker} kini {direction_text} target\n"
                        f"Harga saat ini : {format_rupiah(current_price)}\n"
                        f"Harga target   : {format_rupiah(alert['target_price'])}"
                    )

                # Mark as triggered
                await vps_execute(
                    "UPDATE alerts SET is_triggered = TRUE WHERE id = $1",
                    alert["id"]
                )
    except Exception as e:
        logger.error(f"check_and_fire_alerts error: {e}")
