"""
MetaTrader5 Trading Execution Module

Handles trade execution, position management, and risk management based on LLM signals.
"""

import MetaTrader5 as mt5
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .connection import MT5Connection
from ..config.settings import get_mt5_settings

logger = logging.getLogger(__name__)

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
    except ImportError as e:
        logger.error(f"Failed to import LLM data types: {e}")
        logger.error("Make sure the LLM module is available in the project")
        # Create dummy classes as fallback
        from enum import Enum
        from dataclasses import dataclass
        from typing import Optional, List
        from datetime import datetime
        
        class SignalType(Enum):
            BUY = "buy"
            SELL = "sell"
            HOLD = "hold"
            
        class SignalStrength(Enum):
            WEAK = "weak"
            MODERATE = "moderate"
            STRONG = "strong"
            VERY_STRONG = "very_strong"
            
        @dataclass
        class TradingSignal:
            symbol: str
            signal_type: SignalType
            strength: SignalStrength
            confidence: float
            entry_price: Optional[float] = None
            stop_loss: Optional[float] = None
            take_profit: Optional[float] = None
            reasoning: Optional[str] = None
            key_factors: List[str] = None
            risks: List[str] = None
            timeframe: Optional[str] = None
            timestamp: Optional[datetime] = None
            expires_at: Optional[datetime] = None

class OrderType(Enum):
    """MT5 Order types"""
    BUY = mt5.ORDER_TYPE_BUY
    SELL = mt5.ORDER_TYPE_SELL
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP

class TradeResult(Enum):
    """Trade execution results"""
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    INVALID_SIGNAL = "invalid_signal"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    MARKET_CLOSED = "market_closed"
    SYMBOL_UNAVAILABLE = "symbol_unavailable"
    RISK_EXCEEDED = "risk_exceeded"

@dataclass
class TradeExecution:
    """Trade execution result"""
    result: TradeResult
    ticket: Optional[int] = None
    volume: Optional[float] = None
    price: Optional[float] = None
    error_message: Optional[str] = None
    execution_time: Optional[datetime] = None

@dataclass
class Position:
    """Open position information"""
    ticket: int
    symbol: str
    type: OrderType
    volume: float
    price_open: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_price: Optional[float] = None
    profit: Optional[float] = None
    swap: Optional[float] = None
    magic_number: Optional[int] = None
    comment: Optional[str] = None
    time_open: Optional[datetime] = None

