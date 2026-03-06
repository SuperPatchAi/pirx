"""Token encryption/decryption using Fernet symmetric encryption."""

import base64
import hashlib
from cryptography.fernet import Fernet


def _get_fernet(key: str) -> Fernet:
    """Derive a valid Fernet key from an arbitrary string."""
    if not key:
        raise ValueError("TOKEN_ENCRYPTION_KEY is not configured")
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_token(plaintext: str, key: str) -> str:
    """Encrypt a token string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = _get_fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, key: str) -> str:
    """Decrypt a token string. Returns plaintext."""
    if not ciphertext:
        return ""
    f = _get_fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
