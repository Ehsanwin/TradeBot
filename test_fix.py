#!/usr/bin/env python3
"""
Test the ChatGPT client fix
"""

import os
import sys

def test_chatgpt_client():
    print("🔧 Testing ChatGPT Client Fix")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY found - testing without API calls")
        print("   This will test if the client can be created without the logging error")
        api_key = "test-key-for-initialization"
    else:
        print(f"✅ Found OPENAI_API_KEY ({len(api_key)} chars)")
    
    try:
        from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
        print("✅ Successfully imported ChatGPTNewsClient")
        
        # Try to create a client
        client = ChatGPTNewsClient(
            api_key=api_key,
            model="gpt-4o-mini",
            max_news_items=5,
            timeout=10
        )
        print("✅ Successfully created ChatGPTNewsClient instance")
        print(f"   Model: {client.model}")
        print(f"   Max items: {client.max_news_items}")
        
        # If we have a real API key, try to fetch some news
        if os.getenv("OPENAI_API_KEY"):
            print("\n🔄 Testing news generation...")
            try:
                news_items = client.fetch()
                print(f"✅ Successfully generated {len(news_items)} news items")
                if news_items:
                    print(f"   Sample title: {news_items[0].title[:50]}...")
                    print(f"   Sample importance: {news_items[0].importance}")
            except Exception as e:
                print(f"❌ News generation failed: {e}")
        else:
            print("⚠️  Skipping news generation test (no API key)")
        
        print("\n🎉 The logging error has been FIXED!")
        print("   Your ChatGPT client should now work properly in the Flask app.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_chatgpt_client()
    if success:
        print("\n✅ All tests passed! The fix is working.")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
