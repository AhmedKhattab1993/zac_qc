# main_minimal.py - Minimal Algorithm for Testing
from AlgorithmImports import *
from config.parameters import TradingParameters

class MinimalTradingAlgorithm(QCAlgorithm):
    """
    Lightweight algorithm used for smoke testing ZacQC dependencies.
    """
    
    def Initialize(self):
        """
        Configure a minimal environment with a single equity.

        Returns
        -------
        None
        """
        # Basic setup only
        self.SetStartDate(2024, 1, 3)
        self.SetCash(100000)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        # Add single symbol
        self.symbol = self.AddEquity("AAPL", Resolution.Second).Symbol
        
        self.Log("Minimal algorithm initialized successfully")
    
    def OnData(self, data):
        """
        No-op data handler used for interface validation.

        Parameters
        ----------
        data : Slice
            QuantConnect data slice.

        Returns
        -------
        None
        """
        pass
