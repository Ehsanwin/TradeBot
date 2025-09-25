from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel
import dotenv

from .setting_schema import MT5TradingSystemConfig

# Load environment variables from mt/.env
mt_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
dotenv.load_dotenv(mt_env_path)

# Also load from root .env if exists
root_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(root_env_path):
    dotenv.load_dotenv(root_env_path)

class MT5Settings(BaseModel):
    """MT5 Trading System settings wrapper"""
    
    core: MT5TradingSystemConfig
    environment: str = "development"
    
    # Runtime overrides
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def connection_valid(self) -> bool:
        """Check if connection settings are valid"""
        return (
            self.core.connection.login > 0 and
            bool(self.core.connection.password) and
            bool(self.core.connection.server)
        )

@lru_cache()
def get_mt5_settings() -> MT5Settings:
    """Get cached MT5 settings instance"""
    
    core = MT5TradingSystemConfig()
    environment = os.getenv("ENVIRONMENT", "development")
    
    return MT5Settings(
        core=core,
        environment=environment
    )

def validate_settings() -> tuple[bool, str]:
    """Validate MT5 settings and return (is_valid, error_message)"""
    try:
        settings = get_mt5_settings()
        
        if not settings.core.enabled:
            return False, "MT5 trading system is disabled"
        
        if not settings.connection_valid:
            return False, "Invalid MT5 connection settings (login, password, server required)"
        
        if settings.core.trading.max_risk_percent <= 0:
            return False, "Invalid risk percentage"
        
        if settings.core.trading.min_risk_reward <= 0:
            return False, "Invalid risk-reward ratio"
        
        if settings.core.trading.default_volume <= 0:
            return False, "Invalid default volume"
        
        if not settings.core.trading.default_symbols:
            return False, "No default symbols configured"
        
        return True, "Settings validation successful"
        
    except Exception as e:
        return False, f"Settings validation error: {e}"
