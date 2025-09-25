#!/usr/bin/env python3
"""
MT5 API Client - For Docker Services
Connects to the local MT5 API service running on Windows

This client is used by Docker services to communicate with the local
MT5 API service via HTTP/REST API calls.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MT5APIClient:
    """Client for communicating with local MT5 API service"""
    
    def __init__(self, base_url: str = "http://host.docker.internal:8001", timeout: int = 30):
        """
        Initialize MT5 API client
        
        Args:
            base_url: Base URL of MT5 API service (use host.docker.internal for Docker)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.connected = False
        
        # HTTP client with retry and timeout configuration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        logger.info(f"MT5 API Client initialized - Base URL: {self.base_url}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if MT5 API service is healthy"""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            
            result = response.json()
            self.connected = result.get("connected", False)
            return result
            
        except Exception as e:
            logger.error(f"MT5 API health check failed: {e}")
            self.connected = False
            return {
                "connected": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def connect(self) -> Dict[str, Any]:
        """Connect to MT5 via API"""
        try:
            response = await self.client.post("/connect")
            response.raise_for_status()
            
            result = response.json()
            self.connected = result.get("connected", False)
            
            if self.connected:
                logger.info("✅ Connected to MT5 via API")
            else:
                logger.error(f"❌ MT5 connection failed: {result.get('message', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"MT5 API connect failed: {e}")
            self.connected = False
            return {
                "connected": False,
                "message": f"Connection failed: {str(e)}"
            }
    
    async def disconnect(self) -> Dict[str, Any]:
        """Disconnect from MT5 via API"""
        try:
            response = await self.client.post("/disconnect")
            response.raise_for_status()
            
            result = response.json()
            self.connected = False
            logger.info("MT5 disconnected via API")
            return result
            
        except Exception as e:
            logger.error(f"MT5 API disconnect failed: {e}")
            return {
                "success": False,
                "message": f"Disconnect failed: {str(e)}"
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            response = await self.client.get("/account_info")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Get account info failed: {e}")
            return {"error": f"Failed to get account info: {str(e)}"}
    
    async def execute_trade(
        self,
        symbol: str,
        action: str,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "API Trade",
        magic: int = 123456
    ) -> Dict[str, Any]:
        """
        Execute a trade
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            action: "BUY" or "SELL"
            volume: Trade volume
            price: Entry price (optional, uses market price if None)
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Trade comment
            magic: Magic number
            
        Returns:
            Dictionary with trade result
        """
        try:
            trade_data = {
                "symbol": symbol,
                "action": action,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
                "magic": magic
            }
            
            response = await self.client.post("/execute_trade", json=trade_data)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("success"):
                logger.info(f"✅ Trade executed: {symbol} {action} {volume} lots - Ticket: {result.get('ticket')}")
            else:
                logger.warning(f"❌ Trade failed: {symbol} {action} - {result.get('message')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Execute trade failed: {e}")
            return {
                "success": False,
                "message": f"Trade execution failed: {str(e)}"
            }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            response = await self.client.get("/positions")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            return []
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for symbol"""
        try:
            response = await self.client.get(f"/market_data/{symbol}")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.debug(f"Get market data failed for {symbol}: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        try:
            response = await self.client.get("/symbols")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Get symbols failed: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("MT5 API client closed")

class MT5TradeSignal:
    """Compatibility class for MT5 trade signals"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_api_request(self) -> Dict[str, Any]:
        """Convert to API trade request format"""
        return {
            "symbol": getattr(self, 'symbol', ''),
            "action": getattr(self, 'signal_type', 'BUY').value if hasattr(getattr(self, 'signal_type', ''), 'value') else str(getattr(self, 'signal_type', 'BUY')),
            "volume": getattr(self, 'volume', 0.01),
            "price": getattr(self, 'entry_price', None),
            "sl": getattr(self, 'stop_loss', None),
            "tp": getattr(self, 'take_profit', None),
            "comment": getattr(self, 'reasoning', 'API Trade')[:31],  # MT5 comment limit
            "magic": 123456
        }

class MT5APITrader:
    """Trader class using MT5 API - Compatible interface"""
    
    def __init__(self, api_client: MT5APIClient):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__ + ".MT5APITrader")
    
    async def execute_signal(self, signal: MT5TradeSignal) -> Dict[str, Any]:
        """Execute a trading signal via API"""
        
        # Ensure API connection
        if not self.api_client.connected:
            health = await self.api_client.health_check()
            if not health.get("connected"):
                connection_result = await self.api_client.connect()
                if not connection_result.get("connected"):
                    return {
                        "success": False,
                        "error": f"MT5 API not connected: {connection_result.get('message', 'Unknown error')}"
                    }
        
        try:
            # Convert signal to API request
            trade_request = signal.to_api_request()
            
            # Execute trade via API
            result = await self.api_client.execute_trade(**trade_request)
            
            # Return compatible result format
            return {
                "success": result.get("success", False),
                "ticket": result.get("ticket"),
                "message": result.get("message", ""),
                "error": result.get("message", "") if not result.get("success") else None
            }
            
        except Exception as e:
            self.logger.error(f"Signal execution failed: {e}")
            return {
                "success": False,
                "error": f"Signal execution error: {str(e)}"
            }
    
    async def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading summary"""
        try:
            account_info = await self.api_client.get_account_info()
            positions = await self.api_client.get_positions()
            
            return {
                "account_balance": account_info.get("balance", 0),
                "equity": account_info.get("equity", 0),
                "margin": account_info.get("margin", 0),
                "free_margin": account_info.get("margin_free", 0),
                "open_positions": len(positions),
                "total_profit": account_info.get("profit", 0),
                "win_rate_30d": 0  # Would need historical data
            }
            
        except Exception as e:
            self.logger.error(f"Get trading summary failed: {e}")
            return {
                "account_balance": 0,
                "open_positions": 0,
                "win_rate_30d": 0
            }

# Singleton instances for easy import
mt5_api_client = None
mt5_api_trader = None

async def get_mt5_api_client(base_url: str = "http://host.docker.internal:8001") -> MT5APIClient:
    """Get or create MT5 API client instance"""
    global mt5_api_client
    
    if mt5_api_client is None:
        mt5_api_client = MT5APIClient(base_url)
        
        # Test connection
        health = await mt5_api_client.health_check()
        if health.get("connected"):
            logger.info("✅ MT5 API client connected successfully")
        else:
            logger.warning(f"⚠️  MT5 API client connection issue: {health.get('message', 'Unknown')}")
    
    return mt5_api_client

async def get_mt5_api_trader(base_url: str = "http://host.docker.internal:8001") -> MT5APITrader:
    """Get or create MT5 API trader instance"""
    global mt5_api_trader
    
    if mt5_api_trader is None:
        client = await get_mt5_api_client(base_url)
        mt5_api_trader = MT5APITrader(client)
        logger.info("✅ MT5 API trader initialized")
    
    return mt5_api_trader

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_api():
        """Test the MT5 API client"""
        client = MT5APIClient()
        
        try:
            print("Testing MT5 API client...")
            
            # Health check
            health = await client.health_check()
            print(f"Health: {health}")
            
            if not health.get("connected"):
                # Try to connect
                connection = await client.connect()
                print(f"Connection: {connection}")
            
            # Get account info
            account = await client.get_account_info()
            print(f"Account: {account}")
            
            # Get symbols (first 5)
            symbols = await client.get_symbols()
            print(f"Symbols (first 5): {symbols[:5]}")
            
            # Get market data
            if symbols:
                market_data = await client.get_market_data(symbols[0])
                print(f"Market data for {symbols[0]}: {market_data}")
            
        except Exception as e:
            print(f"Test error: {e}")
        
        finally:
            await client.close()
    
    asyncio.run(test_api())
