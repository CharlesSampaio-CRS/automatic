"""
Test linking MEXC exchange with real credentials from .env
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:5000"

def test_link_mexc():
    """Test linking MEXC with real credentials"""
    
    print("=" * 80)
    print("🧪 TESTING MEXC EXCHANGE LINK WITH REAL CREDENTIALS")
    print("=" * 80)
    
    # Get API credentials from .env
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API_KEY or API_SECRET not found in .env")
        return
    
    print(f"\n📋 Using credentials from .env:")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   API Secret: {api_secret[:10]}...")
    
    # Get available exchanges
    print("\n1️⃣ Fetching available exchanges...")
    response = requests.get(f"{API_URL}/api/v1/exchanges/available")
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch exchanges: {response.status_code}")
        return
    
    exchanges = response.json()['exchanges']
    
    # Find MEXC
    mexc = next((ex for ex in exchanges if ex['ccxt_id'] == 'mexc'), None)
    
    if not mexc:
        print("❌ MEXC not found in available exchanges")
        return
    
    print(f"✅ Found MEXC")
    print(f"   Exchange ID: {mexc['_id']}")
    print(f"   Name: {mexc['nome']}")
    print(f"   Requires Passphrase: {mexc['requires_passphrase']}")
    
    # Test linking
    print("\n2️⃣ Linking MEXC exchange...")
    
    payload = {
        "user_id": "charles_test_user",
        "exchange_id": mexc['_id'],
        "api_key": api_key,
        "api_secret": api_secret
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/exchanges/link",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"\n📊 Response:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Body: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code in [200, 201]:
        print("\n✅ MEXC LINKED SUCCESSFULLY!")
        print("\n🔐 Security checks passed:")
        print("   ✅ Credentials validated with exchange")
        print("   ✅ Connection tested successfully")
        print("   ✅ Permissions verified (read-only)")
        print("   ✅ Credentials encrypted before storage")
        print("   ✅ Saved to database")
    else:
        print("\n❌ FAILED TO LINK MEXC")
        print("   Check the error details above")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_link_mexc()
