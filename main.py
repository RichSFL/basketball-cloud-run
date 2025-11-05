"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
from api_client import fetch_games
from firestore_manager import FirestoreManager
from projections import ProjectionEngine

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
firestore_mgr = FirestoreManager(GCS_PROJECT)
engine = ProjectionEngine()

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
        return jsonify({"count": len(games_list), "saved": saved}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/projections', methods=['GET'])
def projections():
    """Calculate projections for live games"""
    try:
        games_list = fetch_games()
        projections_data = []
        
        for game in games_list:
            try:
                # Parse game data
                ss = game['ss'].split('-')
                home_score = int(ss[0])
                away_score = int(ss[1])
                total_score = home_score + away_score
                
                quarter = int(game['timer']['q'])
                minute = int(game['timer']['tm'])
                second = int(game['timer']['ts'])
                
                # Skip Q1 (no projections yet)
                if quarter < 2:
                    continue
                
                # Calculate played time
                played = engine.calculate_played_time(quarter, minute, second)
                if played <= 0:
                    continue
                
                # Calculate PPS
                home_pps = engine.calculate_pps(home_score, played)
                away_pps = engine.calculate_pps(away_score, played)
                total_pps = engine.calculate_pps(total_score, played)
                
                # Project full game
                home_proj = round(home_pps * engine.GAME_SECONDS, 1)
                away_proj = round(away_pps * engine.GAME_SECONDS, 1)
                total_proj = round(total_pps * engine.GAME_SECONDS, 1)
                
                # Momentum
                momentum = engine.analyze_momentum([total_pps])  # Simple check
                
                projections_data.append({
                    "game_id": game['id'],
                    "home": game['home']['name'],
                    "away": game['away']['name'],
                    "score": f"{home_score}-{away_score}",
                    "quarter": quarter,
                    "played_seconds": played,
                    "home_projection": home_proj,
                    "away_projection": away_proj,
                    "total_projection": total_proj,
                    "momentum": momentum
                })
            except Exception as e:
                logger.warning(f"Could not process game: {e}")
                continue
        
        return jsonify({"active_projections": len(projections_data), "data": projections_data}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
