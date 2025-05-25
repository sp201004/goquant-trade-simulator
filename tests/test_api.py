#!/usr/bin/env python3
"""
Test suite for GoQuant Trade Simulator API endpoints.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Server configuration
BASE_URL = "http://localhost:8080"

def test_health_endpoint():
    """Test the health check endpoint."""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Health endpoint: PASSED")
                return True
            else:
                print(f"❌ Health endpoint: Unexpected response - {data}")
                return False
        else:
            print(f"❌ Health endpoint: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint: Connection failed - {e}")
        return False

def test_status_endpoint():
    """Test the status endpoint."""
    print("🔍 Testing status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            required_fields = ["is_running", "trade_count", "market"]
            if all(field in data for field in required_fields):
                print("✅ Status endpoint: PASSED")
                print(f"   📊 Status: {data['is_running']}, Trades: {data['trade_count']}")
                return True
            else:
                print(f"❌ Status endpoint: Missing fields - {data}")
                return False
        else:
            print(f"❌ Status endpoint: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status endpoint: Connection failed - {e}")
        return False

def test_estimate_endpoint():
    """Test the trade cost estimation endpoint."""
    print("🔍 Testing estimate endpoint...")
    
    test_cases = [
        {
            "name": "Small Market Order",
            "data": {
                "trade_size": 0.1,
                "order_type": "market",
                "side": "buy",
                "time_horizon": 60.0
            }
        },
        {
            "name": "Large Limit Order",
            "data": {
                "trade_size": 10.0,
                "order_type": "limit",
                "side": "sell",
                "limit_price": 50000.0,
                "time_horizon": 600.0
            }
        }
    ]
    
    passed = 0
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/estimate",
                json=test_case["data"],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = [
                    "cost_breakdown", "probabilities", "market_conditions",
                    "current_price", "optimal_strategy"
                ]
                
                if all(field in data for field in required_fields):
                    cost = data["cost_breakdown"].get("total_cost", 0)
                    print(f"✅ {test_case['name']}: PASSED (Cost: ${cost:.2f})")
                    passed += 1
                else:
                    print(f"❌ {test_case['name']}: Missing response fields")
            else:
                print(f"❌ {test_case['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {test_case['name']}: Failed - {e}")
    
    if passed == len(test_cases):
        print("✅ Estimate endpoint: ALL TESTS PASSED")
        return True
    else:
        print(f"❌ Estimate endpoint: {passed}/{len(test_cases)} tests passed")
        return False

def test_web_interface():
    """Test that the web interface loads."""
    print("🔍 Testing web interface...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200 and "GoQuant" in response.text:
            print("✅ Web interface: PASSED")
            return True
        else:
            print(f"❌ Web interface: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web interface: Connection failed - {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Starting GoQuant Trade Simulator API Tests\n")
    
    tests = [
        ("Server Health", test_health_endpoint),
        ("API Status", test_status_endpoint),
        ("Trade Estimation", test_estimate_endpoint),
        ("Web Interface", test_web_interface)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print('='*50)
        
        if test_func():
            passed += 1
        
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print('='*50)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! GoQuant is working perfectly.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Please check the server status.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode - just health and status
        print("🏃 Quick test mode")
        health_ok = test_health_endpoint()
        status_ok = test_status_endpoint()
        if health_ok and status_ok:
            print("✅ Quick test: Server is running!")
        else:
            print("❌ Quick test: Server issues detected")
    else:
        # Full test suite
        run_all_tests()
