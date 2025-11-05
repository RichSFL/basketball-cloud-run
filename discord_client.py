"""Discord webhook client"""
import requests
import logging

logger = logging.getLogger(__name__)

class DiscordClient:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_message(self, title, description, color=3447003):
        """Send embedded message to Discord"""
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color
            }
            payload = {"embeds": [embed]}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return False
    
    def send_projection_alert(self, player_name, projection, betting_line):
        """Send projection alert"""
        title = f"🏀 {player_name} Projection"
        description = f"**Projection:** {projection}\n**Line:** {betting_line}"
        return self.send_message(title, description)
