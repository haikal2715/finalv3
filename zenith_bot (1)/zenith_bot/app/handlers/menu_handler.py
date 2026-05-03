# -*- coding: utf-8 -*-
"""
Zenith Bot — Menu & Navigation Handlers
Menu utama, profil, langganan
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import date

from app.utils.keyboards import kb_main_menu, kb_tier_select, kb_profile_actions
from app.utils.helpers import get_daily_quote, format_date_id, format_rupiah
from app.services.subscription_service import get_active_subscription, get_days_remaining
from app.services.payment_service import create_payment
from app.config import TIER_PRICES

router = Router()


def _require_login(user: dict) -> bool:
    return user is not None


def _require_subscription(tier: str) -> bool:
    return tier is not None


# =====================================================
# MENU UTAMA
# =====================================================

@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, user: dict = None, tier: str = None):
    try:
        if not _require_login(user):
            await callback.answer("Silakan login terlebih dahulu.", show_alert=True)
            return

        quote = await get_daily_quote()
        sub = await get_active_subscription(user["id"])
        days_left = await get_days_remaining(user["id"])
        tier_display = tier.capitalize() if tier else "Tidak aktif"
        username = user.get("username") or "Pengguna"

        text = (
            f"ZENITH\n\n"
            f"Selamat datang, {username}\n"
            f"Plan    : {tier_display}\n"
            f"Berlaku : {days_left} hari lagi\n\n"
            f"{'-' * 30}\n"
            f'"{quote["quote_text"]}"\n'
            f"  - {quote['author']}\n"
            f"{'-' * 30}"
        )
        await callback.message.edit_text(text, reply_markup=kb_main_menu(tier))
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_main_menu error: {e}")


@router.callback_query(F.data == "menu:back")
async def cb_back(callback: CallbackQuery, user: dict = None, tier: str = None):
    await cb_main_menu(callback, user, tier)


# =====================================================
# PROFIL & LANGGANAN
# =====================================================

@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery, user: dict = None, tier: str = None, subscription: dict = None):
    try:
        if not _require_login(user):
            await callback.answer("Silakan login terlebih dahulu.", show_alert=True)
            return

        username = user.get("username") or "Pengguna"
        email = user.get("email") or "-"
        tier_display = tier.capitalize() if tier else "Tidak aktif"
        days_left = await get_days_remaining(user["id"])

        if subscription:
            end_date = date.fromisoformat(subscription["end_date"])
            end_str = format_date_id(end_date)
        else:
            end_str = "-"

        text = (
            f"PROFIL\n\n"
            f"Username : {username}\n"
            f"Email    : {email}\n"
            f"Plan     : {tier_display}\n"
            f"Berlaku s/d : {end_str}\n"
            f"Sisa     : {days_left} hari\n\n"
            f"Harga paket:\n"
            f"Bronze  : {format_rupiah(TIER_PRICES['bronze'])}/bulan\n"
            f"Silver  : {format_rupiah(TIER_PRICES['silver'])}/bulan\n"
            f"Diamond : {format_rupiah(TIER_PRICES['diamond'])}/bulan"
        )
        await callback.message.edit_text(text, reply_markup=kb_profile_actions(tier))
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_profile error: {e}")


@router.callback_query(F.data == "sub:select")
async def cb_sub_select(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "Pilih paket langganan:",
            reply_markup=kb_tier_select(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_sub_select error: {e}")


@router.callback_query(F.data.startswith("sub:") & ~F.data.startswith("sub:select"))
async def cb_sub_tier(callback: CallbackQuery, user: dict = None):
    try:
        if not _require_login(user):
            await callback.answer("Silakan login terlebih dahulu.", show_alert=True)
            return

        tier = callback.data.replace("sub:", "")
        if tier not in TIER_PRICES:
            await callback.answer("Tier tidak valid.", show_alert=True)
            return

        payment = await create_payment(
            user_id=user["id"],
            telegram_id=callback.from_user.id,
            tier=tier,
            user_email=user.get("email"),
            user_name=user.get("username"),
        )

        if not payment:
            await callback.answer("Gagal membuat pembayaran. Coba lagi.", show_alert=True)
            return

        text = (
            f"PEMBAYARAN\n\n"
            f"Paket  : {tier.capitalize()}\n"
            f"Harga  : {format_rupiah(payment['amount'])}\n"
            f"Order  : {payment['order_id']}\n\n"
            f"Klik link berikut untuk melanjutkan pembayaran:\n"
            f"{payment['redirect_url']}\n\n"
            f"Setelah pembayaran berhasil, akses akan aktif otomatis."
        )
        await callback.message.edit_text(text)
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_sub_tier error: {e}")
