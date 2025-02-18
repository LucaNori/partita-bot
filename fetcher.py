import os
import json
import requests
import yaml
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config
import glob

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
        cache_files = glob.glob(os.path.join(self.data_dir, 'matches_*.json'))
        
        if len(cache_files) > 7:
            cache_files.sort(key=lambda x: os.path.getmtime(x))
            files_to_delete = cache_files[:-7]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"Deleted old cache file: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"Error deleting cache file {file_path}: {str(e)}")

    def _load_cached_data(self, date: datetime) -> dict:
        cache_file = self._get_cache_filename(date)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache file: {str(e)}")
        return None

    def _save_to_cache(self, date: datetime, data: dict):
        cache_file = self._get_cache_filename(date)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving to cache: {str(e)}")

    def _get_team_city(self, team_name: str) -> str:
        cities = self.teams_config.get('cities', {})
        for city, teams in cities.items():
            if team_name in teams:
                return city
        return None

    def _format_time(self, utc_time_str: str) -> dict:
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        rome_time = utc_time.astimezone(ZoneInfo('Europe/Rome'))
        return {
            'utc': utc_time.strftime('%H:%M'),
            'local': rome_time.strftime('%H:%M'),
            'datetime': rome_time
        }

    def _is_match_today(self, match_datetime: datetime, rome_today: datetime) -> bool:
        match_date = match_datetime.date()
        return match_date == rome_today.date()

    def _fetch_matches(self, target_date: datetime) -> dict:
        cached_data = self._load_cached_data(target_date)
        if cached_data is not None:
            return cached_data

        yesterday = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')

        try:
            url = f"{self.base_url}/matches"
            params = {
                'dateFrom': yesterday,
                'dateTo': tomorrow,
                'areas': self.teams_config.get('area_ids', {}).get('italy', 2114)
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            self._save_to_cache(target_date, data)
            return data

        except Exception as e:
            print(f"Error fetching matches: {str(e)}")
            return None

    def get_matches_for_city(self, city: str, target_date: datetime = None) -> list:
        if target_date is None:
            target_date = datetime.now(ZoneInfo('Europe/Rome'))

        data = self._fetch_matches(target_date)
        if not data:
            return []

        matches_by_city = {}
        
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

        city_lower = city.lower()
        for stored_city, matches in matches_by_city.items():
            if stored_city.lower() == city_lower:
                return matches
        return []

    def format_match_message(self, matches: list) -> str:
        if not matches:
            return None
        
        message = "🎯 Oggi nella tua città ci sono le seguenti partite:\n\n"
        for match in matches:
            message += (f"⚽️ {match['home']} vs {match['away']}\n"
                       f"🕒 {match['time_local']} (CET)\n\n")
        
        return message.strip()

    def check_matches_for_city(self, city: str) -> str:
        matches = self.get_matches_for_city(city)
        message = self.format_match_message(matches)
        self._cleanup_old_cache_files()
        return message