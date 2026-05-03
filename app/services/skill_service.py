# -*- coding: utf-8 -*-
"""
Zenith Bot — Skill Service
Manajemen skill Hermes: global, silver, diamond personal
"""

from typing import Optional
from loguru import logger
from app.database import get_supabase


async def get_active_skills() -> list[dict]:
    """Ambil semua skill global yang aktif"""
    try:
        sb = get_supabase()
        result = sb.table("hermes_skills").select("*").eq("is_active", True).eq("source", "admin").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"get_active_skills error: {e}")
        return []


async def get_user_active_skills(user_id: str) -> list[dict]:
    """Ambil skill yang sedang aktif untuk user (Silver/Diamond)"""
    try:
        sb = get_supabase()
        # Implementasi tracking skill aktif per user via tabel user_active_skills
        result = sb.table("user_active_skills").select("skill_id, hermes_skills(*)").eq("user_id", user_id).execute()
        if result.data:
            return [row["hermes_skills"] for row in result.data if row.get("hermes_skills")]
        return []
    except Exception as e:
        logger.error(f"get_user_active_skills error: {e}")
        return []


async def get_skill_context(user_id: str, tier: str) -> str:
    """Build skill context string untuk prompt Hermes"""
    try:
        skills = await get_user_active_skills(user_id)
        if not skills:
            skills = await get_active_skills()

        if not skills:
            return ""

        context_parts = []
        for skill in skills[:2]:  # Max 2 skill aktif
            context_parts.append(f"[{skill.get('name', '')}] {skill.get('content_text', '')[:500]}")

        return "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"get_skill_context error: {e}")
        return ""


async def list_available_skills() -> list[dict]:
    """List semua skill yang tersedia (untuk Silver /switchskill)"""
    try:
        sb = get_supabase()
        result = sb.table("hermes_skills").select("id, name, description, category, is_active").eq("source", "admin").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"list_available_skills error: {e}")
        return []


async def activate_skill_for_user(user_id: str, skill_id: str) -> tuple[bool, str]:
    """Aktifkan skill untuk user, max 2 skill bersamaan"""
    try:
        sb = get_supabase()

        # Cek jumlah skill aktif saat ini
        current = sb.table("user_active_skills").select("id").eq("user_id", user_id).execute()
        if len(current.data or []) >= 2:
            return False, "Sudah ada 2 skill aktif. Nonaktifkan 1 skill terlebih dahulu."

        # Cek skill sudah aktif
        existing = sb.table("user_active_skills").select("id").eq("user_id", user_id).eq("skill_id", skill_id).execute()
        if existing.data:
            return False, "Skill ini sudah aktif."

        sb.table("user_active_skills").insert({"user_id": user_id, "skill_id": skill_id}).execute()
        return True, "Skill berhasil diaktifkan."
    except Exception as e:
        logger.error(f"activate_skill_for_user error: {e}")
        return False, "Terjadi kesalahan sistem."


async def deactivate_skill_for_user(user_id: str, skill_id: str) -> bool:
    try:
        sb = get_supabase()
        sb.table("user_active_skills").delete().eq("user_id", user_id).eq("skill_id", skill_id).execute()
        return True
    except Exception as e:
        logger.error(f"deactivate_skill_for_user error: {e}")
        return False


async def upload_personal_skill(user_id: str, content: str, category: str = "personal") -> bool:
    """Upload skill personal Diamond"""
    try:
        sb = get_supabase()
        sb.table("rag_user_skills").insert({
            "user_id": user_id,
            "content_type": "text",
            "content_text": content,
            "category": category,
            "file_size": len(content.encode("utf-8")),
        }).execute()
        logger.info(f"Personal skill uploaded for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"upload_personal_skill error: {e}")
        return False


async def add_skill_admin(name: str, description: str, content: str, category: str = "general") -> bool:
    """Admin upload skill global"""
    try:
        sb = get_supabase()
        sb.table("hermes_skills").insert({
            "name": name,
            "description": description,
            "content_text": content,
            "category": category,
            "source": "admin",
            "is_active": True,
        }).execute()
        logger.info(f"Admin skill added: {name}")
        return True
    except Exception as e:
        logger.error(f"add_skill_admin error: {e}")
        return False
