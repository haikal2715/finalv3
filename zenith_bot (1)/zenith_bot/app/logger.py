# -*- coding: utf-8 -*-
"""
Zenith Bot — Logging Setup
Menggunakan loguru untuk log yang lebih informatif
"""

import sys
from loguru import logger
from app.config import settings


def setup_logger():
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    # File — rotasi harian, simpan 30 hari
    logger.add(
        "logs/zenith_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info("Zenith Bot logger initialized")
    return logger


setup_logger()
