"""Utility functions"""
import pytz
from datetime import datetime
from config import TIMEZONE

def get_current_time():
    """Get current time in configured timezone"""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def time_remaining_in_quarter(quarter, time_elapsed):
    """Calculate time remaining based on quarter"""
    from config import QUARTER_SECONDS, OT_SECONDS
    if quarter > 4:
        max_seconds = OT_SECONDS
    else:
        max_seconds = QUARTER_SECONDS
    return max(0, max_seconds - time_elapsed)

def format_timestamp(dt):
    """Format datetime to ISO string"""
    return dt.isoformat()
