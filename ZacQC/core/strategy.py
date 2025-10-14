# strategy.py - Basic Strategy for Reference Behavior
from AlgorithmImports import *
from datetime import timedelta

class Strategy:
    """
    Basic strategy management for Reference behavior
    Simplified from enhanced ZacQC implementation
    """
    
    def __init__(self, algorithm, account_id, symbol_name):
        self.algorithm = algorithm
        self.account_id = account_id
        self.symbol_name = symbol_name
        
        # Basic state tracking
        self.pending_orders = {}
        self.active_positions = {}
        
        # Gap threshold check - trading enabled flag (Reference implementation)
        self.trading_enabled = True
        self.gap_threshold_logged = False  # Track if gap threshold message was logged today
        self.range_threshold_logged = False  # Track if range threshold message was logged today
        
        # Range Multiple Threshold - algorithm enabled flag (Reference implementation)
        # This matches Reference metric_algo variable (ib.py line 1011)
        self.algo_enabled = True
        
        # Phase 3: Reference Sequential State Machine - Persistent condition states (like strategy.c1, strategy.c2, etc.)
        self.c1 = False  # Condition 1 persistent state (matches Reference strategy.c1)
        self.c2 = False  # Condition 2 persistent state (matches Reference strategy.c2)
        self.c3 = False  # Condition 3 persistent state (matches Reference strategy.c3)
        self.c4 = False  # Condition 4 persistent state (matches Reference strategy.c4)
        self.c5 = False  # Condition 5 persistent state (matches Reference strategy.c5)
        
        # Phase 3: Last execution tracking for timing constraints (matches Reference)
        self.last_execution_date_c1 = self.algorithm.Time
        self.last_execution_date_c2 = self.algorithm.Time
        self.last_execution_date_c3 = self.algorithm.Time
        self.last_execution_date_c4 = self.algorithm.Time
        self.last_execution_date_c5 = self.algorithm.Time
        
        # Phase 3: Configuration reference for timing constraints
        self.cfg = algorithm.parameters  # Reference to trading parameters
        
        # Action time tracking (Reference: ib.py lines 139-141)
        self.trade_start_time = None
        self.trade_start_time_actionx = False
        self.trade_start_time_actiony = False
        self.last_update_trade_start_time = self.algorithm.Time
        
        # Legacy compatibility - keep for existing code
        self.condition_states = {
            'cond1': False,
            'cond2': False,
            'cond3': False,
            'cond4': False,
            'cond5': False
        }
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Basic Strategy initialized for {symbol_name} - account {account_id}")
    
    def Initialize(self):
        """Initialize basic strategy"""
        
        # Reset all states
        self.pending_orders.clear()
        self.active_positions.clear()
        
        for condition in self.condition_states:
            self.condition_states[condition] = False
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Basic strategy initialized for {self.symbol_name}")
    
    def ResetDailyState(self):
        """Reset daily strategy state"""
        
        # Clear pending orders
        self.pending_orders.clear()
        
        # Reset gap threshold logging flag for next day
        self.gap_threshold_logged = False
        self.range_threshold_logged = False
        
        # Phase 3: Reset Reference-style persistent condition states
        self.c1 = False
        self.c2 = False
        self.c3 = False
        self.c4 = False
        self.c5 = False
        
        # Reset last execution dates to current time
        current_time = self.algorithm.Time
        self.last_execution_date_c1 = current_time
        self.last_execution_date_c2 = current_time
        self.last_execution_date_c3 = current_time
        self.last_execution_date_c4 = current_time
        self.last_execution_date_c5 = current_time
        
        # ACTION TIME: Reset trade time actions for new day
        self.reset_trade_time_actions()
        
        # Legacy compatibility - reset condition states
        for condition in self.condition_states:
            self.condition_states[condition] = False
    
    def LogTrailingOrderPrices(self):
        """Log current stop prices and update trailing entry orders - called every 15 seconds"""
        if not self.pending_orders:
            return
            
        current_time = self.algorithm.Time
        # Get current price from securities
        symbol = self.algorithm.symbols.get(self.symbol_name)
        if symbol:
            current_price = self.algorithm.Securities[symbol].Price
        else:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - TRAILING UPDATE WARNING - Unable to get symbol for {self.symbol_name}")
            return
        
        # Create a copy of the items to avoid "dictionary changed size during iteration" error
        for condition, order_info in list(self.pending_orders.items()):
            if order_info.get('ticket') and order_info.get('type') == 'long_entry_trail':
                ticket = order_info['ticket']
                try:
                    # Get current order stop price
                    if hasattr(ticket, 'Get'):
                        current_stop_price = ticket.Get(OrderField.StopPrice)
                        current_limit_price = ticket.Get(OrderField.LimitPrice) if hasattr(ticket, 'LimitPrice') else 'N/A'
                        trailing_pct = order_info.get('trailing_pct', 'Unknown')
                        old_market_price = order_info.get('current_market_price', current_price)
                        
                        # Calculate new entry price based on trailing logic
                        new_entry_price = current_price * (1 + trailing_pct / 100)
                        
                        # Update entry price if market moved UP (trailing up for breakout strategy)
                        if current_price > old_market_price:
                            # Update the order with new entry price
                            try:
                                # Cancel old order and place new one with updated price
                                self.algorithm.Transactions.CancelOrder(ticket.OrderId)
                                
                                # Create new order with updated entry price
                                new_ticket = self.algorithm.StopMarketOrder(
                                    symbol,
                                    order_info['size'],
                                    new_entry_price,
                                    tag=f"Trail-Update-{condition}-{symbol.Value}"
                                )
                                
                                # Update order info
                                order_info['ticket'] = new_ticket
                                order_info['entry_price'] = new_entry_price
                                order_info['current_market_price'] = current_price
                                order_info['last_update_time'] = current_time
                                
                                if self.algorithm.enable_logging:
                                    self.algorithm.Log(f"TRAILING UPDATE - {current_time}: {condition} OrderID={new_ticket.OrderId}, NEW Entry Price={new_entry_price:.2f}, Market Price={current_price:.2f}, Old Entry={current_stop_price:.2f}, Trailing %={trailing_pct:.3f}%")
                                
                            except Exception as update_error:
                                if self.algorithm.enable_logging:
                                    self.algorithm.Log(f"{self.algorithm.Time} - TRAILING UPDATE ERROR - Failed to update order: {update_error}")
                        else:
                            # No update needed - just log current status - DISABLED for performance (high-frequency)
                            if self.algorithm.enable_logging:
                                # self.algorithm.Log(f"TRAILING UPDATE - {current_time}: {condition} OrderID={ticket.OrderId}, Entry Price={current_stop_price:.2f}, Market Price={current_price:.2f}, No Update Needed, Trailing %={trailing_pct:.3f}%")
                                pass
                        
                        # Update current market price for next check
                        order_info['current_market_price'] = current_price
                            
                    else:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"TRAILING UPDATE - {current_time}: {condition} OrderID={ticket.OrderId if ticket else 'None'} - Unable to get current prices")
                except Exception as e:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"TRAILING UPDATE ERROR - {current_time}: {condition} - {e}")
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Daily state reset for {self.symbol_name}")
    
    def UpdateConditionState(self, condition, state):
        """Update condition state - legacy compatibility"""
        
        if condition in self.condition_states:
            self.condition_states[condition] = state
            
        # Phase 3: Also update Reference-style persistent states
        if condition == 'cond1':
            self.c1 = state
        elif condition == 'cond2':
            self.c2 = state
        elif condition == 'cond3':
            self.c3 = state
        elif condition == 'cond4':
            self.c4 = state
        elif condition == 'cond5':
            self.c5 = state
    
    def GetConditionState(self, condition):
        """Get condition state - legacy compatibility"""
        
        # Phase 3: Get from Reference-style persistent states
        if condition == 'cond1':
            return self.c1
        elif condition == 'cond2':
            return self.c2
        elif condition == 'cond3':
            return self.c3
        elif condition == 'cond4':
            return self.c4
        elif condition == 'cond5':
            return self.c5
        
        return self.condition_states.get(condition, False)
    
    def set_condition_state(self, condition, state):
        """Set persistent condition state (Reference-style - replaces strategy.c1 = True)"""
        if condition == 'c1':
            self.c1 = state
        elif condition == 'c2':
            self.c2 = state
        elif condition == 'c3':
            self.c3 = state
        elif condition == 'c4':
            self.c4 = state
        elif condition == 'c5':
            self.c5 = state
        
        # Update legacy compatibility
        condition_key = f'cond{condition[1:]}' if condition.startswith('c') else condition
        if condition_key in self.condition_states:
            self.condition_states[condition_key] = state
            
    def get_condition_state(self, condition):
        """Get persistent condition state (Reference-style - replaces strategy.c1)"""
        if condition == 'c1':
            return self.c1
        elif condition == 'c2':
            return self.c2
        elif condition == 'c3':
            return self.c3
        elif condition == 'c4':
            return self.c4
        elif condition == 'c5':
            return self.c5
        return False
        
    def reset_condition_state(self, condition):
        """Reset condition state when rally/VWAP fails (Reference-style)"""
        self.set_condition_state(condition, False)
        
    def update_last_execution_date(self, condition):
        """Update last execution date for timing constraints (Reference-style)"""
        current_time = self.algorithm.Time
        if condition == 'c1':
            self.last_execution_date_c1 = current_time
        elif condition == 'c2':
            self.last_execution_date_c2 = current_time
        elif condition == 'c3':
            self.last_execution_date_c3 = current_time
        elif condition == 'c4':
            self.last_execution_date_c4 = current_time
        elif condition == 'c5':
            self.last_execution_date_c5 = current_time
            
    def get_last_execution_date(self, condition):
        """Get last execution date for timing constraints (Reference-style)"""
        if condition == 'c1':
            return self.last_execution_date_c1
        elif condition == 'c2':
            return self.last_execution_date_c2
        elif condition == 'c3':
            return self.last_execution_date_c3
        elif condition == 'c4':
            return self.last_execution_date_c4
        elif condition == 'c5':
            return self.last_execution_date_c5
        return self.algorithm.Time
    
    def AddPendingOrder(self, condition, order_info):
        """Add pending order"""
        
        self.pending_orders[condition] = order_info
    
    def RemovePendingOrder(self, condition):
        """Remove pending order"""
        
        if condition in self.pending_orders:
            del self.pending_orders[condition]
    
    def GetPendingOrder(self, condition):
        """Get pending order"""
        
        return self.pending_orders.get(condition, None)
    
    def UpdatePosition(self, symbol, quantity):
        """Update position tracking"""
        
        if symbol not in self.active_positions:
            self.active_positions[symbol] = 0
        
        self.active_positions[symbol] += quantity
    
    def GetPosition(self, symbol):
        """Get position quantity"""
        
        return self.active_positions.get(symbol, 0)
    
    def trade_time_action(self, last_price):
        """
        Execute time-based actions on trades (Reference: ib.py lines 197-254)
        Action1: Move TP/SL to breakeven after Action1_Time minutes
        Action2: Cancel all orders and close positions after Action2_Time minutes
        """
        # Skip if actions are disabled
        if not self.cfg.Allow_Actions:
            return
            
        # Skip if no trade start time
        if self.trade_start_time is None:
            return
            
        current_time = self.algorithm.Time
        
        # Only update every 10 seconds to avoid excessive processing
        if (current_time - self.last_update_trade_start_time).total_seconds() <= 10:
            return
            
        diff_minutes = (current_time - self.trade_start_time).total_seconds() / 60.0
        self.last_update_trade_start_time = current_time
        
        # Action 1: Move TP/SL to breakeven
        if not self.trade_start_time_actionx and self.cfg.Action1_Time <= diff_minutes:
            self.trade_start_time_actionx = True
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1 TRIGGERED for {self.symbol_name} after {diff_minutes:.1f} minutes")
            
            # Get current position
            symbol = self.algorithm.symbols.get(self.symbol_name)
            if symbol and symbol in self.algorithm.Portfolio:
                position = self.algorithm.Portfolio[symbol]
                if position.Quantity != 0:
                    avg_cost = position.AveragePrice
                    
                    # Check if position is in profit or loss
                    if (last_price < avg_cost and position.Quantity > 0) or (last_price > avg_cost and position.Quantity < 0):
                        # In loss - move TP to breakeven
                        self._adjust_tp_to_breakeven(symbol, avg_cost)
                    else:
                        # In profit - move SL to breakeven
                        self._adjust_sl_to_breakeven(symbol, avg_cost)
                        
        # Action 2: Cancel all orders and close positions
        if not self.trade_start_time_actiony and self.cfg.Action2_Time <= diff_minutes:
            self.trade_start_time_actiony = True
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 2 TRIGGERED for {self.symbol_name} after {diff_minutes:.1f} minutes")
            
            # Cancel all pending orders
            self._cancel_all_orders()
            
            # Close position if any
            self._close_position()
            
    def _adjust_tp_to_breakeven(self, symbol, breakeven_price):
        """Adjust take profit orders to breakeven price"""
        for order in self.algorithm.Transactions.GetOpenOrders(symbol):
            # Check if this is a TP order
            if "-TP" in order.Tag or "TP-" in order.Tag:
                try:
                    # Get the order ticket
                    ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
                    if ticket:
                        update_fields = UpdateOrderFields()
                        update_fields.LimitPrice = round(breakeven_price, 2)
                        response = ticket.Update(update_fields)
                        if response.IsSuccess:
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1: Updated TP order {order.Id} to breakeven {breakeven_price}")
                        else:
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1: Failed to update TP order {order.Id}: {response.ErrorMessage}")
                    else:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1 ERROR: Could not get ticket for order {order.Id}")
                except Exception as e:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1 ERROR: Failed to update TP order: {e}")
                    
    def _adjust_sl_to_breakeven(self, symbol, breakeven_price):
        """Adjust stop loss orders to breakeven price"""
        for order in self.algorithm.Transactions.GetOpenOrders(symbol):
            # Check if this is a SL order
            if "-SL" in order.Tag or "SL-" in order.Tag:
                try:
                    # Get the order ticket
                    ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
                    if ticket:
                        update_fields = UpdateOrderFields()
                        update_fields.StopPrice = round(breakeven_price, 2)
                        response = ticket.Update(update_fields)
                        if response.IsSuccess:
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1: Updated SL order {order.Id} to breakeven {breakeven_price}")
                        else:
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1: Failed to update SL order {order.Id}: {response.ErrorMessage}")
                    else:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1 ERROR: Could not get ticket for order {order.Id}")
                except Exception as e:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - ACTION 1 ERROR: Failed to update SL order: {e}")
                    
    def _cancel_all_orders(self):
        """Cancel all open orders for this symbol"""
        symbol = self.algorithm.symbols.get(self.symbol_name)
        if symbol:
            for order in self.algorithm.Transactions.GetOpenOrders(symbol):
                if "eod" not in order.Tag:  # Don't cancel if already marked as EOD
                    self.algorithm.Transactions.CancelOrder(order.Id)
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - ACTION 2: Cancelled order {order.Id} ({order.Tag})")
                    
    def _close_position(self):
        """Close any open position for this symbol"""
        symbol = self.algorithm.symbols.get(self.symbol_name)
        if symbol and symbol in self.algorithm.Portfolio:
            position = self.algorithm.Portfolio[symbol]
            if position.Quantity != 0:
                # Create market order to close position
                order_tag = f"eod-action2-{self.symbol_name}"
                if position.Quantity > 0:
                    self.algorithm.MarketOrder(symbol, -position.Quantity, tag=order_tag)
                else:
                    self.algorithm.MarketOrder(symbol, -position.Quantity, tag=order_tag)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - ACTION 2: Closing position {position.Quantity} shares at market")
    
    def set_trade_start_time(self):
        """Set the trade start time when a new position is opened"""
        if self.trade_start_time is None:
            self.trade_start_time = self.algorithm.Time
            self.trade_start_time_actionx = False
            self.trade_start_time_actiony = False
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Trade start time set for {self.symbol_name} at {self.trade_start_time}")
            
    def reset_trade_time_actions(self):
        """Reset trade time action states"""
        self.trade_start_time = None
        self.trade_start_time_actionx = False
        self.trade_start_time_actiony = False
    
    def set_algo(self, enabled):
        """
        DEPRECATED - Now using trading_enabled flag for all threshold checks
        Enable or disable algorithm trading (Reference implementation)
        Matches Reference set_algo() method from ib.py line 1010
        """
        # No longer used - all thresholds now use trading_enabled
        pass
    
    def check_gap_threshold(self, metrics_calculator):
        """
        Check if gap exceeds threshold and disable trading if needed
        Reference implementation: if abs(metric_1d_gap) > metric_range_price30DMA * gap_threshold / 100
        """
        try:
            # Get the calculated metrics
            metric_1d_gap = metrics_calculator.metric_1d_gap
            metric_range_price30DMA = metrics_calculator.metric_range_price30DMA
            
            # Get gap threshold parameter
            gap_threshold = self.algorithm.parameters.Gap_Threshold
            
            # Log gap check details once daily
            current_time = self.algorithm.Time
            if not hasattr(self, 'last_gap_log_date') or self.last_gap_log_date != current_time.date():
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"GAP CHECK - {self.symbol_name}: Gap={metric_1d_gap:.2f}%, 30DMA={metric_range_price30DMA:.2f}%, Threshold={gap_threshold}")
                self.last_gap_log_date = current_time.date()
            
            # Reference check: abs(metric_1d_gap) > metric_range_price30DMA * gap_threshold / 100.0
            if metric_range_price30DMA is not None and metric_range_price30DMA > 0:
                threshold_value = metric_range_price30DMA * gap_threshold / 100.0
                
                if abs(metric_1d_gap) > threshold_value:
                    # Disable trading (Reference: self.set_algo(False))
                    self.trading_enabled = False
                    # Only log once per day
                    if not self.gap_threshold_logged:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"🚫 GAP THRESHOLD EXCEEDED - {self.symbol_name}: |Gap {metric_1d_gap:.2f}%| > {threshold_value:.2f}% (30DMA={metric_range_price30DMA:.2f}% * {gap_threshold}/100) - Trading DISABLED")
                        self.gap_threshold_logged = True
                else:
                    # Keep trading enabled
                    if not self.trading_enabled and self.gap_threshold_logged:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"✅ GAP THRESHOLD OK - {self.symbol_name}: |Gap {metric_1d_gap:.2f}%| <= {threshold_value:.2f}% - Trading remains enabled")
                        self.gap_threshold_logged = False
                    self.trading_enabled = True
            else:
                # If we don't have 30DMA data, keep trading enabled
                self.trading_enabled = True
                
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Error in gap threshold check: {e}")
            # On error, keep trading enabled
            self.trading_enabled = True
    
    def check_sharp_movement_threshold(self, metrics_calculator):
        """
        Check if sharp movement exceeds threshold and disable trading if needed
        Reference implementation: if (change_percentage/metric_range_price30DMA) > (sharpmovement_threshold/100.0)
        """
        try:
            # Check if the sharp movement threshold was exceeded in metrics
            metrics = metrics_calculator.GetAllMetrics()
            
            if metrics.get('sharp_movement_threshold_exceeded', False):
                # Disable trading (Reference: self.set_algo(False))
                self.trading_enabled = False
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Sharp movement threshold exceeded for {self.symbol_name} - Trading DISABLED")
            # Note: We don't re-enable trading here because once disabled, it stays disabled for the day
            # (matches Reference behavior where set_algo(False) disables until manually re-enabled)
                
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Error in sharp movement threshold check: {e}")
            # On error, don't change trading state
    
    def check_range_and_liquidity_threshold(self, metrics_calculator):
        """
        Check range multiple and liquidity thresholds using daily data only
        Similar to gap threshold - disables trading for the day if exceeded
        """
        try:
            # Only check once at market open (similar to gap threshold)
            current_time = self.algorithm.Time
            market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            
            # Check within first minute of market open
            if current_time < market_open or current_time > market_open + timedelta(minutes=1):
                return
                
            # Get yesterday's values from daily data
            metric_range_multiplier = metrics_calculator.metric_range_multiplier
            metric_liquidity = metrics_calculator.metric_liquidity
            
            # Get threshold parameters
            rangemultiple_threshold = self.cfg.RangeMultipleThreshold
            liquidity_threshold = self.cfg.Liquidity_Threshold
            
            # Check range multiple threshold
            if metric_range_multiplier > rangemultiple_threshold:
                self.trading_enabled = False
                if not self.range_threshold_logged:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Range Multiple threshold exceeded for {self.symbol_name}: {metric_range_multiplier:.2f} > {rangemultiple_threshold} - Trading DISABLED for the day")
                    self.range_threshold_logged = True
                return  # No need to check liquidity if range already disabled trading
            
            # Check liquidity threshold (using millions)
            if metric_liquidity / 1e6 < liquidity_threshold:
                self.trading_enabled = False
                if not self.range_threshold_logged:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Liquidity below threshold for {self.symbol_name}: {metric_liquidity/1e6:.2f}M < {liquidity_threshold}M - Trading DISABLED for the day")
                    self.range_threshold_logged = True
                    
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Error in range/liquidity threshold check: {e}")
            # On error, don't change trading state
        
    def __str__(self):
        """String representation"""
        return f"BasicStrategy({self.account_id}, {self.symbol_name}, orders={len(self.pending_orders)}, positions={len(self.active_positions)})"