"""API client for basketball data"""
import requests
import logging
from config import API_TOKEN, LEAGUE_ID, SPORT_ID

logger = logging.getLogger(__name__)

class BasketballAPIClient:
    def __init__(self):
        self.api_token = API_TOKEN
        self.base_url = "https://api.b365api.com/v1"
    
    def get_live_games(self):
        """Fetch live games"""
        try:
            url = f"{self.base_url}/events/?token={self.api_token}&sport_id={SPORT_ID}&league_id={LEAGUE_ID}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching live games: {e}")
            return None
    
    def get_game_details(self, game_id):
        """Fetch specific game details"""
        try:
            url = f"{self.base_url}/event/details/?token={self.api_token}&event_id={game_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching game details: {e}")
            return None
