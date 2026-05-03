# -*- coding: utf-8 -*-
"""
Zenith Bot — Auth Service
JWT, password hashing, Google OAuth
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from jose import jwt, JWTError
from passlib.context import CryptContext
from loguru import logger
import httpx

from app.config import settings
from app.database import get_supabase

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =====================================================
# PASSWORD
# =====================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# =====================================================
# JWT
# =====================================================

def create_jwt_token(user_id: str, telegram_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub": user_id,
        "telegram_id": telegram_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# =====================================================
# USER MANAGEMENT
# =====================================================

async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    try:
        sb = get_supabase()
        result = sb.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"get_user_by_telegram_id error: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[dict]:
    try:
        sb = get_supabase()
        result = sb.table("users").select("*").eq("email", email.lower()).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"get_user_by_email error: {e}")
        return None


async def create_user(telegram_id: int, email: str = None, password: str = None,
                      username: str = None, google_id: str = None) -> Optional[dict]:
    try:
        sb = get_supabase()
        data = {"telegram_id": telegram_id}
        if email:
            data["email"] = email.lower()
        if password:
            data["password_hash"] = hash_password(password)
        if username:
            data["username"] = username
        if google_id:
            data["google_id"] = google_id

        result = sb.table("users").insert(data).execute()
        if result.data:
            logger.info(f"User created: telegram_id={telegram_id}")
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"create_user error: {e}")
        return None


async def login_with_email(email: str, password: str, telegram_id: int) -> Optional[str]:
    """Login dengan email+password, return JWT token"""
    try:
        user = await get_user_by_email(email)
        if not user:
            return None
        if not user.get("password_hash"):
            return None
        if not verify_password(password, user["password_hash"]):
            return None

        # Update telegram_id jika belum sesuai
        sb = get_supabase()
        sb.table("users").update({"telegram_id": telegram_id}).eq("id", user["id"]).execute()

        token = create_jwt_token(user["id"], telegram_id)
        await save_session(user["id"], token, telegram_id)
        return token
    except Exception as e:
        logger.error(f"login_with_email error: {e}")
        return None


async def save_session(user_id: str, jwt_token: str, telegram_id: int):
    try:
        sb = get_supabase()
        # Nonaktifkan session lama
        sb.table("sessions").update({"is_active": False}).eq("user_id", user_id).execute()
        # Buat session baru
        sb.table("sessions").insert({
            "user_id": user_id,
            "jwt_token": jwt_token,
            "telegram_id": telegram_id,
        }).execute()
    except Exception as e:
        logger.error(f"save_session error: {e}")


async def generate_password_reset_token(email: str) -> Optional[str]:
    try:
        user = await get_user_by_email(email)
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        # Simpan token di Supabase (kolom reset_token, expired 1 jam)
        sb = get_supabase()
        expire = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        sb.table("users").update({
            "reset_token": token,
            "reset_token_expires": expire
        }).eq("id", user["id"]).execute()
        return token
    except Exception as e:
        logger.error(f"generate_password_reset_token error: {e}")
        return None


# =====================================================
# GOOGLE OAUTH
# =====================================================

def generate_google_auth_url(telegram_id: int) -> str:
    state = f"{telegram_id}:{secrets.token_urlsafe(16)}"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"https://accounts.google.com/o/oauth2/auth?{query}"


async def exchange_google_code(code: str) -> Optional[dict]:
    """Tukar authorization code dengan user info dari Google"""
    try:
        async with httpx.AsyncClient() as client:
            # Token exchange
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(f"Google token exchange failed: {token_data}")
                return None

            # Get user info
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return userinfo_resp.json()
    except Exception as e:
        logger.error(f"exchange_google_code error: {e}")
        return None
