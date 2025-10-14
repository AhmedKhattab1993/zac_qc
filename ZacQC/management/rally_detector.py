# rally_detector.py - Phase 3: Rally Detection System
from AlgorithmImports import *
from datetime import datetime, time, timedelta

class RallyDetector:
    """
    Evaluate rally momentum thresholds that gate condition execution.

    Parameters
    ----------
    algorithm : Algorithm
        Parent QCAlgorithm instance.
    params : TradingParameters
        Parameter container supplying rally thresholds.
    """
    
    def __init__(self, algorithm, params):
        self.algorithm = algorithm
        self.params = params
        self.data_cache = {}  # Store 15-second price data per symbol
        self.market_open = time(9, 30)  # 9:30 AM
        self.market_close = time(15, 59)  # 3:59 PM
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - RallyDetector initialized - Phase 3 momentum gate system")
    
    def update_price_data(self, symbol, bar_data):
        """
        Store 15-second price data for use in rally calculations.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        bar_data : TradeBar
            Consolidated 15-second bar.

        Returns
        -------
        None
        """
        timestamp = self.algorithm.Time
        
        # Only store data during market hours
        if not self.is_market_hours(timestamp):
            return
            
        # Initialize symbol cache if not exists
        if symbol not in self.data_cache:
            self.data_cache[symbol] = []
            
        price_data = {
            'symbol': symbol,
            'time': timestamp,
            'high': float(bar_data.High),
            'low': float(bar_data.Low),
            'close': float(bar_data.Close),
            'open': float(bar_data.Open)
        }
        
        self.data_cache[symbol].append(price_data)
        
        # Keep only recent data (rolling window - keep last 4 hours of 15-second data)
        max_entries = 4 * 60 * 4  # 4 hours * 60 minutes * 4 (15-second intervals per minute)
        if len(self.data_cache[symbol]) > max_entries:
            self.data_cache[symbol] = self.data_cache[symbol][-max_entries:]
    
    def is_market_hours(self, timestamp):
        """
        Determine whether a timestamp occurs during trading hours.

        Parameters
        ----------
        timestamp : datetime.datetime
            Timestamp to evaluate.

        Returns
        -------
        bool
            True when between 09:30 and 15:59 inclusive.
        """
        current_time = timestamp.time()
        return self.market_open <= current_time <= self.market_close
    
    def filter_market_hours_data(self, symbol):
        """
        Retrieve cached 15-second bars for today's session.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.

        Returns
        -------
        list[dict]
            Sequence of cached bar dictionaries constrained to market hours.
        """
        current_date = self.algorithm.Time.date()
        
        # Return empty list if symbol not in cache
        if symbol not in self.data_cache:
            return []
            
        # Filter for today's market hours only
        return [d for d in self.data_cache[symbol] 
                if d['time'].date() == current_date and self.is_market_hours(d['time'])]
    
    def check_long_rally_condition(self, symbol, metrics):
        """
        Validate upward rally momentum for long conditions.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        bool
            True when the rally supports long entries.
        """
        try:
            # Filter 15-second data for market hours only (9:30-15:59) - HARDCODED like Reference
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 10:  # Need minimum data points
                return False
                
            # Find lowest point first (matches Reference line 1123)
            lows = [(i, d['low'], d['time']) for i, d in enumerate(filtered)]
            lowest_idx, lowest_price, lowest_time = min(lows, key=lambda x: x[1])
            
            # Filter data from lowest point onwards (matches Reference line 1124)
            filtered_from_low = filtered[lowest_idx:]
            
            # Find highest point AFTER the lowest (matches Reference lines 1127-1128)
            if len(filtered_from_low) == 0:
                return False
            highs_after_low = [d['high'] for d in filtered_from_low]
            highest_price = max(highs_after_low)
            
            # Find the time of the highest price
            for d in filtered_from_low:
                if d['high'] == highest_price:
                    highest_time = d['time']
                    break
            
            # Rally X: Measure upward momentum (lowest to highest) - Reference lines 1120-1123
            metric_range_price = metrics.metric_range_price
            rally_x = ((highest_price - lowest_price) * 100.0 / lowest_price) / metric_range_price
            rally_x_condition = (rally_x >= (self.params.Rally_X_Min_PCT/100.0)) and \
                               (rally_x <= (self.params.Rally_X_Max_PCT/100.0))
            
            # Rally Y: Measure pullback from high (highest to current low) - Reference lines 1138-1144
            # Find index of highest in filtered_from_low
            highest_idx_in_filtered = None
            for i, d in enumerate(filtered_from_low):
                if d['high'] == highest_price:
                    highest_idx_in_filtered = i
                    break
                    
            # Filter from highest point onwards (matches Reference line 1140)
            if highest_idx_in_filtered is None:
                return False
            filtered_from_high = filtered_from_low[highest_idx_in_filtered:]
            
            if len(filtered_from_high) == 0:
                return False
                
            # Get last low from the filtered data (matches Reference line 1141)
            last_low = filtered_from_high[-1]['low']
            last_low_time = filtered_from_high[-1]['time']
            
            rally_y = abs((highest_price - last_low) * 100.0 / highest_price) / metric_range_price
            rally_y_condition = rally_y >= (self.params.Rally_Y_PCT/100.0)
            
            # Time constraint validation - matches Reference lines 1149-1150
            # delta = last_low_date - lowest_date
            time_constraint = self.validate_time_constraint_long(symbol, metrics, lowest_time, last_low_time)
            
            result = rally_x_condition and rally_y_condition and time_constraint
            
            # Log rally details with symbol and timestamp including thresholds
            rally_x_min_threshold = self.params.Rally_X_Min_PCT/100.0
            rally_x_max_threshold = self.params.Rally_X_Max_PCT/100.0
            rally_y_threshold = self.params.Rally_Y_PCT/100.0
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG {symbol}: Rally X={rally_x:.3f} [need {rally_x_min_threshold:.3f}-{rally_x_max_threshold:.3f}] ({rally_x_condition}), Rally Y={rally_y:.3f} [need ≥{rally_y_threshold:.3f}] ({rally_y_condition}), Time OK={time_constraint}")
            
            return result
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG ERROR - {symbol}: {e}")
            return False
    
    def check_short_rally_condition(self, symbol, metrics):
        """
        Validate downward rally momentum for short conditions.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        bool
            True when the rally supports short entries.
        """
        try:
            # Filter 15-second data for market hours only (9:30-15:59) - HARDCODED like Reference
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 10:  # Need minimum data points
                return False
                
            # Find highest point first (matches Reference line 1171)
            highs = [(i, d['high'], d['time']) for i, d in enumerate(filtered)]
            highest_idx, highest_price, highest_time = max(highs, key=lambda x: x[1])
            
            # Filter data from highest point onwards (matches Reference line 1172)
            filtered_from_high = filtered[highest_idx:]
            
            # Find lowest point AFTER the highest (matches Reference lines 1175-1176)
            if len(filtered_from_high) == 0:
                return False
            lows_after_high = [d['low'] for d in filtered_from_high]
            lowest_price = min(lows_after_high)
            
            # Find the time of the lowest price
            for d in filtered_from_high:
                if d['low'] == lowest_price:
                    lowest_time = d['time']
                    break
            
            # Rally X: Measure downward momentum (highest to lowest) - Reference lines 1174-1177
            metric_range_price = metrics.metric_range_price
            rally_x = ((highest_price - lowest_price) * 100.0 / highest_price) / metric_range_price
            rally_x_condition = (rally_x >= (self.params.Rally_X_Min_PCT/100.0)) and \
                               (rally_x <= (self.params.Rally_X_Max_PCT/100.0))
            
            # Rally Y: Measure bounce from low (lowest to current high) - Reference lines 1186-1194
            # Find index of lowest in filtered_from_high
            lowest_idx_in_filtered = None
            for i, d in enumerate(filtered_from_high):
                if d['low'] == lowest_price:
                    lowest_idx_in_filtered = i
                    break
                    
            # Filter from lowest point onwards (matches Reference line 1188)
            if lowest_idx_in_filtered is None:
                return False
            filtered_from_low = filtered_from_high[lowest_idx_in_filtered:]
            
            if len(filtered_from_low) == 0:
                return False
                
            # Get last high from the filtered data (matches Reference line 1189)
            last_high = filtered_from_low[-1]['high']
            last_high_time = filtered_from_low[-1]['time']
            
            rally_y = abs((last_high - lowest_price) * 100.0 / lowest_price) / metric_range_price
            rally_y_condition = rally_y >= (self.params.Rally_Y_PCT/100.0)
            
            # Time constraint validation - matches Reference lines 1149-1150
            # delta = last_high_date - highest_date
            time_constraint = self.validate_time_constraint_short(symbol, metrics, highest_time, last_high_time)
            
            result = rally_x_condition and rally_y_condition and time_constraint
            
            # Log rally details with symbol and timestamp including thresholds
            rally_x_min_threshold = self.params.Rally_X_Min_PCT/100.0
            rally_x_max_threshold = self.params.Rally_X_Max_PCT/100.0
            rally_y_threshold = self.params.Rally_Y_PCT/100.0
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT {symbol}: Rally X={rally_x:.3f} [need {rally_x_min_threshold:.3f}-{rally_x_max_threshold:.3f}] ({rally_x_condition}), Rally Y={rally_y:.3f} [need ≥{rally_y_threshold:.3f}] ({rally_y_condition}), Time OK={time_constraint}")
            
            return result
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT ERROR - {symbol}: {e}")
            return False
    
    def validate_time_constraint_long(self, symbol, metrics, lowest_time, last_low_time):
        """
        Enforce rally timing constraints for long entries.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range multiples.
        lowest_time : datetime.datetime
            Timestamp of the lowest price in the rally.
        last_low_time : datetime.datetime
            Timestamp of the most recent low.

        Returns
        -------
        bool
            True when the rally duration satisfies configured thresholds.
        """
        try:
            # Get metric_range_multiplier from metrics
            metric_range_multiplier = metrics.metric_range_multiplier
            
            # Check if time constraint applies
            if metric_range_multiplier > self.params.Rally_Time_Constraint_Threshold:
                # Calculate actual rally duration from lowest to last low
                delta = last_low_time - lowest_time
                rally_duration_minutes = delta.total_seconds() / 60  # Convert to minutes
                required_minutes = self.params.Rally_Time_Constraint  # Already in minutes
                
                if rally_duration_minutes < required_minutes:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT FAILED {symbol} LONG - Duration: {rally_duration_minutes:.1f}min < Required: {required_minutes:.1f}min")
                    return False
                    
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT OK {symbol} LONG - Duration: {rally_duration_minutes:.1f}min >= Required: {required_minutes:.1f}min")
            
            return True
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT ERROR {symbol}: {e}")
            return True  # Default to allowing if error
    
    def validate_time_constraint_short(self, symbol, metrics, highest_time, last_high_time):
        """
        Enforce rally timing constraints for short entries.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range multiples.
        highest_time : datetime.datetime
            Timestamp of the highest price in the rally.
        last_high_time : datetime.datetime
            Timestamp of the most recent high.

        Returns
        -------
        bool
            True when the rally duration satisfies configured thresholds.
        """
        try:
            # Get metric_range_multiplier from metrics
            metric_range_multiplier = metrics.metric_range_multiplier
            
            # Check if time constraint applies
            if metric_range_multiplier > self.params.Rally_Time_Constraint_Threshold:
                # Calculate actual rally duration from highest to last high
                delta = last_high_time - highest_time
                rally_duration_minutes = delta.total_seconds() / 60  # Convert to minutes
                required_minutes = self.params.Rally_Time_Constraint  # Already in minutes
                
                if rally_duration_minutes < required_minutes:
                    if self.algorithm.enable_logging:
                        self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT FAILED {symbol} SHORT - Duration: {rally_duration_minutes:.1f}min < Required: {required_minutes:.1f}min")
                    return False
                    
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT OK {symbol} SHORT - Duration: {rally_duration_minutes:.1f}min >= Required: {required_minutes:.1f}min")
            
            return True
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY TIME CONSTRAINT ERROR {symbol}: {e}")
            return True  # Default to allowing if error
    
    def reset_daily_data(self):
        """
        Clear cached price data for the next trading session.

        Returns
        -------
        None
        """
        self.data_cache.clear()
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - RallyDetector reset for new trading day")
    
    def get_rally_statistics(self, symbol):
        """
        Provide summary statistics for debugging rally behaviour.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.

        Returns
        -------
        dict or None
            Snapshot of highs/lows and data density.
        """
        market_data = self.filter_market_hours_data(symbol)
        
        if len(market_data) < 2:
            return None
            
        lows = [d['low'] for d in market_data]
        highs = [d['high'] for d in market_data]
        
        return {
            'data_points': len(market_data),
            'lowest': min(lows),
            'highest': max(highs),
            'current_low': market_data[-1]['low'],
            'current_high': market_data[-1]['high'],
            'duration_minutes': self.calculate_rally_duration()
        }
    
    def check_long_rally_with_reset(self, symbol, metrics):
        """
        Evaluate long rally conditions and determine whether to reset state.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        tuple[bool, bool]
            Tuple of `(rally_result, reset_required)`.
        """
        try:
            # Filter 15-second data for market hours only
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 10:  # Need minimum data points
                return False, False
                
            # Find lowest point first (matches Reference line 1123)
            lows = [(i, d['low'], d['time']) for i, d in enumerate(filtered)]
            lowest_idx, lowest_price, lowest_time = min(lows, key=lambda x: x[1])
            
            # Filter data from lowest point onwards (matches Reference line 1124)
            filtered_from_low = filtered[lowest_idx:]
            
            # Find highest point AFTER the lowest (matches Reference lines 1127-1128)
            if len(filtered_from_low) == 0:
                return False, False
            highs_after_low = [d['high'] for d in filtered_from_low]
            highest_price = max(highs_after_low)
            
            # Find the time of the highest price
            for d in filtered_from_low:
                if d['high'] == highest_price:
                    highest_time = d['time']
                    break
            
            # Rally X: Measure upward momentum
            metric_range_price = metrics.metric_range_price
            rally_x = ((highest_price - lowest_price) * 100.0 / lowest_price) / metric_range_price
            rally_x_condition = (rally_x >= (self.params.Rally_X_Min_PCT/100.0)) and \
                               (rally_x <= (self.params.Rally_X_Max_PCT/100.0))
            
            # Rally Y: Measure pullback from high (matches Reference lines 1138-1144)
            # Find index of highest in filtered_from_low
            highest_idx_in_filtered = None
            for i, d in enumerate(filtered_from_low):
                if d['high'] == highest_price:
                    highest_idx_in_filtered = i
                    break
                    
            # Filter from highest point onwards
            if highest_idx_in_filtered is None:
                return False, False
            filtered_from_high = filtered_from_low[highest_idx_in_filtered:]
            
            if len(filtered_from_high) == 0:
                return False, False
                
            # Get last low from the filtered data
            last_low = filtered_from_high[-1]['low']
            last_low_time = filtered_from_high[-1]['time']
            
            rally_y = abs((highest_price - last_low) * 100.0 / highest_price) / metric_range_price
            rally_y_condition = rally_y >= (self.params.Rally_Y_PCT/100.0)
            
            # Time constraint validation
            time_constraint = self.validate_time_constraint_long(symbol, metrics, lowest_time, last_low_time)
            
            rally_result = rally_x_condition and rally_y_condition and time_constraint
            
            # Reference reset logic: reset when rally_x exceeds maximum
            reset_required = rally_x > (self.params.Rally_X_Max_PCT/100.0)
            
            # Log rally details with reset info
            rally_x_min_threshold = self.params.Rally_X_Min_PCT/100.0
            rally_x_max_threshold = self.params.Rally_X_Max_PCT/100.0
            rally_y_threshold = self.params.Rally_Y_PCT/100.0
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG {symbol}: Rally X={rally_x:.3f} [need {rally_x_min_threshold:.3f}-{rally_x_max_threshold:.3f}] ({rally_x_condition}), Rally Y={rally_y:.3f} [need ≥{rally_y_threshold:.3f}] ({rally_y_condition}), Time OK={time_constraint}, Reset={reset_required}")
            
            return rally_result, reset_required
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG WITH RESET ERROR - {symbol}: {e}")
            return False, True  # Error = reset conditions
    
    def check_short_rally_with_reset(self, symbol, metrics):
        """
        Evaluate short rally conditions and determine whether to reset state.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        tuple[bool, bool]
            Tuple of `(rally_result, reset_required)`.
        """
        try:
            # Filter 15-second data for market hours only
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 10:  # Need minimum data points
                return False, False
                
            # Find highest point first (mirrors long rally logic but opposite)
            highs = [(i, d['high'], d['time']) for i, d in enumerate(filtered)]
            highest_idx, highest_price, highest_time = max(highs, key=lambda x: x[1])
            
            # Filter data from highest point onwards (mirrors long rally logic)
            filtered_from_high = filtered[highest_idx:]
            
            # Find lowest point AFTER the highest (mirrors long rally logic)
            if len(filtered_from_high) == 0:
                return False, False
            lows_after_high = [d['low'] for d in filtered_from_high]
            lowest_price = min(lows_after_high)
            
            # Find the time of the lowest price
            for d in filtered_from_high:
                if d['low'] == lowest_price:
                    lowest_time = d['time']
                    break
            
            # Rally X: Measure downward momentum (highest to lowest)
            metric_range_price = metrics.metric_range_price
            rally_x = ((highest_price - lowest_price) * 100.0 / highest_price) / metric_range_price
            rally_x_condition = (rally_x >= (self.params.Rally_X_Min_PCT/100.0)) and \
                               (rally_x <= (self.params.Rally_X_Max_PCT/100.0))
            
            # Rally Y: Measure bounce from low (mirrors long rally logic)
            # Find index of lowest in filtered_from_high
            lowest_idx_in_filtered = None
            for i, d in enumerate(filtered_from_high):
                if d['low'] == lowest_price:
                    lowest_idx_in_filtered = i
                    break
                    
            # Filter from lowest point onwards
            if lowest_idx_in_filtered is None:
                return False, False
            filtered_from_low = filtered_from_high[lowest_idx_in_filtered:]
            
            if len(filtered_from_low) == 0:
                return False, False
                
            # Get last high from the filtered data
            last_high = filtered_from_low[-1]['high']
            last_high_time = filtered_from_low[-1]['time']
            
            rally_y = abs((last_high - lowest_price) * 100.0 / lowest_price) / metric_range_price
            rally_y_condition = rally_y >= (self.params.Rally_Y_PCT/100.0)
            
            # Time constraint validation
            time_constraint = self.validate_time_constraint_short(symbol, metrics, highest_time, last_high_time)
            
            rally_result = rally_x_condition and rally_y_condition and time_constraint
            
            # Reference reset logic: reset when rally_x exceeds maximum
            reset_required = rally_x > (self.params.Rally_X_Max_PCT/100.0)
            
            # Log rally details with reset info
            rally_x_min_threshold = self.params.Rally_X_Min_PCT/100.0
            rally_x_max_threshold = self.params.Rally_X_Max_PCT/100.0
            rally_y_threshold = self.params.Rally_Y_PCT/100.0
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT {symbol}: Rally X={rally_x:.3f} [need {rally_x_min_threshold:.3f}-{rally_x_max_threshold:.3f}] ({rally_x_condition}), Rally Y={rally_y:.3f} [need ≥{rally_y_threshold:.3f}] ({rally_y_condition}), Time OK={time_constraint}, Reset={reset_required}")
            
            return rally_result, reset_required
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT WITH RESET ERROR - {symbol}: {e}")
            return False, True  # Error = reset conditions
    
    def should_reset_conditions_long(self, symbol, metrics):
        """
        Decide whether long condition state should be reset due to momentum loss.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        bool
            True when conditions should reset.
        """
        try:
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 5:
                return True  # Reset if insufficient data
                
            # Check if recent price action shows rally deterioration
            recent_data = filtered[-5:]  # Last 5 data points
            recent_lows = [d['low'] for d in recent_data]
            recent_highs = [d['high'] for d in recent_data]
            
            # Check for significant downward trend in recent data
            if len(recent_data) >= 3:
                trend_decline = (recent_highs[0] - recent_lows[-1]) / recent_highs[0]
                if trend_decline > 0.02:  # 2% decline suggests rally failure
                    return True
                    
            return False  # Don't reset by default
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RESET CHECK LONG ERROR - {symbol}: {e}")
            return True  # Reset on error to be safe
    
    def should_reset_conditions_short(self, symbol, metrics):
        """
        Decide whether short condition state should be reset due to momentum loss.

        Parameters
        ----------
        symbol : str
            Trading symbol identifier.
        metrics : MetricsCalculator
            Metrics calculator exposing range values.

        Returns
        -------
        bool
            True when conditions should reset.
        """
        try:
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 5:
                return True  # Reset if insufficient data
                
            # Check if recent price action shows rally deterioration
            recent_data = filtered[-5:]  # Last 5 data points
            recent_lows = [d['low'] for d in recent_data]
            recent_highs = [d['high'] for d in recent_data]
            
            # Check for significant upward trend in recent data
            if len(recent_data) >= 3:
                trend_incline = (recent_highs[-1] - recent_lows[0]) / recent_lows[0]
                if trend_incline > 0.02:  # 2% incline suggests short rally failure
                    return True
                    
            return False  # Don't reset by default
            
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RESET CHECK SHORT ERROR - {symbol}: {e}")
            return True  # Reset on error to be safe
