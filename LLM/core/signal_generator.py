from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .openai_client import OpenAIHTTPClient, ChatMessage, create_system_prompt
from .data_types import (
    MarketData, TradingSignal, SignalType, SignalStrength,
    NewsEvent, TechnicalAnalysis, ForexQuote
)

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Generates trading signals using ChatGPT analysis of market data"""
    
    def __init__(
        self,
        openai_client: OpenAIHTTPClient,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2000,
        temperature: float = 0.3,  # Lower temperature for more consistent analysis
        confidence_threshold: float = 0.6
    ):
        self.openai_client = openai_client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.confidence_threshold = confidence_threshold
    
    def _format_market_data_for_prompt(self, market_data: MarketData) -> str:
        """Format market data into a structured prompt for ChatGPT"""
        
        sections = [f"MARKET DATA ANALYSIS FOR {market_data.symbol}"]
        sections.append("=" * 50)
        
        # Forex Quote Section
        if market_data.forex_quote:
            quote = market_data.forex_quote
            sections.append("\n📈 CURRENT PRICE DATA:")
            sections.append(f"Symbol: {quote.name} ({quote.symbol})")
            sections.append(f"Current Price: {quote.current_price}")
            
            if quote.change and quote.change_percent:
                change_direction = "📈" if quote.change > 0 else "📉"
                sections.append(f"Daily Change: {quote.change} ({quote.change_percent:.2f}%) {change_direction}")
            
            if quote.high_price and quote.low_price:
                sections.append(f"Daily Range: {quote.low_price} - {quote.high_price}")
        
        # Technical Analysis Section
        if market_data.technical_analysis:
            ta = market_data.technical_analysis
            sections.append("\n🔍 TECHNICAL ANALYSIS:")
            
            # Support/Resistance
            if ta.support_levels:
                support_levels = [f"{level.level:.5f}" for level in ta.support_levels[:3]]  # Top 3
                sections.append(f"Key Support Levels: {', '.join(support_levels)}")
            
            if ta.resistance_levels:
                resistance_levels = [f"{level.level:.5f}" for level in ta.resistance_levels[:3]]  # Top 3
                sections.append(f"Key Resistance Levels: {', '.join(resistance_levels)}")
            
            # Nearest levels
            if ta.nearest_support:
                sections.append(f"Nearest Support: {ta.nearest_support['level']:.5f} "
                              f"({ta.nearest_support['distance_percentage']:.2f}% away)")
            
            if ta.nearest_resistance:
                sections.append(f"Nearest Resistance: {ta.nearest_resistance['level']:.5f} "
                              f"({ta.nearest_resistance['distance_percentage']:.2f}% away)")
            
            # Patterns
            if ta.patterns:
                sections.append(f"\nChart Patterns Detected ({len(ta.patterns)}):")
                for pattern in ta.patterns[:5]:  # Top 5 patterns
                    # Safely format confidence to avoid string formatting errors
                    try:
                        if pattern.confidence and isinstance(pattern.confidence, (int, float)):
                            confidence_str = f"{float(pattern.confidence):.0%}"
                        else:
                            confidence_str = "N/A"
                    except (ValueError, TypeError):
                        confidence_str = "N/A"
                    sections.append(f"- {pattern.pattern_type} (Confidence: {confidence_str})")
        
        # News Analysis Section
        if market_data.related_news:
            sections.append(f"\n📰 RECENT NEWS ({len(market_data.related_news)} events):")
            
            # Sort news by importance and timestamp
            sorted_news = sorted(
                market_data.related_news,
                key=lambda x: (x.importance.value, x.timestamp or datetime.min),
                reverse=True
            )
            
            for news in sorted_news[:5]:  # Top 5 news items
                importance_emoji = "🔴" if news.importance.value >= 3 else "🟡" if news.importance.value >= 2 else "⚪"
                time_str = news.timestamp.strftime("%m-%d %H:%M") if news.timestamp else "Unknown"
                sections.append(f"{importance_emoji} [{time_str}] {news.title}")
                if news.description and len(news.description) < 150:
                    sections.append(f"   └─ {news.description}")
        
        return "\n".join(sections)
    
    def _create_signal_analysis_prompt(self, market_data: MarketData) -> List[ChatMessage]:
        """Create chat messages for signal analysis"""
        
        system_prompt = create_system_prompt(
            "trading_analyst",
            "You will analyze forex market data and provide a structured trading signal. "
            "Focus on actionable insights based on technical levels, patterns, and news impact. "
            "Be conservative and risk-aware in your recommendations."
        )
        
        market_data_text = self._format_market_data_for_prompt(market_data)
        
        user_prompt = f"""
{market_data_text}

Based on this market data, provide a trading analysis and signal in the following JSON format:

