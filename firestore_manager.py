"""Firestore database manager"""
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)

class FirestoreManager:
    def __init__(self, project_id):
        self.db = firestore.Client(project=project_id)
    
    def save_projection(self, game_id, player_id, projection_data):
        """Save projection to Firestore"""
        try:
            doc_ref = self.db.collection('projections').document(f"{game_id}_{player_id}")
            doc_ref.set(projection_data, merge=True)
            logger.info(f"Saved projection for {player_id} in game {game_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving projection: {e}")
            return False
    
    def get_projection(self, game_id, player_id):
        """Get projection from Firestore"""
        try:
            doc = self.db.collection('projections').document(f"{game_id}_{player_id}").get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting projection: {e}")
            return None
    
    def save_sample(self, sample_data):
        """Save sample data to Firestore"""
        try:
            self.db.collection('samples').add(sample_data)
            return True
        except Exception as e:
            logger.error(f"Error saving sample: {e}")
            return False
