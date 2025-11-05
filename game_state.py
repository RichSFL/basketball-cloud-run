"""Game state management"""
from google.cloud import firestore
import logging
import json

logger = logging.getLogger(__name__)

class GameStateManager:
    """Manages game state in Firestore"""
    
    def __init__(self, project_id):
        try:
            self.db = firestore.Client(project=project_id)
        except Exception as e:
            logger.error(f"Firestore init error: {e}")
            self.db = None
    
    def get_state(self, game_id):
        """Get game state from Firestore"""
        if not self.db:
            return self._default_state(game_id)
        
        try:
            doc = self.db.collection('game_states').document(game_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Get state error: {e}")
        
        return self._default_state(game_id)
    
    def save_state(self, game_id, state):
        """Save game state to Firestore"""
        if not self.db:
            return False
        
        try:
            self.db.collection('game_states').document(game_id).set(state, merge=True)
            return True
        except Exception as e:
            logger.error(f"Save state error: {e}")
            return False
    
    def _default_state(self, game_id):
        """Default game state"""
        return {
            "game_id": game_id,
            "home_samples": [],
            "away_samples": [],
            "total_samples": [],
            "missed_cycles": 0,
            "silent_mode": True,
            "pace_history": "",
            "final_report_sent": False,
            "last_timestamp": "",
            "last_alert": 0,
            "betting_window_fired": False,
            "decision_window_complete": False,
            "saw_q4_yet": False,
            "last_home_score": 0,
            "last_away_score": 0,
            "last_total_score": 0,
            "last_home_name": "",
            "last_away_name": "",
            "betting_window_projection": None,
            "betting_window_line": None,
            "betting_window_recommendation": None,
            "home_team_projection": None,
            "home_team_line": None,
            "home_team_rec": None,
            "away_team_projection": None,
            "away_team_line": None,
            "away_team_rec": None
        }