{{
    "signal_type": "buy|sell|hold|close_long|close_short",
    "strength": "weak|moderate|strong|very_strong",
    "confidence": 0.75,
    "entry_price": 1.2345,
    "stop_loss": 1.2300,
    "take_profit": 1.2400,
    "reasoning": "Brief explanation of the signal rationale",
    "key_factors": [
        "List of key technical and fundamental factors",
        "supporting this signal"
    ],
    "risks": [
        "List of key risks and potential",
        "scenarios that could invalidate the signal"
    ],
    "timeframe": "suggested timeframe for this trade"
}}

IMPORTANT:
- Only suggest entry if there's a clear, high-probability setup
- If uncertain, recommend "hold" and explain why
- Consider risk-reward ratio (minimum 1:2)
- Factor in both technical and news analysis
- Be specific about entry, stop loss, and take profit levels
- Keep reasoning concise but comprehensive
"""
        
        return [
            system_prompt,
            ChatMessage(role="user", content=user_prompt)
        ]
    
    def _parse_signal_response(self, content: str, symbol: str) -> Optional[TradingSignal]:
        """Parse ChatGPT response into TradingSignal object"""
        
        try:
            # Extract JSON from response
            content = content.strip()
            
            # Find JSON block in response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in signal response")
                return None
            
            json_str = content[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Parse signal type
            signal_type_str = data.get('signal_type', 'hold').lower()
            try:
                signal_type = SignalType(signal_type_str)
            except ValueError:
                logger.warning(f"Invalid signal type: {signal_type_str}, defaulting to HOLD")
                signal_type = SignalType.HOLD
            
            # Parse signal strength
            strength_str = data.get('strength', 'moderate').lower()
            try:
                strength = SignalStrength(strength_str)
            except ValueError:
                logger.warning(f"Invalid signal strength: {strength_str}, defaulting to MODERATE")
                strength = SignalStrength.MODERATE
            
            # Parse confidence
            confidence = float(data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
            
            # Create signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                entry_price=data.get('entry_price'),
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                reasoning=data.get('reasoning'),
                key_factors=data.get('key_factors', []),
                risks=data.get('risks', []),
                timeframe=data.get('timeframe'),
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)  # Default 24h expiry
            )
            
            return signal
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from signal response: {e}")
            logger.debug(f"Response content: {content}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse signal response: {e}")
            return None
    
    def generate_signal(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Generate a single trading signal for market data"""
        
        if not market_data.symbol:
            logger.error("Market data missing symbol")
            return None
        
        try:
            logger.info(f"Generating signal for {market_data.symbol}")
            
            # Create prompt
            messages = self._create_signal_analysis_prompt(market_data)
            
            # Get ChatGPT response (remove problematic parameters)
            response = self.openai_client.chat_completion(
                messages=messages,
                model=self.model
            )
            
            logger.debug(f"ChatGPT response for {market_data.symbol}: {response.content[:200]}...")
            
            # Parse response into signal
            signal = self._parse_signal_response(response.content, market_data.symbol)
            
            if signal:
                # Apply confidence threshold
                if signal.confidence < self.confidence_threshold:
                    logger.info(f"Signal for {market_data.symbol} below confidence threshold "
                              f"({signal.confidence:.2f} < {self.confidence_threshold}), "
                              f"converting to HOLD")
                    signal.signal_type = SignalType.HOLD
                    signal.reasoning = (f"Low confidence ({signal.confidence:.2f}). " + 
                                      (signal.reasoning or ""))
                
                logger.info(f"Generated {signal.signal_type.value} signal for {market_data.symbol} "
                          f"(confidence: {signal.confidence:.2f}, strength: {signal.strength.value})")
                return signal
            else:
                logger.warning(f"Failed to parse signal for {market_data.symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate signal for {market_data.symbol}: {e}")
            return None
    
    def generate_signals(self, market_data_list: List[MarketData]) -> List[TradingSignal]:
        """Generate trading signals for multiple symbols"""
        
        logger.info(f"Generating signals for {len(market_data_list)} symbols")
        
        signals = []
        for market_data in market_data_list:
            try:
                signal = self.generate_signal(market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Failed to generate signal for {market_data.symbol}: {e}")
                continue
        
        logger.info(f"Generated {len(signals)} signals")
        
        # Sort by confidence and strength
        signals.sort(key=lambda s: (s.confidence, s.strength.value), reverse=True)
        
        return signals
    
    def filter_actionable_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Filter signals to only include actionable ones (buy/sell)"""
        
        actionable = [s for s in signals if s.signal_type in [SignalType.BUY, SignalType.SELL]]
        logger.info(f"Found {len(actionable)} actionable signals out of {len(signals)} total")
        
        return actionable
