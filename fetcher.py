import os
import json
import requests
import yaml
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config
import glob

logger = logging.getLogger(__name__)

class MatchFetcher:
    def __init__(self):
        self.headers = {
            'X-Auth-Token': config.FOOTBALL_API_TOKEN
        }
        self.base_url = "http://api.football-data.org/v4"
        self.teams_config = self._load_teams_config()
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_teams_config(self) -> dict:
        config_path = os.path.join(os.path.dirname(__file__), 'teams.yml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_cache_filename(self, date: datetime) -> str:
        return os.path.join(self.data_dir, f'matches_{date.strftime("%Y-%m-%d")}.json')

    def _cleanup_old_cache_files(self):
        try:
            cache_files = glob.glob(os.path.join(self.data_dir, 'matches_*.json'))
            
            if len(cache_files) > 7:
                cache_files.sort(key=lambda x: os.path.getmtime(x))
                files_to_delete = cache_files[:-7]
                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        logger.debug(f"Deleted old cache file: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.error(f"Error deleting cache file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}")

    def _load_cached_data(self, date: datetime) -> dict:
        cache_file = self._get_cache_filename(date)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Loaded data from cache for {date.strftime('%Y-%m-%d')}")
                return data
            except Exception as e:
                logger.error(f"Error reading cache file: {str(e)}")
                try:
                    # If cache is corrupted, delete it
                    os.remove(cache_file)
                    logger.info(f"Deleted corrupted cache file: {cache_file}")
                except Exception as del_e:
                    logger.error(f"Error deleting corrupted cache: {str(del_e)}")
        return None

    def _save_to_cache(self, date: datetime, data: dict):
        if not data:
            logger.warning("Attempted to cache empty data")
            return
            
        cache_file = self._get_cache_filename(date)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved data to cache for {date.strftime('%Y-%m-%d')}")
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")

    def _get_team_city(self, team_name: str) -> str:
        cities = self.teams_config.get('cities', {})
        if not team_name:
            return None
            
        team_name = team_name.strip()
        for city, teams in cities.items():
            if team_name in teams:
                return city.lower()  # Store cities in lowercase
        return None

    def _normalize_city(self, city: str) -> str:
        """Normalize city name for consistent matching."""
        if not city:
            return None
        return city.strip().lower()

    def _format_time(self, utc_time_str: str) -> dict:
        """Convert UTC time string to local time and return formatted dict"""
        # Convert ISO format to datetime object with proper timezone
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        # Convert to Italy timezone for display
        rome_time = utc_time.astimezone(ZoneInfo('Europe/Rome'))
        
        return {
            'utc': utc_time.strftime('%H:%M'),
            'local': rome_time.strftime('%H:%M'),
            'datetime': rome_time
        }

    def _is_match_today(self, match_datetime: datetime, reference_date: datetime) -> bool:
        """Check if match is on the same day as the reference date"""
        match_date = match_datetime.date()
        reference_date = reference_date.date()
        return match_date == reference_date

    def _fetch_matches(self, target_date: datetime) -> dict:
        """Fetch matches from API or cache for the given date"""
        # Try loading from cache first
        cached_data = self._load_cached_data(target_date)
        if cached_data is not None:
            logger.debug(f"Using cached data for {target_date.strftime('%Y-%m-%d')}")
            return cached_data

        # Prepare date range (yesterday to tomorrow to catch overnight matches)
        yesterday = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get Italy area ID from config or use default
        italy_area_id = self.teams_config.get('area_ids', {}).get('italy', 2114)

        try:
            # Prepare API request
            url = f"{self.base_url}/matches"
            params = {
                'dateFrom': yesterday,
                'dateTo': tomorrow,
                'areas': italy_area_id
            }
            
            # Make the API request
            logger.info(f"Fetching matches from API for {target_date.strftime('%Y-%m-%d')}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Check if we got any matches
            if not data.get('matches'):
                logger.warning(f"API returned no matches for {target_date.strftime('%Y-%m-%d')}")
                return None

            # Cache the successful response
            self._save_to_cache(target_date, data)
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching matches: {str(e)}", exc_info=True)
            return None

    def get_matches_for_city(self, city: str, target_date: datetime = None) -> list:
        """Get matches for a specific city on the given date"""
        if target_date is None:
            target_date = datetime.now(ZoneInfo('Europe/Rome'))

        normalized_city = self._normalize_city(city)
        if not normalized_city:
            logger.warning(f"Invalid city name provided: '{city}'")
            return []

        data = self._fetch_matches(target_date)
        if not data:
            logger.warning(f"No match data available for {target_date.strftime('%Y-%m-%d')}")
            return []

        matches_by_city = {}
        logger.info(f"Looking for matches in {normalized_city} on {target_date.strftime('%Y-%m-%d')}")

        for match in data.get('matches', []):

            if match.get('competition', {}).get('code') == 'SA':

                times = self._format_time(match.get('utcDate'))
                
                if not self._is_match_today(times['datetime'], target_date):
                    continue

                home_team = match.get('homeTeam', {})
                away_team = match.get('awayTeam', {})
                home_name = home_team.get('shortName')
                
                match_city = self._get_team_city(home_name)
                
                if match_city:
                    match_info = {
                        'home': home_name,
                        'away': away_team.get('shortName', 'Unknown'),
                        'time_utc': times['utc'],
                        'time_local': times['local'],
                        'status': match.get('status'),
                        'date': times['datetime'].date().isoformat()
                    }
                    
                    if match_city not in matches_by_city:
                        matches_by_city[match_city] = []
                    matches_by_city[match_city].append(match_info)
                    logger.debug(f"Added match in {match_city}: {home_name} vs {away_team.get('shortName')}")

        matches = matches_by_city.get(normalized_city, [])
        logger.info(f"Found {len(matches)} matches in {normalized_city}")
        return matches

    def format_match_message(self, matches: list) -> str:
        """Format matches into a human-readable message"""
        if not matches:
            return None
        
        message = "🎯 Oggi nella tua città ci sono le seguenti partite:\n\n"
        for match in matches:
            message += (f"⚽️ {match['home']} vs {match['away']}\n"
                       f"🕒 {match['time_local']} (CET)\n\n")
        
        return message.strip()

    def check_matches_for_city(self, city: str) -> str:
        """Check for matches in a city and return formatted message"""
        matches = self.get_matches_for_city(city)

        message = self.format_match_message(matches)

        self._cleanup_old_cache_files()
        
        return message
