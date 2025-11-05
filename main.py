"""Flask app for Cloud Run"""
from flask import Flask, jsonify, request
import os
import logging
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')

def send_discord_message(title, message):
    """Send message to Discord"""
    if not DISCORD_WEBHOOK:
        logger.warning("Discord webhook not configured")
        return False
    
    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": 3447003
            }]
        }
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        return True
    except Exception as e:
        logger.error(f"Discord error: {e}")
        return False

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/projections', methods=['GET'])
def projections():
    return jsonify({"message": "Projections endpoint", "data": []}), 200

@app.route('/test-discord', methods=['POST'])
def test_discord():
    """Test Discord webhook"""
    success = send_discord_message(
        "🏀 Basketball Projections",
        "System is online and working!"
    )
    return jsonify({"discord_sent": success}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
