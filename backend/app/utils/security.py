# English only for code
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()  # Argon2id defaults: strong & memory-hard

def hash_password(raw: str) -> str:
    return _ph.hash(raw)

def verify_password(stored_hash: str, raw: str) -> bool:
    try:
        _ph.verify(stored_hash, raw)
        return True
    except VerifyMismatchError:
        return False

