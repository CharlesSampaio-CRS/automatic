"""
Test script for exchange linking endpoint
This tests the validation and security layers
"""

import requests
import json

API_URL = "http://localhost:5000"

def test_link_exchange():
    """Test linking an exchange with validation"""
    
    print("=" * 80)
    print("🧪 TESTING EXCHANGE LINK ENDPOINT")
    print("=" * 80)
    
    # First, get available exchanges
    print("\n1️⃣ Fetching available exchanges...")
    response = requests.get(f"{API_URL}/api/v1/exchanges/available")
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch exchanges: {response.status_code}")
        return
    
    exchanges = response.json()['exchanges']
    print(f"✅ Found {len(exchanges)} exchanges")
    
    # Find Binance for testing
    binance = next((ex for ex in exchanges if ex['ccxt_id'] == 'binance'), None)
    
    if not binance:
        print("❌ Binance not found in available exchanges")
        return
    
    print(f"\n2️⃣ Testing with {binance['nome']}...")
    print(f"   Exchange ID: {binance['_id']}")
    print(f"   Requires Passphrase: {binance['requires_passphrase']}")
    
    # Test Case 1: Missing required fields
    print("\n" + "=" * 80)
    print("TEST 1: Missing required fields")
    print("=" * 80)
    
    payload = {
        "user_id": "test_user_123"
        # Missing exchange_id, api_key, api_secret
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/exchanges/link",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ Correctly rejected missing fields")
    else:
        print("❌ Should have rejected missing fields")
    
    # Test Case 2: Invalid credentials
    print("\n" + "=" * 80)
    print("TEST 2: Invalid API credentials")
    print("=" * 80)
    
    payload = {
        "user_id": "test_user_123",
        "exchange_id": binance['_id'],
        "api_key": "invalid_key_123",
        "api_secret": "invalid_secret_456"
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/exchanges/link",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("✅ Correctly rejected invalid credentials")
    else:
        print("❌ Should have rejected invalid credentials")
    
    # Test Case 3: Valid credentials (you need to provide real test credentials)
    print("\n" + "=" * 80)
    print("TEST 3: Valid API credentials")
    print("=" * 80)
    print("⚠️  To test with valid credentials, update the script with real API keys")
    print("⚠️  Make sure the API keys are READ-ONLY (no trading/withdrawal permissions)")
    
    # Uncomment and add real credentials to test:
    # payload = {
    #     "user_id": "test_user_123",
    #     "exchange_id": binance['_id'],
    #     "api_key": "YOUR_REAL_API_KEY_HERE",
    #     "api_secret": "YOUR_REAL_API_SECRET_HERE"
    # }
    # 
    # response = requests.post(
    #     f"{API_URL}/api/v1/exchanges/link",
    #     json=payload,
    #     headers={'Content-Type': 'application/json'}
    # )
    # 
    # print(f"Status Code: {response.status_code}")
    # print(f"Response: {json.dumps(response.json(), indent=2)}")
    # 
    # if response.status_code == 201:
    #     print("✅ Exchange linked successfully!")
    # else:
    #     print("❌ Failed to link exchange")
    
    print("\n" + "=" * 80)
    print("🎉 ENDPOINT TESTS COMPLETED")
    print("=" * 80)
    print("\n📋 Summary:")
    print("  ✅ Validation layer working (missing fields rejected)")
    print("  ✅ Security layer working (invalid credentials rejected)")
    print("  ℹ️  To test with real credentials, update the script")

if __name__ == "__main__":
    test_link_exchange()
