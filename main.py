"""Flask app for Cloud Run"""
from flask import Flask, jsonify
import os
import logging
from api_client import fetch_games
from firestore_manager import FirestoreManager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')
GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')

fs = FirestoreManager(GCS_PROJECT)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/games', methods=['GET'])
def games():
    """Fetch and save live games"""
    games_list = fetch_games()
    saved = 0
    for game in games_list:
        if fs.save_game(game):
            saved += 1
    return jsonify({"games": games_list, "count": len(games_list), "saved": saved}), 200

@app.route('/projections', methods=['GET'])
def projections():
    return jsonify({"message": "Projections endpoint", "data": []}), 200

@app.route('/test-discord', methods=['POST'])
def test_discord():
    return jsonify({"discord_sent": bool(DISCORD_WEBHOOK)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
