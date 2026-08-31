"""Journalisation : console + fichier horodaté (traçabilité — Partie 2)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pipeline.config import settings


def get_logger(name: str = "eds") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    settings.logs_dir.mkdir(exist_ok=True)
    fileh = logging.FileHandler(settings.logs_dir / f"pipeline-{datetime.now(UTC):%Y%m%d}.log")
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)

    return logger
