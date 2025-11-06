"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
from datetime import datetime, timezone, timedelta
from api_client import fetch_games
from firestore_manager import FirestoreManager
from discord_client import DiscordClient
from projections import ProjectionEngine

import time
import datetime

# ---- GLOBAL state, for one slot (replace with Firestore later)
tracked_game = {}      # holds gameId, state, etc.
ALERT_THRESHOLD_POINTS = 5
ALERT_MIN_INTERVAL = 30   # seconds

def process_tracked_slot_one(games, discord, odds_fetcher):
    global tracked_game
    now = int(time.time())
    
    # 1. TRACK OR SELECT GAME
    if not tracked_game.get("id"):
        for g in games:
            # Pick a Q1 or Q2 game not being tracked already
            q = int(g['timer']['q'])
            if q == 1 or q == 2:
                tracked_game = {
                    "id": g['id'],
                    "samples": {"home": [], "away": [], "total": []},
                    "last_stamp": "",
                    "missed_cycles": 0,
                    "betting_window_fired": False,
                    "decision_complete": False,
                    "last_alert": 0,
                    "final_report_sent": False,
                    "full_state": {},
                }
                break
        return  # If not found, wait till next tick

    # 2. FIND MATCHING GAME IN LIVE DATA
    game = next((g for g in games if g['id'] == tracked_game['id']), None)
    if not game:
        return  # In prod: handle removal, clean-up, alert

    # 3. CORE LOGIC (PORTED FROM PROCESSGAME)
    # -- scores/time
    try:
        home_score, away_score = map(int, game['ss'].split('-'))
    except Exception:
        return
    
    q = int(game['timer']['q'])
    m = int(game['timer']['tm'])
    s = int(game['timer']['ts'])
    stamp = f"{q}-{m}-{s}"
    total_score = home_score + away_score

    # STALE/NO UPDATE DETECTION
    if tracked_game["last_stamp"] == stamp:
        tracked_game["missed_cycles"] += 1
        if tracked_game["missed_cycles"] > 8 and q <= 2:
            discord.send_message(f"Game stalled (Q{q}, no update 8 cycles), releasing slot.")
            tracked_game.clear()
        return
    tracked_game["last_stamp"] = stamp
    tracked_game["missed_cycles"] = 0
    
    # SKIP Q1
    if q == 1:
        return
    
    # SAMPLES
    played = (q-1)*300 + (300 - (m*60+s))  # for simulation, update with your logic
    if played <= 0:
        return
    home_pps = home_score / played
    away_pps = away_score / played
    total_pps = total_score / played

    tracked_game["samples"]["home"].append(home_pps)
    tracked_game["samples"]["away"].append(away_pps)
    tracked_game["samples"]["total"].append(total_pps)

    home_avg = round(sum(tracked_game["samples"]["home"]) / len(tracked_game["samples"]["home"]) * 1200, 1)
    away_avg = round(sum(tracked_game["samples"]["away"]) / len(tracked_game["samples"]["away"]) * 1200, 1)
    total_avg = round(sum(tracked_game["samples"]["total"]) / len(tracked_game["samples"]["total"]) * 1200, 1)

    # Q4: BETTING DECISION WINDOW (once per tracked session)
    if q == 4 and not tracked_game["betting_window_fired"]:
        tracked_game["betting_window_fired"] = True
        last_line = 110  # TODO: fetch odds for game, that is "odds_fetcher(game['id'])"
        diff = total_avg - last_line
        rec = "NO BET"
        if isinstance(last_line, (int, float)):
            if abs(diff) > ALERT_THRESHOLD_POINTS:
                rec = "OVER" if diff > 0 else "UNDER"
        msg = (
            f"⏰ {datetime.datetime.now()}\n\n"
            f"🎯🚨 BETTING WINDOW 🚨🎯\n"
            f"{game['home']['name']} vs. {game['away']['name']}\n"
            f"Q{q} {m}:{str(s).zfill(2)} | 📊 {total_score} ({home_score}-{away_score})\n"
            f"Avg: {total_avg} | Line: {last_line} | Diff: {diff:.1f} | REC: {rec}\n"
        )
        discord.send_message(msg)
        tracked_game["decision_complete"] = True
        tracked_game["last_alert"] = now
        return

    # Q3/Q4: AUTOMATED ALERTS (sampled every 30s, only if not fired very recently)
    if q >= 3 and (now - tracked_game.get("last_alert", 0)) >= ALERT_MIN_INTERVAL:
        msg = (
            f"⏰ {datetime.datetime.now()} \n"
            f"{game['home']['name']} vs. {game['away']['name']}\n"
            f"Q{q} {m}:{str(s).zfill(2)} | 📊 {total_score} ({home_score}-{away_score})\n"
            f"Total (avg): {total_avg}\n"
        )
        discord.send_message(msg)
        tracked_game["last_alert"] = now
        return

    # GAME END (Q4 0:00, not tied)
    if q == 4 and m == 0 and s == 0 and home_score != away_score and not tracked_game.get("final_report_sent"):
        discord.send_message(f"🏁 FINAL: {game['home']['name']} vs. {game['away']['name']} ended {home_score}-{away_score} (Total: {total_score})")
        tracked_game["final_report_sent"] = True
        tracked_game.clear()

    # Add/expand as needed!

# Usage: (inside your /projections endpoint, after fetching games)
# process_tracked_slot_one(games_from_api, discord, odds_fetcher=None)







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

        process_tracked_slot_one(games_list, discord, odds_fetcher=None)

        
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
