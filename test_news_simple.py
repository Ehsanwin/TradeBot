#!/usr/bin/env python3
"""
Simple News Tester - Test news functionality without database requirements

This script allows you to test the news fetching functionality independently
of the database connection requirements.
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_test_environment():
    """Set up test environment with working news URLs"""
    
    # Set up working URLs for testing
    os.environ["FF_EXPORT_JSON_URL"] = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    os.environ["INVESTING_RSS_URLS"] = "https://www.investing.com/rss/news.rss,https://www.investing.com/rss/economic_indicators.rss"
    
    # Basic settings
    os.environ["NEWS_ENABLED"] = "true"
    os.environ["NEWS_REQUEST_TIMEOUT"] = "15"
    os.environ["NEWS_RETRIES"] = "2"
    os.environ["NEWS_MAX_ITEMS_PER_SOURCE"] = "50"
    os.environ["NEWS_IMPORTANCE_DEFAULT"] = "2"

def format_news_item(item, index: int) -> str:
    """Format a news item for display"""
    timestamp = datetime.fromtimestamp(item.t).strftime('%Y-%m-%d %H:%M:%S UTC')
    importance_map = {1: "Low", 2: "Medium", 3: "High"}
    importance_str = importance_map.get(item.importance, "Unknown")
    
    return f"""
{index:2d}. {item.title}
    Source: {item.source}
    Time: {timestamp}
    Importance: {importance_str} ({item.importance})
    Country: {item.country or 'N/A'}
    Currency: {item.currency or 'N/A'}
    Category: {item.category or 'N/A'}
    URL: {item.url or 'N/A'}
    """.strip()

def analyze_news_items(items: List) -> Dict[str, Any]:
    """Analyze fetched news items"""
    if not items:
        return {}
    
    sources = {}
    importance_counts = {1: 0, 2: 0, 3: 0}
    currencies = {}
    countries = {}
    
    for item in items:
        # Count by source
        sources[item.source] = sources.get(item.source, 0) + 1
        
        # Count by importance
        importance_counts[item.importance] = importance_counts.get(item.importance, 0) + 1
        
        # Count by currency
        if item.currency:
            currencies[item.currency] = currencies.get(item.currency, 0) + 1
            
        # Count by country
        if item.country:
            countries[item.country] = countries.get(item.country, 0) + 1
    
    return {
        'total_items': len(items),
        'sources': sources,
        'importance': importance_counts,
        'currencies': dict(sorted(currencies.items(), key=lambda x: x[1], reverse=True)[:10]),
        'countries': dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
    }

def main():
    """Main test function"""
    print("=== Simple News Functionality Test ===\n")
    
    try:
        # Setup environment
        setup_test_environment()
        print("✓ Test environment configured")
        
        # Import and test news service
        from TradeBot.core.news.service import NewsService
        
        print("✓ News service imported successfully")
        
        # Initialize service
        svc = NewsService()
        print(f"✓ News service initialized")
        print(f"  - Enabled: {svc.enabled}")
        print(f"  - Sources: {sorted(svc.sources)}")
        print(f"  - Clients: {len(svc.clients)} ({[type(c).__name__ for c in svc.clients]})")
        
        # Fetch news
        print("\n--- Fetching News ---")
        items = svc.fetch_all()
        print(f"✓ Fetched {len(items)} news items")
        
        if not items:
            print("❌ No news items were fetched!")
            print("   This could be due to:")
            print("   - Network connectivity issues")
            print("   - Invalid or unreachable news source URLs")
            print("   - Temporary server issues")
            return
        
        # Analyze results
        analysis = analyze_news_items(items)
        
        print("\n--- Analysis ---")
        print(f"Total items: {analysis['total_items']}")
        print(f"Sources: {analysis['sources']}")
        print(f"Importance distribution: {analysis['importance']}")
        if analysis['currencies']:
            print(f"Top currencies: {list(analysis['currencies'].keys())[:5]}")
        if analysis['countries']:
            print(f"Top countries: {list(analysis['countries'].keys())[:5]}")
        
        # Show sample items
        print(f"\n--- Sample News Items (showing up to 5) ---")
        for i, item in enumerate(items[:5], 1):
            print(format_news_item(item, i))
            print()
        
        # Success message
        print("🎉 NEWS SYSTEM IS WORKING! 🎉")
        print(f"Successfully fetched {len(items)} news items from {len(analysis['sources'])} sources.")
        print("\nTo use this in your trading bot:")
        print("1. Set the environment variables shown in this script")
        print("2. Make sure your database is running if you want to persist news")
        print("3. Start your Flask application: python TradeBot/main.py")
        print("4. Access news via API endpoints:")
        print("   - GET /api/v1/news/fetch (fetch fresh news)")
        print("   - GET /api/v1/news/list (list stored news)")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running this from the project root directory.")
        print("Current directory:", os.getcwd())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
