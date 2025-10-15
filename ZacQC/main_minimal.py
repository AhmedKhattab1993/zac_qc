# main_minimal.py - Minimal Algorithm for Testing
from AlgorithmImports import *
from config.parameters import TradingParameters

class MinimalTradingAlgorithm(QCAlgorithm):
    """Minimal algorithm to test initialization"""
    
    def Initialize(self):
        # Basic setup only
        self.SetStartDate(2024, 1, 3)
        self.SetCash(100000)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        # Add single symbol
        self.symbol = self.AddEquity("AAPL", Resolution.Second).Symbol
        
        self.Log("Minimal algorithm initialized successfully")
    
    def OnData(self, data):
        """Minimal data processing"""
        pass