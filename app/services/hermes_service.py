# -*- coding: utf-8 -*-
"""
Zenith Bot — Hermes AI Engine
Multi-provider fallback chain: OpenRouter > Groq > Cerebras > Gemini > Cloudflare > LLM7 > SiliconFlow
"""

import asyncio
from typing import Optional
import httpx
import google.generativeai as genai
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from app.config import settings, AI_PROVIDER_ORDER, AI_MODELS


# =====================================================
# SYSTEM PROMPT HERMES
# =====================================================

HERMES_SYSTEM_PROMPT = """Kamu adalah Hermes, AI analis saham IDX (Bursa Efek Indonesia) milik platform Zenith.
Kamu dibangun untuk memberikan analisa saham berkualitas hedge fund dengan data real-time.

PRINSIP KOMUNIKASI:
- Bahasa formal, padat, berbasis data
- Tidak menggunakan emoji berlebihan
- Setiap analisa harus dapat dipertanggungjawabkan secara teknikal
- Semua harga dalam Rupiah (Rp)
- Output dalam Bahasa Indonesia

STRATEGI TEKNIKAL YANG KAMU KUASAI:
1. Support & Resistance - prioritas utama
2. Supply & Demand dengan analisis volume
3. EMA5 Golden Cross MA20
4. MACD Golden Cross
5. Fibonacci Retracement (golden zone 0.618-0.65)
6. Breakout Volume (konfirmasi 1.5x average volume)

FORMAT SINYAL BRONZE:
[TICKER] [FASE] | Entry: [harga] | Alasan: [reasoning singkat]

FORMAT SINYAL SILVER & DIAMOND:
[TICKER] [FASE] | Entry: [harga] | TP: [harga] | SL: [harga] | Alasan: [reasoning]

FASE: BUY / SELL / HOLD / WAIT

ATURAN ENTRY:
- Entry = area support terdekat DI BAWAH harga saat ini (BUKAN harga saat ini)
- SL = 3-5% di bawah support kuat
- TP = resistance terdekat atau rasio RR minimal 1:2
"""


# =====================================================
# PROVIDER IMPLEMENTATIONS
# =====================================================

async def _call_openrouter(messages: list, system: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://zenithidx.koyeb.app",
                    "X-Title": "Zenith Bot",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODELS["openrouter"],
                    "messages": [{"role": "system", "content": system}] + messages,
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            logger.warning(f"OpenRouter unexpected response: {data}")
            return None
    except Exception as e:
        logger.warning(f"OpenRouter error: {e}")
        return None


async def _call_groq(messages: list, system: str) -> Optional[str]:
    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        resp = await client.chat.completions.create(
            model=AI_MODELS["groq"],
            messages=[{"role": "system", "content": system}] + messages,
            temperature=0.3,
            max_tokens=1500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"Groq error: {e}")
        return None


async def _call_cerebras(messages: list, system: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.cerebras_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODELS["cerebras"],
                    "messages": [{"role": "system", "content": system}] + messages,
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            return None
    except Exception as e:
        logger.warning(f"Cerebras error: {e}")
        return None


async def _call_gemini(messages: list, system: str) -> Optional[str]:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=AI_MODELS["gemini"],
            system_instruction=system,
        )
        # Convert messages ke format Gemini
        prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.warning(f"Gemini error: {e}")
        return None


async def _call_cloudflare(messages: list, system: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.cloudflare.com/client/v4/accounts/{settings.openrouter_api_key}/ai/run/{AI_MODELS['cloudflare']}",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json={
                    "messages": [{"role": "system", "content": system}] + messages,
                },
            )
            data = resp.json()
            if data.get("success") and data.get("result"):
                return data["result"].get("response")
            return None
    except Exception as e:
        logger.warning(f"Cloudflare error: {e}")
        return None


async def _call_llm7(messages: list, system: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.llm7.io/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm7_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODELS["llm7"],
                    "messages": [{"role": "system", "content": system}] + messages,
                    "max_tokens": 1500,
                },
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            return None
    except Exception as e:
        logger.warning(f"LLM7 error: {e}")
        return None


