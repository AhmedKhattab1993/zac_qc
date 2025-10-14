# order_manager.py - Risk-Safe Order Management (Phase 2.5)
from AlgorithmImports import *

class OrderManager:
    """
    Coordinate entry and exit order lifecycles for the reference strategy.

    The manager encapsulates phase 1 risk controls, phase 2 trailing entry
    mechanics, and the phase 2.5 safety patches that delay SL/TP creation
    until fills confirm. It also enforces hard constraints to avoid duplicate
    orders.

    Parameters
    ----------
    algorithm : Algorithm
        Parent QCAlgorithm wrapped by the symbol manager.
    """
    
    def __init__(self, algorithm):
        """
        Initialise state containers used for order tracking.

        Parameters
        ----------
        algorithm : Algorithm
            Parent QCAlgorithm wrapped by the symbol manager.
        """
        self.algorithm = algorithm
        self.params = algorithm.parameters
        self.data_manager = algorithm.data_manager
        
        # Basic position tracking
        self.active_positions = {}
        self.pending_orders = {}
        
        # Phase 1: Stop Loss Management System
        self.stop_loss_orders = {}  # Track stop loss orders by condition
        self.profit_take_orders = {}  # Track profit take orders by condition
        
        # Phase 2.5: Enhanced order tracking for entry->SL/TP linking
        self.entry_to_sltp_mapping = {}  # Maps entry order IDs to their SL/TP orders
        
        # HARD CONSTRAINT: Track orders sent in current cycle but not yet reflected by system
        self.orders_sent_this_cycle = set()  # Track symbols with orders sent this cycle
        self.order_sent_flags = {}  # Track specific order details by symbol
        
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("OrderManager initialized with HARD CONSTRAINT system, Phase 2.5 critical risk fixes, Phase 2 trailing entry orders and Phase 1 risk management systems")
    
    def ExecuteLongEntry(self, strategy, condition, current_price, metrics):
        """
        Submit a long trailing entry order when prerequisites are satisfied.

        Parameters
        ----------
        strategy : Strategy
            Strategy issuing the order.
        condition : str
            Condition identifier (``"cond1"``-``"cond3"``).
        current_price : float
            Latest traded price.
        metrics : dict
            Metrics snapshot used for validation.

        Returns
        -------
        bool
            True when the order was submitted.
        """
        
        # Phase 3: VWAP validation before order placement
        if not self.validate_vwap_conditions("LONG"):
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"VWAP validation failed for {self.algorithm.symbol.Value} condition {condition} LONG")
            return
        
        # Check if we already have pending orders or open positions for this symbol
        if self.HasPendingOrdersOrPositions(strategy):
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Cannot place new {condition} order - existing pending orders or open positions for {self.algorithm.symbol.Value}")
            return
        
        # Basic position size calculation
        position_size = self.CalculateBasicPositionSize(current_price)
        
        if position_size <= 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"No cash available for {condition} entry")
            return
        
        # Phase 2.5 FIX: Calculate trailing percentage matching Reference/ib.py logic
        # Reference uses dollar amounts based on nominal_range, we need to convert to percentage
        
        # Get nominal_range (daily high - daily low) from data manager
        nominal_range = self.data_manager.daily_high - self.data_manager.daily_low
        
        if nominal_range <= 0:
            # Fallback to a reasonable percentage if no range available yet
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Warning: nominal_range is {nominal_range}, using 1% of price as fallback")
            nominal_range = current_price * 0.01
        
        if condition in ['cond1', 'cond2']:
            # Reference: trailingAmount = round((param4 / 100) * nominal_range, 2)
            # For LONG conditions 1,2: trails based on nominal range
            trailing_dollar_amount = (self.params.Parameter_4 / 100) * nominal_range
            # Convert to percentage for QuantConnect
            trailing_percentage = (trailing_dollar_amount / current_price) * 100
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{condition}: nominal_range={nominal_range:.2f}, trailing_dollar={trailing_dollar_amount:.2f}, trailing_pct={trailing_percentage:.3f}%")
            
        elif condition == 'cond3':
            # Reference: trailingAmount = round((param5 / 100) * price, 2)
            # For LONG condition 3: trails based on current price
            trailing_dollar_amount = (self.params.Parameter_5 / 100) * current_price
            # Convert to percentage (should equal Parameter_5)
            trailing_percentage = self.params.Parameter_5
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{condition}: price-based trailing, trailing_dollar={trailing_dollar_amount:.2f}, trailing_pct={trailing_percentage:.3f}%")
            
        elif condition in ['cond4', 'cond5']:
            # Reference uses Parameter_4 for short conditions too
            # Reference: trailingAmount = round((param4 / 100) * nominal_range, 2)
            trailing_dollar_amount = (self.params.Parameter_4 / 100) * nominal_range
            # Convert to percentage for QuantConnect
            trailing_percentage = (trailing_dollar_amount / current_price) * 100
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{condition}: nominal_range={nominal_range:.2f}, trailing_dollar={trailing_dollar_amount:.2f}, trailing_pct={trailing_percentage:.3f}%")
            
        else:
            # Fallback to Parameter_4 logic for any other conditions
            trailing_dollar_amount = (self.params.Parameter_4 / 100) * nominal_range
            trailing_percentage = (trailing_dollar_amount / current_price) * 100
        
        # Create order tag for trailing entry
        order_tag = f"Buy-{condition}-Trail-{self.algorithm.symbol.Value}"
        
        # Always execute orders automatically (removed automatic buy check)
        # Store order info BEFORE placing order for immediate execution tracking
        strategy.pending_orders[condition] = {
            'ticket': None,  # Will be updated after order placement
            'entry_price': current_price * (1 + trailing_percentage / 100),
            'current_market_price': current_price,  # Track current market for trailing updates
            'original_entry_price': current_price * (1 + trailing_percentage / 100),
            'size': position_size,
            'condition': condition,
            'type': 'long_entry_trail',
            'trailing_pct': trailing_percentage,
            'last_update_time': self.algorithm.Time
        }
        
        # Use StopMarketOrder for LONG entry breakout strategy
        # Calculate entry price above current market price for breakout
        entry_price = current_price * (1 + trailing_percentage / 100)
        
        # Pre-trade P&L validation
        if hasattr(self.algorithm, 'risk_manager') and hasattr(self.algorithm.risk_manager, 'CanPlaceOrder'):
            if not self.algorithm.risk_manager.CanPlaceOrder(self.algorithm.symbol, position_size, current_price):
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"LONG {condition} order blocked - daily P&L limit reached")
                return None
        
        ticket = self.algorithm.StopMarketOrder(
            self.algorithm.symbol,
            position_size,           # POSITIVE quantity = BUY order
            entry_price,            # Stop price ABOVE current market for breakout
            tag=order_tag
        )
        
        # Enhanced order creation logging
        if ticket:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"=== ORDER CREATED === Time: {self.algorithm.Time}, Symbol: {self.algorithm.symbol.Value}, OrderID: {ticket.OrderId}, Type: LONG ENTRY, Condition: {condition}, Quantity: {position_size}, Entry Price: {entry_price:.2f}, Current Price: {current_price:.2f}, Trail %: {trailing_percentage:.3f}%, Tag: {order_tag}")
        
        # Update the ticket in the stored order info
        strategy.pending_orders[condition]['ticket'] = ticket
        
        # HARD CONSTRAINT: Mark this symbol as having an order sent this cycle
        self._set_order_sent_flag(condition, "LONG")
        
        # Phase 2.5: SL/TP orders will be created in OnOrderFilled after entry confirms
        # This prevents premature SL/TP creation before entry fills
        
        return True  # Order placed successfully
    
    def ExecuteShortEntry(self, strategy, condition, current_price, metrics):
        """
        Submit a short trailing entry order when prerequisites are satisfied.

        Parameters
        ----------
        strategy : Strategy
            Strategy issuing the order.
        condition : str
            Condition identifier (``"cond4"``-``"cond5"``).
        current_price : float
            Latest traded price.
        metrics : dict
            Metrics snapshot used for validation.

        Returns
        -------
        bool
            True when the order was submitted.
        """
        
        # Phase 3: VWAP validation before order placement
        if not self.validate_vwap_conditions("SHORT"):
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"VWAP validation failed for {self.algorithm.symbol.Value} condition {condition} SHORT")
            return
        
        # Check if we already have pending orders or open positions for this symbol
        if self.HasPendingOrdersOrPositions(strategy):
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Cannot place new {condition} order - existing pending orders or open positions for {self.algorithm.symbol.Value}")
            return
        
        # Basic position size calculation
        position_size = self.CalculateBasicPositionSize(current_price)
        
        if position_size <= 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"No cash available for {condition} entry")
            return
        
        # Phase 2.5 FIX: Calculate trailing percentage matching Reference/ib.py logic
        # Reference uses dollar amounts based on nominal_range, we need to convert to percentage
        
        # Get nominal_range (daily high - daily low) from data manager
        nominal_range = self.data_manager.daily_high - self.data_manager.daily_low
        
        if nominal_range <= 0:
            # Fallback to a reasonable percentage if no range available yet
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Warning: nominal_range is {nominal_range}, using 1% of price as fallback")
            nominal_range = current_price * 0.01
        
        # For SHORT conditions, Reference always uses Parameter_4 with nominal_range
        # Reference: trailingAmount = round((param4 / 100) * nominal_range, 2)
        trailing_dollar_amount = (self.params.Parameter_4 / 100) * nominal_range
        # Convert to percentage for QuantConnect
        trailing_percentage = (trailing_dollar_amount / current_price) * 100
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{condition} SHORT: nominal_range={nominal_range:.2f}, trailing_dollar={trailing_dollar_amount:.2f}, trailing_pct={trailing_percentage:.3f}%")
        
        # Create order tag for trailing entry
        order_tag = f"Short-{condition}-Trail-{self.algorithm.symbol.Value}"
        
        # Always execute orders automatically (removed automatic sell check)
        # Store order info BEFORE placing order for immediate execution tracking
        strategy.pending_orders[condition] = {
            'ticket': None,  # Will be updated after order placement
            'entry_price': current_price * (1 - trailing_percentage / 100),
            'current_market_price': current_price,  # Track current market for trailing updates
            'original_entry_price': current_price * (1 - trailing_percentage / 100),
            'size': position_size,
            'condition': condition,
            'type': 'short_entry_trail',
            'trailing_pct': trailing_percentage,
            'last_update_time': self.algorithm.Time
        }
        
        # Use StopMarketOrder for SHORT entry breakout strategy
        # Calculate entry price below current market price for SHORT breakout
        entry_price = current_price * (1 - trailing_percentage / 100)
        
        # Pre-trade P&L validation
        if hasattr(self.algorithm, 'risk_manager') and hasattr(self.algorithm.risk_manager, 'CanPlaceOrder'):
            if not self.algorithm.risk_manager.CanPlaceOrder(self.algorithm.symbol, -position_size, current_price):
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"SHORT {condition} order blocked - daily P&L limit reached")
                return None
        
        ticket = self.algorithm.StopMarketOrder(
            self.algorithm.symbol,
            -position_size,          # NEGATIVE quantity = SELL order
            entry_price,            # Stop price BELOW current market for breakout
            tag=order_tag
        )
        
        # Enhanced order creation logging
        if ticket:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"=== ORDER CREATED === Time: {self.algorithm.Time}, Symbol: {self.algorithm.symbol.Value}, OrderID: {ticket.OrderId}, Type: SHORT ENTRY, Condition: {condition}, Quantity: {-position_size}, Entry Price: {entry_price:.2f}, Current Price: {current_price:.2f}, Trail %: {trailing_percentage:.3f}%, Tag: {order_tag}")
        
        # Update the ticket in the stored order info
        strategy.pending_orders[condition]['ticket'] = ticket
        
        # HARD CONSTRAINT: Mark this symbol as having an order sent this cycle
        self._set_order_sent_flag(condition, "SHORT")
        
        # Phase 2.5: SL/TP orders will be created in OnOrderFilled after entry confirms
        # This prevents premature SL/TP creation before entry fills
        
        return True  # Order placed successfully
    
    def CalculateBasicPositionSize(self, current_price):
        """Calculate basic position size - Exact Reference/ib.py behavior"""
        
        # Get net liquidation value (total portfolio value)
        net_liquidation = self.algorithm.Portfolio.TotalPortfolioValue
        
        # Calculate cash to use based on cash_pct (Reference: line 528)
        # Reference: cash = self.cash_pct * netLiquidation / 100.0
        cash = self.params.cash_pct * net_liquidation / 100.0
        
        # Calculate cash used in existing positions
        cash_used = 0
        for symbol, quantity in self.algorithm.Portfolio.items():
            if quantity.Quantity != 0:
                # Reference uses avgCost, we use AveragePrice
                cash_used += abs(quantity.AveragePrice * abs(quantity.Quantity))
        
        # Calculate max cash allowed (Reference: line 529)
        # Reference: max_cash = self.cfg.maxCapitalPct * netLiquidation / 100.0
        max_cash = self.params.MaxCapitalPCT * net_liquidation / 100.0
        
        # Check if we can use the requested cash (Reference: lines 530-533)
        # Reference: if max_cash >= cash + cash_used: return cash else: return 0
        if max_cash >= cash + cash_used:
            available_cash = cash
        else:
            available_cash = 0
            
        # Calculate position size (Reference: line 544 for long, 645 for short)
        # Reference: self.size = int(cash / price)
        if available_cash > 0:
            position_size = int(available_cash / current_price)
        else:
            position_size = 0
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"Position sizing: NetLiq={net_liquidation:.2f}, cash_pct={self.params.cash_pct}%, cash={cash:.2f}, cash_used={cash_used:.2f}, max_cash={max_cash:.2f}, available={available_cash:.2f}, size={position_size}")
        
        return max(0, position_size)
    
    def CalculateNominalRange(self):
        """Calculate nominal range (exact Reference replication)"""
        
        # Exact Reference calculation: nominal_range = symbol.daily_high - symbol.daily_low
        daily_high = self.data_manager.daily_high
        daily_low = self.data_manager.daily_low
        
        nominal_range = daily_high - daily_low
        
        # Ensure we have a valid range
        if nominal_range <= 0:
            # Fallback: use current price as a percentage-based range
            current_price = self.data_manager.bars_15s[0].Close if self.data_manager.bars_15s.Count > 0 else 100
            nominal_range = current_price * 0.01  # 1% fallback
        
        return nominal_range
    
    def HasPendingOrdersOrPositions(self, strategy):
        """
        HARD CONSTRAINT: Check if we have any pending orders, open positions, 
        or orders sent this cycle for this symbol
        """
        symbol_name = self.algorithm.symbol.Value
        
        # HARD CONSTRAINT 1: Check if order was sent this cycle but not yet reflected
        if symbol_name in self.orders_sent_this_cycle:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"HARD CONSTRAINT: Order already sent this cycle for {symbol_name}")
            return True
        
        # HARD CONSTRAINT 2: Check pending orders in strategy
        if len(strategy.pending_orders) > 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"HARD CONSTRAINT: Pending orders exist for {symbol_name} - {list(strategy.pending_orders.keys())}")
            return True
        
        # HARD CONSTRAINT 3: Check open positions (local tracking)
        if self.algorithm.symbol in self.active_positions:
            position_size = self.active_positions[self.algorithm.symbol]
            if position_size != 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"HARD CONSTRAINT: Open position exists for {symbol_name} - Local: {position_size}")
                return True
        
        # HARD CONSTRAINT 4: Check algorithm portfolio for any open positions
        portfolio_quantity = self.algorithm.Portfolio[self.algorithm.symbol].Quantity
        if portfolio_quantity != 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"HARD CONSTRAINT: Open position exists for {symbol_name} - Portfolio: {portfolio_quantity}")
            return True
        
        # HARD CONSTRAINT 5: Check for any pending orders in the algorithm
        open_orders = self.algorithm.Transactions.GetOpenOrders(self.algorithm.symbol)
        if len(open_orders) > 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"HARD CONSTRAINT: Open orders exist for {symbol_name} - Count: {len(open_orders)}")
            return True
        
        return False
    
    def OnOrderEvent(self, orderEvent, strategies=None):
        """
        Handle order events with simplified SL/TP cancellation logic.
        When any order fills and results in position = 0, cancel all open orders.
        This ensures clean exit without complex order tracking.
        """
        
        if orderEvent.Status == OrderStatus.Filled:
            self.OnOrderFilled(orderEvent, strategies)
            
            # SIMPLIFIED LOGIC: Check if position is now 0 and cancel all open orders
            portfolio_position = self.algorithm.Portfolio[orderEvent.Symbol].Quantity
            if portfolio_position == 0:
                # Get order details for enhanced logging
                order_ticket = self.algorithm.Transactions.GetOrderTicket(orderEvent.OrderId)
                order_tag = order_ticket.Tag if order_ticket else "Unknown"
                
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"=== POSITION CLOSED === Symbol: {orderEvent.Symbol}, Final Position: 0")
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"  Closing Order: ID={orderEvent.OrderId}, Tag={order_tag}, Quantity={orderEvent.FillQuantity}, Price={orderEvent.FillPrice}")
                
                # Get count of open orders before cancellation
                open_orders = self.algorithm.Transactions.GetOpenOrders(orderEvent.Symbol)
                open_order_count = len(open_orders)
                
                if open_order_count > 0:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"  Found {open_order_count} open orders to cancel:")
                    for order in open_orders:
                        order_ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
                        order_tag = order_ticket.Tag if order_ticket else "Unknown"
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"    - OrderID: {order.Id}, Tag: {order_tag}, Quantity: {order.Quantity}")
                
                # Cancel all open orders
                self._cancel_all_orders_for_symbol("Position closed to 0")
                
                # Update timing if this was a SL or TP fill
                if "SL-" in order_tag or "TP-" in order_tag:
                    # Extract condition from tag
                    if "-" in order_tag:
                        parts = order_tag.split("-")
                        if len(parts) >= 2:
                            condition = parts[1]
                            self._update_timing_on_exit(condition, "SL" if "SL-" in order_tag else "TP")
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"  Updated timing for condition {condition} after position exit")
            else:
                # Position is not 0, log this for clarity
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"  Position remains open: {portfolio_position} shares - no cancellation needed")
                
        elif orderEvent.Status == OrderStatus.Canceled:
            self.OnOrderCanceled(orderEvent, strategies)
    
    def OnOrderFilled(self, orderEvent, strategies=None):
        """
        Phase 2.5: Enhanced order fill handling with proper SL/TP creation sequence
        Creates SL/TP orders ONLY after entry orders fill, using actual fill prices
        """
        
        current_time = self.algorithm.Time
        order_id = orderEvent.OrderId
        fill_price = orderEvent.FillPrice
        fill_quantity = orderEvent.FillQuantity
        
        # Enhanced order fill logging with complete details
        order_ticket = self.algorithm.Transactions.GetOrderTicket(order_id)
        order_tag = order_ticket.Tag if order_ticket else "Unknown"
        order_type = "BUY" if fill_quantity > 0 else "SELL"
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"=== ORDER FILLED === Time: {current_time}, Symbol: {orderEvent.Symbol}, OrderID: {order_id}, Type: {order_type}, Quantity: {fill_quantity}, Price: {fill_price}, Tag: {order_tag}")
        
        # HARD CONSTRAINT: Clear the order sent flag when order fills
        self._clear_order_sent_flag("Order filled")
        
        # Update position tracking
        if orderEvent.Symbol not in self.active_positions:
            self.active_positions[orderEvent.Symbol] = 0
        
        old_position = self.active_positions[orderEvent.Symbol]
        self.active_positions[orderEvent.Symbol] += fill_quantity
        new_position = self.active_positions[orderEvent.Symbol]
        
        portfolio_position = self.algorithm.Portfolio[orderEvent.Symbol].Quantity
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"Position update at {current_time}: {orderEvent.Symbol} Local: {old_position} -> {new_position}, Portfolio: {portfolio_position}")
        
        # DEBUG: Check if strategies parameter is provided
        if strategies is None:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"DEBUG: OnOrderFilled called with strategies=None for order {order_id}")
        else:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"DEBUG: OnOrderFilled called with {len(strategies) if strategies else 0} strategies for order {order_id}")
        
        # Phase 2.5: Check if this is an entry order fill and create SL/TP
        entry_order_info = self._find_and_remove_entry_order(order_id, strategies)
        if entry_order_info:
            condition = entry_order_info['condition']
            order_type = entry_order_info['type']
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Entry order filled: {condition} {order_type} at {fill_price}")
            
            # Determine direction from order type
            if 'long_entry' in order_type:
                direction = "LONG"
            elif 'short_entry' in order_type:
                direction = "SHORT"
            else:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Unknown entry order type: {order_type}")
                return
            
            # ACTION TIME: Set trade start time when position is opened (Reference: ib.py trade_start_time)
            if strategies:
                for strategy in strategies:
                    if hasattr(strategy, 'set_trade_start_time'):
                        strategy.set_trade_start_time()
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"Trade start time set for {condition} entry at {current_time}")
            
            
            # Phase 2.5: Create SL/TP using ACTUAL fill price and quantity
            # Apply SharesToSell percentage as in Reference/ib.py
            sl_tp_size = int(abs(fill_quantity) * (self.params.SharesToSell / 100.0))
            sl_order = self.CreateStopLossOrder(fill_price, sl_tp_size, condition, direction)
            tp_order = self.CreateProfitTakeOrder(fill_price, sl_tp_size, condition, direction)
            
            # Phase 2.5: No need for complex linking - we'll cancel all orders when SL/TP fills
            if sl_order and tp_order:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Created SL/TP orders for {condition} {direction} using fill price {fill_price}")
        else:
            # CRITICAL FIX: If we can't find the entry order info, but we have a position increase,
            # assume this is an entry order and create SL/TP anyway
            if abs(fill_quantity) > 0 and abs(new_position) > abs(old_position):
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"DEBUG: Entry order not found in pending orders for OrderID {order_id}, but position increased. Creating SL/TP anyway.")
                
                # Default to condition cond2 (most common) and LONG direction for missing entry tracking
                # This ensures SL/TP are created even if entry order tracking fails
                condition = 'cond2'  # Default assumption for missing tracking
                direction = "LONG" if fill_quantity > 0 else "SHORT"
                
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"FALLBACK: Creating SL/TP for assumed {direction} entry at {fill_price} (OrderID: {order_id})")
                
                # ACTION TIME: Set trade start time for fallback entry as well
                if strategies:
                    for strategy in strategies:
                        if hasattr(strategy, 'set_trade_start_time'):
                            strategy.set_trade_start_time()
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"FALLBACK: Trade start time set for assumed {condition} entry at {current_time}")
                
                
                # Create SL/TP using fallback logic
                # Apply SharesToSell percentage as in Reference/ib.py
                sl_tp_size = int(abs(fill_quantity) * (self.params.SharesToSell / 100.0))
                sl_order = self.CreateStopLossOrder(fill_price, sl_tp_size, condition, direction)
                tp_order = self.CreateProfitTakeOrder(fill_price, sl_tp_size, condition, direction)
                
                # Phase 2.5: No need for complex linking - we'll cancel all orders when SL/TP fills
                if sl_order and tp_order:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"FALLBACK: Created SL/TP orders for {condition} {direction} using fill price {fill_price}")
        
        # Removed complex SL/TP cancellation - now handled in OnOrderEvent when position becomes 0
    
    
    def OnOrderCanceled(self, orderEvent, strategies=None):
        """Handle order cancellations"""
        # Enhanced order cancellation logging
        order_id = orderEvent.OrderId
        order_ticket = self.algorithm.Transactions.GetOrderTicket(order_id)
        order_tag = order_ticket.Tag if order_ticket else "Unknown"
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"=== ORDER CANCELED === Time: {self.algorithm.Time}, Symbol: {orderEvent.Symbol}, OrderID: {order_id}, Quantity: {orderEvent.Quantity}, Tag: {order_tag}")
        
        # HARD CONSTRAINT: Clear the order sent flag when order is cancelled
        self._clear_order_sent_flag("Order cancelled")
        
        # Clean up pending orders for this canceled order across all strategies
        order_id = orderEvent.OrderId
        
        if strategies:
            for strategy in strategies:
                orders_to_remove = []
                
                for condition, order_info in strategy.pending_orders.items():
                    if order_info.get('ticket') and order_info['ticket'].OrderId == order_id:
                        orders_to_remove.append(condition)
                
                for condition in orders_to_remove:
                    del strategy.pending_orders[condition]
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"Removed pending order for canceled condition: {condition}")
    
    def CloseAllPositions(self):
        """Close all positions at market close"""
        
        # Always use the algorithm portfolio as the source of truth
        portfolio_quantity = self.algorithm.Portfolio[self.algorithm.symbol].Quantity
        local_quantity = self.active_positions.get(self.algorithm.symbol, 0)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"EOD Check - Portfolio: {portfolio_quantity}, Local tracking: {local_quantity} for {self.algorithm.symbol}")
        
        if portfolio_quantity != 0:
            self.algorithm.MarketOrder(self.algorithm.symbol, -portfolio_quantity, tag="EOD-Close")
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Placed EOD close order: {self.algorithm.symbol} quantity {-portfolio_quantity}")
        else:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"No position to close for {self.algorithm.symbol}")
        
        # Cancel any pending orders for this symbol using our robust method
        self._cancel_all_orders_for_symbol("EOD cleanup")
        
        # Reset local tracking to match portfolio (should be 0 after close order fills)
        self.active_positions[self.algorithm.symbol] = 0
        
        # HARD CONSTRAINT: Clear all order sent flags at EOD
        self._clear_order_sent_flag("EOD cleanup")
        
        # Don't clear all pending orders here - let them be cleared when the strategy level clears them
    
    # =======================================================================
    # PHASE 1: STOP LOSS AND PROFIT TAKE MANAGEMENT SYSTEM
    # =======================================================================
    
    def CreateStopLossOrder(self, fill_price, size, condition, direction):
        """
        Create stop loss order based on Reference implementation
        Reference: lines 386-404 and 494-513 in ib.py
        """
        if not self.params.StopLossUpdate:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Stop loss updates disabled - skipping stop loss for {condition}")
            return None
            
        # Get metric_range_price30DMA from data manager
        try:
            metric_30dma = self.algorithm.metrics_calculator.metric_range_price30DMA
            if metric_30dma is None or metric_30dma <= 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Invalid metric_range_price30DMA: {metric_30dma} - skipping stop loss")
                return None
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error getting metric_range_price30DMA: {e}")
            return None
            
        # Calculate stop loss price using exact Reference formula
        # Reference: stop_loss = round(fill_price + fill_price * self.cfg.stoploss * (self.s.metric_range_price30DMA/100) / 100.0, 2)
        if direction == "LONG":
            # For long positions: stop below entry price
            stop_price = round(fill_price - fill_price * self.params.StopLoss * (metric_30dma/100) / 100.0, 2)
            order_quantity = -size  # Negative quantity = SELL to exit long position
            order_action = "SELL"
        else:  # SHORT
            # For short positions: stop above entry price  
            stop_price = round(fill_price + fill_price * self.params.StopLoss * (metric_30dma/100) / 100.0, 2)
            order_quantity = abs(size)   # Positive quantity = BUY to cover short position
            order_action = "BUY"
        
        # Create stop market order (QuantConnect equivalent of Reference StopOrder)
        try:
            # Create order with tag to match Reference implementation  
            tag = f"SL-{condition}-{self.algorithm.symbol.Value}-{fill_price}"
            stop_order = self.algorithm.StopMarketOrder(self.algorithm.symbol, order_quantity, stop_price, tag=tag)
            
            # Enhanced stop loss order creation logging
            if stop_order:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"=== ORDER CREATED === Time: {self.algorithm.Time}, Symbol: {self.algorithm.symbol.Value}, OrderID: {stop_order.OrderId}, Type: STOP LOSS, Condition: {condition}, Direction: {direction}, Quantity: {order_quantity}, Stop Price: {stop_price:.2f}, Fill Price: {fill_price:.2f}, Tag: {tag}")
            
            # Store stop loss order for tracking
            stop_key = f"{condition}_{direction}"
            self.stop_loss_orders[stop_key] = {
                'order': stop_order,
                'condition': condition,
                'direction': direction,
                'stop_price': stop_price,
                'size': abs(order_quantity)
            }
            return stop_order
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error creating stop loss order: {e}")
            return None
    
    def CreateProfitTakeOrder(self, fill_price, size, condition, direction):
        """
        Create profit take order based on Reference implementation
        Reference: lines 369-383 and 475-491 in ib.py
        """
        # Get condition-specific profit take percentage using existing helper
        try:
            profit_take_pct = self.params.get_condition_profit_take(condition)
            if profit_take_pct is None or profit_take_pct <= 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Invalid profit take percentage for {condition}: {profit_take_pct}")
                return None
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error getting profit take percentage: {e}")
            return None
            
        # Get metric_range_price30DMA from data manager
        try:
            metric_30dma = self.algorithm.metrics_calculator.metric_range_price30DMA
            if metric_30dma is None or metric_30dma <= 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Invalid metric_range_price30DMA: {metric_30dma} - skipping profit take")
                return None
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error getting metric_range_price30DMA: {e}")
            return None
            
        # Calculate profit take price using exact Reference formula
        # Reference: lmt_price = round(fill_price - fill_price * profit_take * (self.s.metric_range_price30DMA/100) / 100.0, 2)
        if direction == "LONG":
            # For long positions: profit above entry price
            profit_price = round(fill_price + fill_price * profit_take_pct * (metric_30dma/100) / 100.0, 2)
            order_quantity = -size  # Negative quantity = SELL to exit long position
            order_action = "SELL"
        else:  # SHORT
            # For short positions: profit below entry price
            profit_price = round(fill_price - fill_price * profit_take_pct * (metric_30dma/100) / 100.0, 2)
            order_quantity = abs(size)   # Positive quantity = BUY to cover short position
            order_action = "BUY"
        
        # Create limit order for profit take (QuantConnect equivalent of Reference LimitOrder)
        try:
            # Create order with tag to match Reference implementation
            tag = f"TP-{condition}-{self.algorithm.symbol.Value}-{fill_price}"
            profit_order = self.algorithm.LimitOrder(self.algorithm.symbol, order_quantity, profit_price, tag=tag)
            
            # Enhanced profit take order creation logging
            if profit_order:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"=== ORDER CREATED === Time: {self.algorithm.Time}, Symbol: {self.algorithm.symbol.Value}, OrderID: {profit_order.OrderId}, Type: PROFIT TAKE, Condition: {condition}, Direction: {direction}, Quantity: {order_quantity}, Limit Price: {profit_price:.2f}, Fill Price: {fill_price:.2f}, Tag: {tag}")
            
            # Store profit take order for tracking
            profit_key = f"{condition}_{direction}"
            self.profit_take_orders[profit_key] = {
                'order': profit_order,
                'condition': condition,
                'direction': direction,
                'profit_price': profit_price,
                'size': abs(order_quantity)
            }
            return profit_order
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error creating profit take order: {e}")
            return None
    
    # =======================================================================
    # PHASE 2.5: ENHANCED ORDER TRACKING AND MUTUAL CANCELLATION SYSTEM
    # =======================================================================
    
    def _find_and_remove_entry_order(self, order_id, strategies):
        """
        Phase 2.5: Find and remove entry order from pending orders
        Returns order info if found, None otherwise
        """
        if not strategies:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"DEBUG: _find_and_remove_entry_order called with no strategies for order {order_id}")
            return None
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"DEBUG: Searching for entry order {order_id} across {len(strategies)} strategies")
        
        for i, strategy in enumerate(strategies):
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"DEBUG: Strategy {i} has {len(strategy.pending_orders) if hasattr(strategy, 'pending_orders') else 0} pending orders")
            
            if not hasattr(strategy, 'pending_orders'):
                continue
                
            orders_to_remove = []
            order_info = None
            
            # DEBUG: Log all pending orders for this strategy
            for condition, pending_order_info in strategy.pending_orders.items():
                ticket = pending_order_info.get('ticket')
                order_type = pending_order_info.get('type', 'unknown')
                ticket_id = ticket.OrderId if ticket and hasattr(ticket, 'OrderId') else 'None'
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"DEBUG: Pending order - Condition: {condition}, Type: {order_type}, OrderID: {ticket_id}")
                
                if (pending_order_info.get('ticket') and 
                    pending_order_info['ticket'].OrderId == order_id and
                    'entry' in pending_order_info.get('type', '')):
                    
                    order_info = pending_order_info.copy()
                    orders_to_remove.append(condition)
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"DEBUG: FOUND matching entry order for {condition} with OrderID {order_id}")
            
            # Remove the found entry order(s)
            for condition in orders_to_remove:
                del strategy.pending_orders[condition]
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Removed entry order for condition: {condition}")
            
            if order_info:
                return order_info
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"DEBUG: No entry order found for OrderID {order_id}")
        return None
    
    
    def _cancel_order_safely(self, order, reason):
        """
        Phase 2.5: Safely cancel an order with error handling
        """
        try:
            if order and hasattr(order, 'OrderId'):
                # Get order details for enhanced logging
                order_ticket = self.algorithm.Transactions.GetOrderTicket(order.OrderId)
                order_tag = order_ticket.Tag if order_ticket else "Unknown"
                
                self.algorithm.Transactions.CancelOrder(order.OrderId)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"=== ORDER CANCEL REQUEST === Time: {self.algorithm.Time}, Symbol: {self.algorithm.symbol.Value}, OrderID: {order.OrderId}, Reason: {reason}, Tag: {order_tag}")
            else:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Cannot cancel {reason} - invalid order object")
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error cancelling {reason} order: {e}")
    
    def _update_timing_on_exit(self, condition, exit_type):
        """
        Update timing constraints when a position exits (SL or TP fill)
        This is when the cooldown period should start
        """
        try:
            # Access the symbol manager through the algorithm's symbol managers
            symbol_managers = getattr(self.algorithm, 'symbol_managers', {})
            symbol_name = self.algorithm.symbol.Value
            
            if symbol_name in symbol_managers:
                symbol_manager = symbol_managers[symbol_name]
                symbol_manager.UpdateExecutionTime(condition)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"TIMING UPDATE: Cooldown started for {condition} after {exit_type} exit at {self.algorithm.Time}")
                
                # Update strategy timing as well (conditions checker uses strategy timing)
                for strategy in symbol_manager.strategies:
                    # Update the strategy's last execution date for this condition
                    if hasattr(strategy, 'update_last_execution_date'):
                        # Convert condition format if needed (e.g., "cond1" -> "c1")
                        strategy_condition = condition.replace("cond", "c") if condition.startswith("cond") else condition
                        strategy.update_last_execution_date(strategy_condition)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"TIMING UPDATE: Strategy timing updated for {strategy_condition}")
                    
                    # ACTION TIME: Reset trade time actions when position exits
                    if hasattr(strategy, 'reset_trade_time_actions'):
                        strategy.reset_trade_time_actions()
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"ACTION TIME: Trade time actions reset for {symbol_name} after {exit_type}")
            else:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Warning: Could not find symbol manager for {symbol_name} to update timing")
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error updating timing on exit: {e}")
    
    # =======================================================================
    # HARD CONSTRAINT SYSTEM: Prevent multiple orders per symbol per cycle
    # =======================================================================
    
    def _set_order_sent_flag(self, condition, direction):
        """Set flag that an order was sent this cycle for this symbol"""
        symbol_name = self.algorithm.symbol.Value
        current_time = self.algorithm.Time
        
        self.orders_sent_this_cycle.add(symbol_name)
        self.order_sent_flags[symbol_name] = {
            'condition': condition,
            'direction': direction,
            'time': current_time,
            'cycle': current_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"HARD CONSTRAINT: Flag set for {symbol_name} - {condition} {direction} at {current_time}")
    
    def _cancel_all_orders_for_symbol(self, reason=""):
        """
        Robustly cancel all open orders for the current symbol
        Uses CancelOpenOrders with manual fallback for reliability
        """
        symbol = self.algorithm.symbol
        symbol_name = symbol.Value
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"=== CANCELLING ALL ORDERS === Symbol: {symbol_name}, Reason: {reason}")
        
        # First, use the recommended CancelOpenOrders method
        self.algorithm.Transactions.CancelOpenOrders(symbol)
        
        # Then verify and handle any remaining orders
        remaining_orders = self.algorithm.Transactions.GetOpenOrders(symbol)
        if len(remaining_orders) > 0:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"WARNING: {len(remaining_orders)} orders still open after CancelOpenOrders for {symbol_name}")
            
            # Manual fallback cancellation
            cancelled_manually = 0
            for order in remaining_orders:
                try:
                    self.algorithm.Transactions.CancelOrder(order.Id)
                    cancelled_manually += 1
                    
                    # Log details of manually cancelled order
                    order_ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
                    order_tag = order_ticket.Tag if order_ticket else "Unknown"
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"  Manually cancelled OrderID: {order.Id}, Tag: {order_tag}")
                except Exception as e:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"  ERROR cancelling OrderID {order.Id}: {e}")
            
            if cancelled_manually > 0:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"  Manually cancelled {cancelled_manually} remaining orders")
        else:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"  SUCCESS: All orders cancelled for {symbol_name}")
        
        return True
    
    def _clear_order_sent_flag(self, reason="Order processed"):
        """Clear the order sent flag for this symbol"""
        symbol_name = self.algorithm.symbol.Value
        
        if symbol_name in self.orders_sent_this_cycle:
            self.orders_sent_this_cycle.remove(symbol_name)
            if symbol_name in self.order_sent_flags:
                flag_info = self.order_sent_flags.pop(symbol_name)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"HARD CONSTRAINT: Flag cleared for {symbol_name} - {reason} - Was: {flag_info['condition']} {flag_info['direction']}")
    
    def LogOrderSummary(self):
        """Log comprehensive order summary for tracking and debugging"""
        symbol = self.algorithm.symbol.Value
        
        # Get all open orders
        open_orders = self.algorithm.Transactions.GetOpenOrders(self.algorithm.symbol)
        
        # Get portfolio position
        portfolio_position = self.algorithm.Portfolio[self.algorithm.symbol].Quantity
        local_position = self.active_positions.get(self.algorithm.symbol, 0)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"=== ORDER SUMMARY === Time: {self.algorithm.Time}, Symbol: {symbol}")
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"  Position: Portfolio={portfolio_position}, Local={local_position}")
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"  Open Orders: {len(open_orders)} total")
        
        for order in open_orders:
            order_ticket = self.algorithm.Transactions.GetOrderTicket(order.Id)
            order_tag = order_ticket.Tag if order_ticket else "Unknown"
            order_type = "BUY" if order.Quantity > 0 else "SELL"
            
            # Determine order details based on order type
            if hasattr(order, 'StopPrice') and order.StopPrice > 0:
                price_info = f"Stop={order.StopPrice}"
            elif hasattr(order, 'LimitPrice') and order.LimitPrice > 0:
                price_info = f"Limit={order.LimitPrice}"
            else:
                price_info = "Market"
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"    OrderID: {order.Id}, Type: {order_type}, Qty: {order.Quantity}, {price_info}, Tag: {order_tag}")
        
        # Log SL/TP tracking
        if self.stop_loss_orders:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"  Tracked SL Orders: {list(self.stop_loss_orders.keys())}")
        if self.profit_take_orders:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"  Tracked TP Orders: {list(self.profit_take_orders.keys())}")
    
    def _clear_all_flags_for_symbol(self, symbol_name, reason="Symbol cleanup"):
        """Clear all flags for a specific symbol"""
        if symbol_name in self.orders_sent_this_cycle:
            self.orders_sent_this_cycle.remove(symbol_name)
        if symbol_name in self.order_sent_flags:
            flag_info = self.order_sent_flags.pop(symbol_name)
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"HARD CONSTRAINT: All flags cleared for {symbol_name} - {reason}")
    
    def validate_vwap_conditions(self, direction):
        """Phase 3: Validate VWAP conditions before order placement (Reference implementation)
        USES HARD THRESHOLD (no margin) matching Reference/ib.py lines 1262-1263, 1280-1281
        """
        try:
            # Get VWAP data from metrics calculator
            vwap_price = self.algorithm.metrics_calculator.metric_vwap_price
            range_price_7dma = self.algorithm.metrics_calculator.metric_range_price7DMA
            
            if vwap_price is None or range_price_7dma is None:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"VWAP validation - No data available (VWAP: {vwap_price}, Range7DMA: {range_price_7dma})")
                return True  # Allow if no VWAP data available
                
            # Calculate VWAP threshold - HARD threshold for order placement
            vwap_pct = self.params.VWAP_PCT
            
            # Reference: vwap_condition12 = self.metric_vwap_price < 0 and abs(self.metric_vwap_price) >= (
            #     self.cfg.vwap_pct * self.metric_range_price7DMA/100.0)
            hard_vwap_threshold = (vwap_pct * range_price_7dma / 100.0)
            
            result = False
            if direction == "SHORT":
                # For short orders: vwap_price > 0 and abs(vwap_price) >= threshold
                sign_ok = vwap_price > 0
                magnitude_ok = abs(vwap_price) >= hard_vwap_threshold
                result = sign_ok and magnitude_ok
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"VWAP VALIDATION {direction} (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_vwap_threshold:.4f}, Sign>0: {sign_ok}, Magnitude: {magnitude_ok}, Result: {result}")
            else:  # BUY/LONG
                # For buy orders: vwap_price < 0 and abs(vwap_price) >= threshold  
                sign_ok = vwap_price < 0
                magnitude_ok = abs(vwap_price) >= hard_vwap_threshold
                result = sign_ok and magnitude_ok
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"VWAP VALIDATION {direction} (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_vwap_threshold:.4f}, Sign<0: {sign_ok}, Magnitude: {magnitude_ok}, Result: {result}")
                
            return result
                
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"VWAP validation error: {e}")
            return True  # Default to allowing if error
    
    def update_stop_loss(self):
        """
        Dynamic stop loss update implementation (Reference/ib.py lines 1034-1110)
        Updates stop loss orders based on profit thresholds defined by StopLossX/Y parameters
        """
        if not self.params.StopLossUpdate:
            return
            
        # Check all open stop loss orders
        for sl_key, sl_info in list(self.stop_loss_orders.items()):
            try:
                sl_order = sl_info.get('order')
                if not sl_order or not hasattr(sl_order, 'OrderId'):
                    continue
                    
                # Check if order is still open
                order_status = self.algorithm.Transactions.GetOrderById(sl_order.OrderId)
                if not order_status or order_status.Status in [OrderStatus.Filled, OrderStatus.Canceled]:
                    continue
                    
                condition = sl_info.get('condition', 'cond1')
                direction = sl_info.get('direction', 'LONG')
                
                # Get current position and average price
                portfolio_item = self.algorithm.Portfolio[self.algorithm.symbol]
                if portfolio_item.Quantity == 0:
                    continue
                    
                avg_price = portfolio_item.AveragePrice
                current_price = self.algorithm.Securities[self.algorithm.symbol].Price
                
                # Get stop loss X/Y parameters for this condition
                stop_loss_x, stop_loss_y = self.params.get_stop_loss_parameters(condition)
                
                # Get profit take percentage for scaling
                profit_take_pct = self.params.get_condition_profit_take(condition)
                
                # Get metric_range_price30DMA for scaling
                metric_30dma = getattr(self.algorithm.metrics_calculator, 'metric_range_price30DMA', 0)
                if metric_30dma <= 0:
                    continue
                
                # Calculate scaled stop loss parameters (Reference formula)
                # Reference: stop_loss_x = self.cfg.stopLossXC1 * (self.cfg.profittakeC1/100) * (self.metric_range_price30DMA/100)
                stop_loss_x_scaled = stop_loss_x * (profit_take_pct/100) * (metric_30dma/100)
                stop_loss_y_scaled = stop_loss_y * (profit_take_pct/100) * (metric_30dma/100)
                
                # Calculate profit percentage
                if direction == "LONG" and condition in ['cond1', 'cond2', 'cond3']:
                    # For long positions, use high price
                    pr_inc = (current_price - avg_price) * 100.0 / avg_price
                    
                    # Check if profit threshold reached
                    if pr_inc >= stop_loss_y_scaled:
                        # Calculate new stop price (move stop loss up)
                        new_stop_price = round((1 + stop_loss_x_scaled/100) * avg_price, 2)
                        current_stop_price = sl_order.Get(OrderField.StopPrice) if hasattr(sl_order, 'Get') else sl_info.get('stop_price', 0)
                        
                        # Only update if new stop price is different
                        if round(current_stop_price, 2) != new_stop_price:
                            # Cancel old order and create new one
                            self.algorithm.Transactions.CancelOrder(sl_order.OrderId)
                            
                            # Create new stop loss order with updated price
                            tag = f"SL-{condition}-{self.algorithm.symbol.Value}-Updated"
                            new_sl_order = self.algorithm.StopMarketOrder(
                                self.algorithm.symbol, 
                                -sl_info['size'],  # Negative for sell
                                new_stop_price, 
                                tag=tag
                            )
                            
                            # Update tracking
                            sl_info['order'] = new_sl_order
                            sl_info['stop_price'] = new_stop_price
                            
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"Stop Loss Updated: {condition} {direction} - Old: {current_stop_price:.2f}, New: {new_stop_price:.2f}, Profit: {pr_inc:.2f}%, Threshold: {stop_loss_y_scaled:.2f}%")
                            
                elif direction == "SHORT" and condition in ['cond4', 'cond5']:
                    # For short positions, use low price
                    pr_inc = (avg_price - current_price) * 100.0 / avg_price
                    
                    # Check if profit threshold reached (for shorts, it's negative)
                    if pr_inc >= stop_loss_y_scaled:
                        # Calculate new stop price (move stop loss down)
                        new_stop_price = round((1 - stop_loss_x_scaled/100) * avg_price, 2)
                        current_stop_price = sl_order.Get(OrderField.StopPrice) if hasattr(sl_order, 'Get') else sl_info.get('stop_price', 0)
                        
                        # Only update if new stop price is different
                        if round(current_stop_price, 2) != new_stop_price:
                            # Cancel old order and create new one
                            self.algorithm.Transactions.CancelOrder(sl_order.OrderId)
                            
                            # Create new stop loss order with updated price
                            tag = f"SL-{condition}-{self.algorithm.symbol.Value}-Updated"
                            new_sl_order = self.algorithm.StopMarketOrder(
                                self.algorithm.symbol,
                                sl_info['size'],  # Positive for buy to cover
                                new_stop_price,
                                tag=tag
                            )
                            
                            # Update tracking
                            sl_info['order'] = new_sl_order
                            sl_info['stop_price'] = new_stop_price
                            
                            if self.algorithm.enable_logging:
                                self.algorithm.Log(f"Stop Loss Updated: {condition} {direction} - Old: {current_stop_price:.2f}, New: {new_stop_price:.2f}, Profit: {pr_inc:.2f}%, Threshold: {stop_loss_y_scaled:.2f}%")
                            
            except Exception as e:
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"Error updating stop loss for {sl_key}: {e}")
    
    def monitor_vwap_conditions(self):
        """Phase 3: Monitor and cancel orders that no longer meet VWAP conditions (Reference implementation)
        USES SOFT THRESHOLD (with margin) matching Reference/ib.py vwap_reset() lines 171, 181
        """
        try:
            # Monitor pending orders
            symbol = self.algorithm.symbol
            open_orders = self.algorithm.Transactions.GetOpenOrders(symbol)
            
            if not open_orders:
                return  # No orders to monitor
                
            # Get current VWAP metrics
            vwap_price = getattr(self.algorithm.metrics_calculator, 'metric_vwap_price', None)
            range_price_7dma = getattr(self.algorithm.metrics_calculator, 'metric_range_price7DMA', None)
            
            if vwap_price is None or range_price_7dma is None:
                return  # No VWAP data to monitor
                
            vwap_pct = self.params.VWAP_PCT
            vwap_margin = self.params.Vwap_Margin
            
            # Calculate both thresholds for logging
            hard_vwap_threshold = (vwap_pct * range_price_7dma / 100.0)
            soft_vwap_threshold = hard_vwap_threshold - (vwap_margin * range_price_7dma / 100.0)
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"VWAP MONITOR - VWAP Price: {vwap_price:.4f}, Hard Threshold: {hard_vwap_threshold:.4f}, Soft Threshold: {soft_vwap_threshold:.4f}")
            
            for order in open_orders:
                order_tag = getattr(order, 'Tag', '')
                
                # Skip non-entry orders (SL/TP)
                if "SL-" in order_tag or "TP-" in order_tag:
                    continue
                    
                # Check SHORT orders
                if "Short" in order_tag or order.Quantity < 0:
                    # Reference: soft_vwap_condition = vwap_price > 0 and abs(vwap_price) >= 
                    #            ((self.cfg.vwap_pct * range_price_7dma/100.0) - (self.cfg.vwap_margin * range_price_7dma/100.0))
                    soft_vwap_valid = vwap_price > 0 and abs(vwap_price) >= soft_vwap_threshold
                    
                    if not soft_vwap_valid:
                        self.algorithm.Transactions.CancelOrder(order.Id)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"🚫 VWAP CANCELLATION - SHORT order {order.Id} cancelled - SOFT threshold failed (VWAP: {vwap_price:.4f} < Soft: {soft_vwap_threshold:.4f})")
                        # Reset condition state like Reference does
                        # Note: Access strategies through proper path
                        if "cond4" in order_tag:
                            if hasattr(self.algorithm, 'strategies'):
                                for strategy in self.algorithm.strategies:
                                    strategy.reset_condition_state('c4')
                        elif "cond5" in order_tag:
                            if hasattr(self.algorithm, 'strategies'):
                                for strategy in self.algorithm.strategies:
                                    strategy.reset_condition_state('c5')
                    else:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"✅ VWAP CHECK - SHORT order {order.Id} still valid (VWAP: {vwap_price:.4f} >= Soft: {soft_vwap_threshold:.4f})")
                
                # Check BUY/LONG orders
                elif "Buy" in order_tag or order.Quantity > 0:
                    # Reference: soft_vwap_condition = vwap_price < 0 and abs(vwap_price) >= 
                    #            ((self.cfg.vwap_pct * range_price_7dma/100.0) - (self.cfg.vwap_margin * range_price_7dma/100.0))
                    soft_vwap_valid = vwap_price < 0 and abs(vwap_price) >= soft_vwap_threshold
                    
                    if not soft_vwap_valid:
                        self.algorithm.Transactions.CancelOrder(order.Id)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"🚫 VWAP CANCELLATION - LONG order {order.Id} cancelled - SOFT threshold failed (VWAP: {vwap_price:.4f} < Soft: {soft_vwap_threshold:.4f})")
                        # Reset condition state like Reference does
                        # Note: Access strategies through proper path
                        if "cond1" in order_tag:
                            if hasattr(self.algorithm, 'strategies'):
                                for strategy in self.algorithm.strategies:
                                    strategy.reset_condition_state('c1')
                        elif "cond2" in order_tag:
                            if hasattr(self.algorithm, 'strategies'):
                                for strategy in self.algorithm.strategies:
                                    strategy.reset_condition_state('c2')
                    else:
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"✅ VWAP CHECK - LONG order {order.Id} still valid (VWAP: {vwap_price:.4f} >= Soft: {soft_vwap_threshold:.4f})")
                        
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"VWAP monitoring error: {e}")
    
    def cancel_long_orders(self):
        """
        Cancel LONG entry orders based on price range breakout (Reference/ib.py lines 1347-1355)
        Cancels buy orders when the second-to-last 15-second bar's low is below 
        the minimum of all previous lows by more than New_Range_Order_Cancellation_Margin
        """
        try:
            # Get 15-second bars from data manager
            bars_15s = self.data_manager.bars_15s
            if bars_15s.Count < 3:  # Need at least 3 bars to check
                return
            
            # Convert bars to list for easier access
            bar_list = list(bars_15s)
            
            # Get the second-to-last bar's low
            second_last_low = bar_list[-2].Low
            
            # Get minimum of all previous bars except the last two
            previous_lows = [bar.Low for bar in bar_list[:-2]]
            if not previous_lows:
                return
                
            min_previous_low = min(previous_lows)
            
            # Check if difference exceeds margin
            price_diff = abs(second_last_low - min_previous_low)
            cancel_margin = self.params.New_Range_Order_Cancellation_Margin
            
            if price_diff > cancel_margin:
                # Cancel all pending LONG entry orders
                open_orders = self.algorithm.Transactions.GetOpenOrders(self.algorithm.symbol)
                
                for order in open_orders:
                    order_tag = getattr(order, 'Tag', '')
                    
                    # Only cancel BUY entry orders (not SL/TP)
                    if ("Buy" in order_tag or order.Quantity > 0) and "SL-" not in order_tag and "TP-" not in order_tag:
                        self.algorithm.Transactions.CancelOrder(order.Id)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"🚫 RANGE CANCELLATION - LONG order {order.Id} cancelled - Price broke below range by {price_diff:.2f} > {cancel_margin}")
                        
                        # Clear order sent flag
                        self._clear_order_sent_flag("Range cancellation - LONG")
                        
                        # Reset condition state
                        if "cond1" in order_tag:
                            self._reset_strategy_condition('c1')
                        elif "cond2" in order_tag:
                            self._reset_strategy_condition('c2')
                        elif "cond3" in order_tag:
                            self._reset_strategy_condition('c3')
                            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error in cancel_long_orders: {e}")
    
    def cancel_short_orders(self):
        """
        Cancel SHORT entry orders based on price range breakout (Reference/ib.py lines 1357-1365)
        Cancels short orders when the second-to-last 15-second bar's high is above
        the maximum of all previous highs by more than New_Range_Order_Cancellation_Margin
        """
        try:
            # Get 15-second bars from data manager
            bars_15s = self.data_manager.bars_15s
            if bars_15s.Count < 3:  # Need at least 3 bars to check
                return
            
            # Convert bars to list for easier access
            bar_list = list(bars_15s)
            
            # Get the second-to-last bar's high
            second_last_high = bar_list[-2].High
            
            # Get maximum of all previous bars except the last two
            previous_highs = [bar.High for bar in bar_list[:-2]]
            if not previous_highs:
                return
                
            max_previous_high = max(previous_highs)
            
            # Check if difference exceeds margin
            price_diff = abs(second_last_high - max_previous_high)
            cancel_margin = self.params.New_Range_Order_Cancellation_Margin
            
            if price_diff > cancel_margin:
                # Cancel all pending SHORT entry orders
                open_orders = self.algorithm.Transactions.GetOpenOrders(self.algorithm.symbol)
                
                for order in open_orders:
                    order_tag = getattr(order, 'Tag', '')
                    
                    # Only cancel SHORT entry orders (not SL/TP)
                    if ("Short" in order_tag or order.Quantity < 0) and "SL-" not in order_tag and "TP-" not in order_tag:
                        self.algorithm.Transactions.CancelOrder(order.Id)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"🚫 RANGE CANCELLATION - SHORT order {order.Id} cancelled - Price broke above range by {price_diff:.2f} > {cancel_margin}")
                        
                        # Clear order sent flag
                        self._clear_order_sent_flag("Range cancellation - SHORT")
                        
                        # Reset condition state
                        if "cond4" in order_tag:
                            self._reset_strategy_condition('c4')
                        elif "cond5" in order_tag:
                            self._reset_strategy_condition('c5')
                            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error in cancel_short_orders: {e}")
    
    def _reset_strategy_condition(self, condition_key):
        """Helper to reset strategy condition state"""
        try:
            # Access strategies through symbol managers
            symbol_managers = getattr(self.algorithm, 'symbol_managers', {})
            symbol_name = self.algorithm.symbol.Value
            
            if symbol_name in symbol_managers:
                symbol_manager = symbol_managers[symbol_name]
                for strategy in symbol_manager.strategies:
                    if hasattr(strategy, 'reset_condition_state'):
                        strategy.reset_condition_state(condition_key)
                        if self.algorithm.enable_logging:
                            self.algorithm.Log(f"Reset condition state for {condition_key}")
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Error resetting strategy condition: {e}")
    
    def monitor_range_based_cancellations(self):
        """
        Monitor and cancel orders based on range breakouts
        Called periodically to check if orders should be cancelled
        """
        # Check if we have any open orders to monitor
        open_orders = self.algorithm.Transactions.GetOpenOrders(self.algorithm.symbol)
        if not open_orders:
            return
        
        # Separate orders by type
        has_long_orders = any("Buy" in getattr(o, 'Tag', '') or o.Quantity > 0 
                             for o in open_orders 
                             if "SL-" not in getattr(o, 'Tag', '') and "TP-" not in getattr(o, 'Tag', ''))
        has_short_orders = any("Short" in getattr(o, 'Tag', '') or o.Quantity < 0 
                              for o in open_orders 
                              if "SL-" not in getattr(o, 'Tag', '') and "TP-" not in getattr(o, 'Tag', ''))
        
        # Only check cancellations for order types we have
        if has_long_orders:
            self.cancel_long_orders()
        if has_short_orders:
            self.cancel_short_orders()
    
    def __str__(self):
        """String representation"""
        return f"OrderManager(positions={len(self.active_positions)}, pending={len(self.pending_orders)}, stop_loss={len(self.stop_loss_orders)}, profit_take={len(self.profit_take_orders)})"
