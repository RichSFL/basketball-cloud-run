"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
from api_client import fetch_games
from firestore_manager import FirestoreManager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
firestore_mgr = FirestoreManager(GCS_PROJECT)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/games', methods=['GET'])
def games():
    """Fetch and save games"""
    try:
        games_list = fetch_games()
        saved = 0
        for game in games_list:
            if firestore_mgr.save_game(game):
                saved += 1
        return jsonify({"count": len(games_list), "saved": saved, "data": games_list}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
