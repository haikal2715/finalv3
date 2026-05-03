# -*- coding: utf-8 -*-
"""
Zenith Bot — FSM States
Semua state untuk conversation flow Aiogram 3.x
"""

from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_email = State()
    waiting_password = State()
    waiting_register_email = State()
    waiting_register_password = State()
    waiting_register_confirm = State()
    waiting_forgot_email = State()


class RequestStates(StatesGroup):
    waiting_ticker = State()
    waiting_category = State()
    waiting_preset = State()


class AlertStates(StatesGroup):
    waiting_ticker = State()
    waiting_price = State()
    waiting_direction = State()


class AdminStates(StatesGroup):
    hermes_chat = State()
    waiting_skill_name = State()
    waiting_skill_desc = State()
    waiting_skill_content = State()
    waiting_saran_ticker = State()
    waiting_saran_context = State()
    waiting_adduser_id = State()
    waiting_adduser_days = State()
    waiting_quote_text = State()
    waiting_quote_author = State()


class SkillUploadStates(StatesGroup):
    waiting_skill_content = State()
