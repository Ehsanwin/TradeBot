#!/usr/bin/env python3
"""
MT5 API Service - Local Windows Service
Provides REST API interface to MetaTrader5 for Docker services

This service runs locally on Windows and provides a stable API interface
that the Docker containers can connect to for MT5 trading operations.

Usage:
    python mt5_api_service.py

API Endpoints:
    GET  /health                    - Health check
    POST /connect                   - Connect to MT5
    POST /disconnect                - Disconnect from MT5  
    GET  /account_info              - Get account information
    POST /execute_trade             - Execute a trade
    GET  /positions                 - Get open positions
    POST /close_position            - Close a position
    GET  /market_data/{symbol}      - Get market data for symbol
    GET  /symbols                   - Get available symbols
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback

# FastAPI for REST API
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# MetaTrader5 (Windows only)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    print("⚠️  MetaTrader5 not available. This service must run on Windows with MT5 installed.")
    MT5_AVAILABLE = False

# Add project to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import MT5 configurations
from mt.config.settings import get_mt5_settings
from mt.logger import setup_logging, get_logger

# Setup logging
logger = get_logger(__name__)

# Pydantic models for API
class TradeRequest(BaseModel):
    symbol: str
    action: str  # "BUY" or "SELL"
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None  # Stop Loss
    tp: Optional[float] = None  # Take Profit
    comment: str = "API Trade"
    magic: int = 123456

class TradeResponse(BaseModel):
    success: bool
    ticket: Optional[int] = None
    message: str
    error_code: Optional[int] = None

class PositionInfo(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    price_open: float
    price_current: float
    profit: float
    comment: str

class MarketData(BaseModel):
    symbol: str
    bid: float
    ask: float
    spread: float
    volume: int
    time: str

class ConnectionStatus(BaseModel):
    connected: bool
    account: Optional[int] = None
    server: Optional[str] = None
    balance: Optional[float] = None
    equity: Optional[float] = None
    message: str

# FastAPI app
app = FastAPI(
    title="MT5 API Service",
    description="Local MetaTrader5 API for Docker services",
    version="1.0.0"
)

# CORS middleware for Docker containers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Docker communication
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MT5APIService:
    """MT5 API Service Manager"""
    
    def __init__(self):
        self.connected = False
        self.settings = None
        self.last_health_check = None
        
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 module not available!")
            return
            
        try:
            self.settings = get_mt5_settings()
            logger.info("MT5 API Service initialized")
        except Exception as e:
            logger.error(f"Failed to load MT5 settings: {e}")
    
    def connect_mt5(self) -> ConnectionStatus:
        """Connect to MetaTrader5"""
        if not MT5_AVAILABLE:
            return ConnectionStatus(
                connected=False, 
                message="MetaTrader5 not available on this system"
            )
        
        try:
            # Initialize MT5
            if not mt5.initialize():
                error = mt5.last_error()
                return ConnectionStatus(
                    connected=False,
                    message=f"MT5 initialization failed: {error}"
                )
            
            # Login if credentials provided
            if (hasattr(self.settings, 'core') and 
                hasattr(self.settings.core, 'connection')):
                
                conn = self.settings.core.connection
                if conn.login and conn.password and conn.server:
                    login_result = mt5.login(
                        login=conn.login,
                        password=conn.password, 
                        server=conn.server
                    )
                    
                    if not login_result:
                        error = mt5.last_error()
                        mt5.shutdown()
                        return ConnectionStatus(
                            connected=False,
                            message=f"MT5 login failed: {error}"
                        )
            
            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                mt5.shutdown()
                return ConnectionStatus(
                    connected=False,
                    message="Failed to get account information"
                )
            
            self.connected = True
            self.last_health_check = datetime.now()
            
            return ConnectionStatus(
                connected=True,
                account=account_info.login,
                server=account_info.server,
                balance=account_info.balance,
                equity=account_info.equity,
                message="Successfully connected to MT5"
            )
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return ConnectionStatus(
                connected=False,
                message=f"Connection error: {str(e)}"
            )
    
    def disconnect_mt5(self) -> Dict[str, Any]:
        """Disconnect from MetaTrader5"""
        if not MT5_AVAILABLE:
            return {"success": False, "message": "MT5 not available"}
        
        try:
            mt5.shutdown()
            self.connected = False
            return {"success": True, "message": "Disconnected from MT5"}
        except Exception as e:
            return {"success": False, "message": f"Disconnect error: {str(e)}"}
    
    def execute_trade(self, trade_request: TradeRequest) -> TradeResponse:
        """Execute a trade"""
        if not self.connected or not MT5_AVAILABLE:
            return TradeResponse(
                success=False,
                message="MT5 not connected"
            )
        
        try:
            # Validate symbol
            symbol_info = mt5.symbol_info(trade_request.symbol)
            if symbol_info is None:
                return TradeResponse(
                    success=False,
                    message=f"Symbol {trade_request.symbol} not found"
                )
            
            # Enable symbol if not enabled
            if not symbol_info.visible:
                if not mt5.symbol_select(trade_request.symbol, True):
                    return TradeResponse(
                        success=False,
                        message=f"Failed to enable symbol {trade_request.symbol}"
                    )
            
            # Prepare trade request
            if trade_request.action.upper() == "BUY":
                trade_type = mt5.ORDER_TYPE_BUY
                price = trade_request.price or mt5.symbol_info_tick(trade_request.symbol).ask
            elif trade_request.action.upper() == "SELL":
                trade_type = mt5.ORDER_TYPE_SELL
                price = trade_request.price or mt5.symbol_info_tick(trade_request.symbol).bid
            else:
                return TradeResponse(
                    success=False,
                    message=f"Invalid trade action: {trade_request.action}"
                )
            
            # Create trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": trade_request.symbol,
                "volume": trade_request.volume,
                "type": trade_type,
                "price": price,
                "sl": trade_request.sl or 0,
                "tp": trade_request.tp or 0,
                "comment": trade_request.comment,
                "magic": trade_request.magic,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            # Send trade request
            result = mt5.order_send(request)
            
            if result is None:
                return TradeResponse(
                    success=False,
                    message="Trade request failed - no response"
                )
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return TradeResponse(
                    success=False,
                    message=f"Trade failed: {result.comment}",
                    error_code=result.retcode
                )
            
            return TradeResponse(
                success=True,
                ticket=result.order,
                message=f"Trade executed successfully - Ticket: {result.order}"
            )
            
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return TradeResponse(
                success=False,
                message=f"Execution error: {str(e)}"
            )
    
    def get_positions(self) -> List[PositionInfo]:
        """Get all open positions"""
        if not self.connected or not MT5_AVAILABLE:
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append(PositionInfo(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type="BUY" if pos.type == 0 else "SELL",
                    volume=pos.volume,
                    price_open=pos.price_open,
                    price_current=pos.price_current,
                    profit=pos.profit,
                    comment=pos.comment
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for symbol"""
        if not self.connected or not MT5_AVAILABLE:
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return MarketData(
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                spread=tick.ask - tick.bid,
                volume=tick.volume,
                time=datetime.fromtimestamp(tick.time).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Get market data error: {e}")
            return None
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.connected or not MT5_AVAILABLE:
            return {"error": "MT5 not connected"}
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return {"error": "Failed to get account info"}
            
            return {
                "login": account_info.login,
                "server": account_info.server,
                "currency": account_info.currency,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "margin_free": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "profit": account_info.profit
            }
            
        except Exception as e:
            logger.error(f"Get account info error: {e}")
            return {"error": str(e)}

# Global service instance
mt5_service = MT5APIService()

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "MT5 API Service",
        "version": "1.0.0",
        "status": "running",
        "mt5_available": str(MT5_AVAILABLE),
        "connected": str(mt5_service.connected if mt5_service else False)
    }

