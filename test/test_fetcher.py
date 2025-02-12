#!/usr/bin/env python3
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fetcher import MatchFetcher

def main():
    # Initialize the fetcher
    fetcher = MatchFetcher()
    
    # Test date (February 14, 2025)
    test_date = datetime(2025, 2, 14, tzinfo=ZoneInfo('Europe/Rome'))
    
    # Test cities
    test_cities = ['milano', 'roma', 'bologna', 'napoli']
    
    print(f"Testing match fetcher for date: {test_date.strftime('%Y-%m-%d')}\n")
    
    for city in test_cities:
        print(f"Checking matches in {city.upper()}:")
        matches = fetcher.get_matches_for_city(city, test_date)
        message = fetcher.format_match_message(matches)
        print(f"{message}\n")

if __name__ == "__main__":
    main()