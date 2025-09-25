from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .httpClient import FinnhubHTTP
from TradeBot.logger import get_logger

log = get_logger(__name__)

# Resolutions supported by Finnhub
_ALLOWED_RESOLUTIONS = {"1", "5", "15", "30", "60", "D", "W", "M"}


def _ensure_unix(ts: Union[int, float, dt.datetime, dt.date]) -> int:
    """Convert datetime/date to Unix timestamp."""
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, dt.datetime):
        return int(ts.timestamp())
    if isinstance(ts, dt.date):
        return int(dt.datetime(ts.year, ts.month, ts.day).timestamp())
    raise TypeError("timestamp must be int(timestamp) or datetime/date.")




def support_resistance_levels(
    client: FinnhubHTTP,
    symbol: str,
    resolution: str = "15",
    start: Optional[Union[int, float, dt.datetime, dt.date]] = None,
    end: Optional[Union[int, float, dt.datetime, dt.date]] = None,
) -> Dict[str, List[float]]:
    """
    Calculate support and resistance levels based on price action.
    
    This identifies potential support/resistance using:
    - Local highs and lows (swing points)
    - Moving averages (20, 50 period)
    - Volume-weighted price levels
    - Previous significant price levels
    """
    log.debug("support_resistance_levels(symbol=%s, resolution=%s)", symbol, resolution)
    
    if start is None:
        start = dt.datetime.now() - dt.timedelta(days=100)
    if end is None:
        end = dt.datetime.now()
    
    # Get price data
    from .forex import candles
    price_df = candles(client, symbol, resolution, start, end, as_df=True)
    
    if price_df.empty:
        return {"support": [], "resistance": []}
    
    support_levels = []
    resistance_levels = []
    
    try:
        # Calculate moving averages locally
        price_df['sma_20'] = price_df['close'].rolling(window=20).mean()
        price_df['sma_50'] = price_df['close'].rolling(window=50).mean()
        
        # Add moving average levels as potential support/resistance
        sma20_levels = price_df['sma_20'].dropna().tolist()
        sma50_levels = price_df['sma_50'].dropna().tolist()
        
        support_levels.extend(sma20_levels)
        resistance_levels.extend(sma20_levels)
        support_levels.extend(sma50_levels)
        resistance_levels.extend(sma50_levels)
        
        # Find swing highs and lows (local maxima/minima)
        # Look for peaks and troughs over a rolling window
        window = min(10, len(price_df) // 4)  # Adaptive window size
        
        if window > 2:
            # Find local highs (resistance)
            for i in range(window, len(price_df) - window):
                if price_df['high'].iloc[i] == price_df['high'].iloc[i-window:i+window+1].max():
                    resistance_levels.append(price_df['high'].iloc[i])
            
            # Find local lows (support)
            for i in range(window, len(price_df) - window):
                if price_df['low'].iloc[i] == price_df['low'].iloc[i-window:i+window+1].min():
                    support_levels.append(price_df['low'].iloc[i])
        
        # Add recent significant levels
        recent_days = min(20, len(price_df))
        if recent_days > 0:
            recent_data = price_df.tail(recent_days)
            recent_high = recent_data['high'].max()
            recent_low = recent_data['low'].min()
            
            resistance_levels.append(recent_high)
            support_levels.append(recent_low)
            
            # Add weekly/monthly levels if enough data
            if len(price_df) > 30:
                weekly_high = price_df.tail(7)['high'].max()
                weekly_low = price_df.tail(7)['low'].min()
                resistance_levels.append(weekly_high)
                support_levels.append(weekly_low)
        
        # Volume-weighted average price (if volume data available)
        if 'volume' in price_df.columns and price_df['volume'].sum() > 0:
            vwap = (price_df['close'] * price_df['volume']).sum() / price_df['volume'].sum()
            support_levels.append(vwap)
            resistance_levels.append(vwap)
    
    except Exception as e:
        log.warning("Error calculating some support/resistance levels: %s", e)
        # Fallback to simple high/low levels
        if not price_df.empty:
            resistance_levels.append(price_df['high'].max())
            support_levels.append(price_df['low'].min())
    
    # Remove duplicates, filter valid levels, and sort
    support_levels = [x for x in support_levels if x is not None and not pd.isna(x)]
    resistance_levels = [x for x in resistance_levels if x is not None and not pd.isna(x)]
    
    # Remove duplicates with tolerance (combine levels that are very close)
    def consolidate_levels(levels: List[float], tolerance: float = 0.001) -> List[float]:
        if not levels:
            return []
        
        sorted_levels = sorted(set(levels))
        consolidated = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # If level is significantly different from the last consolidated level
            if abs(level - consolidated[-1]) / consolidated[-1] > tolerance:
                consolidated.append(level)
        
        return consolidated
    
    support_levels = consolidate_levels(support_levels)
    resistance_levels = consolidate_levels(resistance_levels)
    
    log.debug("support_resistance_levels: %d support, %d resistance levels", 
              len(support_levels), len(resistance_levels))
    
    # Return most relevant levels (recent and significant)
    return {
        "support": support_levels[-15:],  # Last 15 most significant support levels
        "resistance": resistance_levels[-15:]  # Last 15 most significant resistance levels
    }


def pattern_recognition(
    client: FinnhubHTTP,
    symbol: str,
    resolution: str = "D",
) -> Dict[str, Any]:
    """
    Get pattern recognition data from Finnhub.
    
    Args:
        client: FinnhubHTTP client instance
        symbol: Symbol to analyze
        resolution: Data resolution
    
    Returns:
        Pattern recognition results
    """
    log.debug("pattern_recognition(symbol=%s, resolution=%s)", symbol, resolution)
    
    # Try multiple possible endpoints for pattern recognition
    endpoints_to_try = [
        "/scan/pattern",
        "/scan/technical-analysis", 
        "/technical-analysis"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            log.debug("Trying pattern recognition endpoint: %s", endpoint)
            data = client.get(endpoint, params={
                "symbol": symbol,
                "resolution": resolution
            })
            
            log.debug("Response from %s: %s", endpoint, data)
            
            # Check if we got pattern data
            if isinstance(data, dict):
                if "points" in data or "patterns" in data or "technicalAnalysis" in data:
                    patterns = data.get("points", data.get("patterns", []))
                    if patterns:
                        log.info("Found %d patterns using endpoint %s", len(patterns), endpoint)
                        return {"points": patterns, "endpoint_used": endpoint}
                    
                    # Handle different response formats
                    if "technicalAnalysis" in data:
                        log.info("Got technical analysis data from %s", endpoint)
                        return {
                            "points": [], 
                            "technicalAnalysis": data.get("technicalAnalysis"),
                            "endpoint_used": endpoint
                        }
                        
                    # Even if no patterns, return successful response
                    log.info("No patterns found but got valid response from %s", endpoint)
                    return {"points": [], "endpoint_used": endpoint, "raw_response": data}
            
        except Exception as e:
            log.warning("Error with endpoint %s: %s", endpoint, e)
            continue
    
    # If all endpoints failed, try a basic fallback approach
    log.warning("All pattern recognition endpoints failed, trying fallback approach")
    try:
        # Try getting basic quote data to see if symbol is valid
        quote_data = client.get("/quote", params={"symbol": symbol})
        if quote_data.get("c") is not None:  # Has current price
            log.info("Symbol %s is valid (got quote), but no pattern recognition available", symbol)
            return {
                "points": [], 
                "message": "Symbol is valid but no patterns detected", 
                "quote_available": True
            }
    except Exception as e:
        log.error("Symbol validation failed: %s", e)
    
    return {
        "points": [], 
        "error": "All pattern recognition endpoints failed",
        "endpoints_tried": endpoints_to_try
    }


def simple_pattern_detection(
    client: FinnhubHTTP,
    symbol: str,
    resolution: str = "D",
    start: Optional[Union[int, float, dt.datetime, dt.date]] = None,
    end: Optional[Union[int, float, dt.datetime, dt.date]] = None,
) -> Dict[str, Any]:
    """
    Simple pattern detection using price action analysis as fallback.
    
    This provides basic pattern detection when Finnhub's pattern recognition
    API doesn't return results.
    """
    log.debug("simple_pattern_detection(symbol=%s, resolution=%s)", symbol, resolution)
    
    if start is None:
        start = dt.datetime.now() - dt.timedelta(days=50)
    if end is None:
        end = dt.datetime.now()
    
    try:
        # Get price data
        from .forex import candles
        price_df = candles(client, symbol, resolution, start, end, as_df=True)
        
        if price_df.empty:
            return {"points": [], "error": "No price data available"}
        
        patterns = []
        
        # Simple pattern detection logic
        if len(price_df) >= 20:  # Need enough data points
            
            # 1. Detect Double Top/Bottom patterns
            highs = price_df['high'].rolling(window=5, center=True).max()
            lows = price_df['low'].rolling(window=5, center=True).min()
            
            # Find local peaks (double tops)
            peaks = []
            troughs = []
            
            for i in range(2, len(price_df) - 2):
                if price_df['high'].iloc[i] == highs.iloc[i]:
                    peaks.append((i, price_df['high'].iloc[i]))
                if price_df['low'].iloc[i] == lows.iloc[i]:
                    troughs.append((i, price_df['low'].iloc[i]))
            
            # Check for double tops (two peaks at similar levels)
            if len(peaks) >= 2:
                for i in range(len(peaks) - 1):
                    for j in range(i + 1, len(peaks)):
                        peak1_idx, peak1_price = peaks[i]
                        peak2_idx, peak2_price = peaks[j]
                        
                        # Check if peaks are at similar levels (within 1%)
                        if abs(peak1_price - peak2_price) / peak1_price < 0.01:
                            # Check if there's a valley between them
                            valley_between = min(price_df['low'].iloc[peak1_idx:peak2_idx])
                            if valley_between < min(peak1_price, peak2_price) * 0.98:
                                patterns.append({
                                    "pattern": "Double Top",
                                    "time": price_df.index[peak2_idx].isoformat() if hasattr(price_df.index[peak2_idx], 'isoformat') else str(price_df.index[peak2_idx]),
                                    "price": peak2_price,
                                    "confidence": "medium",
                                    "type": "bearish"
                                })
                                break
            
            # Check for double bottoms (two troughs at similar levels)
            if len(troughs) >= 2:
                for i in range(len(troughs) - 1):
                    for j in range(i + 1, len(troughs)):
                        trough1_idx, trough1_price = troughs[i]
                        trough2_idx, trough2_price = troughs[j]
                        
                        # Check if troughs are at similar levels (within 1%)
                        if abs(trough1_price - trough2_price) / trough1_price < 0.01:
                            # Check if there's a peak between them
                            peak_between = max(price_df['high'].iloc[trough1_idx:trough2_idx])
                            if peak_between > max(trough1_price, trough2_price) * 1.02:
                                patterns.append({
                                    "pattern": "Double Bottom",
                                    "time": price_df.index[trough2_idx].isoformat() if hasattr(price_df.index[trough2_idx], 'isoformat') else str(price_df.index[trough2_idx]),
                                    "price": trough2_price,
                                    "confidence": "medium",
                                    "type": "bullish"
                                })
                                break
            
            # 2. Detect trend breakouts
            recent_data = price_df.tail(10)  # Last 10 periods
            if len(recent_data) >= 10:
                # Simple trend detection
                recent_highs = recent_data['high'].values
                recent_lows = recent_data['low'].values
                
                # Check for breakout above recent highs
                latest_high = recent_data['high'].iloc[-1]
                previous_highs = recent_highs[:-1]
                if latest_high > max(previous_highs) * 1.005:  # 0.5% breakout
                    patterns.append({
                        "pattern": "Breakout High",
                        "time": recent_data.index[-1].isoformat() if hasattr(recent_data.index[-1], 'isoformat') else str(recent_data.index[-1]),
                        "price": latest_high,
                        "confidence": "low",
                        "type": "bullish"
                    })
                
                # Check for breakdown below recent lows
                latest_low = recent_data['low'].iloc[-1]
                previous_lows = recent_lows[:-1]
                if latest_low < min(previous_lows) * 0.995:  # 0.5% breakdown
                    patterns.append({
                        "pattern": "Breakdown Low",
                        "time": recent_data.index[-1].isoformat() if hasattr(recent_data.index[-1], 'isoformat') else str(recent_data.index[-1]),
                        "price": latest_low,
                        "confidence": "low",
                        "type": "bearish"
                    })
        
        log.debug("simple_pattern_detection: found %d basic patterns", len(patterns))
        return {
            "points": patterns,
            "method": "simple_detection",
            "data_points": len(price_df)
        }
        
    except Exception as e:
        log.error("Simple pattern detection failed: %s", e)
        return {"points": [], "error": str(e)}


def get_analysis(
    client: FinnhubHTTP,
    symbol: str,
    resolution: str = "D",
    start: Optional[Union[int, float, dt.datetime, dt.date]] = None,
    end: Optional[Union[int, float, dt.datetime, dt.date]] = None,
) -> Dict[str, Any]:
    """
    Get support/resistance and pattern recognition analysis.
    
    Args:
        client: FinnhubHTTP client instance
        symbol: Symbol to analyze
        resolution: Data resolution
        start: Start time for analysis
        end: End time for analysis
    
    Returns:
        Analysis results with support/resistance levels and patterns
    """
    log.debug("get_analysis(symbol=%s)", symbol)
    
    results = {
        "symbol": symbol,
        "resolution": resolution,
        "timestamp": dt.datetime.now().isoformat(),
    }
    
    try:
        # Get support/resistance levels
        results["support_resistance"] = support_resistance_levels(
            client, symbol, resolution, start, end
        )
        
        # Get pattern recognition
        patterns = pattern_recognition(client, symbol, resolution)
        
        # If no patterns found, try simple detection as fallback
        if not patterns.get("points") and not patterns.get("error"):
            log.info("No patterns from API, trying simple detection for %s", symbol)
            simple_patterns = simple_pattern_detection(client, symbol, resolution, start, end)
            if simple_patterns.get("points"):
                patterns["fallback_patterns"] = simple_patterns
                log.info("Found %d patterns using simple detection", len(simple_patterns["points"]))
        
        results["patterns"] = patterns
        
        log.info("Analysis completed for %s", symbol)
        
    except Exception as e:
        log.error("Error in analysis: %s", e)
        results["error"] = str(e)
    
    return results
