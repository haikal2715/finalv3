# -*- coding: utf-8 -*-
"""
Zenith Bot — Request Analisa Handler
/request — analisa saham per tier
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.utils.keyboards import kb_request_type, kb_indicator_preset, kb_main_menu
from app.utils.states import RequestStates
from app.utils.helpers import sanitize_ticker
from app.services.signal_service import run_full_analysis, format_signal_message
from app.services.usage_service import check_request_limit, increment_request, get_usage_today
from app.services.skill_service import get_skill_context
from app.config import TIER_LIMITS

router = Router()


@router.callback_query(F.data == "menu:request")
async def cb_request_menu(callback: CallbackQuery, user: dict = None, tier: str = None):
    try:
        if not user:
            await callback.answer("Silakan login terlebih dahulu.", show_alert=True)
            return
        if not tier:
            await callback.answer("Langganan diperlukan untuk fitur ini.", show_alert=True)
            return

        usage = await get_usage_today(user["id"])
        limit = TIER_LIMITS[tier]["request_per_day"]
        remaining = limit - usage["request_count"]

        if remaining <= 0:
            await callback.answer(
                f"Batas request harian ({limit}x) sudah tercapai. Coba lagi besok.",
                show_alert=True
            )
            return

        if tier == "bronze":
            # Bronze langsung minta ticker
            await callback.message.edit_text(
                f"Request Analisa (Bronze)\n"
                f"Sisa: {remaining}/{limit} hari ini\n\n"
                "Masukkan kode saham (contoh: BBCA, TLKM):"
            )
            await callback.answer()
            # Set state
            from aiogram.fsm.context import FSMContext
            # Handled via text handler below
            await callback.message.bot.set_state = None  # handled in process
        else:
            await callback.message.edit_text(
                f"Request Analisa ({tier.capitalize()})\n"
                f"Sisa: {remaining}/{limit} hari ini\n\n"
                "Pilih jenis analisa:",
                reply_markup=kb_request_type(),
            )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_request_menu error: {e}")


@router.callback_query(F.data == "req:ticker")
async def cb_req_ticker(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(RequestStates.waiting_ticker)
        await callback.message.edit_text(
            "Masukkan kode saham (contoh: BBCA, TLKM, GOTO):"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_req_ticker error: {e}")


@router.callback_query(F.data.startswith("req:cat:"))
async def cb_req_category(callback: CallbackQuery, state: FSMContext):
    try:
        category = callback.data.replace("req:cat:", "")
        await state.update_data(req_category=category)
        await callback.message.edit_text(
            f"Kategori: {category.upper()}\n\nPilih preset indikator:",
            reply_markup=kb_indicator_preset(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"cb_req_category error: {e}")


@router.callback_query(F.data.startswith("preset:"))
async def cb_req_preset(callback: CallbackQuery, state: FSMContext, user: dict = None, tier: str = None):
    try:
        preset = callback.data.replace("preset:", "")
        data = await state.get_data()
        category = data.get("req_category", "idxsmc30")
        await state.clear()

        await callback.message.edit_text("Hermes sedang menganalisa... mohon tunggu.")
        await callback.answer()

        # Pilih 2 saham dari kategori
        from app.services.market_service import IDX_SCAN_LISTS
        tickers = IDX_SCAN_LISTS.get(category, IDX_SCAN_LISTS["idxsmc30"])[:5]

        skill_ctx = await get_skill_context(user["id"], tier) if user else ""
        results = []

        for ticker in tickers[:2]:
            result = await run_full_analysis(ticker, tier=tier, skill_context=skill_ctx)
            if result:
                results.append(result)

        if not results:
            await callback.message.edit_text(
                "Analisa gagal. Data tidak tersedia. Coba lagi nanti.",
                reply_markup=kb_main_menu(tier),
            )
            return

        await increment_request(user["id"])

        for result in results:
            msg_text = format_signal_message(result, tier)
            chart_path = result.get("chart_path")

            if chart_path:
                try:
                    await callback.message.answer_photo(
                        photo=FSInputFile(chart_path),
                        caption=msg_text,
                    )
                except Exception as e:
                    logger.warning(f"Chart send failed: {e}")
                    await callback.message.answer(msg_text)
            else:
                await callback.message.answer(msg_text)

        await callback.message.answer("Analisa selesai.", reply_markup=kb_main_menu(tier))
    except Exception as e:
        logger.error(f"cb_req_preset error: {e}")


# Handler untuk input ticker langsung (Bronze & Silver/Diamond ticker spesifik)
@router.message(RequestStates.waiting_ticker)
async def process_ticker_input(message: Message, state: FSMContext, user: dict = None, tier: str = None):
    try:
        ticker = sanitize_ticker(message.text)
        if not ticker or len(ticker) < 2:
            await message.answer("Kode saham tidak valid. Contoh: BBCA, TLKM")
            return

        can_request = await check_request_limit(user["id"], tier)
        if not can_request:
            limit = TIER_LIMITS[tier]["request_per_day"]
            await state.clear()
            await message.answer(
                f"Batas request harian ({limit}x) sudah tercapai.",
                reply_markup=kb_main_menu(tier),
            )
            return

        await state.clear()
        wait_msg = await message.answer(f"Hermes menganalisa {ticker}... mohon tunggu.")

        skill_ctx = await get_skill_context(user["id"], tier) if user else ""
        result = await run_full_analysis(ticker, tier=tier, skill_context=skill_ctx)

        try:
            await wait_msg.delete()
        except Exception:
            pass

        if not result:
            await message.answer(
                f"Analisa {ticker} gagal. Data tidak tersedia atau ticker tidak valid.",
                reply_markup=kb_main_menu(tier),
            )
            return

        await increment_request(user["id"])

        msg_text = format_signal_message(result, tier)
        chart_path = result.get("chart_path")

        if chart_path:
            try:
                await message.answer_photo(
                    photo=FSInputFile(chart_path),
                    caption=msg_text,
                )
            except Exception as e:
                logger.warning(f"Chart send failed: {e}")
                await message.answer(msg_text)
        else:
            await message.answer(msg_text)

        usage = await get_usage_today(user["id"])
        limit = TIER_LIMITS[tier]["request_per_day"]
        remaining = limit - usage["request_count"]
        await message.answer(
            f"Sisa request hari ini: {remaining}/{limit}",
            reply_markup=kb_main_menu(tier),
        )
    except Exception as e:
        logger.error(f"process_ticker_input error: {e}")
