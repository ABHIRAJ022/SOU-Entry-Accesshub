import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def _key():
    configured = os.getenv('BIOMETRIC_AES256_KEY')
    if configured:
        try:
            key = base64.urlsafe_b64decode(configured.encode())
            if len(key) != 32:
                raise ValueError
            return key
        except (ValueError, TypeError, base64.binascii.Error) as exc:
            raise ValueError('BIOMETRIC_AES256_KEY must be a URL-safe base64 encoded 32-byte key.') from exc
    return hashlib.sha256(settings.SECRET_KEY.encode()).digest()


def encrypt_vector(vector):
    nonce = os.urandom(12)
    plaintext = ','.join(f'{float(value):.12g}' for value in vector).encode()
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext, b'smart-campus-face-vector-v1')
    return base64.urlsafe_b64encode(nonce + ciphertext).decode()


def decrypt_vector(payload):
    raw = base64.urlsafe_b64decode(payload.encode())
    plaintext = AESGCM(_key()).decrypt(raw[:12], raw[12:], b'smart-campus-face-vector-v1')
    return [float(value) for value in plaintext.decode().split(',')]
