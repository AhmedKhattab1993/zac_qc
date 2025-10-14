# utils.py - Basic Utility Functions for Reference Behavior
from AlgorithmImports import *
from datetime import time

class TradingUtils:
    """
    Basic utility functions for Reference behavior
    Simplified from enhanced ZacQC implementation
    """
    
    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.params = algorithm.parameters
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("Basic TradingUtils initialized")
    
    def IsMarketHours(self, dt=None):
        """Check if given time is during market hours"""
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time(9, 30) <= time_obj <= time(16, 0)
    
    def IsPreMarket(self, dt=None):
        """Check if given time is during pre-market hours"""
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time(4, 0) <= time_obj < time(9, 30)
    
    def IsAfterMarket(self, dt=None):
        """Check if given time is during after-market hours"""
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time_obj > time(16, 0) or time_obj < time(4, 0)
    
    def GetCurrentPrice(self, symbol):
        """Get current price for symbol"""
        
        if symbol in self.algorithm.Securities:
            return self.algorithm.Securities[symbol].Price
        return 0
    
    def FormatCurrency(self, amount):
        """Format amount as currency"""
        return f"${amount:.2f}"
    
    def FormatPercentage(self, value):
        """Format value as percentage"""
        return f"{value:.2f}%"
    
    def CalculatePercentageChange(self, old_value, new_value):
        """Calculate percentage change between two values"""
        
        if old_value == 0:
            return 0
        
        return ((new_value - old_value) / old_value) * 100
    
    def RoundToTick(self, price, tick_size=0.01):
        """Round price to nearest tick size"""
        
        return round(price / tick_size) * tick_size
    
    def ValidateOrder(self, symbol, quantity, price):
        """Basic order validation"""
        
        # Check for valid inputs
        if quantity <= 0 or price <= 0:
            return False
        
        # Check if symbol exists
        if symbol not in self.algorithm.Securities:
            return False
        
        # Check if market is open
        if not self.algorithm.IsMarketOpen(symbol):
            return False
        
        return True
    
    def __str__(self):
        """String representation"""
        return f"BasicTradingUtils(algorithm={self.algorithm.__class__.__name__})"