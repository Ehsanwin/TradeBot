#!/usr/bin/env python3
"""
Example usage of the technical analysis module for support/resistance and pattern recognition.
"""

import datetime as dt
from TradeBot.core.finnhub_data.httpClient import FinnhubHTTP
from TradeBot.core.finnhub_data.technical_analysis import (
    support_resistance_levels,
    pattern_recognition,
    get_analysis
)
from TradeBot.logger import get_logger

log = get_logger(__name__)


def main():
    """Example usage of support/resistance and pattern recognition functions."""
    
    # Initialize Finnhub client
    with FinnhubHTTP() as client:
        symbol = "OANDA:EUR_USD"  # EUR/USD forex pair
        
        # Set time range (last 100 days)
        end_time = dt.datetime.now()
        start_time = end_time - dt.timedelta(days=100)
        
        print(f"🔍 Technical Analysis for {symbol}")
        print("=" * 50)
        
        # 1. Get Support and Resistance Levels
        print("\n🎯 Support & Resistance Analysis:")
        try:
            sr_levels = support_resistance_levels(
                client, symbol, resolution="D", start=start_time, end=end_time
            )
            
            support_count = len(sr_levels['support'])
            resistance_count = len(sr_levels['resistance'])
            
            print(f"  📊 Found {support_count} support levels and {resistance_count} resistance levels")
            
            if support_count > 0:
                print(f"\n  📉 Key Support Levels:")
                for i, level in enumerate(sr_levels['support'][-5:], 1):  # Show last 5
                    print(f"    {i}. {level:.5f}")
            
            if resistance_count > 0:
                print(f"\n  📈 Key Resistance Levels:")
                for i, level in enumerate(sr_levels['resistance'][-5:], 1):  # Show last 5
                    print(f"    {i}. {level:.5f}")
            
            # Get current price for context
            from TradeBot.core.finnhub_data.forex import quote
            try:
                current_quote = quote(client, symbol)
                current_price = current_quote.get('c')  # current price
                
                if current_price:
                    print(f"\n  💰 Current Price: {current_price:.5f}")
                    
                    # Find nearest support and resistance
                    supports_below = [s for s in sr_levels['support'] if s < current_price]
                    resistances_above = [r for r in sr_levels['resistance'] if r > current_price]
                    
                    if supports_below:
                        nearest_support = max(supports_below)
                        distance_to_support = ((current_price - nearest_support) / current_price) * 100
                        print(f"  📉 Nearest Support: {nearest_support:.5f} ({distance_to_support:.2f}% below)")
                    
                    if resistances_above:
                        nearest_resistance = min(resistances_above)
                        distance_to_resistance = ((nearest_resistance - current_price) / current_price) * 100
                        print(f"  📈 Nearest Resistance: {nearest_resistance:.5f} ({distance_to_resistance:.2f}% above)")
                        
            except Exception as e:
                print(f"  ℹ️  Could not get current price: {e}")
                
        except Exception as e:
            print(f"  ❌ Error getting support/resistance levels: {e}")
        
        # 2. Pattern Recognition
        print("\n🔍 Pattern Recognition:")
        try:
            patterns = pattern_recognition(client, symbol, resolution="D")
            
            if patterns.get('points') and len(patterns['points']) > 0:
                print(f"  📈 Found {len(patterns['points'])} chart patterns:")
                
                for i, pattern in enumerate(patterns['points'][:5], 1):  # Show first 5
                    if isinstance(pattern, dict):
                        pattern_type = pattern.get('patternname', 'Unknown')
                        pattern_time = pattern.get('time', 'Unknown')
                        print(f"    {i}. {pattern_type} (Time: {pattern_time})")
                    else:
                        print(f"    {i}. {pattern}")
                        
                if len(patterns['points']) > 5:
                    print(f"    ... and {len(patterns['points']) - 5} more patterns")
                    
            else:
                print("  📋 No chart patterns detected at this time")
                print("  ℹ️  This could mean:")
                print("     • No clear patterns in recent price action")
                print("     • Pattern detection data temporarily unavailable")
                print("     • Symbol may not support pattern recognition")
                
        except Exception as e:
            print(f"  ❌ Error getting pattern recognition: {e}")
        
        # 3. Combined Analysis
        print("\n🔬 Combined Analysis:")
        try:
            analysis = get_analysis(
                client, symbol, resolution="D", start=start_time, end=end_time
            )
            
            print(f"  🎯 Symbol: {analysis.get('symbol', 'N/A')}")
            print(f"  📅 Analysis Time: {analysis.get('timestamp', 'N/A')}")
            print(f"  📊 Resolution: {analysis.get('resolution', 'N/A')}")
            
            # Summary
            sr = analysis.get('support_resistance', {})
            patterns = analysis.get('patterns', {})
            
            print(f"\n  📊 Summary:")
            print(f"     • Support Levels: {len(sr.get('support', []))}")
            print(f"     • Resistance Levels: {len(sr.get('resistance', []))}")
            print(f"     • Detected Patterns: {len(patterns.get('points', []))}")
            
            # Trading insights
            print(f"\n  💡 Trading Insights:")
            support_levels = sr.get('support', [])
            resistance_levels = sr.get('resistance', [])
            
            if len(support_levels) > 0 and len(resistance_levels) > 0:
                # Calculate average distance between levels
                all_levels = sorted(support_levels + resistance_levels)
                if len(all_levels) > 1:
                    distances = [all_levels[i+1] - all_levels[i] for i in range(len(all_levels)-1)]
                    avg_distance = sum(distances) / len(distances)
                    print(f"     • Average level spacing: {avg_distance:.5f}")
                    
                # Identify consolidation zones
                tight_ranges = [d for d in distances if d < avg_distance * 0.5]
                if tight_ranges:
                    print(f"     • Potential consolidation zones detected")
                    
            if patterns.get('points'):
                print(f"     • Recent pattern activity suggests increased volatility")
            else:
                print(f"     • No recent patterns - price action may be in consolidation")
                
        except Exception as e:
            print(f"  ❌ Error getting combined analysis: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Analysis completed!")
        print("ℹ️  Use this data to identify potential entry/exit points")
        print("⚠️  Always combine with other analysis methods and risk management")


if __name__ == "__main__":
    main()
