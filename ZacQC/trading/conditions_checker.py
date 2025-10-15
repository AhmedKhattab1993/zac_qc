# conditions_checker.py - Basic Trading Conditions for Reference Behavior
from AlgorithmImports import *
from management.rally_detector import RallyDetector

class ConditionsChecker:
    """
    Basic trading condition logic for Reference behavior
    Simplified from enhanced ZacQC implementation
    """
    
    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.params = algorithm.parameters
        
        # Phase 3: Initialize Rally Detection System
        self.rally_detector = RallyDetector(algorithm, self.params)
        
        if self.algorithm.enable_logging:
            self.algorithm.Log(f"{self.algorithm.Time} - Basic ConditionsChecker initialized with Phase 3 Rally Detection")
    
    def update_rally_data(self, symbol, bar_data):
        """Update rally detector with new price data"""
        self.rally_detector.update_price_data(symbol, bar_data)
    
    def reset_daily_rally_data(self):
        """Reset rally detector for new trading day"""
        self.rally_detector.reset_daily_data()
    
    def IsConditionEnabled(self, condition):
        """Check if specific condition is enabled via parameters"""
        
        condition_map = {
            'cond1': self.params.C1,
            'cond2': self.params.C2, 
            'cond3': self.params.C3,
            'cond4': self.params.C4,
            'cond5': self.params.C5
        }
        
        return condition_map.get(condition, False)
    
    def CheckAllConditions(self, strategy, metrics):
        """Check all trading conditions using Reference sequential state machine"""
        
        # Check risk manager validation first (including Max_Daily_PNL)
        if hasattr(self.algorithm, 'risk_manager'):
            if not self.algorithm.risk_manager.ValidateTradingConditions(metrics):
                # Trading disabled due to risk limits (e.g., daily P&L limit reached)
                return {
                    'cond1': False,
                    'cond2': False,
                    'cond3': False,
                    'cond4': False,
                    'cond5': False
                }
        
        # Check if current time is before 15:59 (EOD liquidation time)
        current_hour = self.algorithm.Time.hour
        current_minute = self.algorithm.Time.minute
        
        # Convert to minutes for easier comparison
        current_minutes = current_hour * 60 + current_minute
        cutoff_minutes = 15 * 60 + 59  # 15:59 in minutes
        
        if current_minutes >= cutoff_minutes:
            # No new entries after 15:59 to avoid conflicts with EOD liquidation
            return {
                'cond1': False,
                'cond2': False,
                'cond3': False,
                'cond4': False,
                'cond5': False
            }
        
        # Phase 3: Reference Sequential State Machine - conditions are checked individually
        conditions = {}
        for condition in ['cond1', 'cond2', 'cond3', 'cond4', 'cond5']:
            # Check condition enablement
            is_enabled = self.IsConditionEnabled(condition)
            
            if not is_enabled:
                conditions[condition] = False
                continue
                
            # Check condition logic using sequential state machine
            if condition == 'cond1':
                condition_met = self.CheckCondition1(metrics, strategy)
            elif condition == 'cond2':
                condition_met = self.CheckCondition2(metrics, strategy)
            elif condition == 'cond3':
                condition_met = self.CheckCondition3(metrics, strategy)
            elif condition == 'cond4':
                condition_met = self.CheckCondition4(metrics, strategy)
            elif condition == 'cond5':
                condition_met = self.CheckCondition5(metrics, strategy)
            else:
                condition_met = False
                
            conditions[condition] = condition_met
        
        return conditions
    
    def CheckCondition1(self, metrics, strategy):
        """Reference-accurate sequential state machine for Condition 1 (LONG)"""
        
        # Get current time for timing constraints
        now = self.algorithm.Time
        
        # Phase 3: Pre-condition timing check (matches Reference pre_cond1)
        time_since_last = (now - strategy.get_last_execution_date('c1')).total_seconds()
        required_cooldown = strategy.cfg.SameConditionTimeC1 * 60  # Convert minutes to seconds
        pre_cond1 = time_since_last > required_cooldown
        
        if not pre_cond1:
            return False  # Timing constraint not met
            
        # Phase 3: Entry order guard validation
        if not self.is_entry_order_enabled():
            return False
            
        # Initialize rally condition result
        rally_cond = False
        
        # STEP 1: Check if basic condition should be evaluated (Reference sequential logic)
        if not strategy.get_condition_state('c1'):
            # Basic condition logic (FIRST STEP - matches Reference)
            metrics_calc = self.algorithm.metrics_calculator
            metric_range_percfromopen = metrics.get('metric_range_percfromopen', 0)
            metric_range_price30DMA = metrics_calc.metric_range_price30DMA
            actual_p1 = metrics_calc.actual_p1  # Parameter_1 = 120
            
            if metric_range_price30DMA is None or metric_range_price30DMA <= 0:
                return False
                
            # Exact Reference Parameter_1 logic replication
            p1_threshold = -1.0 * metric_range_price30DMA * actual_p1 / 100.0
            condition_triggered = metric_range_percfromopen <= p1_threshold
            
            if condition_triggered:
                strategy.set_condition_state('c1', True)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 1 TRIGGERED {self.algorithm.symbol.Value} - Now monitoring for rally/VWAP")
                
        # STEP 2: If condition is active, monitor rally + VWAP (SECOND STEP)
        else:  # strategy.c1 is already True
            # VWAP validation for LONG (matches Reference vwap_condition12)
            vwap_condition12 = self.check_vwap_condition_long()
            
            # Rally validation with reset logic (only call once)
            rally_cond, reset = self.rally_detector.check_long_rally_with_reset(self.algorithm.symbol.Value, self.algorithm.metrics_calculator)
            
            # Reset condition if rally indicates reset (matches Reference)
            if reset:
                strategy.reset_condition_state('c1')
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 1 RESET {self.algorithm.symbol.Value} - Rally conditions failed")
                
        # STEP 3: Final execution check (all must be True simultaneously - matches Reference)
        # Use the rally_cond result from above instead of calling again
        return (strategy.get_condition_state('c1') and 
                rally_cond and
                vwap_condition12 and
                pre_cond1)
    
    def CheckCondition2(self, metrics, strategy):
        """Reference-accurate sequential state machine for Condition 2 (LONG)"""
        
        # Get current time for timing constraints
        now = self.algorithm.Time
        
        # Phase 3: Pre-condition timing check (matches Reference pre_cond2)
        time_since_last = (now - strategy.get_last_execution_date('c2')).total_seconds()
        required_cooldown = strategy.cfg.SameConditionTimeC2 * 60  # Convert minutes to seconds
        pre_cond2 = time_since_last > required_cooldown
        
        if not pre_cond2:
            return False  # Timing constraint not met
            
        # Phase 3: Entry order guard validation
        if not self.is_entry_order_enabled():
            return False
            
        # Initialize rally condition result
        rally_cond = False
        
        # STEP 1: Check if basic condition should be evaluated (Reference sequential logic)
        if not strategy.get_condition_state('c2'):
            # Basic condition logic (FIRST STEP - matches Reference)
            metrics_calc = self.algorithm.metrics_calculator
            metric_range_price = metrics.get('metric_range_price', 0)
            metric_range_price30DMA = metrics_calc.metric_range_price30DMA
            actual_p2 = metrics_calc.actual_p2  # Parameter_2 = 130
            
            if metric_range_price30DMA is None or metric_range_price30DMA <= 0:
                return False
            
            # Get today's 15-second bars only (matches Reference lines 1273-1275)
            today_bars = self._get_today_15s_bars()
            if len(today_bars) < 3:
                return False
                
            # Reference logic: second-to-last low < all previous lows (new low condition)
            second_last_low = today_bars[-2].Low  # [-2] in Reference
            previous_lows = [bar.Low for bar in today_bars[:-2]]  # [:-2] in Reference
            
            if len(previous_lows) == 0:
                return False
                
            new_low_condition = second_last_low < min(previous_lows)
            
            # Exact Reference Parameter_2 logic replication
            p2_threshold = (actual_p2 / 100.0) * metric_range_price30DMA
            range_condition = metric_range_price >= p2_threshold
            
            # Both conditions must be true
            condition_triggered = new_low_condition and range_condition
            
            if condition_triggered:
                strategy.set_condition_state('c2', True)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 2 TRIGGERED {self.algorithm.symbol.Value} - New Low: {new_low_condition}, Range: {range_condition} - Now monitoring for rally/VWAP")
                
        # STEP 2: If condition is active, monitor rally + VWAP (SECOND STEP)
        else:  # strategy.c2 is already True
            # VWAP validation for LONG (matches Reference vwap_condition12)
            vwap_condition12 = self.check_vwap_condition_long()
            
            # Rally validation with reset logic (only call once)
            rally_cond, reset = self.rally_detector.check_long_rally_with_reset(self.algorithm.symbol.Value, self.algorithm.metrics_calculator)
            
            # Reset condition if rally indicates reset (matches Reference)
            if reset:
                strategy.reset_condition_state('c2')
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 2 RESET {self.algorithm.symbol.Value} - Rally conditions failed")
                
        # STEP 3: Final execution check (all must be True simultaneously - matches Reference)
        # Use the rally_cond result from above instead of calling again
        return (strategy.get_condition_state('c2') and 
                rally_cond and
                vwap_condition12 and
                pre_cond2)
    
    def CheckCondition3(self, metrics, strategy):
        """Reference-accurate sequential state machine for Condition 3 (NEUTRAL)"""
        
        # Get current time for timing constraints
        now = self.algorithm.Time
        
        # Phase 3: Pre-condition timing check (matches Reference pre_cond3)
        time_since_last = (now - strategy.get_last_execution_date('c3')).total_seconds()
        required_cooldown = strategy.cfg.SameConditionTimeC3 * 60  # Convert minutes to seconds
        pre_cond3 = time_since_last > required_cooldown
        
        if not pre_cond3:
            return False  # Timing constraint not met
            
        # Phase 3: Entry order guard validation
        if not self.is_entry_order_enabled():
            return False
            
        # Condition 3 is simpler - no rally/VWAP requirements (matches Reference)
        metrics_calc = self.algorithm.metrics_calculator
        
        # Calculate mdp (max down percentage in last 1800 seconds - exact Reference)
        mdp = metrics_calc.CalculateMaxDownPercentage(1800)
        
        # Get metric_range_price30DMA (exact Reference)
        metric_range_price30DMA = metrics_calc.metric_range_price30DMA
        
        if metric_range_price30DMA is None or metric_range_price30DMA <= 0:
            return False
        
        # Exact Reference Parameter_3 logic replication
        param3_threshold = -1 * (self.params.Parameter_3 / 100.0)  # Parameter_3 = 300, so threshold = -3.0
        condition_result = mdp / metric_range_price30DMA <= param3_threshold
        
        return condition_result
    
    def CheckCondition4(self, metrics, strategy):
        """Reference-accurate sequential state machine for Condition 4 (SHORT)"""
        
        # Get current time for timing constraints
        now = self.algorithm.Time
        
        # Phase 3: Pre-condition timing check (matches Reference pre_cond4)
        time_since_last = (now - strategy.get_last_execution_date('c4')).total_seconds()
        required_cooldown = strategy.cfg.SameConditionTimeC4 * 60  # Convert minutes to seconds
        pre_cond4 = time_since_last > required_cooldown
        
        if not pre_cond4:
            return False  # Timing constraint not met
            
        # Phase 3: Entry order guard validation
        if not self.is_entry_order_enabled():
            return False
            
        # Initialize rally condition result
        rally_cond_short = False
        
        # STEP 1: Check if basic condition should be evaluated (Reference sequential logic)
        if not strategy.get_condition_state('c4'):
            # Basic condition logic (FIRST STEP - matches Reference)
            metrics_calc = self.algorithm.metrics_calculator
            metric_range_percfromopen = metrics.get('metric_range_percfromopen', 0)
            metric_range_price30DMA = metrics_calc.metric_range_price30DMA
            actual_p1 = metrics_calc.actual_p1  # Parameter_1 = 120
            
            if metric_range_price30DMA is None or metric_range_price30DMA <= 0:
                return False
                
            # Exact Reference Parameter_1 logic replication for SHORT
            p1_threshold = 1.0 * metric_range_price30DMA * actual_p1 / 100.0
            condition_triggered = metric_range_percfromopen >= p1_threshold
            
            if condition_triggered:
                strategy.set_condition_state('c4', True)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 4 TRIGGERED {self.algorithm.symbol.Value} - Now monitoring for rally/VWAP")
                
        # STEP 2: If condition is active, monitor rally + VWAP (SECOND STEP)
        else:  # strategy.c4 is already True
            # VWAP validation for SHORT (matches Reference vwap_condition45)
            vwap_condition45 = self.check_vwap_condition_short()
            
            # Rally validation with reset logic (only call once)
            rally_cond_short, reset = self.rally_detector.check_short_rally_with_reset(self.algorithm.symbol.Value, self.algorithm.metrics_calculator)
            
            # Reset condition if rally indicates reset (matches Reference)
            if reset:
                strategy.reset_condition_state('c4')
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 4 RESET {self.algorithm.symbol.Value} - Rally conditions failed")
                
        # STEP 3: Final execution check (all must be True simultaneously - matches Reference)
        # Use the rally_cond_short result from above instead of calling again
        return (strategy.get_condition_state('c4') and 
                rally_cond_short and
                vwap_condition45 and
                pre_cond4)
    
    def CheckCondition5(self, metrics, strategy):
        """Reference-accurate sequential state machine for Condition 5 (SHORT)"""
        
        # Get current time for timing constraints
        now = self.algorithm.Time
        
        # Phase 3: Pre-condition timing check (matches Reference pre_cond5)
        time_since_last = (now - strategy.get_last_execution_date('c5')).total_seconds()
        required_cooldown = strategy.cfg.SameConditionTimeC5 * 60  # Convert minutes to seconds
        pre_cond5 = time_since_last > required_cooldown
        
        if not pre_cond5:
            return False  # Timing constraint not met
            
        # Phase 3: Entry order guard validation
        if not self.is_entry_order_enabled():
            return False
            
        # Initialize rally condition result
        rally_cond_short = False
        
        # STEP 1: Check if basic condition should be evaluated (Reference sequential logic)
        if not strategy.get_condition_state('c5'):
            # Basic condition logic (FIRST STEP - matches Reference)
            metrics_calc = self.algorithm.metrics_calculator
            metric_range_price = metrics.get('metric_range_price', 0)
            metric_range_price30DMA = metrics_calc.metric_range_price30DMA
            actual_p2 = metrics_calc.actual_p2  # Parameter_2 = 130
            
            if metric_range_price30DMA is None or metric_range_price30DMA <= 0:
                return False
            
            # Get today's 15-second bars only (matches Reference lines 1306-1308)
            today_bars = self._get_today_15s_bars()
            if len(today_bars) < 3:
                return False
            
            # Reference logic: second-to-last high > all previous highs (new high condition)
            second_last_high = today_bars[-2].High  # [-2] in Reference
            previous_highs = [bar.High for bar in today_bars[:-2]]  # [:-2] in Reference
            
            if len(previous_highs) == 0:
                return False
                
            new_high_condition = second_last_high > max(previous_highs)
            
            # Exact Reference Parameter_2 logic replication
            p2_threshold = (actual_p2 / 100.0) * metric_range_price30DMA
            range_condition = metric_range_price >= p2_threshold
            
            # Both conditions must be true
            condition_triggered = new_high_condition and range_condition
            
            if condition_triggered:
                strategy.set_condition_state('c5', True)
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 5 TRIGGERED {self.algorithm.symbol.Value} - New High: {new_high_condition}, Range: {range_condition} - Now monitoring for rally/VWAP")
                
        # STEP 2: If condition is active, monitor rally + VWAP (SECOND STEP)
        else:  # strategy.c5 is already True
            # VWAP validation for SHORT (matches Reference vwap_condition45)
            vwap_condition45 = self.check_vwap_condition_short()
            
            # Rally validation with reset logic (only call once)
            rally_cond_short, reset = self.rally_detector.check_short_rally_with_reset(self.algorithm.symbol.Value, self.algorithm.metrics_calculator)
            
            # Reset condition if rally indicates reset (matches Reference)
            if reset:
                strategy.reset_condition_state('c5')
                if self.algorithm.enable_logging:
                    self.algorithm.Log(f"{self.algorithm.Time} - Condition 5 RESET {self.algorithm.symbol.Value} - Rally conditions failed")
                
        # STEP 3: Final execution check (all must be True simultaneously - matches Reference)
        # Use the rally_cond_short result from above instead of calling again
        return (strategy.get_condition_state('c5') and 
                rally_cond_short and
                vwap_condition45 and
                pre_cond5)
    
    def is_entry_order_enabled(self):
        """Check if current time is within entry order guard window (using Algo_Off_Before/After)"""
        # Get current hour and minute from algorithm time
        current_hour = self.algorithm.Time.hour
        current_minute = self.algorithm.Time.minute
        
        # Use Algo_Off_Before and Algo_Off_After (frontend configurable guard times)
        guard_start = self.params.Algo_Off_Before
        guard_end = self.params.Algo_Off_After
        
        # Convert current time to minutes since midnight for comparison
        current_minutes = current_hour * 60 + current_minute
        start_minutes = guard_start.hour * 60 + guard_start.minute
        end_minutes = guard_end.hour * 60 + guard_end.minute
        
        # Check if current time is within the trading window
        return start_minutes <= current_minutes < end_minutes
    
    def check_vwap_condition_long(self):
        """VWAP condition for LONG positions (conditions 1,2)
        Uses HARD threshold (no margin) matching Reference/ib.py lines 1262-1263, 1280-1281
        """
        try:
            vwap_price = self.algorithm.metrics_calculator.metric_vwap_price
            range_price_7dma = self.algorithm.metrics_calculator.metric_range_price7DMA
            vwap_pct = self.params.VWAP_PCT
            
            if vwap_price is None or range_price_7dma is None:
                return True  # Allow if no VWAP data available
                
            # Reference logic: vwap_price < 0 and abs(vwap_price) >= threshold
            # This is HARD threshold for condition checking
            hard_threshold = (vwap_pct * range_price_7dma / 100.0)
            result = (vwap_price < 0 and abs(vwap_price) >= hard_threshold)
            
            # Log disabled for performance (high-frequency)
            if self.algorithm.enable_logging:
                # self.algorithm.Log(f"VWAP Condition Check LONG (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_threshold:.4f}, Result: {result}")
                pass
            return result
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - VWAP LONG check error: {e}")
            return True  # Default to allowing if error
            
    def check_vwap_condition_short(self):
        """VWAP condition for SHORT positions (conditions 4,5)
        Uses HARD threshold (no margin) matching Reference/ib.py lines 1295-1296, 1313-1314
        """
        try:
            vwap_price = self.algorithm.metrics_calculator.metric_vwap_price
            range_price_7dma = self.algorithm.metrics_calculator.metric_range_price7DMA
            vwap_pct = self.params.VWAP_PCT
            
            if vwap_price is None or range_price_7dma is None:
                return True  # Allow if no VWAP data available
                
            # Reference logic: vwap_price > 0 and abs(vwap_price) >= threshold  
            # This is HARD threshold for condition checking
            hard_threshold = (vwap_pct * range_price_7dma / 100.0)
            result = (vwap_price > 0 and abs(vwap_price) >= hard_threshold)
            
            # Log disabled for performance (high-frequency)
            if self.algorithm.enable_logging:
                pass  # self.algorithm.Log(f"VWAP Condition Check SHORT (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_threshold:.4f}, Result: {result}")
            return result
        except Exception as e:
            if self.algorithm.enable_logging:
                self.algorithm.Log(f"{self.algorithm.Time} - VWAP SHORT check error: {e}")
            return True  # Default to allowing if error
            
    def check_rally_condition_long(self):
        """Check rally condition for LONG positions (wrapper)"""
        symbol = self.algorithm.symbol.Value
        return self.rally_detector.check_long_rally_condition(symbol, self.algorithm.metrics_calculator)
        
    def check_rally_condition_short(self):
        """Check rally condition for SHORT positions (wrapper)"""
        symbol = self.algorithm.symbol.Value
        return self.rally_detector.check_short_rally_condition(symbol, self.algorithm.metrics_calculator)
    
    def _get_today_15s_bars(self):
        """Get only today's 15-second bars starting from 9:30 AM"""
        bars_15s = self.algorithm.data_manager.bars_15s
        current_date = self.algorithm.Time.date()
        market_open = datetime.strptime("09:30", "%H:%M").time()
        
        today_bars = []
        for i in range(bars_15s.Count):
            bar = bars_15s[i]
            if bar.Time.date() == current_date and bar.Time.time() >= market_open:
                today_bars.append(bar)
        
        # Reverse to get chronological order (oldest first)
        today_bars.reverse()
        return today_bars
    
    def __str__(self):
        """String representation"""
        return f"BasicConditionsChecker(enabled_conditions={sum([self.IsConditionEnabled(f'cond{i}') for i in range(1, 6)])})"