from datetime import datetime
import requests
from typing import List, Dict, Any, Optional
import config
import yaml
import os

class MatchFetcher:
    def __init__(self):
        self.headers = config.FOOTBALL_API_HEADERS
        self.base_url = config.FOOTBALL_API_BASE_URL
        self.stadiums_config = self._load_stadiums_config()

    def _load_stadiums_config(self) -> dict:
        """Load stadiums configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), 'stadiums.yml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_area_id_by_city(self, city: str) -> Optional[int]:
        """
        Get the area ID for a given Italian city.
        
        Args:
            city (str): The city name
            
        Returns:
            Optional[int]: The area ID if found, None otherwise
        """
        area_ids = self.stadiums_config.get('area_ids', {})
        return area_ids.get(city.lower())

    def _get_stadium_by_city(self, city: str) -> List[str]:
        """
        Get the stadium names for a given Italian city.
        
        Args:
            city (str): The city name
            
        Returns:
            List[str]: List of stadium names in that city
        """
        stadiums = self.stadiums_config.get('stadiums', {})
        return stadiums.get(city.lower(), [])

    def get_matches_for_city(self, city: str) -> List[Dict[str, Any]]:
        """
        Fetch matches for a specific city on the current date.
        
        Args:
            city (str): The city to check for matches
            
        Returns:
            List[Dict[str, Any]]: List of matches in the city for today
        """
        area_id = self._get_area_id_by_city(city)
        if not area_id:
            return []

        stadiums = self._get_stadium_by_city(city)
        if not stadiums:
            return []

        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Get all matches for today in the Italian league
            url = f"{self.base_url}/matches"
            params = {
                'dateFrom': today,
                'dateTo': today,
                'areas': area_id
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Filter matches by stadium
            matches = []
            for match in data.get('matches', []):
                if match.get('venue') in stadiums:
                    matches.append({
                        'home': match['homeTeam']['shortName'] or match['homeTeam']['name'],
                        'away': match['awayTeam']['shortName'] or match['awayTeam']['name'],
                        'time': datetime.fromisoformat(match['utcDate']).strftime('%H:%M'),
                        'venue': match['venue']
                    })
            
            return matches
            
        except requests.RequestException as e:
            print(f"Error fetching matches: {str(e)}")
            return []

    def format_match_message(self, matches: List[Dict[str, Any]]) -> str:
        """
        Format matches into a readable message.
        
        Args:
            matches (list): List of matches to format
            
        Returns:
            str: Formatted message about the matches
        """
        if not matches:
            return "Non ci sono partite oggi nella tua città! ⚽️"
        
        message = "🎯 Oggi nella tua città ci sono le seguenti partite:\n\n"
        for match in matches:
            message += (f"⚽️ {match['home']} vs {match['away']}\n"
                       f"🏟 {match['venue']}\n"
                       f"🕒 {match['time']}\n\n")
        
        return message.strip()

    def check_matches_for_city(self, city: str) -> str:
        """
        Check and format matches for a specific city.
        
        Args:
            city (str): The city to check for matches
            
        Returns:
            str: Formatted message about matches in the city
        """
        matches = self.get_matches_for_city(city)
        return self.format_match_message(matches)