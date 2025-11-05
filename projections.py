"""Projection calculation logic"""
import statistics
import logging

logger = logging.getLogger(__name__)

class ProjectionCalculator:
    def __init__(self):
        self.samples = []
    
    def add_sample(self, value):
        """Add a data sample"""
        self.samples.append(value)
    
    def raw_projection(self):
        """Calculate raw average projection"""
        if not self.samples:
            return None
        return statistics.mean(self.samples)
    
    def simple_average(self):
        """Simple moving average"""
        if len(self.samples) < 2:
            return self.raw_projection()
        return statistics.mean(self.samples[-5:]) if len(self.samples) >= 5 else statistics.mean(self.samples)
    
    def exponential_moving_avg(self, alpha=0.3):
        """Exponential moving average"""
        if not self.samples:
            return None
        ema = self.samples[0]
        for value in self.samples[1:]:
            ema = (alpha * value) + ((1 - alpha) * ema)
        return ema
    
    def clear_samples(self):
        """Clear sample history"""
        self.samples = []
