# metrics_calculator.py - Basic Metrics Calculator for Reference Behavior
from AlgorithmImports import *

class MetricsCalculator:
    """
    Basic metrics calculation for Reference behavior
    Only calculates metrics actually used in trading decisions
    Simplified from enhanced ZacQC implementation
    """
    
    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.data_manager = algorithm.data_manager
        self.params = algorithm.parameters
        self.metrics = {}
        
        # Reference Parameter_1 and Parameter_2 storage (exact replication)
        self.actual_p1 = self.params.Parameter_1
        self.actual_p2 = self.params.Parameter_2
        
        # Reference metric_range_price30DMA calculation storage
        self.metric_range_price30DMA = None
        
        # Phase 3: VWAP calculation storage (for VWAP validation)
        self.metric_vwap_price = None
        self.metric_range_price7DMA = None
        self.metric_range_price = 0.0
        self.metric_range_multiplier = 0.0
        
        # Gap calculation storage (Reference implementation)
        self.metric_1d_gap = 0.0
        
        # Liquidity calculation storage (Reference implementation)
        self.metric_liquidity = 0.0
        
        # Sharp movement calculation storage (Reference implementation)
        self.metric_sharp_movement_pct = 0.0
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Basic MetricsCalculator initialized with Phase 3 VWAP support")
    
    def CalculateAllMetrics(self, data):
        """Calculate only essential metrics used in Reference trading decisions"""
        
        if self.data_manager.bars_15s.Count < 2:
            return self.metrics
        
        current_price = data[self.algorithm.symbol].Close
        
        # Calculate Reference Parameter-based metrics
        self.CalculateReferenceParameterMetrics()
        
        # Only calculate metrics actually used in Reference trading logic
        self.CalculateEssentialMetrics(current_price)
        
        # Calculate gap metric (Reference implementation)
        self.CalculateGapMetric()
        
        # Calculate liquidity metric (Reference implementation)
        self.CalculateLiquidityMetric(current_price)
        
        # Calculate sharp movement metric (Reference implementation)
        self.CalculateSharpMovementMetric()
        
        return self.metrics
    
    def CalculateEssentialMetrics(self, current_price):
        """Calculate only the essential metrics for Reference trading"""
        
        # Basic price data (used in conditions_checker.py)
        self.metrics['price'] = current_price
        self.metrics['daily_high'] = self.data_manager.daily_high
        self.metrics['daily_low'] = self.data_manager.daily_low
        self.metrics['daily_open'] = self.data_manager.daily_open
        
        # Phase 3: Calculate VWAP and related metrics
        self.CalculateVWAPMetrics(current_price)
        self.metrics['daily_close'] = self.data_manager.daily_close
        self.metrics['daily_volume'] = self.data_manager.daily_volume
        
        # VWAP (used in CheckCondition1 and CheckCondition4)
        self.metrics['metric_vwap'] = self.data_manager.GetVWAP()
        
        # Reference Parameter_1 and Parameter_2 dependent metrics (exact replication)
        if self.data_manager.daily_open > 0:
            # metric_range_percfromopen = (daily_close - daily_open) * 100 / daily_open
            self.metrics['metric_range_percfromopen'] = (self.data_manager.daily_close - self.data_manager.daily_open) * 100 / self.data_manager.daily_open
            
            # metric_range_price = (daily_high - daily_low) * 100.0 / daily_open
            self.metrics['metric_range_price'] = (self.data_manager.daily_high - self.data_manager.daily_low) * 100.0 / self.data_manager.daily_open
        else:
            self.metrics['metric_range_percfromopen'] = 0
            self.metrics['metric_range_price'] = 0
        
        # Basic range calculation for condition logic
        if self.data_manager.daily_high > self.data_manager.daily_low:
            range_size = self.data_manager.daily_high - self.data_manager.daily_low
            # Position within daily range (used in CheckCondition2 and CheckCondition5)
            self.metrics['daily_range'] = range_size
            self.metrics['range_position'] = (current_price - self.data_manager.daily_low) / range_size
        else:
            self.metrics['daily_range'] = 0
            self.metrics['range_position'] = 0.5
        
        # Basic momentum for CheckCondition3
        if self.data_manager.bars_15s.Count >= 4:
            current_bar = self.data_manager.bars_15s[0]
            prev_bar = self.data_manager.bars_15s[3]
            if prev_bar.Close > 0:
                self.metrics['momentum_3_bars'] = (current_bar.Close - prev_bar.Close) / prev_bar.Close
            else:
                self.metrics['momentum_3_bars'] = 0
        else:
            self.metrics['momentum_3_bars'] = 0
    
    def GetMetric(self, metric_name):
        """Get a metric value"""
        return self.metrics[metric_name]
    
    def CalculateReferenceParameterMetrics(self):
        """Calculate Reference-specific metrics that use Parameter_1, Parameter_2, Parameter_3"""
        
        range_pct_30dma = getattr(self.data_manager, 'metric_range_price30DMA', None)
        if range_pct_30dma is None or range_pct_30dma <= 0:
            range_pct_30dma = 1.0

        self.metric_range_price30DMA = range_pct_30dma
        self.metrics['metric_range_price30DMA'] = self.metric_range_price30DMA
    
    def CalculateMaxDownPercentage(self, max_seconds=1800):
        """Calculate max down percentage over specified seconds (exact Reference replication)"""
        
        if self.data_manager.bars_15s.Count < 2:
            return 0.0
        
        # Get current time and market open time
        current_time = self.algorithm.Time
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        
        # If before market open, return 0
        if current_time < market_open:
            return 0.0
        
        # Find bars within the time window (exact Reference logic)
        bars_15s = self.data_manager.bars_15s
        current_bar_time = bars_15s[0].Time

        start_idx = None
        for idx in range(bars_15s.Count - 1, -1, -1):
            bar = bars_15s[idx]
            diff_seconds = (current_bar_time - bar.Time).total_seconds()
            if diff_seconds > max_seconds or bar.Time < market_open:
                break
            start_idx = idx

        if start_idx is None or start_idx >= bars_15s.Count - 1:
            return 0.0

        max_down = 0.0
        max_high = bars_15s[start_idx].High

        for idx in range(start_idx + 1, bars_15s.Count):
            bar = bars_15s[idx]
            if bar.High > max_high:
                max_high = bar.High

            if max_high > 0:
                down_pct = (bar.Low - max_high) * 100 / max_high
                if down_pct < max_down:
                    max_down = down_pct

        return max_down
    
    def CalculateVWAPMetrics(self, current_price):
        """Phase 3: Calculate VWAP and related metrics for Reference implementation"""
        try:
            # Basic implementation - can be enhanced later
            # For now, use daily open as VWAP reference point
            daily_open = self.data_manager.daily_open
            
            if daily_open and daily_open > 0:
                # Calculate VWAP price difference (simplified)
                self.metric_vwap_price = ((current_price - daily_open) / daily_open) * 100
            else:
                self.metric_vwap_price = 0.0
                
            # Calculate range-based metrics
            daily_high = self.data_manager.daily_high
            daily_low = self.data_manager.daily_low
            daily_open = self.data_manager.daily_open
            
            # Use daily_open as denominator to match Reference implementation
            if daily_high and daily_low and daily_open and daily_open > 0:
                self.metric_range_price = ((daily_high - daily_low) / daily_open) * 100
            else:
                self.metric_range_price = 1.0
                
            # Use metric_range_price30DMA for metric_range_price7DMA (simplified)
            self.metric_range_price7DMA = self.metric_range_price30DMA if self.metric_range_price30DMA else 1.0
            
            # Calculate range multiplier (simplified)
            if self.metric_range_price30DMA and self.metric_range_price30DMA > 0:
                self.metric_range_multiplier = self.metric_range_price / self.metric_range_price30DMA
            else:
                self.metric_range_multiplier = 1.0
                
            # Store in metrics dict
            self.metrics['metric_vwap_price'] = self.metric_vwap_price
            self.metrics['metric_range_price'] = self.metric_range_price
            self.metrics['metric_range_price7DMA'] = self.metric_range_price7DMA
            self.metrics['metric_range_multiplier'] = self.metric_range_multiplier
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - VWAP calculation error: {e}")
            # Set defaults on error
            self.metric_vwap_price = 0.0
            self.metric_range_price = 1.0
            self.metric_range_price7DMA = 1.0
            self.metric_range_multiplier = 1.0
    
    def CalculateGapMetric(self):
        """
        Calculate the 1-day gap metric (Reference implementation)
        Formula: (today_open - yesterday_close) * 100 / yesterday_close
        """
        try:
            # Need at least 2 daily bars for gap calculation
            if self.data_manager.bars_daily.Count < 2:
                self.metric_1d_gap = 0.0
                self.metrics['metric_1d_gap'] = self.metric_1d_gap
                return
            
            # Get today's open from daily data
            today_open = self.data_manager.daily_open
            
            # Get yesterday's close
            # The most recent daily bar [0] might be today's incomplete bar
            # So we look at [1] for yesterday
            yesterday_bar = self.data_manager.bars_daily[1]
            yesterday_close = yesterday_bar.Close
            
            # Calculate gap percentage (exact Reference formula)
            if yesterday_close > 0:
                self.metric_1d_gap = (today_open - yesterday_close) * 100.0 / yesterday_close
                self.metric_1d_gap = round(self.metric_1d_gap, 2)
            else:
                self.metric_1d_gap = 0.0
            
            self.metrics['metric_1d_gap'] = self.metric_1d_gap
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Gap calculation error: {e}")
            self.metric_1d_gap = 0.0
            self.metrics['metric_1d_gap'] = self.metric_1d_gap
    
    def CalculateLiquidityMetric(self, current_price):
        """
        Calculate liquidity metric (Reference implementation)
        Formula: metric_liquidity = metric_Vol7DMA / SECONDS_PER_TRADING_DAY * price
        """
        try:
            # Define seconds per trading day (9:30 AM to 4:00 PM = 6.5 hours)
            SECONDS_PER_TRADING_DAY = 6.5 * 60 * 60  # 23400 seconds
            
            # Get 7-day moving average of volume
            metric_Vol7DMA = self.data_manager.GetVol7DMA()
            
            # Calculate liquidity metric (exact Reference formula)
            if metric_Vol7DMA > 0 and current_price > 0:
                self.metric_liquidity = metric_Vol7DMA / SECONDS_PER_TRADING_DAY * current_price
            else:
                self.metric_liquidity = 0.0
            
            # Store in metrics dict
            self.metrics['metric_liquidity'] = self.metric_liquidity
            self.metrics['metric_Vol7DMA'] = metric_Vol7DMA
            
            # Also store liquidity in millions for easy threshold comparison
            self.metrics['metric_liquidity_millions'] = self.metric_liquidity / 1e6
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Liquidity calculation error: {e}")
            self.metric_liquidity = 0.0
            self.metrics['metric_liquidity'] = self.metric_liquidity
            self.metrics['metric_Vol7DMA'] = 0.0
            self.metrics['metric_liquidity_millions'] = 0.0
    
    def CalculateSharpMovementMetric(self):
        """
        Calculate sharp movement metric (Reference implementation)
        Formula: change_percentage = abs(highest_high - lowest_low) / lowest_low * 100
        Check: (change_percentage/metric_range_price30DMA) > (sharpmovement_threshold/100.0)
        """
        try:
            # Only calculate during market hours (Reference: is_marketopen check)
            current_time = self.algorithm.Time
            market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
            
            if current_time < market_open or current_time >= market_close:
                self.metric_sharp_movement_pct = 0.0
                self.metrics['metric_sharp_movement_pct'] = self.metric_sharp_movement_pct
                self.metrics['sharp_movement_threshold_exceeded'] = False
                return
            
            # Get the number of bars to look back (4 * SharpMovement_Minutes)
            sharp_movement_minutes = self.params.SharpMovement_Minutes
            bars_to_check = 4 * sharp_movement_minutes  # 15-second bars
            
            # Check if we have enough bars
            if self.data_manager.bars_15s.Count < bars_to_check:
                self.metric_sharp_movement_pct = 0.0
                self.metrics['metric_sharp_movement_pct'] = self.metric_sharp_movement_pct
                self.metrics['sharp_movement_threshold_exceeded'] = False
                return
            
            # Get last N bars (Reference: last_n_rows = self.df_15secs.tail(4 * self.cfg.sharpmovement_minutes))
            lowest_low = float('inf')
            highest_high = float('-inf')
            
            for i in range(bars_to_check):
                bar = self.data_manager.bars_15s[i]
                lowest_low = min(lowest_low, bar.Low)
                highest_high = max(highest_high, bar.High)
            
            # Calculate change percentage (Reference formula)
            if lowest_low > 0:
                change_percentage = abs(highest_high - lowest_low) / lowest_low * 100
            else:
                change_percentage = 0.0
            
            self.metric_sharp_movement_pct = change_percentage
            self.metrics['metric_sharp_movement_pct'] = self.metric_sharp_movement_pct
            
            # Check if threshold is exceeded (Reference: if (change_percentage/self.metric_range_price30DMA) > (self.cfg.sharpmovement_threshold/100.0))
            if self.metric_range_price30DMA and self.metric_range_price30DMA > 0:
                sharp_movement_threshold = self.params.SharpMovement_Threshold
                threshold_check = (change_percentage / self.metric_range_price30DMA) > (sharp_movement_threshold / 100.0)
                self.metrics['sharp_movement_threshold_exceeded'] = threshold_check
                
                if threshold_check:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - Sharp movement detected: {change_percentage:.2f}% / {self.metric_range_price30DMA:.2f} = {change_percentage/self.metric_range_price30DMA:.2f} > {sharp_movement_threshold/100.0:.2f}")
            else:
                self.metrics['sharp_movement_threshold_exceeded'] = False
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - Sharp movement calculation error: {e}")
            self.metric_sharp_movement_pct = 0.0
            self.metrics['metric_sharp_movement_pct'] = self.metric_sharp_movement_pct
            self.metrics['sharp_movement_threshold_exceeded'] = False
    
    def GetAllMetrics(self):
        """Get all calculated metrics"""
        return self.metrics.copy()
    
    def __str__(self):
        """String representation"""
        return f"BasicMetricsCalculator(metrics_count={len(self.metrics)}, price={self.metrics.get('price', 0):.2f})"
