from AlgorithmImports import *
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.parameters import TradingParameters
from core.strategy import Strategy
from core.symbol_manager import SymbolManager
from core.utils import TradingUtils
from core.custom_fill_model import PreciseFillModel
from data.data_manager import DataManager
from data.metrics_calculator import MetricsCalculator
from management.risk_manager import RiskManager
from trading.conditions_checker import ConditionsChecker
from trading.order_manager import OrderManager
from trading.trail_order_manager import TrailOrderManager

class ZacReferenceAlgorithm(QCAlgorithm):
    """
    Reference Implementation - Simplified Trading Algorithm
    Migrated from ZacQC enhanced system to pure Reference behavior
    Parameters reduced from 220 to 81 (77 Reference + 4 frontend)
    """
    
    def Initialize(self):
        """Initialize the trading algorithm"""
        
        try:
            # Enable/disable logging globally (set to False to reduce RAM consumption)
            self.enable_logging = False
            
            # Basic initialization
            if self.enable_logging:
                self.Log("=== ZAC REFERENCE ALGORITHM INITIALIZATION ===")
            
            # Load parameters
            self.parameters = TradingParameters()
            
            # Set algorithm basics - convert string dates to datetime objects
            start_date = datetime.strptime(self.parameters.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.parameters.end_date, "%Y-%m-%d")
            self.SetStartDate(start_date.year, start_date.month, start_date.day)
            self.SetEndDate(end_date.year, end_date.month, end_date.day)
            self.SetCash(self.parameters.starting_cash)
            
            # Initialize multiple symbols
            self.symbols = {}
            self.symbol_managers = {}
            
            # Initialize global management systems (shared across symbols)
            self.risk_manager = RiskManager(self)
            self.utils = TradingUtils(self)
            
            # Initialize each symbol with its own components
            for symbol_name in self.parameters.symbols:
                # Add symbol to algorithm
                equity = self.AddEquity(symbol_name, Resolution.Second)
                symbol = equity.Symbol
                self.symbols[symbol_name] = symbol
                
                # Set custom fill model for precise backtesting (no bid-ask spread)
                # This ensures P&L limits are respected exactly
                if not self.LiveMode:
                    equity.SetFillModel(PreciseFillModel(self))
                    if self.enable_logging:
                        self.Log(f"Added symbol {symbol} with precise fill model")
                else:
                    if self.enable_logging:
                        self.Log(f"Added symbol {symbol} with default fill model (live mode)")
                
                # Create symbol manager for this symbol
                symbol_manager = SymbolManager(self, symbol_name, symbol)
                symbol_manager.Initialize()
                self.symbol_managers[symbol_name] = symbol_manager
                
                if self.enable_logging:
                    self.Log(f"Initialized SymbolManager for {symbol_name}")
            
            # Store first symbol as primary (for backward compatibility)
            self.symbol = self.symbols[self.parameters.symbols[0]]
            
            # Schedule custom end-of-day liquidation at 15:59 (1 minute before market close)
            self.Schedule.On(
                self.DateRules.EveryDay(),
                self.TimeRules.At(15, 59),
                self.CustomEndOfDay
            )
            if self.enable_logging:
                self.Log("Scheduled custom end-of-day liquidation at 15:59")
            
            # Schedule entry order cancellation at Algo_Off_After time
            algo_off_hour = self.parameters.Algo_Off_After.hour
            algo_off_minute = self.parameters.Algo_Off_After.minute
            self.Schedule.On(
                self.DateRules.EveryDay(),
                self.TimeRules.At(algo_off_hour, algo_off_minute),
                self.CancelEntryOrdersAtAlgoOff
            )
            if self.enable_logging:
                self.Log(f"Scheduled entry order cancellation at {algo_off_hour:02d}:{algo_off_minute:02d} (Algo_Off_After)")
            
            if self.enable_logging:
                self.Log("=== ALGORITHM INITIALIZATION COMPLETE ===")
            
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in Initialize: {str(e)}")
            import traceback
            if self.enable_logging:
                self.Log(f"Traceback: {traceback.format_exc()}")
            raise
    
    def OnData(self, data):
        """Main data processing method - handles multiple symbols"""
        
        try:
            # Process data for each symbol that has data
            for symbol_name, symbol_manager in self.symbol_managers.items():
                symbol = self.symbols[symbol_name]
                
                # Skip if no data for this symbol
                if symbol not in data or data[symbol] is None:
                    continue
                
                # Process data for this symbol through its symbol manager
                symbol_manager.OnData(data)
            
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in OnData: {str(e)}")
            import traceback
            if self.enable_logging:
                self.Log(f"Traceback: {traceback.format_exc()}")
    
    def OnEndOfDay(self, symbol):
        """Built-in end of day processing - final cleanup after market close"""
        
        try:
            # Find which symbol this is and do final verification
            for symbol_name, tracked_symbol in self.symbols.items():
                if symbol == tracked_symbol:
                    symbol_manager = self.symbol_managers[symbol_name]
                    symbol_manager.OnMarketClose()  # Final verification only
                    
                    # Log daily summary
                    position = self.Portfolio[symbol].Quantity
                    unrealized_pnl = self.Portfolio[symbol].UnrealizedProfit
                    
                    if self.enable_logging:
                        self.Log(f"End of Day {symbol_name} - Position: {position}, Unrealized PnL: ${unrealized_pnl:.2f}")
                    break
            
            # Reset algorithm-level daily states after all symbols processed
            if hasattr(self, 'risk_manager') and hasattr(self.risk_manager, 'ResetDaily'):
                self.risk_manager.ResetDaily()
                
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in OnEndOfDay: {str(e)}")
    
    def OnOrderEvent(self, orderEvent):
        """Handle order events - handles multiple symbols"""
        
        try:
            # Find which symbol this order belongs to and route to appropriate symbol manager
            for symbol_name, tracked_symbol in self.symbols.items():
                if orderEvent.Symbol == tracked_symbol:
                    symbol_manager = self.symbol_managers[symbol_name]
                    symbol_manager.OnOrderEvent(orderEvent)
                    
                    # Only log meaningful order events (avoid logging zeros for non-fill events)
                    if orderEvent.Status == OrderStatus.Filled and orderEvent.FillQuantity != 0:
                        if self.enable_logging:
                            self.Log(f"Order filled at {self.Time}: {symbol_name} {orderEvent.FillQuantity} at {orderEvent.FillPrice}")
                    elif orderEvent.Status == OrderStatus.Canceled:
                        if self.enable_logging:
                            self.Log(f"Order canceled at {self.Time}: {symbol_name} Order {orderEvent.OrderId}")
                    elif orderEvent.Status == OrderStatus.Invalid:
                        if self.enable_logging:
                            self.Log(f"Order invalid at {self.Time}: {symbol_name} Order {orderEvent.OrderId} - {orderEvent.Message}")
                    # Skip logging for Submitted/New orders to reduce noise
                    break
                
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in OnOrderEvent: {str(e)}")
    
    def CustomEndOfDay(self):
        """Custom end-of-day liquidation called at 15:59"""
        
        try:
            if self.enable_logging:
                self.Log("=== CUSTOM END-OF-DAY LIQUIDATION STARTED (15:59) ===")
            
            # Liquidate all positions for each symbol
            for symbol_name, symbol_manager in self.symbol_managers.items():
                if self.enable_logging:
                    self.Log(f"Processing EOD liquidation for {symbol_name}")
                symbol_manager.CustomEndOfDay()
            
            # Log portfolio summary
            total_portfolio_value = self.Portfolio.TotalPortfolioValue
            total_cash = self.Portfolio.Cash
            if self.enable_logging:
                self.Log(f"EOD Portfolio Summary - Total Value: ${total_portfolio_value:.2f}, Cash: ${total_cash:.2f}")
            
            if self.enable_logging:
                self.Log("=== CUSTOM END-OF-DAY LIQUIDATION COMPLETE ===")
            
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in CustomEndOfDay: {str(e)}")
            import traceback
            if self.enable_logging:
                self.Log(f"Traceback: {traceback.format_exc()}")
    
    def CancelEntryOrdersAtAlgoOff(self):
        """Cancel only pending entry orders at Algo_Off_After time"""
        
        try:
            if self.enable_logging:
                self.Log(f"=== CANCELLING ENTRY ORDERS AT ALGO_OFF_AFTER ({self.Time}) ===")
            
            # Process each symbol
            for symbol_name, symbol_manager in self.symbol_managers.items():
                symbol = self.symbols[symbol_name]
                
                # Get all open orders for this symbol
                open_orders = self.Transactions.GetOpenOrders(symbol)
                
                if len(open_orders) == 0:
                    continue
                
                if self.enable_logging:
                    self.Log(f"Processing {symbol_name}: {len(open_orders)} open orders")
                
                # Debug: Log all order tags for visibility
                for order in open_orders:
                    order_ticket = self.Transactions.GetOrderTicket(order.Id)
                    order_tag = order_ticket.Tag if order_ticket else ""
                    if self.enable_logging:
                        self.Log(f"  Found order: OrderID={order.Id}, Tag='{order_tag}'")
                
                # Cancel only entry orders (identified by tag patterns)
                entry_cancelled_count = 0
                exit_preserved_count = 0
                
                for order in open_orders:
                    order_ticket = self.Transactions.GetOrderTicket(order.Id)
                    order_tag = order_ticket.Tag if order_ticket else ""
                    
                    # Identify entry orders by their tags
                    # Entry orders have tags like:
                    # - "Buy-cond1-Trail-AAPL" or "Short-cond4-Trail-AAPL" (initial orders)
                    # - "Trail-Update-cond1-AAPL" (updated trail orders)
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
                        self.Transactions.CancelOrder(order.Id)
                        entry_cancelled_count += 1
                        if self.enable_logging:
                            self.Log(f"  Cancelled ENTRY order: OrderID={order.Id}, Tag={order_tag}")
                        
                        # Clear the pending order from strategy tracking
                        # Extract condition from tag
                        condition = None
                        if order_tag.startswith("Trail-Update-"):
                            # Format: "Trail-Update-cond1-AAPL" -> "cond1"
                            parts = order_tag.split("-")
                            if len(parts) >= 3:
                                condition = parts[2]  # Extract "cond1" from "Trail-Update-cond1-AAPL"
                        elif "-Trail-" in order_tag:
                            # Format: "Buy-cond1-Trail-AAPL" -> "cond1"
                            parts = order_tag.split("-")
                            if len(parts) >= 2:
                                condition = parts[1]  # Extract "cond1" from "Buy-cond1-Trail-AAPL"
                        
                        if condition:
                                # Iterate through all strategies in the symbol manager
                                for strategy in symbol_manager.strategies:
                                    if hasattr(strategy, 'pending_orders') and condition in strategy.pending_orders:
                                        del strategy.pending_orders[condition]
                                        if self.enable_logging:
                                            self.Log(f"    Cleared pending order tracking for {condition}")
                                    
                                    # Reset the condition state to allow it to be triggered again later
                                    # This matches the behavior in VWAP monitoring cancellation
                                    if hasattr(strategy, 'reset_condition_state'):
                                        # Convert condition format (e.g., "cond1" -> "c1")
                                        condition_key = condition.replace("cond", "c")
                                        strategy.reset_condition_state(condition_key)
                                        if self.enable_logging:
                                            self.Log(f"    Reset condition state for {condition_key}")
                    else:
                        # Preserve exit orders (SL, TP, etc.)
                        exit_preserved_count += 1
                        order_type = "SL" if "SL-" in order_tag else ("TP" if "TP-" in order_tag else "EXIT")
                        if self.enable_logging:
                            self.Log(f"  Preserved {order_type} order: OrderID={order.Id}, Tag={order_tag}")
                
                if entry_cancelled_count > 0 or exit_preserved_count > 0:
                    if self.enable_logging:
                        self.Log(f"  {symbol_name} Summary: Cancelled {entry_cancelled_count} entry orders, Preserved {exit_preserved_count} exit orders")
            
            if self.enable_logging:
                self.Log("=== ENTRY ORDER CANCELLATION COMPLETE ===")
            
        except Exception as e:
            if self.enable_logging:
                self.Log(f"ERROR in CancelEntryOrdersAtAlgoOff: {str(e)}")
            import traceback
            if self.enable_logging:
                self.Log(f"Traceback: {traceback.format_exc()}")