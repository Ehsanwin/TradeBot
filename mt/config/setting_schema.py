from __future__ import annotations

import os
from typing import List, Optional
from pydantic import BaseModel, Field
import dotenv

dotenv.load_dotenv()

class MT5ConnectionConfig(BaseModel):
    """MetaTrader 5 connection configuration"""
    login: int = Field(description="MT5 account login number")
    password: str = Field(description="MT5 account password")
    server: str = Field(description="MT5 server name")
    timeout: int = Field(default=30000, description="Connection timeout in milliseconds")
    retries: int = Field(default=3, description="Connection retry attempts")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")
    path: Optional[str] = Field(default=None, description="MT5 terminal path (auto-detect if None)")

class MT5TradingConfig(BaseModel):
    """MetaTrader 5 trading configuration"""
    magic_number: int = Field(default=234001, description="Magic number for trades")
    default_symbols: List[str] = Field(default=["XAUUSD", "EURUSD", "GBPUSD"], description="Default trading symbols")
    default_volume: float = Field(default=0.01, description="Default trade volume")
    max_slippage: int = Field(default=20, description="Maximum allowed slippage in points")
    max_spread: int = Field(default=50, description="Maximum allowed spread in points")
    
    # Risk Management
    max_risk_percent: float = Field(default=2.0, description="Maximum risk per trade (%)")
    min_risk_reward: float = Field(default=1.5, description="Minimum risk-reward ratio")
    max_positions: int = Field(default=3, description="Maximum concurrent positions")
    max_daily_loss: float = Field(default=5.0, description="Maximum daily loss (%)")
    
    # Trade Management
    partial_close_percent: float = Field(default=50.0, description="Percentage to close at first target")
    trailing_stop_points: int = Field(default=200, description="Trailing stop distance in points")
    break_even_points: int = Field(default=100, description="Break even trigger distance in points")

class LLMIntegrationConfig(BaseModel):
    """LLM integration configuration"""
    api_base_url: str = Field(default="http://localhost:5001", description="LLM API base URL")
    analysis_interval_minutes: int = Field(default=15, description="Analysis interval in minutes")
    signal_expiry_minutes: int = Field(default=60, description="Signal expiry time in minutes")
    min_confidence_threshold: float = Field(default=0.7, description="Minimum signal confidence to trade")
    allowed_signal_types: List[str] = Field(default=["BUY", "SELL"], description="Allowed signal types")
    timeout: int = Field(default=30, description="API request timeout in seconds")
    retries: int = Field(default=3, description="API request retries")

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Logging level")
    file: str = Field(default="logs/mt5_trading.log", description="Log file path")
    max_size: str = Field(default="10MB", description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    console_output: bool = Field(default=True, description="Enable console output")
    file_output: bool = Field(default=True, description="Enable file output")

class MT5TradingSystemConfig(BaseModel):
    """Main MT5 Trading System configuration"""
    
    # Core configurations
    connection: MT5ConnectionConfig = Field(
        default_factory=lambda: MT5ConnectionConfig(
            path=os.getenv("MT5_PATH", ""),
            login=int(os.getenv("MT5_LOGIN", "0")),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "")
        )
    )
    
    trading: MT5TradingConfig = Field(default_factory=MT5TradingConfig)
    llm: LLMIntegrationConfig = Field(default_factory=LLMIntegrationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # System settings
    enabled: bool = Field(default=True, description="Enable MT5 trading system")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    dry_run: bool = Field(default=False, description="Enable dry run mode (no actual trades)")
    auto_trade: bool = Field(default=True, description="Enable automatic trading")
    health_check_interval: int = Field(default=60, description="Health check interval in seconds")

    def __init__(self, **data):
        super().__init__(**data)
        
        # Override from environment variables
        if os.getenv("MT5_MAGIC_NUMBER"):
            self.trading.magic_number = int(os.getenv("MT5_MAGIC_NUMBER"))
        
        if os.getenv("MT5_DEFAULT_SYMBOLS"):
            symbols = [s.strip() for s in os.getenv("MT5_DEFAULT_SYMBOLS").split(",") if s.strip()]
            if symbols:
                self.trading.default_symbols = symbols
        
        if os.getenv("MT5_DEFAULT_VOLUME"):
            self.trading.default_volume = float(os.getenv("MT5_DEFAULT_VOLUME"))
        
        if os.getenv("MT5_MAX_SLIPPAGE"):
            self.trading.max_slippage = int(os.getenv("MT5_MAX_SLIPPAGE"))
        
        if os.getenv("MT5_MAX_SPREAD"):
            self.trading.max_spread = int(os.getenv("MT5_MAX_SPREAD"))
        
        if os.getenv("MT5_MAX_RISK_PERCENT"):
            self.trading.max_risk_percent = float(os.getenv("MT5_MAX_RISK_PERCENT"))
        
        if os.getenv("MT5_MIN_RISK_REWARD"):
            self.trading.min_risk_reward = float(os.getenv("MT5_MIN_RISK_REWARD"))
        
        if os.getenv("MT5_MAX_POSITIONS"):
            self.trading.max_positions = int(os.getenv("MT5_MAX_POSITIONS"))
        
        if os.getenv("LLM_API_BASE_URL"):
            self.llm.api_base_url = os.getenv("LLM_API_BASE_URL")
        
        if os.getenv("LLM_ANALYSIS_INTERVAL_MINUTES"):
            self.llm.analysis_interval_minutes = int(os.getenv("LLM_ANALYSIS_INTERVAL_MINUTES"))
        
        if os.getenv("LLM_SIGNAL_EXPIRY_MINUTES"):
            self.llm.signal_expiry_minutes = int(os.getenv("LLM_SIGNAL_EXPIRY_MINUTES"))
        
        if os.getenv("MT5_ENABLED"):
            self.enabled = os.getenv("MT5_ENABLED").lower() in ("1", "true", "yes")
        
        if os.getenv("MT5_DEBUG"):
            self.debug_mode = os.getenv("MT5_DEBUG").lower() in ("1", "true", "yes")
        
        if os.getenv("MT5_LOG_LEVEL"):
            self.logging.level = os.getenv("MT5_LOG_LEVEL")
