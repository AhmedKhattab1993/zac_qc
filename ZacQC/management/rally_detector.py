# rally_detector.py - Phase 3: Rally Detection System
from AlgorithmImports import *
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from itertools import islice

@dataclass(slots=True)
class RallySample:
    """Lightweight container for rally detection samples."""
    time: datetime
    high: float
    low: float
    close: float
    open: float

class RallyDetector:
    """
    Phase 3: Rally Detection System - MOMENTUM GATE FOR EXISTING CONDITIONS
    
    This module implements the 5-parameter rally detection system that acts as
    a momentum gate for existing entry conditions. Rally detection ENHANCES
    but does NOT replace the existing 4 entry conditions from previous phases.
    
    Parameters used:
    - Rally_X_Min_PCT: Rally X minimum percentage (rally_x_min_pct)
    - Rally_X_Max_PCT: Rally X maximum percentage (rally_x_max_pct)  
    - Rally_Y_PCT: Rally Y percentage threshold (rally_y_pct)
    - Rally_Time_Constraint: Rally time constraint in MINUTES (rally_x_rally_y_time_constraint)
    - Rally_Time_Constraint_Threshold: Rally threshold multiplier (threshold)
    """
    
    def __init__(self, algorithm, params):
        self.algorithm = algorithm
        self.params = params
        self.data_cache = {}  # Store 15-second price data per symbol
        self.market_open = time(9, 30)  # 9:30 AM
        self.market_close = time(15, 59)  # 3:59 PM
        # Keep a bounded window of 15-second samples tuned to rally constraints
        window_minutes = max(float(params.Rally_Time_Constraint) * 4.0, 120.0)
        self.max_entries = int(window_minutes * 4)  # 4 samples per minute
        self._state = {}
        self._rally_x_min = params.Rally_X_Min_PCT / 100.0
        self._rally_x_max = params.Rally_X_Max_PCT / 100.0
        self._rally_y_threshold = params.Rally_Y_PCT / 100.0
        self._time_constraint_threshold = params.Rally_Time_Constraint_Threshold
        self._time_constraint_minutes = float(params.Rally_Time_Constraint)
        self._prune_window = timedelta(minutes=window_minutes)
        self._session_date = None
        self._session_open_dt = None
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - RallyDetector initialized - Phase 3 momentum gate system")
    
    def update_price_data(self, symbol, bar_data):
        """
        Store 15-second price data for rally calculations
        Called from main algorithm on each price update
        """
        timestamp = self.algorithm.Time
        
        # Only store data during market hours
        if not self.is_market_hours(timestamp):
            return
            
        # Initialize symbol cache if not exists
        if symbol not in self.data_cache:
            self.data_cache[symbol] = []

        cache = self.data_cache[symbol]
        cache.append(
            RallySample(
                time=timestamp,
                high=float(bar_data.High),
                low=float(bar_data.Low),
                close=float(bar_data.Close),
                open=float(bar_data.Open)
            )
        )
        self._prune_symbol_cache(symbol)
        self._mark_dirty(symbol, timestamp)
    
    def is_market_hours(self, timestamp):
        """Check if timestamp is within market hours (9:30 AM - 3:59 PM)"""
        current_time = timestamp.time()
        return self.market_open <= current_time <= self.market_close
    
    def filter_market_hours_data(self, symbol):
        """Filter cached data for today's market hours only and specific symbol"""
        cache = self.data_cache.get(symbol)
        if not cache:
            return []

        # Cache already pruned to current-day market hours
        return cache
    
    def _prune_symbol_cache(self, symbol):
        """Keep cache entries bounded to the current session and rolling window"""
        cache = self.data_cache.get(symbol)
        if not cache:
            return

        now = self.algorithm.Time
        current_date = now.date()
        if self._session_date != current_date:
            self._session_date = current_date
            self._session_open_dt = datetime.combine(current_date, self.market_open)

        open_dt = self._session_open_dt
        cutoff_time = now - self._prune_window
        threshold_time = open_dt if open_dt > cutoff_time else cutoff_time

        prune_count = 0
        for sample in cache:
            if sample.time >= threshold_time and sample.time.date() == current_date:
                break
            prune_count += 1

        if prune_count > 0:
            del cache[:prune_count]

        # Enforce max length by removing oldest entries
        excess = len(cache) - self.max_entries
        if excess > 0:
            del cache[:excess]

    def _ensure_state_entry(self, symbol):
        """Ensure the rally state dict exists for a symbol."""
        if symbol not in self._state:
            self._state[symbol] = {
                'latest_time': None,
                'long': {
                    'computed_time': None,
                    'result': False,
                    'reset': False
                },
                'short': {
                    'computed_time': None,
                    'result': False,
                    'reset': False
                }
            }
        return self._state[symbol]

    def _mark_dirty(self, symbol, timestamp):
        """Mark cached rally computations stale after new data arrives."""
        state = self._ensure_state_entry(symbol)
        state['latest_time'] = timestamp
        state['long']['computed_time'] = None
        state['short']['computed_time'] = None

    def _compute_long_state(self, symbol, metrics):
        """Compute or retrieve cached rally metrics for long conditions."""
        state = self._ensure_state_entry(symbol)
        latest_time = state.get('latest_time')
        long_state = state['long']

        if latest_time is None:
            long_state['computed_time'] = None
            long_state['result'] = False
            long_state['reset'] = False
            return long_state

        if long_state['computed_time'] == latest_time:
            return long_state

        filtered = self.filter_market_hours_data(symbol)
        metric_range_price = getattr(metrics, 'metric_range_price', None)

        if len(filtered) < 10 or not metric_range_price or metric_range_price <= 0:
            long_state['computed_time'] = latest_time
            long_state['result'] = False
            long_state['reset'] = False
            return long_state
        try:
            lowest_idx, lowest_sample = min(
                enumerate(filtered),
                key=lambda item: item[1].low
            )
        except ValueError:
            long_state['computed_time'] = latest_time
            long_state['result'] = False
            long_state['reset'] = False
            return long_state

        lowest_price = lowest_sample.low
        lowest_time = lowest_sample.time

        slice_iter = enumerate(islice(filtered, lowest_idx, None), start=lowest_idx)
        try:
            highest_idx, highest_sample = max(
                slice_iter,
                key=lambda item: item[1].high
            )
        except ValueError:
            long_state['computed_time'] = latest_time
            long_state['result'] = False
            long_state['reset'] = False
            return long_state

        highest_price = highest_sample.high
        highest_time = highest_sample.time
        last_sample = filtered[-1]
        last_low = last_sample.low
        last_low_time = last_sample.time

        rally_x = ((highest_price - lowest_price) * 100.0 / lowest_price) / metric_range_price
        rally_x_condition = self._rally_x_min <= rally_x <= self._rally_x_max

        rally_y = abs((highest_price - last_low) * 100.0 / highest_price) / metric_range_price
        rally_y_condition = rally_y >= self._rally_y_threshold

        time_constraint = self.validate_time_constraint_long(symbol, metrics, lowest_time, last_low_time)

        long_state['computed_time'] = latest_time
        long_state['result'] = rally_x_condition and rally_y_condition and time_constraint
        long_state['reset'] = rally_x > self._rally_x_max

        if self.algorithm.enable_logging:
            self.algorithm.Log(
                f"{self.algorithm.Time} - RALLY LONG {symbol}: "
                f"Rally X={rally_x:.3f} [need {self._rally_x_min:.3f}-{self._rally_x_max:.3f}] ({rally_x_condition}), "
                f"Rally Y={rally_y:.3f} [need ≥{self._rally_y_threshold:.3f}] ({rally_y_condition}), "
                f"Time OK={time_constraint}, Reset={long_state['reset']}"
            )

        return long_state

    def _compute_short_state(self, symbol, metrics):
        """Compute or retrieve cached rally metrics for short conditions."""
        state = self._ensure_state_entry(symbol)
        latest_time = state.get('latest_time')
        short_state = state['short']

        if latest_time is None:
            short_state['computed_time'] = None
            short_state['result'] = False
            short_state['reset'] = False
            return short_state

        if short_state['computed_time'] == latest_time:
            return short_state

        filtered = self.filter_market_hours_data(symbol)
        metric_range_price = getattr(metrics, 'metric_range_price', None)

        if len(filtered) < 10 or not metric_range_price or metric_range_price <= 0:
            short_state['computed_time'] = latest_time
            short_state['result'] = False
            short_state['reset'] = False
            return short_state

        try:
            highest_idx, highest_sample = max(
                enumerate(filtered),
                key=lambda item: item[1].high
            )
        except ValueError:
            short_state['computed_time'] = latest_time
            short_state['result'] = False
            short_state['reset'] = False
            return short_state

        highest_price = highest_sample.high
        highest_time = highest_sample.time

        slice_iter = enumerate(islice(filtered, highest_idx, None), start=highest_idx)
        try:
            lowest_idx, lowest_sample = min(
                slice_iter,
                key=lambda item: item[1].low
            )
        except ValueError:
            short_state['computed_time'] = latest_time
            short_state['result'] = False
            short_state['reset'] = False
            return short_state

        lowest_price = lowest_sample.low
        lowest_time = lowest_sample.time
        last_sample = filtered[-1]
        last_high = last_sample.high
        last_high_time = last_sample.time

        rally_x = ((highest_price - lowest_price) * 100.0 / highest_price) / metric_range_price
        rally_x_condition = self._rally_x_min <= rally_x <= self._rally_x_max

        rally_y = abs((last_high - lowest_price) * 100.0 / lowest_price) / metric_range_price
        rally_y_condition = rally_y >= self._rally_y_threshold

        time_constraint = self.validate_time_constraint_short(symbol, metrics, highest_time, last_high_time)

        short_state['computed_time'] = latest_time
        short_state['result'] = rally_x_condition and rally_y_condition and time_constraint
        short_state['reset'] = rally_x > self._rally_x_max

        if self.algorithm.enable_logging:
            self.algorithm.Log(
                f"{self.algorithm.Time} - RALLY SHORT {symbol}: "
                f"Rally X={rally_x:.3f} [need {self._rally_x_min:.3f}-{self._rally_x_max:.3f}] ({rally_x_condition}), "
                f"Rally Y={rally_y:.3f} [need ≥{self._rally_y_threshold:.3f}] ({rally_y_condition}), "
                f"Time OK={time_constraint}, Reset={short_state['reset']}"
            )

        return short_state
    
    def check_long_rally_condition(self, symbol, metrics):
        """
        Validate upward rally momentum for LONG conditions (C1, C2) - Reference implementation
        
        Matches Reference rally_condition() method exactly
        
        Returns: True if rally momentum supports LONG entry, False otherwise
        """
        try:
            return self._compute_long_state(symbol, metrics)['result']
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG ERROR - {symbol}: {e}")
            return False
    
    def check_short_rally_condition(self, symbol, metrics):
        """
        Validate downward rally momentum for SHORT conditions (C4, C5) - Reference implementation
        
        Matches Reference rally_cond_short() method exactly
        
        Returns: True if rally momentum supports SHORT entry, False otherwise
        """
        try:
            return self._compute_short_state(symbol, metrics)['result']
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT ERROR - {symbol}: {e}")
            return False

    def validate_time_constraint_long(self, symbol, metrics, lowest_time, last_low_time):
        """
        Check rally timing requirements for LONG positions
        Matches Reference lines 1149-1150: delta = last_low_date - lowest_date
        
        Args:
            symbol: Trading symbol
            metrics: Metrics calculator instance
            lowest_time: Timestamp of the lowest price point
            last_low_time: Timestamp of the most recent low
        """
        try:
            # Get metric_range_multiplier from metrics
            metric_range_multiplier = metrics.metric_range_multiplier
            
            # Check if time constraint applies
            if metric_range_multiplier > self._time_constraint_threshold:
                # Calculate actual rally duration from lowest to last low
                delta = last_low_time - lowest_time
                rally_duration_minutes = delta.total_seconds() / 60  # Convert to minutes
                required_minutes = self._time_constraint_minutes  # Already in minutes
                
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
        Check rally timing requirements for SHORT positions
        Matches Reference: delta = last_high_date - highest_date
        
        Args:
            symbol: Trading symbol
            metrics: Metrics calculator instance
            highest_time: Timestamp of the highest price point
            last_high_time: Timestamp of the most recent high
        """
        try:
            # Get metric_range_multiplier from metrics
            metric_range_multiplier = metrics.metric_range_multiplier
            
            # Check if time constraint applies
            if metric_range_multiplier > self._time_constraint_threshold:
                # Calculate actual rally duration from highest to last high
                delta = last_high_time - highest_time
                rally_duration_minutes = delta.total_seconds() / 60  # Convert to minutes
                required_minutes = self._time_constraint_minutes  # Already in minutes
                
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
        """Reset rally detector for new trading day"""
        self.data_cache.clear()
        self._state.clear()
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - RallyDetector reset for new trading day")
    
    def get_rally_statistics(self, symbol):
        """Get current rally statistics for debugging/monitoring"""
        market_data = self.filter_market_hours_data(symbol)
        
        if len(market_data) < 2:
            return None
            
        lows = [d.low for d in market_data]
        highs = [d.high for d in market_data]
        
        return {
            'data_points': len(market_data),
            'lowest': min(lows),
            'highest': max(highs),
            'current_low': market_data[-1].low,
            'current_high': market_data[-1].high,
            'duration_minutes': self.calculate_rally_duration()
        }
    
    def check_long_rally_with_reset(self, symbol, metrics):
        """
        Check rally condition and return reset flag for LONG conditions (Reference-style)
        
        Returns: (rally_result, reset_required)
        """
        try:
            state = self._compute_long_state(symbol, metrics)
            return state['result'], state['reset']
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY LONG WITH RESET ERROR - {symbol}: {e}")
            return False, True  # Error = reset conditions

    def check_short_rally_with_reset(self, symbol, metrics):
        """
        Check rally condition and return reset flag for SHORT conditions (Reference-style)
        
        Returns: (rally_result, reset_required)
        """
        try:
            state = self._compute_short_state(symbol, metrics)
            return state['result'], state['reset']
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - RALLY SHORT WITH RESET ERROR - {symbol}: {e}")
            return False, True  # Error = reset conditions

    def should_reset_conditions_long(self, symbol, metrics):
        """
        Determine if LONG conditions should be reset based on rally deterioration
        
        Reference logic: Reset when rally momentum is lost or unfavorable
        """
        try:
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 5:
                return True  # Reset if insufficient data
                
            # Check if recent price action shows rally deterioration
            recent_data = filtered[-5:]  # Last 5 data points
            recent_lows = [d.low for d in recent_data]
            recent_highs = [d.high for d in recent_data]
            
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
        Determine if SHORT conditions should be reset based on rally deterioration
        
        Reference logic: Reset when rally momentum is lost or unfavorable
        """
        try:
            filtered = self.filter_market_hours_data(symbol)
            
            if len(filtered) < 5:
                return True  # Reset if insufficient data
                
            # Check if recent price action shows rally deterioration
            recent_data = filtered[-5:]  # Last 5 data points
            recent_lows = [d.low for d in recent_data]
            recent_highs = [d.high for d in recent_data]
            
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
