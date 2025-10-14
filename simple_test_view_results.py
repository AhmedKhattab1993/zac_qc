#!/usr/bin/env python3
"""
Simple test for View Results functionality
Tests the UI without conflicting with existing server
"""

import requests
import time
import sys

def test_view_results_functionality():
    """Test that View Results works after backtest completion"""
    base_url = 'http://localhost:5001/api'  # Use existing server on port 5001
    
    print("🧪 Testing View Results functionality...")
    
    try:
        # Step 1: Check if server is running
        print("📡 Step 1: Checking server connection...")
        response = requests.get(f'{base_url}/backtest/status', timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding: {response.status_code}")
            return False
        
        status = response.json()
        print(f"✅ Server connected. Current status: {status['status']}")
        
        # Step 2: Start a backtest if idle
        if status['status'] == 'idle':
            print("🏁 Step 2: Starting backtest...")
            response = requests.post(f'{base_url}/backtest/start', json={})
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Backtest started: {result}")
            else:
                print(f"❌ Failed to start backtest: {response.status_code}")
                return False
        
        # Step 3: Monitor until completion
        print("⏱️ Step 3: Monitoring backtest progress...")
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(f'{base_url}/backtest/status')
            status = response.json()
            current_status = status['status']
            
            elapsed = time.time() - start_time
            print(f"Status: {current_status} (elapsed: {elapsed:.1f}s)")
            
            if current_status == 'completed':
                print("🎉 Backtest completed!")
                break
            elif current_status == 'error':
                print("❌ Backtest failed")
                return False
            
            time.sleep(5)
        else:
            print("⏰ Timeout waiting for completion")
            return False
        
        # Step 4: Test results endpoint
        print("📊 Step 4: Testing results endpoint...")
        response = requests.get(f'{base_url}/backtest/results')
        
        if response.status_code == 200:
            results = response.json()
            print("✅ Results endpoint working!")
            
            # Check results structure
            if 'Statistics' in results:
                stats = results['Statistics']
                print(f"📈 Found statistics:")
                print(f"   - Net Profit: {stats.get('Net Profit', 'N/A')}")
                print(f"   - Total Orders: {stats.get('Total Orders', 'N/A')}")
                print(f"   - Win Rate: {stats.get('Win Rate', 'N/A')}")
                print(f"   - Sharpe Ratio: {stats.get('Sharpe Ratio', 'N/A')}")
            
            if 'Charts' in results:
                print("📈 Chart data available")
            
            return True
        else:
            print(f"❌ Results endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running on port 5001")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main test execution"""
    print("🧪 Simple View Results Test")
    print("=" * 40)
    
    success = test_view_results_functionality()
    
    if success:
        print("\n🎉 TEST PASSED!")
        print("✅ View Results functionality is working")
        print("💡 You can now:")
        print("   1. Run a backtest")
        print("   2. Wait for completion")
        print("   3. Click 'View Results' button")
        print("   4. See results displayed")
    else:
        print("\n❌ TEST FAILED!")
        print("💡 Check the server and try again")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)