@app.get("/health", response_model=ConnectionStatus)
async def health_check():
    """Health check endpoint"""
    if not mt5_service:
        return ConnectionStatus(
            connected=False,
            message="MT5 service not initialized"
        )
    
    # Update health check timestamp
    mt5_service.last_health_check = datetime.now()
    
    if not mt5_service.connected:
        return ConnectionStatus(
            connected=False,
            message="MT5 not connected"
        )
    
    # Get fresh account info for health check
    account_info = mt5_service.get_account_info()
    
    if "error" in account_info:
        return ConnectionStatus(
            connected=False,
            message=account_info["error"]
        )
    
    return ConnectionStatus(
        connected=True,
        account=account_info.get("login"),
        server=account_info.get("server"),
        balance=account_info.get("balance"),
        equity=account_info.get("equity"),
        message="MT5 connection healthy"
    )

@app.post("/connect", response_model=ConnectionStatus)
async def connect():
    """Connect to MT5"""
    return mt5_service.connect_mt5()

@app.post("/disconnect", response_model=Dict[str, Any])
async def disconnect():
    """Disconnect from MT5"""
    return mt5_service.disconnect_mt5()

@app.get("/account_info", response_model=Dict[str, Any])
async def get_account_info():
    """Get account information"""
    return mt5_service.get_account_info()

