"""Basketball projections API"""
from flask import Flask, jsonify
import os
import logging
from datetime import datetime, timezone, timedelta
from api_client import fetch_games
from firestore_manager import FirestoreManager
from discord_client import DiscordClient
from projections import ProjectionEngine
from discord_client import build_game_embed
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
    played = (q-1)*300 + (300 - (m*60+s))
    if played <= 0:
        return
    
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
    home_line = total_line = away_line = 110  # TODO: replace with real odds
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
        discord.send_embed(**embed)
        tracked_game["last_alert"] = now
        return

    # GAME END (Q4 0:00, not tied)
    if q == 4 and m == 0 and s == 0 and home_score != away_score and not tracked_game.get("final_report_sent"):
        discord.send_message(f"🏁 FINAL: {game['home']['name']} vs. {game['away']['name']} ended {home_score}-{away_score} (Total: {total_score})")
        tracked_game["final_report_sent"] = True
        tracked_game.clear()
