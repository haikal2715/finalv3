# -*- coding: utf-8 -*-
"""
Zenith Bot — Utilities
Helper functions yang digunakan di seluruh aplikasi
"""

import re
from datetime import date
from loguru import logger
from app.database import get_supabase


def sanitize_ticker(ticker: str) -> str:
    """Sanitasi input ticker saham"""
    cleaned = ticker.upper().strip()
    cleaned = re.sub(r"[^A-Z0-9]", "", cleaned)
    return cleaned[:10]


def format_rupiah(amount: int | float) -> str:
    """Format angka ke format Rupiah"""
    return f"Rp {int(amount):,}".replace(",", ".")


def format_date_id(d: date) -> str:
    """Format date ke format Indonesia"""
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{d.day} {months[d.month - 1]} {d.year}"


async def get_daily_quote() -> dict:
    """Ambil kutipan harian berdasarkan hari dalam tahun"""
    try:
        sb = get_supabase()
        result = sb.table("daily_quotes").select("id, quote_text, author").execute()
        quotes = result.data or []
        if not quotes:
            return {"quote_text": "The market rewards patience.", "author": "Anonim"}

        day_of_year = date.today().timetuple().tm_yday
        index = day_of_year % len(quotes)
        return quotes[index]
    except Exception as e:
        logger.error(f"get_daily_quote error: {e}")
        return {"quote_text": "The market rewards patience.", "author": "Anonim"}


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_price(price_str: str) -> tuple[bool, float]:
    """Validasi input harga dari user"""
    try:
        cleaned = price_str.replace(".", "").replace(",", "").strip()
        price = float(cleaned)
        if price <= 0 or price > 100_000_000:
            return False, 0
        return True, price
    except (ValueError, AttributeError):
        return False, 0
