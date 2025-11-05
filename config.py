"""Config"""
import os

API_TOKEN = os.getenv('API_TOKEN', '')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')
GCS_BUCKET = os.getenv('GCS_BUCKET', 'basketball-projections')
GCS_PROJECT = os.getenv('GCS_PROJECT', 'basketball-projections-python')
