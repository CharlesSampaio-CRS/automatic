"""
Script to generate a new Fernet encryption key
Run this once and add the key to your .env file as ENCRYPTION_KEY
"""

from cryptography.fernet import Fernet

def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    key = Fernet.generate_key()
    key_str = key.decode()
    
    print("=" * 80)
    print("🔐 NEW ENCRYPTION KEY GENERATED")
    print("=" * 80)
    print("\nCopy this key to your .env file:\n")
    print(f"ENCRYPTION_KEY={key_str}")
    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("=" * 80)
    print("1. Keep this key SECRET - never commit it to version control")
    print("2. Store it securely in your .env file (which should be in .gitignore)")
    print("3. If you lose this key, you CANNOT decrypt existing data")
    print("4. Use the same key across all environments for the same database")
    print("5. Rotate this key periodically for better security")
    print("=" * 80)
    
    return key_str

if __name__ == "__main__":
    generate_encryption_key()
