#!/usr/bin/env python3
"""
Test script for ChatGPT News Service

This script tests the new ChatGPT-based news generation system.
Make sure to set your OPENAI_API_KEY environment variable before running.

Usage:
    python TradeBot/test_chatgpt_news.py
"""

import os
import sys
from datetime import datetime
from typing import List

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from TradeBot.logger import setup_logging, get_logger
from TradeBot.core.news.service import NewsService
from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
from TradeBot.core.news.types import NormalizedNews

# Setup logging
setup_logging()
log = get_logger(__name__)

def test_chatgpt_client_direct():
    """Test ChatGPT client directly"""
    print("=" * 60)
    print("TESTING CHATGPT CLIENT DIRECTLY")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        # Create ChatGPT client
        client = ChatGPTNewsClient(
            api_key=api_key,
            model="gpt-4o-mini",
            max_news_items=5  # Generate fewer items for testing
        )
        
        print(f"✓ ChatGPT client created successfully")
        print(f"  Model: {client.model}")
        print(f"  Max items: {client.max_news_items}")
        print()
        
        # Fetch news
        print("Fetching news from ChatGPT...")
        news_items = client.fetch()
        
        if not news_items:
            print("❌ No news items received from ChatGPT")
            return False
        
        print(f"✓ Successfully fetched {len(news_items)} news items")
        print()
        
        # Display news items
        for i, item in enumerate(news_items, 1):
            print(f"📰 News Item #{i}")
            print(f"   Title: {item.title}")
            print(f"   Source: {item.source}")
            print(f"   Importance: {item.importance}/3")
            print(f"   Country: {item.country or 'N/A'}")
            print(f"   Currency: {item.currency or 'N/A'}")
            print(f"   Category: {item.category or 'N/A'}")
            print(f"   Time: {datetime.fromtimestamp(item.t).strftime('%Y-%m-%d %H:%M:%S') if item.t else 'N/A'}")
            if item.body:
                print(f"   Body: {item.body[:100]}{'...' if len(item.body) > 100 else ''}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ChatGPT client: {e}")
        return False

def test_news_service():
    """Test NewsService with ChatGPT integration"""
    print("=" * 60)
    print("TESTING NEWS SERVICE WITH CHATGPT")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        return False
    
    try:
        # Create news service
        service = NewsService()
        
        print(f"✓ NewsService created")
        print(f"  Enabled: {service.enabled}")
        print(f"  Sources: {sorted(service.sources)}")
        print(f"  Clients: {len(service.clients)}")
        print()
        
        if not service.clients:
            print("❌ No news clients configured!")
            print("Make sure NEWS_SOURCES environment variable includes 'chatgpt'")
            return False
        
        # Fetch news
        print("Fetching news via NewsService...")
        news_items = service.fetch_all()
        
        if not news_items:
            print("❌ No news items received via NewsService")
            return False
        
        print(f"✓ Successfully fetched {len(news_items)} news items via NewsService")
        print()
        
        # Display summary
        sources = {}
        importance_counts = {1: 0, 2: 0, 3: 0}
        
        for item in news_items:
            sources[item.source] = sources.get(item.source, 0) + 1
            importance_counts[item.importance] = importance_counts.get(item.importance, 0) + 1
        
        print("📊 News Summary:")
        print(f"   Total items: {len(news_items)}")
        print(f"   By source: {sources}")
        print(f"   By importance: High={importance_counts[3]}, Medium={importance_counts[2]}, Low={importance_counts[1]}")
        print()
        
        # Test persistence (optional)
        persist_test = input("Do you want to test database persistence? (y/N): ").strip().lower()
        if persist_test == 'y':
            try:
                saved_count = service.persist(news_items)
                print(f"✓ Successfully saved {saved_count} news items to database")
            except Exception as e:
                print(f"⚠️  Database persistence test failed: {e}")
                print("This is normal if database is not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing NewsService: {e}")
        return False

def main():
    """Main test function"""
    print("ChatGPT News Service Test")
    print("=" * 60)
    print(f"Current time: {datetime.now()}")
    print()
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set!")
        print()
        print("To fix this:")
        print("1. Get your OpenAI API key from https://platform.openai.com/api-keys")
        print("2. Set the environment variable:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("3. Run this test again")
        return
    
    print(f"✓ OpenAI API key found (length: {len(api_key)})")
    print()
    
    # Run tests
    success1 = test_chatgpt_client_direct()
    print()
    
    success2 = test_news_service()
    print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Direct ChatGPT Client Test: {'✓ PASSED' if success1 else '❌ FAILED'}")
    print(f"NewsService Integration Test: {'✓ PASSED' if success2 else '❌ FAILED'}")
    print()
    
    if success1 and success2:
        print("🎉 All tests passed! Your ChatGPT news service is working correctly.")
        print()
        print("Next steps:")
        print("1. Start the main TradeBot application")
        print("2. Use the /api/v1/news/fetch endpoint to fetch news")
        print("3. Use the /api/v1/news/list endpoint to view saved news")
    else:
        print("❌ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
