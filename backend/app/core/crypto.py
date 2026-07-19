# app/core/crypto.py
"""
Envelope encryption for vendor payment gateway credentials
(company_payment_accounts.credentials_encrypted). Never log, return, or include the plaintext or
the encrypted bytes in any API response or Pydantic schema -- a leak here compromises every vendor
on the platform simultaneously.
"""
import json

from cryptography.fernet import Fernet, InvalidToken

from app.db.config import CREDENTIALS_ENCRYPTION_KEY

_fernet = Fernet(
    CREDENTIALS_ENCRYPTION_KEY.encode()
    if isinstance(CREDENTIALS_ENCRYPTION_KEY, str)
    else CREDENTIALS_ENCRYPTION_KEY
)


def encrypt_credentials(credentials: dict) -> bytes:
    """JSON-serialize then Fernet-encrypt a provider credential dict (e.g. {"api_key": ...,
    "secret_key": ...} for Flow) for storage in company_payment_accounts.credentials_encrypted."""
    plaintext = json.dumps(credentials).encode("utf-8")
    return _fernet.encrypt(plaintext)


def decrypt_credentials(ciphertext: bytes) -> dict:
    """Inverse of encrypt_credentials. Raises ValueError on a corrupted/wrong-key ciphertext
    rather than leaking the raw InvalidToken internals."""
    try:
        plaintext = _fernet.decrypt(bytes(ciphertext))
    except InvalidToken as exc:
        raise ValueError("Could not decrypt provider credentials (wrong key or corrupted data)") from exc
    return json.loads(plaintext.decode("utf-8"))
