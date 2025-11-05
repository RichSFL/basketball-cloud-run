"""Flask app for Cloud Run"""
from flask import Flask, jsonify
import os
import logging
from api_client import fetch_games

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/games', methods=['GET'])
def games():
    """Fetch live games from API"""
    games_list = fetch_games()
    return jsonify({"games": games_list, "count": len(games_list)}), 200

@app.route('/projections', methods=['GET'])
def projections():
    return jsonify({"message": "Projections endpoint", "data": []}), 200

@app.route('/test-discord', methods=['POST'])
def test_discord():
    return jsonify({"discord_sent": bool(DISCORD_WEBHOOK)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
