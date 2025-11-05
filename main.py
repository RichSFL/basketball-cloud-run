"""Basketball projections API - Cloud Run"""
from flask import Flask, jsonify, request
import os
import logging
import json
from api_client import fetch_games
from firestore_manager import FirestoreManager
from game_state import GameStateManager
from game_processor import GameProcessor
from discord_client import DiscordClient
from csv_logger import CSVLogger

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
GCS_BUCKET = os.getenv('GCS_BUCKET', 'basketball-projections')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')

firestore_mgr = FirestoreManager(GCS_PROJECT)
state_mgr = GameStateManager(GCS_PROJECT)
discord = DiscordClient(DISCORD_WEBHOOK)
csv_logger = CSVLogger(GCS_BUCKET, GCS_PROJECT)
processor = GameProcessor(state_mgr, discord, csv_logger)

@app.route('/', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/games', methods=['GET'])
def games():
    """Fetch, process, and save live games"""
    logger.info("📊 Fetching live games...")
    games_list = fetch_games()
    saved = 0
    processed = 0
    
    for game in games_list:
        # Save to Firestore
        if firestore_mgr.save_game(game):
            saved += 1
        
        # Process game (calculate projections)
        try:
            slot = f"game_{processed % 6}"  # Cycle through A-F
            processor.process_game(game, None, slot)
            processed += 1
            logger.info(f"✅ Processed game {game['id']}")
        except Exception as e:
            logger.error(f"❌ Error processing game {game['id']}: {e}")
    
    logger.info(f"📈 Summary: {len(games_list)} games fetched, {saved} saved, {processed} processed")
    
    return jsonify({
        "games": len(games_list),
        "saved": saved,
        "processed": processed,
        "data": games_list
    }), 200

@app.route('/projections', methods=['GET'])
def projections():
    """Get active projections"""
    return jsonify({
        "message": "Projections system active",
        "status": "ready",
        "endpoint": "/games to fetch live projections"
    }), 200

@app.route('/test-discord', methods=['POST'])
def test_discord():
    """Test Discord webhook"""
    success = discord.send_message("🏀 Basketball Projections System Online!")
    return jsonify({"discord_sent": success}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting Basketball Projections on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
