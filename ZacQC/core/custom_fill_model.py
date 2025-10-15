# custom_fill_model.py - Custom fill model for precise backtesting
from AlgorithmImports import *
from QuantConnect.Orders.Fills import FillModel
from QuantConnect.Data.Market import TradeBar

class PreciseFillModel(FillModel):
    """
    Custom fill model that fills orders at exact prices without bid-ask spread
    This ensures P&L limits are respected precisely in backtests
    """
    
    def __init__(self, algorithm=None):
        super().__init__()
        self.algorithm = algorithm
    
    def MarketFill(self, asset, order):
        """Fill market orders at the current price"""
        
        # Create order event
        fill = self._CreateOrderEvent(asset, order)
        
        if order.Status == OrderStatus.Canceled:
            return fill
        
        # Get current price - use Close price for precise fills
        price = asset.Price
        
        # Log the fill details for debugging P&L limit orders
        if self.algorithm and hasattr(order, 'Tag') and order.Tag == "targetprofit":
            # Also log the last update time and local time
            last_update = asset.Cache.LastUpdate if hasattr(asset.Cache, 'LastUpdate') else 'Unknown'
            local_time = asset.LocalTime
            self.algorithm.Log(f"CUSTOM FILL MODEL - Market order for {asset.Symbol}: Current Price={price:.4f}, Quantity={order.Quantity}, LocalTime={local_time}, LastUpdate={last_update}")
        
        # Fill at exact current price
        fill.Status = OrderStatus.Filled
        fill.FillQuantity = order.Quantity
        fill.FillPrice = price
        
        return fill
    
    def StopMarketFill(self, asset, order):
        """Fill stop market orders at exact stop price when triggered"""
        
        # Create order event
        fill = self._CreateOrderEvent(asset, order)
        
        if order.Status == OrderStatus.Canceled:
            return fill
        
        # Get stop price and current bar
        stop_price = order.StopPrice
        
        # Check if we have TradeBar data
        trade_bars = asset.Cache.GetData[TradeBar]()
        if trade_bars is None:
            # Use current price if no bar data
            current_price = asset.Price
            
            # Check if stop is triggered
            if order.Direction == OrderDirection.Sell and current_price <= stop_price:
                # SHORT entry or LONG exit - fill at stop price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = stop_price
            elif order.Direction == OrderDirection.Buy and current_price >= stop_price:
                # LONG entry or SHORT exit - fill at stop price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = stop_price
        else:
            # Use bar data for more accurate triggering
            bar = trade_bars[0] if isinstance(trade_bars, list) else trade_bars
            
            # Check if stop is triggered based on bar high/low
            if order.Direction == OrderDirection.Sell and bar.Low <= stop_price:
                # SHORT entry or LONG exit - fill at stop price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = stop_price
            elif order.Direction == OrderDirection.Buy and bar.High >= stop_price:
                # LONG entry or SHORT exit - fill at stop price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = stop_price
        
        return fill
    
    def LimitFill(self, asset, order):
        """Fill limit orders at exact limit price when touched"""
        
        # Create order event
        fill = self._CreateOrderEvent(asset, order)
        
        if order.Status == OrderStatus.Canceled:
            return fill
        
        # Get limit price and current bar
        limit_price = order.LimitPrice
        
        # Log the fill details for debugging P&L limit orders
        if self.algorithm and hasattr(order, 'Tag') and order.Tag == "targetprofit":
            self.algorithm.Log(f"CUSTOM FILL MODEL - Limit order for {asset.Symbol}: Limit Price={limit_price:.4f}, Current Price={asset.Price:.4f}, Quantity={order.Quantity}")
        
        # Check if we have TradeBar data
        trade_bars = asset.Cache.GetData[TradeBar]()
        if trade_bars is None:
            # Use current price if no bar data
            current_price = asset.Price
            
            # Check if limit is reached
            if order.Direction == OrderDirection.Sell and current_price >= limit_price:
                # Sell limit order - fill at limit price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = limit_price
            elif order.Direction == OrderDirection.Buy and current_price <= limit_price:
                # Buy limit order - fill at limit price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = limit_price
        else:
            # Use bar data for more accurate triggering
            bar = trade_bars[0] if isinstance(trade_bars, list) else trade_bars
            
            # Check if limit is reached based on bar high/low
            if order.Direction == OrderDirection.Sell and bar.High >= limit_price:
                # Sell limit order - fill at limit price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = limit_price
            elif order.Direction == OrderDirection.Buy and bar.Low <= limit_price:
                # Buy limit order - fill at limit price
                fill.Status = OrderStatus.Filled
                fill.FillQuantity = order.Quantity
                fill.FillPrice = limit_price
        
        return fill
    
    def MarketOnOpenFill(self, asset, order):
        """Fill market on open orders"""
        
        # Create order event
        fill = self._CreateOrderEvent(asset, order)
        
        if order.Status == OrderStatus.Canceled:
            return fill
        
        # Check if market just opened
        if asset.Exchange.DateTimeIsOpen(asset.LocalTime):
            # Fill at open price
            fill.Status = OrderStatus.Filled
            fill.FillQuantity = order.Quantity
            fill.FillPrice = asset.Open
        
        return fill
    
    def MarketOnCloseFill(self, asset, order):
        """Fill market on close orders"""
        
        # Create order event
        fill = self._CreateOrderEvent(asset, order)
        
        if order.Status == OrderStatus.Canceled:
            return fill
        
        # Fill at close price
        fill.Status = OrderStatus.Filled
        fill.FillQuantity = order.Quantity
        fill.FillPrice = asset.Close
        
        return fill
    
    def _CreateOrderEvent(self, asset, order):
        """Create an order event with proper UTC time"""
        
        utc_time = Extensions.ConvertToUtc(asset.LocalTime, asset.Exchange.TimeZone)
        # Use zero fees for backtesting precision
        return OrderEvent(order, utc_time, OrderFee.Zero)