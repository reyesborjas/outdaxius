# app/db/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env if present

# === Database configuration ===
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:123456789@localhost:5432/outdaxius_db"
)

# === JWT / Authentication ===
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_for_jwt")  # 🔑 used for JWT tokens
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# === Vendor payment-credential encryption (Phase 4) ===
# Nothing consumes this yet — company_payment_accounts.credentials_encrypted (Fernet) is Phase 4
# work — but the app must refuse to boot without it rather than silently breaking later.
CREDENTIALS_ENCRYPTION_KEY = os.getenv("CREDENTIALS_ENCRYPTION_KEY")
if not CREDENTIALS_ENCRYPTION_KEY:
    raise RuntimeError(
        "CREDENTIALS_ENCRYPTION_KEY environment variable is not set. "
        "This key encrypts vendor payment gateway credentials at rest and the application "
        "must not boot without it. Generate one with: "
        "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )
