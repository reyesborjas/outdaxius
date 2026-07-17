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
