from __future__ import annotations

import os
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import dotenv

dotenv.load_dotenv()

PYDANTIC_AVAILABLE = True

class DatabaseConfig(BaseModel):
    """Database configuration schema"""
    host: str = Field(default="postgres", description="Database host")
    port: int = Field(default=5432, description="Database port")
    user: str = Field(default="trading_bot", description="Database user")
    password: str = Field(description="Database password")
    database: str = Field(default="trading_db", description="Database name")
    
    # Connection pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle seconds")

    @property
    def url(self) -> str:
        """Build database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

class LoggingConfig(BaseModel):
    """Logging configuration schema"""
    
    level: str = Field(default="INFO", description="Logging level")
    file: str = Field(default="logs/trading.log", description="Log file path")
    max_size: str = Field(default="10MB", description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    console_output: bool = Field(default=True, description="Enable console output")
    file_output: bool = Field(default=True, description="Enable file output")

class MT5Config(BaseModel):
    """MetaTrader 5 configuration schema"""
    
    login: Optional[int] = Field(None, description="MT5 login number")
    password: Optional[str] = Field(None, description="MT5 password")
    server: Optional[str] = Field(None, description="MT5 server")
    timeout: int = Field(default=30000, description="Connection timeout (ms)")
    retries: int = Field(default=3, description="Connection retry attempts")

class TradingConfig(BaseModel):
    """Trading configuration schema"""
    
    symbols: List[str] = Field(default=["XAUUSD"], description="Trading symbols")
    default_timeframe: str = Field(default="M5", description="Default timeframe")
    max_positions: int = Field(default=3, description="Maximum concurrent positions")
    default_risk_percent: float = Field(default=1.0, description="Default risk percentage")
    max_risk_percent: float = Field(default=2.0, description="Maximum risk percentage")
    min_risk_reward: float = Field(default=1.5, description="Minimum risk-reward ratio")
    magic_number: int = Field(default=234000, description="MT5 magic number")
    max_slippage: int = Field(default=20, description="Maximum slippage (points)")
    max_spread: int = Field(default=50, description="Maximum spread (points)")
    
    # Trading hours
    trading_start: str = Field(default="00:00", description="Trading start time")
    trading_end: str = Field(default="23:59", description="Trading end time")
    timezone: str = Field(default="UTC", description="Trading timezone")

class TelegramConfig(BaseModel):
    """Telegram bot configuration schema"""
    
    bot_token: Optional[str] = Field(None, description="Telegram bot token")
    admin_chat_ids: List[int] = Field(default=[], description="Admin chat IDs")
    notification_level: Optional[str] = Field(default="INFO", description="Notification level")
    command_timeout: Optional[int] = Field(default=30, description="Command timeout seconds")
    max_message_length: Optional[int] = Field(default=4000, description="Maximum message length")

class StrategyConfig(BaseModel):
    """Strategy configuration schema"""
    
    enabled: List[str] = Field(
        default=["al_brooks", "linda_raschke", "ict"], 
        description="Enabled strategies"
    )
    weights: Dict[str, float] = Field(
        default={"al_brooks": 1.0, "linda_raschke": 1.0, "ict": 1.0},
        description="Strategy weights"
    )
    combination_mode: str = Field(default="weighted", description="Signal combination mode")
    signal_threshold: float = Field(default=0.7, description="Minimum signal strength")

class RiskConfig(BaseModel):
    """Risk management configuration schema"""
    max_daily_loss: float = Field(default=5.0, description="Maximum daily loss percentage")
    max_weekly_loss: float = Field(default=10.0, description="Maximum weekly loss percentage")
    max_monthly_loss: float = Field(default=20.0, description="Maximum monthly loss percentage")
    max_drawdown: float = Field(default=15.0, description="Maximum drawdown percentage")
    position_correlation_limit: float = Field(default=0.7, description="Maximum position correlation")
    
    # Emergency stop
    emergency_stop_enabled: bool = Field(default=True, description="Enable emergency stop")
    emergency_loss_threshold: float = Field(default=10.0, description="Emergency stop loss threshold")

class TradingBotConfig(BaseModel):
    """Main trading bot configuration schema"""
    
    # Core configurations
    database: DatabaseConfig = Field(
        default_factory=lambda: DatabaseConfig(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            password=os.getenv("POSTGRES_PASSWORD", "default_password"),
            user=os.getenv("POSTGRES_USER", "default_user")
            )
        )
    
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    mt5: MT5Config = Field(
        default_factory=lambda: MT5Config(
            login=int(os.getenv("MT5_LOGIN", "123456")),
            password=os.getenv("MT5_PASSWORD", "default_password"),
            server=os.getenv("MT5_SERVER", "MetaQuotes-Demo")
            )
        )
    
    trading: TradingConfig = Field(default_factory=TradingConfig)
    telegram: TelegramConfig = Field(default_factory=lambda: TelegramConfig(
        bot_token=os.getenv("TELEGRAM_TOKEN")
    ))

    strategies: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)

    # System settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    auto_restart: bool = Field(default=True, description="Enable auto restart")
    health_check_interval: int = Field(default=60, description="Health check interval seconds")
    data_backup_interval: int = Field(default=3600, description="Data backup interval seconds")

    def __init__(self, **data):
        # This avoids duplication of environment override logic
        super().__init__(**data)
