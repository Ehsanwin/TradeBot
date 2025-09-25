#!/usr/bin/env python3
"""
Quick test to validate the fast system is working
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_openai_api():
    """Test OpenAI API with correct parameters"""
    try:
        from LLM.config.settings import get_llm_settings
        from LLM.core.openai_client import OpenAIHTTPClient, ChatMessage
        
        settings = get_llm_settings()
        if not settings.openai_api_key:
            print("❌ No OpenAI API key configured")
            return False
        
        client = OpenAIHTTPClient(
            api_key=settings.openai_api_key,
            timeout=20,
            retries=1
        )
        
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Say 'API test successful' in JSON format: {\"result\": \"API test successful\"}")
        ]
        
        print("🧪 Testing OpenAI API...")
        response = client.chat_completion(
            messages=messages,
            model="gpt-4o-mini"
        )
        
        print(f"✅ OpenAI API working: {response.content[:50]}...")
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def test_tradebot_api():
    """Test TradeBot API endpoints"""
    try:
        import requests
        
        print("🧪 Testing TradeBot API...")
        
        # Test health
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ TradeBot API health: OK")
        else:
            print(f"⚠️ TradeBot API health: {response.status_code}")
        
        # Test quotes (fast endpoint)
        response = requests.get(
            "http://127.0.0.1:5000/api/v1/forex/quote", 
            params={'names': 'EURUSD'},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('data'):
                print(f"✅ Forex quotes working: {len(data['data'])} quotes")
            else:
                print(f"⚠️ Forex quotes: {data}")
        else:
            print(f"❌ Forex quotes failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ TradeBot API test failed: {e}")
        return False

def test_fast_system():
    """Test the fast analysis system with minimal data"""
    try:
        from LLM.fast_main import FastLLMTradingSystem
        
        print("🧪 Testing Fast LLM System...")
        
        system = FastLLMTradingSystem()
        system.initialize_services()
        
        # Test with single symbol for speed
        results = system.run_fast_analysis(
            symbols=["OANDA:EUR_USD"],
            max_symbols=1
        )
        
        if results.get("success"):
            print(f"✅ Fast analysis successful in {results.get('analysis_time')}")
            print(f"   Signals: {results.get('total_signals')}")
            return True
        else:
            print(f"❌ Fast analysis failed: {results.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Fast system test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Quick System Test")
    print("=" * 30)
    
    tests = [
        ("TradeBot API", test_tradebot_api),
        ("OpenAI API", test_openai_api),
        ("Fast LLM System", test_fast_system)
    ]
    
    passed = 0
    for name, test_func in tests:
        try:
            print(f"\n🧪 {name}:")
            if test_func():
                passed += 1
            else:
                print(f"❌ {name} test failed")
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
    
    print("\n" + "=" * 30)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! System is ready.")
    else:
        print("⚠️ Some tests failed. Check the issues above.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
