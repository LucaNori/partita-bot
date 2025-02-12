from datetime import datetime
import requests
from typing import List, Dict, Any, Optional
import config

class MatchFetcher:
    def __init__(self):
        self.headers = config.FOOTBALL_API_HEADERS
        self.base_url = config.FOOTBALL_API_BASE_URL

    def _get_area_id_by_city(self, city: str) -> Optional[int]:
        """
        Get the area ID for a given Italian city.
        
        Args:
            city (str): The city name
            
        Returns:
            Optional[int]: The area ID if found, None otherwise
        """
        # Map of Italian cities to their area IDs
        city_map = {
            'milano': 2114,    # Italy (Milan teams play here)
            'roma': 2114,      # Italy (Roma teams play here)
            'napoli': 2114,    # Italy (Napoli plays here)
            'torino': 2114,    # Italy (Turin teams play here)
            'firenze': 2114,   # Italy (Fiorentina plays here)
            'genova': 2114,    # Italy (Genoa teams play here)
            'bologna': 2114,   # Italy (Bologna plays here)
            'verona': 2114,    # Italy (Verona plays here)
            'bergamo': 2114,   # Italy (Atalanta plays here)
            'udine': 2114,     # Italy (Udinese plays here)
            'sassuolo': 2114,  # Italy (Sassuolo plays here)
            'empoli': 2114,    # Italy (Empoli plays here)
            'lecce': 2114,     # Italy (Lecce plays here)
            'salerno': 2114,   # Italy (Salernitana plays here)
            'frosinone': 2114, # Italy (Frosinone plays here)
            'cagliari': 2114,  # Italy (Cagliari plays here)
        }
        return city_map.get(city.lower())

    def _get_stadium_by_city(self, city: str) -> List[str]:
        """
        Get the stadium names for a given Italian city.
        
        Args:
            city (str): The city name
            
        Returns:
            List[str]: List of stadium names in that city
        """
        stadium_map = {
            'milano': ['Giuseppe Meazza', 'San Siro'],
            'roma': ['Stadio Olimpico'],
            'napoli': ['Diego Armando Maradona', 'Stadio Diego Armando Maradona'],
            'torino': ['Allianz Stadium', 'Olimpico Grande Torino'],
            'firenze': ['Artemio Franchi'],
            'genova': ['Luigi Ferraris'],
            'bologna': ['Renato Dall\'Ara'],
            'verona': ['Marcantonio Bentegodi'],
            'bergamo': ['Gewiss Stadium'],
            'udine': ['Bluenergy Stadium', 'Dacia Arena'],
            'sassuolo': ['MAPEI Stadium - Città del Tricolore'],
            'empoli': ['Carlo Castellani'],
            'lecce': ['Via del Mare'],
            'salerno': ['Arechi'],
            'frosinone': ['Benito Stirpe'],
            'cagliari': ['Unipol Domus'],
        }
        return stadium_map.get(city.lower(), [])

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