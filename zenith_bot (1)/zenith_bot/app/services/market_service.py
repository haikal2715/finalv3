# -*- coding: utf-8 -*-
"""
Zenith Bot — Market Data Service
Primary: tvdatafeed (TradingView)
Fallback: yfinance
Indicators: ta library
"""

import asyncio
from typing import Optional
import pandas as pd
import numpy as np
from loguru import logger

try:
    from tvdatafeed import TvDatafeed, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False
    logger.warning("tvdatafeed not available, using yfinance only")

import yfinance as yf
import ta


# =====================================================
# DATA FETCHING
# =====================================================

def _fetch_tv_sync(ticker: str, exchange: str = "IDX", n_bars: int = 100) -> Optional[pd.DataFrame]:
    """Fetch data dari TradingView (sync, dijalankan di thread)"""
    if not TV_AVAILABLE:
        return None
    try:
        tv = TvDatafeed()
        df = tv.get_hist(
            symbol=ticker,
            exchange=exchange,
            interval=Interval.in_daily,
            n_bars=n_bars,
        )
        if df is not None and not df.empty:
            return df
        return None
    except Exception as e:
        logger.warning(f"tvdatafeed error for {ticker}: {e}")
        return None


def _fetch_yfinance_sync(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """Fetch data dari yfinance (sync)"""
    try:
        # IDX ticker format di yfinance: BBCA.JK
        yf_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        df = yf.download(yf_ticker, period=period, progress=False)
        if df is not None and not df.empty:
            df.columns = [c.lower() for c in df.columns]
            return df
        return None
    except Exception as e:
        logger.warning(f"yfinance error for {ticker}: {e}")
        return None


async def fetch_ohlcv(ticker: str, n_bars: int = 100) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data dengan fallback chain.
    Return DataFrame dengan kolom: open, high, low, close, volume
    """
    ticker = ticker.upper().strip()

    # Coba tvdatafeed dulu
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, _fetch_tv_sync, ticker, "IDX", n_bars)

    if df is not None:
        logger.info(f"Data {ticker} fetched via tvdatafeed ({len(df)} bars)")
        return df

    # Fallback yfinance
    logger.info(f"Fallback yfinance for {ticker}")
    df = await loop.run_in_executor(None, _fetch_yfinance_sync, ticker)
    if df is not None:
        logger.info(f"Data {ticker} fetched via yfinance ({len(df)} bars)")
        return df

    logger.error(f"Failed to fetch data for {ticker}")
    return None


def get_latest_ohlcv(df: pd.DataFrame) -> dict:
    """Extract latest OHLCV dari DataFrame"""
    if df is None or df.empty:
        return {}
    last = df.iloc[-1]
    volume_avg = df["volume"].tail(20).mean() if "volume" in df.columns else 0
    return {
        "open": round(float(last.get("open", 0)), 2),
        "high": round(float(last.get("high", 0)), 2),
        "low": round(float(last.get("low", 0)), 2),
        "close": round(float(last.get("close", 0)), 2),
        "volume": int(last.get("volume", 0)),
        "volume_avg": round(float(volume_avg), 0),
    }


# =====================================================
# TECHNICAL INDICATORS
# =====================================================

def calculate_indicators(df: pd.DataFrame) -> dict:
    """Hitung semua indikator teknikal yang diperlukan Hermes"""
    if df is None or len(df) < 30:
        return {}

    try:
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)

        # RSI
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()

        # MACD
        macd_ind = ta.trend.MACD(close, window_fast=12, window_slow=26, window_sign=9)
        macd_line = macd_ind.macd()
        macd_signal = macd_ind.macd_signal()

        # EMA & MA
        ema5 = ta.trend.EMAIndicator(close, window=5).ema_indicator()
        ma20 = ta.trend.SMAIndicator(close, window=20).sma_indicator()
        ma50 = ta.trend.SMAIndicator(close, window=50).sma_indicator()

        # Support & Resistance (simplified: pivot dari 20 bar terakhir)
        recent_high = high.tail(20)
        recent_low = low.tail(20)
        pivot = (recent_high.max() + recent_low.min() + close.iloc[-1]) / 3
        r1 = 2 * pivot - recent_low.min()
        s1 = 2 * pivot - recent_high.max()
        r2 = pivot + (recent_high.max() - recent_low.min())
        s2 = pivot - (recent_high.max() - recent_low.min())

        return {
            "rsi": round(float(rsi.iloc[-1]), 2),
            "macd": round(float(macd_line.iloc[-1]), 4),
            "macd_signal": round(float(macd_signal.iloc[-1]), 4),
            "ema5": round(float(ema5.iloc[-1]), 2),
            "ma20": round(float(ma20.iloc[-1]), 2),
            "ma50": round(float(ma50.iloc[-1]), 2),
            "support1": round(float(s1), 2),
            "support2": round(float(s2), 2),
            "resistance1": round(float(r1), 2),
            "resistance2": round(float(r2), 2),
        }
    except Exception as e:
        logger.error(f"calculate_indicators error: {e}")
        return {}


# =====================================================
# CHART GENERATION
# =====================================================

async def generate_chart(ticker: str, df: pd.DataFrame) -> Optional[str]:
    """Generate chart teknikal sebagai PNG file"""
    try:
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import os

        os.makedirs("charts", exist_ok=True)
        chart_path = f"charts/{ticker}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.png"

        # Prepare data
        plot_df = df.tail(60).copy()
        plot_df.index = pd.DatetimeIndex(plot_df.index)

        # Plot
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save_chart, plot_df, ticker, chart_path)

        return chart_path
    except Exception as e:
        logger.error(f"generate_chart error for {ticker}: {e}")
        return None


def _save_chart(df: pd.DataFrame, ticker: str, path: str):
    import mplfinance as mpf

    # Moving averages overlay
    ema5 = ta.trend.EMAIndicator(df["close"].astype(float), window=5).ema_indicator()
    ma20 = ta.trend.SMAIndicator(df["close"].astype(float), window=20).sma_indicator()

    apds = [
        mpf.make_addplot(ema5, color="orange", width=1, label="EMA5"),
        mpf.make_addplot(ma20, color="blue", width=1.5, label="MA20"),
    ]

    mpf.plot(
        df,
        type="candle",
        style="charles",
        title=f"\n{ticker} - Zenith",
        ylabel="Harga (Rp)",
        volume=True,
        addplot=apds,
        figsize=(12, 7),
        savefig=dict(fname=path, dpi=150, bbox_inches="tight"),
    )


# =====================================================
# IDX SCANNER
# =====================================================

IDX_SCAN_LISTS = {
    "idxsmc30": ["BBCA", "BBRI", "BBNI", "BMRI", "TLKM", "ASII", "UNVR", "ICBP", "KLBF", "GOTO",
                 "BYAN", "ADRO", "PTBA", "INCO", "ANTM", "SMGR", "PGAS", "JSMR", "EXCL", "ISAT",
                 "MNCN", "EMTK", "BUKA", "ARTO", "BREN", "AMMN", "MBMA", "CUAN", "PGEO", "TPIA"],
    "lq45": ["AALI", "ADRO", "AKRA", "AMRT", "ANTM", "ARTO", "ASII", "BBCA", "BBNI", "BBRI",
              "BBTN", "BJTM", "BKSL", "BMRI", "BREN", "BRMS", "BYAN", "CPIN", "CTRA", "EMTK",
              "ERAA", "ESSA", "EXCL", "GGRM", "GOTO", "HEAL", "HMSP", "HRUM", "ICBP", "INCO",
              "INDF", "INKP", "INTP", "ISAT", "ITMG", "JSMR", "KLBF", "MAPI", "MBMA", "MNCN",
              "PGAS", "PTBA", "SMGR", "TLKM", "UNVR"],
}
