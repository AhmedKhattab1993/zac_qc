# parameters.py - Trading Parameters Configuration
from datetime import time
import importlib.util
import json
import os
import sys
from pathlib import Path

class TradingParameters:
    """
    All trading parameters - replaces Google Sheets configuration
    Modify these values to adjust trading behavior
    
    FRONTEND-CONFIGURABLE PARAMETERS ARE ORDERED FIRST
    """
    
    def __init__(self):
        # ========================================================================
        # FRONTEND-CONFIGURABLE PARAMETERS (Set from Web UI) - ORDER PRIORITY #1
        # EXACT MAPPING TO REFERENCE PROJECT drive_sheet_values.txt
        # ========================================================================
        
        # Core Trading Parameters (rows 1-5 from Reference)
        # REALISTIC VALUES - Proper distances for take profit and stop loss
        self.Parameter_1 = 120 # Row 1 - Realistic threshold for proper TP/SL distances
        self.Parameter_2 = 130 # Row 2 - Realistic threshold for proper TP/SL distances
        self.Parameter_3 = 300 # Row 3 - Slightly lower for more opportunities
        self.Parameter_4 = 8 # Row 4 - Moderate trailing stop distance
        self.Parameter_5 = 0.85 # Row 5 - Moderate trailing stop distance
        
        # Condition Enablement (rows 6-10 from Reference)
        self.C1 = True # Row 6 - Reference value 1
        self.C2 = True # Row 7 - Reference value 1
        self.C3 = False # Row 8 - Disabled per user request
        self.C4 = True # Row 9 - Reference value 1
        self.C5 = True # Row 10 - Reference value 1
        
        # Profit Take Settings (rows 11-15 from Reference)
        self.ProfitTakeC1 = 20 # Row 11 - Slightly higher for better profits
        self.ProfitTakeC2 = 20 # Row 12 - Slightly higher for better profits
        self.ProfitTakeC3 = 20 # Row 13 - Slightly higher for better profits
        self.ProfitTakeC4 = 20 # Row 14 - Slightly higher for better profits
        self.ProfitTakeC5 = 20 # Row 15 - Lower for more realistic targets
        
        # Risk Management (rows 16-18 from Reference)
        self.StopLoss = 125 # Row 16 - Increased for more realistic stop distances
        self.SharesToSell = 100 # Row 17 - Reference value
        self.OffsetPCT = 0.1 # Row 18 - Balanced offset for good fills
        
        # Timing Constraints (rows 19-24 from Reference)
        # TUNED VALUES - Reduced for more frequent trading
        self.SameSymbolTime = 240 # Row 19 - Reference value
        self.SameConditionTimeC1 = 10 # Row 20 - Reduced for more trades
        self.SameConditionTimeC2 = 10 # Row 21 - Reference value
        self.SameConditionTimeC3 = 30 # Row 22 - Reference value
        self.SameConditionTimeC4 = 10 # Row 23 - Reference value
        self.SameConditionTimeC5 = 10 # Row 24 - Reference value
        
        # Stop Loss Update (row 36 from Reference)
        self.StopLossUpdate = 1 # Row 36 - Reference value (1=True)
        
        # Stop Loss X/Y Parameters (rows 37-46 from Reference)
        self.StopLossXC1 = 10 # Row 37 - Reference value
        self.StopLossYC1 = 50 # Row 38 - Reference value
        self.StopLossXC2 = 10 # Row 39 - Reference value
        self.StopLossYC2 = 50 # Row 40 - Reference value
        self.StopLossXC3 = 10 # Row 41 - Reference value
        self.StopLossYC3 = 50 # Row 42 - Reference value
        self.StopLossXC4 = 10 # Row 43 - Reference value
        self.StopLossYC4 = 50 # Row 44 - Reference value
        self.StopLossXC5 = 10 # Row 45 - Reference value
        self.StopLossYC5 = 50 # Row 46 - Reference value
        
        # Capital Management (row 52 from Reference)
        self.MaxCapitalPCT = 225 # Row 52 - Reference value
        
        # VWAP Settings (rows 53, 69 from Reference) - TUNED VALUES
        self.VWAP_PCT = 55 # Row 53 - Higher threshold for easier entries
        self.Vwap_Margin = 7 # Row 69 - Higher margin for more flexibility
        
        # Rally Conditions (rows 54-56, 66, 67 from Reference) - TUNED VALUES
        self.Rally_X_Min_PCT = 4 # Row 54 - Very low for easier rally detection
        self.Rally_X_Max_PCT = 20 # Row 55 - Much higher for wider rally range
        self.Rally_Y_PCT = 2 # Row 56 - Very low for easier rally detection
        self.Rally_Time_Constraint = 7 # Row 66 - Longer time window for rally (in MINUTES)
        self.Rally_Time_Constraint_Threshold = 1.3 # Row 67 - Rally threshold multiplier
        
        # Action Timing (rows 57-59 from Reference)
        self.Allow_Actions = True # Row 57 - Enabled to test action time functionality
        self.Action1_Time = 30 # Row 58 - 1 minute for breakeven adjustment
        self.Action2_Time = 150 # Row 59 - 3 minutes for force close
        
        # Market Hours (rows 60-61 from Reference) - FRONTEND CONFIGURABLE
        # These act as the actual guard times
        self.Algo_Off_Before = time(10, 57) # Row 60 - Algorithm start time (frontend configurable)
        self.Algo_Off_After = time(14, 0) # Row 61 - Algorithm end time (frontend configurable)
        
        # Daily Limits (row 62 from Reference)
        self.Max_Daily_PNL = 0.27 # Row 62 - Reference value
        
        # Advanced Settings (rows 68, 70-74 from Reference)
        self.New_Range_Order_Cancellation_Margin = 0.5 # Row 68 - Reference value
        self.RangeMultipleThreshold = 2.2 # Row 70 - Reference value
        self.Liquidity_Threshold = 0.011 # Row 71 - Reference value
        self.Gap_Threshold = 90 # Row 72 - Reference value
        self.SharpMovement_Threshold = 75 # Row 73 - Reference value
        self.SharpMovement_Minutes = 4 # Row 74 - Reference value
        
        # Port, Account, Cash (rows 75-77 from Reference)
        # self.Port = 9874                    # Row 75 - Not needed for QuantConnect
        # self.AccountId_1 = "DU3166840"      # Row 76 - Using account_id below
        self.cash_pct = 60 # Row 77 - Percentage of portfolio to use per position
        
        # Additional frontend parameters (keeping for compatibility)
        self.symbols = [
            'AAPL',
            'NVDA',
            'TSLA',
            'V',
            'AMZN',
            'META',
            'ABBV',
            'AMD',
            'GS',
            'HAL',
            'JNJ',
            'MCD',
            'OXY',
            'SHOP',
            'UBER'
        ]    # List of symbols to trade - comprehensive portfolio
        self.starting_cash = 500000 # Starting cash amount
        self.start_date = "2025-10-01" # Backtest start date
        self.end_date = "2025-10-10" # Backtest end date
        self.account_id = "DU3166840"       # Account ID for trading

        # Optional diagnostics
        self.Enable_Debug_Logging = False  # Toggle high-volume algorithm logging
        
        # REMOVED: _load_from_config() - Now uses ONLY hardcoded values from parameters.py
        # No more config.json override - browser and backtest both use the same source
        self._apply_env_override()
    
    def _load_from_config(self):
        """Load parameters from config.json if it exists"""
        try:
            # Look for config.json in various locations
            possible_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'configs', 'config.json'),
                '/LeanCLI/config.json'  # For backtest environment
            ]
            
            config_data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        config_data = json.load(f)
                    break
            
            if config_data:
                # Update parameters from config
                for key, value in config_data.items():
                    if hasattr(self, key):
                        # Handle time parameters
                        if key in ['Algo_Off_Before', 'Algo_Off_After'] and isinstance(value, str):
                            # Handle various time formats: "9:30", "09:30", etc.
                            try:
                                parts = value.strip().split(':')
                                if len(parts) == 2:
                                    # Remove any leading/trailing whitespace from parts
                                    hour_str = parts[0].strip()
                                    minute_str = parts[1].strip()
                                    
                                    # Parse hour and minute, handling empty strings and leading zeros
                                    hour = int(hour_str) if hour_str else 0
                                    minute = int(minute_str) if minute_str else 0
                                    
                                    # Validate ranges
                                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                                        value = time(hour, minute)
                                    else:
                                        print(f"Warning: Invalid time values for {key}: hour={hour}, minute={minute}")
                                        continue
                                else:
                                    print(f"Warning: Invalid time format for {key}: {value}")
                                    continue
                            except (ValueError, AttributeError) as e:
                                print(f"Warning: Error parsing time for {key}: {value} - {e}")
                                continue
                        setattr(self, key, value)
        except Exception as e:
            # Log the error for debugging but continue with defaults
            print(f"Warning: Error loading config parameters: {e}", file=sys.stderr)
            pass

    # ------------------------------------------------------------------
    # Test / automation helpers
    # ------------------------------------------------------------------
    def _apply_env_override(self):
        """Override parameter values using external module path if configured."""
        override_path = os.environ.get("BACKTEST_CONFIG_PATH")
        if not override_path:
            return

        try:
            resolved_override = Path(override_path).expanduser().resolve()
            current_file = Path(__file__).resolve()
        except Exception:
            resolved_override = Path(os.path.abspath(override_path))
            current_file = Path(os.path.abspath(__file__))

        if resolved_override == current_file:
            return

        try:
            override_instance = self._load_external_parameters(resolved_override)
        except Exception as exc:
            print(f"Warning: Failed to load BACKTEST_CONFIG_PATH override '{override_path}': {exc}", file=sys.stderr)
            return

        self._copy_public_attributes(override_instance)

    @staticmethod
    def _load_external_parameters(path: Path):
        """Load a TradingParameters instance from another Python module."""
        spec = importlib.util.spec_from_file_location("zacqc_parameters_override", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to create module spec for {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]

        if hasattr(module, "TradingParameters"):
            override_cls = getattr(module, "TradingParameters")
            override_instance = override_cls()
        elif hasattr(module, "parameters"):
            override_instance = getattr(module, "parameters")
        else:
            raise AttributeError(f"{path} must define TradingParameters or 'parameters'")

        return override_instance

    def _copy_public_attributes(self, override_instance):
        """Copy public, non-callable attributes from override instance onto self."""
        for attr in dir(override_instance):
            if attr.startswith("_"):
                continue

            value = getattr(override_instance, attr)
            if callable(value):
                continue

            setattr(self, attr, value)
    
    def update_parameter(self, param_name, value):
        """
        Dynamically update a parameter
        Usage: params.update_parameter('Parameter_1', 150)
        """
        if hasattr(self, param_name):
            setattr(self, param_name, value)
            return True
        return False
    
    def get_condition_profit_take(self, condition):
        """Get profit take percentage for a condition"""
        profit_map = {
            'cond1': self.ProfitTakeC1,
            'cond2': self.ProfitTakeC2,
            'cond3': self.ProfitTakeC3,
            'cond4': self.ProfitTakeC4,
            'cond5': self.ProfitTakeC5
        }
        return profit_map.get(condition, self.ProfitTakeC1)
    
    def get_condition_cooldown(self, condition):
        """Get cooldown time for a condition"""
        cooldown_map = {
            'cond1': self.SameConditionTimeC1,
            'cond2': self.SameConditionTimeC2,
            'cond3': self.SameConditionTimeC3,
            'cond4': self.SameConditionTimeC4,
            'cond5': self.SameConditionTimeC5
        }
        return cooldown_map.get(condition, 60)
    
    
    def get_stop_loss_parameters(self, condition):
        """Get stop loss X and Y parameters for a condition"""
        stop_loss_map = {
            'cond1': (self.StopLossXC1, self.StopLossYC1),
            'cond2': (self.StopLossXC2, self.StopLossYC2),
            'cond3': (self.StopLossXC3, self.StopLossYC3),
            'cond4': (self.StopLossXC4, self.StopLossYC4),
            'cond5': (self.StopLossXC5, self.StopLossYC5)
        }
        return stop_loss_map.get(condition, (10.0, 80.0))
    
    def validate_parameters(self):
        """Validate parameter values are within reasonable ranges"""
        errors = []
        
        # Check percentages are positive
        percent_params = ['ProfitTakeC1', 'ProfitTakeC2', 'ProfitTakeC3', 'ProfitTakeC4', 'ProfitTakeC5', 
                         'StopLoss', 'SharesToSell', 'MaxCapitalPCT', 'Max_Daily_PNL']
        for param in percent_params:
            if getattr(self, param) <= 0:
                errors.append(f"{param} must be positive")
        
        # Check time parameters are positive
        time_params = ['SameSymbolTime', 'SameConditionTimeC1', 'SameConditionTimeC2', 
                      'SameConditionTimeC3', 'SameConditionTimeC4', 'SameConditionTimeC5']
        for param in time_params:
            if getattr(self, param) <= 0:
                errors.append(f"{param} must be positive")
        
        # Check symbols list is not empty
        if not self.symbols:
            errors.append("At least one symbol must be configured")
        
        return errors
    
    def __str__(self):
        """String representation of parameters"""
        return f"TradingParameters(symbols={len(self.symbols)}, C1={self.C1}, C2={self.C2}, C3={self.C3}, C4={self.C4}, C5={self.C5})"
