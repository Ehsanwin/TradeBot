from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel
import dotenv

from .setting_schema import TradingBotConfig

dotenv.load_dotenv()

def _parse_int_list(csv: str) -> List[int]:
    return [int(x.strip()) for x in (csv or "").split(",") if x.strip()]

class AppSetting(BaseModel):
    core: TradingBotConfig
    backend_base_url: str
    telegram_enabled: bool = True
    telegram_allowed_chat_ids: List[int] = []
    bot_username: str = ""
    log_rotation_hours: Optional[int] = None

@lru_cache()
def get_settings() -> AppSetting:
    core = TradingBotConfig()

    admin_ids = _parse_int_list(os.getenv("TELEGRAM_CHAT_IDS", 'FLASK_PORT'))
    backend_base_url = f"http://127.0.0.1:5000"
    telegram_enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() in ("1", "true", "yes")
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
    log_rotation_hours = int(os.getenv("LOG_ROTATION_HOURS", "24"))

    if os.getenv("LOG_LEVEL"):
        core.logging.level = os.getenv("LOG_LEVEL", "")
    if os.getenv("LOG_FILE_PATH"):
        core.logging.file = os.getenv("LOG_FILE_PATH", "")
    if os.getenv("LOG_BACKUP_COUNT"):
        core.logging.backup_count = int(os.getenv("LOG_BACKUP_COUNT", ""))
    if os.getenv("LOG_MAX_FILE_SIZE"):
        core.logging.max_size = os.getenv("LOG_MAX_FILE_SIZE", "")

    return AppSetting(
        core=core,
        backend_base_url=backend_base_url,
        telegram_enabled=telegram_enabled,
        telegram_allowed_chat_ids=admin_ids,
        bot_username=bot_username,
        log_rotation_hours=log_rotation_hours
    )

