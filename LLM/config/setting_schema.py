from __future__ import annotations

import os
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import dotenv

dotenv.load_dotenv()

class OpenAIConfig(BaseModel):
    """OpenAI/ChatGPT API configuration schema"""
    
    api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY"), description="OpenAI API key")
    api_base: str = Field(default="https://api.openai.com/v1", description="OpenAI API base URL")
    model: str = Field(default="gpt-4o-mini", description="ChatGPT model to use")
    max_tokens: int = Field(default=2000, description="Maximum tokens for response")
    temperature: float = Field(default=0.7, description="Model temperature (0-2)")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retry attempts")
    backoff: float = Field(default=1.0, description="Exponential backoff base (seconds)")

class DataSourceConfig(BaseModel):
    """Configuration for data sources API endpoints"""
    
    base_url: str = Field(default="http://127.0.0.1:5000", description="Base URL for TradeBot API")
    
    # Forex endpoints
    forex_quote_endpoint: str = Field(default="/api/v1/forex/quote", description="Forex quote endpoint")
    forex_symbols_endpoint: str = Field(default="/api/v1/forex/symbols", description="Forex symbols endpoint")
    forex_candles_endpoint: str = Field(default="/api/v1/forex/candles", description="Forex candles endpoint")
    
    # Technical analysis endpoints  
    technical_analysis_endpoint: str = Field(default="/api/v1/technical/analysis", description="Combined technical analysis endpoint")
    support_resistance_endpoint: str = Field(default="/api/v1/technical/support-resistance", description="Support/resistance endpoint")
    patterns_endpoint: str = Field(default="/api/v1/technical/patterns", description="Pattern recognition endpoint")
    
    # News endpoints
    news_fetch_endpoint: str = Field(default="/api/v1/news/fetch", description="News fetch endpoint")
    news_list_endpoint: str = Field(default="/api/v1/news/list", description="News list endpoint")
    
    # Request settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retry attempts")

class TradingAnalysisConfig(BaseModel):
    """Configuration for trading analysis parameters"""
    
    # Symbols to analyze
    default_symbols: List[str] = Field(default=["OANDA:EUR_USD", "OANDA:GBP_USD", "OANDA:USD_JPY", "OANDA:AUD_USD", "OANDA:XAU_USD"], description="Default symbols for analysis")
    
    # Timeframes for analysis
    primary_timeframe: str = Field(default="15", description="Primary timeframe for analysis")
    secondary_timeframes: List[str] = Field(default=["5", "60"], description="Additional timeframes to consider")
    
    # Technical analysis parameters
    analysis_days: int = Field(default=30, description="Days of historical data for analysis")
    pattern_days: int = Field(default=14, description="Days for pattern recognition")
    
    # News analysis parameters
    news_lookback_hours: int = Field(default=24, description="Hours to look back for news")
    news_importance_threshold: int = Field(default=2, description="Minimum news importance level (1-3)")
    
    # Signal generation
    signal_confidence_threshold: float = Field(default=0.6, description="Minimum confidence for signal generation")
    max_concurrent_signals: int = Field(default=5, description="Maximum concurrent trading signals")

class ReportingConfig(BaseModel):
    """Configuration for market reporting and analysis"""
    
    # Report generation
    auto_generate_reports: bool = Field(default=True, description="Automatically generate market reports")
    report_interval_minutes: int = Field(default=60, description="Interval between reports in minutes")
    
    # Report content
    include_technical_summary: bool = Field(default=True, description="Include technical analysis in reports")
    include_news_summary: bool = Field(default=True, description="Include news analysis in reports")
    include_trading_signals: bool = Field(default=True, description="Include trading signals in reports")
    include_risk_assessment: bool = Field(default=True, description="Include risk assessment in reports")
    
    # Output settings
    max_report_length: int = Field(default=1500, description="Maximum report length in characters")
    report_format: str = Field(default="markdown", description="Report output format (markdown, text, html)")

class LLMTradingConfig(BaseModel):
    """Main LLM Trading Analysis configuration schema"""
    
    # Core configurations
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    data_sources: DataSourceConfig = Field(default_factory=DataSourceConfig) 
    analysis: TradingAnalysisConfig = Field(default_factory=TradingAnalysisConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    
    # System settings
    enabled: bool = Field(default=True, description="Enable LLM trading analysis")
    debug_mode: bool = Field(default=False, description="Enable debug logging")
    cache_duration_minutes: int = Field(default=5, description="Cache duration for API responses")
    max_concurrent_requests: int = Field(default=3, description="Maximum concurrent API requests")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/llm_trading.log", description="Log file path")
    
    def __init__(self, **data):
        super().__init__(**data)
