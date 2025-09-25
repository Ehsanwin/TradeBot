from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .openai_client import OpenAIHTTPClient, ChatMessage, create_system_prompt
from .data_types import (
    MarketData, TradingSignal, SignalType, SignalStrength,
    NewsEvent, TechnicalAnalysis, ForexQuote
)

logger = logging.getLogger(__name__)

class FastSignalGenerator:
    """Fast signal generator with parallel processing and optimized prompts"""
    
    def __init__(
        self,
        openai_client: OpenAIHTTPClient,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1000,  # Reduced tokens for faster response
        temperature: float = 0.2,  # Lower temperature for faster, more consistent responses
        confidence_threshold: float = 0.6,
        max_workers: int = 3  # Parallel processing
    ):
        self.openai_client = openai_client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.confidence_threshold = confidence_threshold
        self.max_workers = max_workers
    
    def _create_fast_analysis_prompt(self, market_data: MarketData) -> List[ChatMessage]:
        """Create optimized, shorter prompt for faster analysis"""
        
        system_prompt = create_system_prompt(
            "trading_analyst",
            "Analyze market data quickly and provide a concise trading signal. "
            "Focus on the most important factors only. Be decisive and brief."
        )
        
        # Build concise market summary
        sections = [f"QUICK ANALYSIS: {market_data.symbol}"]
        
        # Current price (essential)
        if market_data.forex_quote:
            quote = market_data.forex_quote
            change_dir = "↗️" if (quote.change or 0) >= 0 else "↘️"
            sections.append(f"Price: {quote.current_price} {change_dir} {quote.change_percent:.1f}%" if quote.change_percent else f"Price: {quote.current_price}")
        
        # Key technical levels (top 2 only)
        if market_data.technical_analysis:
            ta = market_data.technical_analysis
            
            if ta.nearest_support:
                sections.append(f"Support: {ta.nearest_support['level']:.5f} ({ta.nearest_support['distance_percentage']:.1f}% away)")
            
            if ta.nearest_resistance:
                sections.append(f"Resistance: {ta.nearest_resistance['level']:.5f} ({ta.nearest_resistance['distance_percentage']:.1f}% away)")
            
            # Top patterns only
            if ta.patterns:
                top_patterns = [p.pattern_type for p in ta.patterns[:2] if hasattr(p, 'pattern_type')]
                if top_patterns:
                    sections.append(f"Patterns: {', '.join(top_patterns)}")
        
        # High impact news only
        if market_data.related_news:
            high_impact = [n for n in market_data.related_news if n.importance.value >= 3]
            if high_impact:
                sections.append(f"High Impact News: {high_impact[0].title[:50]}...")
        
        market_data_text = "\n".join(sections)
        
        # Simplified prompt for speed
        user_prompt = f"""
{market_data_text}

Provide FAST trading signal in JSON:
{{
    "signal": "buy|sell|hold",
    "strength": "weak|moderate|strong", 
    "confidence": 0.75,
    "entry": 1.2345,
    "stop": 1.2300,
    "target": 1.2400,
    "reason": "Brief explanation (max 50 words)",
    "factors": ["Factor 1", "Factor 2"],
    "risks": ["Risk 1"]
}}

Requirements:
- Only suggest buy/sell if confidence > 70%
- Otherwise recommend hold
- Keep reasoning under 50 words
- Max 2 factors, 1 risk
- Be decisive and quick
"""
        
        return [
            system_prompt,
            ChatMessage(role="user", content=user_prompt)
        ]
    
    def _parse_fast_signal_response(self, content: str, symbol: str) -> Optional[TradingSignal]:
        """Parse fast signal response"""
        
        try:
            # Extract JSON from response
            content = content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error(f"No JSON found in fast signal response for {symbol}")
                return None
            
            json_str = content[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Parse signal type
            signal_type_str = data.get('signal', 'hold').lower()
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
                entry_price=data.get('entry'),
                stop_loss=data.get('stop'),
                take_profit=data.get('target'),
                reasoning=data.get('reason'),
                key_factors=data.get('factors', [])[:2],  # Max 2
                risks=data.get('risks', [])[:1],  # Max 1
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=12)  # Shorter expiry
            )
            
            return signal
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from fast signal response for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse fast signal response for {symbol}: {e}")
            return None
    
    def generate_signal_fast(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Generate a single trading signal quickly"""
        
        if not market_data.symbol:
            logger.error("Market data missing symbol")
            return None
        
        try:
            logger.debug(f"Fast signal generation for {market_data.symbol}")
            
            # Create optimized prompt
            messages = self._create_fast_analysis_prompt(market_data)
            
            # Get ChatGPT response (remove problematic parameters)
            response = self.openai_client.chat_completion(
                messages=messages,
                model=self.model
            )
            
            # Parse response into signal
            signal = self._parse_fast_signal_response(response.content, market_data.symbol)
            
            if signal:
                # Apply confidence threshold
                if signal.confidence < self.confidence_threshold:
                    logger.debug(f"Signal for {market_data.symbol} below confidence threshold "
                              f"({signal.confidence:.2f} < {self.confidence_threshold}), "
                              f"converting to HOLD")
                    signal.signal_type = SignalType.HOLD
                    signal.reasoning = f"Low confidence ({signal.confidence:.2f}). " + (signal.reasoning or "")
                
                logger.info(f"Fast {signal.signal_type.value} signal for {market_data.symbol} "
                          f"(confidence: {signal.confidence:.2f})")
                return signal
            else:
                logger.warning(f"Failed to parse fast signal for {market_data.symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate fast signal for {market_data.symbol}: {e}")
            return None
    
    def generate_signals_parallel(self, market_data_list: List[MarketData]) -> List[TradingSignal]:
        """Generate trading signals in parallel for speed"""
        
        logger.info(f"Generating fast signals for {len(market_data_list)} symbols (parallel)")
        
        def generate_single_signal(market_data: MarketData) -> Optional[TradingSignal]:
            """Generate signal for single market data"""
            return self.generate_signal_fast(market_data)
        
        signals = []
        max_workers = min(self.max_workers, len(market_data_list))
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_data = {
                executor.submit(generate_single_signal, data): data 
                for data in market_data_list
            }
            
            for future in as_completed(future_to_data):
                market_data = future_to_data[future]
                try:
                    signal = future.result(timeout=15)  # 15s timeout per signal
                    if signal:
                        signals.append(signal)
                        logger.debug(f"Generated signal for {signal.symbol}")
                    else:
                        logger.warning(f"No signal for {market_data.symbol}")
                except Exception as e:
                    logger.error(f"Signal generation failed for {market_data.symbol}: {e}")
        
        logger.info(f"Generated {len(signals)} signals in parallel")
        
        # Sort by confidence and strength
        signals.sort(key=lambda s: (s.confidence, s.strength.value), reverse=True)
        
        return signals
    
    def filter_actionable_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Filter signals to only include actionable ones (buy/sell)"""
        
        actionable = [s for s in signals if s.signal_type in [SignalType.BUY, SignalType.SELL]]
        logger.info(f"Found {len(actionable)} actionable signals out of {len(signals)} total")
        
        return actionable
