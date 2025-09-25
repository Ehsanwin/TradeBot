#!/usr/bin/env python3
"""
News Configuration Script for Trading Bot

This script helps you configure and test the news functionality.
Run this to set up your news sources and test if they work.
"""

import os
import sys
from typing import List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_environment():
    """Set up environment variables for news sources"""
    
    # ForexFactory JSON export URL (free alternative endpoints)
    ff_urls = [
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "https://www.forexfactory.com/calendar.php?week=this",
        ""  # User can add their own
    ]
    
    # Investing.com RSS feeds
    investing_feeds = [
        "https://www.investing.com/rss/news.rss",
        "https://www.investing.com/rss/economic_indicators.rss", 
        "https://www.investing.com/rss/news_301.rss",  # Economic News
        "https://www.investing.com/rss/news_95.rss",   # Forex News
    ]
    
    print("=== Trading Bot News Configuration ===\n")
    
    # Set ForexFactory URL
    print("1. ForexFactory Configuration:")
    print("   Available options:")
    for i, url in enumerate(ff_urls):
        if url:
            print(f"   [{i+1}] {url}")
        else:
            print(f"   [{i+1}] Custom URL")
    
    choice = input("\n   Select ForexFactory source (1-3, or press Enter for default): ").strip()
    if choice and choice.isdigit() and 1 <= int(choice) <= len(ff_urls):
        ff_url = ff_urls[int(choice)-1]
        if not ff_url:
            ff_url = input("   Enter custom ForexFactory JSON URL: ").strip()
    else:
        ff_url = ff_urls[0]  # Default
    
    if ff_url:
        os.environ["FF_EXPORT_JSON_URL"] = ff_url
        print(f"   ✓ Set FF_EXPORT_JSON_URL = {ff_url}")
    
    # Set Investing RSS URLs
    print("\n2. Investing.com RSS Configuration:")
    print("   Available RSS feeds:")
    for i, url in enumerate(investing_feeds):
        print(f"   [{i+1}] {url}")
    
    selection = input("\n   Select feeds (e.g., '1,2,3' or press Enter for all): ").strip()
    if selection:
        try:
            indices = [int(x.strip())-1 for x in selection.split(',')]
            selected_feeds = [investing_feeds[i] for i in indices if 0 <= i < len(investing_feeds)]
        except:
            selected_feeds = investing_feeds  # Default to all
    else:
        selected_feeds = investing_feeds  # Default to all
    
    if selected_feeds:
        rss_urls = ",".join(selected_feeds)
        os.environ["INVESTING_RSS_URLS"] = rss_urls
        print(f"   ✓ Set INVESTING_RSS_URLS = {len(selected_feeds)} feeds")
    
    # Other settings
    os.environ["NEWS_ENABLED"] = "true"
    os.environ["NEWS_REQUEST_TIMEOUT"] = "15"
    os.environ["NEWS_RETRIES"] = "2"
    os.environ["REFRESH_INTERVAL_MIN"] = "15"
    
    print("\n✓ Environment variables configured!")

def test_news_sources():
    """Test news source functionality"""
    try:
        from TradeBot.core.news.service import NewsService
        
        print("\n=== Testing News Sources ===")
        
        # Initialize service
        svc = NewsService()
        print(f"News service enabled: {svc.enabled}")
        print(f"Configured sources: {sorted(svc.sources)}")
        print(f"Initialized clients: {len(svc.clients)}")
        
        # Test fetching
        print("\nFetching news...")
        items = svc.fetch_all()
        
        print(f"✓ Successfully fetched {len(items)} news items")
        
        if items:
            print("\nSample news items:")
            for i, item in enumerate(items[:5], 1):
                print(f"{i:2d}. {item.title[:60]}...")
                print(f"     Source: {item.source}, Importance: {item.importance}")
                print(f"     Time: {item.t}")
        
        return items
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running this from the project root directory.")
        return []
    except Exception as e:
        print(f"✗ Error testing news sources: {e}")
        return []

def test_api_endpoints():
    """Test the news API endpoints"""
    try:
        print("\n=== Testing API Endpoints ===")
        print("You can test these endpoints when your Flask app is running:")
        print()
        print("1. Fetch news:")
        print("   GET  http://localhost:5000/api/v1/news/fetch")
        print("   POST http://localhost:5000/api/v1/news/fetch")
        print()
        print("2. List news (requires database):")
        print("   GET  http://localhost:5000/api/v1/news/list")
        print("   GET  http://localhost:5000/api/v1/news/list?limit=10&min_importance=2")
        print()
        print("To start the Flask app with news configured:")
        print("   python TradeBot/main.py")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    """Main configuration function"""
    try:
        setup_environment()
        items = test_news_sources()
        
        if items:
            print(f"\n🎉 News system is working! Fetched {len(items)} items.")
            test_api_endpoints()
        else:
            print("\n❌ No news items fetched. Check your internet connection and URLs.")
            
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
