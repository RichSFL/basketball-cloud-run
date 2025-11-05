"""CSV logging for projections"""
import csv
import logging
from datetime import datetime
from config import TIMEZONE
import pytz

logger = logging.getLogger(__name__)

class CSVLogger:
    def __init__(self, filename):
        self.filename = filename
        self.tz = pytz.timezone(TIMEZONE)
    
    def log_sample(self, row_data):
        """Log projection sample to CSV"""
        try:
            with open(self.filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row_data.keys())
                writer.writerow(row_data)
            return True
        except Exception as e:
            logger.error(f"Error logging to CSV: {e}")
            return False
    
    def initialize_csv(self, headers):
        """Initialize CSV with headers"""
        try:
            with open(self.filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            return True
        except Exception as e:
            logger.error(f"Error initializing CSV: {e}")
            return False
