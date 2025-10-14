#!/usr/bin/env python3
"""
Sync parameters.py values to config.json for browser interface
"""

import sys
import os
import json

# Add ZacQC to path to import parameters
sys.path.append('ZacQC')
from config.parameters import TradingParameters

def sync_config():
    """Sync parameters.py to config.json"""
    
    # Load current parameters
    params = TradingParameters()
    
    # Create config dict with all parameters
    config = {
        # Core Trading Parameters
        "Parameter_1": params.Parameter_1,
        "Parameter_2": params.Parameter_2, 
        "Parameter_3": params.Parameter_3,
        "Parameter_4": params.Parameter_4,
        "Parameter_5": params.Parameter_5,
        
        # Condition Enablement
        "C1": params.C1,
        "C2": params.C2,
        "C3": params.C3,
        "C4": params.C4,
        "C5": params.C5,
        
        # Profit Take Settings
        "ProfitTakeC1": params.ProfitTakeC1,
        "ProfitTakeC2": params.ProfitTakeC2,
        "ProfitTakeC3": params.ProfitTakeC3,
        "ProfitTakeC4": params.ProfitTakeC4,
        "ProfitTakeC5": params.ProfitTakeC5,
        
        # Risk Management
        "StopLoss": params.StopLoss,
        "SharesToSell": params.SharesToSell,
        "OffsetPCT": params.OffsetPCT,
        
        # Timing Constraints
        "SameSymbolTime": params.SameSymbolTime,
        "SameConditionTimeC1": params.SameConditionTimeC1,
        "SameConditionTimeC2": params.SameConditionTimeC2,
        "SameConditionTimeC3": params.SameConditionTimeC3,
        "SameConditionTimeC4": params.SameConditionTimeC4,
        "SameConditionTimeC5": params.SameConditionTimeC5,
        
        # Stop Loss Update
        "StopLossUpdate": params.StopLossUpdate,
        
        # Stop Loss X/Y Parameters
        "StopLossXC1": params.StopLossXC1,
        "StopLossYC1": params.StopLossYC1,
        "StopLossXC2": params.StopLossXC2,
        "StopLossYC2": params.StopLossYC2,
        "StopLossXC3": params.StopLossXC3,
        "StopLossYC3": params.StopLossYC3,
        "StopLossXC4": params.StopLossXC4,
        "StopLossYC4": params.StopLossYC4,
        "StopLossXC5": params.StopLossXC5,
        "StopLossYC5": params.StopLossYC5,
        
        # Capital Management
        "cash_pct": params.cash_pct,
        "MaxCapitalPCT": params.MaxCapitalPCT,
        
        # VWAP Settings
        "VWAP_PCT": params.VWAP_PCT,
        "Vwap_Margin": params.Vwap_Margin,
        
        # Rally Conditions
        "Rally_X_Min_PCT": params.Rally_X_Min_PCT,
        "Rally_X_Max_PCT": params.Rally_X_Max_PCT,
        "Rally_Y_PCT": params.Rally_Y_PCT,
        "Rally_Time_Constraint": params.Rally_Time_Constraint,
        "Rally_Time_Constraint_Threshold": params.Rally_Time_Constraint_Threshold,
        
        # Action Timing
        "Allow_Actions": params.Allow_Actions,
        "Action1_Time": params.Action1_Time,
        "Action2_Time": params.Action2_Time,
        
        # Market Hours
        "Algo_Off_Before": params.Algo_Off_Before.strftime("%H:%M"),
        "Algo_Off_After": params.Algo_Off_After.strftime("%H:%M"),
        
        # Daily Limits
        "Max_Daily_PNL": params.Max_Daily_PNL,
        
        # Advanced Settings
        "New_Range_Order_Cancellation_Margin": params.New_Range_Order_Cancellation_Margin,
        "RangeMultipleThreshold": params.RangeMultipleThreshold,
        "Liquidity_Threshold": params.Liquidity_Threshold,
        "Gap_Threshold": params.Gap_Threshold,
        "SharpMovement_Threshold": params.SharpMovement_Threshold,
        "SharpMovement_Minutes": params.SharpMovement_Minutes,
        
        # Frontend parameters
        "symbols": params.symbols,
        "starting_cash": params.starting_cash,
        "start_date": params.start_date,
        "end_date": params.end_date,
        "account_id": params.account_id
    }
    
    # Write to config.json
    config_path = "configs/config.json"
    os.makedirs("configs", exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Synced parameters.py to {config_path}")
    print(f"Key values: Parameter_1={config['Parameter_1']}, StopLoss={config['StopLoss']}, Allow_Actions={config['Allow_Actions']}")

if __name__ == "__main__":
    sync_config()