#!/usr/bin/env python3
"""
Cost Calculation Validation Test
Validates that the GoQuant Trade Simulator returns correct cost estimates.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "https://trade-simulator-production.up.railway.app"

def test_cost_calculation(trade_size: float, order_type: str, side: str, time_horizon: float = 300.0) -> Dict[str, Any]:
    """Test cost calculation for given parameters."""
    
    payload = {
        "trade_size": trade_size,
        "order_type": order_type,
        "side": side,
        "time_horizon": time_horizon
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/estimate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            cost_breakdown = data.get("cost_breakdown", {})
            current_price = data.get("current_price", 50000)
            
            # Calculate expected values for validation
            notional_value = trade_size * current_price
            
            # Expected rates
            if order_type == "limit":
                expected_fee_rate = 0.0002  # 2 bps
            else:
                expected_fee_rate = 0.0005  # 5 bps
                
            expected_slippage_rate = 0.0002  # 2 bps base
            if time_horizon < 60:
                expected_slippage_rate *= 2
            if trade_size > 1.0:
                expected_slippage_rate *= (1 + (trade_size - 1) * 0.1)
                
            expected_impact_rate = 0.0001  # 1 bp base
            if trade_size > 0.5:
                expected_impact_rate *= (1 + (trade_size - 0.5) * 0.2)
            
            # Expected costs
            expected_fee = notional_value * expected_fee_rate
            expected_slippage = notional_value * expected_slippage_rate
            expected_impact = notional_value * expected_impact_rate
            expected_total = expected_fee + expected_slippage + expected_impact
            expected_bps = (expected_total / notional_value) * 10000
            
            # Actual costs
            actual_fee = cost_breakdown.get("exchange_fee", 0)
            actual_slippage = cost_breakdown.get("slippage_cost", 0)
            actual_impact = cost_breakdown.get("market_impact", 0)
            actual_total = cost_breakdown.get("total_cost", 0)
            actual_bps = cost_breakdown.get("cost_bps", 0)
            
            # Validation (allow 1% tolerance for rounding)
            tolerance = 0.01
            
            def is_close(actual, expected, tolerance=tolerance):
                return abs(actual - expected) / max(expected, 0.01) <= tolerance
            
            validation = {
                "fee_valid": is_close(actual_fee, expected_fee),
                "slippage_valid": is_close(actual_slippage, expected_slippage),
                "impact_valid": is_close(actual_impact, expected_impact),
                "total_valid": is_close(actual_total, expected_total),
                "bps_valid": is_close(actual_bps, expected_bps)
            }
            
            return {
                "success": True,
                "trade_size": trade_size,
                "order_type": order_type,
                "current_price": current_price,
                "notional_value": notional_value,
                "expected": {
                    "fee": expected_fee,
                    "slippage": expected_slippage,
                    "impact": expected_impact,
                    "total": expected_total,
                    "bps": expected_bps
                },
                "actual": {
                    "fee": actual_fee,
                    "slippage": actual_slippage,
                    "impact": actual_impact,
                    "total": actual_total,
                    "bps": actual_bps
                },
                "validation": validation,
                "all_valid": all(validation.values())
            }
            
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Run comprehensive cost calculation tests."""
    print("🧮 GoQuant Trade Simulator - Cost Calculation Validation")
    print("=" * 60)
    
    test_cases = [
        # Test case: (trade_size, order_type, side, time_horizon)
        (1.0, "market", "buy", 60.0),      # Standard market order
        (0.1, "limit", "buy", 300.0),     # Small limit order
        (2.5, "market", "sell", 30.0),    # Large urgent market order
        (5.0, "limit", "sell", 600.0),    # Large patient limit order
        (0.01, "market", "buy", 120.0),   # Very small market order
        (10.0, "limit", "buy", 900.0),    # Very large limit order
    ]
    
    all_passed = True
    
    for i, (trade_size, order_type, side, time_horizon) in enumerate(test_cases, 1):
        print(f"\n📊 Test Case {i}: {trade_size} BTC {order_type} {side} ({time_horizon}s)")
        print("-" * 50)
        
        result = test_cost_calculation(trade_size, order_type, side, time_horizon)
        
        if result["success"]:
            if result["all_valid"]:
                print(f"✅ PASSED - All calculations correct")
                print(f"   💰 Total Cost: ${result['actual']['total']:.2f} ({result['actual']['bps']:.1f} bps)")
                print(f"   📈 Notional: ${result['notional_value']:,.2f}")
            else:
                print(f"❌ FAILED - Calculation errors detected")
                all_passed = False
                
                for component, valid in result["validation"].items():
                    if not valid:
                        expected = result["expected"][component.split("_")[0]]
                        actual = result["actual"][component.split("_")[0]]
                        print(f"   ⚠️  {component}: Expected {expected:.2f}, Got {actual:.2f}")
        else:
            print(f"❌ FAILED - {result['error']}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Cost calculations are correct!")
        print("\n📋 Summary:")
        print("   ✅ Exchange fees calculated properly (based on notional value)")
        print("   ✅ Slippage costs scale with trade size and urgency")
        print("   ✅ Market impact increases with trade size")
        print("   ✅ Basis points calculations are accurate")
        print("   ✅ Total costs sum correctly")
    else:
        print("💥 SOME TESTS FAILED - Please review the calculations")
    
    print(f"\n🔗 Live Application: {BASE_URL}")

if __name__ == "__main__":
    main()
