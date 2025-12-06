"""
Verify encrypted data in database
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pymongo import MongoClient
from src.security.encryption import get_encryption_service

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['MultExchange']

def verify_encrypted_data():
    """Verify data is properly encrypted in database"""
    
    print("=" * 80)
    print("🔍 VERIFYING ENCRYPTED DATA IN DATABASE")
    print("=" * 80)
    
    # Get linked exchanges
    user_exchanges = list(db.user_exchanges.find())
    
    if not user_exchanges:
        print("\n❌ No linked exchanges found in database")
        return
    
    print(f"\n✅ Found {len(user_exchanges)} linked exchange(s)")
    
    encryption_service = get_encryption_service()
    
    for idx, link in enumerate(user_exchanges, 1):
        print(f"\n{'=' * 80}")
        print(f"LINK #{idx}")
        print('=' * 80)
        
        # Get exchange details
        exchange = db.exchanges.find_one({'_id': link['exchange_id']})
        
        print(f"\n📊 Basic Info:")
        print(f"   User ID: {link['user_id']}")
        print(f"   Exchange: {exchange['nome']}")
        print(f"   Link ID: {link['_id']}")
        print(f"   Created: {link['created_at']}")
        print(f"   Active: {link['is_active']}")
        
        print(f"\n🔐 Encrypted Data (stored in DB):")
        print(f"   API Key: {link['api_key_encrypted'][:50]}...")
        print(f"   API Secret: {link['api_secret_encrypted'][:50]}...")
        if link.get('passphrase_encrypted'):
            print(f"   Passphrase: {link['passphrase_encrypted'][:50]}...")
        else:
            print(f"   Passphrase: None (not required)")
        
        # Decrypt to verify
        try:
            decrypted_key = encryption_service.decrypt(link['api_key_encrypted'])
            decrypted_secret = encryption_service.decrypt(link['api_secret_encrypted'])
            
            print(f"\n✅ Decrypted Data (verified):")
            print(f"   API Key: {decrypted_key[:10]}... (length: {len(decrypted_key)})")
            print(f"   API Secret: {decrypted_secret[:10]}... (length: {len(decrypted_secret)})")
            
            if link.get('passphrase_encrypted'):
                decrypted_passphrase = encryption_service.decrypt(link['passphrase_encrypted'])
                print(f"   Passphrase: {decrypted_passphrase[:10]}... (length: {len(decrypted_passphrase)})")
            
            print(f"\n✅ Decryption successful! Data integrity verified.")
            
        except Exception as e:
            print(f"\n❌ Decryption failed: {str(e)}")
    
    print(f"\n{'=' * 80}")
    print("🎉 VERIFICATION COMPLETED")
    print('=' * 80)

if __name__ == "__main__":
    verify_encrypted_data()
