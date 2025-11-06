"""Basketball projections engine - Python port of JavaScript"""
import statistics
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProjectionEngine:
    """Main projection calculation engine"""
    
    QUARTER_SECONDS = 300
    OT_SECONDS = 180
    GAME_SECONDS = 1200
    ALERT_THRESHOLD_POINTS = 5
    LEADER_THRESHOLD_POINTS = 5
    EXP_THRESHOLD = 1.5
    BLEND_RATIO = 0.3
    
    def __init__(self):
        pass
    
    def calculate_pps(self, score, seconds_played):
        """Calculate Points Per Second"""
        if seconds_played <= 0:
            return 0
        return score / seconds_played
    
    def project_full_game(self, pps):
        """Project full game score from PPS"""
        return pps * self.GAME_SECONDS
    
    def calculate_played_time(self, quarter, minute, second):
        """Calculate seconds played in game"""
        if quarter <= 4:
            return ((quarter - 1) * self.QUARTER_SECONDS) + (self.QUARTER_SECONDS - (minute * 60 + second))
        else:
            regulation = 4 * self.QUARTER_SECONDS
            ot_periods = quarter - 4
            completed_ots = (ot_periods - 1) * self.OT_SECONDS
            current_ot = self.OT_SECONDS - (minute * 60 + second)
            return regulation + completed_ots + current_ot
    
    def analyze_momentum(self, samples):
        """Analyze momentum from samples"""
        if not samples or len(samples) < 5:
            return "INSUFFICIENT_DATA"
        
        last_5 = samples[-5:]
        diffs = [last_5[i] - last_5[i-1] for i in range(1, len(last_5))]
        
        ups = sum(1 for d in diffs if d > 0.0005)
        downs = sum(1 for d in diffs if d < -0.0005)
        
        if ups >= 3:
            return "ON_FIRE"
        if downs >= 3:
            return "COOLING_OFF"
        if ups == downs:
            return "STEADY_PACE"
        if ups > downs:
            return "HEATING_UP"
        return "SLOWING_DOWN"
    
    def classify_pace_trend(self, pps_samples):
        """Classify pace trend reliability"""
        if not pps_samples or len(pps_samples) < 5:
            return "Not enough data"
        
        last_5 = pps_samples[-5:]
        range_val = max(last_5) - min(last_5)
        
        if range_val <= 0.002:
            return "RELIABLE - Rock Solid"
        
        diffs = [last_5[i] - last_5[i-1] for i in range(1, len(last_5))]
        ups = sum(1 for d in diffs if d > 0)
        downs = sum(1 for d in diffs if d < 0)
        
        if ups == 4:
            return "STRONG - Heating Up"
        if downs == 4:
            return "CAUTION - Cooling Down"
        
        turns = 0
        for i in range(len(diffs)-1):
            if diffs[i] != 0 and diffs[i+1] != 0:
                if (diffs[i] > 0) != (diffs[i+1] > 0):
                    turns += 1
        
        if turns >= 2:
            return "RISKY - Unpredictable"
        
        return "STRONG - Heating Up" if ups > downs else "CAUTION - Cooling Down"
    
    def calculate_team_totals(self, game_total, spread):
        """Calculate team totals from game total and spread"""
        T = game_total
        S = abs(spread)
        
        TT_high = (T + S) / 2
        TT_low = T - TT_high
        
        high_decimal = TT_high % 1
        low_decimal = TT_low % 1
        
        if high_decimal == 0.5 and low_decimal == 0.5:
            return {"high": TT_high, "low": TT_low}
        
        if high_decimal == 0 and low_decimal == 0:
            TT_high -= 0.5
            TT_low -= 0.5
            return {"high": TT_high, "low": TT_low}
        
        if high_decimal == 0 and low_decimal == 0.5:
            TT_high -= 0.5
            return {"high": TT_high, "low": TT_low}
        
        if high_decimal == 0.5 and low_decimal == 0:
            TT_low -= 0.5
            return {"high": TT_high, "low": TT_low}
        
        if S <= 2.0 and abs(TT_high - TT_low) <= 1.0:
            avg_tt = round(T / 2 * 2) / 2
            return {"high": avg_tt, "low": avg_tt}
        
        TT_high = round(TT_high * 2) / 2
        TT_low = round(TT_low * 2) / 2
        
        return {"high": TT_high, "low": TT_low}
    
    def is_accelerating(self, samples):
        """Check if pace is accelerating"""
        if not samples or len(samples) < 5:
            return False
        
        last_5 = samples[-5:]
        diffs = [last_5[i] - last_5[i-1] for i in range(1, len(last_5))]
        
        ups = sum(1 for d in diffs if d > 0.0005)
        return ups >= 3
    
    def is_leader_on_fire(self, samples):
        """Check if leader is on fire"""
        return self.analyze_momentum(samples) == "ON_FIRE"


    def project_points(self, current_score, seconds_played):
        """Project points for full game based on current score and time played"""
        if seconds_played <= 0:
            return 0
        pps = current_score / seconds_played
        return round(pps * self.GAME_SECONDS, 1)

    def project_points_from_samples(self, samples):
        """Project points from average PPS of samples"""
        if not samples:
            return 0
        avg_pps = statistics.mean(samples)
        return round(avg_pps * self.GAME_SECONDS, 1)


