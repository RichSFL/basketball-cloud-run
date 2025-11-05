"""Configuration"""
import os

# API Config
API_TOKEN = os.getenv('API_TOKEN', '')
SPORT_ID = '18'              # Basketball
LEAGUE_ID = '25067'          # Your league
API_VERSION = 'v3'           # Use v3 for in-play!

# Google Cloud
GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
GCS_BUCKET = os.getenv('GCS_BUCKET', 'basketball-projections')

# Discord
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')

# Game timing
QUARTER_SECONDS = 300
OT_SECONDS = 180
GAME_SECONDS = 1200
TIMEZONE = 'America/New_York'
