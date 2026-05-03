# -*- coding: utf-8 -*-
"""
Zenith Bot — Konfigurasi Terpusat
Semua settings dibaca dari environment variables via .env
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import pytz


class Settings(BaseSettings):
    # Telegram
    bot_token: str = Field(..., env="BOT_TOKEN")
    admin_telegram_id: int = Field(..., env="ADMIN_TELEGRAM_ID")

    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")

    # VPS PostgreSQL Cache
    vps_db_host: str = Field(default="localhost", env="VPS_DB_HOST")
    vps_db_port: int = Field(default=5432, env="VPS_DB_PORT")
    vps_db_name: str = Field(default="zenith_cache", env="VPS_DB_NAME")
    vps_db_user: str = Field(..., env="VPS_DB_USER")
    vps_db_pass: str = Field(..., env="VPS_DB_PASS")

    # AI Providers
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    cerebras_api_key: str = Field(..., env="CEREBRAS_API_KEY")
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    llm7_api_key: str = Field(default="", env="LLM7_API_KEY")
    siliconflow_api_key: str = Field(default="", env="SILICONFLOW_API_KEY")

    # Cohere
    cohere_api_key: str = Field(..., env="COHERE_API_KEY")

    # News
    gnews_api_key: str = Field(..., env="GNEWS_API_KEY")

    # Payment
    midtrans_server_key: str = Field(..., env="MIDTRANS_SERVER_KEY")
    midtrans_client_key: str = Field(..., env="MIDTRANS_CLIENT_KEY")
    midtrans_is_production: bool = Field(default=False, env="MIDTRANS_IS_PRODUCTION")

    # Auth
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_days: int = Field(default=365)

    # Google OAuth
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI")

    # Web Server
    web_host: str = Field(default="0.0.0.0", env="WEB_HOST")
    web_port: int = Field(default=8000, env="WEB_PORT")
    base_url: str = Field(..., env="BASE_URL")

    # App
    app_env: str = Field(default="production", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    timezone: str = Field(default="Asia/Jakarta", env="TIMEZONE")

    @property
    def tz(self) -> pytz.BaseTzInfo:
        return pytz.timezone(self.timezone)

    @property
    def vps_db_url(self) -> str:
        return (
            f"postgresql://{self.vps_db_user}:{self.vps_db_pass}"
            f"@{self.vps_db_host}:{self.vps_db_port}/{self.vps_db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

# Pricing config
TIER_PRICES = {
    "bronze": 59_000,
    "silver": 109_000,
    "diamond": 189_000,
}

TIER_LIMITS = {
    "bronze": {"request_per_day": 1, "alert_per_day": 1, "skill_switch": False, "upload_skill": False, "rag_personal": False},
    "silver": {"request_per_day": 3, "alert_per_day": 2, "skill_switch": True, "upload_skill": False, "rag_personal": False},
    "diamond": {"request_per_day": 6, "alert_per_day": 3, "skill_switch": True, "upload_skill": True, "rag_personal": True},
}

# AI Provider order
AI_PROVIDER_ORDER = [
    "openrouter",
    "groq",
    "cerebras",
    "gemini",
    "cloudflare",
    "llm7",
    "siliconflow",
]

# Model mapping per provider
AI_MODELS = {
    "openrouter": "nousresearch/hermes-3-llama-3.1-70b",
    "groq": "llama-3.3-70b-versatile",
    "cerebras": "llama3.1-8b",
    "gemini": "gemini-2.0-flash",
    "cloudflare": "@cf/meta/llama-3.1-8b-instruct",
    "llm7": "auto",
    "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
}
