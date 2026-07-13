"""Fernet encryption for bearer credentials stored at rest (spec §9).

The AI Labs API key is a bearer credential to the employee's agent. It must never
be stored in plaintext and never sent to a browser.
"""

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.FERNET_KEY.encode())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
