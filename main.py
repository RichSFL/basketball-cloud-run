"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
import time
from api_client import fetch_games
from firestore_manager import FirestoreManager
from discord_client import DiscordClient, build_game_embed
from projections import ProjectionEngine

app = Flask(__name__)

# ---- GLOBAL state, for one slot (replace with Firestore later)
tracked_game = {}      # holds gameId, state, etc.
ALERT_THRESHOLD_POINTS = 5
ALERT_MIN_INTERVAL = 30   # seconds

# Configure logger for better visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("basketball_main")

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')
if not DISCORD_WEBHOOK:
    logger.warning("DISCORD_WEBHOOK environment variable not set!")
discord = DiscordClient(DISCORD_WEBHOOK)

def process_tracked_slot_one(games, discord, odds_fetcher):
    global tracked_game
    now = int(time.time())
    
   # 1. TRACK OR SELECT GAME
if not tracked_game.get("id"):
    for g in games:
        # Defensive check for timer data
        timer = g.get('timer')
        if not timer or 'q' not in timer:
            logger.warning(f"Game missing timer/q: {g}")
            continue
        try:
            q = int(timer['q'])
        except Exception as e:
            logger.warning(f"Invalid quarter in timer for game {g}: {e}")
            continue
        # Pick a Q1 or Q2 game not being tracked already
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
            logger.info(f"Now tracking game: {g['id']}")
            break
    return  # If not found, wait till next tick

    # 2. FIND MATCHING GAME IN LIVE DATA
    game = next((g for g in games if g['id'] == tracked_game['id']), None)
    if not game:
        logger.warning("Tracked game not found in live games!")
        return

    # 3. CORE LOGIC (PORTED FROM PROCESSGAME)
    # -- scores/time
    try:
        home_score, away_score = map(int, game['ss'].split('-'))
    except Exception as e:
        logger.error(f"Failed to parse score for game {tracked_game['id']}: {e}")
        return

    q = int(game['timer']['q'])
    m = int(game['timer']['tm'])
    s = int(game['timer']['ts'])
    stamp = f"{q}-{m}-{s}"
    total_score = home_score + away_score

    logger.info(f"Tracking: id={tracked_game['id']}, q={q}, m={m}, s={s}, scores: {home_score}-{away_score}, played={played}")
    logger.info(f"Samples: home={tracked_game['samples']['home']} away={tracked_game['samples']['away']} total={tracked_game['samples']['total']}")


    # STALE/NO UPDATE DETECTION
    if tracked_game["last_stamp"] == stamp:
        tracked_game["missed_cycles"] += 1
        if tracked_game["missed_cycles"] > 8 and q <= 2:
            discord.send_message(f"Game stalled (Q{q}, no update 8 cycles), releasing slot.")
            logger.info("Releasing stalled game slot.")
            tracked_game.clear()
        return
    tracked_game["last_stamp"] = stamp
    tracked_game["missed_cycles"] = 0

    # SKIP Q1
    if q == 1:
        return

    # SAMPLES
    played = (q-1)*300 + (300 - (m*60+s))
    if played <= 0:
        return

    engine = ProjectionEngine()

    # Instead of inline calculations, use your ProjectionEngine:
    home_pps = engine.calculate_pps(home_score, played)
    away_pps = engine.calculate_pps(away_score, played)
    total_pps = engine.calculate_pps(total_score, played)
    
    # Store samples as before
    tracked_game["samples"]["home"].append(home_pps)
    tracked_game["samples"]["away"].append(away_pps)
    tracked_game["samples"]["total"].append(total_pps)
    
    # Use engine to calculate raw and averaged projections
    home_raw = engine.project_points(home_score, played)
    away_raw = engine.project_points(away_score, played)
    total_raw = engine.project_points(total_score, played)
    
    home_avg = engine.project_points_from_samples(tracked_game["samples"]["home"])
    away_avg = engine.project_points_from_samples(tracked_game["samples"]["away"])
    total_avg = engine.project_points_from_samples(tracked_game["samples"]["total"])
    
    # Dummy values for line/reliability/momentum (replace with your own logic as needed)
    home_line = total_line = away_line = 110
    reliability = "⚠️ CAUTION"
    home_momentum = "📉 SLOWING DOWN"
    away_momentum = "⚡ HEATING UP"

    # Q4: BETTING DECISION WINDOW (once per tracked session)
    if q == 4 and not tracked_game["betting_window_fired"]:
        tracked_game["betting_window_fired"] = True
        last_line = total_line
        diff = total_avg - last_line
        rec = "NO BET"
        if isinstance(last_line, (int, float)):
            if abs(diff) > ALERT_THRESHOLD_POINTS:
                rec = "OVER" if diff > 0 else "UNDER"
        embed = build_game_embed(
            game, home_score, away_score, total_score, q, m, s,
            home_raw, home_avg, away_raw, away_avg, total_raw, total_avg,
            home_line, away_line, total_line,
            home_momentum, away_momentum, reliability,
            len(tracked_game["samples"]["total"])
        )
        logger.info(f"Sending Q4 betting decision: {rec}")
        discord.send_embed(**embed)
        tracked_game["decision_complete"] = True
        tracked_game["last_alert"] = now
        return

    # Q3/Q4: AUTOMATED ALERTS (sampled every 30s, only if not fired very recently)
    if q >= 3 and (now - tracked_game.get("last_alert", 0)) >= ALERT_MIN_INTERVAL:
        embed = build_game_embed(
            game, home_score, away_score, total_score, q, m, s,
            home_raw, home_avg, away_raw, away_avg, total_raw, total_avg,
            home_line, away_line, total_line,
            home_momentum, away_momentum, reliability,
            len(tracked_game["samples"]["total"])
        )
        logger.info(f"Sending alert (Q{q}, t={m:02}:{s:02}, total_samples={len(tracked_game['samples']['total'])})")
        discord.send_embed(**embed)
        tracked_game["last_alert"] = now
        return

    # GAME END (Q4 0:00, not tied)
    if q == 4 and m == 0 and s == 0 and home_score != away_score and not tracked_game.get("final_report_sent"):
        msg = f"🏁 FINAL: {game['home']['name']} vs. {game['away']['name']} ended {home_score}-{away_score} (Total: {total_score})"
        logger.info("Sending final report.")
        discord.send_message(msg)
        tracked_game["final_report_sent"] = True
        tracked_game.clear()

@app.route("/")
def index():
    return jsonify({"msg": "Basketball projections API is running."})

@app.route("/projections")
def projections():
    return jsonify({"ok": True, "tracked_game": tracked_game})

@app.route("/tick")
def tick():
    try:
        games = fetch_games()
        odds_fetcher = None  # Implement as needed
        process_tracked_slot_one(games, discord, odds_fetcher)
        return jsonify({"ok": True, "tracked_game": tracked_game})
    except Exception as e:
        logger.exception("Error in /tick")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

@app.route("/test-alert")
def test_alert():
    discord.send_message("Test Alert: Discord connection working!")
    return jsonify({"ok": True})

@app.route("/test-embed")
def test_embed():
    fake_game = {
        'home': {'name': 'Test Home'}, 
        'away': {'name': 'Test Away'}
    }
    embed_data = build_game_embed(
        fake_game, 50, 47, 97, 4, 1, 12,
        100, 98, 90, 92, 190, 188,
        110, 110, 110,
        "⚡ HEATING UP", "📉 SLOWING DOWN", "⚠️ CAUTION",
        10
    )
    discord.send_embed(**embed_data)
    return jsonify({"ok": True})

