"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
from datetime import datetime, timezone, timedelta
from api_client import fetch_games
from firestore_manager import FirestoreManager
from discord_client import DiscordClient
from projections import ProjectionEngine

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')

firestore_mgr = FirestoreManager(GCS_PROJECT)
discord = DiscordClient(DISCORD_WEBHOOK)
engine = ProjectionEngine()

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/games', methods=['GET'])
def games():
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
    try:
        games_list = fetch_games()
        projections_data = []
        
        for game in games_list:
            try:
                ss = game['ss'].split('-')
                home_score = int(ss[0])
                away_score = int(ss[1])
                total_score = home_score + away_score
                
                quarter = int(game['timer']['q'])
                minute = int(game['timer']['tm'])
                second = int(game['timer']['ts'])
                
                if quarter < 2:
                    continue
                
                played = engine.calculate_played_time(quarter, minute, second)
                if played <= 0:
                    continue
                
                home_pps = engine.calculate_pps(home_score, played)
                away_pps = engine.calculate_pps(away_score, played)
                total_pps = engine.calculate_pps(total_score, played)
                
                home_proj = round(home_pps * engine.GAME_SECONDS, 1)
                away_proj = round(away_pps * engine.GAME_SECONDS, 1)
                total_proj = round(total_pps * engine.GAME_SECONDS, 1)
                
                proj = {
                    "game_id": game['id'],
                    "home": game['home']['name'],
                    "away": game['away']['name'],
                    "score": f"{home_score}-{away_score}",
                    "quarter": quarter,
                    "time": f"Q{quarter}, {minute}:{str(second).zfill(2)}",
                    "home_projection": home_proj,
                    "away_projection": away_proj,
                    "total_projection": total_proj
                }
                
                projections_data.append(proj)
                
                # SEND DISCORD ALERT ON Q4
                if quarter == 4:
                    msg = f"""🏀 **Q4 ALERT!** [{game['home']['name'].split('(')[1].rstrip(')')} vs {game['away']['name'].split('(')[1].rstrip(')')}]

📊 Score: {home_score}-{away_score} ({total_score})
⏱️ {proj['time']}

💰 **PROJECTIONS:**
**Total:** {total_proj}
**Home:** {home_proj}
**Away:** {away_proj}"""
                    discord.send_message(msg)
                    logger.info(f"📤 Discord alert sent for game {game['id']}")
            
            except Exception as e:
                logger.warning(f"Could not process game: {e}")
                continue
        
        return jsonify({"active_projections": len(projections_data), "data": projections_data}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Basketball Projections online on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
