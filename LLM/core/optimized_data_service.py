from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from .data_types import (
    ForexQuote, TechnicalAnalysis, NewsEvent, MarketData,
    NewsImportance, extract_currencies_from_symbol
)

logger = logging.getLogger(__name__)

class OptimizedMarketDataService:
    """Optimized market data service for faster data fetching"""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5000",
        timeout: int = 15,  # Reduced timeout
        retries: int = 1,   # Reduced retries
        max_workers: int = 3  # Parallel requests
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.max_workers = max_workers
        
        # Setup session
        self.session = requests.Session()
        self.session.timeout = timeout
        
        # Cache for API responses
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 180  # 3 minutes cache
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request with reduced timeout and retries"""
        
        # Create cache key
        cache_key = f"{endpoint}:{str(sorted((params or {}).items()))}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                logger.debug(f"Using cached data for {endpoint}")
                return cached_data['data']
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retries + 1):
            try:
                logger.debug(f"Request attempt {attempt + 1} to {url}")
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('ok'):
                    error_msg = data.get('error', 'Unknown API error')
                    raise ValueError(f"API error: {error_msg}")
                
                # Cache the response
                self._cache[cache_key] = {
                    'data': data,
                    'timestamp': time.time()
                }
                
                return data
                
            except (requests.exceptions.RequestException, ValueError) as e:
                if attempt == self.retries:
                    logger.error(f"Request failed after {self.retries + 1} attempts: {e}")
                    raise
                logger.warning(f"Request attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(0.5)  # Short delay between retries
        
        raise Exception("Should not reach here")
    
    def get_forex_quotes(self, symbols: Optional[List[str]] = None) -> List[ForexQuote]:
        """Fetch forex quotes (fast)"""
        
        params = {}
        if symbols:
            params['symbols'] = ','.join(symbols)
        
        try:
            data = self._make_request('/api/v1/forex/quote', params)
            quotes = []
            
            for item in data.get('data', []):
                try:
                    quote = ForexQuote.from_api_response(item)
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse forex quote: {e}")
                    continue
            
            logger.info(f"Fetched {len(quotes)} forex quotes")
            return quotes
            
        except Exception as e:
            logger.error(f"Failed to fetch forex quotes: {e}")
            return []
    
    def get_technical_analysis_fast(
        self, 
        symbol: str, 
        timeframe: str = "15", 
        days: int = 7  # Reduced from 30 to 7 days
    ) -> Optional[TechnicalAnalysis]:
        """Fetch technical analysis with reduced data for speed"""
        
        params = {
            'symbol': symbol,
            'resolution': timeframe,
            'days': str(days)  # Much less data
        }
        
        try:
            data = self._make_request('/api/v1/technical/analysis', params)
            
            analysis = TechnicalAnalysis.from_api_response(symbol, data)
            logger.debug(f"Fast TA for {symbol}: {analysis.pattern_count} patterns")
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Fast TA failed for {symbol}, trying basic: {e}")
            
            # Fallback: try support/resistance only (faster)
            try:
                sr_params = {
                    'symbol': symbol,
                    'resolution': timeframe,
                    'days': str(days)
                }
                sr_data = self._make_request('/api/v1/technical/support-resistance', sr_params)
                
                # Create basic technical analysis from S/R data
                return TechnicalAnalysis(
                    symbol=symbol,
                    timeframe=timeframe,
                    support_levels=[],  # Would need to parse from sr_data
                    resistance_levels=[],
                    patterns=[],
                    timestamp=datetime.now()
                )
            except Exception as e2:
                logger.error(f"Fallback TA also failed for {symbol}: {e2}")
                return None
    
    def get_recent_news_fast(
        self, 
        hours_back: int = 12,  # Reduced from 24 to 12 hours
        min_importance: int = 2,  # Only medium+ importance
        limit: int = 50  # Reduced limit
    ) -> List[NewsEvent]:
        """Fetch recent news with faster parameters"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        params = {
            'from_ts': str(int(start_time.timestamp())),
            'to_ts': str(int(end_time.timestamp())),
            'min_importance': str(min_importance),
            'limit': str(limit)
        }
        
        try:
            # Skip news fetch trigger for speed
            data = self._make_request('/api/v1/news/list', params)
            
            news_events = []
            for item in data.get('data', []):
                try:
                    news_event = NewsEvent.from_api_response(item)
                    news_events.append(news_event)
                except Exception as e:
                    logger.warning(f"Failed to parse news event: {e}")
                    continue
            
            logger.info(f"Fetched {len(news_events)} news events (fast)")
            return news_events
            
        except Exception as e:
            logger.error(f"Failed to fetch news events: {e}")
            return []
    
    def get_market_data_parallel(
        self, 
        symbols: List[str], 
        timeframe: str = "15",
        analysis_days: int = 7,  # Reduced days
        news_hours: int = 12,    # Reduced hours
        max_workers: int = None
    ) -> List[MarketData]:
        """Fetch market data in parallel for speed"""
        
        logger.info(f"Fetching market data for {len(symbols)} symbols (parallel)")
        
        if max_workers is None:
            max_workers = min(self.max_workers, len(symbols))
        
        # Fetch forex quotes for all symbols (fast)
        quotes_map = {}
        try:
            quotes = self.get_forex_quotes(symbols)
            quotes_map = {quote.symbol: quote for quote in quotes}
            logger.info(f"Got quotes for {len(quotes_map)} symbols")
        except Exception as e:
            logger.error(f"Failed to fetch forex quotes: {e}")
        
        # Fetch news once (shared across all symbols)
        all_news = self.get_recent_news_fast(news_hours)
        logger.info(f"Got {len(all_news)} news events")
        
        # Fetch technical analysis in parallel
        market_data_list = []
        
        def fetch_technical_for_symbol(symbol: str) -> Optional[MarketData]:
            """Fetch technical analysis for one symbol"""
            try:
                logger.debug(f"Fetching TA for {symbol}")
                
                forex_quote = quotes_map.get(symbol)
                technical_analysis = self.get_technical_analysis_fast(symbol, timeframe, analysis_days)
                related_news = self.get_symbol_related_news(symbol, all_news)
                
                return MarketData(
                    symbol=symbol,
                    forex_quote=forex_quote,
                    technical_analysis=technical_analysis,
                    related_news=related_news,
                    timestamp=datetime.now()
                )
                
            except Exception as e:
                logger.error(f"Failed to fetch TA for {symbol}: {e}")
                return None
        
        # Process symbols in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(fetch_technical_for_symbol, symbol): symbol 
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    market_data = future.result(timeout=20)  # 20s timeout per symbol
                    if market_data:
                        market_data_list.append(market_data)
                        logger.debug(f"Completed {symbol}")
                    else:
                        logger.warning(f"Failed {symbol}")
                except Exception as e:
                    logger.error(f"Exception for {symbol}: {e}")
        
        logger.info(f"Successfully fetched market data for {len(market_data_list)} symbols")
        return market_data_list
    
    def get_symbol_related_news(
        self, 
        symbol: str, 
        news_events: List[NewsEvent]
    ) -> List[NewsEvent]:
        """Filter news events related to a specific symbol's currencies"""
        
        currencies = extract_currencies_from_symbol(symbol)
        related_news = []
        
        for event in news_events:
            # Check if news title/description contains currency codes
            title_lower = event.title.lower()
            desc_lower = (event.description or '').lower()
            
            # Check for currency codes in text
            is_related = False
            for currency in currencies:
                currency_lower = currency.lower()
                if (currency_lower in title_lower or 
                    currency_lower in desc_lower or
                    currency in event.affected_currencies):
                    is_related = True
                    break
            
            # Also check for common forex-related terms
            if not is_related:
                forex_terms = ['forex', 'currency', 'central bank', 'interest rate']
                for term in forex_terms:
                    if term in title_lower:
                        is_related = True
                        break
            
            if is_related:
                related_news.append(event)
        
        return related_news
    
    def set_cache_ttl(self, seconds: int):
        """Set cache TTL for API responses"""
        self._cache_ttl = seconds
    
    def clear_cache(self):
        """Clear all cached responses"""
        self._cache.clear()
    
    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
