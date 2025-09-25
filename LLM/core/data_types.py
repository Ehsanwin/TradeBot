from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell" 
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class NewsImportance(Enum):
    """News importance levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class ForexQuote:
    """Normalized forex quote data"""
    symbol: str
    name: str
    current_price: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ForexQuote':
        """Create ForexQuote from TradeBot API response"""
        quote_data = data.get('quote', {})
        return cls(
            symbol=data.get('symbol', ''),
            name=data.get('name', data.get('symbol', '')),
            current_price=quote_data.get('c', 0.0),
            open_price=quote_data.get('o'),
            high_price=quote_data.get('h'), 
            low_price=quote_data.get('l'),
            previous_close=quote_data.get('pc'),
            change=quote_data.get('d'),
            change_percent=quote_data.get('dp'),
            timestamp=datetime.now()
        )

@dataclass
class TechnicalLevel:
    """Support or resistance level"""
    level: float
    strength: float  # 0-1 scale
    touches: int
    level_type: str  # "support" or "resistance"

@dataclass
class PatternPoint:
    """Pattern recognition point"""
    symbol: str
    pattern_type: str
    confidence: float
    timestamp: Optional[datetime] = None
    description: Optional[str] = None

@dataclass  
class TechnicalAnalysis:
    """Normalized technical analysis data"""
    symbol: str
    timeframe: str
    current_price: Optional[float] = None
    
    # Support/Resistance
    support_levels: List[TechnicalLevel] = None
    resistance_levels: List[TechnicalLevel] = None
    nearest_support: Optional[Dict[str, Any]] = None
    nearest_resistance: Optional[Dict[str, Any]] = None
    
    # Patterns
    patterns: List[PatternPoint] = None
    pattern_count: int = 0
    
    # Analysis metadata
    analysis_period_start: Optional[datetime] = None
    analysis_period_end: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.support_levels is None:
            self.support_levels = []
        if self.resistance_levels is None:
            self.resistance_levels = []
        if self.patterns is None:
            self.patterns = []
            
    @classmethod
    def from_api_response(cls, symbol: str, data: Dict[str, Any]) -> 'TechnicalAnalysis':
        """Create TechnicalAnalysis from TradeBot API response"""
        sr_data = data.get('support_resistance', {})
        pattern_data = data.get('patterns', {})
        
        # Parse support levels
        support_levels = []
        for level in sr_data.get('support', []):
            support_levels.append(TechnicalLevel(
                level=level,
                strength=0.7,  # Default strength
                touches=1,     # Would need more data to calculate
                level_type="support"
            ))
        
        # Parse resistance levels
        resistance_levels = []
        for level in sr_data.get('resistance', []):
            resistance_levels.append(TechnicalLevel(
                level=level,
                strength=0.7,  # Default strength
                touches=1,     # Would need more data to calculate
                level_type="resistance"
            ))
        
        # Parse patterns
        patterns = []
        api_patterns = pattern_data.get('points', [])
        fallback_patterns = pattern_data.get('fallback_patterns', {}).get('points', [])
        
        for pattern in api_patterns + fallback_patterns:
            patterns.append(PatternPoint(
                symbol=symbol,
                pattern_type=pattern.get('patternname', 'unknown'),
                confidence=pattern.get('confidence', 0.5),
                description=pattern.get('description')
            ))
        
        return cls(
            symbol=symbol,
            timeframe=data.get('resolution', 'D'),
            current_price=data.get('current_price'),
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            nearest_support=data.get('nearest_levels', {}).get('nearest_support'),
            nearest_resistance=data.get('nearest_levels', {}).get('nearest_resistance'),
            patterns=patterns,
            pattern_count=len(patterns),
            timestamp=datetime.now()
        )

@dataclass
class NewsEvent:
    """Normalized news event data"""
    title: str
    source: str
    timestamp: Optional[datetime] = None
    importance: NewsImportance = NewsImportance.MEDIUM
    impact: Optional[str] = None  # "positive", "negative", "neutral"
    affected_currencies: List[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    
    def __post_init__(self):
        if self.affected_currencies is None:
            self.affected_currencies = []
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'NewsEvent':
        """Create NewsEvent from TradeBot API response"""
        timestamp = None
        if data.get('t'):
            try:
                timestamp = datetime.fromtimestamp(data['t'])
            except (ValueError, TypeError):
                pass
        
        importance = NewsImportance.MEDIUM
        if data.get('importance'):
            try:
                importance = NewsImportance(int(data['importance']))
            except (ValueError, TypeError):
                pass
        
        return cls(
            title=data.get('title', ''),
            source=data.get('source', ''),
            timestamp=timestamp,
            importance=importance,
            description=data.get('description'),
            url=data.get('url')
        )

@dataclass
class MarketData:
    """Combined market data for analysis"""
    symbol: str
    forex_quote: Optional[ForexQuote] = None
    technical_analysis: Optional[TechnicalAnalysis] = None
    related_news: List[NewsEvent] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.related_news is None:
            self.related_news = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TradingSignal:
    """Trading signal generated by LLM analysis"""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0-1 scale
    
    # Price targets
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Analysis reasoning
    reasoning: Optional[str] = None
    key_factors: List[str] = None
    risks: List[str] = None
    
    # Metadata
    timeframe: Optional[str] = None
    timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.key_factors is None:
            self.key_factors = []
        if self.risks is None:
            self.risks = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass  
class MarketReport:
    """Market analysis report generated by LLM"""
    title: str
    summary: str
    content: str
    
    # Analysis components
    technical_summary: Optional[str] = None
    news_summary: Optional[str] = None
    trading_signals: List[TradingSignal] = None
    risk_assessment: Optional[str] = None
    
    # Market outlook
    market_bias: Optional[str] = None  # "bullish", "bearish", "neutral"
    key_levels: Dict[str, List[float]] = None  # symbol -> levels
    
    # Metadata
    symbols_analyzed: List[str] = None
    timestamp: Optional[datetime] = None
    report_type: str = "market_analysis"
    
    def __post_init__(self):
        if self.trading_signals is None:
            self.trading_signals = []
        if self.key_levels is None:
            self.key_levels = {}
        if self.symbols_analyzed is None:
            self.symbols_analyzed = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

# Utility functions for data validation and conversion
def normalize_symbol(symbol: str) -> str:
    """Normalize symbol format (e.g., OANDA:EUR_USD -> EUR_USD)"""
    if ':' in symbol:
        return symbol.split(':', 1)[1]
    return symbol

def extract_currencies_from_symbol(symbol: str) -> List[str]:
    """Extract currency codes from symbol (e.g., EUR_USD -> ['EUR', 'USD'])"""
    normalized = normalize_symbol(symbol)
    
    # Common forex pairs
    if '_' in normalized:
        return normalized.split('_')
    elif len(normalized) == 6:
        return [normalized[:3], normalized[3:]]
    elif normalized.startswith('XAU'):
        return ['XAU', normalized[3:]]  # Gold pairs
    elif normalized.startswith('XAG'):
        return ['XAG', normalized[3:]]  # Silver pairs
    
    return [normalized]

def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profit: float) -> Optional[float]:
    """Calculate risk-reward ratio for a trade"""
    if not all([entry, stop_loss, take_profit]):
        return None
    
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    
    if risk == 0:
        return None
    
    return reward / risk
