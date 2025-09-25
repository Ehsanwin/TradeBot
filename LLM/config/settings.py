from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel
import dotenv

from .setting_schema import LLMTradingConfig

dotenv.load_dotenv()

class LLMSettings(BaseModel):
    """LLM Trading Analysis settings wrapper"""
    
    core: LLMTradingConfig
    environment: str = "development"
    
    # Flask/API settings if needed
    flask_host: str = "0.0.0.0"
    flask_port: int = 5001
    flask_debug: bool = False
    
    # Override specific settings from environment
    @property
    def openai_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY") or self.core.openai.api_key
    
    @property
    def backend_base_url(self) -> str:
        return os.getenv("TRADEBOT_API_BASE_URL", self.core.data_sources.base_url)

@lru_cache()
def get_llm_settings() -> LLMSettings:
    """Get cached LLM settings instance"""
    
    core = LLMTradingConfig()
    
    # Override environment-specific settings
    environment = os.getenv("ENVIRONMENT", "development")
    flask_host = os.getenv("LLM_FLASK_HOST", "0.0.0.0")
    flask_port = int(os.getenv("LLM_FLASK_PORT", "5001"))
    flask_debug = (os.getenv("LLM_FLASK_DEBUG", "false").lower() in ("1", "true", "yes"))
    
    # Override OpenAI settings from env if present
    if os.getenv("OPENAI_API_KEY"):
        core.openai.api_key = os.getenv("OPENAI_API_KEY")
    if os.getenv("OPENAI_MODEL"):
        core.openai.model = os.getenv("OPENAI_MODEL")
    if os.getenv("OPENAI_MAX_TOKENS"):
        core.openai.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS"))
    if os.getenv("OPENAI_TEMPERATURE"):
        core.openai.temperature = float(os.getenv("OPENAI_TEMPERATURE"))
    
    # Override data source URL from env if present  
    if os.getenv("TRADEBOT_API_BASE_URL"):
        core.data_sources.base_url = os.getenv("TRADEBOT_API_BASE_URL")
    
    # Override analysis settings
    if os.getenv("LLM_DEFAULT_SYMBOLS"):
        symbols = [s.strip() for s in os.getenv("LLM_DEFAULT_SYMBOLS").split(",") if s.strip()]
        if symbols:
            core.analysis.default_symbols = symbols
    
    if os.getenv("LLM_ANALYSIS_DAYS"):
        core.analysis.analysis_days = int(os.getenv("LLM_ANALYSIS_DAYS"))
    
    if os.getenv("LLM_NEWS_LOOKBACK_HOURS"):
        core.analysis.news_lookback_hours = int(os.getenv("LLM_NEWS_LOOKBACK_HOURS"))
    
    # Override system settings
    if os.getenv("LLM_ENABLED"):
        core.enabled = (os.getenv("LLM_ENABLED").lower() in ("1", "true", "yes"))
    
    if os.getenv("LLM_DEBUG"):
        core.debug_mode = (os.getenv("LLM_DEBUG").lower() in ("1", "true", "yes"))
    
    if os.getenv("LLM_LOG_LEVEL"):
        core.log_level = os.getenv("LLM_LOG_LEVEL")
    
    return LLMSettings(
        core=core,
        environment=environment,
        flask_host=flask_host,
        flask_port=flask_port,
        flask_debug=flask_debug
    )
