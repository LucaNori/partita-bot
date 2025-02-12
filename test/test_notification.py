#!/usr/bin/env python3
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fetcher import MatchFetcher

async def simulate_notification(city: str, test_date: datetime):
    """Simulate what a user would receive as a notification."""
    fetcher = MatchFetcher()
    
    print(f"Simulating notification for {city}")
    print(f"Date: {test_date.strftime('%Y-%m-%d')}")
    print("Time of notification: 07:00 (user's local time)")
    
    # Check if we have cached data
    cache_file = os.path.join(fetcher.data_dir, f'matches_{test_date.strftime("%Y-%m-%d")}.json')
    cache_status = "Using cached data" if os.path.exists(cache_file) else "No cache found, will fetch from API"
    print(f"Cache status: {cache_status}")
    
    print("\nNotification content:")
    print("-" * 50)
    
    # Get matches and format the message
    matches = fetcher.get_matches_for_city(city, test_date)
    message = fetcher.format_match_message(matches)
    
    print(message)
    print("-" * 50)

async def main():
    # Test both dates
    test_dates = [
        datetime(2025, 2, 14, tzinfo=ZoneInfo('Europe/Rome')),  # Bologna match
        datetime(2025, 2, 16, tzinfo=ZoneInfo('Europe/Rome'))   # Parma match
    ]
    
    # Test different case variations for cities
    test_cities = [
        'Parma',  # Title case
        'parma',  # Lower case
        'PARMA',  # Upper case
        'PaRmA',  # Mixed case
        'bologna'  # Control case - we know this one has a match on 14th
    ]
    
    # First run - should fetch from API
    print("=== First run (should fetch from API) ===")
    for test_date in test_dates:
        print(f"\n=== Testing for date: {test_date.strftime('%Y-%m-%d')} ===\n")
        for city in test_cities:
            print("\n")
            await simulate_notification(city, test_date)
            
    # Second run - should use cache
    print("\n=== Second run (should use cache) ===")
    for test_date in test_dates:
        print(f"\n=== Testing for date: {test_date.strftime('%Y-%m-%d')} ===\n")
        for city in test_cities:
            print("\n")
            await simulate_notification(city, test_date)

if __name__ == "__main__":
    asyncio.run(main())