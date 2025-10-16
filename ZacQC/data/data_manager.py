# data_manager.py - Data Management and Consolidation
from AlgorithmImports import *
from datetime import timedelta, time, datetime
from collections import deque

class DataManager:
    """
    Handles all data consolidation, storage, and management
    Replaces the data handling logic from original ibinsync code
    """
    
    def __init__(self, algorithm, symbol_manager=None):
        self.algorithm = algorithm
        self.params = algorithm.parameters
        self.symbol = algorithm.symbol
        self.symbol_manager = symbol_manager  # Reference to access strategies for trailing order logging
        
        # Initialize data storage
        self.InitializeDataStorage()
        
        # Initialize consolidators
        self.InitializeConsolidators()
        
        # State tracking
        self.hasNewBar = False
        self.data_fetch_success = True
        self.last_bar_time = datetime.min
        
        # Daily values (will be calculated from bars)
        self.daily_high = 0
        self.daily_low = 0
        self.daily_open = 0
        self.daily_close = 0
        self.daily_volume = 0
        
        # Volume tracking for liquidity calculation (Reference implementation)
        self.daily_volumes = []  # List to store last 7 days of volume
        self.metric_Vol7DMA = 0  # 7-day moving average of volume
        self.metric_range_price30DMA = 1.0  # 30-day moving average of daily range percentage
        self._range_pct_window = deque()
        self._range_pct_sum = 0.0
        
        # Track if we've processed today's daily bar to avoid duplicates
        self.last_daily_bar_date = None
        
        # Flag to track historical loading status
        self.historical_data_loaded = False
        
        # Preload historical data so the first bar doesn't pay the cost
        if self.LoadHistoricalData():
            self.historical_data_loaded = True
    
        if self.algorithm.enable_logging:
            self.algorithm.Log("DataManager initialized")
    
    def InitializeDataStorage(self):
        """Initialize all data storage windows"""
        
        # Optimized window sizes based on actual usage analysis
        self.bars_15s = RollingWindow[TradeBar](45)  # Increased: needs 40 for sharp movement calc + buffer
        self.bars_1m = RollingWindow[TradeBar](5)    # Reduced: not used in calculations
        self.bars_daily = RollingWindow[TradeBar](35) # Reduced: needs 30 for 30DMA + buffer
        self.bars_weekly = RollingWindow[TradeBar](2) # Reduced: not used in calculations
        
        # Basic VWAP calculation for Reference behavior
        self.vwap_numerator = 0
        self.vwap_denominator = 0
        self.current_vwap = 0
    
    def LoadHistoricalData(self):
        """Load all required historical data immediately - matches ib.py fetch_data()"""
        
        # Reset status before attempting load
        self.data_fetch_success = True
        
        try:
            # Basic historical data loading for Reference behavior
            daily_history = self.algorithm.History(self.symbol, 50, Resolution.Daily)
            daily_count = 0
            
            if not daily_history.empty:
                for index, row in daily_history.iterrows():
                    try:
                        if isinstance(index, tuple):
                            datetime_val = index[1] if len(index) > 1 else index[0]
                        else:
                            datetime_val = index
                        
                        bar = TradeBar(datetime_val, self.symbol, 
                                     float(row['open']), float(row['high']), 
                                     float(row['low']), float(row['close']), 
                                     int(row['volume']))
                        self.bars_daily.Add(bar)
                        daily_count += 1
                        
                        # Also update volume tracking for liquidity
                        self.UpdateDailyVolumeTracking(bar)
                        self._update_daily_range_metric(bar)
                    except Exception as e:
                        self.algorithm.Debug(f"Error creating daily bar: {e}")
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"Basic historical data loaded: {daily_count} daily bars")
            
            return True
        except Exception as e:
            self.algorithm.Error(f"Error loading historical data: {e}")
            self.data_fetch_success = False
            return False
    
    def InitializeConsolidators(self):
        """Set up basic data consolidators for Reference behavior"""
        
        # Basic 15-second consolidator
        self.algorithm.Consolidate(self.symbol, timedelta(seconds=15), self.On15SecondBar)
        
        # Basic 1-minute consolidator
        self.algorithm.Consolidate(self.symbol, Resolution.Minute, self.OnMinuteBar)
        
        # Daily consolidator for updating 30DMA and other daily metrics
        self.algorithm.Consolidate(self.symbol, Resolution.Daily, self.OnDailyBar)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log("Basic data consolidators initialized")
    
    def On15SecondBar(self, bar):
        """Handle 15-second bar updates - Reference behavior"""
        
        # Log 15-second bar activity - DISABLED for performance (high-frequency)
        if self.algorithm.enable_logging:
            # self.algorithm.Log(f"15s Bar {self.symbol}: {bar.Time} | O:{bar.Open:.2f} H:{bar.High:.2f} L:{bar.Low:.2f} C:{bar.Close:.2f} V:{bar.Volume}")
            pass
        
        # Basic bar storage
        self.bars_15s.Add(bar)
        
        # Basic VWAP calculation
        self.UpdateVWAP(bar)
        
        # Basic daily values update
        self.UpdateDailyValues(bar)
        
        # Log current prices of active trailing orders every 15 seconds
        if self.symbol_manager and hasattr(self.symbol_manager, 'strategies'):
            for strategy in self.symbol_manager.strategies:
                strategy.LogTrailingOrderPrices()
        
        # Set new bar flag
        self.hasNewBar = True
        self.last_bar_time = bar.Time
    
    def OnMinuteBar(self, bar):
        """Handle 1-minute bars"""
        self.bars_1m.Add(bar)
    
    def OnDailyBar(self, bar):
        """Handle daily bar updates - Update 30DMA and other daily metrics"""
        
        # Avoid processing the same day multiple times
        if self.last_daily_bar_date and bar.Time.date() == self.last_daily_bar_date:
            return
            
        self.last_daily_bar_date = bar.Time.date()
        
        # Add the new daily bar to our rolling window
        self.bars_daily.Add(bar)
        
        # Update volume tracking for liquidity
        self.UpdateDailyVolumeTracking(bar)
        self._update_daily_range_metric(bar)
        
        # Clean up old 15-second bars from previous days
        self._cleanup_old_15s_bars()
        
        # Log the daily bar update
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Daily bar added for {self.symbol}: Date={bar.Time.date()}, O={bar.Open:.2f}, H={bar.High:.2f}, L={bar.Low:.2f}, C={bar.Close:.2f}, V={bar.Volume}")
        
        # The 30DMA will be automatically recalculated on the next metrics calculation
        # since CalculateReferenceParameterMetrics() uses self.bars_daily
    
    def OnData(self, data):
        """Main data processing entry point"""
        
        # Load historical data on first call if pre-load failed
        if not self.historical_data_loaded:
            if self.LoadHistoricalData():
                self.historical_data_loaded = True
        
        # Only process if we have a new 15-second bar
        if not self.hasNewBar:
            return False
        
        # Reset flag
        self.hasNewBar = False
        
        # Validate data quality
        if not self.ValidateDataQuality():
            return False
        
        return True
    
    
    def ValidateDataQuality(self):
        """Validate data quality and freshness"""
        
        if self.bars_15s.Count < 2:
            return False
        
        # Check if data is too old
        current_time = self.algorithm.Time
        last_bar_time = self.last_bar_time
        
        if (current_time - last_bar_time).total_seconds() > 300:  # 5 minutes
            # self.algorithm.Debug(f"Data may be stale: last bar {last_bar_time}, current {current_time}")
            return False
        
        return True
    
    def UpdateVWAP(self, bar):
        """Update VWAP calculation with new bar"""
        
        # Only use market hours for VWAP
        if not self.IsMarketHours(bar.Time):
            return
        
        # Calculate typical price
        typical_price = (bar.High + bar.Low + bar.Close) / 3
        
        # Update VWAP components
        self.vwap_numerator += typical_price * bar.Volume
        self.vwap_denominator += bar.Volume
        
        # Calculate current VWAP
        if self.vwap_denominator > 0:
            self.current_vwap = self.vwap_numerator / self.vwap_denominator
        else:
            self.current_vwap = bar.Close
    
    def UpdateDailyValues(self, bar):
        """Update daily OHLCV values - Reference behavior"""
        
        # Basic daily values update
        if self.daily_high == 0 or bar.High > self.daily_high:
            self.daily_high = bar.High
        if self.daily_low == 0 or bar.Low < self.daily_low:
            self.daily_low = bar.Low
        if self.daily_open == 0:
            self.daily_open = bar.Open
        self.daily_close = bar.Close
        self.daily_volume += bar.Volume
    
    def ResetDailyVWAP(self):
        """Reset VWAP calculation for new day"""
        self.vwap_numerator = 0
        self.vwap_denominator = 0
        self.current_vwap = 0
    
    def ResetDaily(self):
        """Reset all daily tracking values (preserve accumulated bars)"""
        
        # Reset daily OHLCV values
        self.daily_high = 0
        self.daily_low = 0
        self.daily_open = 0
        self.daily_close = 0
        self.daily_volume = 0
        
        # Reset VWAP calculation
        self.ResetDailyVWAP()
        
        # Reset bar flags
        self.hasNewBar = False
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"Daily data values reset for {self.symbol}")
    
    
    def IsMarketHours(self, dt):
        """Check if datetime is during market hours (9:30 AM - 4:00 PM ET)"""
        time_obj = dt.time()
        return time(9, 30) <= time_obj <= time(16, 0)
    
    
    
    def GetVWAP(self):
        """Get current VWAP value"""
        return self.current_vwap
    
    def GetVWAPDeviation(self, current_price):
        """Get VWAP deviation as percentage"""
        if self.current_vwap > 0:
            return (current_price - self.current_vwap) * 100.0 / current_price
        return 0
    
    def UpdateDailyVolumeTracking(self, bar):
        """Update daily volume tracking for liquidity calculation (Reference implementation)"""
        # Add the bar's volume to our tracking list
        self.daily_volumes.append(bar.Volume)
        
        # Keep only the last 7 days
        if len(self.daily_volumes) > 7:
            self.daily_volumes.pop(0)
        
        # Calculate 7-day moving average
        self.CalculateVol7DMA()
    
    def CalculateVol7DMA(self):
        """Calculate 7-day moving average of volume (Reference implementation)"""
        if len(self.daily_volumes) > 0:
            self.metric_Vol7DMA = sum(self.daily_volumes) / len(self.daily_volumes)
        else:
            self.metric_Vol7DMA = 0
    
    def _update_daily_range_metric(self, bar):
        """Maintain rolling 30-day average of (high-low)/open range percentage."""
        if bar.Open > 0:
            range_pct = ((bar.High - bar.Low) * 100.0) / bar.Open
        else:
            range_pct = 0.0

        window = self._range_pct_window
        if len(window) == 30:
            self._range_pct_sum -= window.popleft()

        window.append(range_pct)
        self._range_pct_sum += range_pct

        if window:
            self.metric_range_price30DMA = self._range_pct_sum / len(window)
        else:
            self.metric_range_price30DMA = 1.0  # Fallback to avoid division by zero
    
    def GetVol7DMA(self):
        """Get the 7-day moving average of volume"""
        # If we don't have enough daily data, calculate from available daily bars
        if self.metric_Vol7DMA == 0 and self.bars_daily.Count > 0:
            volumes = []
            for i in range(min(7, self.bars_daily.Count)):
                volumes.append(self.bars_daily[i].Volume)
            if len(volumes) > 0:
                self.metric_Vol7DMA = sum(volumes) / len(volumes)
        
        return self.metric_Vol7DMA
    
    
    
    
    
    def _cleanup_old_15s_bars(self):
        """Remove 15-second bars from previous days to ensure we only use today's data"""
        current_date = self.algorithm.Time.date()
        
        # Create a new list with only today's bars
        today_bars = []
        for i in range(self.bars_15s.Count):
            bar = self.bars_15s[i]
            if bar.Time.date() == current_date:
                today_bars.append(bar)
        
        # Clear and repopulate the rolling window with today's bars only
        # Note: We add in reverse order since RollingWindow stores newest first
        if len(today_bars) > 0:
            # Clear the window
            while self.bars_15s.Count > 0:
                self.bars_15s.Reset()
            
            # Add today's bars back (newest to oldest)
            for bar in today_bars:
                self.bars_15s.Add(bar)
            
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Cleaned up 15s bars, kept {len(today_bars)} bars from today")

    def __str__(self):
        """String representation"""
        return f"DataManager(15s_bars={self.bars_15s.Count}, daily_bars={self.bars_daily.Count}, vwap={self.current_vwap:.2f})"
