"""Configuration"""
import os

# API Config
API_TOKEN = os.getenv('API_TOKEN', 'test-token')
LEAGUE_ID = os.getenv('LEAGUE_ID', '1')
SPORT_ID = os.getenv('SPORT_ID', '2')

# GCS Config
GCS_PROJECT_ID = os.getenv('GCS_PROJECT', 'basketball-projections-python')
GCS_BUCKET = os.getenv('GCS_BUCKET', 'basketball-projections')

# Game Config
QUARTER_SECONDS = 720
OT_SECONDS = 300
TIMEZONE = 'America/New_York'

# Thresholds
LEADER_THRESHOLD_POINTS = 5
LEADER_THRESHOLD_REBOUNDS = 3
LEADER_THRESHOLD_ASSISTS = 3
