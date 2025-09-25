"""
MetaTrader5 Connection Manager

Handles connection, reconnection, and status monitoring for MT5 terminal.
"""

import MetaTrader5 as mt5
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..config.settings import get_mt5_settings

logger = logging.getLogger(__name__)

@dataclass
class ConnectionStatus:
    """MT5 connection status information"""
    connected: bool
    account_info: Optional[Dict[str, Any]] = None
    terminal_info: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    connection_time: Optional[datetime] = None
    last_check: Optional[datetime] = None

class MT5Connection:
    """MetaTrader5 connection manager"""
    
    def __init__(self):
        self.settings = get_mt5_settings()
        self._status = ConnectionStatus(connected=False)
        self._connection_attempts = 0
        self._max_connection_attempts = self.settings.core.connection.retries
        
        logger.info("MT5 Connection manager initialized")
    
    @property
    def is_connected(self) -> bool:
        """Check if MT5 is connected"""
        return self._status.connected and mt5.terminal_info() is not None
    
    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self._status
    
    def connect(self) -> bool:
        """
        Connect to MT5 terminal
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Attempting to connect to MT5 terminal...")
            
            # Check if MT5 is available
            try:
                import MetaTrader5 as mt5
            except ImportError:
                error_msg = "MetaTrader5 module not available. This system requires Windows with MT5 installed."
                logger.error(error_msg)
                self._status.last_error = error_msg
                return False
            
            # Prepare connection parameters
            conn_params = {}
            
            # Only add non-empty parameters
            if self.settings.core.connection.path:
                conn_params['path'] = self.settings.core.connection.path
                
            if self.settings.core.connection.login:
                conn_params['login'] = self.settings.core.connection.login
                
            if self.settings.core.connection.password:
                conn_params['password'] = self.settings.core.connection.password
                
            if self.settings.core.connection.server:
                conn_params['server'] = self.settings.core.connection.server
                
            if self.settings.core.connection.timeout:
                conn_params['timeout'] = self.settings.core.connection.timeout
            
            logger.debug(f"Connection parameters: {list(conn_params.keys())}")
            
            # Initialize MT5 connection
            if not mt5.initialize(**conn_params):
                error_code = mt5.last_error()
                error_msg = f"MT5 initialization failed: {error_code}"
                logger.error(error_msg)
                self._status.last_error = error_msg
                return False
            
            # Verify connection by getting account info
            account_info = mt5.account_info()
            if account_info is None:
                error_code = mt5.last_error()
                error_msg = f"Failed to get account info: {error_code}"
                logger.error(error_msg)
                self._status.last_error = error_msg
                mt5.shutdown()
                return False
            
            # Get terminal info
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.warning("Could not retrieve terminal info")
            
            # Update status
            self._status = ConnectionStatus(
                connected=True,
                account_info=account_info._asdict() if account_info else None,
                terminal_info=terminal_info._asdict() if terminal_info else None,
                connection_time=datetime.now(),
                last_check=datetime.now()
            )
            
            self._connection_attempts = 0
            
            logger.info(f"Successfully connected to MT5 - Account: {account_info.login if account_info else 'Unknown'}")
            logger.info(f"Account Balance: {account_info.balance if account_info else 'Unknown'}")
            logger.info(f"Account Currency: {account_info.currency if account_info else 'Unknown'}")
            
            return True
            
        except Exception as e:
            error_msg = f"Connection error: {e}"
            logger.error(error_msg)
            self._status.last_error = error_msg
            return False
    
    def disconnect(self):
        """Disconnect from MT5 terminal"""
        try:
            if self.is_connected:
                mt5.shutdown()
                logger.info("Disconnected from MT5 terminal")
            
            self._status = ConnectionStatus(connected=False)
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect to MT5 terminal
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        logger.info("Attempting to reconnect to MT5...")
        
        if self._connection_attempts >= self._max_connection_attempts:
            logger.error(f"Maximum reconnection attempts ({self._max_connection_attempts}) reached")
            return False
        
        self._connection_attempts += 1
        
        # Disconnect first
        self.disconnect()
        
        # Wait before reconnecting
        time.sleep(self.settings.core.connection.retry_delay)
        
        # Attempt connection
        return self.connect()
    
    def check_connection(self) -> bool:
        """
        Check and validate current connection status
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            # Quick check - if we think we're disconnected, don't bother
            if not self._status.connected:
                return False
            
            # Check if MT5 terminal is still responsive
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.warning("MT5 terminal not responding")
                self._status.connected = False
                return False
            
            # Check if account info is still accessible
            account_info = mt5.account_info()
            if account_info is None:
                logger.warning("Cannot access account info")
                self._status.connected = False
                return False
            
            # Update last check time
            self._status.last_check = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            self._status.connected = False
            self._status.last_error = str(e)
            return False
    
    def ensure_connection(self) -> bool:
        """
        Ensure MT5 connection is active, reconnect if necessary
        
        Returns:
            bool: True if connection is active, False otherwise
        """
        if self.check_connection():
            return True
        
        logger.info("Connection check failed, attempting to reconnect...")
        return self.reconnect()
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information
        
        Returns:
            Optional[Dict]: Account info dictionary or None if not connected
        """
        if not self.ensure_connection():
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info:
                return account_info._asdict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current terminal information
        
        Returns:
            Optional[Dict]: Terminal info dictionary or None if not connected
        """
        if not self.ensure_connection():
            return None
        
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info:
                return terminal_info._asdict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get terminal info: {e}")
            return None
    
    def get_symbols(self) -> list:
        """
        Get available symbols from MT5
        
        Returns:
            list: List of available symbols
        """
        if not self.ensure_connection():
            return []
        
        try:
            symbols = mt5.symbols_get()
            if symbols:
                return [symbol.name for symbol in symbols]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            return []
    
    def symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information
        
        Args:
            symbol: Symbol name (e.g., "EURUSD")
        
        Returns:
            Optional[Dict]: Symbol info dictionary or None if not found
        """
        if not self.ensure_connection():
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                return symbol_info._asdict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