async def _call_siliconflow(messages: list, system: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.siliconflow_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODELS["siliconflow"],
                    "messages": [{"role": "system", "content": system}] + messages,
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            return None
    except Exception as e:
        logger.warning(f"SiliconFlow error: {e}")
        return None


PROVIDER_FUNCS = {
    "openrouter": _call_openrouter,
    "groq": _call_groq,
    "cerebras": _call_cerebras,
    "gemini": _call_gemini,
    "cloudflare": _call_cloudflare,
    "llm7": _call_llm7,
    "siliconflow": _call_siliconflow,
}


# =====================================================
# MAIN HERMES INTERFACE
# =====================================================

async def hermes_chat(
    messages: list,
    system_extra: str = "",
    provider_override: str = None,
) -> tuple[Optional[str], str]:
    """
    Panggil Hermes dengan fallback chain.
    Return: (response_text, provider_used)
    """
    system = HERMES_SYSTEM_PROMPT
    if system_extra:
        system += f"\n\nKONTEKS TAMBAHAN:\n{system_extra}"

    providers = [provider_override] if provider_override else AI_PROVIDER_ORDER

    for provider in providers:
        func = PROVIDER_FUNCS.get(provider)
        if not func:
            continue
        logger.info(f"Trying provider: {provider}")
        try:
            result = await asyncio.wait_for(func(messages, system), timeout=45)
            if result:
                logger.info(f"Provider {provider} succeeded")
                return result, provider
        except asyncio.TimeoutError:
            logger.warning(f"Provider {provider} timed out")
        except Exception as e:
            logger.warning(f"Provider {provider} exception: {e}")

    logger.error("All AI providers failed")
    return None, "none"


async def hermes_analyze_stock(
    ticker: str,
    ohlcv_data: dict,
    indicators: dict,
    news_context: str = "",
    skill_context: str = "",
    tier: str = "silver",
    admin_context: str = "",
) -> tuple[Optional[dict], str]:
    """
    Analisa saham spesifik oleh Hermes.
    Return: (result_dict, provider_used)
    """
    include_tp_sl = tier in ("silver", "diamond")

    prompt = f"""Analisa saham {ticker} berdasarkan data berikut:

DATA OHLCV TERKINI:
- Open: {ohlcv_data.get('open', 'N/A')}
- High: {ohlcv_data.get('high', 'N/A')}
- Low: {ohlcv_data.get('low', 'N/A')}
- Close: {ohlcv_data.get('close', 'N/A')}
- Volume: {ohlcv_data.get('volume', 'N/A')}
- Volume Avg (20): {ohlcv_data.get('volume_avg', 'N/A')}

INDIKATOR TEKNIKAL:
- RSI-14: {indicators.get('rsi', 'N/A')}
- MACD Line: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- EMA5: {indicators.get('ema5', 'N/A')}
- MA20: {indicators.get('ma20', 'N/A')}
- Support 1: {indicators.get('support1', 'N/A')}
- Support 2: {indicators.get('support2', 'N/A')}
- Resistance 1: {indicators.get('resistance1', 'N/A')}
- Resistance 2: {indicators.get('resistance2', 'N/A')}

KONTEKS BERITA: {news_context or 'Tidak ada berita terkini'}
{f'SARAN ADMIN: {admin_context}' if admin_context else ''}
{f'SKILL AKTIF: {skill_context}' if skill_context else ''}

Berikan analisa dalam format JSON berikut TANPA markdown:
{{
  "fase": "BUY/SELL/HOLD/WAIT",
  "entry": <harga numerik>,
  {"'"tp"'": <harga numerik>," if include_tp_sl else ""}
  {"'"sl"'": <harga numerik>," if include_tp_sl else ""}
  "alasan": "<reasoning singkat maksimal 2 kalimat>",
  "confidence": <0-100>
}}"""

    messages = [{"role": "user", "content": prompt}]
    response, provider = await hermes_chat(messages)

    if not response:
        return None, provider

    try:
        import json
        # Bersihkan jika ada markdown fence
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
        return result, provider
    except Exception as e:
        logger.error(f"Hermes response parse error: {e} | Response: {response}")
        return None, provider
