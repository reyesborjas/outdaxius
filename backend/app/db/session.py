# app/db/session.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.config import DATABASE_URL

# echo was hardcoded True, which logs every statement and its bound parameters. That buries the
# output of any management script and, in a deployed environment, writes user data into the
# application log. Opt in explicitly with SQL_ECHO=1 when debugging a query.
SQL_ECHO = os.getenv("SQL_ECHO", "").strip().lower() in {"1", "true", "yes"}

# Create engine
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, future=True)

# SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
