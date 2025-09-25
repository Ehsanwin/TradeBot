from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .data_types import (
    ForexQuote, TechnicalAnalysis, NewsEvent, MarketData,
    NewsImportance, extract_currencies_from_symbol
)

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for fetching and normalizing market data from TradeBot APIs"""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5000",
        timeout: int = 30,
        retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        
        # Setup HTTP session with retry logic
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=0.5
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Cache for API responses
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes default
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to TradeBot API with caching"""
        
        # Create cache key
        cache_key = f"{endpoint}:{str(sorted((params or {}).items()))}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                logger.debug(f"Using cached data for {endpoint}")
                return cached_data['data']
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making request to {url} with params: {params}")
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise
        except ValueError as e:
            logger.error(f"API error for {endpoint}: {e}")
            raise
    
    def get_forex_quotes(self, symbols: Optional[List[str]] = None) -> List[ForexQuote]:
        """Fetch forex quotes for given symbols"""
        
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
    
    def get_technical_analysis(
        self, 
        symbol: str, 
        timeframe: str = "15", 
        days: int = 30
    ) -> Optional[TechnicalAnalysis]:
        """Fetch technical analysis for a symbol"""
        
        params = {
            'symbol': symbol,
            'resolution': timeframe,
            'days': str(days)
        }
        
        try:
            data = self._make_request('/api/v1/technical/analysis', params)
            
            analysis = TechnicalAnalysis.from_api_response(symbol, data)
            logger.debug(f"Fetched technical analysis for {symbol}: {analysis.pattern_count} patterns, "
                        f"{len(analysis.support_levels)} supports, {len(analysis.resistance_levels)} resistances")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to fetch technical analysis for {symbol}: {e}")
            return None
    
    def get_recent_news(
        self, 
        hours_back: int = 24, 
        min_importance: int = 1, 
        limit: int = 100
    ) -> List[NewsEvent]:
        """Fetch recent news events"""
        
        # Calculate timestamp range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        params = {
            'from_ts': str(int(start_time.timestamp())),
            'to_ts': str(int(end_time.timestamp())),
            'min_importance': str(min_importance),
            'limit': str(limit)
        }
        
        try:
            # First, trigger news fetch to ensure we have recent data
            try:
                self._make_request('/api/v1/news/fetch', {'persist': 'true'})
            except Exception as e:
                logger.warning(f"Failed to trigger news fetch: {e}")
            
            # Then retrieve the news
            data = self._make_request('/api/v1/news/list', params)
            
            news_events = []
            for item in data.get('data', []):
                try:
                    news_event = NewsEvent.from_api_response(item)
                    news_events.append(news_event)
                except Exception as e:
                    logger.warning(f"Failed to parse news event: {e}")
                    continue
            
            logger.info(f"Fetched {len(news_events)} news events from last {hours_back} hours")
            return news_events
            
        except Exception as e:
            logger.error(f"Failed to fetch news events: {e}")
            return []
    
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
            forex_terms = ['forex', 'currency', 'central bank', 'interest rate', 'inflation', 'gdp', 'employment']
            if not is_related:
                for term in forex_terms:
                    if term in title_lower:
                        is_related = True
                        break
            
            if is_related:
                related_news.append(event)
        
        return related_news
    
    def get_market_data(
        self, 
        symbols: List[str], 
        timeframe: str = "15",
        analysis_days: int = 30,
        news_hours: int = 24
    ) -> List[MarketData]:
        """Fetch complete market data for given symbols"""
        
        logger.info(f"Fetching market data for {len(symbols)} symbols")
        
        # Fetch forex quotes for all symbols
        quotes_map = {}
        try:
            quotes = self.get_forex_quotes(symbols)
            quotes_map = {quote.symbol: quote for quote in quotes}
        except Exception as e:
            logger.error(f"Failed to fetch forex quotes: {e}")
        
        # Fetch recent news once for all symbols
        all_news = self.get_recent_news(news_hours)
        
        market_data_list = []
        
        for symbol in symbols:
            try:
                logger.debug(f"Processing market data for {symbol}")
                
                # Get components
                forex_quote = quotes_map.get(symbol)
                technical_analysis = self.get_technical_analysis(symbol, timeframe, analysis_days)
                related_news = self.get_symbol_related_news(symbol, all_news)
                
                # Create market data object
                market_data = MarketData(
                    symbol=symbol,
                    forex_quote=forex_quote,
                    technical_analysis=technical_analysis,
                    related_news=related_news,
                    timestamp=datetime.now()
                )
                
                market_data_list.append(market_data)
                
                logger.debug(f"Market data for {symbol}: quote={'✓' if forex_quote else '✗'}, "
                           f"technical={'✓' if technical_analysis else '✗'}, "
                           f"news={len(related_news)} events")
                
            except Exception as e:
                logger.error(f"Failed to fetch market data for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched market data for {len(market_data_list)} symbols")
        return market_data_list
    
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
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
