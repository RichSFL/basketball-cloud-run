"""Discord integration"""
import requests
import logging

logger = logging.getLogger(__name__)

class DiscordClient:
    """Send messages to Discord"""
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_message(self, message):
        """Send text message to Discord"""
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            payload = {"content": message}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("✅ Discord message sent")
            return True
        except Exception as e:
            logger.error(f"Discord error: {e}")
            return False
    
    def send_embed(self, title, description, fields=None):
        """Send embed to Discord"""
        if not self.webhook_url:
            return False
        
        try:
            embed = {
                "title": title,
                "description": description,
                "color": 3447003
            }
            if fields:
                embed["fields"] = fields
            
            payload = {"embeds": [embed]}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Discord embed error: {e}")
            return False

# --- The following function MUST be OUTSIDE the class! ---
def build_game_embed(game, home_score, away_score, total_score, q, m, s,
                    home_raw, home_avg, away_raw, away_avg, total_raw, total_avg,
                    home_line, away_line, total_line,
                    home_momentum, away_momentum, reliability, samples):
    """Return a dict suitable for DiscordClient.send_embed()"""

    quarter_label = f"Q{q}" if q <= 4 else f"OT{q-4}"
    time_str = f"{m}:{str(s).zfill(2)}"
    title = f"🏀 {game['home']['name']} vs. {game['away']['name']} | {quarter_label}, {time_str}"
    description = f"Score: {home_score}-{away_score} ({total_score})"

    fields = [
        {
            "name": f"{game['home']['name']} ({home_score})",
            "value": f"Raw: {home_raw} | Avg: **{home_avg}**\nLine: **{home_line}**\nMomentum: {home_momentum}",
            "inline": True
        },
        {
            "name": f"{game['away']['name']} ({away_score})",
            "value": f"Raw: {away_raw} | Avg: **{away_avg}**\nLine: **{away_line}**\nMomentum: {away_momentum}",
            "inline": True
        },
        {
            "name": "GAME TOTAL",
            "value": f"Raw: {total_raw} | Avg: **{total_avg}**\nLine: **{total_line}** | Diff: **{total_avg - total_line:.1f}**",
            "inline": False
        },
        {
            "name": "Reliability",
            "value": reliability,
            "inline": True
        },
        {
            "name": "Samples",
            "value": str(samples),
            "inline": True
        }
    ]

    return {
        "title": title,
        "description": description,
        "fields": fields
    }
