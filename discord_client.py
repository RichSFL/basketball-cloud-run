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

