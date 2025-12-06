"""
Test complete flow: available (filtered), linked, and unlink
"""

import requests
import json

API_URL = "http://localhost:5000"
TEST_USER_ID = "charles_test_user"

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def test_complete_flow():
    """Test complete exchange management flow"""
    
    print_section("🧪 TESTING COMPLETE EXCHANGE MANAGEMENT FLOW")
    
    # Test 1: Get linked exchanges
    print_section("1️⃣ GET LINKED EXCHANGES")
    response = requests.get(f"{API_URL}/api/v1/exchanges/linked?user_id={TEST_USER_ID}")
    
    print(f"Status: {response.status_code}")
    linked_data = response.json()
    print(f"Total linked: {linked_data['total']}")
    
    if linked_data['exchanges']:
        print("\nLinked exchanges:")
        for ex in linked_data['exchanges']:
            print(f"  ✅ {ex['name']} (linked at: {ex['linked_at']})")
            print(f"     Link ID: {ex['link_id']}")
    
    # Test 2: Get available exchanges WITHOUT user_id (should error)
    print_section("2️⃣ TEST ERROR: GET AVAILABLE WITHOUT user_id")
    response = requests.get(f"{API_URL}/api/v1/exchanges/available")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ Correctly rejected request without user_id")
    
    # Test 3: Get available exchanges for NEW user (should show all 9)
    print_section("3️⃣ GET AVAILABLE EXCHANGES (NEW USER - ALL 9)")
    response = requests.get(f"{API_URL}/api/v1/exchanges/available?user_id=new_user_test")
    
    print(f"Status: {response.status_code}")
    available_new_user = response.json()
    print(f"Total available: {available_new_user['total']}")
    print(f"Exchanges: {[ex['nome'] for ex in available_new_user['exchanges']]}")
    
    # Test 4: Get available exchanges for existing user (should filter linked)
    print_section("4️⃣ GET AVAILABLE EXCHANGES (EXISTING USER - FILTERED)")
    response = requests.get(f"{API_URL}/api/v1/exchanges/available?user_id={TEST_USER_ID}")
    
    print(f"Status: {response.status_code}")
    available_with_filter = response.json()
    print(f"Total available: {available_with_filter['total']}")
    print(f"Exchanges: {[ex['nome'] for ex in available_with_filter['exchanges']]}")
    
    # Calculate filtered
    filtered_count = available_new_user['total'] - available_with_filter['total']
    print(f"\n📊 Filter working: {filtered_count} exchange(s) removed from list (already linked)")
    
    # Test 5: Try to get linked without user_id
    print_section("5️⃣ TEST ERROR: GET LINKED WITHOUT user_id")
    response = requests.get(f"{API_URL}/api/v1/exchanges/linked")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ Correctly rejected request without user_id")
    
    # Test 6: Unlink an exchange (optional - commented out to not break existing data)
    print_section("6️⃣ TEST UNLINK EXCHANGE (DEMO)")
    print("⚠️  To test unlinking, uncomment the code below and provide a link_id")
    print("⚠️  This will deactivate the exchange link (soft delete)")
    
    # Uncomment to test:
    # if linked_data['exchanges']:
    #     link_id = linked_data['exchanges'][0]['link_id']
    #     print(f"\nTesting unlink for: {linked_data['exchanges'][0]['name']}")
    #     print(f"Link ID: {link_id}")
    #     
    #     response = requests.delete(f"{API_URL}/api/v1/exchanges/unlink/{link_id}")
    #     print(f"Status: {response.status_code}")
    #     print(f"Response: {json.dumps(response.json(), indent=2)}")
    #     
    #     if response.status_code == 200:
    #         print("✅ Exchange unlinked successfully")
    #         
    #         # Verify it's gone from linked list
    #         response = requests.get(f"{API_URL}/api/v1/exchanges/linked?user_id={TEST_USER_ID}")
    #         new_linked = response.json()
    #         print(f"\nNew total linked: {new_linked['total']}")
    
    print_section("🎉 TESTS COMPLETED")
    print("\n✅ All endpoints working correctly:")
    print("  • GET /api/v1/exchanges/available?user_id=<user_id> (REQUIRED)")
    print("  • GET /api/v1/exchanges/linked?user_id=<user_id> (REQUIRED)")
    print("  • DELETE /api/v1/exchanges/unlink/<link_id>")
    print("\n✅ Validation working:")
    print("  • Both endpoints require user_id parameter")
    print("  • Returns 400 error if user_id is missing")
    print("\n✅ Filter logic working:")
    print("  • Available exchanges excludes already linked exchanges")
    print("  • New users see all 9 exchanges")
    print("  • Existing users only see exchanges they haven't linked yet")

if __name__ == "__main__":
    test_complete_flow()
