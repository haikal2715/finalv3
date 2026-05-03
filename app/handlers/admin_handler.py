# -*- coding: utf-8 -*-
"""
Zenith Bot — Admin Handlers
/dashboard, /hermesAdmin, /tambahskill, /adduser, dll
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from loguru import logger

from app.utils.keyboards import kb_admin_dashboard, kb_hermes_admin_mode, kb_admin_tier
from app.utils.states import AdminStates
from app.utils.helpers import sanitize_ticker
from app.services.hermes_service import hermes_chat, HERMES_SYSTEM_PROMPT
from app.services.signal_service import run_full_analysis, format_signal_message
from app.services.skill_service import add_skill_admin, list_available_skills
from app.services.subscription_service import activate_subscription
from app.services.auth_service import get_user_by_telegram_id, create_user
from app.database import get_supabase
from app.config import settings

router = Router()

ADMIN_ID = settings.admin_telegram_id


def is_admin(telegram_id: int) -> bool:
    return telegram_id == ADMIN_ID


# =====================================================
# /dashboard
# =====================================================

@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message):
    try:
        if not is_admin(message.from_user.id):
            return

        sb = get_supabase()
        users_count = len(sb.table("users").select("id").execute().data or [])
        subs = sb.table("subscriptions").select("tier, status").eq("status", "active").execute().data or []
        bronze = sum(1 for s in subs if s["tier"] == "bronze")
        silver = sum(1 for s in subs if s["tier"] == "silver")
        diamond = sum(1 for s in subs if s["tier"] == "diamond")

        text = (
            f"ZENITH DASHBOARD ADMIN\n\n"
            f"Total user  : {users_count}\n"
            f"Aktif       : {len(subs)}\n"
            f"  Bronze    : {bronze}\n"
            f"  Silver    : {silver}\n"
            f"  Diamond   : {diamond}\n"
        )
        await message.answer(text, reply_markup=kb_admin_dashboard())
    except Exception as e:
        logger.error(f"cmd_dashboard error: {e}")


@router.callback_query(F.data == "admin:dashboard")
async def cb_admin_dashboard(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            return
        await callback.message.edit_text("Dashboard Admin", reply_markup=kb_admin_dashboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_dashboard error: {e}")


# =====================================================
# HERMES ADMIN CHAT
# =====================================================

@router.callback_query(F.data == "admin:hermes")
async def cb_admin_hermes(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            return
        await callback.message.edit_text(
            "Hermes Admin — Pilih mode:",
            reply_markup=kb_hermes_admin_mode(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_hermes error: {e}")


@router.callback_query(F.data.startswith("admin:hermes:"))
async def cb_admin_hermes_mode(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return

        mode = callback.data.replace("admin:hermes:", "")
        mode_names = {
            "analisa": "Analisa",
            "konsultasi": "Konsultasi",
            "debug": "Debug",
        }
        mode_desc = {
            "analisa": "Analisa saham apapun tanpa limit. Ketik ticker (contoh: BBCA) atau perintah analisa.",
            "konsultasi": "Tanya kondisi market, evaluasi strategi, brainstorm. Ketik pertanyaanmu.",
            "debug": "Investigasi sinyal yang kena SL. Ketik ticker + konteks (contoh: BBCA SL kenapa?).",
        }
        await state.set_state(AdminStates.hermes_chat)
        await state.update_data(hermes_mode=mode)
        await callback.message.edit_text(
            f"Mode {mode_names.get(mode, mode)}\n\n{mode_desc.get(mode, '')}\n\n"
            "Ketik /exit untuk keluar."
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_hermes_mode error: {e}")


@router.message(AdminStates.hermes_chat)
async def process_admin_hermes_chat(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return

        if message.text.strip() == "/exit":
            await state.clear()
            await message.answer("Keluar dari Hermes Admin.", reply_markup=kb_admin_dashboard())
            return

        data = await state.get_data()
        mode = data.get("hermes_mode", "konsultasi")

        system_extra = f"MODE ADMIN: {mode.upper()}\nAdmin adalah TheProfessor, pemilik platform Zenith."

        # Jika mode analisa dan text pendek, coba parse sebagai ticker
        if mode == "analisa" and len(message.text.strip()) <= 10:
            ticker = sanitize_ticker(message.text.strip())
            if len(ticker) >= 2:
                wait_msg = await message.answer(f"Menganalisa {ticker}...")
                result = await run_full_analysis(ticker, tier="diamond", force_refresh=True)
                try:
                    await wait_msg.delete()
                except Exception:
                    pass
                if result:
                    await message.answer(format_signal_message(result, "diamond"))
                    return

        wait_msg = await message.answer("Hermes sedang berpikir...")
        response, provider = await hermes_chat(
            messages=[{"role": "user", "content": message.text}],
            system_extra=system_extra,
        )
        try:
            await wait_msg.delete()
        except Exception:
            pass

        if response:
            await message.answer(f"[{provider}]\n\n{response}")
        else:
            await message.answer("Hermes tidak dapat merespons saat ini. Coba lagi.")
    except Exception as e:
        logger.error(f"process_admin_hermes_chat error: {e}")


# =====================================================
# TAMBAH SKILL
# =====================================================

@router.callback_query(F.data == "admin:addskill")
async def cb_admin_addskill(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return
        await state.set_state(AdminStates.waiting_skill_name)
        await callback.message.edit_text("Tambah Skill Hermes\n\nMasukkan nama skill:")
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_addskill error: {e}")


@router.message(AdminStates.waiting_skill_name)
async def process_skill_name(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        await state.update_data(skill_name=message.text.strip())
        await state.set_state(AdminStates.waiting_skill_desc)
        await message.answer("Masukkan deskripsi singkat skill:")
    except Exception as e:
        logger.error(f"process_skill_name error: {e}")


@router.message(AdminStates.waiting_skill_desc)
async def process_skill_desc(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        await state.update_data(skill_desc=message.text.strip())
        await state.set_state(AdminStates.waiting_skill_content)
        await message.answer("Masukkan konten skill (instruksi lengkap untuk Hermes):")
    except Exception as e:
        logger.error(f"process_skill_desc error: {e}")


@router.message(AdminStates.waiting_skill_content)
async def process_skill_content(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        data = await state.get_data()
        await state.clear()

        success = await add_skill_admin(
            name=data.get("skill_name", ""),
            description=data.get("skill_desc", ""),
            content=message.text.strip(),
        )

        if success:
            await message.answer(
                f"Skill '{data.get('skill_name')}' berhasil ditambahkan.",
                reply_markup=kb_admin_dashboard(),
            )
        else:
            await message.answer("Gagal menambahkan skill.", reply_markup=kb_admin_dashboard())
    except Exception as e:
        logger.error(f"process_skill_content error: {e}")


# =====================================================
# LIST SKILL
# =====================================================

@router.callback_query(F.data == "admin:listskill")
async def cb_admin_listskill(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            return
        skills = await list_available_skills()
        if not skills:
            await callback.answer("Belum ada skill.", show_alert=True)
            return

        lines = ["DAFTAR SKILL HERMES\n"]
        for s in skills:
            status = "AKTIF" if s.get("is_active") else "NONAKTIF"
            lines.append(f"[{status}] {s['name']}\n{s.get('description', '')}\n")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=kb_admin_dashboard(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_listskill error: {e}")


# =====================================================
# SARAN ANALISA UNTUK HERMES
# =====================================================

@router.callback_query(F.data == "admin:saran")
async def cb_admin_saran(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return
        await state.set_state(AdminStates.waiting_saran_ticker)
        await callback.message.edit_text(
            "Saran Analisa ke Hermes\n\nMasukkan ticker saham:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_saran error: {e}")


@router.message(AdminStates.waiting_saran_ticker)
async def process_saran_ticker(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        ticker = sanitize_ticker(message.text)
        await state.update_data(saran_ticker=ticker)
        await state.set_state(AdminStates.waiting_saran_context)
        await message.answer(f"Saham: {ticker}\n\nMasukkan konteks market (alasan kamu tertarik saham ini):")
    except Exception as e:
        logger.error(f"process_saran_ticker error: {e}")


@router.message(AdminStates.waiting_saran_context)
async def process_saran_context(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        data = await state.get_data()
        ticker = data.get("saran_ticker")
        context = message.text.strip()
        await state.clear()

        wait_msg = await message.answer(f"Hermes menganalisa {ticker} dengan konteksmu...")
        result = await run_full_analysis(ticker, tier="diamond", admin_context=context, force_refresh=True)

        try:
            await wait_msg.delete()
        except Exception:
            pass

        if result:
            # Simpan ke admin_suggestions
            sb = get_supabase()
            sb.table("admin_suggestions").insert({
                "admin_id": message.from_user.id,
                "ticker": ticker,
                "context": context,
                "hermes_result": str(result),
                "is_signal": result.get("fase") in ("BUY", "SELL"),
            }).execute()

            await message.answer(
                format_signal_message(result, "diamond"),
                reply_markup=kb_admin_dashboard(),
            )
        else:
            await message.answer("Analisa gagal.", reply_markup=kb_admin_dashboard())
    except Exception as e:
        logger.error(f"process_saran_context error: {e}")


# =====================================================
# ADD USER MANUAL (influencer/mitra)
# =====================================================

@router.callback_query(F.data == "admin:adduser")
async def cb_admin_adduser(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return
        await state.set_state(AdminStates.waiting_adduser_id)
        await callback.message.edit_text(
            "Tambah User Manual\n\nMasukkan @username atau Telegram ID:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_adduser error: {e}")


@router.message(AdminStates.waiting_adduser_id)
async def process_adduser_id(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        await state.update_data(target_user=message.text.strip())
        await message.answer(
            f"User: {message.text.strip()}\n\nPilih tier:",
            reply_markup=kb_admin_tier(),
        )
    except Exception as e:
        logger.error(f"process_adduser_id error: {e}")


@router.callback_query(F.data.startswith("admin:adduser:"))
async def cb_adduser_tier(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return
        tier = callback.data.replace("admin:adduser:", "")
        await state.update_data(adduser_tier=tier)
        await state.set_state(AdminStates.waiting_adduser_days)
        await callback.message.edit_text(f"Tier: {tier.capitalize()}\n\nMasa berlaku berapa hari?")
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_adduser_tier error: {e}")


@router.message(AdminStates.waiting_adduser_days)
async def process_adduser_days(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        try:
            days = int(message.text.strip())
            if days <= 0 or days > 3650:
                raise ValueError
        except ValueError:
            await message.answer("Masukkan jumlah hari yang valid (1-3650):")
            return

        data = await state.get_data()
        target = data.get("target_user", "")
        tier = data.get("adduser_tier", "bronze")
        await state.clear()

        await message.answer(
            f"Konfirmasi:\n"
            f"User   : {target}\n"
            f"Tier   : {tier.capitalize()}\n"
            f"Berlaku: {days} hari\n\n"
            f"Ketik KONFIRMASI untuk melanjutkan atau /batal:"
        )
        await state.update_data(confirm_target=target, confirm_tier=tier, confirm_days=days)
        await state.set_state(AdminStates.waiting_adduser_id)  # Reuse state for confirm
    except Exception as e:
        logger.error(f"process_adduser_days error: {e}")


# =====================================================
# TAMBAH KUTIPAN
# =====================================================

@router.callback_query(F.data == "admin:addquote")
async def cb_admin_addquote(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            return
        await state.set_state(AdminStates.waiting_quote_text)
        await callback.message.edit_text("Tambah Kutipan Harian\n\nMasukkan teks kutipan:")
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_admin_addquote error: {e}")


@router.message(AdminStates.waiting_quote_text)
async def process_quote_text(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        await state.update_data(quote_text=message.text.strip())
        await state.set_state(AdminStates.waiting_quote_author)
        await message.answer("Masukkan nama tokoh/sumber:")
    except Exception as e:
        logger.error(f"process_quote_text error: {e}")


@router.message(AdminStates.waiting_quote_author)
async def process_quote_author(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            return
        data = await state.get_data()
        await state.clear()

        sb = get_supabase()
        sb.table("daily_quotes").insert({
            "quote_text": data.get("quote_text", ""),
            "author": message.text.strip(),
        }).execute()

        await message.answer("Kutipan berhasil ditambahkan.", reply_markup=kb_admin_dashboard())
    except Exception as e:
        logger.error(f"process_quote_author error: {e}")
