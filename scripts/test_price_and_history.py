#!/usr/bin/env python3
"""
Test script for price feed and balance history features
Tests the complete flow: balances → prices → history
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"
USER_ID = "charles_test_user"

def print_section(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test API health"""
    print_section("1. Testing API Health")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.status_code == 200

def test_clear_cache():
    """Clear balance cache"""
    print_section("2. Clearing Balance Cache")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/balances/clear-cache",
        json={"user_id": USER_ID}
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_fetch_balances():
    """Fetch balances with prices"""
    print_section("3. Fetching Balances (with prices)")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/balances",
        params={
            "user_id": USER_ID,
            "force_refresh": "true"
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Summary
        print(f"\n✅ Balance fetch successful!")
        print(f"Total USD: ${data.get('total_usd', 0):,.2f}")
        print(f"Total BRL: R${data.get('total_brl', 0):,.2f}")
        print(f"USD/BRL Rate: {data.get('usd_brl_rate', 0):.4f}")
        print(f"Unique Tokens: {data.get('total_unique_tokens', 0)}")
        print(f"Fetch Time: {data.get('fetch_time', 0):.3f}s")
        
        # Token details
        print("\n📊 Token Summary:")
        tokens = data.get('tokens_summary', {})
        for token, info in tokens.items():
            amount = info.get('total', 0)
            price = info.get('price_usd', 0)
            value_usd = info.get('value_usd', 0)
            value_brl = info.get('value_brl', 0)
            
            print(f"\n  {token}:")
            print(f"    Amount: {amount:.8f}")
            print(f"    Price USD: ${price:.6f}")
            print(f"    Value USD: ${value_usd:.2f}")
            print(f"    Value BRL: R${value_brl:.2f}")
        
        # Exchange breakdown
        print("\n🏦 Exchange Breakdown:")
        for exchange in data.get('exchanges', []):
            print(f"\n  {exchange['exchange_name']}:")
            print(f"    Success: {exchange['success']}")
            print(f"    Total USD: ${exchange.get('total_usd', 0):.2f}")
            print(f"    Total BRL: R${exchange.get('total_brl', 0):.2f}")
        
        # Price metadata
        if 'prices_updated_at' in data:
            print(f"\n⏱️  Prices Updated: {data['prices_updated_at']}")
        
        return True
    else:
        print("❌ Error fetching balances")
        print(json.dumps(response.json(), indent=2))
        return False

def test_latest_snapshot():
    """Get latest balance snapshot"""
    print_section("4. Getting Latest Balance Snapshot")
    
    # Wait a moment to ensure snapshot was saved
    time.sleep(1)
    
    response = requests.get(
        f"{BASE_URL}/api/v1/balances/history/latest",
        params={"user_id": USER_ID}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        snapshot = data.get('snapshot', {})
        
        print(f"\n✅ Latest snapshot found!")
        print(f"Timestamp: {snapshot.get('timestamp', 'N/A')}")
        print(f"Total USD: ${snapshot.get('total_usd', 0):,.2f}")
        print(f"Total BRL: R${snapshot.get('total_brl', 0):,.2f}")
        print(f"Unique Tokens: {snapshot.get('total_unique_tokens', 0)}")
        print(f"Exchanges: {snapshot.get('total_exchanges', 0)}")
        
        return True
    else:
        print("❌ Error getting snapshot")
        print(json.dumps(response.json(), indent=2))
        return False

def test_balance_history():
    """Get balance history"""
    print_section("5. Getting Balance History")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/balances/history",
        params={
            "user_id": USER_ID,
            "limit": 10
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        snapshots = data.get('snapshots', [])
        
        print(f"\n✅ Found {len(snapshots)} historical snapshots")
        
        for i, snapshot in enumerate(snapshots[:3], 1):
            print(f"\nSnapshot {i}:")
            print(f"  Timestamp: {snapshot.get('timestamp', 'N/A')}")
            print(f"  Total USD: ${snapshot.get('total_usd', 0):,.2f}")
            print(f"  Total BRL: R${snapshot.get('total_brl', 0):,.2f}")
        
        return True
    else:
        print("❌ Error getting history")
        print(json.dumps(response.json(), indent=2))
        return False

def test_token_history():
    """Get history for specific token"""
    print_section("6. Getting Token History (USDT)")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/balances/history/token/USDT",
        params={
            "user_id": USER_ID,
            "limit": 5
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        history = data.get('history', [])
        
        print(f"\n✅ Found {len(history)} USDT snapshots")
        
        for i, record in enumerate(history[:3], 1):
            print(f"\nRecord {i}:")
            print(f"  Timestamp: {record.get('timestamp', 'N/A')}")
            print(f"  Amount: {record.get('amount', 0):.8f} USDT")
            print(f"  Price: ${record.get('price_usd', 0):.6f}")
            print(f"  Value USD: ${record.get('value_usd', 0):.2f}")
        
        return True
    else:
        print("❌ Error getting token history")
        print(json.dumps(response.json(), indent=2))
        return False

def test_portfolio_evolution():
    """Get portfolio evolution"""
    print_section("7. Getting Portfolio Evolution (30 days)")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/balances/history/evolution",
        params={
            "user_id": USER_ID,
            "days": 30
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        evolution = data.get('evolution', {})
        summary = evolution.get('summary', {})
        
        if summary:
            print(f"\n✅ Portfolio Evolution Summary:")
            print(f"Period: {summary.get('period_days', 0)} days")
            print(f"Data Points: {summary.get('data_points', 0)}")
            print(f"Start Value: ${summary.get('start_value_usd', 0):,.2f}")
            print(f"End Value: ${summary.get('end_value_usd', 0):,.2f}")
            print(f"Change: ${summary.get('change_usd', 0):,.2f} ({summary.get('change_percent', 0):.2f}%)")
            print(f"Min Value: ${summary.get('min_value_usd', 0):,.2f}")
            print(f"Max Value: ${summary.get('max_value_usd', 0):,.2f}")
        else:
            print("ℹ️  No historical data yet (need more snapshots)")
        
        return True
    else:
        print("❌ Error getting evolution")
        print(json.dumps(response.json(), indent=2))
        return False

def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*58)
    print("  PRICE FEED & BALANCE HISTORY TEST SUITE")
    print("="*60)
    print(f"Testing with user: {USER_ID}")
    print(f"Base URL: {BASE_URL}")
    
    results = []
    
    # Run tests
    try:
        results.append(("API Health", test_health()))
        test_clear_cache()
        results.append(("Fetch Balances with Prices", test_fetch_balances()))
        results.append(("Latest Snapshot", test_latest_snapshot()))
        results.append(("Balance History", test_balance_history()))
        results.append(("Token History", test_token_history()))
        results.append(("Portfolio Evolution", test_portfolio_evolution()))
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API")
        print("Make sure the server is running on port 5000")
        return
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")

if __name__ == '__main__':
    main()