class MT5Trader:
    """MetaTrader5 trading execution manager"""
    
    def __init__(self, connection: MT5Connection):
        self.connection = connection
        self.settings = get_mt5_settings()
        self._active_signals: Dict[str, TradingSignal] = {}
        self._executed_signals: Dict[str, TradeExecution] = {}
        
        logger.info("MT5 Trader initialized")
    
    def validate_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        Validate trading signal before execution
        
        Args:
            signal: TradingSignal to validate
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check if signal is expired
            if signal.expires_at and datetime.now() > signal.expires_at:
                return False, "Signal has expired"
            
            # Check signal type
            if signal.signal_type not in [SignalType.BUY, SignalType.SELL]:
                return False, f"Invalid signal type: {signal.signal_type}"
            
            # Check confidence threshold
            if signal.confidence < self.settings.core.llm.min_confidence_threshold:
                return False, f"Signal confidence {signal.confidence} below threshold {self.settings.core.llm.min_confidence_threshold}"
            
            # Check if symbol is available
            symbol_info = self.connection.symbol_info(signal.symbol)
            if not symbol_info:
                return False, f"Symbol {signal.symbol} not available"
            
            # Check if market is open
            if not symbol_info.get('trade_mode', 0):
                return False, f"Trading not allowed for {signal.symbol}"
            
            # Validate price levels
            if signal.entry_price and signal.entry_price <= 0:
                return False, "Invalid entry price"
            
            if signal.stop_loss and signal.stop_loss <= 0:
                return False, "Invalid stop loss"
            
            if signal.take_profit and signal.take_profit <= 0:
                return False, "Invalid take profit"
            
            # Check risk-reward ratio
            if signal.entry_price and signal.stop_loss and signal.take_profit:
                risk_reward = self._calculate_risk_reward(signal)
                if risk_reward < self.settings.core.trading.min_risk_reward:
                    return False, f"Risk-reward ratio {risk_reward:.2f} below minimum {self.settings.core.trading.min_risk_reward}"
            
            return True, "Signal validation successful"
            
        except Exception as e:
            return False, f"Signal validation error: {e}"
    
    def calculate_position_size(self, signal: TradingSignal, account_balance: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            signal: TradingSignal
            account_balance: Current account balance
        
        Returns:
            float: Position size (volume)
        """
        try:
            # Get symbol info
            symbol_info = self.connection.symbol_info(signal.symbol)
            if not symbol_info:
                logger.error(f"Cannot get symbol info for {signal.symbol}")
                return self.settings.core.trading.default_volume
            
            # Calculate risk amount
            risk_amount = account_balance * (self.settings.core.trading.max_risk_percent / 100)
            
            # Calculate pip value and risk in pips
            if signal.entry_price and signal.stop_loss:
                risk_pips = abs(signal.entry_price - signal.stop_loss) / symbol_info.get('point', 0.00001)
                
                # Calculate position size
                pip_value = symbol_info.get('trade_tick_value', 1.0)
                position_size = risk_amount / (risk_pips * pip_value)
                
                # Apply volume constraints
                min_volume = symbol_info.get('volume_min', 0.01)
                max_volume = symbol_info.get('volume_max', 100.0)
                volume_step = symbol_info.get('volume_step', 0.01)
                
                # Round to volume step
                position_size = round(position_size / volume_step) * volume_step
                
                # Apply limits
                position_size = max(min_volume, min(position_size, max_volume))
                
                # Additional safety: don't exceed default volume too much
                max_allowed = self.settings.core.trading.default_volume * 10
                position_size = min(position_size, max_allowed)
                
                return position_size
            
            # Fallback to default volume
            return self.settings.core.trading.default_volume
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.settings.core.trading.default_volume
    
    def execute_signal(self, signal: TradingSignal) -> TradeExecution:
        """
        Execute a trading signal
        
        Args:
            signal: TradingSignal to execute
        
        Returns:
            TradeExecution: Result of trade execution
        """
        try:
            logger.info(f"Executing signal: {signal.symbol} {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
            
            # Validate connection
            if not self.connection.ensure_connection():
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message="MT5 connection not available",
                    execution_time=datetime.now()
                )
            
            # Validate signal
            is_valid, error_msg = self.validate_signal(signal)
            if not is_valid:
                logger.warning(f"Signal validation failed: {error_msg}")
                return TradeExecution(
                    result=TradeResult.INVALID_SIGNAL,
                    error_message=error_msg,
                    execution_time=datetime.now()
                )
            
            # Check maximum positions
            current_positions = self.get_open_positions()
            if len(current_positions) >= self.settings.core.trading.max_positions:
                return TradeExecution(
                    result=TradeResult.REJECTED,
                    error_message=f"Maximum positions limit ({self.settings.core.trading.max_positions}) reached",
                    execution_time=datetime.now()
                )
            
            # Get account info for position sizing
            account_info = self.connection.get_account_info()
            if not account_info:
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message="Cannot get account information",
                    execution_time=datetime.now()
                )
            
            # Calculate position size
            volume = self.calculate_position_size(signal, account_info['balance'])
            
            # Prepare order request
            symbol_info = self.connection.symbol_info(signal.symbol)
            current_price = symbol_info.get('bid' if signal.signal_type == SignalType.SELL else 'ask', 0)
            
            # Determine order type
            order_type = OrderType.SELL.value if signal.signal_type == SignalType.SELL else OrderType.BUY.value
            
            # Build order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": volume,
                "type": order_type,
                "price": current_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "deviation": self.settings.core.trading.max_slippage,
                "magic": self.settings.core.trading.magic_number,
                "comment": f"LLM Signal - {signal.signal_type.value.upper()}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Check if dry run mode
            if self.settings.core.dry_run:
                logger.info(f"DRY RUN: Would execute order: {request}")
                return TradeExecution(
                    result=TradeResult.SUCCESS,
                    ticket=999999,  # Fake ticket for dry run
                    volume=volume,
                    price=current_price,
                    execution_time=datetime.now()
                )
            
            # Execute the order
            result = mt5.order_send(request)
            if result is None:
                error_code = mt5.last_error()
                error_msg = f"Order send failed: {error_code}"
                logger.error(error_msg)
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message=error_msg,
                    execution_time=datetime.now()
                )
            
            # Check result
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Order executed successfully - Ticket: {result.order}, Volume: {result.volume}, Price: {result.price}")
                
                execution = TradeExecution(
                    result=TradeResult.SUCCESS,
                    ticket=result.order,
                    volume=result.volume,
                    price=result.price,
                    execution_time=datetime.now()
                )
                
                # Store executed signal
                signal_key = f"{signal.symbol}_{signal.signal_type.value}_{int(signal.timestamp.timestamp())}"
                self._executed_signals[signal_key] = execution
                
                return execution
            
            else:
                error_msg = f"Order rejected - Return code: {result.retcode}, Comment: {result.comment}"
                logger.error(error_msg)
                return TradeExecution(
                    result=TradeResult.REJECTED,
                    error_message=error_msg,
                    execution_time=datetime.now()
                )
            
        except Exception as e:
            error_msg = f"Trade execution error: {e}"
            logger.error(error_msg)
            return TradeExecution(
                result=TradeResult.FAILED,
                error_message=error_msg,
                execution_time=datetime.now()
            )
    
    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions
        
        Returns:
            List[Position]: List of open positions
        """
        if not self.connection.ensure_connection():
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                position = Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type=OrderType(pos.type),
                    volume=pos.volume,
                    price_open=pos.price_open,
                    stop_loss=pos.sl if pos.sl != 0 else None,
                    take_profit=pos.tp if pos.tp != 0 else None,
                    current_price=pos.price_current,
                    profit=pos.profit,
                    swap=pos.swap,
                    magic_number=pos.magic,
                    comment=pos.comment,
                    time_open=datetime.fromtimestamp(pos.time) if pos.time else None
                )
                result.append(position)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def close_position(self, ticket: int) -> TradeExecution:
        """
        Close a position by ticket
        
        Args:
            ticket: Position ticket number
        
        Returns:
            TradeExecution: Result of position close
        """
        try:
            if not self.connection.ensure_connection():
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message="MT5 connection not available",
                    execution_time=datetime.now()
                )
            
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message=f"Position {ticket} not found",
                    execution_time=datetime.now()
                )
            
            pos = position[0]
            
            # Determine opposite order type
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            # Get current price
            symbol_info = self.connection.symbol_info(pos.symbol)
            if not symbol_info:
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message=f"Cannot get symbol info for {pos.symbol}",
                    execution_time=datetime.now()
                )
            
            price = symbol_info.get('bid' if close_type == mt5.ORDER_TYPE_SELL else 'ask', 0)
            
            # Build close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": self.settings.core.trading.max_slippage,
                "magic": self.settings.core.trading.magic_number,
                "comment": f"Close position {ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Check if dry run mode
            if self.settings.core.dry_run:
                logger.info(f"DRY RUN: Would close position: {request}")
                return TradeExecution(
                    result=TradeResult.SUCCESS,
                    ticket=ticket,
                    volume=pos.volume,
                    price=price,
                    execution_time=datetime.now()
                )
            
            # Execute close order
            result = mt5.order_send(request)
            if result is None:
                error_code = mt5.last_error()
                return TradeExecution(
                    result=TradeResult.FAILED,
                    error_message=f"Close order failed: {error_code}",
                    execution_time=datetime.now()
                )
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} closed successfully")
                return TradeExecution(
                    result=TradeResult.SUCCESS,
                    ticket=result.order,
                    volume=result.volume,
                    price=result.price,
                    execution_time=datetime.now()
                )
            else:
                return TradeExecution(
                    result=TradeResult.REJECTED,
                    error_message=f"Close rejected - Return code: {result.retcode}",
                    execution_time=datetime.now()
                )
            
        except Exception as e:
            logger.error(f"Error closing position {ticket}: {e}")
            return TradeExecution(
                result=TradeResult.FAILED,
                error_message=str(e),
                execution_time=datetime.now()
            )
    
    def get_trade_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get trade history for specified number of days
        
        Args:
            days: Number of days to look back
        
        Returns:
            List[Dict]: List of historical trades
        """
        if not self.connection.ensure_connection():
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get deals (executed trades)
            deals = mt5.history_deals_get(start_date, end_date)
            if deals is None:
                return []
            
            result = []
            for deal in deals:
                if deal.magic == self.settings.core.trading.magic_number:
                    trade_info = {
                        'ticket': deal.ticket,
                        'order': deal.order,
                        'symbol': deal.symbol,
                        'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                        'volume': deal.volume,
                        'price': deal.price,
                        'profit': deal.profit,
                        'swap': deal.swap,
                        'commission': deal.commission,
                        'time': datetime.fromtimestamp(deal.time),
                        'comment': deal.comment
                    }
                    result.append(trade_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return []
    
    def _calculate_risk_reward(self, signal: TradingSignal) -> float:
        """Calculate risk-reward ratio for a signal"""
        if not all([signal.entry_price, signal.stop_loss, signal.take_profit]):
            return 0.0
        
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """
        Get trading summary and statistics
        
        Returns:
            Dict: Trading summary
        """
        try:
            account_info = self.connection.get_account_info()
            positions = self.get_open_positions()
            history = self.get_trade_history(30)  # Last 30 days
            
            # Calculate statistics
            total_trades = len(history)
            profitable_trades = len([t for t in history if t['profit'] > 0])
            losing_trades = total_trades - profitable_trades
            
            total_profit = sum(t['profit'] for t in history)
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'account_balance': account_info.get('balance', 0) if account_info else 0,
                'account_equity': account_info.get('equity', 0) if account_info else 0,
                'account_margin': account_info.get('margin', 0) if account_info else 0,
                'open_positions': len(positions),
                'total_trades_30d': total_trades,
                'profitable_trades_30d': profitable_trades,
                'losing_trades_30d': losing_trades,
                'win_rate_30d': round(win_rate, 2),
                'total_profit_30d': round(total_profit, 2),
                'executed_signals': len(self._executed_signals),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get trading summary: {e}")
            return {}
