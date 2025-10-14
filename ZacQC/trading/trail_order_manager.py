# trail_order_manager.py - LimitTrail Order Manager
from AlgorithmImports import *
from datetime import timedelta, time, datetime

class TrailOrderManager:
    """
    Emulate Interactive Brokers limit-trailing order behaviour.

    Parameters
    ----------
    algorithm : Algorithm
        Parent QCAlgorithm instance.
    """
    
    def __init__(self, algorithm):
        """
        Configure internal tracking structures for trail orders.

        Parameters
        ----------
        algorithm : Algorithm
            Parent QCAlgorithm instance.
        """
        self.algorithm = algorithm
        self.params = algorithm.parameters
        
        # Active trail orders tracking
        self.active_trail_orders = {}
        self.last_update_time = datetime.min
        
        # Set reference in order manager to resolve circular dependency
        # TODO: Add set_trail_order_manager method to OrderManager if needed
        # if hasattr(algorithm, 'order_manager'):
        #     algorithm.order_manager.set_trail_order_manager(self)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("TrailOrderManager initialized")
    
    def PlaceStopTrailOrder(self, symbol, action, quantity, trail_stop_price, trailing_amount, condition):
        """
        Submit a stop-trailing order following IB semantics.

        Parameters
        ----------
        symbol : Symbol
            Symbol to trade.
        action : str
            ``"BUY"`` or ``"SELL"`` action.
        quantity : int
            Order quantity in shares.
        trail_stop_price : float
            Initial trailing stop anchor.
        trailing_amount : float
            Trail amount expressed in price units.
        condition : str
            Triggering condition identifier.

        Returns
        -------
        OrderTicket
            Ticket for the newly submitted stop order.
        """
        
        # Place initial stop market order
        if action == "BUY":
            ticket = self.algorithm.StopMarketOrder(symbol, quantity, trail_stop_price)
        else:
            ticket = self.algorithm.StopMarketOrder(symbol, -quantity, trail_stop_price)
        
        # Store trail order parameters
        self.active_trail_orders[ticket.OrderId] = {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'trail_stop_price': trail_stop_price,
            'trailing_amount': trailing_amount,
            'condition': condition,
            'ticket': ticket,
            'best_price': None,  # Track best price for trailing
            'initial_price': self.algorithm.Securities[symbol].Price,
            'created_time': self.algorithm.Time,
            'last_update_time': self.algorithm.Time
        }
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"StopTrail order placed: {action} {quantity} {symbol} at stop {trail_stop_price:.2f}, trailing_amount {trailing_amount:.2f}")
        
        return ticket
    
    def UpdateAllTrailOrders(self):
        """
        Refresh all tracked trail orders if the throttle window has passed.

        Returns
        -------
        None
        """
        
        current_time = self.algorithm.Time
        
        # Throttle updates based on parameters (15 seconds as per IB)
        if (current_time - self.last_update_time).total_seconds() < 15:
            return
        
        self.last_update_time = current_time
        
        # Skip if market is closed
        if not self.algorithm.IsMarketOpen(self.algorithm.symbol):
            return
        
        orders_to_remove = []
        
        for order_id, order_info in self.active_trail_orders.items():
            ticket = order_info['ticket']
            
            # Remove if order is no longer active
            if ticket.Status in [OrderStatus.Filled, OrderStatus.Canceled, OrderStatus.Invalid]:
                orders_to_remove.append(order_id)
                continue
            
            # Update trail logic for active orders
            try:
                self.UpdateSingleTrailOrder(order_info)
            except Exception as e:
                self.algorithm.Error(f"Error updating trail order {order_id}: {e}")
                orders_to_remove.append(order_id)
        
        # Clean up completed orders
        for order_id in orders_to_remove:
            self.RemoveTrailOrder(order_id)
    
    def UpdateSingleTrailOrder(self, order_info):
        """
        Recalculate trail parameters for a single order.

        Parameters
        ----------
        order_info : dict
            Metadata dictionary stored when the trail was created.

        Returns
        -------
        None
        """
        
        symbol = order_info['symbol']
        current_price = self.algorithm.Securities[symbol].Price
        action = order_info['action']
        condition = order_info.get('condition', 'unknown')
        
        # Initialize best price tracking on first update
        if order_info['best_price'] is None:
            order_info['best_price'] = current_price
            return
        
        should_update = False
        new_trail_stop = order_info['trail_stop_price']
        
        # Calculate new trailing amount if price has moved favorably
        # This ensures trailing amount adjusts with current market conditions
        nominal_range = self.algorithm.data_manager.daily_high - self.algorithm.data_manager.daily_low
        if nominal_range <= 0:
            nominal_range = current_price * 0.01
        
        if action == "BUY":
            # For buy orders, trail down when price goes down
            if current_price < order_info['best_price']:
                order_info['best_price'] = current_price
                
                # Recalculate trailing amount based on current conditions
                if condition in ['cond1', 'cond2']:
                    new_trailing_amount = (self.params.param4 / 100.0) * nominal_range
                elif condition == 'cond3':
                    new_trailing_amount = (self.params.param5 / 100.0) * current_price
                else:
                    new_trailing_amount = order_info['trailing_amount']
                
                new_trail_stop = current_price + new_trailing_amount
                
                # Only update if new trail stop is lower (better for buying)
                if new_trail_stop < order_info['trail_stop_price']:
                    should_update = True
                    order_info['trailing_amount'] = new_trailing_amount
                    
        else:  # SELL
            # For sell orders, trail up when price goes up
            if current_price > order_info['best_price']:
                order_info['best_price'] = current_price
                
                # Recalculate trailing amount for conditions 4 & 5
                new_trailing_amount = (self.params.param4 / 100.0) * nominal_range
                new_trail_stop = current_price - new_trailing_amount
                
                # Only update if new trail stop is higher (better for selling)
                if new_trail_stop > order_info['trail_stop_price']:
                    should_update = True
                    order_info['trailing_amount'] = new_trailing_amount
        
        if should_update:
            # Update the stop order
            try:
                update_fields = UpdateOrderFields()
                update_fields.StopPrice = round(new_trail_stop, 2)
                order_info['ticket'].Update(update_fields)
                
                # Update tracking
                order_info['trail_stop_price'] = new_trail_stop
                order_info['last_update_time'] = self.algorithm.Time
                
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Trail order updated: {symbol} {action} new stop: {new_trail_stop:.2f}, trailing_amount: {order_info['trailing_amount']:.2f}")
                
            except Exception as e:
                self.algorithm.Error(f"Error updating trail order: {e}")
                # Remove problematic order
                self.RemoveTrailOrder(order_info['ticket'].OrderId)
    
    def RemoveTrailOrder(self, order_id):
        """
        Remove a trail order from the active tracking cache.

        Parameters
        ----------
        order_id : int
            Order identifier assigned by QuantConnect.

        Returns
        -------
        None
        """
        if order_id in self.active_trail_orders:
            order_info = self.active_trail_orders[order_id]
            self.algorithm.Debug(f"Removed trail order: {order_info['symbol']} {order_info['action']}")
            del self.active_trail_orders[order_id]
    
    def CancelAllTrailOrders(self, symbol=None):
        """
        Cancel outstanding trail orders.

        Parameters
        ----------
        symbol : Symbol, optional
            Restrict cancellation to a single symbol.

        Returns
        -------
        None
        """
        
        orders_to_cancel = []
        
        for order_id, order_info in self.active_trail_orders.items():
            if symbol is None or order_info['symbol'] == symbol:
                orders_to_cancel.append(order_id)
        
        for order_id in orders_to_cancel:
            order_info = self.active_trail_orders[order_id]
            try:
                order_info['ticket'].Cancel("Manual cancellation")
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Cancelled trail order: {order_info['symbol']} {order_info['action']}")
            except Exception as e:
                self.algorithm.Error(f"Error cancelling trail order {order_id}: {e}")
            
            self.RemoveTrailOrder(order_id)
    
    def GetTrailOrderStatus(self, order_id):
        """Get status of a specific trail order"""
        
        if order_id not in self.active_trail_orders:
            return None
        
        order_info = self.active_trail_orders[order_id]
        current_price = self.algorithm.Securities[order_info['symbol']].Price
        
        status = {
            'order_id': order_id,
            'symbol': str(order_info['symbol']),
            'action': order_info['action'],
            'quantity': order_info['quantity'],
            'current_price': current_price,
            'trail_stop_price': order_info['trail_stop_price'],
            'trailing_amount': order_info['trailing_amount'],
            'limit_offset_pct': order_info['limit_offset_pct'],
            'best_price': order_info['best_price'],
            'initial_price': order_info['initial_price'],
            'created_time': order_info['created_time'],
            'last_update_time': order_info['last_update_time'],
            'ticket_status': order_info['ticket'].Status,
            'current_limit_price': order_info['ticket'].Get(OrderField.LimitPrice) if hasattr(order_info['ticket'], 'Get') else 0
        }
        
        return status
    
    def GetAllTrailOrderStatuses(self):
        """Get status of all active trail orders"""
        
        statuses = []
        for order_id in self.active_trail_orders:
            status = self.GetTrailOrderStatus(order_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    def UpdateStrategyTrailPrices(self, strategy):
        """
        Update strategy-specific trail prices (cond12_price, cond3_price, cond45_price)
        Enables active trail order updates following IB methodology
        """
        
        current_price = self.algorithm.Securities[self.algorithm.symbol].Price
        
        # Update cond12_price (conditions 1 and 2) - trail down for better buy prices
        if strategy.cond12_price is not None and current_price < strategy.cond12_price:
            old_price = strategy.cond12_price
            strategy.cond12_price = current_price
            
            # Update active trail orders for entry conditions
            self.UpdateConditionTrailOrders(["cond1", "cond2"], current_price, "BUY")
            
            self.algorithm.Debug(f"Updated cond12_price: {old_price:.2f} -> {current_price:.2f}")
        
        # Update cond3_price (condition 3) - trail down for better buy prices
        if strategy.cond3_price is not None and current_price < strategy.cond3_price:
            old_price = strategy.cond3_price
            strategy.cond3_price = current_price
            
            # Update active trail orders for entry conditions
            self.UpdateConditionTrailOrders(["cond3"], current_price, "BUY")
            
            self.algorithm.Debug(f"Updated cond3_price: {old_price:.2f} -> {current_price:.2f}")
        
        # Update cond45_price (conditions 4 and 5) - trail up for better sell prices
        if strategy.cond45_price is not None and current_price > strategy.cond45_price:
            old_price = strategy.cond45_price
            strategy.cond45_price = current_price
            
            # Update active trail orders for entry conditions
            self.UpdateConditionTrailOrders(["cond4", "cond5"], current_price, "SELL")
            
            self.algorithm.Debug(f"Updated cond45_price: {old_price:.2f} -> {current_price:.2f}")
    
    def UpdateConditionTrailOrders(self, conditions, new_price, action):
        """Update trail orders for specific conditions based on new price"""
        
        for order_id, order_info in self.active_trail_orders.items():
            ticket = order_info['ticket']
            order_tag = ticket.Tag or ""
            
            # Check if this order matches any of the conditions
            condition_match = any(cond in order_tag for cond in conditions)
            action_match = order_info['action'] == action
            
            if condition_match and action_match:
                # Force update of this specific order
                try:
                    if action == "BUY":
                        # For buy orders, recalculate based on param4 or param5
                        if any(c in ["cond1", "cond2"] for c in conditions):
                            nominal_range = self.algorithm.data_manager.daily_high - self.algorithm.data_manager.daily_low  
                            new_trail_stop = new_price + (self.params.param4 / 100.0) * nominal_range
                            new_trailing_amount = (self.params.param4 / 100.0) * nominal_range
                        else:  # cond3
                            new_trail_stop = new_price + (self.params.param5 / 100.0) * new_price
                            new_trailing_amount = (self.params.param5 / 100.0) * new_price
                    else:  # SELL
                        # For sell orders (cond4, cond5)
                        nominal_range = self.algorithm.data_manager.daily_high - self.algorithm.data_manager.daily_low
                        new_trail_stop = new_price - (self.params.param4 / 100.0) * nominal_range
                        new_trailing_amount = (self.params.param4 / 100.0) * nominal_range
                    
                    # Update order parameters
                    order_info['trail_stop_price'] = new_trail_stop
                    order_info['trailing_amount'] = new_trailing_amount
                    
                    # Calculate and update limit price
                    if action == "BUY":
                        new_limit_price = max(0.01, new_trail_stop - (order_info['limit_offset_pct'] * new_trail_stop))
                    else:
                        new_limit_price = new_trail_stop + (order_info['limit_offset_pct'] * new_trail_stop)
                    
                    # Update the actual order
                    update_fields = UpdateOrderFields()
                    update_fields.StopPrice = round(new_trail_stop, 2)
                    ticket.Update(update_fields)
                    
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"Condition trail update: {order_tag} new limit: {new_limit_price:.2f}")
                    
                except Exception as e:
                    self.algorithm.Error(f"Error updating condition trail order {order_tag}: {e}")
    
    def GetTrailOrdersByCondition(self, condition):
        """Get all trail orders for a specific condition"""
        
        matching_orders = []
        
        for order_id, order_info in self.active_trail_orders.items():
            ticket = order_info['ticket']
            order_tag = ticket.Tag or ""
            
            if condition in order_tag:
                status = self.GetTrailOrderStatus(order_id)
                if status:
                    matching_orders.append(status)
        
        return matching_orders
    
    def GetTrailOrderStatistics(self):
        """Get statistics about trail orders"""
        
        total_orders = len(self.active_trail_orders)
        buy_orders = sum(1 for info in self.active_trail_orders.values() if info['action'] == 'BUY')
        sell_orders = sum(1 for info in self.active_trail_orders.values() if info['action'] == 'SELL')
        
        # Calculate average age
        current_time = self.algorithm.Time
        total_age_seconds = sum(
            (current_time - info['created_time']).total_seconds() 
            for info in self.active_trail_orders.values()
        )
        avg_age_minutes = (total_age_seconds / 60.0 / total_orders) if total_orders > 0 else 0
        
        # Count by condition
        condition_counts = {}
        for order_info in self.active_trail_orders.values():
            order_tag = order_info['ticket'].Tag or ""
            for cond in ["cond1", "cond2", "cond3", "cond4", "cond5"]:
                if cond in order_tag:
                    condition_counts[cond] = condition_counts.get(cond, 0) + 1
                    break
        
        stats = {
            'total_orders': total_orders,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'avg_age_minutes': avg_age_minutes,
            'condition_counts': condition_counts,
            'last_update_time': self.last_update_time
        }
        
        return stats
    
    def ValidateTrailOrders(self):
        """Validate all trail orders for consistency"""
        
        issues = []
        
        for order_id, order_info in self.active_trail_orders.items():
            try:
                ticket = order_info['ticket']
                symbol = order_info['symbol']
                current_price = self.algorithm.Securities[symbol].Price
                
                # Check if order is still valid
                if ticket.Status in [OrderStatus.Invalid, OrderStatus.Canceled]:
                    issues.append(f"Order {order_id} has invalid status: {ticket.Status}")
                    continue
                
                # Check if prices are reasonable
                if order_info['trail_stop_price'] <= 0:
                    issues.append(f"Order {order_id} has invalid trail stop price: {order_info['trail_stop_price']}")
                
                if order_info['trailing_amount'] <= 0:
                    issues.append(f"Order {order_id} has invalid trailing amount: {order_info['trailing_amount']}")
                
                # Check if limit price is reasonable relative to current price
                try:
                    current_limit = ticket.Get(OrderField.LimitPrice)
                    if order_info['action'] == 'BUY':
                        if current_limit > current_price * 1.1:  # Limit shouldn't be way above market
                            issues.append(f"Buy order {order_id} limit price {current_limit:.2f} too high vs market {current_price:.2f}")
                    else:  # SELL
                        if current_limit < current_price * 0.9:  # Limit shouldn't be way below market
                            issues.append(f"Sell order {order_id} limit price {current_limit:.2f} too low vs market {current_price:.2f}")
                except:
                    pass  # Ignore if we can't get limit price
                
            except Exception as e:
                issues.append(f"Error validating order {order_id}: {e}")
        
        return issues
    
    def __str__(self):
        """String representation"""
        return f"TrailOrderManager(active_orders={len(self.active_trail_orders)})"
