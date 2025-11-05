"""Firestore database operations"""
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)

class FirestoreManager:
    def __init__(self, project_id):
        try:
            self.db = firestore.Client(project=project_id)
        except Exception as e:
            logger.error(f"Firestore error: {e}")
            self.db = None
    
    def save_game(self, game_data):
        """Save game to Firestore"""
        if not self.db:
            return False
        try:
            game_id = game_data.get('id', '')
            self.db.collection('games').document(game_id).set(game_data, merge=True)
            logger.info(f"Saved game {game_id}")
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False
