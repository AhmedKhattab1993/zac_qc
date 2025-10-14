# utils.py - Basic Utility Functions for Reference Behavior
from AlgorithmImports import *
from datetime import time

class TradingUtils:
    """
    Convenience utilities shared across trading components.

    The helper functions centralize calendar checks, formatting helpers,
    and lightweight calculations so that other modules can remain focused
    on strategy logic. The utilities require access to the parent algorithm
    to pull clock, parameter, and portfolio context.

    Parameters
    ----------
    algorithm : Algorithm
        The QuantConnect `QCAlgorithm` implementation that owns these utilities.
    """
    
    def __init__(self, algorithm):
        """
        Store references to the parent algorithm and its parameter set.

        Parameters
        ----------
        algorithm : Algorithm
            The algorithm instance that exposes time, securities, and logging APIs.
        """
        self.algorithm = algorithm
        self.params = algorithm.parameters
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("Basic TradingUtils initialized")
    
    def IsMarketHours(self, dt=None):
        """
        Check whether the supplied timestamp falls inside regular market hours.

        Parameters
        ----------
        dt : datetime.datetime, optional
            Timestamp to evaluate. Defaults to the algorithm clock.

        Returns
        -------
        bool
            True when the time is between 09:30 and 16:00 inclusive.
        """
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time(9, 30) <= time_obj <= time(16, 0)
    
    def IsPreMarket(self, dt=None):
        """
        Determine whether the timestamp occurs during the pre-market session.

        Parameters
        ----------
        dt : datetime.datetime, optional
            Timestamp to evaluate. Defaults to the algorithm clock.

        Returns
        -------
        bool
            True when the time is between 04:00 and 09:30.
        """
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time(4, 0) <= time_obj < time(9, 30)
    
    def IsAfterMarket(self, dt=None):
        """
        Determine whether the timestamp occurs during the post-market session.

        Parameters
        ----------
        dt : datetime.datetime, optional
            Timestamp to evaluate. Defaults to the algorithm clock.

        Returns
        -------
        bool
            True when the time is after 16:00 or before 04:00.
        """
        if dt is None:
            dt = self.algorithm.Time
        
        time_obj = dt.time()
        return time_obj > time(16, 0) or time_obj < time(4, 0)
    
    def GetCurrentPrice(self, symbol):
        """
        Fetch the current price for a tracked security.

        Parameters
        ----------
        symbol : Symbol
            QuantConnect security symbol.

        Returns
        -------
        float
            Last known price for the security, or 0 when the symbol is absent.
        """
        
        if symbol in self.algorithm.Securities:
            return self.algorithm.Securities[symbol].Price
        return 0
    
    def FormatCurrency(self, amount):
        """
        Render monetary values as human-friendly strings.

        Parameters
        ----------
        amount : float
            Dollar amount to format.

        Returns
        -------
        str
            Currency string representation (e.g. ``$10.00``).
        """
        return f"${amount:.2f}"
    
    def FormatPercentage(self, value):
        """
        Render fractional values as percentages.

        Parameters
        ----------
        value : float
            Percentage value expressed as a numeric scalar. The formatting
            does not scale the number, so pass 50 for 50%.

        Returns
        -------
        str
            Percentage string representation (e.g. ``50.00%``).
        """
        return f"{value:.2f}%"
    
    def CalculatePercentageChange(self, old_value, new_value):
        """
        Compute the percentage change between two values.

        Parameters
        ----------
        old_value : float
            Baseline value.
        new_value : float
            Updated value.

        Returns
        -------
        float
            Percentage change expressed as a floating-point number.
        """
        
        if old_value == 0:
            return 0
        
        return ((new_value - old_value) / old_value) * 100
    
    def RoundToTick(self, price, tick_size=0.01):
        """
        Snap prices to the nearest permitted tick size.

        Parameters
        ----------
        price : float
            Raw price to round.
        tick_size : float, default 0.01
            Minimum tick increment for the instrument.

        Returns
        -------
        float
            Price aligned to the tick grid.
        """
        
        return round(price / tick_size) * tick_size
    
    def ValidateOrder(self, symbol, quantity, price):
        """
        Validate basic order parameters before submission.

        Parameters
        ----------
        symbol : Symbol
            QuantConnect security symbol.
        quantity : int
            Shares to trade. Must be positive.
        price : float
            Target price level. Must be positive.

        Returns
        -------
        bool
            True when the order passes basic validation checks.
        """
        
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
        """
        Return a readable representation of the utility wrapper.

        Returns
        -------
        str
            Name of the owning algorithm for debugging.
        """
        return f"BasicTradingUtils(algorithm={self.algorithm.__class__.__name__})"
