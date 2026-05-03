# -*- coding: utf-8 -*-
"""
Zenith Bot — Keyboard Builder
Semua inline keyboard dan reply keyboard untuk bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_start() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Login", callback_data="auth:login"),
        InlineKeyboardButton(text="Register", callback_data="auth:register"),
    )
    return builder.as_markup()


def kb_login_method() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Email & Password", callback_data="auth:email"),
        InlineKeyboardButton(text="Hubungkan Google", callback_data="auth:google"),
    )
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="auth:back"))
    return builder.as_markup()


def kb_main_menu(tier: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Request Analisa", callback_data="menu:request"),
        InlineKeyboardButton(text="Alert Harga", callback_data="menu:alert"),
    )
    if tier in ("silver", "diamond"):
        builder.row(InlineKeyboardButton(text="Ganti Skill Hermes", callback_data="menu:switchskill"))
    if tier == "diamond":
        builder.row(InlineKeyboardButton(text="Hermes Personal", callback_data="menu:hermes_personal"))
    builder.row(InlineKeyboardButton(text="Profil & Langganan", callback_data="menu:profile"))
    return builder.as_markup()


def kb_request_type() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Ticker Spesifik", callback_data="req:ticker"))
    builder.row(
        InlineKeyboardButton(text="Top Gainer", callback_data="req:cat:gainer"),
        InlineKeyboardButton(text="IDX30", callback_data="req:cat:idxsmc30"),
    )
    builder.row(
        InlineKeyboardButton(text="LQ45", callback_data="req:cat:lq45"),
        InlineKeyboardButton(text="Top Volume", callback_data="req:cat:volume"),
    )
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="menu:back"))
    return builder.as_markup()


def kb_indicator_preset() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    presets = [
        ("Support & Resistance + Volume", "preset:snr"),
        ("Supply & Demand + Volume", "preset:snd"),
        ("MA10 + MA20 + Volume", "preset:ma"),
        ("Bollinger Bands + RSI", "preset:bb"),
        ("Super Trend + Volume", "preset:st"),
    ]
    for label, cb in presets:
        builder.row(InlineKeyboardButton(text=label, callback_data=cb))
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="req:back"))
    return builder.as_markup()


def kb_tier_select() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Bronze - Rp 59.000", callback_data="sub:bronze"),
        InlineKeyboardButton(text="Silver - Rp 109.000", callback_data="sub:silver"),
    )
    builder.row(InlineKeyboardButton(text="Diamond - Rp 189.000", callback_data="sub:diamond"))
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="menu:back"))
    return builder.as_markup()


def kb_confirm(action: str, yes_data: str, no_data: str = "menu:back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Konfirmasi", callback_data=yes_data),
        InlineKeyboardButton(text="Batal", callback_data=no_data),
    )
    return builder.as_markup()


def kb_profile_actions(tier: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Perpanjang / Upgrade", callback_data="sub:select"))
    builder.row(InlineKeyboardButton(text="Kembali ke Menu", callback_data="menu:main"))
    return builder.as_markup()


def kb_skill_list(skills: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for skill in skills:
        builder.row(InlineKeyboardButton(
            text=f"{skill['name']}",
            callback_data=f"skill:toggle:{skill['id']}"
        ))
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="menu:back"))
    return builder.as_markup()


def kb_admin_dashboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Hermes Admin", callback_data="admin:hermes"),
        InlineKeyboardButton(text="Tambah Skill", callback_data="admin:addskill"),
    )
    builder.row(
        InlineKeyboardButton(text="List Skill", callback_data="admin:listskill"),
        InlineKeyboardButton(text="Saran Analisa", callback_data="admin:saran"),
    )
    builder.row(
        InlineKeyboardButton(text="Tambah User", callback_data="admin:adduser"),
        InlineKeyboardButton(text="Tambah Kutipan", callback_data="admin:addquote"),
    )
    return builder.as_markup()


def kb_hermes_admin_mode() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Mode Analisa", callback_data="admin:hermes:analisa"),
        InlineKeyboardButton(text="Mode Konsultasi", callback_data="admin:hermes:konsultasi"),
    )
    builder.row(InlineKeyboardButton(text="Mode Debug", callback_data="admin:hermes:debug"))
    builder.row(InlineKeyboardButton(text="Kembali", callback_data="admin:dashboard"))
    return builder.as_markup()


def kb_admin_tier() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Bronze", callback_data="admin:adduser:bronze"),
        InlineKeyboardButton(text="Silver", callback_data="admin:adduser:silver"),
        InlineKeyboardButton(text="Diamond", callback_data="admin:adduser:diamond"),
    )
    return builder.as_markup()


def kb_forgot_password() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Lupa Password?", callback_data="auth:forgot"))
    return builder.as_markup()
