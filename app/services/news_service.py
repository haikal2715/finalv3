# -*- coding: utf-8 -*-
"""
Zenith Bot — News Service
RSS Kontan, CNBC Indo, Bisnis.com + GNews API + Google News RSS
"""

import asyncio
from typing import Optional
import feedparser
import httpx
from loguru import logger

from app.config import settings

NEWS_RSS_SOURCES = {
    "kontan": "https://www.kontan.co.id/rss/news",
    "cnbc_indo": "https://www.cnbcindonesia.com/rss",
    "bisnis": "https://bisnis.com/rss",
    "google_news_idx": "https://news.google.com/rss/search?q=saham+IDX+bursa+efek&hl=id&gl=ID&ceid=ID:id",
}


async def fetch_rss_news(source_url: str, max_items: int = 5) -> list[dict]:
    try:
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, source_url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:300],
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return items
    except Exception as e:
        logger.warning(f"RSS fetch error {source_url}: {e}")
        return []


async def fetch_gnews(query: str, max_items: int = 3) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q": query,
                    "lang": "id",
                    "country": "id",
                    "max": max_items,
                    "token": settings.gnews_api_key,
                },
            )
            data = resp.json()
            articles = data.get("articles", [])
            return [{"title": a["title"], "summary": a.get("description", "")[:200]} for a in articles]
    except Exception as e:
        logger.warning(f"GNews error: {e}")
        return []


async def get_market_news_context(ticker: str = None) -> str:
    """Kumpulkan berita terkini untuk konteks Hermes"""
    news_items = []

    # Fetch dari semua sumber paralel
    tasks = [fetch_rss_news(url, 3) for url in NEWS_RSS_SOURCES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            news_items.extend(result)

    # Tambah GNews jika ada ticker spesifik
    if ticker:
        gnews_items = await fetch_gnews(f"saham {ticker} Indonesia")
        news_items.extend(gnews_items)

    if not news_items:
        return "Tidak ada berita terkini."

    # Format untuk prompt Hermes
    lines = []
    for item in news_items[:8]:
        title = item.get("title", "")
        if title:
            lines.append(f"- {title}")

    return "\n".join(lines) if lines else "Tidak ada berita terkini."
