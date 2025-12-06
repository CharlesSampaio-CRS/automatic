"""
Test script for encryption service
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.security.encryption import get_encryption_service

def test_encryption():
    """Test encryption and decryption"""
    try:
        print("🔐 Testing Encryption Service\n")
        print("=" * 80)
        
        # Get service
        service = get_encryption_service()
        print("✅ Encryption service initialized successfully")
        
        # Test simple encryption/decryption
        print("\n📝 Test 1: Simple string encryption")
        original = "my_secret_api_key_12345"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        
        print(f"  Original:  {original}")
        print(f"  Encrypted: {encrypted}")
        print(f"  Decrypted: {decrypted}")
        
        assert original == decrypted, "Decryption failed!"
        print("  ✅ Simple encryption/decryption works!")
        
        # Test credentials encryption
        print("\n📝 Test 2: Exchange credentials encryption")
        api_key = "test_api_key_abc123"
        api_secret = "test_api_secret_xyz789"
        passphrase = "test_passphrase"
        
        encrypted_creds = service.encrypt_credentials(api_key, api_secret, passphrase)
        print(f"  Original API Key:    {api_key}")
        print(f"  Encrypted API Key:   {encrypted_creds['api_key'][:50]}...")
        print(f"  Original Secret:     {api_secret}")
        print(f"  Encrypted Secret:    {encrypted_creds['api_secret'][:50]}...")
        print(f"  Original Passphrase: {passphrase}")
        print(f"  Encrypted Passphrase: {encrypted_creds['passphrase'][:50]}...")
        
        decrypted_creds = service.decrypt_credentials(encrypted_creds)
        print(f"\n  Decrypted API Key:    {decrypted_creds['api_key']}")
        print(f"  Decrypted Secret:     {decrypted_creds['api_secret']}")
        print(f"  Decrypted Passphrase: {decrypted_creds['passphrase']}")
        
        assert decrypted_creds['api_key'] == api_key, "API key decryption failed!"
        assert decrypted_creds['api_secret'] == api_secret, "API secret decryption failed!"
        assert decrypted_creds['passphrase'] == passphrase, "Passphrase decryption failed!"
        print("  ✅ Credentials encryption/decryption works!")
        
        # Test without passphrase
        print("\n📝 Test 3: Credentials without passphrase")
        encrypted_no_pass = service.encrypt_credentials(api_key, api_secret)
        decrypted_no_pass = service.decrypt_credentials(encrypted_no_pass)
        
        assert 'passphrase' not in encrypted_no_pass, "Passphrase should not exist!"
        assert 'passphrase' not in decrypted_no_pass, "Passphrase should not exist!"
        print("  ✅ Credentials without passphrase works!")
        
        print("\n" + "=" * 80)
        print("🎉 All encryption tests passed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_encryption()
