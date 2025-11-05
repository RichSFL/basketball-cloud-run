"""Basketball API client - mirrors JavaScript logic"""
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_games():
    """Fetch in-play games (mirrors JavaScript getEvents)"""
    from config import API_TOKEN, SPORT_ID, LEAGUE_ID, API_VERSION
    
    try:
        if not API_TOKEN:
            logger.warning("No API token")
            return []
        
        url = f"https://api.b365api.com/{API_VERSION}/events/inplay?sport_id={SPORT_ID}&league_id={LEAGUE_ID}&token={API_TOKEN}"
        logger.info(f"Fetching from: {url}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"API Response: success={data.get('success')}, results={len(data.get('results', []))}")
        
        if data.get('success') != 1:
            logger.warning(f"API error: {data}")
            return []
        
        return data.get('results', [])
    except Exception as e:
        logger.error(f"API fetch error: {e}")
        return []
