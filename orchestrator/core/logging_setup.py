from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Union

def _to_int_bytes(v: Union[str, int]) -> int:
    if isinstance(v, int):
        return v
    s = str(v).strip().lower()
    try:
        return int(s)
    except ValueError:
        if s.endswith("mb"):
            return int(float(s[:-2].strip()) * 1024 * 1024)
        if s.endswith("kb"):
            return int(float(s[:-2].strip()) * 1024)
        return 10 * 1024 * 1024

def configure_logging(level: str, file_path: str, max_size: Union[str, int], backup_count: int) -> None:
    logger = logging.getLogger()
    logger.setLevel(level.upper() if level else "INFO")

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File
    if file_path:
        fh = RotatingFileHandler(
            filename=file_path,
            maxBytes=_to_int_bytes(max_size),
            backupCount=backup_count,
            encoding="utf-8"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
