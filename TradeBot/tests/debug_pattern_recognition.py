#!/usr/bin/env python3
"""
Debug script for pattern recognition API testing.
"""

import datetime as dt
from TradeBot.core.finnhub_data.httpClient import FinnhubHTTP
from TradeBot.core.finnhub_data.technical_analysis import pattern_recognition
from TradeBot.logger import get_logger

log = get_logger(__name__)


def test_pattern_recognition():
    """Test pattern recognition with different symbols and resolutions."""
    
    # Test symbols - mix of forex and stocks
    test_symbols = [
        "OANDA:EUR_USD",    # Original symbol
        "AAPL",             # Popular stock
        "MSFT",             # Another stock
        "OANDA:GBP_USD",    # Different forex pair
        "BINANCE:BTCUSDT",  # Crypto (if supported)
    ]
    
    # Test resolutions
    test_resolutions = ["D", "60", "15", "5"]
    
    print("🔍 Testing Pattern Recognition API")
    print("=" * 60)
    
    with FinnhubHTTP() as client:
        for symbol in test_symbols:
            print(f"\n📊 Testing symbol: {symbol}")
            print("-" * 40)
            
            for resolution in test_resolutions:
                try:
                    print(f"  Resolution: {resolution}")
                    result = pattern_recognition(client, symbol, resolution)
                    
                    if result:
                        patterns = result.get("points", [])
                        endpoint_used = result.get("endpoint_used", "unknown")
                        
                        print(f"    ✅ Endpoint: {endpoint_used}")
                        print(f"    📈 Patterns found: {len(patterns)}")
                        
                        if patterns:
                            print(f"    🎯 First pattern: {patterns[0]}")
                            break  # Found patterns, move to next symbol
                        
                        # Check for other data
                        if "technicalAnalysis" in result:
                            print(f"    📊 Technical Analysis available")
                        if "message" in result:
                            print(f"    💬 Message: {result['message']}")
                        if "raw_response" in result:
                            raw = result["raw_response"]
                            print(f"    📄 Raw keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
                    else:
                        print(f"    ❌ No result returned")
                        
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    
            print()


def test_direct_api_calls():
    """Test direct API calls to see raw responses."""
    
    print("\n🔧 Direct API Testing")
    print("=" * 60)
    
    symbol = "AAPL"  # Use a popular stock symbol
    
    endpoints_to_test = [
        "/scan/pattern",
        "/scan/technical-analysis",
        "/technical-analysis",
        "/stock/pattern",
        "/quote"  # For comparison
    ]
    
    with FinnhubHTTP() as client:
        for endpoint in endpoints_to_test:
            print(f"\n🌐 Testing endpoint: {endpoint}")
            try:
                if endpoint == "/quote":
                    data = client.get(endpoint, params={"symbol": symbol})
                else:
                    data = client.get(endpoint, params={"symbol": symbol, "resolution": "D"})
                
                print(f"  ✅ Response type: {type(data)}")
                if isinstance(data, dict):
                    print(f"  📊 Keys: {list(data.keys())}")
                    
                    # Show first few items of any lists
                    for key, value in data.items():
                        if isinstance(value, list):
                            print(f"    {key}: {len(value)} items")
                            if value:
                                print(f"      First item: {value[0]}")
                        elif isinstance(value, dict):
                            print(f"    {key}: dict with keys {list(value.keys())}")
                        else:
                            print(f"    {key}: {value}")
                else:
                    print(f"  📄 Data: {data}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Starting Pattern Recognition Debug")
    print("=" * 60)
    
    test_pattern_recognition()
    test_direct_api_calls()
    
    print("\n" + "=" * 60)
    print("✅ Debug testing completed!")
    print("Check the logs above for detailed information.")
    print("\n💡 Tips:")
    print("  • If no patterns found, try different symbols (stocks vs forex)")
    print("  • Different resolutions may show different patterns")
    print("  • Check if your Finnhub plan supports pattern recognition")
    print("  • Pattern recognition may not always have data available")
