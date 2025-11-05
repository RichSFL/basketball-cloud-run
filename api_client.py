"""Basketball API client"""
import requests
import logging
from config import API_TOKEN

logger = logging.getLogger(__name__)

def fetch_games():
    """Fetch live games from API"""
    try:
        if not API_TOKEN:
            logger.warning("No API token configured")
            return []
        
        url = f"https://api.b365api.com/v1/events/?token={API_TOKEN}&sport_id=2&league_id=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        return []
