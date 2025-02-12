#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

def get_team_city(team_name):
    """Map team names directly to their home cities."""
    team_cities = {
        "Milan": "milano",
        "Inter": "milano",
        "Roma": "roma",
        "Lazio": "roma",
        "Napoli": "napoli",
        "Juventus": "torino",
        "Torino": "torino",
        "Fiorentina": "firenze",
        "Genoa": "genova",
        "Sampdoria": "genova",
        "Bologna": "bologna",
        "Hellas Verona": "verona",
        "Verona": "verona",
        "Atalanta": "bergamo",
        "Udinese": "udine",
        "Sassuolo": "reggio_emilia",
        "Empoli": "empoli",
        "Lecce": "lecce",
        "Salernitana": "salerno",
        "Frosinone": "frosinone",
        "Cagliari": "cagliari",
        "Parma": "parma"
    }
    return team_cities.get(team_name)

def format_time(utc_time_str):
    """Convert UTC time string to both UTC and Rome time."""
    utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
    rome_time = utc_time.astimezone(ZoneInfo('Europe/Rome'))
    return {
        'utc': utc_time.strftime('%H:%M'),
        'local': rome_time.strftime('%H:%M'),
        'datetime': rome_time
    }

def is_match_today(match_datetime, rome_today):
    """Check if a match is happening today (Rome time)."""
    match_date = match_datetime.date()
    return match_date == rome_today.date()

def main():
    # Load environment variables
    load_dotenv()
    api_token = os.getenv('FOOTBALL_API_TOKEN')
    if not api_token:
        print("Error: FOOTBALL_API_TOKEN not found in .env file")
        return

    # API configuration
    headers = {
        'X-Auth-Token': api_token
    }
    base_url = "http://api.football-data.org/v4"

    # For testing: use a specific date (February 14, 2025)
    test_date = datetime(2025, 2, 14, tzinfo=ZoneInfo('Europe/Rome'))
    
    # Get date range (yesterday to tomorrow)
    yesterday = (test_date - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (test_date + timedelta(days=1)).strftime('%Y-%m-%d')

    try:
        url = f"{base_url}/matches"
        params = {
            'dateFrom': yesterday,
            'dateTo': tomorrow,
            'areas': 2114  # Italy
        }
        
        print(f"Fetching matches between {yesterday} and {tomorrow}")
        print(f"Will filter for date: {test_date.strftime('%Y-%m-%d')}")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Save raw response to file
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(test_data_dir, exist_ok=True)
        with open(os.path.join(test_data_dir, 'fetcher_test.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nRaw API response saved to test/data/fetcher_test.json")

        # Process Serie A matches
        print("\nSerie A matches found:")
        matches_by_city = {}
        total_matches = 0
        filtered_matches = 0
        
        for match in data.get('matches', []):
            if match.get('competition', {}).get('code') == 'SA':
                total_matches += 1
                # Convert match time and verify it's today
                times = format_time(match.get('utcDate'))
                if not is_match_today(times['datetime'], test_date):
                    continue

                filtered_matches += 1
                home_team = match.get('homeTeam', {})
                away_team = match.get('awayTeam', {})
                home_name = home_team.get('shortName')
                city = get_team_city(home_name)
                
                if city:
                    match_info = {
                        'home': home_name,
                        'away': away_team.get('shortName', 'Unknown'),
                        'time_utc': times['utc'],
                        'time_local': times['local'],
                        'status': match.get('status')
                    }
                    
                    if city not in matches_by_city:
                        matches_by_city[city] = []
                    matches_by_city[city].append(match_info)

        print(f"\nFound {total_matches} total Serie A matches in date range")
        print(f"Filtered to {filtered_matches} matches for {test_date.strftime('%Y-%m-%d')}\n")

        if matches_by_city:
            # Print matches grouped by city
            for city, matches in sorted(matches_by_city.items()):
                print(f"\n{city.upper()}:")
                for match in matches:
                    print(f"- {match['home']} vs {match['away']}")
                    print(f"  Time: {match['time_local']} (CET)")
                    print(f"  Status: {match['status']}")
        else:
            print("No Serie A matches scheduled for this date")

    except requests.RequestException as e:
        print(f"Error making API request: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()