@app.post("/execute_trade", response_model=TradeResponse)
async def execute_trade(trade_request: TradeRequest):
    """Execute a trade"""
    return mt5_service.execute_trade(trade_request)

@app.get("/positions", response_model=List[PositionInfo])
async def get_positions():
    """Get open positions"""
    return mt5_service.get_positions()

@app.get("/market_data/{symbol}", response_model=Optional[MarketData])
async def get_market_data(symbol: str):
    """Get market data for symbol"""
    data = mt5_service.get_market_data(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail="Symbol not found or MT5 not connected")
    return data

@app.get("/symbols", response_model=List[str])
async def get_symbols():
    """Get available symbols"""
    if not mt5_service.connected or not MT5_AVAILABLE:
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    try:
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        
        return [symbol.name for symbol in symbols[:100]]  # Limit to 100 symbols
        
    except Exception as e:
        logger.error(f"Get symbols error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"API error: {exc}")
    logger.error(traceback.format_exc())
    
    return HTTPException(
        status_code=500,
        detail=f"Internal server error: {str(exc)}"
    )

def main():
    """Main entry point"""
    
    print("🚀 MT5 API Service Starting...")
    print("=" * 40)
    
    if not MT5_AVAILABLE:
        print("❌ MetaTrader5 not available!")
        print("   This service requires MetaTrader5 to be installed on Windows.")
        print("   Please install MT5 and try again.")
        sys.exit(1)
    
    # Setup logging
    setup_logging(
        level="INFO",
        log_file="logs/mt5_api_service.log",
        console_output=True
    )
    
    print("✅ MT5 API Service initialized")
    print("📊 Available endpoints:")
    print("   • GET  /health                 - Health check")
    print("   • POST /connect                - Connect to MT5") 
    print("   • POST /disconnect             - Disconnect from MT5")
    print("   • GET  /account_info           - Account information")
    print("   • POST /execute_trade          - Execute trade")
    print("   • GET  /positions              - Open positions")
    print("   • GET  /market_data/{symbol}   - Market data")
    print("   • GET  /symbols                - Available symbols")
    print("")
    print("🌐 Starting API server on http://localhost:8001")
    print("🔗 Docker services can connect via: http://host.docker.internal:8001")
    print("")
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Start the API server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",  # Listen on all interfaces
            port=8001,       # Different port from Docker services
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 MT5 API Service stopping...")
        if mt5_service:
            mt5_service.disconnect_mt5()
        print("✅ MT5 API Service stopped")

if __name__ == "__main__":
    main()
