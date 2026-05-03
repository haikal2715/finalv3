# -*- coding: utf-8 -*-
"""
Zenith Bot — Start & Auth Handlers
/start, login, register, Google OAuth
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.utils.keyboards import kb_start, kb_login_method, kb_main_menu, kb_forgot_password
from app.utils.states import AuthStates
from app.utils.helpers import get_daily_quote, format_date_id, is_valid_email
from app.services.auth_service import (
    login_with_email, create_user, get_user_by_telegram_id,
    generate_google_auth_url, generate_password_reset_token
)
from app.services.subscription_service import get_active_subscription, get_days_remaining
from app.config import settings

router = Router()


# =====================================================
# /start
# =====================================================

@router.message(F.text == "/start")
async def cmd_start(message: Message, user: dict = None, tier: str = None):
    try:
        if user and tier:
            await show_main_menu(message, user, tier)
        else:
            await message.answer(
                "ZENITH\n\n"
                "Platform analisa saham IDX berbasis Hermes AI.\n"
                "Dirancang untuk meningkatkan akurasi keputusan trading\n"
                "dengan data real-time dan machine learning.",
                reply_markup=kb_start(),
            )
    except Exception as e:
        logger.error(f"cmd_start error: {e}")


async def show_main_menu(message: Message, user: dict, tier: str):
    """Tampilkan menu utama dengan kutipan harian dan info langganan"""
    try:
        quote = await get_daily_quote()
        sub = await get_active_subscription(user["id"])
        days_left = await get_days_remaining(user["id"])

        tier_display = tier.capitalize() if tier else "Tidak aktif"
        username = user.get("username") or user.get("email", "").split("@")[0] or "Pengguna"

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
        await message.answer(text, reply_markup=kb_main_menu(tier))
    except Exception as e:
        logger.error(f"show_main_menu error: {e}")


# =====================================================
# AUTH CALLBACKS
# =====================================================

@router.callback_query(F.data == "auth:login")
async def cb_login(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "Pilih metode login:",
            reply_markup=kb_login_method(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_login error: {e}")


@router.callback_query(F.data == "auth:register")
async def cb_register(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(AuthStates.waiting_register_email)
        await callback.message.edit_text(
            "Registrasi akun baru.\n\nMasukkan email:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_register error: {e}")


@router.callback_query(F.data == "auth:email")
async def cb_login_email(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(AuthStates.waiting_email)
        await callback.message.edit_text(
            "Masukkan email terdaftar:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_login_email error: {e}")


@router.callback_query(F.data == "auth:google")
async def cb_login_google(callback: CallbackQuery):
    try:
        telegram_id = callback.from_user.id
        auth_url = generate_google_auth_url(telegram_id)
        await callback.message.edit_text(
            f"Klik link berikut untuk login dengan Google:\n{auth_url}\n\n"
            "Setelah login, akun Telegram kamu akan terhubung otomatis."
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_login_google error: {e}")


@router.callback_query(F.data == "auth:back")
async def cb_auth_back(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "ZENITH\n\nPlatform analisa saham IDX berbasis Hermes AI.",
            reply_markup=kb_start(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_auth_back error: {e}")


# =====================================================
# LOGIN FLOW — Email
# =====================================================

@router.message(AuthStates.waiting_email)
async def process_login_email(message: Message, state: FSMContext):
    try:
        email = message.text.strip().lower()
        if not is_valid_email(email):
            await message.answer("Format email tidak valid. Masukkan email yang benar:")
            return
        await state.update_data(email=email)
        await state.set_state(AuthStates.waiting_password)
        await message.answer(
            "Masukkan password:",
            reply_markup=kb_forgot_password(),
        )
    except Exception as e:
        logger.error(f"process_login_email error: {e}")


@router.message(AuthStates.waiting_password)
async def process_login_password(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        email = data.get("email", "")
        password = message.text.strip()
        telegram_id = message.from_user.id

        # Hapus pesan password dari chat (keamanan)
        try:
            await message.delete()
        except Exception:
            pass

        token = await login_with_email(email, password, telegram_id)
        if not token:
            await message.answer(
                "Email atau password tidak valid.\nCoba lagi atau klik Lupa Password.",
                reply_markup=kb_forgot_password(),
            )
            await state.set_state(AuthStates.waiting_email)
            return

        await state.clear()
        user = await get_user_by_telegram_id(telegram_id)
        sub = await get_active_subscription(user["id"]) if user else None
        tier = sub["tier"] if sub else None

        await message.answer("Login berhasil.")
        await show_main_menu(message, user, tier)
    except Exception as e:
        logger.error(f"process_login_password error: {e}")


# =====================================================
# FORGOT PASSWORD
# =====================================================

@router.callback_query(F.data == "auth:forgot")
async def cb_forgot(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(AuthStates.waiting_forgot_email)
        await callback.message.edit_text("Masukkan email terdaftar untuk reset password:")
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_forgot error: {e}")


@router.message(AuthStates.waiting_forgot_email)
async def process_forgot_email(message: Message, state: FSMContext):
    try:
        email = message.text.strip().lower()
        token = await generate_password_reset_token(email)
        await state.clear()
        if token:
            reset_url = f"{settings.base_url}/reset-password?token={token}"
            await message.answer(
                f"Link reset password telah dikirim ke {email}.\n"
                f"Link: {reset_url}\n\nLink berlaku 1 jam."
            )
        else:
            await message.answer("Email tidak ditemukan di sistem kami.")
    except Exception as e:
        logger.error(f"process_forgot_email error: {e}")


# =====================================================
# REGISTER FLOW
# =====================================================

@router.message(AuthStates.waiting_register_email)
async def process_register_email(message: Message, state: FSMContext):
    try:
        email = message.text.strip().lower()
        if not is_valid_email(email):
            await message.answer("Format email tidak valid. Masukkan email yang benar:")
            return
        await state.update_data(reg_email=email)
        await state.set_state(AuthStates.waiting_register_password)
        await message.answer("Buat password (minimal 8 karakter):")
    except Exception as e:
        logger.error(f"process_register_email error: {e}")


@router.message(AuthStates.waiting_register_password)
async def process_register_password(message: Message, state: FSMContext):
    try:
        password = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if len(password) < 8:
            await message.answer("Password minimal 8 karakter. Coba lagi:")
            return

        data = await state.get_data()
        email = data.get("reg_email", "")
        telegram_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name

        user = await create_user(
            telegram_id=telegram_id,
            email=email,
            password=password,
            username=username,
        )

        await state.clear()
        if user:
            await message.answer(
                "Akun berhasil dibuat.\n\n"
                "Silakan pilih paket langganan untuk mulai menggunakan Zenith.",
                reply_markup=__import__("app.utils.keyboards", fromlist=["kb_tier_select"]).kb_tier_select(),
            )
        else:
            await message.answer(
                "Email sudah terdaftar atau terjadi kesalahan. Coba login atau gunakan email lain."
            )
    except Exception as e:
        logger.error(f"process_register_password error: {e}")
