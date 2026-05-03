# -*- coding: utf-8 -*-
"""
Zenith Bot — Skill Switch Handler
/switchskill untuk Silver dan Diamond
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.utils.keyboards import kb_skill_list, kb_main_menu
from app.utils.states import SkillUploadStates
from app.services.skill_service import (
    list_available_skills, activate_skill_for_user,
    deactivate_skill_for_user, get_user_active_skills,
    upload_personal_skill
)

router = Router()


@router.callback_query(F.data == "menu:switchskill")
async def cb_switchskill(callback: CallbackQuery, user: dict = None, tier: str = None):
    try:
        if not user or tier not in ("silver", "diamond"):
            await callback.answer("Fitur ini hanya untuk Silver dan Diamond.", show_alert=True)
            return

        skills = await list_available_skills()
        active_skills = await get_user_active_skills(user["id"])
        active_ids = {s["id"] for s in active_skills}

        if not skills:
            await callback.answer("Belum ada skill tersedia.", show_alert=True)
            return

        lines = ["SKILL HERMES\n"]
        for skill in skills:
            status = "[AKTIF]" if skill["id"] in active_ids else "[  ]"
            lines.append(f"{status} {skill['name']}\n{skill.get('description', '')}\n")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=kb_skill_list(skills),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_switchskill error: {e}")


@router.callback_query(F.data.startswith("skill:toggle:"))
async def cb_skill_toggle(callback: CallbackQuery, user: dict = None, tier: str = None):
    try:
        if not user:
            await callback.answer("Login diperlukan.", show_alert=True)
            return

        skill_id = callback.data.replace("skill:toggle:", "")
        active_skills = await get_user_active_skills(user["id"])
        active_ids = {s["id"] for s in active_skills}

        if skill_id in active_ids:
            # Deactivate
            await deactivate_skill_for_user(user["id"], skill_id)
            await callback.answer("Skill dinonaktifkan.")
        else:
            # Activate
            success, msg = await activate_skill_for_user(user["id"], skill_id)
            await callback.answer(msg, show_alert=not success)

        # Refresh list
        skills = await list_available_skills()
        active_skills = await get_user_active_skills(user["id"])
        active_ids = {s["id"] for s in active_skills}

        lines = ["SKILL HERMES\n"]
        for skill in skills:
            status = "[AKTIF]" if skill["id"] in active_ids else "[  ]"
            lines.append(f"{status} {skill['name']}\n{skill.get('description', '')}\n")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=kb_skill_list(skills),
        )
    except Exception as e:
        logger.error(f"cb_skill_toggle error: {e}")


# =====================================================
# UPLOAD SKILL PERSONAL (Diamond)
# =====================================================

@router.callback_query(F.data == "menu:hermes_personal")
async def cb_hermes_personal(callback: CallbackQuery, user: dict = None, tier: str = None):
    try:
        if not user or tier != "diamond":
            await callback.answer("Fitur ini khusus Diamond.", show_alert=True)
            return

        await callback.message.edit_text(
            "Hermes Personal (Diamond)\n\n"
            "Kamu bisa upload style trading pribadimu dalam bentuk teks.\n"
            "Hermes akan belajar dari pola tradingmu dan memberikan\n"
            "analisa yang makin personal.\n\n"
            "Kirim teks gaya trading atau strategi favoritmu:"
        )
        # Set state untuk upload
        from aiogram.fsm.context import FSMContext
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_hermes_personal error: {e}")


@router.message(SkillUploadStates.waiting_skill_content)
async def process_skill_upload(message: Message, state: FSMContext, user: dict = None, tier: str = None):
    try:
        content = message.text.strip()
        if len(content) < 50:
            await message.answer("Konten terlalu singkat. Tambahkan lebih banyak detail tentang strategi tradingmu.")
            return

        success = await upload_personal_skill(user["id"], content)
        await state.clear()

        if success:
            await message.answer(
                "Skill personal berhasil disimpan.\n"
                "Hermes akan menggunakan strategi ini dalam analisa selanjutnya.",
                reply_markup=kb_main_menu(tier),
            )
        else:
            await message.answer("Gagal menyimpan skill. Coba lagi.", reply_markup=kb_main_menu(tier))
    except Exception as e:
        logger.error(f"process_skill_upload error: {e}")
