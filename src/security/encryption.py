"""
Encryption module for securing sensitive data (API keys, secrets)
Uses Fernet symmetric encryption from cryptography library
"""

import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        """Initialize encryption service with key from environment"""
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if not self.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY not found in environment variables. "
                "Please generate one using: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            self.cipher = Fernet(self.encryption_key.encode())
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY format: {str(e)}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            encrypted_text: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            raise ValueError("Cannot decrypt empty string")
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    def encrypt_credentials(self, api_key: str, api_secret: str, passphrase: str = None) -> dict:
        """
        Encrypt exchange credentials
        
        Args:
            api_key: Exchange API key
            api_secret: Exchange API secret
            passphrase: Optional passphrase (for exchanges that require it)
            
        Returns:
            Dictionary with encrypted credentials
        """
        encrypted = {
            'api_key': self.encrypt(api_key),
            'api_secret': self.encrypt(api_secret)
        }
        
        if passphrase:
            encrypted['passphrase'] = self.encrypt(passphrase)
        
        return encrypted
    
    def decrypt_credentials(self, encrypted_credentials: dict) -> dict:
        """
        Decrypt exchange credentials
        
        Args:
            encrypted_credentials: Dictionary with encrypted credentials
            
        Returns:
            Dictionary with decrypted credentials
        """
        decrypted = {
            'api_key': self.decrypt(encrypted_credentials['api_key']),
            'api_secret': self.decrypt(encrypted_credentials['api_secret'])
        }
        
        if 'passphrase' in encrypted_credentials and encrypted_credentials['passphrase']:
            decrypted['passphrase'] = self.decrypt(encrypted_credentials['passphrase'])
        
        return decrypted


# Singleton instance
_encryption_service = None

def get_encryption_service() -> EncryptionService:
    """Get singleton instance of encryption service"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
