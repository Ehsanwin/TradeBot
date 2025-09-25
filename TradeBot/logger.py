from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from TradeBot.config.setting_schema import TradingBotConfig

_CFG = TradingBotConfig().logging  # LoggingConfig

_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMG]B?)?\s*$", re.I)

def _parse_size(value: object, default_bytes: int = 10 * 1024 * 1024) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return default_bytes

    s = value.strip()

    if s.isdigit():
        return max(0, int(s))

    m = _SIZE_RE.match(s)
    if not m:
        return default_bytes
    num = float(m.group(1))
    unit = (m.group(2) or "").upper()

    factor = 1
    if unit in ("K", "KB"):
        factor = 1024
    elif unit in ("M", "MB"):
        factor = 1024 ** 2
    elif unit in ("G", "GB"):
        factor = 1024 ** 3

    return max(0, int(num * factor))

def _resolve_level() -> int:
    level_name = (_CFG.level or os.getenv("LOG_LEVEL", "INFO")).upper()
    return _LEVELS.get(level_name, logging.INFO)

def _resolve_file_path() -> str:
    return (_CFG.file or os.getenv("LOG_FILE_PATH") or "logs/trading.log")

def _resolve_max_bytes() -> int:
    env_bytes = os.getenv("LOG_MAX_FILE_SIZE")
    if env_bytes and env_bytes.isdigit():
        return int(env_bytes)
    return _parse_size(_CFG.max_size)

def _resolve_backup_count() -> int:
    try:
        return int(_CFG.backup_count or int(os.getenv("LOG_BACKUP_COUNT", "5")))
    except Exception:
        return 5

def _resolve_rotation_hours() -> int:
    try:
        return int(os.getenv("LOG_ROTATION_HOURS", "0"))
    except Exception:
        return 0

def setup_logging(force: bool = False) -> logging.Logger:
    root = logging.getLogger()
    if getattr(root, "_finnhub_logging_configured", False) and not force:
        return root

    root.setLevel(_resolve_level())

    fmt = logging.Formatter(_CFG.format)

    if _CFG.console_output:
        ch = logging.StreamHandler()
        ch.setLevel(_resolve_level())
        ch.setFormatter(fmt)
        root.addHandler(ch)

    if _CFG.file_output:
        log_path = Path(_resolve_file_path()).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        rotation_hours = _resolve_rotation_hours()
        if rotation_hours > 0:
            fh = TimedRotatingFileHandler(
                str(log_path), when="h", interval=rotation_hours,
                backupCount=_resolve_backup_count(), encoding="utf-8"
            )
        else:
            fh = RotatingFileHandler(
                str(log_path), maxBytes=_resolve_max_bytes(),
                backupCount=_resolve_backup_count(), encoding="utf-8"
            )
        fh.setLevel(_resolve_level())
        fh.setFormatter(fmt)
        root.addHandler(fh)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    root._finnhub_logging_configured = True  # type: ignore[attr-defined]
    return root

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
