# symbol_manager.py - Basic Symbol Management for Reference Behavior
from AlgorithmImports import *

from data.data_manager import DataManager
from data.metrics_calculator import MetricsCalculator
from trading.order_manager import OrderManager
from trading.conditions_checker import ConditionsChecker
from core.strategy import Strategy

class AlgorithmWrapper:
    """Wrapper to provide symbol-specific context"""
    
    def __init__(self, algorithm, symbol):
        self.algorithm = algorithm
        self.symbol = symbol
    
    def __getattr__(self, name):
        """Delegate all other attributes to the original algorithm"""
        # CRITICAL FIX: Intercept 'symbol' access to return the wrapper's symbol instead of the main algorithm's symbol
        if name == 'symbol':
            return self.symbol
        return getattr(self.algorithm, name)

class SymbolManager:
    """
    Basic symbol management for Reference behavior
    Simplified from enhanced ZacQC implementation
    """
    
    def __init__(self, algorithm, symbol_name, symbol):
        self.algorithm = algorithm
        self.symbol_name = symbol_name
        self.symbol = symbol
        self.params = algorithm.parameters
        
        # Basic components
        self.data_manager = None
        self.metrics_calculator = None
        self.conditions_checker = None
        self.order_manager = None
        self.strategies = []
        
        # Phase 1: Timing Controls System
        self.last_execution_time_symbol = None
        self.last_execution_times = {
            'cond1': None,
            'cond2': None, 
            'cond3': None,
            'cond4': None,
            'cond5': None
        }
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - SymbolManager created for {symbol_name} with Phase 1 timing controls")
    
    def Initialize(self):
        """Initialize basic symbol management"""
        
        try:
            # Symbol already provided in constructor - no need to add again
            
            # Create wrapper for symbol-specific context
            wrapped_algorithm = AlgorithmWrapper(self.algorithm, self.symbol)
            
            # Initialize basic components - data_manager first
            self.data_manager = DataManager(wrapped_algorithm, self)  # Pass self for trailing order logging
            # Note: InitializeConsolidators() is called in DataManager constructor - no need to call again
            
            # Add data_manager to wrapped algorithm for other components
            wrapped_algorithm.data_manager = self.data_manager
            
            self.metrics_calculator = MetricsCalculator(wrapped_algorithm)
            
            # Add metrics_calculator to wrapped algorithm for conditions checker access
            wrapped_algorithm.metrics_calculator = self.metrics_calculator
            
            self.conditions_checker = ConditionsChecker(wrapped_algorithm)
            self.order_manager = OrderManager(wrapped_algorithm)
            
            # Initialize basic strategy
            self.InitializeBasicStrategy()
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Basic SymbolManager initialized for {self.symbol_name}")
            
        except Exception as e:
            self.algorithm.Error(f"Error initializing SymbolManager for {self.symbol_name}: {e}")
            raise
    
    def InitializeBasicStrategy(self):
        """Initialize basic strategy for Reference behavior"""
        
        # Create single basic strategy
        strategy = Strategy(self.algorithm, "basic_strategy", self.symbol_name)
        strategy.Initialize()
        self.strategies.append(strategy)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Basic strategy initialized for {self.symbol_name}")
    
    def OnData(self, data):
        """Process data for this symbol - Reference behavior"""
        
        if self.symbol not in data or not data[self.symbol]:
            return
        
        try:
            # CRITICAL: Check P&L limit EVERY SECOND before any other processing
            # This ensures we catch limit breaches immediately, not just every 15 seconds
            if hasattr(self.algorithm, 'risk_manager'):
                # Check if daily limit already reached
                if hasattr(self.algorithm.risk_manager, 'daily_limit_reached') and self.algorithm.risk_manager.daily_limit_reached:
                    return
                
                # Do fresh P&L check including unrealized P&L
                if hasattr(self.algorithm.risk_manager, 'CheckDailyPnLLimit'):
                    if self.algorithm.risk_manager.CheckDailyPnLLimit():
                        # Limit just hit - stop all processing
                        return
            
            # Basic data processing (only continues every 15 seconds)
            if not self.data_manager.OnData(data):
                return
            
            # Phase 3: Update rally detector with new price data
            if hasattr(self.conditions_checker, 'update_rally_data'):
                self.conditions_checker.update_rally_data(self.symbol_name, data[self.symbol])
            
            # Calculate basic metrics
            metrics = self.metrics_calculator.CalculateAllMetrics(data)
            
            # Check gap threshold for all strategies (Reference implementation)
            for strategy in self.strategies:
                strategy.check_gap_threshold(self.metrics_calculator)
            
            # Check range and liquidity thresholds (similar to gap threshold - daily check)
            for strategy in self.strategies:
                strategy.check_range_and_liquidity_threshold(self.metrics_calculator)
            
            # Check sharp movement threshold for all strategies (Reference implementation)
            for strategy in self.strategies:
                strategy.check_sharp_movement_threshold(self.metrics_calculator)
            
            # Process each strategy
            for strategy in self.strategies:
                self.ProcessBasicStrategy(strategy, data, metrics)
                
                # Phase 3: Continuous VWAP monitoring for order cancellation
                if hasattr(self.order_manager, 'monitor_vwap_conditions'):
                    self.order_manager.monitor_vwap_conditions()
                
                # Range-based order cancellation monitoring (Reference: ib.py cancel_long/cancel_short)
                if hasattr(self.order_manager, 'monitor_range_based_cancellations'):
                    self.order_manager.monitor_range_based_cancellations()
                
                # Update stop loss orders based on profit thresholds (Reference: ib.py update_stop_loss)
                if hasattr(self.order_manager, 'update_stop_loss'):
                    self.order_manager.update_stop_loss()
                
                # ACTION TIME: Update trade time actions if enabled (Reference: ib.py lines 2882-2891)
                self.update_trade_time_actions(data[self.symbol].Close)
                
        except Exception as e:
            self.algorithm.Error(f"Error in OnData for {self.symbol_name}: {e}")
    
    def ProcessBasicStrategy(self, strategy, data, metrics):
        """Process basic trading logic for strategy"""
        
        current_price = data[self.symbol].Close
        
        # Skip trading if disabled by any threshold (gap, range, liquidity)
        if not strategy.trading_enabled:
            return
        
        # Check liquidity threshold (Reference implementation)
        if not self.check_liquidity_threshold(metrics):
            return
        
        # CRITICAL: Check daily P&L limit before evaluating any conditions
        # This prevents new orders from being placed when daily limit is reached
        if hasattr(self.algorithm, 'risk_manager') and hasattr(self.algorithm.risk_manager, 'daily_limit_reached'):
            if self.algorithm.risk_manager.daily_limit_reached:
                # Skip all condition checking if daily limit was already hit
                return
        
        # Also do a fresh P&L check to catch the limit early
        if hasattr(self.algorithm, 'risk_manager') and hasattr(self.algorithm.risk_manager, 'CheckDailyPnLLimit'):
            if self.algorithm.risk_manager.CheckDailyPnLLimit():
                # Daily limit just hit, skip processing
                return
        
        # Check all conditions
        conditions = self.conditions_checker.CheckAllConditions(strategy, metrics)
        
        # Execute trades based on met conditions
        for condition, is_met in conditions.items():
            if is_met:
                # CRITICAL FIX: Check timing constraints before placing any order
                if not self.ValidateTimingConstraints(condition):
                    continue  # Skip this condition if timing constraints are not met
                
                order_placed = False
                # Check if condition is enabled
                if condition in ['cond1', 'cond2', 'cond3']:
                    order_placed = self.order_manager.ExecuteLongEntry(strategy, condition, current_price, metrics)
                elif condition in ['cond4', 'cond5']:
                    order_placed = self.order_manager.ExecuteShortEntry(strategy, condition, current_price, metrics)
                
                # NOTE: Execution times are updated when positions EXIT, not when orders are placed
                # This happens in order_manager._handle_sltp_fill_and_cancel_counterpart
    
    def OnOrderEvent(self, orderEvent):
        """Handle order events for this symbol"""
        
        if orderEvent.Symbol == self.symbol:
            self.order_manager.OnOrderEvent(orderEvent, self.strategies)
    
    def CustomEndOfDay(self):
        """Custom end-of-day liquidation at 15:59 (1 minute before market close)"""
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - === Custom EOD liquidation started for {self.symbol_name} at 15:59 ===")
        
        # Close all positions and cancel pending orders
        self.order_manager.CloseAllPositions()
        
        # Clear any strategy-level pending orders
        for strategy in self.strategies:
            if hasattr(strategy, 'pending_orders'):
                orders_cleared = len(strategy.pending_orders)
                strategy.pending_orders.clear()
                if orders_cleared > 0:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Cleared {orders_cleared} strategy pending orders for {self.symbol_name}")
        
        # Reset daily states for next trading day
        self.ResetDailyStates()
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Custom EOD liquidation complete for {self.symbol_name}")
    
    def OnMarketClose(self):
        """Built-in market close handler - used for final cleanup only"""
        
        # This runs after market close - just log final status
        portfolio_quantity = self.algorithm.Portfolio[self.symbol].Quantity
        if portfolio_quantity != 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - WARNING: {self.symbol_name} still has position {portfolio_quantity} at market close!")
        else:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Confirmed: {self.symbol_name} position properly closed at market close")
    
    def ResetDailyStates(self):
        """Reset all daily tracking states for next trading day"""
        
        # Reset data manager daily values (but preserve accumulated bars)
        if hasattr(self.data_manager, 'ResetDaily'):
            self.data_manager.ResetDaily()
        
        # Phase 3: Reset rally detector daily data
        if hasattr(self.conditions_checker, 'reset_daily_rally_data'):
            self.conditions_checker.reset_daily_rally_data()
        
        # Reset strategy daily states  
        for strategy in self.strategies:
            if hasattr(strategy, 'ResetDailyState'):
                strategy.ResetDailyState()
            # Reset trading_enabled flag for next day (Reference implementation)
            strategy.trading_enabled = True
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Daily states reset for {self.symbol_name}")
    
    # =======================================================================
    # PHASE 1: TIMING CONTROLS SYSTEM
    # =======================================================================
    
    def ValidateTimingConstraints(self, condition):
        """
        Check if enough time has passed for this condition and symbol
        Reference: lines 765, 777, 805, 818, 830 in ib.py
        """
        current_time = self.algorithm.Time
        
        # Check symbol-level timing constraint
        if self.last_execution_time_symbol:
            symbol_minutes = (current_time - self.last_execution_time_symbol).total_seconds() / 60.0
            if symbol_minutes < self.params.SameSymbolTime:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Symbol timing constraint: {symbol_minutes:.1f} < {self.params.SameSymbolTime} minutes for {self.symbol_name}")
                return False
        
        # Check condition-specific timing constraint
        condition_cooldown = self.params.get_condition_cooldown(condition)
        last_condition_time = self.last_execution_times.get(condition)
        
        if last_condition_time:
            condition_minutes = (current_time - last_condition_time).total_seconds() / 60.0
            if condition_minutes < condition_cooldown:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition timing constraint: {condition} {condition_minutes:.1f} < {condition_cooldown} minutes")
                return False
                
        return True
    
    def UpdateExecutionTime(self, condition):
        """Update execution times after placing an order"""
        current_time = self.algorithm.Time
        self.last_execution_time_symbol = current_time
        self.last_execution_times[condition] = current_time
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"Execution time updated for {condition} at {current_time}")
    
    def update_trade_time_actions(self, last_price):
        """
        Update trade time actions for all strategies (Reference: ib.py lines 2880-2891)
        Called periodically to check if action time thresholds are met
        """
        try:
            if self.params.Allow_Actions:
                for strategy in self.strategies:
                    if hasattr(strategy, 'trade_time_action'):
                        strategy.trade_time_action(last_price)
        except Exception as e:
            self.algorithm.Error(f"Error in update_trade_time_actions for {self.symbol_name}: {e}")
    
    def check_liquidity_threshold(self, metrics):
        """
        Check if liquidity meets minimum threshold (Reference implementation)
        Formula: if metric_liquidity/1e6 > liquidity_threshold
        Returns True if trading is allowed, False if liquidity is too low
        """
        try:
            # Get liquidity threshold parameter
            liquidity_threshold = self.params.Liquidity_Threshold
            
            # If threshold is 0, always allow trading (no liquidity check)
            if liquidity_threshold <= 0:
                return True
            
            # Get liquidity in millions from metrics
            if 'metric_liquidity_millions' in metrics:
                liquidity_millions = metrics['metric_liquidity_millions']
            else:
                # Fallback calculation if not in metrics
                liquidity = metrics.get('metric_liquidity', 0)
                liquidity_millions = liquidity / 1e6
            
            # Check if liquidity exceeds threshold
            if liquidity_millions > liquidity_threshold:
                return True
            else:
                # Log when liquidity check fails (similar to Reference algo disabling)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Liquidity threshold not met for {self.symbol_name}: {liquidity_millions:.2f}M < {liquidity_threshold}M - Trading SKIPPED")
                return False
                
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Error in liquidity threshold check: {e}")
            # On error, allow trading
            return True
    
    def check_range_multiple_threshold_OLD_DEPRECATED(self, metrics_calculator):
        """
        Check if range multiple exceeds threshold and disable algorithm if needed
        Also re-enable algorithm if liquidity conditions are met
        Reference implementation: ib.py lines 2190-2201
        """
        try:
            # Only check during market hours (Reference: if is_marketopen)
            current_time = self.algorithm.Time
            market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
            
            if current_time < market_open or current_time >= market_close:
                return
            
            # Get the calculated metric_range_multiplier
            metric_range_multiplier = metrics_calculator.metric_range_multiplier
            
            # Get RangeMultipleThreshold parameter
            rangemultiple_threshold = self.params.RangeMultipleThreshold
            
            # Reference check: if metric_range_multiplier > rangemultiple_threshold
            if metric_range_multiplier > rangemultiple_threshold:
                # Disable algorithm for all strategies (Reference: self.set_algo(False))
                for strategy in self.strategies:
                    strategy.set_algo(False)
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Range Multiple threshold exceeded for {self.symbol_name}: {metric_range_multiplier:.2f} > {rangemultiple_threshold} - Algorithm DISABLED")
            
            # Reference liquidity check to re-enable algo (ib.py lines 2198-2201)
            # Check if liquidity exceeds threshold and algo was previously enabled
            metric_liquidity = metrics_calculator.metric_liquidity
            liquidity_threshold = self.params.Liquidity_Threshold
            
            if metric_liquidity / 1e6 > liquidity_threshold:
                # Check if any strategy has algo_enabled as True initially (metric_algo == 1)
                for strategy in self.strategies:
                    # Only re-enable if it was initially enabled (similar to metric_algo == 1 check)
                    if hasattr(strategy, 'initial_algo_state'):
                        if strategy.initial_algo_state:
                            strategy.set_algo(True)
                    else:
                        # First time - store initial state
                        strategy.initial_algo_state = strategy.algo_enabled
            else:
                # Disable if liquidity is below threshold
                for strategy in self.strategies:
                    strategy.set_algo(False)
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Liquidity below threshold for {self.symbol_name}: {metric_liquidity/1e6:.2f}M < {liquidity_threshold}M - Algorithm DISABLED")
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Error in range multiple threshold check: {e}")
    
    def __str__(self):
        """String representation"""
        return f"SymbolManager({self.symbol_name}, strategies={len(self.strategies)}, timing_controls=enabled)"