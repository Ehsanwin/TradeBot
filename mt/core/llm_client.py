"""
LLM Integration Client

Handles communication with the LLM service to get trading signals.
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..config.settings import get_mt5_settings

# Import LLM data types
try:
    from LLM.core.data_types import TradingSignal, SignalType, SignalStrength
except ImportError:
    # Fallback import when running from project root
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    try:
        from LLM.core.data_types import TradingSignal, SignalType, SignalStrength
    except ImportError:
        # Import from trader module which has fallback definitions
        from .trader import TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for communicating with LLM trading analysis service"""
    
    def __init__(self):
        self.settings = get_mt5_settings()
        self.base_url = self.settings.core.llm.api_base_url.rstrip('/')
        self.timeout = self.settings.core.llm.timeout
        self.retries = self.settings.core.llm.retries
        self._last_analysis_time: Optional[datetime] = None
        
        logger.info(f"LLM Client initialized - Base URL: {self.base_url}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to LLM service with retry logic
        
        Args:
            endpoint: API endpoint
            params: Request parameters
        
        Returns:
            Optional[Dict]: Response data or None if failed
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                
                response = requests.get(
                    url,
                    params=params or {},
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"LLM service endpoint not found: {url}")
                    return None
                else:
                    logger.warning(f"LLM request failed - Status: {response.status_code}, Response: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.retries})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"LLM connection error (attempt {attempt + 1}/{self.retries})")
            except Exception as e:
                logger.error(f"LLM request error: {e}")
            
            # Wait before retry (except last attempt)
            if attempt < self.retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"All LLM request attempts failed for {url}")
        return None
    
    def get_trading_signals(self, symbols: Optional[List[str]] = None) -> List[TradingSignal]:
        """
        Get trading signals from LLM service
        
        Args:
            symbols: List of symbols to analyze (uses default if None)
        
        Returns:
            List[TradingSignal]: List of trading signals
        """
        try:
            if symbols is None:
                symbols = self.settings.core.trading.default_symbols
            
            logger.info(f"Requesting LLM analysis for symbols: {symbols}")
            
            # Prepare request parameters
            params = {
                'symbols': ','.join(symbols),
                'format': 'json'
            }
            
            # Make request to LLM analysis endpoint
            response_data = self._make_request('/api/analysis', params)
            
            if not response_data:
                logger.error("Failed to get response from LLM service")
                return []
            
            if not response_data.get('success'):
                error_msg = response_data.get('error', 'Unknown error')
                logger.error(f"LLM analysis failed: {error_msg}")
                return []
            
            # Extract signals from response
            signals_data = response_data.get('signals', [])
            if not signals_data:
                logger.warning("No signals received from LLM service")
                return []
            
            # Parse signals
            signals = []
            for signal_data in signals_data:
                try:
                    signal = self._parse_signal(signal_data)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    logger.error(f"Failed to parse signal: {e}")
                    continue
            
            self._last_analysis_time = datetime.now()
            
            logger.info(f"Received {len(signals)} signals from LLM service")
            return signals
            
        except Exception as e:
            logger.error(f"Error getting trading signals: {e}")
            return []
    
    def _parse_signal(self, signal_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Parse signal data from LLM response
        
        Args:
            signal_data: Raw signal data from LLM
        
        Returns:
            Optional[TradingSignal]: Parsed signal or None if parsing failed
        """
        try:
            # Parse signal type
            signal_type_str = signal_data.get('type', '').upper()
            if signal_type_str == 'BUY':
                signal_type = SignalType.BUY
            elif signal_type_str == 'SELL':
                signal_type = SignalType.SELL
            elif signal_type_str == 'HOLD':
                signal_type = SignalType.HOLD
            else:
                logger.warning(f"Unknown signal type: {signal_type_str}")
                return None
            
            # Only process BUY and SELL signals for trading
            if signal_type not in self.settings.core.llm.allowed_signal_types:
                return None
            
            # Parse signal strength
            strength_str = signal_data.get('strength', '').upper()
            if strength_str == 'WEAK':
                strength = SignalStrength.WEAK
            elif strength_str == 'MODERATE':
                strength = SignalStrength.MODERATE
            elif strength_str == 'STRONG':
                strength = SignalStrength.STRONG
            elif strength_str == 'VERY_STRONG':
                strength = SignalStrength.VERY_STRONG
            else:
                strength = SignalStrength.MODERATE  # Default
            
            # Parse confidence (should be float between 0 and 1)
            confidence = float(signal_data.get('confidence', '0.0'))
            if confidence > 1.0:
                confidence = confidence / 100.0  # Convert percentage to decimal
            
            # Parse prices
            entry_price = self._safe_float(signal_data.get('entry_price'))
            stop_loss = self._safe_float(signal_data.get('stop_loss'))
            take_profit = self._safe_float(signal_data.get('take_profit'))
            
            # Calculate expiry time
            signal_expiry = datetime.now() + timedelta(minutes=self.settings.core.llm.signal_expiry_minutes)
            
            # Create signal
            signal = TradingSignal(
                symbol=signal_data.get('symbol', ''),
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=signal_data.get('reasoning', ''),
                key_factors=signal_data.get('key_factors', []),
                risks=signal_data.get('risks', []),
                timeframe=signal_data.get('timeframe', 'M15'),
                timestamp=datetime.now(),
                expires_at=signal_expiry
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error parsing signal data: {e}")
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_market_analysis(self, symbols: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive market analysis from LLM service
        
        Args:
            symbols: List of symbols to analyze
        
        Returns:
            Optional[Dict]: Market analysis data or None if failed
        """
        try:
            if symbols is None:
                symbols = self.settings.core.trading.default_symbols
            
            params = {
                'symbols': ','.join(symbols),
                'generate_report': 'true',
                'format': 'json'
            }
            
            response_data = self._make_request('/api/analysis', params)
            
            if response_data and response_data.get('success'):
                return response_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Check if LLM service is healthy and responsive
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            response_data = self._make_request('/health')
            return response_data is not None and response_data.get('status') == 'healthy'
            
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
    
    def should_request_analysis(self) -> bool:
        """
        Check if it's time to request new analysis based on interval
        
        Returns:
            bool: True if analysis should be requested, False otherwise
        """
        if self._last_analysis_time is None:
            return True
        
        interval_minutes = self.settings.core.llm.analysis_interval_minutes
        time_since_last = datetime.now() - self._last_analysis_time
        
        return time_since_last.total_seconds() >= (interval_minutes * 60)
    
    @property
    def last_analysis_time(self) -> Optional[datetime]:
        """Get timestamp of last analysis request"""
        return self._last_analysis_time
