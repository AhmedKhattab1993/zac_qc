# risk_manager.py - Basic Risk Management for Reference Behavior
from AlgorithmImports import *

class RiskManager:
    """
    Enforce ZacQC reference risk constraints and daily P&L limits.

    Parameters
    ----------
    algorithm : Algorithm
        Parent QCAlgorithm instance.
    """
    
    def __init__(self, algorithm):
        """
        Initialise risk tracking storage and references.

        Parameters
        ----------
        algorithm : Algorithm
            Parent QCAlgorithm instance.
        """
        self.algorithm = algorithm
        self.params = algorithm.parameters
        
        # Basic risk tracking
        self.daily_pnl = 0
        self.max_daily_loss_reached = False
        self.target_pnl_reached = False  # Track if target PnL is reached (matching reference)
        self.daily_limit_reached = False  # Flag to prevent new orders once limit is hit
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("Basic RiskManager initialized")
    
    def ValidateTradingConditions(self, metrics=None):
        """
        Decide whether the strategy may trade at the current time.

        Parameters
        ----------
        metrics : dict, optional
            Optionally supplied metric bundle for context.

        Returns
        -------
        bool
            True when trading is permitted, otherwise False.
        """
        
        # Check daily P&L limit
        if self.CheckDailyPnLLimit():
            return False
        
        # Check market hours
        if not self.IsMarketOpen():
            return False
        
        return True
    
    def CheckDailyPnLLimit(self):
        """
        Determine whether the daily P&L limit has been breached.

        Returns
        -------
        bool
            True when the limit is hit and trading should halt.
        """
        
        # Calculate net liquidation value (portfolio value)
        net_liq = self.algorithm.Portfolio.TotalPortfolioValue
        
        # Skip check if net_liq is 0 to avoid division by zero
        if net_liq == 0:
            return False
        
        # Get starting value for the day (should be tracked at market open)
        # CRITICAL: Only set this ONCE per day at market open, never during the day
        current_date = self.algorithm.Time.date()
        if not hasattr(self, 'daily_starting_value') or not hasattr(self, 'starting_value_date') or self.starting_value_date != current_date:
            # Only set at the beginning of a new trading day
            self.daily_starting_value = net_liq
            self.starting_value_date = current_date
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Daily starting portfolio value set: ${self.daily_starting_value:.2f}")
        
        # CRITICAL FIX: Calculate realized P&L only (excluding unrealized)
        # TotalPortfolioValue already includes unrealized gains, so we need to subtract them
        # to get the true realized P&L for the day
        realized_pnl = self.algorithm.Portfolio.TotalProfit  # This is cumulative realized P&L
        
        # For daily P&L tracking, we need today's realized P&L only
        if not hasattr(self, 'starting_realized_pnl') or self.starting_value_date != current_date:
            self.starting_realized_pnl = realized_pnl
        
        daily_realized_pnl = realized_pnl - self.starting_realized_pnl
        
        # Calculate realized P&L as percentage of starting value
        daily_realized_pnl_pct = (daily_realized_pnl * 100) / self.daily_starting_value
        
        # CRITICAL FIX: Calculate our own unrealized P&L using current prices
        # This is more accurate than QuantConnect's UnrealizedProfit
        total_unrealized = 0
        custom_total_unrealized = 0
        
        # Calculate both QuantConnect's and our custom unrealized P&L
        for symbol_name, symbol in self.algorithm.symbols.items():
            holdings = self.algorithm.Portfolio[symbol]
            if holdings.Quantity != 0:
                # QuantConnect's calculation
                total_unrealized += holdings.UnrealizedProfit
                
                # Our custom calculation using actual current price
                current_price = self.algorithm.Securities[symbol].Price
                avg_price = holdings.AveragePrice
                
                if holdings.Quantity > 0:
                    # Long position: profit = (current - avg) * quantity
                    custom_unrealized = (current_price - avg_price) * holdings.Quantity
                else:
                    # Short position: profit = (avg - current) * abs(quantity)
                    custom_unrealized = (avg_price - current_price) * abs(holdings.Quantity)
                
                custom_total_unrealized += custom_unrealized
        
        # Calculate total P&L (realized + unrealized) using both QC and custom calculations
        qc_total_pnl = daily_realized_pnl + total_unrealized
        qc_total_pnl_pct = (qc_total_pnl * 100) / self.daily_starting_value
        
        # Calculate with custom unrealized for more accuracy
        custom_total_pnl = daily_realized_pnl + custom_total_unrealized
        custom_total_pnl_pct = (custom_total_pnl * 100) / self.daily_starting_value
        
        # Determine if we should log based on P&L level
        current_time = self.algorithm.Time
        should_log = False
        
        # Always log if we're within 0.05% of the limit (using CUSTOM calculation)
        if abs(custom_total_pnl_pct - self.params.Max_Daily_PNL) < 0.05:
            should_log = True
        
        # Or log once per minute when P&L is above 0.20% (approaching limit)
        if custom_total_pnl_pct > 0.20:
            if not hasattr(self, 'last_pnl_log_time') or (current_time - self.last_pnl_log_time).total_seconds() > 60:
                should_log = True
        
        # Or log once per hour normally
        elif not hasattr(self, 'last_pnl_log_time') or (current_time - self.last_pnl_log_time).total_seconds() > 3600:
            should_log = True
        
        
        if should_log and self.algorithm.enable_logging:
            # Show both QC and custom calculations for comparison
            self.algorithm.Log(f"Daily P&L Check: Realized=${daily_realized_pnl:.2f} ({daily_realized_pnl_pct:.2f}%) | QC Unrealized=${total_unrealized:.2f} | Custom Unrealized=${custom_total_unrealized:.2f} | QC Total=${qc_total_pnl:.2f} ({qc_total_pnl_pct:.2f}%) | Custom Total=${custom_total_pnl:.2f} ({custom_total_pnl_pct:.2f}%) | Start=${self.daily_starting_value:.2f}, Current=${net_liq:.2f}, Limit={self.params.Max_Daily_PNL}%")
            self.last_pnl_log_time = current_time
        
        # Check against max daily P&L limit (as percentage, matching reference)
        if self.params.Max_Daily_PNL > 0:
            # CRITICAL FIX: Use CUSTOM P&L calculation for more accurate limit enforcement
            # This ensures we stop trading at exactly the right level
            if custom_total_pnl_pct >= self.params.Max_Daily_PNL:
                if not self.target_pnl_reached:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"🎯 TARGET P&L REACHED: ${custom_total_pnl:.2f} ({custom_total_pnl_pct:.2f}%) [Custom calc] | QC showed: ${qc_total_pnl:.2f} ({qc_total_pnl_pct:.2f}%) | Liquidating all positions")
                    self.target_pnl_reached = True
                    self.daily_limit_reached = True  # Set flag to block new orders
                    # Liquidate all positions and cancel orders (matching reference)
                    self.HandleTargetPnLReached()
                return True
        
        return False
    
    def IsMarketOpen(self):
        """
        Check whether the primary symbol's market is open.

        Returns
        -------
        bool
            True if the exchange is open for trading.
        """
        return self.algorithm.IsMarketOpen(self.algorithm.symbol)
    
    def CanPlaceOrder(self, symbol, quantity, current_price):
        """
        Validate a prospective order against daily P&L gating.

        Parameters
        ----------
        symbol : Symbol
            Symbol to be traded.
        quantity : int
            Intended order quantity.
        current_price : float
            Price estimate used for validation.

        Returns
        -------
        bool
            True when the order may be placed.
        """
        
        # Simple flag check - if limit was reached today, no new orders allowed
        if self.daily_limit_reached:
            return False
            
        # Allow all orders if limit hasn't been reached
        return True
    
    def UpdateDailyPnL(self):
        """
        Refresh cached daily P&L metrics from the portfolio.

        Returns
        -------
        None
        """
        self.daily_pnl = self.algorithm.Portfolio.TotalUnrealizedProfit + self.algorithm.Portfolio.TotalProfit
    
    def ResetDaily(self):
        """
        Reset daily risk state in preparation for the next session.

        Returns
        -------
        None
        """
        
        self.daily_pnl = 0
        self.max_daily_loss_reached = False
        self.target_pnl_reached = False  # Reset target PnL reached flag
        self.daily_limit_reached = False  # Reset the daily limit flag for next day
        
        # Reset realized P&L tracking for next day
        if hasattr(self, 'starting_realized_pnl'):
            self.starting_realized_pnl = self.algorithm.Portfolio.TotalProfit
        
        # Log the day's performance before reset
        if hasattr(self, 'daily_starting_value'):
            old_value = self.daily_starting_value
            current_value = self.algorithm.Portfolio.TotalPortfolioValue
            daily_return = ((current_value - old_value) / old_value) * 100 if old_value != 0 else 0
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Daily performance - Start: ${old_value:.2f}, End: ${current_value:.2f}, Daily Return: {daily_return:.2f}%")
            
            # DON'T delete daily_starting_value here - let it be reset on the next trading day
            # This prevents mid-day resets if ResetDaily is called accidentally
    
    def HandleTargetPnLReached(self):
        """
        Execute liquidation and cancellation workflow after hitting the target P&L.

        Returns
        -------
        None
        """
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("=== TARGET P&L REACHED - CANCELLING ENTRY ORDERS & LIQUIDATING POSITIONS ===")
        
        # First, cancel all pending entry orders (same logic as CancelEntryOrdersAtAlgoOff)
        for symbol_name, symbol_manager in self.algorithm.symbol_managers.items():
            symbol = self.algorithm.symbols[symbol_name]
            
            # Get all open orders for this symbol
            open_orders = self.algorithm.Transactions.GetOpenOrders(symbol)
            
            if len(open_orders) > 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Processing {symbol_name}: {len(open_orders)} open orders")
                
                for order in open_orders:
                    order_ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
                    order_tag = order_ticket.Tag if order_ticket else ""
                    
                    # Identify entry orders by their tags
                    is_entry_order = False
                    if order_tag:
                        if order_tag.startswith("Buy-") and "-Trail-" in order_tag:
                            is_entry_order = True
                        elif order_tag.startswith("Short-") and "-Trail-" in order_tag:
                            is_entry_order = True
                        elif order_tag.startswith("Trail-Update-") and any(cond in order_tag for cond in ["cond1", "cond2", "cond3", "cond4", "cond5"]):
                            is_entry_order = True
                    
                    if is_entry_order:
                        # Cancel entry order
                        self.algorithm.Transactions.CancelOrder(order.Id)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"  Cancelled ENTRY order: OrderID={order.Id}, Tag={order_tag}")
                        
                        # Clear the pending order from strategy tracking
                        condition = None
                        if order_tag.startswith("Trail-Update-"):
                            parts = order_tag.split("-")
                            if len(parts) >= 3:
                                condition = parts[2]
                        elif "-Trail-" in order_tag:
                            parts = order_tag.split("-")
                            if len(parts) >= 2:
                                condition = parts[1]
                        
                        if condition:
                            # Clear pending order tracking and reset condition state
                            for strategy in symbol_manager.strategies:
                                if hasattr(strategy, 'pending_orders') and condition in strategy.pending_orders:
                                    del strategy.pending_orders[condition]
                                    if self.algorithm.enable_logging:
                                        self.algorithm.Log(f"    Cleared pending order tracking for {condition}")
                                
                                if hasattr(strategy, 'reset_condition_state'):
                                    condition_key = condition.replace("cond", "c")
                                    strategy.reset_condition_state(condition_key)
                                    if self.algorithm.enable_logging:
                                        self.algorithm.Log(f"    Reset condition state for {condition_key}")
        
        # Then liquidate all positions with market orders tagged as "targetprofit"
        for symbol_name, symbol in self.algorithm.symbols.items():
            holdings = self.algorithm.Portfolio[symbol]
            if holdings.Quantity != 0:
                # Place market order to close position
                quantity_to_close = -holdings.Quantity  # Negative to close
                order_ticket = self.algorithm.MarketOrder(
                    symbol, 
                    quantity_to_close,
                    tag="targetprofit"
                )
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Liquidating {symbol_name}: {holdings.Quantity} shares at market (Order: {order_ticket.OrderId})")
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("=== TARGET P&L REACHED - ALL ENTRY ORDERS CANCELLED & POSITIONS LIQUIDATED ===")
    
    def __str__(self):
        """String representation"""
        return f"BasicRiskManager(daily_pnl={self.daily_pnl:.2f}, max_loss_reached={self.max_daily_loss_reached})"
