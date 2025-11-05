"""Main Cloud Run entry point"""
import logging
from config import GCS_PROJECT_ID, GCS_BUCKET
from firestore_manager import FirestoreManager
from api_client import BasketballAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_system():
    """Initialize all system components"""
    try:
        db_manager = FirestoreManager(GCS_PROJECT_ID)
        api_client = BasketballAPIClient()
        logger.info("System initialized successfully")
        return db_manager, api_client
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        return None, None

def fetch_and_process_games():
    """Fetch live games and process"""
    db_manager, api_client = initialize_system()
    if not db_manager or not api_client:
        logger.error("Failed to initialize components")
        return
    
    games = api_client.get_live_games()
    if games:
        logger.info(f"Processing {len(games.get('results', []))} games")
    else:
        logger.warning("No games fetched")

if __name__ == "__main__":
    fetch_and_process_games()
