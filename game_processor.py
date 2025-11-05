"""Main game processing engine - ported from JavaScript"""
import logging
from datetime import datetime, timezone, timedelta
from projections import ProjectionEngine
from game_state import GameStateManager

logger = logging.getLogger(__name__)

class GameProcessor:
    """Process live games and calculate projections"""
    
    def __init__(self, state_manager, discord_client, csv_logger):
        self.engine = ProjectionEngine()
        self.state_mgr = state_manager
        self.discord = discord_client
        self.csv = csv_logger
    
    def process_game(self, game, odds_info, slot):
        """Main game processing logic"""
        event_id = game['id']
        state = self.state_mgr.get_state(event_id)
        
        try:
            # Parse game data
            home_name = game['home']['name']
            away_name = game['away']['name']
            ss = game['ss'].split('-')
            home_score = int(ss[0])
            away_score = int(ss[1])
            total_score = home_score + away_score
            
            quarter = int(game['timer']['q'])
            minute = int(game['timer']['tm'])
            second = int(game['timer']['ts'])
            stamp = f"{quarter}-{minute}-{second}"
            
            logger.info(f"Processing {home_name} vs {away_name}: {home_score}-{away_score}, Q{quarter}")
            
            # Store latest scores
            state['last_home_score'] = home_score
            state['last_away_score'] = away_score
            state['last_total_score'] = total_score
            state['last_home_name'] = home_name
            state['last_away_name'] = away_name
            
            # Q1: Skip sampling, just track
            if quarter == 1:
                logger.info("Q1: Tracking only, no sampling yet")
                state['last_timestamp'] = stamp
                self.state_mgr.save_state(event_id, state)
                return
            
            # Duplicate detection
            if state['last_timestamp'] == stamp and state['last_home_score'] == home_score and state['last_away_score'] == away_score:
                logger.info("Duplicate data, skipping")
                state['last_timestamp'] = stamp
                self.state_mgr.save_state(event_id, state)
                return
            
            # Calculate played time and PPS
            played = self.engine.calculate_played_time(quarter, minute, second)
            if played <= 0:
                logger.warning("Played time <= 0, skipping")
                return
            
            home_pps = self.engine.calculate_pps(home_score, played)
            away_pps = self.engine.calculate_pps(away_score, played)
            total_pps = self.engine.calculate_pps(total_score, played)
            
            # Collect samples
            state['home_samples'].append(home_pps)
            state['away_samples'].append(away_pps)
            state['total_samples'].append(total_pps)
            
            logger.info(f"Samples: Home={len(state['home_samples'])}, Away={len(state['away_samples'])}, Total={len(state['total_samples'])}")
            
            # Calculate projections
            home_avg = round(sum(state['home_samples']) / len(state['home_samples']) * self.engine.GAME_SECONDS, 1)
            away_avg = round(sum(state['away_samples']) / len(state['away_samples']) * self.engine.GAME_SECONDS, 1)
            total_avg = round(sum(state['total_samples']) / len(state['total_samples']) * self.engine.GAME_SECONDS, 1)
            
            # Momentum analysis
            home_momentum = self.engine.analyze_momentum(state['home_samples'])
            away_momentum = self.engine.analyze_momentum(state['away_samples'])
            
            logger.info(f"Projections - Home: {home_avg}, Away: {away_avg}, Total: {total_avg}")
            
            # Q4 Betting Decision Window
            if quarter == 4 and not state['betting_window_fired']:
                logger.info("🎯 BETTING DECISION WINDOW TRIGGERED")
                state['betting_window_fired'] = True
                state['decision_window_complete'] = True
                state['betting_window_projection'] = total_avg
                
                if odds_info and 'totalLine' in odds_info:
                    line = odds_info['totalLine']
                    diff = total_avg - line
                    state['betting_window_line'] = line
                    if abs(diff) >= self.engine.ALERT_THRESHOLD_POINTS:
                        state['betting_window_recommendation'] = "OVER" if diff > 0 else "UNDER"
                    else:
                        state['betting_window_recommendation'] = "NO BET"
                else:
                    state['betting_window_recommendation'] = "NO BET"
                
                # Send alert
                self._send_betting_alert(home_name, away_name, home_score, away_score, total_score, total_avg, odds_info, state, quarter, minute, second)
                self.state_mgr.save_state(event_id, state)
                return
            
            # Q3+ Alerts (pre-decision)
            if quarter >= 3 and not state['decision_window_complete']:
                logger.info(f"Q{quarter}: Sending projection alert")
                self._send_projection_alert(home_name, away_name, home_score, away_score, total_score, total_avg, home_avg, away_avg, home_momentum, away_momentum, odds_info, state, quarter, minute, second)
            
            state['last_timestamp'] = stamp
            self.state_mgr.save_state(event_id, state)
        
        except Exception as e:
            logger.error(f"Error processing game {event_id}: {e}")
    
    def _send_betting_alert(self, home_name, away_name, home_score, away_score, total_score, total_avg, odds_info, state, q, m, s):
        """Send betting decision alert to Discord"""
        line = odds_info.get('totalLine') if odds_info else 'N/A'
        diff = total_avg - line if isinstance(line, (int, float)) else 0
        rec = state.get('betting_window_recommendation', 'NO BET')
        
        message = f"""⏰ **{self._get_edt_time()}**

🎯🚨 **BETTING DECISION WINDOW** 🚨🎯

**{home_name} vs. {away_name}**
Q{q}, {m}:{str(s).zfill(2)} | 📊 {total_score} ({home_score}-{away_score})

💰 **GAME TOTAL**: Avg **{total_avg}** | Line **{line}** | Rec: **{rec}**"""
        
        if self.discord:
            self.discord.send_message(message)
    
    def _send_projection_alert(self, home_name, away_name, home_score, away_score, total_score, total_avg, home_avg, away_avg, home_momentum, away_momentum, odds_info, state, q, m, s):
        """Send projection alert to Discord"""
        line = odds_info.get('totalLine') if odds_info else 'N/A'
        
        message = f"""⏰ **{self._get_edt_time()}**

**{home_name} vs. {away_name}**
Q{q}, {m}:{str(s).zfill(2)} | 📊 {total_score} ({home_score}-{away_score})

📊 **PROJECTIONS**
{home_name}: **{home_avg}** ({self._format_momentum(home_momentum)})
{away_name}: **{away_avg}** ({self._format_momentum(away_momentum)})

💰 **GAME TOTAL**: **{total_avg}** | Line: **{line}**"""
        
        if self.discord:
            self.discord.send_message(message)
    
    def _format_momentum(self, momentum):
        """Format momentum for Discord"""
        mapping = {
            "ON_FIRE": "🔥 ON FIRE",
            "HEATING_UP": "⚡ HEATING UP",
            "COOLING_OFF": "❄️ COOLING OFF",
            "SLOWING_DOWN": "📉 SLOWING DOWN",
            "STEADY_PACE": "➡️ STEADY",
            "INSUFFICIENT_DATA": "📊 DATA"
        }
        return mapping.get(momentum, momentum)
    
    def _get_edt_time(self):
        """Get current EDT time"""
        edt = timezone(timedelta(hours=-4))
        return datetime.now(edt).strftime("%m/%d/%Y, %I:%M %p")

