"""Configuración centralizada de logging para el generador de reportes."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_dir: Path, *, console: bool = True, level: int = logging.INFO) -> logging.Logger:
    """Crea o reutiliza un logger con salida a archivo y opcionalmente consola."""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'reporte_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.log_file = str(log_file)  # type: ignore[attr-defined]
    return logger
