#!/usr/bin/env python3
"""
Signal Converter - Convert LLM signals to MT5 trading signals

This module handles the conversion between ChatGPT/LLM generated signals
and MetaTrader5 compatible trading signals with proper risk management.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

# Import LLM data types
from LLM.core.data_types import SignalType, SignalStrength

# Import MT5 data types conditionally
try:
    from mt5_api_client import MT5TradeSignal
    # Create a simple MT5TradeRequest class if needed
    class MT5TradeRequest:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    MT5_AVAILABLE = True
except ImportError:
    # Create dummy classes when MT5 is not available
    class MT5TradeSignal:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class MT5TradeRequest:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)

class SignalConverter:
    """Convert LLM signals to MT5 trade signals"""
    
    def __init__(self, risk_percent: float = 1.0, min_confidence: float = 0.7):
        """
        Initialize signal converter
        
        Args:
            risk_percent: Risk percentage per trade (1.0 = 1%)
            min_confidence: Minimum confidence threshold for signal execution
        """
        self.risk_percent = risk_percent
        self.min_confidence = min_confidence
        
        # Symbol mapping: LLM format -> MT5 format
        self.symbol_mapping = {
            'OANDA:EUR_USD': 'EURUSD',
            'OANDA:GBP_USD': 'GBPUSD', 
            'OANDA:USD_JPY': 'USDJPY',
            'OANDA:AUD_USD': 'AUDUSD',
            'OANDA:USD_CHF': 'USDCHF',
            'OANDA:USD_CAD': 'USDCAD',
            'OANDA:NZD_USD': 'NZDUSD',
            'OANDA:XAU_USD': 'XAUUSD',
            'EUR_USD': 'EURUSD',
            'GBP_USD': 'GBPUSD',
            'USD_JPY': 'USDJPY',
            'AUD_USD': 'AUDUSD',
            'USD_CHF': 'USDCHF',
            'USD_CAD': 'USDCAD',
            'NZD_USD': 'NZDUSD',
            'XAU_USD': 'XAUUSD',
            # Direct MT5 symbol mappings (for when LLM outputs direct symbols)
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'USDJPY': 'USDJPY',
            'AUDUSD': 'AUDUSD',
            'USDCHF': 'USDCHF',
            'USDCAD': 'USDCAD',
            'NZDUSD': 'NZDUSD',
            'XAUUSD': 'XAUUSD',
        }
        
        if not MT5_AVAILABLE:
            logger.warning("MT5 not available - signal converter in analysis-only mode")
        
        logger.info(f"Signal Converter initialized - Risk: {risk_percent}%, Min Confidence: {min_confidence}")
    
    def convert_llm_signals(self, llm_signals: List[Dict[str, Any]]) -> List[MT5TradeSignal]:
        """
        Convert LLM signals to MT5 trade signals
        
        Args:
            llm_signals: List of LLM signal dictionaries
            
        Returns:
            List of MT5TradeSignal objects ready for execution
        """
        mt5_signals = []
        
        for signal_data in llm_signals:
            try:
                mt5_signal = self._convert_single_signal(signal_data)
                if mt5_signal:
                    mt5_signals.append(mt5_signal)
            except Exception as e:
                logger.error(f"Failed to convert signal {signal_data.get('symbol', 'unknown')}: {e}")
        
        logger.info(f"Converted {len(mt5_signals)}/{len(llm_signals)} LLM signals to MT5 signals")
        return mt5_signals
    
    def _convert_single_signal(self, signal_data: Dict[str, Any]) -> Optional[MT5TradeSignal]:
        """Convert a single LLM signal to MT5 signal"""
        
        # Extract signal data
        symbol = signal_data.get('symbol', '')
        signal_type = signal_data.get('type', '').upper()
        confidence = self._parse_confidence(signal_data.get('confidence', '0'))
        strength = signal_data.get('strength', '').upper()
        entry_price = signal_data.get('entry_price')
        stop_loss = signal_data.get('stop_loss')
        take_profit = signal_data.get('take_profit')
        
        # Validation
        if not self._validate_signal(symbol, signal_type, confidence):
            return None
        
        # Map symbol to MT5 format
        mt5_symbol = self._map_symbol(symbol)
        if not mt5_symbol:
            logger.warning(f"Unknown symbol mapping: {symbol}")
            return None
        
        # Calculate position size based on risk
        position_size = self._calculate_position_size(
            mt5_symbol, entry_price, stop_loss, signal_type
        )
        
        # Create MT5 signal
        try:
            mt5_signal = MT5TradeSignal(
                symbol=mt5_symbol,
                signal_type=SignalType.BUY if signal_type == 'BUY' else SignalType.SELL,
                strength=self._map_strength(strength),
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                volume=position_size,
                reasoning=signal_data.get('reasoning', ''),
                key_factors=signal_data.get('key_factors', []),
                risks=signal_data.get('risks', [])
            )
            
            logger.info(f"✅ Converted signal: {mt5_symbol} {signal_type} @ {entry_price} (Vol: {position_size})")
            return mt5_signal
            
        except Exception as e:
            logger.error(f"Failed to create MT5 signal for {symbol}: {e}")
            return None
    
    def _validate_signal(self, symbol: str, signal_type: str, confidence: float) -> bool:
        """Validate signal data"""
        
        # Check required fields
        if not symbol or not signal_type:
            logger.warning("Signal missing symbol or type")
            return False
        
        # Check signal type
        if signal_type not in ['BUY', 'SELL', 'HOLD']:
            logger.warning(f"Invalid signal type: {signal_type}")
            return False
        
        # Skip HOLD signals as they don't require action
        if signal_type == 'HOLD':
            logger.info(f"Skipping HOLD signal for {symbol} - no action required")
            return False
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            logger.info(f"Signal confidence {confidence:.2f} below threshold {self.min_confidence}")
            return False
        
        return True
    
    def _parse_confidence(self, confidence_str: Any) -> float:
        """Parse confidence from various formats"""
        try:
            if isinstance(confidence_str, (int, float)):
                return float(confidence_str)
            elif isinstance(confidence_str, str):
                # Remove % symbol and convert
                clean_str = confidence_str.replace('%', '').strip()
                return float(clean_str) / 100.0 if float(clean_str) > 1 else float(clean_str)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _map_symbol(self, llm_symbol: str) -> Optional[str]:
        """Map LLM symbol format to MT5 symbol format"""
        return self.symbol_mapping.get(llm_symbol)
    
    def _map_strength(self, strength_str: str) -> SignalStrength:
        """Map strength string to SignalStrength enum"""
        mapping = {
            'WEAK': SignalStrength.WEAK,
            'MODERATE': SignalStrength.MODERATE,
            'STRONG': SignalStrength.STRONG
        }
        return mapping.get(strength_str, SignalStrength.MODERATE)
    
    def _calculate_position_size(
        self, 
        symbol: str, 
        entry_price: Optional[float], 
        stop_loss: Optional[float],
        signal_type: str
    ) -> float:
        """
        Calculate position size based on risk management
        
        This is a simplified calculation - you may want to integrate with
        actual account balance and more sophisticated risk management.
        """
        
        try:
            if not entry_price or not stop_loss:
                # Default position size if no price info
                return 0.01  # Minimum lot size
            
            # Calculate risk in pips/points
            price_diff = abs(entry_price - stop_loss)
            
            if price_diff == 0:
                return 0.01
            
            # Basic position sizing (this is simplified)
            # In reality, you'd want to:
            # 1. Get current account balance
            # 2. Calculate pip/point value for the symbol
            # 3. Apply proper risk management formula
            
            # For now, use a conservative fixed size
            if 'JPY' in symbol:
                # JPY pairs have different pip values
                return min(0.1, max(0.01, self.risk_percent / 100))
            else:
                return min(0.1, max(0.01, self.risk_percent / 100))
                
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0.01  # Fallback to minimum size

    def filter_actionable_signals(self, mt5_signals: List[MT5TradeSignal]) -> List[MT5TradeSignal]:
        """Filter signals that should be executed"""
        
        actionable = []
        
        for signal in mt5_signals:
            try:
                # Check confidence
                if signal.confidence < self.min_confidence:
                    continue
                
                # Check for required price levels
                if not signal.entry_price:
                    logger.warning(f"Signal {signal.symbol} missing entry price")
                    continue
                
                # Additional filters can be added here
                # - Time-based filters
                # - Market condition filters
                # - Correlation filters
                
                actionable.append(signal)
                
            except Exception as e:
                logger.error(f"Error filtering signal {signal.symbol}: {e}")
        
        logger.info(f"Filtered to {len(actionable)}/{len(mt5_signals)} actionable signals")
        return actionable
    
    def update_risk_settings(self, risk_percent: float, min_confidence: float):
        """Update risk management settings"""
        self.risk_percent = risk_percent
        self.min_confidence = min_confidence
        logger.info(f"Updated risk settings - Risk: {risk_percent}%, Min Confidence: {min_confidence}")

# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create converter
    converter = SignalConverter(risk_percent=1.0, min_confidence=0.75)
    
    # Test signal conversion
    test_llm_signals = [
        {
            'symbol': 'OANDA:EUR_USD',
            'type': 'BUY',
            'confidence': '85%',
            'strength': 'STRONG',
            'entry_price': 1.0950,
            'stop_loss': 1.0920,
            'take_profit': 1.1000,
            'reasoning': 'Strong technical breakout'
        },
        {
            'symbol': 'GBP_USD',
            'type': 'SELL', 
            'confidence': 0.78,
            'strength': 'MODERATE',
            'entry_price': 1.2650,
            'stop_loss': 1.2680,
            'take_profit': 1.2600,
            'reasoning': 'Bearish divergence'
        }
    ]
    
    # Convert signals
    mt5_signals = converter.convert_llm_signals(test_llm_signals)
    actionable_signals = converter.filter_actionable_signals(mt5_signals)
    
    print(f"\nConverted {len(mt5_signals)} signals, {len(actionable_signals)} actionable")
    for signal in actionable_signals:
        print(f"- {signal.symbol} {signal.signal_type.value} @ {signal.entry_price}")
